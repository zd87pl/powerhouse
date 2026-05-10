"""Fly.io resolver."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class FlyioResolver(Resolver):
    resource_key = "deploy_flyio"

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        return {"exists": False, "provider": "flyio", "note": "stub — no API call yet"}

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.CREATING,
            action_taken="stub — real deploy requires FLY_API_TOKEN",
            drifts_found=drifts,
        )
