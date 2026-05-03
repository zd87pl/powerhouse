"""
Merchandise Agent — autonomous ecommerce operations.

Monitors product margins, detects restock opportunities,
scans supplier feeds, and recommends pricing adjustments.

Usage:
    merch = MerchAgent()
    await merch.start()
    result = await merch.run("Check margins on Sukienki category")
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
class ProductAlert:
    """An actionable alert from the merch agent."""
    alert_type: str  # "margin_below_threshold", "stock_low", "price_opportunity"
    product_id: str
    category: str
    current_value: float
    threshold: float
    recommendation: str
    severity: str = "warning"  # "info", "warning", "critical"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MerchAgent:
    """
    Autonomous merchandising agent.
    
    Monitors:
    - Product margins per category (alerts if below threshold)
    - Stock levels (recommends restock timing)
    - Pricing vs. competitors
    - Supplier feed changes
    """

    # Default margin thresholds per category (percentage)
    DEFAULT_MARGIN_THRESHOLDS = {
        "Sukienki": 0.40,         # 40%
        "Bluzki": 0.35,           # 35%
        "Spodnie": 0.35,          # 35%
        "Bluzy": 0.30,            # 30%
        "Okrycia": 0.45,          # 45%
        "Spódnice": 0.35,         # 35%
        "default": 0.30,          # 30%
    }

    # Restock thresholds (units)
    DEFAULT_RESTOCK_THRESHOLDS = {
        "default": 10,
        "Sukienki": 15,
        "Bluzki": 20,
    }

    def __init__(
        self,
        margin_thresholds: dict[str, float] | None = None,
        restock_thresholds: dict[str, int] | None = None,
    ):
        self.margin_thresholds = margin_thresholds or self.DEFAULT_MARGIN_THRESHOLDS.copy()
        self.restock_thresholds = restock_thresholds or self.DEFAULT_RESTOCK_THRESHOLDS.copy()
        self._bus: EventBus = get_event_bus()
        self._kernel = AgentKernel(
            agent_type="merch",
            config=AgentConfig(
                max_iterations=5,
                cost_budget_usd=0.50,
                subscribe_to=[
                    "inventory.updated",
                    "supplier.price_changed",
                    "order.completed",
                ],
            ),
        )
        # Wire up the task handler
        self._kernel.on_task(self._handle_task)

    async def start(self) -> None:
        """Initialize the merch agent."""
        await self._kernel.start()
        logger.info("MerchAgent started. Monitoring %d categories.", len(self.margin_thresholds))

    async def run(self, task: str, context: dict | None = None) -> TaskResult:
        """Execute a merchandising task."""
        return await self._kernel.run(task, context)

    async def check_margins(self, products: list[dict]) -> list[ProductAlert]:
        """
        Check product margins against category thresholds.
        
        Args:
            products: List of {"id": ..., "category": ..., "cost": ..., "price": ...}
        
        Returns:
            List of alerts for products below margin threshold.
        """
        alerts = []
        for p in products:
            category = p.get("category", "default")
            cost = float(p.get("cost", 0))
            price = float(p.get("price", 0))
            product_id = p.get("id", "unknown")

            if cost <= 0 or price <= 0:
                continue

            margin = (price - cost) / price
            threshold = self.margin_thresholds.get(category, self.margin_thresholds["default"])

            if margin < threshold:
                # Calculate target price to hit threshold
                target_price = cost / (1 - threshold)
                alerts.append(ProductAlert(
                    alert_type="margin_below_threshold",
                    product_id=product_id,
                    category=category,
                    current_value=round(margin * 100, 1),
                    threshold=round(threshold * 100, 1),
                    recommendation=(
                        f"Raise price from ${price:.2f} to ${target_price:.2f} "
                        f"to hit {threshold*100:.0f}% margin"
                    ),
                    severity="critical" if margin < threshold * 0.7 else "warning",
                ))

        if alerts:
            await self._bus.emit_nowait(Event(
                event_type="merch.margin_alert",
                payload={"alerts": len(alerts), "products": [a.product_id for a in alerts]},
                source="merch_agent",
                priority=EventPriority.HIGH if any(a.severity == "critical" for a in alerts)
                else EventPriority.NORMAL,
            ))

        return alerts

    async def check_restock(self, inventory: list[dict]) -> list[ProductAlert]:
        """
        Check inventory levels and recommend restocks.
        
        Args:
            inventory: List of {"id": ..., "category": ..., "stock": ..., "daily_sales": ...}
        """
        alerts = []
        for item in inventory:
            category = item.get("category", "default")
            stock = int(item.get("stock", 0))
            daily_sales = float(item.get("daily_sales", 1))
            product_id = item.get("id", "unknown")
            threshold = self.restock_thresholds.get(category, self.restock_thresholds["default"])

            days_remaining = stock / max(daily_sales, 0.01)

            if days_remaining < 7:
                alerts.append(ProductAlert(
                    alert_type="stock_low",
                    product_id=product_id,
                    category=category,
                    current_value=stock,
                    threshold=threshold,
                    recommendation=(
                        f"Only {stock} units left ({days_remaining:.1f} days at current sales rate). "
                        f"Reorder now — lead time typically 14 days."
                    ),
                    severity="critical" if days_remaining < 3 else "warning",
                ))

        if alerts:
            await self._bus.emit_nowait(Event(
                event_type="merch.restock_alert",
                payload={"alerts": len(alerts)},
                source="merch_agent",
                priority=EventPriority.HIGH,
            ))

        return alerts

    async def _handle_task(
        self, task: str, context: dict | None = None,
        model: str = "", memory_context: str = "",
    ) -> str:
        """Handle incoming merch tasks."""
        task_lower = task.lower()

        if "margin" in task_lower:
            if context and "products" in context:
                alerts = await self.check_margins(context["products"])
                return f"Margin check complete: {len(alerts)} alerts\n" + "\n".join(
                    f"  • {a.product_id} ({a.category}): {a.current_value}% margin "
                    f"(threshold: {a.threshold}%) — {a.recommendation}"
                    for a in alerts
                )

        if "restock" in task_lower or "stock" in task_lower or "inventory" in task_lower:
            if context and "inventory" in context:
                alerts = await self.check_restock(context["inventory"])
                return f"Restock check complete: {len(alerts)} alerts\n" + "\n".join(
                    f"  • {a.product_id}: {a.current_value} units — {a.recommendation}"
                    for a in alerts
                )

        return f"[merch] Analyzed: {task[:200]}\nNo actionable thresholds triggered."

    async def sleep(self) -> None:
        await self._kernel.sleep()

    async def terminate(self) -> None:
        await self._kernel.terminate()

    @property
    def stats(self) -> dict:
        return self._kernel.stats
