"""Tests for the Declarative Intent Engine."""

import tempfile
from pathlib import Path

import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.intent_engine.engine import IntentEngine
from services.intent_engine.reconciler import reconcile, reconcile_summary, _declared_state
from services.intent_engine.resolvers import (
    ReconciliationResult, Resolver, ResolverRegistry, ResourceStatus,
)
from services.intent_engine.schema import (
    CIRunner, IntentFile, Provider, Stack, discover_intents, load_intent,
)


class TestSchemaParsing:
    def test_minimal_intent(self):
        intent = IntentFile.from_dict({"project": "my-app"})
        assert intent.project == "my-app"
        assert intent.stack == Stack.CUSTOM
        assert intent.deploy.provider == Provider.NONE
        assert not intent.needs_deploy
        assert not intent.needs_monitoring
        assert not intent.needs_memory

    def test_full_intent(self):
        data = {"project": "full-app", "description": "A fully configured app", "stack": "nextjs",
                "deploy": {"provider": "vercel", "region": "iad1", "env": {"NODE_ENV": "production"}, "domain": "full-app.vercel.app"},
                "monitoring": {"sentry": True, "phoenix": True, "prometheus": True},
                "memory": {"chromadb": True, "wiki": True},
                "ci": {"runner": "github_actions", "lint": True, "typecheck": True, "test": True, "secrets_scan": True}}
        intent = IntentFile.from_dict(data)
        assert intent.project == "full-app"
        assert intent.stack == Stack.NEXTJS
        assert intent.deploy.provider == Provider.VERCEL
        assert intent.deploy.region == "iad1"
        assert intent.monitoring.sentry is True
        assert intent.monitoring.phoenix is True
        assert intent.memory.chromadb is True
        assert intent.ci.runner == CIRunner.GITHUB

    def test_resource_keys_full(self):
        intent = IntentFile.from_dict({"project": "full", "deploy": {"provider": "vercel"},
                                        "monitoring": {"sentry": True, "phoenix": True},
                                        "memory": {"chromadb": True}, "ci": {"runner": "github_actions"}})
        keys = intent.resource_keys
        for k in ["github_repo", "deploy_vercel", "sentry_project", "phoenix_project", "chromadb_collection", "ci_pipeline"]:
            assert k in keys

    def test_load_from_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".powerhouse.yml"
            p.write_text("project: file-test\nstack: nextjs\ndeploy:\n  provider: vercel\n")
            intent = load_intent(p)
            assert intent.project == "file-test"
            assert intent.stack == Stack.NEXTJS

    def test_discover_intents_subdir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "projects" / "app1").mkdir(parents=True)
            (root / "projects" / "app1" / ".powerhouse.yml").write_text("project: app1\n")
            (root / "projects" / "app2").mkdir(parents=True)
            (root / "projects" / "app2" / ".powerhouse.yml").write_text("project: app2\n")
            assert len(discover_intents(root)) == 2


class TestReconciliation:
    def setup_method(self):
        ResolverRegistry.clear()

    def test_no_resolvers_registered(self):
        intent = IntentFile.from_dict({"project": "no-resolvers"})
        results = reconcile(intent)
        assert all(r.status == ResourceStatus.SKIPPED for r in results)

    def test_dry_run_detects_drifts(self):
        class MockResolver(Resolver):
            resource_key = "github_repo"
            def get_actual_state(self, intent): return {"exists": False, "project": intent.project}
            def apply(self, intent, drifts): return ReconciliationResult(resource_key=self.resource_key, status=ResourceStatus.CREATING, action_taken="created", drifts_resolved=len(drifts))
        ResolverRegistry.register(MockResolver())
        intent = IntentFile.from_dict({"project": "drift-test"})
        results = reconcile(intent, dry_run=True)
        r = [r for r in results if r.resource_key == "github_repo"][0]
        assert r.status == ResourceStatus.DRIFTED
        assert "dry run" in r.action_taken.lower()

    def test_reconcile_no_drift(self):
        class MockResolver(Resolver):
            resource_key = "github_repo"
            def get_actual_state(self, intent): return {"exists": True, "project": intent.project, "description": intent.description}
            def apply(self, intent, drifts): pytest.fail("should not be called")
        ResolverRegistry.register(MockResolver())
        intent = IntentFile.from_dict({"project": "synced", "description": "In sync"})
        results = reconcile(intent)
        r = [r for r in results if r.resource_key == "github_repo"][0]
        assert r.status == ResourceStatus.EXISTS

    def test_resolver_error_handling(self):
        class Failing(Resolver):
            resource_key = "github_repo"
            def get_actual_state(self, intent): raise RuntimeError("timeout")
            def apply(self, intent, drifts): return ReconciliationResult(resource_key=self.resource_key, status=ResourceStatus.ERROR)
        ResolverRegistry.register(Failing())
        intent = IntentFile.from_dict({"project": "error-test"})
        results = reconcile(intent)
        r = [r for r in results if r.resource_key == "github_repo"][0]
        assert r.status == ResourceStatus.ERROR
        assert "timeout" in (r.error_message or "")

    def test_reconcile_summary(self):
        results = [ReconciliationResult(resource_key="a", status=ResourceStatus.EXISTS),
                   ReconciliationResult(resource_key="b", status=ResourceStatus.CREATING),
                   ReconciliationResult(resource_key="c", status=ResourceStatus.ERROR, error_message="broke")]
        summary = reconcile_summary(results)
        assert summary["total_resources"] == 3
        assert summary["healthy"] is False

    def test_declared_state_github(self):
        intent = IntentFile.from_dict({"project": "foo", "description": "Bar"})
        state = _declared_state(intent, "github_repo")
        assert state["project"] == "foo"


class TestEngine:
    def setup_method(self):
        ResolverRegistry.clear()

    def test_engine_discover_and_reconcile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".powerhouse.yml").write_text("project: engine-test\n")
            engine = IntentEngine(root=root)
            records = engine.reconcile_all()
            assert "engine-test" in records
            assert records["engine-test"].error is None

    def test_engine_state_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_dir = Path(td) / "state"
            (root / ".powerhouse.yml").write_text("project: persist\n")
            engine = IntentEngine(root=root, state_dir=state_dir)
            engine.reconcile_all()
            assert len(list(state_dir.glob("*.json"))) == 1

    def test_engine_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".powerhouse.yml").write_text("project: dry\n")
            engine = IntentEngine(root=root, dry_run=True)
            records = engine.reconcile_all()
            assert records["dry"].dry_run is True

    def test_engine_parse_error(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".powerhouse.yml").write_text("just a string, not a mapping\n")
            engine = IntentEngine(root=root)
            records = engine.reconcile_all()
            record = list(records.values())[0]
            assert record.error is not None

    def test_on_reconcile_callback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".powerhouse.yml").write_text("project: cb\n")
            calls = []
            def cb(intent, results): calls.append(intent.project)
            engine = IntentEngine(root=root)
            engine.on_reconcile(cb)
            engine.reconcile_all()
            assert calls == ["cb"]


class TestResolvers:
    def setup_method(self):
        ResolverRegistry.clear()

    def test_registry_register_and_get(self):
        class T(Resolver):
            resource_key = "test"
            def get_actual_state(self, intent): return {}
            def apply(self, intent, drifts): return ReconciliationResult(resource_key="test", status=ResourceStatus.EXISTS)
        ResolverRegistry.register(T())
        assert ResolverRegistry.get("test") is not None

    def test_diff_detects_changes(self):
        class T(Resolver):
            resource_key = "t"
            def get_actual_state(self, intent): return {}
            def apply(self, intent, drifts): return ReconciliationResult(resource_key="t", status=ResourceStatus.EXISTS)
        drifts = T().diff({"exists": True, "region": "iad1"}, {"exists": False, "region": "ams"})
        assert len(drifts) == 2


class TestEdgeCases:
    def test_custom_stack(self):
        intent = IntentFile.from_dict({"project": "custom", "stack": "elixir-phoenix"})
        assert intent.stack == Stack.CUSTOM

    def test_null_deploy(self):
        intent = IntentFile.from_dict({"project": "null-dep", "deploy": None})
        assert intent.deploy.provider == Provider.NONE

    def test_empty_yaml_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".powerhouse.yml"
            p.write_text("")
            intent = load_intent(p)
            assert intent.project == "unknown"

    def test_multiple_intents_in_subdirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for i in range(3):
                proj = root / "projects" / f"app{i}"
                proj.mkdir(parents=True)
                (proj / ".powerhouse.yml").write_text(f"project: app{i}\n")
            assert len(discover_intents(root)) == 3

    def test_schema_all_providers(self):
        for prov in ["vercel", "flyio", "railway", "runpod", "none"]:
            intent = IntentFile.from_dict({"project": "t", "deploy": {"provider": prov}})
            assert intent.deploy.provider.value == prov

    def test_reconciler_includes_duration(self):
        class M(Resolver):
            resource_key = "github_repo"
            def get_actual_state(self, intent): return {"exists": True, "project": intent.project, "description": intent.description}
            def apply(self, intent, drifts): return ReconciliationResult(resource_key=self.resource_key, status=ResourceStatus.EXISTS)
        ResolverRegistry.register(M())
        results = reconcile(IntentFile.from_dict({"project": "dur"}))
        for r in results:
            assert r.duration_ms >= 0
