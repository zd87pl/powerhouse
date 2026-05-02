"""Schema for .powerhouse.yml intent files."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class Stack(str, Enum):
    NEXTJS = "nextjs"
    FASTAPI = "fastapi"
    FULLSTACK = "fullstack"
    STATIC = "static"
    CUSTOM = "custom"


class Provider(str, Enum):
    VERCEL = "vercel"
    FLYIO = "flyio"
    RAILWAY = "railway"
    RUNPOD = "runpod"
    NONE = "none"


class CIRunner(str, Enum):
    GITHUB = "github_actions"
    NONE = "none"


@dataclass
class DeployConfig:
    provider: Provider = Provider.NONE
    region: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    domain: Optional[str] = None


@dataclass
class MonitoringConfig:
    sentry: bool = False
    phoenix: bool = False
    prometheus: bool = False
    uptime_kuma: bool = False


@dataclass
class MemoryConfig:
    chromadb: bool = False
    wiki: bool = False


@dataclass
class CIConfig:
    runner: CIRunner = CIRunner.GITHUB
    lint: bool = True
    typecheck: bool = True
    test: bool = True
    secrets_scan: bool = True


@dataclass
class IntentFile:
    """A parsed .powerhouse.yml intent declaration."""

    project: str
    description: str = ""
    stack: Stack = Stack.CUSTOM
    deploy: DeployConfig = field(default_factory=DeployConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    ci: CIConfig = field(default_factory=CIConfig)
    source_path: Optional[Path] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def needs_github(self) -> bool:
        return True

    @property
    def needs_deploy(self) -> bool:
        return self.deploy.provider != Provider.NONE

    @property
    def needs_monitoring(self) -> bool:
        m = self.monitoring
        return m.sentry or m.phoenix or m.prometheus or m.uptime_kuma

    @property
    def needs_memory(self) -> bool:
        return self.memory.chromadb

    @property
    def needs_ci(self) -> bool:
        return self.ci.runner != CIRunner.NONE

    @property
    def resource_keys(self) -> List[str]:
        keys = []
        if self.needs_github:
            keys.append("github_repo")
        if self.needs_deploy:
            keys.append(f"deploy_{self.deploy.provider.value}")
        if self.monitoring.sentry:
            keys.append("sentry_project")
        if self.monitoring.phoenix:
            keys.append("phoenix_project")
        if self.needs_memory:
            keys.append("chromadb_collection")
        if self.needs_ci:
            keys.append("ci_pipeline")
        return keys

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "project": self.project,
            "description": self.description,
            "stack": self.stack.value if self.stack != Stack.CUSTOM else self.raw.get("stack", "custom"),
        }
        if self.deploy.provider != Provider.NONE:
            d["deploy"] = {"provider": self.deploy.provider.value, "region": self.deploy.region}
            if self.deploy.env:
                d["deploy"]["env"] = self.deploy.env
            if self.deploy.domain:
                d["deploy"]["domain"] = self.deploy.domain
        mon = {}
        if self.monitoring.sentry:
            mon["sentry"] = True
        if self.monitoring.phoenix:
            mon["phoenix"] = True
        if self.monitoring.prometheus:
            mon["prometheus"] = True
        if self.monitoring.uptime_kuma:
            mon["uptime_kuma"] = True
        if mon:
            d["monitoring"] = mon
        mem = {}
        if self.memory.chromadb:
            mem["chromadb"] = True
        if self.memory.wiki:
            mem["wiki"] = True
        if mem:
            d["memory"] = mem
        if self.ci.runner != CIRunner.NONE:
            d["ci"] = {
                "runner": self.ci.runner.value,
                "lint": self.ci.lint,
                "typecheck": self.ci.typecheck,
                "test": self.ci.test,
                "secrets_scan": self.ci.secrets_scan,
            }
        return d

    @classmethod
    def from_file(cls, path: Path) -> "IntentFile":
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(raw, source_path=path)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_path: Optional[Path] = None) -> "IntentFile":
        monitoring_data = data.get("monitoring", {}) or {}
        memory_data = data.get("memory", {}) or {}
        ci_data = data.get("ci", {}) or {}
        deploy_data = data.get("deploy", {}) or {}
        deploy_provider_raw = deploy_data.get("provider", "none")
        try:
            deploy_provider = Provider(deploy_provider_raw)
        except ValueError:
            deploy_provider = Provider.NONE

        deploy = DeployConfig(
            provider=deploy_provider,
            region=deploy_data.get("region", ""),
            env=deploy_data.get("env", {}),
            domain=deploy_data.get("domain"),
        )
        monitoring = MonitoringConfig(
            sentry=monitoring_data.get("sentry", False),
            phoenix=monitoring_data.get("phoenix", False),
            prometheus=monitoring_data.get("prometheus", False),
            uptime_kuma=monitoring_data.get("uptime_kuma", False),
        )
        memory = MemoryConfig(
            chromadb=memory_data.get("chromadb", False),
            wiki=memory_data.get("wiki", False),
        )
        ci = CIConfig(
            runner=CIRunner(ci_data.get("runner", "github_actions")),
            lint=ci_data.get("lint", True),
            typecheck=ci_data.get("typecheck", True),
            test=ci_data.get("test", True),
            secrets_scan=ci_data.get("secrets_scan", True),
        )
        stack_raw = data.get("stack", "custom")
        try:
            stack = Stack(stack_raw)
        except ValueError:
            stack = Stack.CUSTOM

        return cls(
            project=data.get("project", "unknown"),
            description=data.get("description", ""),
            stack=stack,
            deploy=deploy, monitoring=monitoring, memory=memory, ci=ci,
            source_path=source_path, raw=data,
        )


def load_intent(path: Path) -> IntentFile:
    return IntentFile.from_file(path)


def discover_intents(root: Path) -> List[Path]:
    candidates = list(root.glob(".powerhouse.yml"))
    for sub in ["projects", "apps", "services"]:
        subdir = root / sub
        if subdir.is_dir():
            candidates.extend(subdir.glob("**/.powerhouse.yml"))
    return sorted(candidates)
