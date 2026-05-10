"""Sentry resolver."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class SentryResolver(Resolver):
    resource_key = "sentry_project"

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        return {
            "exists": False,
            "project": getattr(intent, "project", ""),
            "note": "stub",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="stub — real setup requires SENTRY_AUTH_TOKEN",
            drifts_found=drifts,
        )
