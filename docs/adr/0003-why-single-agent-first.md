# ADR-0003: Why Single Agent First

## Context

需要设计 Agent 架构，选择单 Agent 还是多 Agent。

## Decision

MVP 阶段使用单 Agent 架构。

## Alternatives

- 多 Agent (Planner + Executor + Critic): 功能更强大，但复杂度高
- Workflow: 固定流程，灵活性差

## Consequences

优点：
- 实现简单，快速验证
- 调试容易
- 面试时能清晰解释

缺点：
- 复杂任务处理能力有限
- 后续需要重构为多 Agent

## Future Plan

后续可以扩展为：
- Planner Agent: 规划执行步骤
- Executor Agent: 执行具体任务
- Critic Agent: 评估回答质量
