"""
Autofix Daemon — Polls Sentry for new errors, diagnoses with LLM, opens GitHub PRs.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Make the shared heuristic diagnosis engine importable when run as a script
# (services/autofix-daemon/ is not an installed package).
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Configuration
SENTRY_AUTH_TOKEN = os.getenv("SENTRY_AUTH_TOKEN", "")
SENTRY_ORG = os.getenv("SENTRY_ORG", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_BASE_BRANCH = os.getenv("GITHUB_BASE_BRANCH", "main")
# Repo ("owner/repo") to open autofix PRs against when an alert doesn't
# carry one. Without a repo the daemon diagnoses but never opens a PR.
AUTOFIX_DEFAULT_REPO = os.getenv("AUTOFIX_DEFAULT_REPO", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
POLL_INTERVAL = int(os.getenv("AUTOFIX_POLL_INTERVAL", "60"))
ALERTS_DIR = Path(
    os.getenv("AUTOFIX_ALERTS_DIR", "/data/powerhouse/observability-bridge/alerts")
)
try:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Don't crash on import when the data dir isn't writable (e.g. tests/CI).
    pass

GITHUB_API = "https://api.github.com"
LLM_API_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "anthropic/claude-sonnet-4"


def load_alert(alert_id: str) -> dict:
    path = ALERTS_DIR / f"{alert_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_alert(alert: dict):
    path = ALERTS_DIR / f"{alert['id']}.json"
    path.write_text(json.dumps(alert, indent=2), encoding="utf-8")


def fetch_sentry_issues() -> list[dict]:
    """Fetch unresolved issues from Sentry."""
    if not SENTRY_AUTH_TOKEN or not SENTRY_ORG:
        return []
    url = f"https://sentry.io/api/0/organizations/{SENTRY_ORG}/issues/"
    headers = {"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"}
    params = {"query": "is:unresolved", "limit": "10"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"Sentry fetch failed: {resp.status_code} {resp.text}")
        return []
    return resp.json()


def _heuristic_diagnosis(error_title: str, error_message: str) -> dict:
    """Offline fallback diagnosis using the shared heuristic engine.

    Produces a real root-cause read (no API key needed) so Sentry-sourced
    alerts get triaged instead of silently skipped. It does not propose code
    changes, so it never opens a PR on its own.
    """
    try:
        from services.instill_api.diagnosis import diagnose_error
    except Exception:
        return {
            "diagnosis": "Skipped: no LLM API key and heuristic engine unavailable",
            "files": [],
            "changes": [],
        }

    d = diagnose_error(
        title=error_title, message=error_message, stack_trace=error_message
    )
    text = f"{d.summary} {d.root_cause}"
    if d.suggested_fix:
        text += " Fix: " + "; ".join(d.suggested_fix)
    return {
        "diagnosis": text,
        "category": d.category,
        "severity": d.severity,
        "files": d.likely_files,
        "changes": [],
        "source": "heuristic",
    }


def diagnose(error_title: str, error_message: str) -> dict:
    """Diagnose an error: LLM when a key is configured, heuristic otherwise."""
    if not OPENROUTER_API_KEY:
        return _heuristic_diagnosis(error_title, error_message)

    system_prompt = (
        "You are an expert software engineer. Analyze the error and produce:\n"
        "1. Root cause diagnosis (2-3 sentences)\n"
        "2. File(s) likely affected\n"
        "3. The exact fix as full replacement file contents\n\n"
        "Respond in JSON with these keys: "
        '{"diagnosis": "...", "files": ["path/one.py"], '
        '"changes": [{"path": "path/one.py", "content": "<entire new file contents>"}]}. '
        'Only include "changes" entries you are confident about; use an empty list if unsure.'
    )

    user_prompt = f"Error title: {error_title}\n\nError message:\n{error_message}"

    resp = requests.post(
        LLM_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )

    if resp.status_code != 200:
        print(f"LLM error {resp.status_code}; falling back to heuristic diagnosis")
        return _heuristic_diagnosis(error_title, error_message)

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed.setdefault("source", "llm")
        return parsed
    except Exception as e:
        print(f"LLM parse error ({e}); falling back to heuristic diagnosis")
        return _heuristic_diagnosis(error_title, error_message)


def _gh_headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def commit_file_changes(
    repo: str,
    branch: str,
    parent_sha: str,
    changes: list[dict],
    message: str,
) -> str | None:
    """Commit full-file replacements onto a branch via the Git Data API.

    Builds a real commit (blob → tree → commit → ref) so the resulting PR
    actually contains the proposed fix instead of an empty diff. Returns the
    new commit SHA, or None if any step fails.
    """
    if not changes:
        return None

    headers = _gh_headers()

    # The new tree is layered on top of the parent commit's tree.
    parent_commit = requests.get(
        f"{GITHUB_API}/repos/{repo}/git/commits/{parent_sha}",
        headers=headers,
        timeout=30,
    )
    if parent_commit.status_code != 200:
        print(f"Could not read base commit: {parent_commit.status_code}")
        return None
    base_tree_sha = parent_commit.json()["tree"]["sha"]

    tree_entries: list[dict] = []
    for change in changes:
        path = change.get("path")
        content = change.get("content")
        if not path or content is None:
            continue
        blob_resp = requests.post(
            f"{GITHUB_API}/repos/{repo}/git/blobs",
            headers=headers,
            json={"content": content, "encoding": "utf-8"},
            timeout=30,
        )
        if blob_resp.status_code not in (200, 201):
            print(f"Blob creation failed for {path}: {blob_resp.status_code}")
            return None
        tree_entries.append(
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_resp.json()["sha"],
            }
        )

    if not tree_entries:
        return None

    tree_resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/git/trees",
        headers=headers,
        json={"base_tree": base_tree_sha, "tree": tree_entries},
        timeout=30,
    )
    if tree_resp.status_code not in (200, 201):
        print(f"Tree creation failed: {tree_resp.status_code}")
        return None

    commit_resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/git/commits",
        headers=headers,
        json={
            "message": message,
            "tree": tree_resp.json()["sha"],
            "parents": [parent_sha],
        },
        timeout=30,
    )
    if commit_resp.status_code not in (200, 201):
        print(f"Commit creation failed: {commit_resp.status_code}")
        return None
    new_commit_sha = commit_resp.json()["sha"]

    ref_resp = requests.patch(
        f"{GITHUB_API}/repos/{repo}/git/refs/heads/{branch}",
        headers=headers,
        json={"sha": new_commit_sha, "force": False},
        timeout=30,
    )
    if ref_resp.status_code not in (200, 201):
        print(f"Ref update failed: {ref_resp.status_code}")
        return None

    return new_commit_sha


def open_github_pr(
    repo: str,
    branch: str,
    title: str,
    body: str,
    changes: list[dict],
    base: str = GITHUB_BASE_BRANCH,
) -> str | None:
    """Create a branch, commit the proposed changes, and open a PR.

    Returns the PR URL, or None if there's nothing to commit or a step fails.
    """
    if not GITHUB_TOKEN or not changes:
        return None

    headers = _gh_headers()

    base_resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/git/refs/heads/{base}",
        headers=headers,
        timeout=30,
    )
    if base_resp.status_code != 200:
        return None
    base_sha = base_resp.json()["object"]["sha"]

    branch_resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        timeout=30,
    )
    if branch_resp.status_code not in (200, 201):
        print(f"Branch creation failed: {branch_resp.status_code} {branch_resp.text}")
        return None

    commit_sha = commit_file_changes(
        repo, branch, base_sha, changes, f"autofix: {title}"
    )
    if not commit_sha:
        return None

    pr_resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/pulls",
        headers=headers,
        json={"title": title, "body": body, "head": branch, "base": base},
        timeout=30,
    )
    if pr_resp.status_code == 201:
        return pr_resp.json().get("html_url")
    print(f"PR creation failed: {pr_resp.status_code} {pr_resp.text}")
    return None


def process_alert(alert: dict):
    """Process a single alert through the autofix pipeline."""
    alert_id = alert.get("id") or str(int(time.time()))
    alert["id"] = alert_id
    existing = load_alert(alert_id)
    if existing.get("status") in ("resolved", "claimed"):
        return

    alert["status"] = "claimed"
    alert["claimed_by"] = "autofix-daemon"
    alert["updated_at"] = datetime.now(timezone.utc).isoformat()

    diagnosis = diagnose(alert.get("title", ""), alert.get("message", ""))
    alert["diagnosis"] = diagnosis.get("diagnosis", "")
    alert["files"] = diagnosis.get("files", [])

    # Open a PR with the proposed change when we have a target repo and a
    # confident, structured fix. Without both we record the diagnosis only.
    changes = diagnosis.get("changes") or []
    repo = alert.get("repo") or AUTOFIX_DEFAULT_REPO
    if repo and changes and GITHUB_TOKEN:
        branch = f"autofix/{alert_id}"
        title = alert.get("title", "Autofix") or "Autofix"
        body = (
            f"## Autofix proposal\n\n{alert.get('diagnosis', '')}\n\n"
            f"Files: {', '.join(diagnosis.get('files', []))}\n\n"
            "_Opened automatically by the Powerhouse autofix daemon. Review before merging._"
        )
        pr_url = open_github_pr(repo, branch, title, body, changes)
        if pr_url:
            alert["pr_url"] = pr_url
            alert["status"] = "pr_opened"

    diag_lower = diagnosis.get("diagnosis", "").lower()
    if diag_lower.startswith("resolved") or " status: resolved" in diag_lower:
        alert["status"] = "resolved"

    save_alert(alert)
    print(f"Processed alert {alert_id}: {alert['status']}")


def main():
    print("🔧 Autofix Daemon started")
    print(f"   Poll interval: {POLL_INTERVAL}s")
    print(f"   Alerts dir: {ALERTS_DIR}")

    if not SENTRY_AUTH_TOKEN:
        print("⚠️  SENTRY_AUTH_TOKEN not set — will only process manual alerts")
    if not OPENROUTER_API_KEY:
        print("⚠️  OPENROUTER_API_KEY not set — diagnosis will be skipped")

    while True:
        try:
            # Fetch from Sentry
            issues = fetch_sentry_issues()
            for issue in issues:
                alert = {
                    "id": issue.get("id"),
                    "source": "sentry",
                    "project": issue.get("project", {}).get("slug")
                    if isinstance(issue.get("project"), dict)
                    else None,
                    "repo": AUTOFIX_DEFAULT_REPO,
                    "severity": "high" if issue.get("isUnhandled") else "medium",
                    "title": issue.get("title"),
                    "message": issue.get("culprit", ""),
                    "status": "open",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                process_alert(alert)

            # Also process any manually dropped JSON files
            for f in ALERTS_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    if data.get("status") == "open":
                        process_alert(data)
                except json.JSONDecodeError as e:
                    print(f"Skipping malformed alert file {f.name}: {e}")
        except Exception as e:
            print(f"Error in main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
