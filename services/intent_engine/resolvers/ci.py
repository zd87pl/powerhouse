"""CI Pipeline resolver."""

from pathlib import Path
from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus


class CIPipelineResolver(Resolver):
    resource_key = "ci_pipeline"

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        source_path = getattr(intent, "source_path", None)
        if source_path:
            workflow = Path(source_path).parent / ".github" / "workflows" / "ci.yml"
            exists = workflow.exists()
        else:
            exists = False
        return {
            "exists": exists,
            "runner": "github_actions",
            "lint": True,
            "typecheck": True,
            "test": True,
            "secrets_scan": True,
            "path": str(workflow) if source_path else "",
        }

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.SKIPPED,
            action_taken="CI workflow creation is not implemented by reconcile yet",
            drifts_found=drifts,
        )
