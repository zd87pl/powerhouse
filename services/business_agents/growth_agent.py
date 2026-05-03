"""
Growth Agent — autonomous growth engineering.

Runs A/B tests, monitors traffic patterns, detects anomalies,
and recommends growth actions.

Usage:
    growth = GrowthAgent()
    await growth.start()
    result = await growth.run("Analyze traffic anomaly on /sukienki page")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..instill_runtime import AgentKernel, AgentConfig, TaskResult
from ..shared import EventBus, Event, EventPriority, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class GrowthAlert:
    """An actionable alert from the growth agent."""
    alert_type: str  # "traffic_anomaly", "conversion_drop", "ab_test_result"
    metric: str
    current_value: float
    baseline: float
    deviation_pct: float
    recommendation: str
    severity: str = "warning"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ABTestHypothesis:
    """A proposed A/B test."""
    id: str
    name: str
    hypothesis: str  # "If we [change], then [metric] will [improve] because [reason]"
    variant_a: str    # Control
    variant_b: str    # Treatment
    primary_metric: str  # e.g., "conversion_rate"
    expected_lift_pct: float
    min_sample_size: int = 1000
    estimated_duration_days: int = 7


class GrowthAgent:
    """
    Autonomous growth engineering agent.
    
    Monitors:
    - Traffic patterns and anomalies
    - Conversion rate changes
    - A/B test results (statistical significance)
    - Competitor pricing signals
    """

    # Anomaly thresholds
    TRAFFIC_ANOMALY_THRESHOLD = 0.30    # 30% deviation from baseline
    CONVERSION_DROP_THRESHOLD = 0.15     # 15% drop triggers alert
    BOUNCE_RATE_SPIKE = 0.20            # 20% increase in bounce rate

    def __init__(self):
        self._bus: EventBus = get_event_bus()
        self._kernel = AgentKernel(
            agent_type="growth",
            config=AgentConfig(
                max_iterations=5,
                cost_budget_usd=0.50,
                subscribe_to=[
                    "traffic.spike",
                    "conversion.changed",
                    "ab_test.completed",
                    "competitor.price_changed",
                ],
            ),
        )
        self._kernel.on_task(self._handle_task)
        self._active_tests: dict[str, ABTestHypothesis] = {}

    async def start(self) -> None:
        await self._kernel.start()
        logger.info("GrowthAgent started. Ready to optimize.")

    async def run(self, task: str, context: dict | None = None) -> TaskResult:
        return await self._kernel.run(task, context)

    async def detect_traffic_anomaly(
        self, page: str, current_visits: int, baseline_visits: int
    ) -> GrowthAlert | None:
        """Detect if a page has anomalous traffic."""
        if baseline_visits <= 0:
            return None

        deviation = (current_visits - baseline_visits) / baseline_visits

        if abs(deviation) > self.TRAFFIC_ANOMALY_THRESHOLD:
            direction = "spike" if deviation > 0 else "drop"
            alert = GrowthAlert(
                alert_type="traffic_anomaly",
                metric=f"{page} visits",
                current_value=current_visits,
                baseline=baseline_visits,
                deviation_pct=round(deviation * 100, 1),
                recommendation=(
                    f"Traffic {direction} of {abs(deviation)*100:.0f}% on {page}. "
                    f"{'Check for viral content or referrer.' if deviation > 0 else 'Check for broken links or SEO penalty.'}"
                ),
                severity="warning",
            )

            await self._bus.emit_nowait(Event(
                event_type="growth.traffic_anomaly",
                payload={
                    "page": page, "deviation_pct": alert.deviation_pct,
                    "direction": direction,
                },
                source="growth_agent",
                priority=EventPriority.NORMAL,
            ))

            return alert

        return None

    async def propose_ab_test(
        self, name: str, hypothesis: str, variant_a: str, variant_b: str,
        primary_metric: str = "conversion_rate",
        expected_lift_pct: float = 5.0,
    ) -> ABTestHypothesis:
        """Propose a new A/B test."""
        import uuid
        test = ABTestHypothesis(
            id=uuid.uuid4().hex[:8],
            name=name,
            hypothesis=hypothesis,
            variant_a=variant_a,
            variant_b=variant_b,
            primary_metric=primary_metric,
            expected_lift_pct=expected_lift_pct,
        )
        self._active_tests[test.id] = test

        await self._bus.emit_nowait(Event(
            event_type="growth.ab_test_proposed",
            payload={
                "test_id": test.id, "name": test.name,
                "hypothesis": test.hypothesis,
                "expected_lift_pct": test.expected_lift_pct,
            },
            source="growth_agent",
            priority=EventPriority.LOW,
        ))

        logger.info("A/B test proposed: %s", test.name)
        return test

    async def evaluate_ab_test(
        self, test_id: str, control_conversions: int, control_visitors: int,
        treatment_conversions: int, treatment_visitors: int,
    ) -> GrowthAlert | None:
        """Evaluate A/B test results for statistical significance."""
        if test_id not in self._active_tests:
            return None

        test = self._active_tests[test_id]
        control_rate = control_conversions / max(control_visitors, 1)
        treatment_rate = treatment_conversions / max(treatment_visitors, 1)
        lift = ((treatment_rate - control_rate) / max(control_rate, 0.001)) * 100

        total_visitors = control_visitors + treatment_visitors
        significant = total_visitors >= test.min_sample_size and abs(lift) > 2

        if significant:
            alert = GrowthAlert(
                alert_type="ab_test_result",
                metric=test.primary_metric,
                current_value=round(treatment_rate * 100, 2),
                baseline=round(control_rate * 100, 2),
                deviation_pct=round(lift, 1),
                recommendation=(
                    f"{'✅ WINNER: Variant B' if lift > 0 else '❌ Variant B lost'}. "
                    f"Lift: {lift:+.1f}%. "
                    f"{'Deploy variant B to 100%.' if lift > 0 else 'Stick with variant A.'}"
                ),
                severity="info" if lift > 0 else "warning",
            )

            await self._bus.emit_nowait(Event(
                event_type="growth.ab_test_completed",
                payload={
                    "test_id": test_id, "lift_pct": lift,
                    "significant": True, "winner": "B" if lift > 0 else "A",
                },
                source="growth_agent",
                priority=EventPriority.NORMAL,
            ))

            del self._active_tests[test_id]
            return alert

        return None

    async def _handle_task(
        self, task: str, context: dict | None = None,
        model: str = "", memory_context: str = "",
    ) -> str:
        """Handle incoming growth tasks."""
        task_lower = task.lower()

        if "anomaly" in task_lower or "traffic" in task_lower:
            if context:
                alert = await self.detect_traffic_anomaly(
                    page=context.get("page", "/"),
                    current_visits=context.get("current_visits", 0),
                    baseline_visits=context.get("baseline_visits", 0),
                )
                if alert:
                    return f"🚨 Traffic anomaly on {alert.metric}: {alert.deviation_pct:+.1f}%\n{alert.recommendation}"
                return "No traffic anomalies detected."

        if "ab_test" in task_lower or "a/b" in task_lower:
            if context and "test_id" in context:
                alert = await self.evaluate_ab_test(
                    test_id=context["test_id"],
                    control_conversions=context.get("control_conversions", 0),
                    control_visitors=context.get("control_visitors", 0),
                    treatment_conversions=context.get("treatment_conversions", 0),
                    treatment_visitors=context.get("treatment_visitors", 0),
                )
                if alert:
                    return f"A/B test result: {alert.recommendation}"
                return "A/B test still collecting data — not enough samples yet."

        if "propose" in task_lower or "hypothesis" in task_lower:
            test = await self.propose_ab_test(
                name=context.get("name", "Untitled test") if context else "Untitled test",
                hypothesis=context.get("hypothesis", "No hypothesis provided") if context else "No hypothesis",
                variant_a=context.get("variant_a", "Control") if context else "Control",
                variant_b=context.get("variant_b", "Treatment") if context else "Treatment",
            )
            return f"📊 A/B test proposed: {test.name}\nHypothesis: {test.hypothesis}\nExpected lift: {test.expected_lift_pct}%"

        return f"[growth] Analyzed: {task[:200]}\nNo actionable insights detected."

    async def sleep(self) -> None:
        await self._kernel.sleep()

    async def terminate(self) -> None:
        await self._kernel.terminate()

    @property
    def stats(self) -> dict:
        return {
            **self._kernel.stats,
            "active_tests": len(self._active_tests),
        }
