"""CI Pipeline resolver."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class CIPipelineResolver(Resolver):
    resource_key = "ci_pipeline"

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        return {
            "exists": False,
            "runner": "github_actions",
            "lint": True,
            "typecheck": True,
            "test": True,
            "secrets_scan": True,
            "note": "stub — verifies by checking if .github/workflows/ci.yml exists",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="stub — CI scaffolding uses project-scaffold skill",
            drifts_found=drifts,
        )
