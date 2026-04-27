"""
Observability Bridge — FastAPI webhook relay for Sentry, custom alerts, and metrics.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request

app = FastAPI(title="Powerhouse Observability Bridge")

ALERTS_DIR = Path("/data/powerhouse/observability-bridge/alerts")
ALERTS_DIR.mkdir(parents=True, exist_ok=True)


def save_alert(alert: dict) -> Path:
    alert_id = alert.get("id", f"{int(datetime.now().timestamp())}")
    path = ALERTS_DIR / f"{alert_id}.json"
    path.write_text(json.dumps(alert, indent=2), encoding="utf-8")
    return path


@app.post("/webhook/sentry")
async def sentry_webhook(request: Request):
    """Receive Sentry webhook events."""
    payload = await request.json()
    alert_id = payload.get("id") or f"sentry-{int(datetime.now().timestamp())}"
    alert = {
        "id": alert_id,
        "source": "sentry",
        "project": payload.get("project", "unknown"),
        "severity": payload.get("level", "error") or "error",
        "title": payload.get("title", "Unknown error"),
        "message": payload.get("message", ""),
        "error_type": payload.get("type"),
        "stack_trace": payload.get("stacktrace", {}).get("raw", "")
        if isinstance(payload.get("stacktrace"), dict)
        else "",
        "url": payload.get("url"),
        "raw_payload": payload,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = save_alert(alert)
    return {"ok": True, "alert_id": alert["id"], "saved_to": str(path)}


@app.post("/webhook/custom")
async def custom_alert(request: Request):
    """Receive custom alerts from any source."""
    payload = await request.json()
    alert_id = payload.get("id") or f"custom-{int(datetime.now().timestamp())}"
    alert = {
        "id": alert_id,
        "source": "custom",
        "project": payload.get("project", "unknown"),
        "severity": payload.get("severity", "medium") or "medium",
        "title": payload.get("title", "Custom alert"),
        "message": payload.get("message", ""),
        "error_type": None,
        "stack_trace": None,
        "file_path": payload.get("file"),
        "line_no": payload.get("line"),
        "url": payload.get("url"),
        "raw_payload": payload,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = save_alert(alert)
    return {"ok": True, "alert_id": alert["id"], "saved_to": str(path)}


@app.get("/alerts")
def list_alerts(status: str | None = None):
    """List all alerts, optionally filtered by status."""
    alerts = []
    for f in ALERTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if status is None or data.get("status") == status:
                alerts.append(data)
        except json.JSONDecodeError:
            continue  # skip malformed files
    return {"alerts": alerts, "count": len(alerts)}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
