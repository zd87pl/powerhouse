"""
Model Router — routes each task to the optimal model.

Not every prompt needs Claude Opus. Not every quick query needs GPT-4o.
The router picks the right model based on task type, complexity, and cost budget.

Saves ~70% on API costs vs. always using the biggest model.
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"  # "What does git status do?"
    SIMPLE = "simple"  # "Add a comment to this function"
    MODERATE = "moderate"  # "Refactor this module"
    COMPLEX = "complex"  # "Design the authentication system"
    CRITICAL = "critical"  # "Fix this production outage"


@dataclass
class RouterCall:
    """Metadata about a routed call."""

    task_type: str
    complexity: TaskComplexity
    model: str
    provider: str = "openrouter"
    estimated_cost_usd: float = 0.0
    actual_tokens: int = 0
    fallback_used: bool = False


class ModelRouter:
    """
    Routes tasks to the optimal model based on complexity and budget.

    Usage:
        router = ModelRouter()

        # Automatic routing
        model = router.route("code_review", TaskComplexity.MODERATE)
        # → returns "anthropic/claude-sonnet-4"

        # With budget constraint
        model = router.route("quick_chat", TaskComplexity.TRIVIAL, max_cost=0.001)
        # → returns "meta-llama/llama-4-maverick:free"
    """

    # Default model assignments per task type × complexity
    # Format: task_type → { complexity_level → model }
    DEFAULT_ROUTES: dict[str, dict[TaskComplexity, str]] = {
        "code_generation": {
            TaskComplexity.TRIVIAL: "meta-llama/llama-4-maverick:free",
            TaskComplexity.SIMPLE: "google/gemini-2.5-flash-lite",
            TaskComplexity.MODERATE: "anthropic/claude-sonnet-4",
            TaskComplexity.COMPLEX: "anthropic/claude-opus-4",
            TaskComplexity.CRITICAL: "anthropic/claude-opus-4",
        },
        "code_review": {
            TaskComplexity.TRIVIAL: "google/gemini-2.5-flash-lite",
            TaskComplexity.SIMPLE: "anthropic/claude-sonnet-4",
            TaskComplexity.MODERATE: "anthropic/claude-sonnet-4",
            TaskComplexity.COMPLEX: "anthropic/claude-opus-4",
            TaskComplexity.CRITICAL: "anthropic/claude-opus-4",
        },
        "planning": {
            TaskComplexity.TRIVIAL: "google/gemini-2.5-flash-lite",
            TaskComplexity.SIMPLE: "anthropic/claude-sonnet-4",
            TaskComplexity.MODERATE: "anthropic/claude-opus-4",
            TaskComplexity.COMPLEX: "anthropic/claude-opus-4",
            TaskComplexity.CRITICAL: "anthropic/claude-opus-4",
        },
        "debugging": {
            TaskComplexity.TRIVIAL: "google/gemini-2.5-flash-lite",
            TaskComplexity.SIMPLE: "anthropic/claude-sonnet-4",
            TaskComplexity.MODERATE: "anthropic/claude-sonnet-4",
            TaskComplexity.COMPLEX: "anthropic/claude-opus-4",
            TaskComplexity.CRITICAL: "anthropic/claude-opus-4",
        },
        "quick_chat": {
            TaskComplexity.TRIVIAL: "meta-llama/llama-4-maverick:free",
            TaskComplexity.SIMPLE: "google/gemini-2.5-flash-lite",
            TaskComplexity.MODERATE: "google/gemini-2.5-flash-lite",
            TaskComplexity.COMPLEX: "anthropic/claude-sonnet-4",
            TaskComplexity.CRITICAL: "anthropic/claude-sonnet-4",
        },
        "research": {
            TaskComplexity.TRIVIAL: "google/gemini-2.5-flash-lite",
            TaskComplexity.SIMPLE: "anthropic/claude-sonnet-4",
            TaskComplexity.MODERATE: "anthropic/claude-opus-4",
            TaskComplexity.COMPLEX: "anthropic/claude-opus-4",
            TaskComplexity.CRITICAL: "anthropic/claude-opus-4",
        },
    }

    # Approximate cost per 1M tokens (USD)
    MODEL_COSTS: dict[str, float] = {
        "meta-llama/llama-4-maverick:free": 0.0,
        "google/gemini-2.5-flash-lite": 0.15,
        "anthropic/claude-sonnet-4": 3.0,
        "deepseek/deepseek-v4-pro": 2.5,
        "anthropic/claude-opus-4": 15.0,
        "openai/gpt-4o": 5.0,
    }

    def __init__(self, overrides: dict | None = None):
        self.routes = self.DEFAULT_ROUTES.copy()
        if overrides:
            for task_type, complexities in overrides.items():
                if task_type not in self.routes:
                    self.routes[task_type] = {}
                self.routes[task_type].update(complexities)

    def route(
        self,
        task_type: str,
        complexity: TaskComplexity,
        max_cost: float | None = None,
    ) -> str:
        """
        Pick the best model for this task.

        Args:
            task_type: e.g. "code_generation", "code_review", "debugging"
            complexity: How hard is this task?
            max_cost: Optional cost cap per 1M tokens. Overrides the default route.

        Returns:
            Model identifier string for OpenRouter API.
        """
        # Get default route
        task_routes = self.routes.get(task_type, self.routes["quick_chat"])
        model = task_routes.get(complexity, task_routes[TaskComplexity.MODERATE])

        # Apply cost budget
        if max_cost is not None:
            model_cost = self.MODEL_COSTS.get(model, 5.0)
            if model_cost > max_cost:
                # Downgrade to cheapest model under budget
                affordable = [
                    (m, c) for m, c in self.MODEL_COSTS.items() if c <= max_cost
                ]
                if affordable:
                    model = sorted(affordable, key=lambda x: x[1], reverse=True)[0][0]
                else:
                    model = "meta-llama/llama-4-maverick:free"

        logger.info(
            "Routed %s/%s → %s ($%.4f/1M tokens)",
            task_type,
            complexity.value,
            model,
            self.MODEL_COSTS.get(model, 0),
        )
        return model

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a call."""
        cost_per_m = self.MODEL_COSTS.get(model, 5.0)
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1_000_000) * cost_per_m

    def get_fallback_chain(self, task_type: str) -> list[str]:
        """
        Ordered fallback chain if the primary model fails.
        Tries progressively cheaper models.
        """
        primary = self.route(task_type, TaskComplexity.MODERATE)
        chain = [primary]
        # Add fallbacks: same tier → cheaper tier → free tier
        alternatives = [
            "deepseek/deepseek-v4-pro",
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash-lite",
            "meta-llama/llama-4-maverick:free",
        ]
        for alt in alternatives:
            if alt != primary:
                chain.append(alt)
        return chain

    def list_models(self) -> dict[str, float]:
        """Return all configured models with their costs."""
        return self.MODEL_COSTS.copy()


# Global singleton
_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
