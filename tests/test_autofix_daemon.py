"""Tests for the autofix daemon's GitHub commit + PR flow.

The daemon lives in a hyphenated directory (not an importable package), so we
load it by file path and stub out ``requests``.
"""

import importlib.util
import tempfile
from pathlib import Path

import pytest

# Load the daemon module by path, pointing its alerts dir at a temp location so
# import never touches /data.
import os

os.environ.setdefault("AUTOFIX_ALERTS_DIR", tempfile.mkdtemp(prefix="autofix-test-"))
_DAEMON_PATH = (
    Path(__file__).resolve().parents[1] / "services" / "autofix-daemon" / "main.py"
)
_spec = importlib.util.spec_from_file_location("autofix_daemon_main", _DAEMON_PATH)
assert _spec and _spec.loader
daemon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daemon)


class _Resp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = ""

    def json(self):
        return self._json


class FakeRequests:
    """Dispatches GET/POST/PATCH on (method, url-substring) and records calls."""

    def __init__(self, routes):
        self.routes = routes  # list[(method, url_substring, _Resp)]
        self.calls = []  # list[(method, url, json_body)]

    def _match(self, method, url):
        for m, sub, resp in self.routes:
            if m == method and sub in url:
                return resp
        raise AssertionError(f"unexpected {method} {url}")

    def get(self, url, **kw):
        self.calls.append(("GET", url, kw.get("json")))
        return self._match("GET", url)

    def post(self, url, **kw):
        self.calls.append(("POST", url, kw.get("json")))
        return self._match("POST", url)

    def patch(self, url, **kw):
        self.calls.append(("PATCH", url, kw.get("json")))
        return self._match("PATCH", url)


@pytest.fixture
def gh(monkeypatch):
    monkeypatch.setattr(daemon, "GITHUB_TOKEN", "tok")
    return monkeypatch


def test_commit_file_changes_builds_real_commit(gh):
    fake = FakeRequests(
        [
            ("GET", "git/commits", _Resp(200, {"tree": {"sha": "basetree"}})),
            ("POST", "git/blobs", _Resp(201, {"sha": "blob1"})),
            ("POST", "git/trees", _Resp(201, {"sha": "newtree"})),
            ("POST", "git/commits", _Resp(201, {"sha": "newcommit"})),
            ("PATCH", "git/refs", _Resp(200, {})),
        ]
    )
    gh.setattr(daemon, "requests", fake)

    sha = daemon.commit_file_changes(
        "owner/repo",
        "autofix/1",
        "parentsha",
        [{"path": "app/x.py", "content": "x = 1\n"}],
        "autofix: fix x",
    )

    assert sha == "newcommit"
    # The blob carried the real file content (so the PR won't be empty).
    blob_calls = [c for c in fake.calls if c[0] == "POST" and "git/blobs" in c[1]]
    assert blob_calls and blob_calls[0][2]["content"] == "x = 1\n"
    # The tree layered on the base tree and the ref was moved to the new commit.
    tree_call = next(c for c in fake.calls if "git/trees" in c[1])
    assert tree_call[2]["base_tree"] == "basetree"
    patch_call = next(c for c in fake.calls if c[0] == "PATCH")
    assert patch_call[2]["sha"] == "newcommit"


def test_commit_file_changes_returns_none_without_changes(gh):
    fake = FakeRequests([])
    gh.setattr(daemon, "requests", fake)
    assert daemon.commit_file_changes("o/r", "b", "sha", [], "msg") is None
    assert fake.calls == []  # never touches the network


def test_open_github_pr_commits_then_opens_pr(gh):
    fake = FakeRequests(
        [
            ("GET", "git/refs/heads", _Resp(200, {"object": {"sha": "basesha"}})),
            ("GET", "git/commits", _Resp(200, {"tree": {"sha": "basetree"}})),
            ("POST", "git/refs", _Resp(201, {})),
            ("POST", "git/blobs", _Resp(201, {"sha": "blob1"})),
            ("POST", "git/trees", _Resp(201, {"sha": "newtree"})),
            ("POST", "git/commits", _Resp(201, {"sha": "newcommit"})),
            ("PATCH", "git/refs", _Resp(200, {})),
            (
                "POST",
                "pulls",
                _Resp(201, {"html_url": "https://github.com/o/r/pull/7"}),
            ),
        ]
    )
    gh.setattr(daemon, "requests", fake)

    url = daemon.open_github_pr(
        "o/r",
        "autofix/7",
        "Fix null deref",
        "body",
        [{"path": "src/a.ts", "content": "export const a = 1;\n"}],
    )
    assert url == "https://github.com/o/r/pull/7"
    # A commit must precede the PR (otherwise the PR is empty).
    methods = [(c[0], c[1]) for c in fake.calls]
    assert any("git/commits" in u for m, u in methods if m == "POST")
    assert any("pulls" in u for m, u in methods)


def test_open_github_pr_returns_none_without_changes(gh):
    fake = FakeRequests([])
    gh.setattr(daemon, "requests", fake)
    assert daemon.open_github_pr("o/r", "b", "t", "body", []) is None
    assert fake.calls == []


def test_process_alert_opens_pr_when_changes_present(gh, monkeypatch):
    monkeypatch.setattr(
        daemon,
        "diagnose",
        lambda title, msg: {
            "diagnosis": "Null deref in handler.",
            "files": ["src/a.ts"],
            "changes": [{"path": "src/a.ts", "content": "export const a = 1;\n"}],
        },
    )
    captured = {}

    def fake_open_pr(
        repo, branch, title, body, changes, base=daemon.GITHUB_BASE_BRANCH
    ):
        captured.update(repo=repo, changes=changes)
        return "https://github.com/o/r/pull/9"

    monkeypatch.setattr(daemon, "open_github_pr", fake_open_pr)

    alert = {"id": "abc", "repo": "o/r", "title": "TypeError", "message": "boom"}
    daemon.process_alert(alert)

    assert alert["pr_url"] == "https://github.com/o/r/pull/9"
    assert alert["status"] == "pr_opened"
    assert captured["repo"] == "o/r"
    assert captured["changes"][0]["path"] == "src/a.ts"
