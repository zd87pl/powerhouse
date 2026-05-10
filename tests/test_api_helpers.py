"""Tests for API safety helpers."""

from services.instill_api.main import _run_reconciliation, _status_from_summary
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
