"""Intent Engine — main discovery and reconciliation loop."""

from __future__ import annotations

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .reconciler import reconcile, reconcile_summary
from .resolvers import ReconciliationResult
from .schema import IntentFile, discover_intents, load_intent

DEFAULT_STATE_DIR = Path(tempfile.gettempdir()) / "intent-engine" / "state"


class RunRecord:
    def __init__(self, project: str, dry_run: bool):
        self.project = project
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.dry_run = dry_run
        self.results: List[ReconciliationResult] = []
        self.summary: Dict = {}
        self.error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "project": self.project,
            "started_at": self.started_at,
            "dry_run": self.dry_run,
            "results": [
                {
                    "resource_key": r.resource_key,
                    "status": r.status.value,
                    "action_taken": r.action_taken,
                    "drifts_found": len(r.drifts_found),
                    "drifts_resolved": r.drifts_resolved,
                    "error_message": r.error_message,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
            "summary": self.summary,
            "error": self.error,
        }


class IntentEngine:
    def __init__(
        self,
        root: Optional[Path] = None,
        state_dir: Optional[Path] = None,
        dry_run: bool = False,
    ):
        self.root = root or Path.cwd()
        self.state_dir = state_dir or DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.dry_run = dry_run
        self._on_reconcile: List[
            Callable[[IntentFile, List[ReconciliationResult]], None]
        ] = []

    def on_reconcile(
        self, callback: Callable[[IntentFile, List[ReconciliationResult]], None]
    ) -> None:
        self._on_reconcile.append(callback)

    def discover(self) -> List[Path]:
        return discover_intents(self.root)

    def reconcile_all(self) -> Dict[str, RunRecord]:
        records: Dict[str, RunRecord] = {}
        paths = self.discover()
        for path in paths:
            try:
                intent = load_intent(path)
            except Exception as e:
                record = RunRecord(project=path.parent.name, dry_run=self.dry_run)
                record.error = f"parse error: {e}"
                records[path.parent.name] = record
                continue
            record = RunRecord(project=intent.project, dry_run=self.dry_run)
            try:
                record.results = reconcile(intent, dry_run=self.dry_run)
                record.summary = reconcile_summary(record.results)
            except Exception as e:
                record.error = f"reconciliation error: {e}"
            records[intent.project] = record
            self._save_record(record)
            for cb in self._on_reconcile:
                cb(intent, record.results)
        return records

    def reconcile_one(self, path: Path) -> RunRecord:
        intent = load_intent(path)
        record = RunRecord(project=intent.project, dry_run=self.dry_run)
        try:
            record.results = reconcile(intent, dry_run=self.dry_run)
            record.summary = reconcile_summary(record.results)
        except Exception as e:
            record.error = f"reconciliation error: {e}"
        self._save_record(record)
        for cb in self._on_reconcile:
            cb(intent, record.results)
        return record

    def status(self, project: Optional[str] = None) -> Dict:
        results: Dict = {}
        pattern = f"{project}-*.json" if project else "*.json"
        for f in sorted(self.state_dir.glob(pattern)):
            data = json.loads(f.read_text(encoding="utf-8"))
            results[data.get("project", f.stem)] = data
        return results

    def watch(self, interval_seconds: float = 30.0) -> None:
        known: Dict[str, float] = {}
        while True:
            paths = self.discover()
            for p in paths:
                mtime = p.stat().st_mtime
                if known.get(str(p)) != mtime:
                    known[str(p)] = mtime
                    self.reconcile_one(p)
            time.sleep(interval_seconds)

    def _save_record(self, record: RunRecord) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        fname = self.state_dir / f"{record.project}-{ts}.json"
        fname.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
