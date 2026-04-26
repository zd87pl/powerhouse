"""Track multi-agent swarm workflow state."""
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

STATE_DIR = Path("/data/powerhouse/orchestrator/runs")
STATE_DIR.mkdir(parents=True, exist_ok=True)


class SwarmRun:
    """Persistent state for one swarm execution."""

    STATUSES = ["pending", "architect", "coding", "review", "revising", "done", "failed"]

    def __init__(self, task_id: str, spec: str, project: str):
        self.task_id = task_id
        self.project = project
        self.spec = spec
        self.status = "pending"
        self.architect_output: Optional[str] = None
        self.coder_output: Optional[str] = None
        self.review_output: Optional[str] = None
        self.review_passed = False
        self.iteration = 0
        self.max_iterations = 3
        self.logs: List[Dict] = []
        self._path = STATE_DIR / f"{task_id}.json"

    def log(self, agent: str, message: str):
        entry = {"time": time.time(), "agent": agent, "message": message}
        self.logs.append(entry)
        self._save()

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "project": self.project,
            "spec": self.spec,
            "status": self.status,
            "architect_output": self.architect_output,
            "coder_output": self.coder_output,
            "review_output": self.review_output,
            "review_passed": self.review_passed,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "logs": self.logs,
        }

    def _save(self):
        self._path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, task_id: str):
        path = STATE_DIR / f"{task_id}.json"
        if not path.exists():
            raise FileNotFoundError(task_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        run = cls(data["task_id"], data["spec"], data["project"])
        for k, v in data.items():
            if hasattr(run, k):
                setattr(run, k, v)
        return run

    @classmethod
    def list_runs(cls):
        return sorted(STATE_DIR.glob("*.json"))
