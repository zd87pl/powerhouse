"""Instill API — FastAPI backend for the Powerhouse SaaS."""

import os
import traceback
import httpx
import jwt
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
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
    ParseRequest,
    ParseResponse,
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

# ── Clerk JWT Validation ──

CLERK_JWKS_URL = "https://api.clerk.com/v1/jwks"
_jwks_client: Optional[jwt.PyJWKClient] = None


def _get_jwks_client() -> jwt.PyJWKClient:
    """Lazy-init singleton JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(CLERK_JWKS_URL)
    return _jwks_client


async def get_clerk_user_id(request: Request) -> Optional[str]:
    """Extract Clerk user ID from JWT in Authorization header.
    
    Returns None if no auth header present (dev fallback).
    Raises HTTPException on invalid/expired tokens.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth[7:]
    clerk_secret = os.getenv("CLERK_SECRET_KEY")
    if not clerk_secret:
        return None  # Dev mode — no Clerk configured

    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        # Verify issuer
        iss = payload.get("iss", "")
        if not iss.startswith("https://clerk."):
            raise HTTPException(status_code=401, detail="Invalid token issuer")
        return payload.get("sub")  # Clerk user ID
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# ── Auth dependency ──


async def get_current_tenant(
    request: Request,
    session: Session = Depends(get_session),
) -> Tenant:
    """Get tenant from Clerk JWT, or fall back to dev tenant."""
    clerk_user_id = await get_clerk_user_id(request)

    if clerk_user_id:
        # Look up existing tenant
        tenant = session.query(Tenant).filter(Tenant.clerk_id == clerk_user_id).first()
        if tenant:
            return tenant
        # Auto-create on first sign-in
        tenant = Tenant(
            id=gen_id(),
            clerk_id=clerk_user_id,
            name=f"User {clerk_user_id[:8]}",
            email=f"{clerk_user_id}@clerk.user",
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        return tenant

    # No auth → dev fallback
    tenant = session.query(Tenant).first()
    if tenant is None:
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


# ── Intent Parser ──

@app.post("/parse", response_model=ParseResponse)
async def parse_intent(data: ParseRequest):
    """Parse a natural language business description into a structured spec."""
    import json
    import re

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if not openrouter_key:
        return _fallback_parse(data.description)

    prompt = f"""You are a business specification parser. Given a natural language description, 
extract the structured intent as JSON. Return ONLY valid JSON, no other text.

Description: {data.description}

Return JSON with these exact keys:
{{
  "project": "project_slug_here",
  "stack": "nextjs" or "fastapi" or "remix" or "astro",
  "market": "2-letter country code or global",
  "features": ["list", "of", "features"],
  "tools": ["list", "of", "required", "tools/services"],
  "explanation": "2-3 sentence explanation of what was understood and what will be built",
  "required_keys": ["GitHub", "Vercel", "OpenAI", "Stripe", ...]
}}

Rules:
- features: include storefront type, payment methods, integrations, languages, size ranges, shipping rules
- tools: include payment gateways (Stripe, BLIK, etc), hosting (Vercel, Fly.io), CMS, analytics
- required_keys: list the API/services the user needs to provide keys for (always include "GitHub")
- project slug: make it short, lowercase, hyphenated
- explanation: mention key stack decisions and why"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3.5-haiku",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            content = body["choices"][0]["message"]["content"]

            # Extract JSON from the response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return ParseResponse(
                    project=parsed.get("project", "my-project"),
                    stack=parsed.get("stack", "nextjs"),
                    market=parsed.get("market", "global"),
                    features=parsed.get("features", []),
                    tools=parsed.get("tools", []),
                    explanation=parsed.get("explanation", ""),
                    required_keys=parsed.get("required_keys", ["GitHub", "Vercel"]),
                )
            else:
                return _fallback_parse(data.description)

    except Exception:
        return _fallback_parse(data.description)


def _fallback_parse(description: str) -> ParseResponse:
    """Rule-based fallback parser when LLM is unavailable."""
    desc_lower = description.lower()

    # Market detection
    if any(w in desc_lower for w in ["poland", "polish", "pl", "polska", "zł", "blik"]):
        market = "PL"
    elif any(w in desc_lower for w in ["brazil", "brazilian", "br"]):
        market = "BR"
    elif any(w in desc_lower for w in ["germany", "german", "de"]):
        market = "DE"
    else:
        market = "global"

    # Stack detection
    if any(w in desc_lower for w in ["wordpress", "wp"]):
        stack = "wordpress"
    elif any(w in desc_lower for w in ["remix", "shopify remix"]):
        stack = "remix"
    elif any(w in desc_lower for w in ["api", "backend", "fastapi"]):
        stack = "fastapi"
    else:
        stack = "nextjs"

    # Features
    features = []
    tools = []
    required_keys = ["GitHub", "Vercel"]

    if any(w in desc_lower for w in ["store", "shop", "ecommerce", "e-commerce", "fashion", "clothing"]):
        features.append("ecommerce-storefront")
        tools.append("Stripe")
        required_keys.append("Stripe")
        if "blik" in desc_lower or market == "PL":
            features.append("blik-payments")
            if "Stripe" not in tools:
                tools.append("Stripe")

    if any(w in desc_lower for w in ["plus-size", "plus size", "xl", "xxl"]):
        features.append("size-guide-xl-6xl")

    if any(w in desc_lower for w in ["free shipping", "darmowa dostawa", "free delivery"]):
        features.append("free-shipping-threshold")

    if any(w in desc_lower for w in ["blog", "content", "newsletter"]):
        features.append("blog")

    if any(w in desc_lower for w in ["saas", "dashboard", "subscription"]):
        features.append("saas-dashboard")
        required_keys.append("Stripe")

    if any(w in desc_lower for w in ["marketplace", "two-sided", "buyers and sellers"]):
        features.append("marketplace")

    if any(w in desc_lower for w in ["shopify", "shopify backend"]):
        features.append("shopify-backend")
        tools.append("Shopify")
        required_keys.append("Shopify")

    if any(w in desc_lower for w in ["dropshipping", "banggood", "aliexpress", "supplier"]):
        features.append("dropship-integration")

    if any(w in desc_lower for w in ["ai", "ml", "machine learning"]):
        tools.append("OpenAI")
        required_keys.append("OpenAI")

    # Generate project slug
    words = re.findall(r'[a-z]+', desc_lower)
    stop_words = {'a', 'an', 'the', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
                  'build', 'create', 'make', 'want', 'need', 'with', 'for', 'and',
                  'or', 'but', 'in', 'on', 'at', 'to', 'of', 'is', 'it', 'that',
                  'this', 'be', 'have', 'has', 'do', 'does', 'from', 'by', 'as'}
    meaningful = [w for w in words if w not in stop_words and len(w) > 2][:3]
    project = "-".join(meaningful) if meaningful else "my-project"

    # Generate explanation
    stack_name = {"nextjs": "Next.js", "fastapi": "FastAPI", "remix": "Remix", "wordpress": "WordPress", "astro": "Astro"}.get(stack, stack)
    feature_desc = ", ".join(f.replace("-", " ") for f in features) if features else "a web application"
    explanation = (
        f"Got it. I'll set up {project} — a {stack_name} application with {feature_desc}. "
        f"Targeting the {market} market. Monitoring and CI/CD included."
    )

    return ParseResponse(
        project=project,
        stack=stack,
        market=market,
        features=features,
        tools=tools,
        explanation=explanation,
        required_keys=required_keys,
    )


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
        run.error_message = str(e)[:500]
        run.log = traceback.format_exc()[:1000]
        project.status = "error"
        project.updated_at = datetime.now(timezone.utc)

    session.commit()
    try:
        session.refresh(run)
        return ReconciliationRunResponse.model_validate(run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serialization error: {str(e)}")


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
    """Parse intent YAML and simulate reconciliation (self-contained, no external imports)."""
    import yaml

    data = yaml.safe_load(intent_yaml) if intent_yaml else {}
    project_name = data.get("project", "unknown")

    resources = ["github_repo"]

    deploy = data.get("deploy", {}) or {}
    provider = deploy.get("provider", "none")
    if provider and provider != "none":
        resources.append(f"deploy_{provider}")

    monitoring = data.get("monitoring", {}) or {}
    if monitoring.get("sentry"):
        resources.append("sentry_project")
    if monitoring.get("phoenix"):
        resources.append("phoenix_project")

    memory = data.get("memory", {}) or {}
    if memory.get("chromadb"):
        resources.append("chromadb_collection")

    ci = data.get("ci", {}) or {}
    if ci.get("runner", "github_actions") != "none":
        resources.append("ci_pipeline")

    # Try to use the real intent engine if available
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        from services.intent_engine.schema import IntentFile
        from services.intent_engine.reconciler import reconcile, reconcile_summary

        intent = IntentFile.from_dict(data)
        results = reconcile(intent, dry_run=dry_run)
        summary = reconcile_summary(results)

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
    except Exception:
        pass

    # Simulated reconciliation (no resolvers registered yet)
    results_dict = [
        {
            "resource_key": r,
            "status": "skipped",
            "action_taken": "no resolver registered for " + r,
            "drifts_found": 0,
            "drifts_resolved": 0,
            "error_message": None,
            "duration_ms": 0.0,
        }
        for r in resources
    ]
    summary = {
        "total_resources": len(resources),
        "by_status": {"skipped": len(resources)},
        "total_drifts": 0,
        "errors": [],
        "healthy": True,
    }
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
