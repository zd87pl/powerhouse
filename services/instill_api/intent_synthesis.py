"""Convert parsed business specs into `.powerhouse.yml` intent documents.

This is the missing link between the intent parser (natural language →
structured spec) and the project/reconciliation layer (intent_yaml →
declared resources). The output vocabulary is restricted to keys that
``services.intent_engine.schema.IntentFile.from_dict`` understands; extra
descriptive keys (market, features, tools) are included for humans and are
tolerated by the schema parser.
"""

from __future__ import annotations

import re
from typing import List, Optional

import yaml

# Stacks that deploy as static/frontend apps → Vercel; API stacks → Fly.io.
_FRONTEND_STACKS = {"nextjs", "remix", "astro", "static", "wordpress"}
_BACKEND_STACKS = {"fastapi"}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", (value or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:64] or "my-project"


def deploy_provider_for_stack(stack: str) -> str:
    stack_lower = (stack or "").strip().lower()
    if stack_lower in _BACKEND_STACKS:
        return "flyio"
    if stack_lower in _FRONTEND_STACKS:
        return "vercel"
    return "vercel"


def spec_to_intent_yaml(
    *,
    project: str,
    stack: str = "nextjs",
    market: str = "",
    features: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    description: str = "",
) -> str:
    """Render a parse result as a `.powerhouse.yml` document.

    Deterministic: the same spec always produces the same YAML. The result
    always declares github + deploy + monitoring + ci resources so a first
    reconcile reports every provider honestly (skipped until keys exist).
    """
    doc: dict = {"project": _slugify(project)}
    if description:
        doc["description"] = description.strip()
    doc["stack"] = (stack or "nextjs").strip().lower() or "nextjs"
    doc["deploy"] = {"provider": deploy_provider_for_stack(stack)}
    doc["monitoring"] = {"sentry": True}
    doc["ci"] = {"runner": "github_actions"}
    if market and market.lower() != "global":
        doc["market"] = market
    if features:
        doc["features"] = list(features)
    if tools:
        doc["tools"] = list(tools)
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
