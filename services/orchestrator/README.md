# Multi-Agent Swarm Orchestrator

## Roles

| Role | Prompt File | Responsibility |
|------|-------------|---------------|
| Architect | `prompts.py::ARCHITECT_SYSTEM` | Analyze request, produce technical spec |
| Coder | `prompts.py::CODER_SYSTEM` | Implement code from spec |
| Reviewer | `prompts.py::REVIEWER_SYSTEM` | Validate code against spec |

## Workflow

```
User Request
    ↓
Architect → spec.json + file plan
    ↓
Coder → implementation code + tests
    ↓
Reviewer → verdict: PASS or REVISE
    ↓ (REVISE)
Coder → revised code (max 3 iterations)
    ↓ (PASS)
GitHub PR → CI/CD → Deploy
```

## State Persistence

`state.py::SwarmRun` stores all intermediate outputs in `/data/powerhouse/orchestrator/runs/`.
Each run is a JSON file tracking status, agent outputs, and logs.

## Usage

```python
from services.orchestrator.state import SwarmRun

run = SwarmRun(task_id="feat-auth-001", spec="Add OAuth2 login", project="my-app")
run.log("orchestrator", "Starting swarm workflow")
run.status = "architect"
run.architect_output = "...spec..."
run._save()
```
