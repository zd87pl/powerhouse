"""
Deliberation Council — multi-agent collaborative decision-making.

Agents don't act unilaterally on high-stakes decisions.
Instead, they propose actions → council members vote → action executes only if approved.

Usage:
    council = DeliberationCouncil(quorum=3, approval_threshold=0.66)
    
    proposal = Proposal(
        agent_id="autofix",
        action="deploy_hotfix",
        description="Fix NullPointerException in auth.ts:42",
        risk_level=RiskLevel.MEDIUM,
    )
    
    verdict = await council.deliberate(proposal)
    if verdict.approved:
        await execute_action(proposal.action)
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..shared import EventBus, Event, EventPriority, get_event_bus
from ..shared import EpisodicMemory, MemoryEntry, get_memory

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"        # Safe, reversible (e.g., add logging)
    MEDIUM = "medium"  # Some risk, reversible (e.g., config change)
    HIGH = "high"      # Significant risk (e.g., database migration)
    CRITICAL = "critical"  # Production impact (e.g., hotfix deploy)


class VoteType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CONDITIONAL = "conditional"  # Approve IF condition met
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """A single council member's vote."""
    voter_id: str
    voter_role: str  # "architect", "reviewer", "devops", etc.
    vote: VoteType
    reason: str = ""
    condition: str = ""  # For CONDITIONAL votes
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Proposal:
    """An action proposed by an agent for council deliberation."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    action: str = ""  # Short name: "deploy_hotfix", "scale_service", "rollback"
    description: str = ""  # What and why
    risk_level: RiskLevel = RiskLevel.MEDIUM
    estimated_cost_usd: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)
    proposed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Verdict:
    """Result of council deliberation."""
    proposal_id: str
    approved: bool
    approval_ratio: float  # 0.0 to 1.0
    votes: list[Vote] = field(default_factory=list)
    summary: str = ""
    resolved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DeliberationCouncil:
    """
    A council of agents that votes on proposed actions.
    
    High-stakes actions (deploy, scale, rollback) must pass council approval.
    Low-risk actions can auto-approve.
    
    Quorum and threshold are configurable per risk level.
    """

    # Auto-approve thresholds per risk level (no council needed)
    AUTO_APPROVE_BELOW = RiskLevel.LOW

    def __init__(
        self,
        quorum: int = 2,
        approval_threshold: float = 0.51,
        council_members: list[dict] | None = None,
    ):
        """
        Args:
            quorum: Minimum number of votes needed to be valid
            approval_threshold: Fraction of APPROVE votes needed (0.0-1.0)
            council_members: List of {"id": ..., "role": ...} dicts
        """
        self.quorum = quorum
        self.approval_threshold = approval_threshold
        self._members: dict[str, str] = {}  # voter_id → role
        self._bus: EventBus = get_event_bus()
        self._memory: EpisodicMemory = get_memory()

        if council_members:
            for m in council_members:
                self._members[m["id"]] = m["role"]

    def add_member(self, voter_id: str, role: str) -> None:
        """Add a voting member to the council."""
        self._members[voter_id] = role
        logger.info("Council member added: %s (%s)", voter_id, role)

    def remove_member(self, voter_id: str) -> None:
        """Remove a member from the council."""
        self._members.pop(voter_id, None)

    @property
    def member_count(self) -> int:
        return len(self._members)

    async def deliberate(self, proposal: Proposal) -> Verdict:
        """
        Run the deliberation process for a proposal.
        
        1. Auto-approve low-risk proposals
        2. Notify council members
        3. Simulate voting (async in production)
        4. Return verdict
        """
        # Auto-approve low-risk
        if proposal.risk_level == self.AUTO_APPROVE_BELOW:
            verdict = Verdict(
                proposal_id=proposal.id,
                approved=True,
                approval_ratio=1.0,
                summary=f"Auto-approved: {proposal.risk_level.value} risk",
            )
            await self._record_verdict(proposal, verdict)
            return verdict

        # Notify the bus
        await self._bus.emit_nowait(Event(
            event_type="council.deliberation_started",
            payload={
                "proposal_id": proposal.id,
                "agent_id": proposal.agent_id,
                "action": proposal.action,
                "risk": proposal.risk_level.value,
                "quorum": self.quorum,
            },
            source="deliberation_council",
            priority=EventPriority.HIGH if proposal.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
            else EventPriority.NORMAL,
        ))

        # Simulate voting (in production, this would be real agent deliberation)
        votes = await self._simulate_voting(proposal)

        # Count votes
        approves = sum(1 for v in votes if v.vote == VoteType.APPROVE)
        conditionals = sum(1 for v in votes if v.vote == VoteType.CONDITIONAL)
        rejects = sum(1 for v in votes if v.vote == VoteType.REJECT)
        total = len(votes)

        # Calculate approval
        # CONDITIONAL votes count as half-approve
        effective_approves = approves + (conditionals * 0.5)
        ratio = effective_approves / max(total, 1)
        has_quorum = total >= self.quorum
        approved = has_quorum and ratio >= self.approval_threshold

        verdict = Verdict(
            proposal_id=proposal.id,
            approved=approved,
            approval_ratio=ratio,
            votes=votes,
            summary=(
                f"{'APPROVED' if approved else 'REJECTED'} "
                f"({approves}✓ {rejects}✗ {conditionals}? of {total} votes, "
                f"{ratio:.0%} approval, quorum={'met' if has_quorum else 'NOT MET'})"
            ),
        )

        await self._record_verdict(proposal, verdict)
        logger.info("Council verdict: %s", verdict.summary)
        return verdict

    async def _simulate_voting(self, proposal: Proposal) -> list[Vote]:
        """
        Simulate council voting.
        
        In production, this would dispatch to real agents and await their deliberation.
        For now, uses heuristic voting based on risk level and member roles.
        """
        votes = []
        for voter_id, role in self._members.items():
            vote = self._heuristic_vote(voter_id, role, proposal)
            votes.append(vote)

        # Mark deliberation complete
        await self._bus.emit_nowait(Event(
            event_type="council.deliberation_complete",
            payload={
                "proposal_id": proposal.id,
                "approved": sum(1 for v in votes if v.vote == VoteType.APPROVE) >= self.quorum,
                "total_votes": len(votes),
            },
            source="deliberation_council",
        ))

        return votes

    def _heuristic_vote(self, voter_id: str, role: str, proposal: Proposal) -> Vote:
        """Heuristic voting logic (placeholder for real agent deliberation)."""
        # Reviewers are cautious
        if role == "reviewer":
            if proposal.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                return Vote(
                    voter_id=voter_id, voter_role=role,
                    vote=VoteType.CONDITIONAL,
                    reason="High risk — needs test verification first",
                    condition="All tests must pass before deployment",
                )
            return Vote(voter_id=voter_id, voter_role=role, vote=VoteType.APPROVE,
                       reason="Looks good from code perspective")

        # DevOps cares about cost and stability
        if role == "devops":
            if proposal.estimated_cost_usd > 10.0:
                return Vote(
                    voter_id=voter_id, voter_role=role,
                    vote=VoteType.CONDITIONAL,
                    reason=f"Cost exceeds budget: ${proposal.estimated_cost_usd:.2f}",
                    condition="Verify cost estimate with finance",
                )
            return Vote(voter_id=voter_id, voter_role=role, vote=VoteType.APPROVE,
                       reason="Infrastructure impact acceptable")

        # Architect approves well-structured proposals
        if role == "architect":
            return Vote(voter_id=voter_id, voter_role=role, vote=VoteType.APPROVE,
                       reason="Architecture-compatible change")

        # Default: cautious approval
        if proposal.risk_level == RiskLevel.CRITICAL:
            return Vote(voter_id=voter_id, voter_role=role,
                       vote=VoteType.CONDITIONAL,
                       reason="Critical risk — requires manual review",
                       condition="Manual approval required")
        return Vote(voter_id=voter_id, voter_role=role, vote=VoteType.APPROVE,
                   reason="Proceed")

    async def _record_verdict(self, proposal: Proposal, verdict: Verdict) -> None:
        """Record the verdict in episodic memory."""
        await self._memory.remember(
            agent_id="deliberation_council",
            memory_type="decision",
            content=f"Verdict on {proposal.action}: {verdict.summary}",
            metadata={
                "proposal_id": proposal.id,
                "agent_id": proposal.agent_id,
                "approved": verdict.approved,
                "approval_ratio": verdict.approval_ratio,
                "risk_level": proposal.risk_level.value,
                "votes": [{"voter": v.voter_id, "vote": v.vote.value} for v in verdict.votes],
            },
        )


# Pre-configured council with standard roles
def get_standard_council(quorum: int = 2) -> DeliberationCouncil:
    """Create a council with the standard five-role setup."""
    return DeliberationCouncil(
        quorum=quorum,
        approval_threshold=0.51,
        council_members=[
            {"id": "architect", "role": "architect"},
            {"id": "coder", "role": "coder"},
            {"id": "reviewer", "role": "reviewer"},
            {"id": "devops", "role": "devops"},
            {"id": "tester", "role": "tester"},
        ],
    )
