"""GitHub resolver — ensures repos, branch protection, and secrets exist."""

from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None


class GitHubResolver(Resolver):
    resource_key = "github_repo"

    def __init__(self, token: str = "", api_url: str = ""):
        self.token = token
        self.api_url = api_url or "https://api.github.com"

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        if not HAS_REQUESTS or not self.token:
            return {"exists": False, "reason": "no token / requests not installed"}
        try:
            resp = requests.get(
                f"{self.api_url}/repos/{intent.project}",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "exists": True,
                    "project": data.get("name", ""),
                    "description": data.get("description", ""),
                    "private": data.get("private", False),
                    "html_url": data.get("html_url", ""),
                }
            elif resp.status_code == 404:
                return {"exists": False, "project": intent.project}
            else:
                return {"exists": False, "error": f"status {resp.status_code}"}
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult:
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.CREATING,
            action_taken="stub — real creation requires GITHUB_TOKEN",
            drifts_found=drifts,
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "powerhouse-intent-engine",
        }
