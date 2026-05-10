"""Tests for API safety helpers."""

from services.instill_api.main import (
    SETUP_PROVIDERS,
    _parse_scope_header,
    _project_run_status_from_summary,
    _run_reconciliation,
    _setup_provider_status,
    _status_from_summary,
    _validation_status,
)
from services.instill_api.secrets import decrypt_secret, encrypt_secret, is_encrypted
from services.intent_engine.resolvers import ResolverRegistry


def test_reconciliation_does_not_mark_skipped_resources_synced(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_OWNER", raising=False)
    ResolverRegistry.clear()

    _results, summary = _run_reconciliation("project: missing-creds\n", dry_run=False)

    assert summary["healthy"] is False
    assert summary["by_status"].get("skipped", 0) >= 1
    assert _status_from_summary(summary) == "error"


def test_secret_encryption_round_trip(monkeypatch):
    monkeypatch.setenv("POWERHOUSE_SECRET_KEY", "test-secret-key")

    encrypted = encrypt_secret("ghp_example")

    assert encrypted != "ghp_example"
    assert is_encrypted(encrypted)
    assert decrypt_secret(encrypted) == "ghp_example"


def test_setup_provider_status_distinguishes_env_and_stored_keys():
    github = next(item for item in SETUP_PROVIDERS if item["provider"] == "github")

    missing = _setup_provider_status(github, has_key=False, env={})
    configured = _setup_provider_status(github, has_key=True, env={})
    connected = _setup_provider_status(
        github,
        has_key=False,
        env={"GITHUB_TOKEN": "token", "GITHUB_OWNER": "owner"},
    )

    assert missing["status"] == "missing"
    assert configured["status"] == "configured"
    assert configured["source"] == "encrypted_key"
    assert connected["status"] == "connected"
    assert connected["missing_env"] == []


def test_project_run_status_preserves_action_required_state():
    assert _project_run_status_from_summary({"errors": ["boom"]}) == "failed"
    assert _project_run_status_from_summary({"healthy": True}) == "succeeded"
    assert (
        _project_run_status_from_summary(
            {"healthy": False, "by_status": {"skipped": 2}}
        )
        == "skipped"
    )
    assert (
        _project_run_status_from_summary(
            {"healthy": False, "by_status": {"drifted": 1, "synced": 1}}
        )
        == "action_required"
    )


def test_validation_status_summarizes_checks():
    assert _validation_status([], has_credential=False) == "missing"
    assert (
        _validation_status(
            [{"label": "Auth", "status": "failed", "detail": "bad token"}],
            has_credential=True,
        )
        == "invalid"
    )
    assert (
        _validation_status(
            [{"label": "Scope", "status": "warning", "detail": "limited"}],
            has_credential=True,
        )
        == "action_required"
    )
    assert (
        _validation_status(
            [{"label": "Auth", "status": "passed", "detail": "ok"}],
            has_credential=True,
        )
        == "valid"
    )


def test_parse_scope_header_deduplicates_and_sorts():
    assert _parse_scope_header("repo, user, repo,  workflow ") == [
        "repo",
        "user",
        "workflow",
    ]
