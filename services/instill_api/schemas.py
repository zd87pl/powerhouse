"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Project ──

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    stack: str = "custom"
    intent_yaml: str = ""  # Raw .powerhouse.yml content


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    intent_yaml: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    stack: str
    status: str
    intent_yaml: str
    github_repo_url: str
    deploy_url: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


# ── Reconciliation ──

class ReconcileRequest(BaseModel):
    dry_run: bool = False


class ReconciliationRunResponse(BaseModel):
    id: str
    project_id: str
    status: str
    dry_run: bool
    drifts_found: List[Any]
    drifts_resolved: List[Any]
    resources_checked: List[Any]
    log: str
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agent ──

class AgentRunRequest(BaseModel):
    agent_type: str = Field(..., pattern="^(autofix|scaffold|swarm|research)$")
    input_spec: str = ""


class AgentRunResponse(BaseModel):
    id: str
    project_id: str
    agent_type: str
    status: str
    input_spec: str
    output: str
    pr_url: str
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── ApiKey ──

class ApiKeyCreate(BaseModel):
    provider: str = Field(..., pattern="^(github|vercel|flyio|sentry)$")
    key_name: str
    key_value: str  # Will be encrypted before storage


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    key_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Health ──

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"
