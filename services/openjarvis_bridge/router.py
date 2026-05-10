"""
Hybrid Router — extends ModelRouter with OpenJarvis local execution target.

Routes each task to the optimal target:
- TRIVIAL / SIMPLE complexity → local OpenJarvis (Qwen 4B, $0, instant)
- MODERATE+ complexity → cloud model via OpenRouter
- Local unavailable → automatic cloud fallback

The user never chooses where it runs. The system decides.
"""

import logging

from ..shared import ModelRouter, TaskComplexity
from ..shared import EventBus, get_event_bus

logger = logging.getLogger(__name__)


class HybridRouter:
    """
    Extends Powerhouse's ModelRouter with local OpenJarvis as a first-class target.

    Usage:
        router = HybridRouter(local_available=True)

        # Auto-routing
        target, model = router.route("check_margin", TaskComplexity.SIMPLE)
        # → ("local", "qwen3:4b")

        target, model = router.route("build_store", TaskComplexity.COMPLEX)
        # → ("cloud", "anthropic/claude-opus-4")
    """

    # Default local models per engine
    LOCAL_MODELS = {
        "ollama": "qwen3:4b",
        "vllm": "qwen3:4b",
        "llama.cpp": "llama-3.2-3b",
    }

    def __init__(
        self,
        local_available: bool = False,
        local_engine: str = "ollama",
        local_model: str = "",
    ):
        self._router = ModelRouter()
        self.local_available = local_available
        self.local_engine = local_engine
        self.local_model = local_model or self.LOCAL_MODELS.get(
            local_engine, "qwen3:4b"
        )
        self._bus: EventBus = get_event_bus()
        self._stats = {
            "local_queries": 0,
            "cloud_queries": 0,
            "local_fallbacks": 0,
            "total_cost_saved_usd": 0.0,
        }

    @property
    def is_local_available(self) -> bool:
        return self.local_available

    def set_local_available(self, available: bool) -> None:
        """Update local availability (e.g., after OpenJarvis init)."""
        was_available = self.local_available
        self.local_available = available
        if available and not was_available:
            logger.info("OpenJarvis local runtime now available")
        elif not available and was_available:
            logger.warning("OpenJarvis local runtime lost — cloud fallback active")

    def route(
        self,
        task_type: str,
        complexity: TaskComplexity,
        max_cost: float | None = None,
        force_target: str | None = None,
    ) -> tuple[str, str]:
        """
        Route a task to the optimal target and model.

        Returns:
            (target, model) — target is "local" or "cloud"
        """
        # Force override
        if force_target == "local" and self.local_available:
            self._stats["local_queries"] += 1
            return ("local", self.local_model)
        if force_target == "cloud":
            model = self._router.route(task_type, complexity, max_cost)
            self._stats["cloud_queries"] += 1
            return ("cloud", model)

        # Local can handle simple tasks
        if self.local_available and complexity in (
            TaskComplexity.TRIVIAL,
            TaskComplexity.SIMPLE,
        ):
            self._stats["local_queries"] += 1

            # Log routing decision
            logger.info(
                "HybridRouter: %s/%s → local (%s)",
                task_type,
                complexity.value,
                self.local_model,
            )
            return ("local", self.local_model)

        # Cloud for everything else
        model = self._router.route(task_type, complexity, max_cost)
        self._stats["cloud_queries"] += 1

        # Estimate cost savings vs. always-cloud
        cloud_cost = self._router.MODEL_COSTS.get(model, 5.0)
        self._stats["total_cost_saved_usd"] += (
            cloud_cost
            if self.local_available
            and complexity in (TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE)
            else 0
        )

        logger.info(
            "HybridRouter: %s/%s → cloud (%s, $%.4f/1M)",
            task_type,
            complexity.value,
            model,
            cloud_cost,
        )
        return ("cloud", model)

    def get_fallback_target(self, primary_target: str) -> str:
        """If primary fails, where to fall back."""
        if primary_target == "local":
            self._stats["local_fallbacks"] += 1
            return "cloud"
        # Cloud failed → try another cloud model
        return "cloud"

    def get_metrics(self) -> dict:
        """Return routing metrics."""
        total = self._stats["local_queries"] + self._stats["cloud_queries"]
        local_pct = (self._stats["local_queries"] / max(total, 1)) * 100
        return {
            **self._stats,
            "total_queries": total,
            "local_percentage": round(local_pct, 1),
            "local_available": self.local_available,
            "local_model": self.local_model,
        }

    def list_targets(self) -> list[dict]:
        """List all available execution targets."""
        targets = [
            {
                "target": "cloud",
                "available": True,
                "models": list(self._router.MODEL_COSTS.keys()),
                "cost": "From $0.15/1M tokens",
                "latency": "1-30s",
            }
        ]
        if self.local_available:
            targets.insert(
                0,
                {
                    "target": "local",
                    "available": True,
                    "model": self.local_model,
                    "cost": "$0.00",
                    "latency": "0.1-1s",
                    "private": True,
                    "offline": True,
                },
            )
        return targets
