"""Instill API — FastAPI backend for the Powerhouse SaaS."""

import os
import traceback
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import get_session, DATABASE_URL
from .models import (
    AgentRun,
    ApiKey,
    Project,
    ReconciliationRun,
    Tenant,
    gen_id,
)
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    HealthResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ReconcileRequest,
    ReconciliationRunResponse,
)

app = FastAPI(
    title="Instill API",
    description="Backend API for the Instill autonomous AI engineering harness",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth helper (stub — Clerk middleware replaces this) ──

async def get_current_tenant(
    session: Session = Depends(get_session),
) -> Tenant:
    """Stub auth: returns first tenant. Replace with Clerk JWT validation."""
    tenant = session.query(Tenant).first()
    if tenant is None:
        # Auto-create dev tenant
        tenant = Tenant(
            id=gen_id(),
            name="Dev Tenant",
            email="dev@instill.dev",
            clerk_id="dev_user",
        )
        session.add(tenant)
        session.commit()
    return tenant


# ── Health ──

@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


# ── Projects ──

@app.get("/api/projects", response_model=ProjectListResponse)
async def list_projects(
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    projects = session.query(Project).filter(Project.tenant_id == tenant.id).all()
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects),
    )


@app.post("/api/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = Project(
        id=gen_id(),
        tenant_id=tenant.id,
        name=data.name,
        description=data.description,
        stack=data.stack,
        intent_yaml=data.intent_yaml,
        status="pending",
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return ProjectResponse.model_validate(project)


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = session.query(Project).filter(
        Project.id == project_id, Project.tenant_id == tenant.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@app.patch("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = session.query(Project).filter(
        Project.id == project_id, Project.tenant_id == tenant.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.intent_yaml is not None:
        project.intent_yaml = data.intent_yaml
    project.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(project)
    return ProjectResponse.model_validate(project)


@app.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = session.query(Project).filter(
        Project.id == project_id, Project.tenant_id == tenant.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    session.delete(project)
    session.commit()


# ── Reconciliation ──

@app.post("/api/projects/{project_id}/reconcile", response_model=ReconciliationRunResponse)
async def reconcile_project(
    project_id: str,
    data: ReconcileRequest = ReconcileRequest(),
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = session.query(Project).filter(
        Project.id == project_id, Project.tenant_id == tenant.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "reconciling"
    run = ReconciliationRun(
        id=gen_id(),
        project_id=project.id,
        status="running",
        dry_run=data.dry_run,
    )
    session.add(run)
    session.commit()

    # Trigger actual reconciliation
    try:
        results, summary = _run_reconciliation(project.intent_yaml, data.dry_run)
        run.status = "synced" if summary["healthy"] else "drifted"
        run.drifts_found = summary.get("by_status", {})
        run.resources_checked = [r["resource_key"] for r in results]
        run.log = str(results)
        project.status = run.status
        project.updated_at = datetime.now(timezone.utc)
    except Exception as e:
        run.status = "error"
        run.error_message = str(e)
        run.log = traceback.format_exc()
        project.status = "error"
        project.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(run)
    return ReconciliationRunResponse.model_validate(run)


@app.get("/api/projects/{project_id}/reconciliations", response_model=List[ReconciliationRunResponse])
async def list_reconciliations(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(default=20, le=100),
):
    runs = (
        session.query(ReconciliationRun)
        .filter(ReconciliationRun.project_id == project_id)
        .order_by(ReconciliationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [ReconciliationRunResponse.model_validate(r) for r in runs]


# ── Agents ──

@app.post("/api/projects/{project_id}/agents", response_model=AgentRunResponse, status_code=201)
async def trigger_agent(
    project_id: str,
    data: AgentRunRequest,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = session.query(Project).filter(
        Project.id == project_id, Project.tenant_id == tenant.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = AgentRun(
        id=gen_id(),
        project_id=project.id,
        agent_type=data.agent_type,
        status="running",
        input_spec=data.input_spec,
    )
    session.add(run)
    session.commit()

    # Trigger agent (stub — replace with actual agent dispatch)
    try:
        output = _run_agent(data.agent_type, data.input_spec, project.intent_yaml)
        run.status = "completed"
        run.output = output
        run.completed_at = datetime.now(timezone.utc)
    except Exception as e:
        run.status = "failed"
        run.log = traceback.format_exc()
        run.completed_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(run)
    return AgentRunResponse.model_validate(run)


@app.get("/api/projects/{project_id}/agents", response_model=List[AgentRunResponse])
async def list_agent_runs(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(default=20, le=100),
):
    runs = (
        session.query(AgentRun)
        .filter(AgentRun.project_id == project_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [AgentRunResponse.model_validate(r) for r in runs]


# ── API Keys ──

@app.get("/api/keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    keys = session.query(ApiKey).filter(ApiKey.tenant_id == tenant.id).all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


@app.post("/api/keys", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    # TODO: encrypt key_value with Fernet before storage
    key = ApiKey(
        id=gen_id(),
        tenant_id=tenant.id,
        provider=data.provider,
        key_name=data.key_name,
        encrypted_value=data.key_value,  # TODO: encrypt
    )
    session.add(key)
    session.commit()
    session.refresh(key)
    return ApiKeyResponse.model_validate(key)


@app.delete("/api/keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    key = session.query(ApiKey).filter(
        ApiKey.id == key_id, ApiKey.tenant_id == tenant.id
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    session.delete(key)
    session.commit()


# ── Internal: reconciliation logic ──

def _run_reconciliation(intent_yaml: str, dry_run: bool = False):
    """Run the intent engine on a .powerhouse.yml string."""
    import sys, os
    # Use the app's base directory (works both locally and on Fly)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    from services.intent_engine.schema import IntentFile
    from services.intent_engine.reconciler import reconcile, reconcile_summary

    import yaml
    data = yaml.safe_load(intent_yaml) if intent_yaml else {}
    intent = IntentFile.from_dict(data)
    results = reconcile(intent, dry_run=dry_run)
    summary = reconcile_summary(results)

    # Convert to dicts for JSON serialization
    results_dict = [
        {
            "resource_key": r.resource_key,
            "status": r.status.value,
            "action_taken": r.action_taken,
            "drifts_found": len(r.drifts_found),
            "drifts_resolved": r.drifts_resolved,
            "error_message": r.error_message,
            "duration_ms": r.duration_ms,
        }
        for r in results
    ]
    return results_dict, summary


def _run_agent(agent_type: str, input_spec: str, intent_yaml: str = "") -> str:
    """Stub agent dispatch. Replace with actual Hermes agent calls."""
    return f"[stub] {agent_type} agent dispatched with spec: {input_spec[:200]}"


# ── Startup ──

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    from .models import init_db
    init_db(DATABASE_URL)
    print(f"Database initialized: {DATABASE_URL}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
