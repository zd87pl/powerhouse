"""Secret encryption helpers for tenant-provided credentials."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


class SecretConfigError(RuntimeError):
    """Raised when secret encryption is not configured safely."""


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _runtime_env() -> str:
    return os.getenv("POWERHOUSE_ENV", os.getenv("ENV", "production")).lower()


def _raw_secret() -> str:
    configured = os.getenv("POWERHOUSE_SECRET_KEY", "")
    if configured:
        return configured

    if _env_bool("POWERHOUSE_ALLOW_INSECURE_DEV_SECRETS") or _runtime_env() in {
        "development",
        "local",
        "test",
    }:
        return "powerhouse-dev-secret-key-do-not-use-in-production"

    raise SecretConfigError("POWERHOUSE_SECRET_KEY is required before storing API keys")


def _fernet() -> Fernet:
    digest = hashlib.sha256(_raw_secret().encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    """Encrypt a secret value for database storage."""
    token = _fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"fernet:{token}"


def decrypt_secret(value: str) -> str:
    """Decrypt a secret previously produced by encrypt_secret."""
    if not value.startswith("fernet:"):
        raise InvalidToken("secret is not encrypted with the current scheme")
    return (
        _fernet().decrypt(value.removeprefix("fernet:").encode("utf-8")).decode("utf-8")
    )


def is_encrypted(value: str) -> bool:
    return value.startswith("fernet:")
