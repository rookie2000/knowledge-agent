# ADR-0004: Add Tracing and Evals

## Context

需要监控 Agent 行为并评估效果。

## Decision

添加完整的 Tracing 和评测体系。

## Alternatives

- 只做日志：信息不够结构化
- 使用第三方 APM：增加外部依赖

## Consequences

优点：
- 可以追踪 Agent 决策过程
- 可以用数据驱动优化
- 面试时能展示可观测性设计

缺点：
- 增加开发量
- 需要维护评测数据集
