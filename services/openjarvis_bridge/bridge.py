"""
OpenJarvis Bridge — local-first agent runtime integrated with Powerhouse.

Wraps Stanford's OpenJarvis framework to provide on-device AI capabilities.
Simple queries run locally (free, instant, private). Complex tasks escalate
to Powerhouse's cloud agent swarm.

Usage:
    bridge = OpenJarvisBridge()
    
    # Simple query → local OpenJarvis (Qwen 4B, ~0.3s)
    result = await bridge.ask("What's my margin on Sukienki XL?")
    
    # Complex task → Powerhouse cloud (Claude Opus, agent swarm)
    result = await bridge.build("Build me a store with Shopify + BLIK")
    
    # The user never chooses — the router decides.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from ..shared import EventBus, Event, EventPriority, get_event_bus
from ..shared import EpisodicMemory, MemoryEntry, get_memory
from ..shared import ModelRouter, TaskComplexity, get_router, get_tracer

logger = logging.getLogger(__name__)


class ExecutionTarget(str, Enum):
    """Where a query was executed."""
    LOCAL = "local"        # OpenJarvis on-device
    CLOUD = "cloud"        # Powerhouse agent swarm
    LOCAL_FALLBACK = "local_fallback"  # Cloud failed, fell back to local


@dataclass
class BridgeResult:
    """Result from the OpenJarvis bridge."""
    query: str
    target: ExecutionTarget
    model: str = ""
    response: str = ""
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    tokens_used: int = 0
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OpenJarvisBridge:
    """
    Bridge between Powerhouse and OpenJarvis local runtime.
    
    Handles:
    - Initializing local OpenJarvis runtime (if available)
    - Routing queries to local or cloud based on complexity
    - Emitting results as events
    - Storing query history in episodic memory
    """

    # Complexity thresholds for local execution
    LOCAL_MAX_COMPLEXITY = TaskComplexity.SIMPLE  # TRIVIAL + SIMPLE → local
    LOCAL_MAX_TOKENS = 500  # Short queries stay local
    LOCAL_MAX_COST = 0.0001  # Effectively $0 for local

    def __init__(
        self,
        engine: str = "ollama",
        local_model: str = "qwen3:4b",
        cloud_model: str = "",
    ):
        self.engine = engine
        self.local_model = local_model
        self.cloud_model = cloud_model
        self._jarvis = None
        self._available = False
        self._bus: EventBus = get_event_bus()
        self._memory: EpisodicMemory = get_memory()
        self._router: ModelRouter = get_router()
        self._tracer = get_tracer("openjarvis_bridge")
        self._init_jarvis()

    def _init_jarvis(self) -> None:
        """Try to initialize OpenJarvis. Graceful fallback if unavailable."""
        try:
            from openjarvis import Jarvis
            self._jarvis = Jarvis(engine_key=self.engine)
            self._available = True
            logger.info(
                "OpenJarvis initialized: engine=%s, model=%s",
                self.engine, self.local_model,
            )
        except ImportError:
            logger.info(
                "OpenJarvis not installed. Install with: "
                "git clone https://github.com/open-jarvis/OpenJarvis && "
                "cd OpenJarvis && uv sync"
            )
            self._available = False
        except Exception as e:
            logger.warning("OpenJarvis init failed: %s. Cloud-only mode.", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        """Is OpenJarvis local runtime available?"""
        return self._available and self._jarvis is not None

    async def ask(self, query: str, force: ExecutionTarget | None = None) -> BridgeResult:
        """
        Ask a question. Router decides local vs cloud.
        
        Args:
            query: The user's question
            force: Override routing (e.g., force cloud for testing)
        """
        started = datetime.now(timezone.utc)

        # Determine target
        if force:
            target = force
        else:
            target = self._route_query(query)

        # Emit start event
        await self._bus.emit_nowait(Event(
            event_type="bridge.query_started",
            payload={"query": query[:200], "target": target.value},
            source="openjarvis_bridge",
        ))

        result = BridgeResult(query=query, target=target)

        try:
            if target == ExecutionTarget.LOCAL:
                result = await self._execute_local(query)
            else:
                result = await self._execute_cloud(query)

            # Store in memory
            await self._memory.remember(
                agent_id="openjarvis_bridge",
                memory_type="action",
                content=f"Query: {query[:200]}",
                metadata={
                    "target": result.target.value,
                    "model": result.model,
                    "duration_ms": result.duration_ms,
                    "cost_usd": result.cost_usd,
                },
            )

            # Emit completion
            await self._bus.emit_nowait(Event(
                event_type="bridge.query_completed",
                payload={
                    "query": query[:200],
                    "target": result.target.value,
                    "duration_ms": result.duration_ms,
                },
                source="openjarvis_bridge",
            ))

        except Exception as e:
            # Local failed → try cloud fallback
            if target == ExecutionTarget.LOCAL and self._router:
                logger.warning("Local execution failed: %s. Falling back to cloud.", e)
                result.target = ExecutionTarget.LOCAL_FALLBACK
                try:
                    result = await self._execute_cloud(query)
                except Exception as e2:
                    result.error = f"Both local and cloud failed: {e2}"

        result.duration_ms = (
            datetime.now(timezone.utc) - started
        ).total_seconds() * 1000
        return result

    async def build(self, intent: str) -> BridgeResult:
        """
        Build something — always goes to cloud for full agent swarm.
        """
        return await self.ask(intent, force=ExecutionTarget.CLOUD)

    async def analyze(self, query: str) -> BridgeResult:
        """
        Analyze data — tries local first for simple analysis.
        """
        return await self.ask(query)

    def _route_query(self, query: str) -> ExecutionTarget:
        """Decide whether to route to local or cloud."""
        if not self.is_available:
            return ExecutionTarget.CLOUD

        # Heuristic: complexity estimation
        complexity = self._estimate_complexity(query)

        if complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE):
            return ExecutionTarget.LOCAL

        # Long queries go to cloud
        if len(query) > self.LOCAL_MAX_TOKENS * 4:
            return ExecutionTarget.CLOUD

        return ExecutionTarget.CLOUD

    async def _execute_local(self, query: str) -> BridgeResult:
        """Execute query on local OpenJarvis."""
        if not self.is_available:
            raise RuntimeError("OpenJarvis not available")

        model = self.local_model

        with self._tracer.span("bridge.local", {"model": model, "query_len": len(query)}):
            try:
                response = self._jarvis.ask(query, model=model)
                return BridgeResult(
                    query=query,
                    target=ExecutionTarget.LOCAL,
                    model=model,
                    response=str(response),
                    cost_usd=0.0,  # Local is free
                )
            except Exception as e:
                raise RuntimeError(f"Local execution failed: {e}")

    async def _execute_cloud(self, query: str) -> BridgeResult:
        """Execute query on Powerhouse cloud agent swarm."""
        model = self.cloud_model or self._router.route(
            "quick_chat", TaskComplexity.MODERATE
        )

        with self._tracer.span("bridge.cloud", {"model": model, "query_len": len(query)}):
            # Delegate to Powerhouse agent kernel
            from ..instill_runtime import AgentKernel, AgentConfig

            kernel = AgentKernel(
                agent_type="cloud_worker",
                config=AgentConfig(
                    model=model,
                    max_iterations=3,
                    cost_budget_usd=1.0,
                ),
            )
            await kernel.start()
            task_result = await kernel.run(query)
            await kernel.terminate()

            return BridgeResult(
                query=query,
                target=ExecutionTarget.CLOUD,
                model=model,
                response=task_result.output,
                cost_usd=task_result.cost_usd,
                tokens_used=0,
            )

    def _estimate_complexity(self, query: str) -> TaskComplexity:
        """Heuristic complexity estimation."""
        query_lower = query.lower()

        # Build/deploy keywords → complex
        if any(w in query_lower for w in [
            "build", "deploy", "create", "scaffold", "design",
            "architecture", "system", "infrastructure",
        ]):
            return TaskComplexity.COMPLEX

        # Analysis keywords → moderate
        if any(w in query_lower for w in [
            "analyze", "optimize", "refactor", "migrate",
            "investigate", "debug", "diagnose",
        ]):
            return TaskComplexity.MODERATE

        # Simple factual queries → simple
        if any(w in query_lower for w in [
            "what", "how many", "show me", "list", "check",
            "summarize", "status", "health",
        ]):
            return TaskComplexity.SIMPLE

        return TaskComplexity.SIMPLE

    def health_check(self) -> dict:
        """Return bridge health status."""
        return {
            "openjarvis_available": self.is_available,
            "engine": self.engine,
            "local_model": self.local_model,
            "cloud_model": self.cloud_model or "auto",
            "local_max_complexity": self.LOCAL_MAX_COMPLEXITY.value,
        }

    def close(self) -> None:
        """Clean shutdown."""
        if self._jarvis:
            try:
                self._jarvis.close()
            except Exception:
                pass
        self._available = False
