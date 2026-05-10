"""Sentry resolver."""

import os
from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class SentryResolver(Resolver):
    resource_key = "sentry_project"

    def __init__(self, token: str = "", org: str = ""):
        self.token = token or os.getenv("SENTRY_AUTH_TOKEN", "")
        self.org = org or os.getenv("SENTRY_ORG", "")

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        if not self.token or not self.org:
            return {
                "exists": False,
                "project": getattr(intent, "project", ""),
                "reason": "SENTRY_AUTH_TOKEN/SENTRY_ORG not configured",
            }
        return {
            "exists": False,
            "project": getattr(intent, "project", ""),
            "note": "Sentry API check not implemented",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        if not self.token or not self.org:
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.SKIPPED,
                action_taken="Sentry reconciliation skipped: configure SENTRY_AUTH_TOKEN and SENTRY_ORG",
                drifts_found=drifts,
            )
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="Sentry reconciliation is not implemented yet",
            drifts_found=drifts,
        )
