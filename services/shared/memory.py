"""
Episodic Memory — persistent agent memory with semantic search.

Two-tier storage:
1. Supabase PostgreSQL — raw event log, decision records
2. ChromaDB — vector embeddings for semantic recall

Agents query their own history: "Have I seen this error before?"
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single record in episodic memory."""

    id: str
    agent_id: str
    memory_type: str  # "decision", "error", "observation", "action"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    project_id: str | None = None


class EpisodicMemory:
    """
    Agent memory with semantic recall.

    Usage:
        mem = EpisodicMemory()
        await mem.remember(agent_id="autofix", memory_type="error",
                           content="NullPointerException in auth.ts:42",
                           metadata={"stack_trace": "..."})

        similar = await mem.recall("NullPointerException in auth", limit=5)
    """

    def __init__(
        self,
        supabase_url: str = "",
        supabase_key: str = "",
        chroma_host: str = "localhost",
        chroma_port: int = 8001,
    ):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY", "")
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self._entries: dict[str, MemoryEntry] = {}  # In-memory fallback
        self._chroma = None

    @property
    def is_connected(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    async def remember(
        self,
        agent_id: str,
        memory_type: str,
        content: str,
        metadata: dict | None = None,
        project_id: str | None = None,
    ) -> MemoryEntry:
        """Store a new memory."""
        import uuid

        entry = MemoryEntry(
            id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            project_id=project_id,
        )

        # Store in-memory (always works)
        self._entries[entry.id] = entry

        # Try storing in ChromaDB for semantic search
        try:
            await self._index_in_chroma(entry)
        except Exception as e:
            logger.warning("ChromaDB index failed (will use in-memory): %s", e)

        logger.debug("Memory stored: %s/%s → %s", agent_id, memory_type, entry.id)
        return entry

    async def recall(
        self,
        query: str,
        agent_id: str | None = None,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Semantic recall — find similar past memories.

        Falls back to keyword matching when ChromaDB is unavailable.
        """
        # Try ChromaDB semantic search
        if self._chroma:
            try:
                return await self._search_chroma(query, agent_id, memory_type, limit)
            except Exception as e:
                logger.warning("ChromaDB search failed, using fallback: %s", e)

        # Fallback: simple keyword match against in-memory entries
        results = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if agent_id and entry.agent_id != agent_id:
                continue
            if memory_type and entry.memory_type != memory_type:
                continue
            if query_lower in entry.content.lower():
                results.append(entry)
        return sorted(results, key=lambda e: e.created_at, reverse=True)[:limit]

    async def get_by_agent(
        self, agent_id: str, memory_type: str | None = None, limit: int = 50
    ) -> list[MemoryEntry]:
        """Get all memories for a specific agent."""
        entries = [
            e
            for e in self._entries.values()
            if e.agent_id == agent_id
            and (memory_type is None or e.memory_type == memory_type)
        ]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)[:limit]

    async def forget(self, entry_id: str) -> bool:
        """Delete a memory."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    async def _index_in_chroma(self, entry: MemoryEntry) -> None:
        """Index a memory in ChromaDB for semantic search."""
        if not self._chroma:
            try:
                import chromadb

                self._chroma = chromadb.HttpClient(
                    host=self.chroma_host, port=self.chroma_port
                )
                # Ensure collection exists
                try:
                    self._chroma.get_collection("agent_memory")
                except Exception:
                    self._chroma.create_collection("agent_memory")
            except ImportError:
                logger.debug("chromadb not installed — semantic search disabled")
                return
            except Exception as e:
                logger.debug("ChromaDB not available: %s", e)
                self._chroma = None
                return

        try:
            collection = self._chroma.get_collection("agent_memory")
            collection.add(
                ids=[entry.id],
                documents=[entry.content],
                metadatas=[
                    {
                        "agent_id": entry.agent_id,
                        "memory_type": entry.memory_type,
                        "project_id": entry.project_id or "",
                        "created_at": entry.created_at,
                    }
                ],
            )
        except Exception as e:
            logger.warning("ChromaDB add failed: %s", e)

    async def _search_chroma(
        self, query: str, agent_id: str | None, memory_type: str | None, limit: int
    ) -> list[MemoryEntry]:
        """Semantic search via ChromaDB."""
        if not self._chroma:
            return []

        where = {}
        if agent_id:
            where["agent_id"] = agent_id
        if memory_type:
            where["memory_type"] = memory_type

        collection = self._chroma.get_collection("agent_memory")
        results = collection.query(
            query_texts=[query],
            n_results=limit,
            where=where if where else None,
        )

        entries = []
        if results.get("ids") and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                entry = self._entries.get(doc_id)
                if not entry:
                    entry = MemoryEntry(
                        id=doc_id,
                        agent_id=results["metadatas"][0][i].get("agent_id", ""),
                        memory_type=results["metadatas"][0][i].get("memory_type", ""),
                        content=results["documents"][0][i]
                        if results.get("documents")
                        else "",
                    )
                entries.append(entry)
        return entries

    def stats(self) -> dict:
        """Return memory statistics."""
        types = {}
        agents = {}
        for entry in self._entries.values():
            types[entry.memory_type] = types.get(entry.memory_type, 0) + 1
            agents[entry.agent_id] = agents.get(entry.agent_id, 0) + 1
        return {
            "total_entries": len(self._entries),
            "by_type": types,
            "by_agent": agents,
            "chromadb_connected": self._chroma is not None,
        }


# Global singleton
_memory: EpisodicMemory | None = None


def get_memory() -> EpisodicMemory:
    global _memory
    if _memory is None:
        _memory = EpisodicMemory()
    return _memory
