"""
Agent Kernel — the runtime heart of every Powerhouse agent.

Manages agent lifecycle: idle → running → sleeping → terminated.
Each agent has its own memory, event subscriptions, and config.

Usage:
    kernel = AgentKernel(
        agent_id="autofix-001",
        agent_type="autofix",
        config=AgentConfig(max_iterations=10),
    )
    await kernel.start()
    result = await kernel.run(task="Fix auth NullPointerException")
    await kernel.sleep()
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

from ..shared import EventBus, Event, EventPriority, get_event_bus
from ..shared import EpisodicMemory, get_memory
from ..shared import ModelRouter, TaskComplexity, get_router
from ..shared import Tracer, get_tracer

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Possible lifecycle states of an agent."""
    IDLE = "idle"          # Created, not yet started
    RUNNING = "running"    # Actively executing a task
    SLEEPING = "sleeping"  # Paused, waiting for trigger
    ERROR = "error"        # Hit an exception, needs intervention
    TERMINATED = "terminated"  # Done, cleaned up


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    max_iterations: int = 10            # Max reasoning loops per task
    max_tokens_per_call: int = 8000     # Truncate prompts above this
    timeout_seconds: int = 300          # Max wall-clock time per task
    retry_on_error: bool = True         # Retry once on failure
    cost_budget_usd: float = 1.0        # Max spend per task
    model: str = ""                     # Override default routing
    subscribe_to: list[str] = field(default_factory=list)  # Event types to listen for


@dataclass
class TaskResult:
    """Result of an agent task execution."""
    task_id: str
    agent_id: str
    status: str  # "completed", "failed", "timeout", "cancelled"
    output: str = ""
    error: str = ""
    iterations: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    memory_entries: int = 0  # How many new memories were created


class AgentKernel:
    """
    The runtime for a single agent.
    
    Handles lifecycle, memory, event subscriptions, and task execution.
    """

    def __init__(
        self,
        agent_id: str = "",
        agent_type: str = "generic",
        config: AgentConfig | None = None,
    ):
        self.agent_id = agent_id or f"{agent_type}-{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self._bus: EventBus = get_event_bus()
        self._memory: EpisodicMemory = get_memory()
        self._router: ModelRouter = get_router()
        self._tracer: Tracer = get_tracer(service_name=self.agent_id)
        self._task_handler: Callable[..., Coroutine] | None = None
        self._created_at = datetime.now(timezone.utc)
        self._stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
        }

    async def start(self) -> None:
        """Initialize the agent and subscribe to events."""
        self.state = AgentState.IDLE

        # Subscribe to configured event types
        for event_type in self.config.subscribe_to:
            self._bus.subscribe(event_type, self._on_event)

        # Announce our existence
        await self._bus.emit_nowait(Event(
            event_type="agent.started",
            payload={"agent_id": self.agent_id, "agent_type": self.agent_type},
            source=self.agent_id,
            priority=EventPriority.LOW,
        ))

        # Remember this startup in episodic memory
        await self._memory.remember(
            agent_id=self.agent_id,
            memory_type="observation",
            content=f"Agent {self.agent_id} ({self.agent_type}) started",
            metadata={"state": self.state.value},
        )

        logger.info("Agent %s started (type=%s)", self.agent_id, self.agent_type)

    async def run(self, task: str, context: dict | None = None) -> TaskResult:
        """
        Execute a task.
        
        The agent will:
        1. Recall similar past tasks from memory
        2. Route to appropriate model based on complexity
        3. Execute the task handler
        4. Record the result
        """
        if self.state == AgentState.TERMINATED:
            return TaskResult(
                task_id="", agent_id=self.agent_id,
                status="failed", error="Agent is terminated"
            )

        task_id = uuid.uuid4().hex[:12]
        started = datetime.now(timezone.utc)
        self.state = AgentState.RUNNING
        iterations = 0

        logger.info("Agent %s running task: %s", self.agent_id, task[:80])

        with self._tracer.span("agent.run", {"task_id": task_id, "agent_id": self.agent_id}):
            try:
                # Step 1: Recall similar past experiences
                memories = await self._memory.recall(
                    query=task, agent_id=self.agent_id, limit=3
                )
                memory_context = "\n".join([m.content for m in memories]) if memories else ""

                # Step 2: Route to appropriate model
                complexity = self._estimate_complexity(task)
                model = self.config.model or self._router.route(
                    self.agent_type, complexity, max_cost=self.config.cost_budget_usd
                )

                # Step 3: Announce task start
                await self._bus.emit_nowait(Event(
                    event_type="agent.task_started",
                    payload={
                        "task_id": task_id, "agent_id": self.agent_id,
                        "task": task[:200], "model": model,
                    },
                    source=self.agent_id,
                ))

                # Step 4: Execute (or simulate if no handler attached)
                if self._task_handler:
                    output = await asyncio.wait_for(
                        self._task_handler(task=task, context=context, model=model,
                                          memory_context=memory_context),
                        timeout=self.config.timeout_seconds,
                    )
                else:
                    output = f"[{self.agent_type}] Received task: {task[:200]}\n"
                    output += f"Model: {model}\n"
                    if memory_context:
                        output += f"Relevant memories: {len(memories)} found\n"
                    output += "No task handler attached — attach one with kernel.on_task(handler)"

                duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
                cost = self._router.estimate_cost(model, len(task) // 4, len(output) // 4)
                self._stats["total_cost_usd"] += cost
                self._stats["tasks_completed"] += 1

                # Step 5: Remember this execution
                await self._memory.remember(
                    agent_id=self.agent_id,
                    memory_type="action",
                    content=f"Completed: {task[:200]}",
                    metadata={
                        "task_id": task_id, "model": model, "cost_usd": cost,
                        "duration_ms": duration_ms, "iterations": iterations,
                    },
                )

                self.state = AgentState.IDLE

                await self._bus.emit_nowait(Event(
                    event_type="agent.task_completed",
                    payload={"task_id": task_id, "agent_id": self.agent_id, "cost_usd": cost},
                    source=self.agent_id,
                ))

                return TaskResult(
                    task_id=task_id, agent_id=self.agent_id,
                    status="completed", output=output,
                    iterations=iterations, cost_usd=cost,
                    duration_ms=duration_ms, memory_entries=1,
                )

            except asyncio.TimeoutError:
                self.state = AgentState.ERROR
                duration_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000
                await self._memory.remember(
                    agent_id=self.agent_id, memory_type="error",
                    content=f"Timeout: {task[:200]}",
                    metadata={"task_id": task_id, "duration_ms": duration_ms},
                )
                return TaskResult(
                    task_id=task_id, agent_id=self.agent_id,
                    status="timeout", error=f"Task exceeded {self.config.timeout_seconds}s",
                    duration_ms=duration_ms,
                )

            except Exception as e:
                self.state = AgentState.ERROR
                self._stats["tasks_failed"] += 1
                await self._memory.remember(
                    agent_id=self.agent_id, memory_type="error",
                    content=f"Error: {str(e)[:500]}",
                    metadata={"task_id": task_id, "task": task[:200]},
                )
                logger.exception("Agent %s task failed", self.agent_id)
                return TaskResult(
                    task_id=task_id, agent_id=self.agent_id,
                    status="failed", error=str(e)[:500],
                )

    async def sleep(self) -> None:
        """Pause the agent — it will wake on subscribed events."""
        self.state = AgentState.SLEEPING
        await self._bus.emit_nowait(Event(
            event_type="agent.sleeping",
            payload={"agent_id": self.agent_id},
            source=self.agent_id,
        ))
        logger.info("Agent %s sleeping", self.agent_id)

    async def wake(self) -> None:
        """Resume from sleep."""
        self.state = AgentState.IDLE
        logger.info("Agent %s awake", self.agent_id)

    async def terminate(self) -> None:
        """Clean shutdown."""
        self.state = AgentState.TERMINATED
        for event_type in self.config.subscribe_to:
            self._bus.unsubscribe(event_type, self._on_event)
        await self._bus.emit_nowait(Event(
            event_type="agent.terminated",
            payload={"agent_id": self.agent_id, "stats": self._stats},
            source=self.agent_id,
        ))
        logger.info("Agent %s terminated. Stats: %s", self.agent_id, self._stats)

    def on_task(self, handler: Callable[..., Coroutine]) -> None:
        """Attach a task handler function."""
        self._task_handler = handler

    async def _on_event(self, event: Event) -> None:
        """Handle subscribed events (wake agent if sleeping)."""
        if self.state == AgentState.SLEEPING:
            await self.wake()
        await self._memory.remember(
            agent_id=self.agent_id,
            memory_type="observation",
            content=f"Received event: {event.event_type}",
            metadata=event.payload,
        )

    def _estimate_complexity(self, task: str) -> TaskComplexity:
        """Heuristic complexity estimation based on task content."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["fix", "bug", "error", "crash", "outage"]):
            return TaskComplexity.COMPLEX
        if any(w in task_lower for w in ["design", "architect", "system", "refactor"]):
            return TaskComplexity.COMPLEX
        if any(w in task_lower for w in ["add", "create", "build", "implement"]):
            return TaskComplexity.MODERATE
        if any(w in task_lower for w in ["check", "test", "review", "lint"]):
            return TaskComplexity.SIMPLE
        return TaskComplexity.SIMPLE

    @property
    def stats(self) -> dict:
        return {**self._stats, "state": self.state.value, "agent_type": self.agent_type}
