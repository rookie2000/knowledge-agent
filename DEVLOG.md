# 开发日志

## 2026-06-10

### 完成

- 项目结构设计
- 核心文档编写：
  - README.md
  - PRD.md
  - ARCHITECTURE.md
  - AGENT_DESIGN.md
  - TOOLS.md
  - EVAL_PLAN.md
  - SECURITY.md
  - ERROR_HANDLING.md
  - DEV_SPEC.md
  - DEMO.md
  - INTERVIEW_QA.md
  - ROADMAP.md
- Prompt 版本管理：
  - prompts/system_prompt.md
  - prompts/CHANGELOG.md
- 架构决策记录：
  - docs/adr/0001-use-fastapi.md
  - docs/adr/0002-use-vector-db-for-code-search.md
  - docs/adr/0003-why-single-agent-first.md
  - docs/adr/0004-add-tracing-and-evals.md

### 问题

- 暂无

### 代码实现

- requirements.txt — 依赖声明
- src/__init__.py — 包初始化
- src/config.py — 配置管理
- src/rag.py — RAG 检索模块 (Document/Chunk 数据模型, RAGManager)
- src/tools.py — 工具定义与执行 (search_knowledge, get_document_info)
- src/agent.py — Agent 核心逻辑 (Agent Loop, 多轮对话)
- src/api.py — FastAPI 路由 (所有 API 接口)
- main.py — 入口文件

### 下一步

- 编写测试
- 准备测试文档进行验证
- 优化 Prompt
