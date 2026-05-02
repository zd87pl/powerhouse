"""ChromaDB resolver."""
from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus

class ChromaDBResolver(Resolver):
    resource_key = "chromadb_collection"
    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        return {"exists": False, "collection": getattr(intent, "project", ""), "note": "stub"}
    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(resource_key=self.resource_key, status=ResourceStatus.SKIPPED,
                                     action_taken="stub — real setup requires running ChromaDB instance", drifts_found=drifts)
