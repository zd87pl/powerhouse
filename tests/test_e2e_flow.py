"""End-to-end MVP flow test, zero API keys.

Exercises the README promise through the real HTTP surface:
describe → parse (with synthesized intent) → create project → reconcile
(honest skipped statuses, never fake failures) → runs visible → diagnose →
autofix agent run recorded.
"""

import yaml
from fastapi.testclient import TestClient

from services.instill_api.main import app
from services.intent_engine.schema import IntentFile

client = TestClient(app)

DESCRIPTION = (
    "Build me a plus-size fashion store for Poland with BLIK payments "
    "and free shipping over 200 zl"
)


def _create_project(**overrides):
    payload = {"name": "curvy-poland", "description": DESCRIPTION}
    payload.update(overrides)
    resp = client.post("/api/projects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_parse_returns_ready_to_use_intent_yaml():
    resp = client.post("/api/demo/parse", json={"description": DESCRIPTION})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["market"] == "PL"
    assert body["intent_yaml"], "parse must return synthesized intent_yaml"

    # The synthesized YAML must parse through the real intent schema and
    # declare the full resource set so a first reconcile checks everything.
    intent = IntentFile.from_dict(yaml.safe_load(body["intent_yaml"]))
    assert intent.project
    assert intent.needs_deploy
    assert intent.monitoring.sentry
    assert intent.needs_ci
    assert "github_repo" in intent.resource_keys


def test_create_project_synthesizes_intent_from_description():
    project = _create_project()
    assert project["intent_yaml"], "intent_yaml must be synthesized when omitted"
    intent = IntentFile.from_dict(yaml.safe_load(project["intent_yaml"]))
    assert intent.needs_deploy
    assert project["stack"] == "nextjs"  # detected from the description


def test_create_project_keeps_caller_supplied_intent():
    supplied = "project: my-api\nstack: fastapi\ndeploy:\n  provider: flyio\n"
    project = _create_project(name="my-api", intent_yaml=supplied)
    assert project["intent_yaml"] == supplied


def test_zero_key_reconcile_is_skipped_not_failed():
    project = _create_project(name="reconcile-me")
    pid = project["id"]

    resp = client.post(f"/api/projects/{pid}/reconcile", json={})
    assert resp.status_code == 200, resp.text
    run = resp.json()
    # Without provider credentials the run needs setup — it did not fail.
    assert run["status"] == "action_required", run
    assert run["error_message"] == ""

    project_after = client.get(f"/api/projects/{pid}").json()
    assert project_after["status"] == "action_required"

    runs = client.get(f"/api/projects/{pid}/runs").json()
    reconcile_runs = [r for r in runs if r["run_type"] == "reconcile"]
    assert reconcile_runs, "reconcile must be recorded as a ProjectRun"
    assert reconcile_runs[0]["status"] == "skipped"
    assert "skipped" in reconcile_runs[0]["summary"]
    assert "failed" not in reconcile_runs[0]["summary"]
    # Per-resource steps are surfaced for the dashboard progress view.
    assert any(s["status"] == "skipped" for s in reconcile_runs[0]["steps"])


def test_autofix_agent_records_succeeded_run_with_diagnosis():
    project = _create_project(name="fixable")
    pid = project["id"]
    resp = client.post(
        f"/api/projects/{pid}/agents",
        json={
            "agent_type": "autofix",
            "input_spec": "ModuleNotFoundError: No module named 'stripe'",
        },
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["status"] == "succeeded"
    assert "Root cause" in run["output"]
    assert "stripe" in run["output"]


def test_unwired_agent_is_recorded_skipped_not_succeeded():
    project = _create_project(name="scaffold-me")
    pid = project["id"]
    resp = client.post(
        f"/api/projects/{pid}/agents",
        json={"agent_type": "scaffold", "input_spec": "scaffold it"},
    )
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["status"] == "skipped"
    assert "not wired" in run["output"]

    runs = client.get(f"/api/projects/{pid}/runs").json()
    scaffold_runs = [r for r in runs if r["run_type"] == "scaffold"]
    assert scaffold_runs and scaffold_runs[0]["status"] == "skipped"


def test_readme_example_intent_yaml_parses():
    # The exact YAML from the README's "How It Works" section must not crash.
    readme_yaml = (
        "project: my-saas\n"
        'description: "Analytics dashboard for ecommerce"\n'
        "stack: nextjs\n"
        "auth: clerk\n"
        "database: supabase\n"
        "billing: stripe\n"
        "monitoring: sentry+phoenix\n"
    )
    intent = IntentFile.from_dict(yaml.safe_load(readme_yaml))
    assert intent.project == "my-saas"
    assert intent.monitoring.sentry and intent.monitoring.phoenix
    assert "sentry_project" in intent.resource_keys


def test_diagnose_endpoint_roundtrip():
    resp = client.post(
        "/api/diagnose",
        json={"message": "ConnectionRefusedError: [Errno 111] Connection refused"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["category"] == "connection_refused"
    assert body["severity"] == "high"


def test_parsed_project_name_is_always_accepted_by_create():
    # Even absurdly long single words must yield a name POST /api/projects takes.
    long_word = "rindfleischetikettierungsueberwachungsaufgabenuebertragungsgesetz"
    resp = client.post(
        "/api/demo/parse", json={"description": f"{long_word} platform for germany"}
    )
    assert resp.status_code == 200
    project_name = resp.json()["project"]
    assert len(project_name) <= 64

    create = client.post(
        "/api/projects", json={"name": project_name, "description": long_word}
    )
    assert create.status_code == 201, create.text


def test_invalid_bearer_token_is_rejected_even_in_dev(monkeypatch):
    # With Clerk configured, a garbage token must 401 — never fall through to
    # another tenant's data (POWERHOUSE_ENV=test is a dev-auth environment).
    monkeypatch.setenv("CLERK_SECRET_KEY", "sk_test_configured")
    resp = client.get("/api/projects", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


def test_api_key_create_upserts_instead_of_duplicating():
    payload = {
        "provider": "github",
        "key_name": "github (setup wizard)",
        "key_value": "token-one",
    }
    first = client.post("/api/keys", json=payload)
    assert first.status_code == 201, first.text
    second = client.post("/api/keys", json={**payload, "key_value": "token-two"})
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]

    keys = client.get("/api/keys").json()
    wizard_rows = [k for k in keys if k["key_name"] == "github (setup wizard)"]
    assert len(wizard_rows) == 1


def test_scalar_deploy_and_ci_shorthands_are_interpreted():
    intent = IntentFile.from_dict({"project": "shorthand", "deploy": "vercel"})
    assert intent.deploy.provider.value == "vercel"
    assert "deploy_vercel" in intent.resource_keys

    opted_out = IntentFile.from_dict({"project": "no-ci", "ci": "none"})
    assert not opted_out.needs_ci


def test_llm_string_list_fields_do_not_char_split():
    from services.instill_api.main import _spec_response

    resp = _spec_response(
        {"project": "shop", "features": "storefront", "required_keys": "GitHub"},
        "a shop",
    )
    assert resp.features == ["storefront"]
    assert resp.required_keys == ["GitHub"]
