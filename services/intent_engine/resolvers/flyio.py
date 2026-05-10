"""Fly.io resolver."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class FlyioResolver(Resolver):
    resource_key = "deploy_flyio"

    def __init__(self, token: str = ""):
        self.token = token

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        if not self.token:
            return {
                "exists": False,
                "provider": "flyio",
                "reason": "FLY_API_TOKEN not configured",
            }
        return {
            "exists": False,
            "provider": "flyio",
            "note": "Fly API check not implemented",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        if not self.token:
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.SKIPPED,
                action_taken="Fly.io reconciliation skipped: configure FLY_API_TOKEN",
                drifts_found=drifts,
            )
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="Fly.io reconciliation is not implemented yet",
            drifts_found=drifts,
        )
