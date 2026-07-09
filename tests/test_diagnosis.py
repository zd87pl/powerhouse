"""Tests for the heuristic error-diagnosis engine and its API wiring."""

from fastapi.testclient import TestClient

from services.instill_api.diagnosis import diagnose_error, extract_files
from services.instill_api.main import _run_agent, app


# ── Heuristic engine ──


def test_python_missing_module_is_high_severity_dependency():
    d = diagnose_error(
        title="ModuleNotFoundError",
        message="ModuleNotFoundError: No module named 'httpx'",
    )
    assert d.category == "missing_dependency"
    assert d.severity == "high"
    assert "httpx" in d.summary
    assert any("httpx" in step for step in d.suggested_fix)
    assert d.source == "heuristic"


def test_python_none_attribute_is_null_reference():
    d = diagnose_error(
        message="AttributeError: 'NoneType' object has no attribute 'name'"
    )
    assert d.category == "null_reference"
    assert "name" in d.summary


def test_python_key_error_captures_key():
    d = diagnose_error(message="KeyError: 'user_id'")
    assert d.category == "missing_key"
    assert "user_id" in d.summary
    assert any(".get(" in step for step in d.suggested_fix)


def test_js_cannot_read_property_is_null_reference():
    d = diagnose_error(
        message="TypeError: Cannot read properties of undefined (reading 'map')"
    )
    assert d.category == "null_reference"
    assert "map" in d.summary
    assert any("?." in step for step in d.suggested_fix)


def test_js_module_not_found_is_missing_dependency():
    d = diagnose_error(message="Module not found: Can't resolve 'axios'")
    assert d.category == "missing_dependency"
    assert any("axios" in step for step in d.suggested_fix)


def test_connection_refused_is_high_severity():
    d = diagnose_error(message="ConnectionRefusedError: [Errno 111] Connection refused")
    assert d.category == "connection_refused"
    assert d.severity == "high"


def test_specific_rule_wins_over_generic():
    # NoneType attribute access must classify as null_reference, not attribute_error.
    d = diagnose_error(message="AttributeError: 'NoneType' object has no attribute 'x'")
    assert d.category == "null_reference"


def test_unknown_error_falls_back_with_low_confidence():
    d = diagnose_error(message="Something completely unparseable happened !!!")
    assert d.category == "unknown"
    assert d.confidence == "low"
    assert d.suggested_fix  # still offers generic triage advice


def test_empty_input_is_handled():
    d = diagnose_error()
    assert d.category == "empty_input"


def test_diagnosis_is_deterministic():
    msg = "TypeError: Cannot read properties of null (reading 'id')"
    assert (
        diagnose_error(message=msg).to_dict() == diagnose_error(message=msg).to_dict()
    )


# ── File extraction ──


def test_extract_files_from_python_traceback_skips_site_packages():
    trace = (
        'File "/app/site-packages/httpx/_client.py", line 1, in send\n'
        '  File "/app/services/instill_api/main.py", line 42, in parse_intent\n'
    )
    files = extract_files(trace)
    assert files == ["/app/services/instill_api/main.py:42"]


def test_extract_files_from_js_stack():
    trace = "at Object.fn (src/app/page.tsx:12:5)\n  at render (src/lib/utils.ts:7:1)"
    files = extract_files(trace)
    assert "src/app/page.tsx:12" in files
    assert "src/lib/utils.ts:7" in files


# ── API wiring ──


def test_demo_diagnose_endpoint_is_public_and_heuristic(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(app)
    resp = client.post(
        "/api/demo/diagnose",
        json={"message": "KeyError: 'tenant_id'"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["category"] == "missing_key"
    assert body["source"] == "heuristic"
    assert isinstance(body["suggested_fix"], list) and body["suggested_fix"]


def test_autofix_agent_runs_diagnosis():
    status, output = _run_agent(
        "autofix",
        "File \"app/main.py\", line 10\nModuleNotFoundError: No module named 'redis'",
    )
    assert status == "succeeded"
    assert "Root cause" in output
    assert "redis" in output


def test_non_autofix_agent_reports_not_wired():
    status, output = _run_agent("research", "look into vector DBs")
    assert status == "skipped"
    assert "not wired" in output
