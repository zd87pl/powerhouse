# ADR-010: Vector Database Evaluation

## Status
Accepted — ChromaDB selected

## Context
Powerhouse needs a vector database for semantic search across code, documentation, arXiv papers, and decision records.

## Evaluation Criteria
| Criterion | Weight | ChromaDB | Qdrant | Weaviate | Pinecone |
|-----------|--------|----------|--------|----------|----------|
| Self-hosted | High | ✅ | ✅ | ✅ | ❌ |
| Multi-tenancy | High | ⚠️ (proxy) | ⚠️ (namespaces) | ✅ | ✅ |
| Embedding models | Medium | ✅ ONNX | ✅ | ✅ | ✅ |
| Performance | Medium | Good | Excellent | Good | Excellent |
| Ecosystem | Medium | Growing | Growing | Mature | Mature |
| Cost | High | Free | Free | Free | $$$ |

## Decision
**ChromaDB** for MVP, with a migration path to Qdrant if multi-tenancy needs exceed proxy capabilities.

## Implementation
- ChromaDB server: `http://localhost:8001`
- Data directory: `/data/powerhouse/chroma-data/`
- Each tenant gets prefixed collections: `tenant_{id}_codebase`, `tenant_{id}_wiki`
- Access enforced via proxy layer (not native ChromaDB auth)

## Migration Path
If ChromaDB proxy proves insufficient at scale:
1. Export all collections to Parquet
2. Import into Qdrant with native multi-tenant collections
3. Update proxy to speak Qdrant API

## Consequences
- **Positive:** Free, self-hosted, good Python integration
- **Negative:** Multi-tenancy requires custom proxy
- **Mitigation:** Build proxy from day one; abstraction layer makes migration transparent

## Rejected Alternatives
- Pinecone: hosted-only, expensive at scale, vendor lock-in
- Weaviate: heavier resource usage, GraphQL query complexity
- Qdrant: excellent but ChromaDB ecosystem more aligned with Python/agent workflows
