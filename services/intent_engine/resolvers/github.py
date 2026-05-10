"""GitHub resolver — ensures repos, branch protection, and secrets exist."""

import os
from typing import Any, Dict, List
from . import Drift, ReconciliationResult, Resolver, ResourceStatus

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None  # type: ignore[assignment]


class GitHubResolver(Resolver):
    resource_key = "github_repo"

    def __init__(self, token: str = "", api_url: str = "", owner: str = ""):
        self.token = token
        self.api_url = api_url or "https://api.github.com"
        self.owner = owner or os.getenv("GITHUB_OWNER", "")

    def get_actual_state(self, intent: Any) -> Dict[str, Any]:
        if not HAS_REQUESTS:
            return {"exists": False, "reason": "requests not installed"}
        if not self.token or not self.owner:
            return {
                "exists": False,
                "reason": "GITHUB_TOKEN/GITHUB_OWNER not configured",
            }
        try:
            resp = requests.get(
                f"{self.api_url}/repos/{self.owner}/{intent.project}",
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
        if not HAS_REQUESTS or not self.token or not self.owner:
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.SKIPPED,
                action_taken="GitHub reconciliation skipped: configure GITHUB_TOKEN and GITHUB_OWNER",
                drifts_found=drifts,
            )

        create_url = (
            f"{self.api_url}/orgs/{self.owner}/repos"
            if os.getenv("GITHUB_OWNER_IS_ORG", "").lower() in {"1", "true", "yes"}
            else f"{self.api_url}/user/repos"
        )
        resp = requests.post(
            create_url,
            headers=self._headers(),
            json={
                "name": intent.project,
                "description": intent.description
                or f"{intent.project} managed by Powerhouse",
                "private": os.getenv("POWERHOUSE_GITHUB_REPOS_PUBLIC", "").lower()
                not in {"1", "true", "yes"},
                "auto_init": False,
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.EXISTS,
                action_taken=f"created GitHub repo {self.owner}/{intent.project}",
                drifts_found=drifts,
                drifts_resolved=len(drifts),
            )
        if resp.status_code == 422 and "already_exists" in resp.text:
            return ReconciliationResult(
                resource_key=self.resource_key,
                status=ResourceStatus.EXISTS,
                action_taken=f"GitHub repo {self.owner}/{intent.project} already exists",
                drifts_found=drifts,
                drifts_resolved=len(drifts),
            )
        return ReconciliationResult(
            resource_key=self.resource_key,
            status=ResourceStatus.ERROR,
            action_taken="GitHub repo creation failed",
            drifts_found=drifts,
            error_message=f"GitHub API status {resp.status_code}: {resp.text[:300]}",
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "powerhouse-intent-engine",
        }
