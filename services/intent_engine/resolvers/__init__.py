"""Resolver interface and base registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import os
from typing import Any, Callable, Dict, List, Optional


class ResourceStatus(str, Enum):
    UNKNOWN = "unknown"
    CREATING = "creating"
    EXISTS = "exists"
    DRIFTED = "drifted"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class Drift:
    resource_key: str
    field: str
    declared: Any
    actual: Any
    severity: str = "warning"


@dataclass
class ReconciliationResult:
    resource_key: str
    status: ResourceStatus
    action_taken: str = ""
    drifts_found: List[Drift] = field(default_factory=list)
    drifts_resolved: int = 0
    error_message: Optional[str] = None
    duration_ms: float = 0.0


class Resolver(ABC):
    resource_key: str = ""

    @abstractmethod
    def get_actual_state(self, intent: Any) -> Dict[str, Any]: ...

    @abstractmethod
    def apply(self, intent: Any, drifts: List[Drift]) -> ReconciliationResult: ...

    def diff(self, declared: Dict[str, Any], actual: Dict[str, Any]) -> List[Drift]:
        drifts: List[Drift] = []
        all_keys = set(declared.keys()) | set(actual.keys())
        for key in sorted(all_keys):
            d = declared.get(key)
            a = actual.get(key)
            if d != a:
                drifts.append(
                    Drift(
                        resource_key=self.resource_key,
                        field=key,
                        declared=d,
                        actual=a,
                        severity="critical"
                        if key in ("exists", "status")
                        else "warning",
                    )
                )
        return drifts


class ResolverRegistry:
    _resolvers: Dict[str, Resolver] = {}

    @classmethod
    def register(cls, resolver: Resolver) -> None:
        if not resolver.resource_key:
            raise ValueError(
                f"Resolver {resolver.__class__.__name__} must set resource_key"
            )
        cls._resolvers[resolver.resource_key] = resolver

    @classmethod
    def get(cls, resource_key: str) -> Optional[Resolver]:
        return cls._resolvers.get(resource_key)

    @classmethod
    def list_keys(cls) -> List[str]:
        return sorted(cls._resolvers.keys())

    @classmethod
    def clear(cls) -> None:
        cls._resolvers.clear()


ResolverFactory = Callable[[], Resolver]


def register_default_resolvers(clear_existing: bool = False) -> None:
    """Register built-in resolvers with credentials from the environment."""
    if clear_existing:
        ResolverRegistry.clear()

    from .chromadb import ChromaDBResolver
    from .ci import CIPipelineResolver
    from .flyio import FlyioResolver
    from .github import GitHubResolver
    from .sentry import SentryResolver
    from .vercel import VercelResolver

    defaults = [
        GitHubResolver(token=os.getenv("GITHUB_TOKEN", "")),
        VercelResolver(token=os.getenv("VERCEL_TOKEN", "")),
        FlyioResolver(token=os.getenv("FLY_API_TOKEN", "")),
        SentryResolver(),
        ChromaDBResolver(),
        CIPipelineResolver(),
    ]
    for resolver in defaults:
        if ResolverRegistry.get(resolver.resource_key) is None:
            ResolverRegistry.register(resolver)
