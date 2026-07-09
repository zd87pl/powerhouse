"""Shared test configuration.

Isolates the suite from the developer's environment BEFORE any application
module is imported: a throwaway SQLite database (never the repo-root
instill.db), dev-mode auth, a deterministic secret key, and no ambient
provider credentials (so no test can ever make a live provider call because
the machine happens to have tokens set).
"""

import os
import tempfile

_TEST_DB_DIR = tempfile.mkdtemp(prefix="powerhouse-test-db-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db"
os.environ.setdefault("POWERHOUSE_ENV", "test")
os.environ.setdefault("POWERHOUSE_SECRET_KEY", "test-secret-key")

for _var in (
    "GITHUB_TOKEN",
    "GITHUB_OWNER",
    "VERCEL_TOKEN",
    "FLY_API_TOKEN",
    "SENTRY_AUTH_TOKEN",
    "SENTRY_ORG",
    "OPENROUTER_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "STRIPE_SECRET_KEY",
    "CLERK_SECRET_KEY",
    "POWERHOUSE_ENABLE_BUILDS",
):
    os.environ.pop(_var, None)
