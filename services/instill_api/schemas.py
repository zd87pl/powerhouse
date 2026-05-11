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
    intent_yaml: Optional[str] = None


class ReconciliationRunResponse(BaseModel):
    id: str
    project_id: str
    status: str
    dry_run: bool
    drifts_found: Any  # Dict or List — varies between real engine and simulated
    drifts_resolved: List[Any]
    resources_checked: List[Any]
    log: str
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Setup ──


class SetupProviderStatus(BaseModel):
    provider: str
    label: str
    required: bool
    status: str
    source: str
    has_key: bool
    required_env: List[str]
    missing_env: List[str]
    docs_url: str
    signup_url: Optional[str] = None
    referral_url: Optional[str] = None
    next_action: str


class SetupStatusResponse(BaseModel):
    ready: bool
    connected: int
    configured: int
    missing_required: int
    total: int
    providers: List[SetupProviderStatus]


class SetupValidationCheck(BaseModel):
    label: str
    status: str
    detail: str


class SetupValidationResponse(BaseModel):
    provider: str
    status: str
    source: str
    validated_at: datetime
    summary: str
    checks: List[SetupValidationCheck]
    account: Dict[str, Any] = Field(default_factory=dict)
    scopes: List[str] = Field(default_factory=list)
    next_action: str


# ── Project Runs ──


class ProjectRunResponse(BaseModel):
    id: str
    tenant_id: str
    project_id: str
    run_type: str
    status: str
    title: str
    summary: str
    log: str
    steps: List[Dict[str, Any]]
    run_metadata: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

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
    provider: str = Field(
        ...,
        pattern="^(github|vercel|flyio|sentry|supabase|openrouter|stripe)$",
    )
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


# ── Intent Parser ──


class ParseRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)


class ParseResponse(BaseModel):
    project: str
    stack: str
    market: str
    features: List[str]
    tools: List[str]
    explanation: str
    required_keys: List[str]


# ── Project Builder ──


class BuildRequest(BaseModel):
    project: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    stack: str = "nextjs"
    features: List[str] = []
    market: str = "global"


class BuildResponse(BaseModel):
    project: str
    deploy_url: str
    status: str  # "building" | "deployed" | "failed"
    message: str
