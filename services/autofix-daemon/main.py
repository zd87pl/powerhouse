"""
Autofix Daemon — Polls Sentry for new errors, diagnoses with LLM, opens GitHub PRs.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Configuration
SENTRY_AUTH_TOKEN = os.getenv("SENTRY_AUTH_TOKEN", "")
SENTRY_ORG = os.getenv("SENTRY_ORG", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
POLL_INTERVAL = int(os.getenv("AUTOFIX_POLL_INTERVAL", "60"))
ALERTS_DIR = Path("/data/powerhouse/observability-bridge/alerts")
ALERTS_DIR.mkdir(parents=True, exist_ok=True)

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


def diagnose(error_title: str, error_message: str) -> dict:
    """Use LLM to diagnose the error and propose a fix."""
    if not OPENROUTER_API_KEY:
        return {"diagnosis": "Skipped: no LLM API key configured", "patch": None}

    system_prompt = (
        "You are an expert software engineer. Analyze the error and produce:\n"
        "1. Root cause diagnosis (2-3 sentences)\n"
        "2. Proposed fix (code patch or specific change)\n"
        "3. File(s) likely affected\n\n"
        "Respond in JSON: {\"diagnosis\": \"...\", \"patch\": \"...\", \"files\": [\"...\"]}"
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
        return {"diagnosis": f"LLM error: {resp.status_code}", "patch": None}

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"diagnosis": f"Parse error: {e}", "patch": None}


def open_github_pr(repo: str, branch: str, title: str, body: str, patch: str) -> str | None:
    """Open a PR with the proposed fix."""
    if not GITHUB_TOKEN:
        return None

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Create branch
    base_resp = requests.get(
        f"https://api.github.com/repos/{repo}/git/refs/heads/main",
        headers=headers,
        timeout=30,
    )
    if base_resp.status_code != 200:
        return None

    sha = base_resp.json()["object"]["sha"]
    requests.post(
        f"https://api.github.com/repos/{repo}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch}", "sha": sha},
        timeout=30,
    )

    # Commit patch (simplified — real impl would use Git tree API)
    # ...

    # Create PR
    pr_resp = requests.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=headers,
        json={"title": title, "body": body, "head": branch, "base": "main"},
        timeout=30,
    )

    if pr_resp.status_code == 201:
        return pr_resp.json().get("html_url")
    return None


def process_alert(alert: dict):
    """Process a single alert through the autofix pipeline."""
    alert_id = alert.get("id", str(int(time.time())))
    existing = load_alert(alert_id)
    if existing.get("status") in ("resolved", "claimed"):
        return

    alert["status"] = "claimed"
    alert["claimed_by"] = "autofix-daemon"
    alert["updated_at"] = datetime.now(timezone.utc).isoformat()

    diagnosis = diagnose(alert.get("title", ""), alert.get("message", ""))
    alert["diagnosis"] = diagnosis.get("diagnosis", "")
    alert["patch"] = diagnosis.get("patch")

    # TODO: Open PR if patch is valid
    # pr_url = open_github_pr(...)
    # alert["pr_url"] = pr_url

    if "resolved" in diagnosis.get("diagnosis", "").lower():
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
        # Fetch from Sentry
        issues = fetch_sentry_issues()
        for issue in issues:
            alert = {
                "id": issue.get("id"),
                "source": "sentry",
                "project": issue.get("project", {}).get("slug"),
                "severity": "high" if issue.get("isUnhandled") else "medium",
                "title": issue.get("title"),
                "message": issue.get("culprit", ""),
                "status": "open",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            process_alert(alert)

        # Also process any manually dropped JSON files
        for f in ALERTS_DIR.glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("status") == "open":
                process_alert(data)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
