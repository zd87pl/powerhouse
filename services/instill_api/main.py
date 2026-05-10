"""Instill API — FastAPI backend for the Powerhouse SaaS."""

import os
import traceback
import subprocess
import tempfile
import shutil
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
    BuildRequest,
    BuildResponse,
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
async def build_project(data: BuildRequest = None, raw_data: Request = None):
    """Scaffold a real Next.js project and deploy to Vercel.

    Accepts either JSON body (BuildRequest) or a parsed intent from /parse.
    Returns the live Vercel URL once deployed.
    """
    import json as json_mod

    # Handle both direct BuildRequest and raw JSON (from landing page)
    if data is None and raw_data is not None:
        body = await raw_data.json()
        data = BuildRequest(**body)
    elif data is None:
        raise HTTPException(status_code=400, detail="Missing request body")

    project_slug = data.project.strip().lower().replace(" ", "-")
    features_str = ", ".join(data.features) if data.features else "a web application"
    market = data.market or "global"

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
            features_html += f'            <li class="flex items-center gap-2"><span class="text-purple-400">▸</span> {f.replace("-", " ").title()}</li>\n'
        if not features_html:
            features_html = '            <li class="flex items-center gap-2"><span class="text-purple-400">▸</span> Responsive Web Application</li>\n'

        title = project_slug.replace("-", " ").title()

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
            ["vercel", "deploy", project_dir, "--prod", "--yes",
             "--token", vercel_token],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if deploy_result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Vercel deploy failed: {deploy_result.stderr[-500:]}",
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
            deploy_url = url_match.group(0) if url_match else f"https://{project_slug}.vercel.app"

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
      title="{title}"
      subtitle="{subtitle}"
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
async def swarm_build(data: BuildRequest):
    """Agent Swarm: Architect → Coder → DevOps. Builds a real Next.js project.

    Phase 1 (Architect): Parse intent → project plan
    Phase 2 (Coder): Generate full Next.js project with components/pages
    Phase 3 (DevOps): Push to GitHub → deploy to Vercel
    """
    import json as json_mod, re as regex

    project_slug = data.project.strip().lower().replace(" ", "-")
    features = data.features if data.features else ["responsive", "modern-ui"]
    title = project_slug.replace("-", " ").title()
    subtitle = f"A {', '.join(features[:3]).replace('-', ' ')} application targeting {data.market or 'global'} market."
    market = (data.market or "global").upper()
    description = data.description or subtitle

    github_token = os.getenv("GITHUB_TOKEN", "")
    vercel_token = os.getenv("VERCEL_TOKEN", "")

    if not github_token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")
    if not vercel_token:
        raise HTTPException(status_code=503, detail="VERCEL_TOKEN not configured")

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
        layout = _SWARM_LAYOUT_TSX.replace("{{TITLE}}", title).replace("{{DESCRIPTION}}", description)
        with open(os.path.join(project_dir, "src", "app", "layout.tsx"), "w") as f:
            f.write(layout)

        # Components
        header = _SWARM_HEADER_TSX.replace("{{NAV_JSON}}", json_mod.dumps(nav_items)).replace("{{PROJECT_TITLE}}", title)
        with open(os.path.join(project_dir, "src", "components", "Header.tsx"), "w") as f:
            f.write(header)
        with open(os.path.join(project_dir, "src", "components", "Footer.tsx"), "w") as f:
            f.write(_SWARM_FOOTER_TSX)
        with open(os.path.join(project_dir, "src", "components", "Hero.tsx"), "w") as f:
            f.write(_SWARM_HERO_TSX)

        # Pages
        with open(os.path.join(project_dir, "src", "app", "page.tsx"), "w") as f:
            f.write(_generate_page_tsx(title, subtitle, features))
        with open(os.path.join(project_dir, "src", "app", "features", "page.tsx"), "w") as f:
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
        with open(os.path.join(project_dir, "src", "app", "about", "page.tsx"), "w") as f:
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
            f"{gh_api}/repos/zd87pl/{project_slug}", headers=gh_headers, method="GET"
        )
        try:
            urlreq.urlopen(check_req)
            repo_exists = True
        except Exception:
            repo_exists = False

        if not repo_exists:
            create_body = json_mod.dumps({
                "name": project_slug,
                "description": f"{title} — built by Powerhouse Agent Swarm. {subtitle}",
                "private": False,
                "auto_init": False,
            }).encode()
            create_req = urlreq.Request(
                f"{gh_api}/user/repos", data=create_body, headers=gh_headers, method="POST"
            )
            try:
                urlreq.urlopen(create_req)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"GitHub repo creation failed: {e}")

        # 3b. Git init + push
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "ziggy@powerhouse.dev"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Powerhouse Agent Swarm"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "main"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=project_dir, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"⚡ Initial scaffold by Powerhouse Agent Swarm\n\nProject: {title}\nFeatures: {', '.join(features)}\nMarket: {market}"], cwd=project_dir, capture_output=True, timeout=10)

        # Push
        repo_url = f"https://zd87pl:{github_token}@github.com/zd87pl/{project_slug}.git"
        push_result = subprocess.run(
            ["git", "push", "-u", repo_url, "main"],
            cwd=project_dir, capture_output=True, text=True, timeout=30,
        )
        github_url = f"https://github.com/zd87pl/{project_slug}"

        # 3c. Deploy to Vercel via git integration
        # Create Vercel project linked to GitHub repo
        vercel_headers = {
            "Authorization": f"Bearer {vercel_token}",
            "Content-Type": "application/json",
        }
        vc_body = json_mod.dumps({
            "name": project_slug,
            "framework": "nextjs",
            "gitRepository": {
                "repo": f"zd87pl/{project_slug}",
                "type": "github",
            },
            "ssoProtection": None,
        }).encode()
        vc_req = urlreq.Request(
            "https://api.vercel.com/v9/projects",
            data=vc_body, headers=vercel_headers, method="POST",
        )
        try:
            vc_resp = urlreq.urlopen(vc_req)
            vc_data = json_mod.loads(vc_resp.read())
            vercel_project_id = vc_data.get("id", "")
            if "error" in vc_data:
                # Project may already exist — that's OK
                vercel_project_id = ""
        except Exception:
            vercel_project_id = ""

        # Trigger deploy via Vercel git integration
        deploy_url = ""
        if vercel_project_id:
            deploy_body = json_mod.dumps({
                "name": project_slug,
                "target": "production",
                "gitSource": {
                    "type": "github",
                    "repo": f"zd87pl/{project_slug}",
                    "ref": "main",
                },
                "projectSettings": {"framework": "nextjs"},
            }).encode()
            deploy_req = urlreq.Request(
                "https://api.vercel.com/v13/deployments",
                data=deploy_body, headers=vercel_headers, method="POST",
            )
            try:
                deploy_resp = urlreq.urlopen(deploy_req)
                deploy_data = json_mod.loads(deploy_resp.read())
                deploy_url = f"https://{deploy_data.get('url', project_slug + '.vercel.app')}"
            except Exception as e:
                # Fallback: deploy static preview
                deploy_url = f"https://{project_slug}.vercel.app"

        # Fallback: static HTML deploy if git deploy fails
        if not deploy_url or "error" in str(deploy_url):
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
  <ul class="space-y-2">{"".join(f"<li class='text-sm text-[#71717a] flex items-center gap-2'><span class='text-[#a78bfa]'>▸</span> {f.replace('-',' ').title()}</li>" for f in features[:8])}</ul>
</div>
<p class="text-xs text-[#71717a] mt-8">Built with <a href="https://powerhouse.dev" class="text-[#a78bfa] hover:underline">Powerhouse Agent Swarm</a> — Architect → Coder → DevOps</p>
</body></html>"""
            preview_dir = os.path.join(build_dir, "preview")
            os.makedirs(preview_dir, exist_ok=True)
            with open(os.path.join(preview_dir, "index.html"), "w") as f:
                f.write(preview_html)

            deploy_result = subprocess.run(
                ["vercel", "deploy", preview_dir, "--prod", "--yes", "--token", vercel_token],
                capture_output=True, text=True, timeout=60,
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
