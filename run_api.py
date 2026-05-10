"""Local development runner for the Powerhouse API."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite:///instill.db")
    os.environ.setdefault("POWERHOUSE_ENV", "development")
    os.environ.setdefault("POWERHOUSE_ALLOW_DEV_AUTH", "1")
    os.environ.setdefault("POWERHOUSE_ALLOW_INSECURE_DEV_SECRETS", "1")

    uvicorn.run(
        "services.instill_api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        reload=os.getenv("POWERHOUSE_RELOAD", "0").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
