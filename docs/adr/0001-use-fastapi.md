# ADR-0001: Use FastAPI as API Layer

## Context

需要构建一个高性能的 API 服务来支持 Knowledge Agent。

## Decision

使用 FastAPI 作为 API 层。

## Alternatives

- Flask: 同步框架，性能一般
- Django: 太重，不适合轻量级 API
- Node.js Express: 需要切换语言栈

## Consequences

优点：
- 原生支持异步，性能好
- 自动生成 OpenAPI 文档
- 类型提示支持好

缺点：
- 内置权限系统简单，需要自己设计
- 生态不如 Django 丰富
