"""SQLAlchemy models for Instill SaaS."""

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    clerk_id = Column(String, unique=True, nullable=False)  # Clerk user ID
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    projects = relationship(
        "Project", back_populates="tenant", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "ApiKey", back_populates="tenant", cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    stack = Column(String, default="custom")
    intent_yaml = Column(Text, default="")  # Raw .powerhouse.yml content
    status = Column(
        String, default="pending"
    )  # pending, reconciling, synced, drifted, error
    github_repo_url = Column(String, default="")
    deploy_url = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tenant = relationship("Tenant", back_populates="projects")
    reconciliation_runs = relationship(
        "ReconciliationRun", back_populates="project", cascade="all, delete-orphan"
    )
    agent_runs = relationship(
        "AgentRun", back_populates="project", cascade="all, delete-orphan"
    )


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    status = Column(
        String, default="pending"
    )  # pending, running, synced, drifted, error
    dry_run = Column(Boolean, default=False)
    drifts_found = Column(JSON, default=list)
    drifts_resolved = Column(JSON, default=list)
    resources_checked = Column(JSON, default=list)
    log = Column(Text, default="")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="reconciliation_runs")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    agent_type = Column(String, nullable=False)  # autofix, scaffold, swarm, research
    status = Column(String, default="pending")  # pending, running, completed, failed
    input_spec = Column(Text, default="")
    output = Column(Text, default="")
    pr_url = Column(String, default="")
    log = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="agent_runs")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=gen_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # github, vercel, flyio, sentry
    key_name = Column(String, nullable=False)  # display name
    encrypted_value = Column(Text, nullable=False)  # TODO: encrypt with Vault/fernet
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="api_keys")


def get_engine(db_url: str = "sqlite:///instill.db"):
    """Create SQLAlchemy engine. Use SQLite for dev, Postgres for prod."""
    return create_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    )


def init_db(db_url: str = "sqlite:///instill.db"):
    """Create all tables."""
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
