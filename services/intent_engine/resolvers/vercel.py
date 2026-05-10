"""Vercel resolver."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None  # type: ignore[assignment]


class VercelResolver(Resolver):
    resource_key = "deploy_vercel"

    def __init__(self, token: str = ""):
        self.token = token

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        if not HAS_REQUESTS or not self.token:
            return {
                "exists": False,
                "provider": "vercel",
                "reason": "VERCEL_TOKEN not configured",
            }
        resp = requests.get(
            f"https://api.vercel.com/v9/projects/{intent.project}",
            headers=self._headers(),
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "exists": True,
                "provider": "vercel",
                "name": data.get("name", ""),
            }
        if resp.status_code == 404:
            return {"exists": False, "provider": "vercel"}
        return {
            "exists": False,
            "provider": "vercel",
            "error": f"status {resp.status_code}",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        if not HAS_REQUESTS or not self.token:
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.SKIPPED,
                action_taken="Vercel reconciliation skipped: configure VERCEL_TOKEN",
                drifts_found=drifts,
            )
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="Vercel project creation is handled by the build pipeline, not reconcile",
            drifts_found=drifts,
        )

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
