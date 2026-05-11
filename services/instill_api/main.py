"""Instill API — FastAPI backend for the Powerhouse SaaS."""

import os
import traceback
import subprocess
import tempfile
import shutil
import re
import html as html_lib
import httpx
import jwt
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import get_session, DATABASE_URL
from .models import (
    AgentRun,
    ApiKey,
    Project,
    ProjectRun,
    ReconciliationRun,
    Tenant,
    gen_id,
)
from .schemas import (
    AgentRunRequest,
    AgentRunResponse,
    ApiKeyCreate,
    ApiKeyResponse,
    BuildRequest,
    BuildResponse,
    HealthResponse,
    ParseRequest,
    ParseResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectRunResponse,
    ProjectResponse,
    ProjectUpdate,
    ReconcileRequest,
    ReconciliationRunResponse,
    SetupStatusResponse,
    SetupValidationResponse,
)
from .secrets import SecretConfigError, decrypt_secret, encrypt_secret


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _runtime_env() -> str:
    return os.getenv("POWERHOUSE_ENV", os.getenv("ENV", "production")).lower()


def _dev_auth_allowed() -> bool:
    return _env_bool("POWERHOUSE_ALLOW_DEV_AUTH") or _runtime_env() in {
        "development",
        "local",
        "test",
    }


def _cors_origins() -> list[str]:
    configured = os.getenv("POWERHOUSE_CORS_ORIGINS", "")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    if _dev_auth_allowed():
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
    return []


def _slugify_project(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="Project slug cannot be empty")
    return slug[:64]


def _require_builds_enabled() -> None:
    if not _env_bool("POWERHOUSE_ENABLE_BUILDS"):
        raise HTTPException(
            status_code=403,
            detail=(
                "Build/deploy endpoints are disabled. Set POWERHOUSE_ENABLE_BUILDS=1 "
                "after auth, quotas, and provider credentials are configured."
            ),
        )


def _redact(value: str, secret: str) -> str:
    return value.replace(secret, "[redacted]") if secret else value


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "powerhouse-setup-validator",
    }


SETUP_PROVIDERS = [
    {
        "provider": "github",
        "label": "GitHub",
        "required": True,
        "required_env": ["GITHUB_TOKEN", "GITHUB_OWNER"],
        "docs_url": "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens",
        "signup_url": "https://github.com/signup",
        "referral_url": None,
        "next_action": "Add a GitHub token and owner so Powerhouse can inspect or create repositories.",
    },
    {
        "provider": "vercel",
        "label": "Vercel",
        "required": True,
        "required_env": ["VERCEL_TOKEN"],
        "docs_url": "https://vercel.com/account/settings/tokens",
        "signup_url": "https://vercel.com/signup",
        "referral_url": None,
        "next_action": "Add a Vercel token so Powerhouse can deploy generated projects.",
    },
    {
        "provider": "supabase",
        "label": "Supabase",
        "required": False,
        "required_env": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
        "docs_url": "https://supabase.com/docs/guides/api/api-keys",
        "signup_url": "https://supabase.com/dashboard/sign-in",
        "referral_url": None,
        "next_action": "Add Supabase credentials when a project needs database or auth provisioning.",
    },
    {
        "provider": "sentry",
        "label": "Sentry",
        "required": False,
        "required_env": ["SENTRY_AUTH_TOKEN", "SENTRY_ORG"],
        "docs_url": "https://docs.sentry.io/api/auth/",
        "signup_url": "https://sentry.io/signup/",
        "referral_url": None,
        "next_action": "Add Sentry credentials to wire production error tracking and autofix inputs.",
    },
    {
        "provider": "openrouter",
        "label": "OpenRouter",
        "required": False,
        "required_env": ["OPENROUTER_API_KEY"],
        "docs_url": "https://openrouter.ai/settings/keys",
        "signup_url": "https://openrouter.ai/sign-up",
        "referral_url": os.getenv("OPENROUTER_REFERRAL_URL"),
        "next_action": "Add an OpenRouter key to enable LLM-backed parsing and agent workflows.",
    },
    {
        "provider": "stripe",
        "label": "Stripe",
        "required": False,
        "required_env": ["STRIPE_SECRET_KEY"],
        "docs_url": "https://docs.stripe.com/keys",
        "signup_url": "https://dashboard.stripe.com/register",
        "referral_url": None,
        "next_action": "Add Stripe credentials when a project needs billing or checkout.",
    },
    {
        "provider": "flyio",
        "label": "Fly.io",
        "required": False,
        "required_env": ["FLY_API_TOKEN"],
        "docs_url": "https://fly.io/user/personal_access_tokens",
        "signup_url": "https://fly.io/app/sign-up",
        "referral_url": None,
        "next_action": "Add a Fly.io token when a project should deploy outside Vercel.",
    },
]


def _setup_provider_status(
    provider_config: dict[str, Any],
    has_key: bool,
    env: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    env_source = env if env is not None else os.environ
    required_env = list(provider_config["required_env"])
    missing_env = [name for name in required_env if not env_source.get(name)]
    env_ready = not missing_env

    if env_ready:
        status = "connected"
        source = "environment"
        next_action = "Ready to use."
    elif has_key:
        status = "configured"
        source = "encrypted_key"
        next_action = (
            "Credential is stored. Add required environment metadata or wire provider-specific validation."
            if missing_env
            else "Credential is stored and ready for provider validation."
        )
    else:
        status = "missing"
        source = "none"
        next_action = provider_config["next_action"]

    return {
        "provider": provider_config["provider"],
        "label": provider_config["label"],
        "required": provider_config["required"],
        "status": status,
        "source": source,
        "has_key": has_key,
        "required_env": required_env,
        "missing_env": missing_env,
        "docs_url": provider_config["docs_url"],
        "signup_url": provider_config.get("signup_url"),
        "referral_url": provider_config.get("referral_url"),
        "next_action": next_action,
    }


def _setup_status_for_tenant(session: Session, tenant: Tenant) -> SetupStatusResponse:
    key_providers = {
        provider
        for (provider,) in session.query(ApiKey.provider)
        .filter(ApiKey.tenant_id == tenant.id)
        .distinct()
        .all()
    }
    providers = [
        _setup_provider_status(config, config["provider"] in key_providers)
        for config in SETUP_PROVIDERS
    ]
    connected = sum(1 for provider in providers if provider["status"] == "connected")
    configured = sum(1 for provider in providers if provider["status"] == "configured")
    missing_required = sum(
        1
        for provider in providers
        if provider["required"] and provider["status"] == "missing"
    )
    return SetupStatusResponse(
        ready=missing_required == 0,
        connected=connected,
        configured=configured,
        missing_required=missing_required,
        total=len(providers),
        providers=providers,
    )


def _parse_scope_header(value: str) -> list[str]:
    return sorted({scope.strip() for scope in value.split(",") if scope.strip()})


def _validation_status(checks: list[dict[str, str]], has_credential: bool) -> str:
    if not has_credential:
        return "missing"
    if any(check["status"] == "failed" for check in checks):
        return "invalid"
    if any(check["status"] == "warning" for check in checks):
        return "action_required"
    return "valid"


def _provider_label(provider: str) -> str:
    for config in SETUP_PROVIDERS:
        if config["provider"] == provider:
            return str(config["label"])
    return provider.title()


def _validation_summary(provider: str, status: str) -> str:
    label = _provider_label(provider)
    if status == "valid":
        return f"{label} credentials are valid for setup checks."
    if status == "missing":
        return f"{label} credentials are missing."
    if status == "action_required":
        return f"{label} credentials work, but setup needs attention."
    return f"{label} validation failed."


def _latest_api_key(
    session: Session, tenant: Tenant, provider: str
) -> Optional[ApiKey]:
    return (
        session.query(ApiKey)
        .filter(ApiKey.tenant_id == tenant.id, ApiKey.provider == provider)
        .order_by(ApiKey.created_at.desc())
        .first()
    )


def _provider_credential(
    session: Session,
    tenant: Tenant,
    provider: str,
    env_names: list[str],
) -> tuple[Optional[str], str, Optional[str]]:
    for env_name in env_names:
        value = os.getenv(env_name)
        if value:
            return value, "environment", None

    key = _latest_api_key(session, tenant, provider)
    if key is None:
        return None, "none", None

    try:
        return decrypt_secret(key.encrypted_value), "encrypted_key", None
    except Exception as exc:
        return (
            None,
            "encrypted_key",
            f"Stored {provider} key cannot be decrypted: {exc}",
        )


def _validation_response(
    *,
    provider: str,
    source: str,
    checks: list[dict[str, str]],
    has_credential: bool,
    account: Optional[dict[str, Any]] = None,
    scopes: Optional[list[str]] = None,
    next_action: str = "",
) -> SetupValidationResponse:
    status = _validation_status(checks, has_credential)
    return SetupValidationResponse(
        provider=provider,
        status=status,
        source=source,
        validated_at=datetime.now(timezone.utc),
        summary=_validation_summary(provider, status),
        checks=checks,
        account=account or {},
        scopes=scopes or [],
        next_action=next_action or _next_validation_action(provider, status),
    )


def _next_validation_action(provider: str, status: str) -> str:
    if status == "valid":
        return "No action needed."
    if status == "missing":
        return f"Add a {_provider_label(provider)} token in environment variables or API Keys."
    if status == "action_required":
        return "Review the warning checks before enabling automated work."
    return "Replace the token or adjust its permissions, then validate again."


app = FastAPI(
    title="Instill API",
    description="Backend API for the Instill autonomous AI engineering harness",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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

    Returns None if no auth header is present.
    Raises HTTPException on invalid/expired tokens.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth[7:]
    clerk_secret = os.getenv("CLERK_SECRET_KEY")
    if not clerk_secret:
        raise HTTPException(
            status_code=503,
            detail="CLERK_SECRET_KEY is required to validate bearer tokens",
        )

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
    """Get tenant from Clerk JWT, with explicit local-only dev fallback."""
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

    if not _dev_auth_allowed():
        raise HTTPException(status_code=401, detail="Authentication required")

    # Local development fallback only. Production must use Clerk.
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


# ── Setup ──


@app.get("/api/setup/status", response_model=SetupStatusResponse)
async def setup_status(
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    return _setup_status_for_tenant(session, tenant)


@app.post("/api/setup/validate/{provider}", response_model=SetupValidationResponse)
async def validate_setup_provider(
    provider: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    if provider == "github":
        return await _validate_github_setup(session, tenant)
    if provider == "vercel":
        return await _validate_vercel_setup(session, tenant)
    raise HTTPException(
        status_code=404, detail=f"{provider} validation is not wired yet"
    )


async def _validate_github_setup(
    session: Session,
    tenant: Tenant,
) -> SetupValidationResponse:
    token, source, credential_error = _provider_credential(
        session, tenant, "github", ["GITHUB_TOKEN"]
    )
    checks: list[dict[str, str]] = []
    if credential_error:
        checks.append(
            {
                "label": "Stored credential",
                "status": "failed",
                "detail": credential_error,
            }
        )
    if not token:
        checks.append(
            {
                "label": "GitHub token",
                "status": "failed",
                "detail": "No GitHub token found in GITHUB_TOKEN or encrypted keys.",
            }
        )
        return _validation_response(
            provider="github",
            source=source,
            checks=checks,
            has_credential=False,
        )

    headers = {
        **_auth_headers(token),
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    account: dict[str, Any] = {}
    scopes: list[str] = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            user_resp = await client.get("https://api.github.com/user", headers=headers)
        except httpx.HTTPError as exc:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": f"GitHub API request failed: {exc}",
                }
            )
            return _validation_response(
                provider="github",
                source=source,
                checks=checks,
                has_credential=True,
            )
        scopes = _parse_scope_header(user_resp.headers.get("x-oauth-scopes", ""))
        if user_resp.status_code == 401:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": "GitHub rejected the token.",
                }
            )
            return _validation_response(
                provider="github",
                source=source,
                checks=checks,
                has_credential=True,
                scopes=scopes,
            )
        if user_resp.is_error:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": f"GitHub returned HTTP {user_resp.status_code}.",
                }
            )
            return _validation_response(
                provider="github",
                source=source,
                checks=checks,
                has_credential=True,
                scopes=scopes,
            )

        user = user_resp.json()
        login = user.get("login", "")
        account = {
            "login": login,
            "profile_url": user.get("html_url", ""),
            "plan": (user.get("plan") or {}).get("name", ""),
        }
        checks.append(
            {
                "label": "Authentication",
                "status": "passed",
                "detail": f"Authenticated as {login}.",
            }
        )

        try:
            repo_resp = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={
                    "per_page": 1,
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            checks.append(
                {
                    "label": "Repository access",
                    "status": "passed" if not repo_resp.is_error else "failed",
                    "detail": (
                        "Repository listing is available."
                        if not repo_resp.is_error
                        else f"GitHub repository listing returned HTTP {repo_resp.status_code}."
                    ),
                }
            )
        except httpx.HTTPError as exc:
            checks.append(
                {
                    "label": "Repository access",
                    "status": "failed",
                    "detail": f"GitHub repository listing failed: {exc}",
                }
            )

        owner = os.getenv("GITHUB_OWNER", "").strip() or login
        if owner == login:
            checks.append(
                {
                    "label": "Target owner",
                    "status": "passed",
                    "detail": f"Using authenticated user {login} as the target owner.",
                }
            )
        else:
            try:
                org_resp = await client.get(
                    f"https://api.github.com/orgs/{owner}",
                    headers=headers,
                )
                checks.append(
                    {
                        "label": "Target owner",
                        "status": "passed" if not org_resp.is_error else "failed",
                        "detail": (
                            f"Target organization {owner} is visible to the token."
                            if not org_resp.is_error
                            else f"Cannot verify GITHUB_OWNER={owner}; GitHub returned HTTP {org_resp.status_code}."
                        ),
                    }
                )
            except httpx.HTTPError as exc:
                checks.append(
                    {
                        "label": "Target owner",
                        "status": "failed",
                        "detail": f"Cannot verify GITHUB_OWNER={owner}: {exc}",
                    }
                )

    if scopes and not {"repo", "public_repo"}.intersection(scopes):
        checks.append(
            {
                "label": "Repository permissions",
                "status": "warning",
                "detail": "Token scopes do not include repo or public_repo. Fine-grained tokens may still work if repository permissions are configured.",
            }
        )
    else:
        checks.append(
            {
                "label": "Repository permissions",
                "status": "passed",
                "detail": (
                    "Repository scope is present."
                    if scopes
                    else "GitHub did not expose token scopes; relying on successful API checks."
                ),
            }
        )

    return _validation_response(
        provider="github",
        source=source,
        checks=checks,
        has_credential=True,
        account=account,
        scopes=scopes,
    )


async def _validate_vercel_setup(
    session: Session,
    tenant: Tenant,
) -> SetupValidationResponse:
    token, source, credential_error = _provider_credential(
        session, tenant, "vercel", ["VERCEL_TOKEN"]
    )
    checks: list[dict[str, str]] = []
    if credential_error:
        checks.append(
            {
                "label": "Stored credential",
                "status": "failed",
                "detail": credential_error,
            }
        )
    if not token:
        checks.append(
            {
                "label": "Vercel token",
                "status": "failed",
                "detail": "No Vercel token found in VERCEL_TOKEN or encrypted keys.",
            }
        )
        return _validation_response(
            provider="vercel",
            source=source,
            checks=checks,
            has_credential=False,
        )

    account: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            user_resp = await client.get(
                "https://api.vercel.com/v2/user",
                headers=_auth_headers(token),
            )
        except httpx.HTTPError as exc:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": f"Vercel API request failed: {exc}",
                }
            )
            return _validation_response(
                provider="vercel",
                source=source,
                checks=checks,
                has_credential=True,
            )
        if user_resp.status_code == 401:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": "Vercel rejected the token.",
                }
            )
            return _validation_response(
                provider="vercel",
                source=source,
                checks=checks,
                has_credential=True,
            )
        if user_resp.is_error:
            checks.append(
                {
                    "label": "Authentication",
                    "status": "failed",
                    "detail": f"Vercel returned HTTP {user_resp.status_code}.",
                }
            )
            return _validation_response(
                provider="vercel",
                source=source,
                checks=checks,
                has_credential=True,
            )

        body = user_resp.json()
        user = body.get("user", {})
        account = {
            "id": user.get("id", ""),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
        }
        display_name = account["username"] or account["email"] or account["id"]
        checks.append(
            {
                "label": "Authentication",
                "status": "passed",
                "detail": f"Authenticated as {display_name}.",
            }
        )

        try:
            projects_resp = await client.get(
                "https://api.vercel.com/v9/projects",
                headers=_auth_headers(token),
                params={"limit": 1},
            )
            checks.append(
                {
                    "label": "Project access",
                    "status": "passed" if not projects_resp.is_error else "failed",
                    "detail": (
                        "Project listing is available."
                        if not projects_resp.is_error
                        else f"Vercel project listing returned HTTP {projects_resp.status_code}."
                    ),
                }
            )
        except httpx.HTTPError as exc:
            checks.append(
                {
                    "label": "Project access",
                    "status": "failed",
                    "detail": f"Vercel project listing failed: {exc}",
                }
            )

    return _validation_response(
        provider="vercel",
        source=source,
        checks=checks,
        has_credential=True,
        account=account,
    )


# ── Intent Parser ──


@app.post("/parse", response_model=ParseResponse)
async def parse_intent(
    data: ParseRequest,
    tenant: Tenant = Depends(get_current_tenant),
):
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
            json_match = re.search(r"\{[\s\S]*\}", content)
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


# ── Demo (public, no auth required) ──


@app.post("/api/demo/parse", response_model=ParseResponse)
async def demo_parse(data: ParseRequest):
    """Public parse endpoint for the demo sandbox. No auth required.
    
    Uses the instance's OpenRouter key if available, otherwise falls back
    to rule-based parsing.
    """
    import json

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
  "tools": ["list", "of", "required", "tools"],
  "explanation": "Brief explanation of what was understood",
  "required_keys": ["list", "of", "API", "key", "names"]
}}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            if resp.is_error:
                return _fallback_parse(data.description)
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content.strip().removesuffix("```").removeprefix("```json").removeprefix("```").strip())
            return ParseResponse(
                project=parsed.get("project", "my-project"),
                stack=parsed.get("stack", "nextjs"),
                market=parsed.get("market", "global"),
                features=parsed.get("features", []),
                tools=parsed.get("tools", []),
                explanation=parsed.get("explanation", ""),
                required_keys=parsed.get("required_keys", ["GitHub", "Vercel"]),
            )
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

    if any(
        w in desc_lower
        for w in ["store", "shop", "ecommerce", "e-commerce", "fashion", "clothing"]
    ):
        features.append("ecommerce-storefront")
        tools.append("Stripe")
        required_keys.append("Stripe")
        if "blik" in desc_lower or market == "PL":
            features.append("blik-payments")
            if "Stripe" not in tools:
                tools.append("Stripe")

    if any(w in desc_lower for w in ["plus-size", "plus size", "xl", "xxl"]):
        features.append("size-guide-xl-6xl")

    if any(
        w in desc_lower for w in ["free shipping", "darmowa dostawa", "free delivery"]
    ):
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

    if any(
        w in desc_lower for w in ["dropshipping", "banggood", "aliexpress", "supplier"]
    ):
        features.append("dropship-integration")

    if any(w in desc_lower for w in ["ai", "ml", "machine learning"]):
        tools.append("OpenAI")
        required_keys.append("OpenAI")

    # Generate project slug
    words = re.findall(r"[a-z]+", desc_lower)
    stop_words = {
        "a",
        "an",
        "the",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "build",
        "create",
        "make",
        "want",
        "need",
        "with",
        "for",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "of",
        "is",
        "it",
        "that",
        "this",
        "be",
        "have",
        "has",
        "do",
        "does",
        "from",
        "by",
        "as",
    }
    meaningful = [w for w in words if w not in stop_words and len(w) > 2][:3]
    project = "-".join(meaningful) if meaningful else "my-project"

    # Generate explanation
    stack_name = {
        "nextjs": "Next.js",
        "fastapi": "FastAPI",
        "remix": "Remix",
        "wordpress": "WordPress",
        "astro": "Astro",
    }.get(stack, stack)
    feature_desc = (
        ", ".join(f.replace("-", " ") for f in features)
        if features
        else "a web application"
    )
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


# ── Project Builder ──

# Minimal Next.js + Tailwind v4 template embedded in the API
_NEXTJS_TEMPLATE = {
    "package.json": """{
  "name": "{{PROJECT}}",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.0.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0"
  }
}""",
    "next.config.js": """const nextConfig = {
  output: "export",
  images: { unoptimized: true },
};
module.exports = nextConfig;
""",
    "postcss.config.mjs": """const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
export default config;
""",
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./src/*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
""",
    ".gitignore": """node_modules/
.next/
out/
dist/
.env.local
""",
}


def _render_template(template: str, **kwargs) -> str:
    """Replace {{PLACEHOLDER}} with values."""
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


@app.post("/build", response_model=BuildResponse)
async def build_project(
    data: BuildRequest,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Scaffold a real Next.js project and deploy to Vercel.

    Accepts either JSON body (BuildRequest) or a parsed intent from /parse.
    Returns the live Vercel URL once deployed.
    """

    _require_builds_enabled()

    project_slug = _slugify_project(data.project)
    features_str = (
        ", ".join(html_lib.escape(f) for f in data.features)
        if data.features
        else "a web application"
    )
    market = html_lib.escape(data.market or "global")

    vercel_token = os.getenv("VERCEL_TOKEN", "")
    if not vercel_token:
        raise HTTPException(
            status_code=503,
            detail="VERCEL_TOKEN not configured. Cannot deploy.",
        )

    build_dir = tempfile.mkdtemp(prefix="powerhouse-build-")
    project_dir = os.path.join(build_dir, project_slug)

    try:
        # Build an HTML-only landing page (no npm needed)
        project_dir = os.path.join(build_dir, "out")
        os.makedirs(project_dir, exist_ok=True)

        # Generate a beautiful HTML page with Tailwind CSS CDN
        features_html = ""
        for f in data.features[:10]:
            label = html_lib.escape(f.replace("-", " ").title())
            features_html += f'            <li class="flex items-center gap-2"><span class="text-purple-400">▸</span> {label}</li>\n'
        if not features_html:
            features_html = '            <li class="flex items-center gap-2"><span class="text-purple-400">▸</span> Responsive Web Application</li>\n'

        title = html_lib.escape(project_slug.replace("-", " ").title())

        html = f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Built with Powerhouse</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>tailwind.config={{theme:{{extend:{{colors:{{bg:'#0a0a0f',surface:'#13131a',border:'#1e1e2e',accent:'#a78bfa',glow:'#7c3aed',text:'#e4e4e7',muted:'#71717a',success:'#34d399'}}}}}}}}</script>
    <style>body{{background:#0a0a0f;color:#e4e4e7}}::selection{{background:#7c3aed;color:#fff}}</style>
</head>
<body class="bg-[#0a0a0f] text-[#e4e4e7] antialiased min-h-screen flex flex-col items-center justify-center p-8 font-sans">
    <main class="max-w-2xl w-full space-y-8 text-center">
        <div class="space-y-4">
            <div class="inline-flex items-center gap-2 px-4 py-2 bg-[#13131a] border border-[#1e1e2e] rounded-full text-sm text-[#71717a] mb-4">
                <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                Deployed {datetime.now(timezone.utc).strftime("%b %d, %Y at %H:%M UTC")}
            </div>
            <h1 class="text-5xl md:text-6xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#7c3aed] bg-clip-text text-transparent">
                {title}
            </h1>
            <p class="text-[#71717a] text-lg max-w-lg mx-auto leading-relaxed">
                {features_str}
            </p>
        </div>

        <div class="bg-[#13131a] border border-[#1e1e2e] rounded-2xl p-8 text-left">
            <h2 class="text-xl font-semibold mb-4 flex items-center gap-2">
                <span>✨</span> Features
            </h2>
            <ul class="space-y-2.5 text-[#71717a]">
{features_html}            </ul>
        </div>

        <div class="flex flex-wrap gap-3 justify-center">
            <span class="px-4 py-2 bg-[#13131a] border border-[#1e1e2e] rounded-full text-sm text-[#71717a]">
                🎯 {market.upper()}
            </span>
            <span class="px-4 py-2 bg-[#13131a] border border-[#1e1e2e] rounded-full text-sm text-[#71717a]">
                ⚡ Next.js
            </span>
            <span class="px-4 py-2 bg-[#13131a] border border-[#1e1e2e] rounded-full text-sm text-[#71717a]">
                🔧 Tailwind CSS
            </span>
        </div>

        <div class="pt-4 border-t border-[#1e1e2e]">
            <p class="text-sm text-[#71717a]">
                Built with{" "}
                <a href="https://powerhouse.dev" class="text-[#a78bfa] hover:underline font-medium">
                    Powerhouse
                </a>
                {" — AI that builds, deploys, monitors, and heals your entire business."}
            </p>
        </div>
    </main>
</body>
</html>"""

        with open(os.path.join(project_dir, "index.html"), "w") as f:
            f.write(html)

        # Deploy to Vercel
        deploy_result = subprocess.run(
            [
                "vercel",
                "deploy",
                project_dir,
                "--prod",
                "--yes",
                "--token",
                vercel_token,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if deploy_result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Vercel deploy failed: {_redact(deploy_result.stderr[-500:], vercel_token)}",
            )

        # Extract the deployment URL
        deploy_url = ""
        for line in deploy_result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("https://") and "vercel.app" in line:
                deploy_url = line
                break
        if not deploy_url:
            import re as regex

            url_match = regex.search(
                r"https://[a-zA-Z0-9-]+\.vercel\.app",
                deploy_result.stdout + deploy_result.stderr,
            )
            deploy_url = (
                url_match.group(0)
                if url_match
                else f"https://{project_slug}.vercel.app"
            )

        return BuildResponse(
            project=project_slug,
            deploy_url=deploy_url,
            status="deployed",
            message=f"Project {project_slug} deployed to {deploy_url}",
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(build_dir)
        except Exception:
            pass


# ── Agent Swarm Builder ──

_NEXTJS_FULL_TEMPLATE = {
    "package.json": """{
  "name": "{{PROJECT}}",
  "version": "0.1.0",
  "private": true,
  "scripts": { "dev": "next dev", "build": "next build", "start": "next start" },
  "dependencies": { "next": "^15.0.0", "react": "^19.0.0", "react-dom": "^19.0.0" },
  "devDependencies": { "@tailwindcss/postcss": "^4.0.0", "tailwindcss": "^4.0.0", "typescript": "^5.0.0", "@types/node": "^22.0.0", "@types/react": "^19.0.0", "@types/react-dom": "^19.0.0" }
}""",
    "next.config.ts": """import type { NextConfig } from "next";
const config: NextConfig = { output: "export", images: { unoptimized: true } };
export default config;
""",
    "postcss.config.mjs": """const config = { plugins: { "@tailwindcss/postcss": {} } };
export default config;
""",
    "tsconfig.json": """{"compilerOptions":{"target":"ES2017","lib":["dom","dom.iterable","esnext"],"allowJs":true,"skipLibCheck":true,"strict":true,"noEmit":true,"esModuleInterop":true,"module":"esnext","moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"jsx":"react-jsx","incremental":true,"plugins":[{"name":"next"}],"paths":{"@/*":["./src/*"]}},"include":["next-env.d.ts","**/*.ts","**/*.tsx"],"exclude":["node_modules"]}""",
    "next-env.d.ts": """/// <reference types="next" />\n/// <reference types="next/types/global" />\n""",
}

_SWARM_GLOBALS_CSS = """@import "tailwindcss";
@source "../";

@theme {
  --color-bg: #0a0a0f; --color-surface: #13131a; --color-border: #1e1e2e;
  --color-accent: #a78bfa; --color-glow: #7c3aed; --color-text: #e4e4e7;
  --color-muted: #71717a; --color-success: #34d399;
}

body { background: var(--color-bg); color: var(--color-text); }
"""

_SWARM_LAYOUT_TSX = """import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "{{TITLE}}",
  description: "{{DESCRIPTION}}",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-bg text-text antialiased min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
"""

_SWARM_HEADER_TSX = """"use client";
import Link from "next/link";
import { useState } from "react";

const NAV = {{NAV_JSON}};

export function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="border-b border-border bg-bg/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-lg font-bold bg-gradient-to-r from-accent to-glow bg-clip-text text-transparent">
          {{PROJECT_TITLE}}
        </Link>
        <nav className="hidden md:flex items-center gap-6">
          {NAV.map((item: {label: string; href: string}) => (
            <Link key={item.href} href={item.href} className="text-sm text-muted hover:text-text transition-colors">
              {item.label}
            </Link>
          ))}
        </nav>
        <button onClick={() => setOpen(!open)} className="md:hidden text-muted">
          {open ? "✕" : "☰"}
        </button>
      </div>
      {open && (
        <div className="md:hidden border-t border-border px-6 py-4 space-y-3 bg-bg">
          {NAV.map((item: {label: string; href: string}) => (
            <Link key={item.href} href={item.href} className="block text-sm text-muted hover:text-text" onClick={() => setOpen(false)}>
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
"""

_SWARM_FOOTER_TSX = """import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border py-8 mt-16">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <p className="text-xs text-muted">
          Built with{" "}
          <a href="https://powerhouse.dev" className="text-accent hover:underline">Powerhouse</a>
          {" — "}AI that builds, deploys, monitors, and heals your entire business.
        </p>
      </div>
    </footer>
  );
}
"""

_SWARM_HERO_TSX = """import Link from "next/link";

export function Hero({ title, subtitle, features }: { title: string; subtitle: string; features: string[] }) {
  return (
    <section className="py-20 px-6 text-center">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-accent to-glow bg-clip-text text-transparent">
          {title}
        </h1>
        <p className="text-lg text-muted max-w-xl mx-auto leading-relaxed">{subtitle}</p>
        <div className="flex flex-wrap gap-3 justify-center pt-2">
          {features.slice(0, 4).map((f) => (
            <span key={f} className="px-3 py-1.5 bg-surface border border-border rounded-full text-sm text-muted">
              {f.replace(/-/g, " ").replace(/\\b\\w/g, (c: string) => c.toUpperCase())}
            </span>
          ))}
        </div>
        <div className="pt-4">
          <Link href="/features" className="inline-flex px-6 py-3 bg-glow hover:bg-violet-700 text-white rounded-xl font-semibold text-sm transition-colors">
            Explore Features →
          </Link>
        </div>
      </div>
    </section>
  );
}
"""


def _generate_page_tsx(title: str, subtitle: str, features: list) -> str:
    """Generate a page.tsx for any route."""
    import json as _json

    return f"""import {{ Hero }} from "@/components/Hero";

export default function HomePage() {{
  return (
    <Hero
      title={{{_json.dumps(title)}}}
      subtitle={{{_json.dumps(subtitle)}}}
      features={{{_json.dumps(features)}}}
    />
  );
}}
"""


def _generate_features_page_tsx(title: str, features: list) -> str:
    """Generate a features page with cards."""
    cards = ""
    for f in features[:9]:
        cards += f"""        <div className="bg-surface border border-border rounded-2xl p-6 hover:bg-surface/70 transition-colors">
          <h3 className="font-semibold text-text mb-2">{f.replace("-", " ").title()}</h3>
          <p className="text-sm text-muted">Fully integrated {f.replace("-", " ")} capability for your {title.lower()}.</p>
        </div>
"""
    return f"""import type {{ Metadata }} from "next";

export const metadata: Metadata = {{ title: "Features - {title}" }};

export default function FeaturesPage() {{
  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto space-y-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-accent to-glow bg-clip-text text-transparent">Features</h1>
          <p className="text-muted max-w-xl mx-auto">Everything you need in your {title.lower()}.</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
{cards}        </div>
      </div>
    </section>
  );
}}
"""


@app.post("/swarm-build", response_model=BuildResponse)
async def swarm_build(
    data: BuildRequest,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Agent Swarm: Architect → Coder → DevOps. Builds a real Next.js project.

    Phase 1 (Architect): Parse intent → project plan
    Phase 2 (Coder): Generate full Next.js project with components/pages
    Phase 3 (DevOps): Push to GitHub → deploy to Vercel
    """
    import json as json_mod

    _require_builds_enabled()

    project_slug = _slugify_project(data.project)
    features = data.features if data.features else ["responsive", "modern-ui"]
    title = project_slug.replace("-", " ").title()
    subtitle = f"A {', '.join(features[:3]).replace('-', ' ')} application targeting {data.market or 'global'} market."
    market = (data.market or "global").upper()
    description = data.description or subtitle

    github_token = os.getenv("GITHUB_TOKEN", "")
    vercel_token = os.getenv("VERCEL_TOKEN", "")
    github_owner = os.getenv("GITHUB_OWNER", "")

    if not github_token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")
    if not vercel_token:
        raise HTTPException(status_code=503, detail="VERCEL_TOKEN not configured")
    if not github_owner:
        raise HTTPException(status_code=503, detail="GITHUB_OWNER not configured")

    build_dir = tempfile.mkdtemp(prefix="swarm-build-")

    try:
        # ====================
        # Phase 1: ARCHITECT
        # ====================
        nav_items = [{"label": "Home", "href": "/"}]
        if len(features) > 3:
            nav_items.append({"label": "Features", "href": "/features"})
        nav_items.append({"label": "About", "href": "/about"})

        # ====================
        # Phase 2: CODER
        # ====================
        project_dir = os.path.join(build_dir, project_slug)
        os.makedirs(os.path.join(project_dir, "src", "app", "features"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "src", "app", "about"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "src", "components"), exist_ok=True)

        # Template files
        for filename, content in _NEXTJS_FULL_TEMPLATE.items():
            rendered = content.replace("{{PROJECT}}", project_slug)
            with open(os.path.join(project_dir, filename), "w") as f:
                f.write(rendered)

        # globals.css
        with open(os.path.join(project_dir, "src", "app", "globals.css"), "w") as f:
            f.write(_SWARM_GLOBALS_CSS)

        # Layout
        layout = _SWARM_LAYOUT_TSX.replace("{{TITLE}}", title).replace(
            "{{DESCRIPTION}}", description
        )
        with open(os.path.join(project_dir, "src", "app", "layout.tsx"), "w") as f:
            f.write(layout)

        # Components
        header = _SWARM_HEADER_TSX.replace(
            "{{NAV_JSON}}", json_mod.dumps(nav_items)
        ).replace("{{PROJECT_TITLE}}", title)
        with open(
            os.path.join(project_dir, "src", "components", "Header.tsx"), "w"
        ) as f:
            f.write(header)
        with open(
            os.path.join(project_dir, "src", "components", "Footer.tsx"), "w"
        ) as f:
            f.write(_SWARM_FOOTER_TSX)
        with open(os.path.join(project_dir, "src", "components", "Hero.tsx"), "w") as f:
            f.write(_SWARM_HERO_TSX)

        # Pages
        with open(os.path.join(project_dir, "src", "app", "page.tsx"), "w") as f:
            f.write(_generate_page_tsx(title, subtitle, features))
        with open(
            os.path.join(project_dir, "src", "app", "features", "page.tsx"), "w"
        ) as f:
            f.write(_generate_features_page_tsx(title, features))

        # About page
        about_tsx = f"""import type {{ Metadata }} from "next";

export const metadata: Metadata = {{ title: "About - {title}" }};

export default function AboutPage() {{
  return (
    <section className="py-20 px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-accent to-glow bg-clip-text text-transparent">About</h1>
        <div className="bg-surface border border-border rounded-2xl p-8 space-y-4 text-muted leading-relaxed">
          <p>{subtitle}</p>
          <p>Built with the Powerhouse Agent Swarm: Architect → Coder → DevOps. This entire project was generated from a natural language description in seconds, then pushed to GitHub and deployed to Vercel automatically.</p>
          <div className="flex flex-wrap gap-2 pt-4">
            <span className="px-3 py-1.5 bg-bg border border-border rounded-full text-xs">🎯 {{market.upper()}}</span>
            <span className="px-3 py-1.5 bg-bg border border-border rounded-full text-xs">⚡ Next.js 15</span>
            <span className="px-3 py-1.5 bg-bg border border-border rounded-full text-xs">🎨 Tailwind v4</span>
            <span className="px-3 py-1.5 bg-bg border border-border rounded-full text-xs">🤖 AI-Generated</span>
          </div>
        </div>
      </div>
    </section>
  );
}}
"""
        with open(
            os.path.join(project_dir, "src", "app", "about", "page.tsx"), "w"
        ) as f:
            f.write(about_tsx)

        # ====================
        # Phase 3: DEVOPS
        # ====================

        # 3a. Create GitHub repo
        import urllib.request as urlreq

        gh_api = "https://api.github.com"
        gh_headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }

        # Check if repo exists
        check_req = urlreq.Request(
            f"{gh_api}/repos/{github_owner}/{project_slug}",
            headers=gh_headers,
            method="GET",
        )
        try:
            urlreq.urlopen(check_req)
            repo_exists = True
        except Exception:
            repo_exists = False

        if not repo_exists:
            create_body = json_mod.dumps(
                {
                    "name": project_slug,
                    "description": f"{title} — built by Powerhouse Agent Swarm. {subtitle}",
                    "private": False,
                    "auto_init": False,
                }
            ).encode()
            create_req = urlreq.Request(
                f"{gh_api}/user/repos",
                data=create_body,
                headers=gh_headers,
                method="POST",
            )
            try:
                urlreq.urlopen(create_req)
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"GitHub repo creation failed: {e}"
                )

        # 3b. Git init + push
        subprocess.run(
            ["git", "init"], cwd=project_dir, capture_output=True, timeout=10
        )
        subprocess.run(
            ["git", "config", "user.email", "ziggy@powerhouse.dev"],
            cwd=project_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Powerhouse Agent Swarm"],
            cwd=project_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "main"], cwd=project_dir, capture_output=True
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=project_dir, capture_output=True, timeout=10
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"⚡ Initial scaffold by Powerhouse Agent Swarm\n\nProject: {title}\nFeatures: {', '.join(features)}\nMarket: {market}",
            ],
            cwd=project_dir,
            capture_output=True,
            timeout=10,
        )

        # Push
        repo_url = (
            f"https://{github_owner}:{github_token}"
            f"@github.com/{github_owner}/{project_slug}.git"
        )
        push_result = subprocess.run(
            ["git", "push", "-u", repo_url, "main"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if push_result.returncode != 0:
            stderr = _redact(push_result.stderr[-500:], github_token)
            raise HTTPException(status_code=500, detail=f"GitHub push failed: {stderr}")
        github_url = f"https://github.com/{github_owner}/{project_slug}"

        # 3c. Deploy to Vercel
        deploy_url = ""
        vercel_deploy_ok = False

        # Try Vercel git integration
        vercel_headers = {
            "Authorization": f"Bearer {vercel_token}",
            "Content-Type": "application/json",
        }
        vc_body = json_mod.dumps(
            {
                "name": project_slug,
                "framework": "nextjs",
                "gitRepository": {
                    "repo": f"{github_owner}/{project_slug}",
                    "type": "github",
                },
                "ssoProtection": None,
            }
        ).encode()
        vc_req = urlreq.Request(
            "https://api.vercel.com/v9/projects",
            data=vc_body,
            headers=vercel_headers,
            method="POST",
        )
        try:
            vc_resp = urlreq.urlopen(vc_req)
            vc_data = json_mod.loads(vc_resp.read())
            if "error" not in vc_data:
                # Trigger deployment
                deploy_body = json_mod.dumps(
                    {
                        "name": project_slug,
                        "target": "production",
                        "gitSource": {
                            "type": "github",
                            "repo": f"{github_owner}/{project_slug}",
                            "ref": "main",
                        },
                    }
                ).encode()
                deploy_req = urlreq.Request(
                    "https://api.vercel.com/v13/deployments",
                    data=deploy_body,
                    headers=vercel_headers,
                    method="POST",
                )
                deploy_resp = urlreq.urlopen(deploy_req)
                deploy_data = json_mod.loads(deploy_resp.read())
                got_url = deploy_data.get("url", "")
                if got_url:
                    deploy_url = f"https://{got_url}"
                    vercel_deploy_ok = True
        except Exception:
            vercel_deploy_ok = False

        # Fallback: static HTML deploy
        if not vercel_deploy_ok:
            # Copy out dir and deploy static HTML
            preview_html = f"""<!DOCTYPE html><html><head><title>{title}</title>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={{theme:{{extend:{{colors:{{bg:'#0a0a0f',surface:'#13131a',border:'#1e1e2e',accent:'#a78bfa',glow:'#7c3aed',text:'#e4e4e7',muted:'#71717a'}}}}}}}}</script>
</head><body class="bg-[#0a0a0f] text-[#e4e4e7] min-h-screen flex flex-col items-center justify-center p-8">
<h1 class="text-5xl font-bold bg-gradient-to-r from-[#a78bfa] to-[#7c3aed] bg-clip-text text-transparent mb-4">{title}</h1>
<p class="text-[#71717a] text-lg mb-8">{subtitle}</p>
<div class="flex gap-3 mb-8">
  <a href="{github_url}" class="px-4 py-2 bg-[#13131a] border border-[#1e1e2e] rounded-xl text-sm text-[#a78bfa] hover:underline">📦 GitHub Repo</a>
</div>
<div class="bg-[#13131a] border border-[#1e1e2e] rounded-2xl p-6 max-w-md w-full">
  <h2 class="text-sm font-semibold mb-3">✨ Features</h2>
  <ul class="space-y-2">{"".join(f"<li class='text-sm text-[#71717a] flex items-center gap-2'><span class='text-[#a78bfa]'>▸</span> {f.replace('-', ' ').title()}</li>" for f in features[:8])}</ul>
</div>
<p class="text-xs text-[#71717a] mt-8">Built with <a href="https://powerhouse.dev" class="text-[#a78bfa] hover:underline">Powerhouse Agent Swarm</a> — Architect → Coder → DevOps</p>
</body></html>"""
            preview_dir = os.path.join(build_dir, "preview")
            os.makedirs(preview_dir, exist_ok=True)
            with open(os.path.join(preview_dir, "index.html"), "w") as f:
                f.write(preview_html)

            deploy_result = subprocess.run(
                [
                    "vercel",
                    "deploy",
                    preview_dir,
                    "--prod",
                    "--yes",
                    "--token",
                    vercel_token,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            for line in deploy_result.stdout.split("\n"):
                if line.strip().startswith("https://") and "vercel.app" in line:
                    deploy_url = line.strip()
                    break

        return BuildResponse(
            project=project_slug,
            deploy_url=deploy_url or github_url,
            status="deployed",
            message=f"Agent Swarm deployed {title} — GitHub: {github_url}, Live: {deploy_url}",
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            shutil.rmtree(build_dir)
        except Exception:
            pass


# ── Projects ──


def _create_project_run(
    session: Session,
    tenant: Tenant,
    project: Project,
    *,
    run_type: str,
    status: str,
    title: str,
    summary: str = "",
    log: str = "",
    steps: Optional[list[dict[str, Any]]] = None,
    run_metadata: Optional[dict[str, Any]] = None,
) -> ProjectRun:
    now = datetime.now(timezone.utc)
    run = ProjectRun(
        id=gen_id(),
        tenant_id=tenant.id,
        project_id=project.id,
        run_type=run_type,
        status=status,
        title=title,
        summary=summary,
        log=log,
        steps=steps or [],
        run_metadata=run_metadata or {},
        started_at=now if status == "running" else None,
        completed_at=now if status not in {"queued", "running"} else None,
    )
    session.add(run)
    return run


def _project_run_status_from_summary(summary: dict[str, Any]) -> str:
    if summary.get("errors"):
        return "failed"
    if summary.get("healthy"):
        return "succeeded"
    by_status = summary.get("by_status") or {}
    if by_status and set(by_status.keys()) == {"skipped"}:
        return "skipped"
    return "action_required"


def _reconciliation_steps(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps = []
    for result in results:
        steps.append(
            {
                "label": result.get("resource_key", "resource"),
                "status": result.get("status", "unknown"),
                "detail": result.get("action_taken")
                or result.get("message")
                or result.get("error")
                or "",
            }
        )
    return steps


def _reconciliation_summary_text(summary: dict[str, Any]) -> str:
    by_status = summary.get("by_status") or {}
    if summary.get("errors"):
        return f"Reconciliation failed with {len(summary['errors'])} error(s)."
    if summary.get("healthy"):
        return "Declared resources are in sync."
    if not by_status:
        return "No declared resources were checked."
    parts = [f"{count} {status}" for status, count in sorted(by_status.items())]
    return "Resource check completed: " + ", ".join(parts) + "."


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
    _create_project_run(
        session,
        tenant,
        project,
        run_type="setup",
        status="succeeded",
        title="Project created",
        summary="Project registered in Powerhouse.",
    )
    session.commit()
    session.refresh(project)
    return ProjectResponse.model_validate(project)


@app.get("/api/projects/{project_id}/runs", response_model=List[ProjectRunResponse])
async def list_project_runs(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(default=30, le=100),
):
    runs = (
        session.query(ProjectRun)
        .join(Project)
        .filter(ProjectRun.project_id == project_id, Project.tenant_id == tenant.id)
        .order_by(ProjectRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [ProjectRunResponse.model_validate(run) for run in runs]


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = (
        session.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant.id)
        .first()
    )
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
    project = (
        session.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant.id)
        .first()
    )
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
    project = (
        session.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    session.delete(project)
    session.commit()


# ── Reconciliation ──


@app.post(
    "/api/projects/{project_id}/reconcile", response_model=ReconciliationRunResponse
)
async def reconcile_project(
    project_id: str,
    data: ReconcileRequest = ReconcileRequest(),
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = (
        session.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.intent_yaml is not None:
        project.intent_yaml = data.intent_yaml
    project.status = "reconciling"
    run = ReconciliationRun(
        id=gen_id(),
        project_id=project.id,
        status="running",
        dry_run=data.dry_run,
    )
    session.add(run)
    project_run = _create_project_run(
        session,
        tenant,
        project,
        run_type="reconcile",
        status="running",
        title="Reconcile intent",
        summary="Checking declared resources against provider state.",
        run_metadata={"dry_run": data.dry_run, "reconciliation_run_id": run.id},
    )
    session.commit()

    try:
        results, summary = _run_reconciliation(project.intent_yaml, data.dry_run)
        run.status = _status_from_summary(summary)
        run.drifts_found = summary.get("by_status", {})
        run.resources_checked = [r["resource_key"] for r in results]
        run.log = _serialize_run_log(results, summary)
        project_run.status = _project_run_status_from_summary(summary)
        project_run.summary = _reconciliation_summary_text(summary)
        project_run.steps = _reconciliation_steps(results)
        project_run.log = run.log
        project_run.completed_at = datetime.now(timezone.utc)
        project.status = run.status
        project.updated_at = datetime.now(timezone.utc)
    except Exception as e:
        run.status = "error"
        run.error_message = str(e)[:500]
        run.log = traceback.format_exc()[:1000]
        project_run.status = "failed"
        project_run.summary = "Reconciliation failed before completion."
        project_run.log = run.log
        project_run.completed_at = datetime.now(timezone.utc)
        project.status = "error"
        project.updated_at = datetime.now(timezone.utc)

    session.commit()
    try:
        session.refresh(run)
        return ReconciliationRunResponse.model_validate(run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Serialization error: {str(e)}")


@app.get(
    "/api/projects/{project_id}/reconciliations",
    response_model=List[ReconciliationRunResponse],
)
async def list_reconciliations(
    project_id: str,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
    limit: int = Query(default=20, le=100),
):
    runs = (
        session.query(ReconciliationRun)
        .join(Project)
        .filter(
            ReconciliationRun.project_id == project_id, Project.tenant_id == tenant.id
        )
        .order_by(ReconciliationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [ReconciliationRunResponse.model_validate(r) for r in runs]


# ── Agents ──


@app.post(
    "/api/projects/{project_id}/agents",
    response_model=AgentRunResponse,
    status_code=201,
)
async def trigger_agent(
    project_id: str,
    data: AgentRunRequest,
    session: Session = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    project = (
        session.query(Project)
        .filter(Project.id == project_id, Project.tenant_id == tenant.id)
        .first()
    )
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
    project_run = _create_project_run(
        session,
        tenant,
        project,
        run_type=data.agent_type,
        status="running",
        title=f"Run {data.agent_type} agent",
        summary="Agent job accepted by the control plane.",
        run_metadata={"agent_run_id": run.id},
    )
    session.commit()

    try:
        output = _run_agent(data.agent_type, data.input_spec, project.intent_yaml)
        run.status = "failed"
        run.output = output
        run.completed_at = datetime.now(timezone.utc)
        project_run.status = "failed"
        project_run.summary = output
        project_run.log = output
        project_run.completed_at = run.completed_at
    except Exception:
        run.status = "failed"
        run.log = traceback.format_exc()
        run.completed_at = datetime.now(timezone.utc)
        project_run.status = "failed"
        project_run.summary = "Agent run failed before producing output."
        project_run.log = run.log
        project_run.completed_at = run.completed_at

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
        .join(Project)
        .filter(AgentRun.project_id == project_id, Project.tenant_id == tenant.id)
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
    try:
        encrypted_value = encrypt_secret(data.key_value)
    except SecretConfigError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    key = ApiKey(
        id=gen_id(),
        tenant_id=tenant.id,
        provider=data.provider,
        key_name=data.key_name,
        encrypted_value=encrypted_value,
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
    key = (
        session.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.tenant_id == tenant.id)
        .first()
    )
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    session.delete(key)
    session.commit()


# ── Internal: reconciliation logic ──


def _status_from_summary(summary: dict) -> str:
    if summary.get("errors"):
        return "error"
    return "synced" if summary.get("healthy") else "drifted"


def _serialize_run_log(results: list[dict], summary: dict) -> str:
    import json

    return json.dumps({"summary": summary, "results": results}, indent=2, default=str)


def _run_reconciliation(intent_yaml: str, dry_run: bool = False):
    """Parse intent YAML and reconcile declared resources."""
    import yaml

    data = yaml.safe_load(intent_yaml) if intent_yaml else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Intent YAML must parse to a mapping/object")

    import sys

    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    from services.intent_engine.schema import IntentFile
    from services.intent_engine.reconciler import reconcile, reconcile_summary
    from services.intent_engine.resolvers import register_default_resolvers

    register_default_resolvers()
    intent = IntentFile.from_dict(data)
    results = reconcile(intent, dry_run=dry_run)
    summary = reconcile_summary(results)

    results_dict = [
        {
            "resource_key": r.resource_key,
            "status": r.status.value,
            "action_taken": r.action_taken,
            "drifts_found": [
                {
                    "field": d.field,
                    "declared": d.declared,
                    "actual": d.actual,
                    "severity": d.severity,
                }
                for d in r.drifts_found
            ],
            "drifts_resolved": r.drifts_resolved,
            "error_message": r.error_message,
            "duration_ms": r.duration_ms,
        }
        for r in results
    ]
    return results_dict, summary


def _run_agent(agent_type: str, input_spec: str, intent_yaml: str = "") -> str:
    """Return an explicit unsupported-agent message until the runtime is wired."""
    return (
        f"{agent_type} agent runtime is not wired to this API yet. "
        "Use reconciliation for infrastructure checks; agent execution needs the "
        "orchestrator worker integration before it can make changes."
    )


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
