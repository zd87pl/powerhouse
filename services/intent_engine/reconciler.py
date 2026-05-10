"""Core reconciliation logic."""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .resolvers import ReconciliationResult, ResolverRegistry, ResourceStatus
from .schema import IntentFile


def reconcile(intent: IntentFile, dry_run: bool = False) -> List[ReconciliationResult]:
    results: List[ReconciliationResult] = []
    for resource_key in intent.resource_keys:
        resolver = ResolverRegistry.get(resource_key)
        if resolver is None:
            results.append(
                ReconciliationResult(
                    resource_key=resource_key,
                    status=ResourceStatus.SKIPPED,
                    action_taken=f"no resolver registered for {resource_key}",
                )
            )
            continue
        t0 = time.monotonic()
        try:
            actual = resolver.get_actual_state(intent)
        except Exception as e:
            results.append(
                ReconciliationResult(
                    resource_key=resource_key,
                    status=ResourceStatus.ERROR,
                    error_message=f"failed to get actual state: {e}",
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            )
            continue
        drifts = resolver.diff(_declared_state(intent, resource_key), actual)
        if not drifts:
            results.append(
                ReconciliationResult(
                    resource_key=resource_key,
                    status=ResourceStatus.EXISTS,
                    action_taken="no drift detected",
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            )
            continue
        if dry_run:
            results.append(
                ReconciliationResult(
                    resource_key=resource_key,
                    status=ResourceStatus.DRIFTED,
                    action_taken="dry run — drifts detected but not applied",
                    drifts_found=drifts,
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            )
            continue
        try:
            result = resolver.apply(intent, drifts)
            result.duration_ms = (time.monotonic() - t0) * 1000
            results.append(result)
        except Exception as e:
            results.append(
                ReconciliationResult(
                    resource_key=resource_key,
                    status=ResourceStatus.ERROR,
                    error_message=f"apply failed: {e}",
                    drifts_found=drifts,
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            )
    return results


def reconcile_summary(results: List[ReconciliationResult]) -> Dict[str, Any]:
    by_status: Dict[str, int] = {}
    total_drifts = 0
    errors: List[str] = []
    for r in results:
        key = r.status.value
        by_status[key] = by_status.get(key, 0) + 1
        total_drifts += len(r.drifts_found) + r.drifts_resolved
        if r.error_message:
            errors.append(f"{r.resource_key}: {r.error_message}")
    return {
        "total_resources": len(results),
        "by_status": by_status,
        "total_drifts": total_drifts,
        "errors": errors,
        "healthy": len(errors) == 0,
    }


def _declared_state(intent: IntentFile, resource_key: str) -> Dict[str, Any]:
    if resource_key == "github_repo":
        return {
            "exists": True,
            "project": intent.project,
            "description": intent.description,
        }
    elif resource_key.startswith("deploy_"):
        provider = resource_key.replace("deploy_", "")
        return {
            "exists": True,
            "provider": provider,
            "region": intent.deploy.region,
            "domain": intent.deploy.domain or "",
        }
    elif resource_key == "sentry_project":
        return {"exists": True, "project": intent.project}
    elif resource_key == "phoenix_project":
        return {"exists": True, "project": intent.project}
    elif resource_key == "chromadb_collection":
        return {"exists": True, "project": intent.project}
    elif resource_key == "ci_pipeline":
        return {
            "exists": True,
            "runner": intent.ci.runner.value,
            "lint": intent.ci.lint,
            "typecheck": intent.ci.typecheck,
            "test": intent.ci.test,
            "secrets_scan": intent.ci.secrets_scan,
        }
    return {}
