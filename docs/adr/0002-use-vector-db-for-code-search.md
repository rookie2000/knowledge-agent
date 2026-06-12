# ADR-0002: Use ChromaDB as Vector Database

## Context

需要存储文档向量并支持语义检索。

## Decision

使用 ChromaDB 作为向量数据库。

## Alternatives

- Pinecone: 托管服务，需要付费
- Weaviate: 功能丰富但部署复杂
- Milvus: 高性能但资源消耗大

## Consequences

优点：
- 本地部署，无需外部依赖
- Python 原生支持
- 足够 MVP 阶段使用

缺点：
- 性能一般，不适合大规模数据
- 功能相对简单
