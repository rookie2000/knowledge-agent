# Roadmap

## v1.0 - MVP (当前)

- [x] 项目结构设计
- [x] 文档设计 (PRD, ARCHITECTURE, AGENT_DESIGN 等)
- [x] 文档上传与索引
- [x] 基础问答功能
- [x] 工具调用 (search_knowledge, get_document_info)
- [x] 多轮对话
- [x] 基础 Trace 记录
- [x] API 接口
- [x] 单元测试 (39 tests, mock ChromaDB + Anthropic API)

## v1.0 补充 - 面试前必做

按优先级排序，直接影响面试表现：

### P0 - 必须有

- [ ] **Dockerfile** — 面试官可能问"怎么部署"，一个 `docker build && docker run` 能跑通
- [ ] **Makefile** — 整合 `make test`、`make run`、`make lint`，显得工程化
- [ ] **API 集成测试** — 用 httpx + TestClient 测试 FastAPI 路由，目前只测了模块级别
- [ ] **pyproject.toml** — 现代 Python 项目标配，替代纯 requirements.txt

### P1 - 加分项

- [ ] **API 调用重试 / 限流** — agent.py 里 Anthropic 调用无 retry，面试时被问"API 失败怎么办"会尴尬
  - 方案：`tenacity` 库 + 指数退避，改动 < 20 行
- [ ] **流式响应 (Streaming)** — Agent 场景下流式输出体验好，Claude API 支持 `stream=True`
  - 涉及：agent.py 返回 generator，api.py 用 SSE
- [ ] **对话持久化** — 当前 `_conversations` 是内存 dict，重启丢失
  - 方案：SQLite 存储 messages 表，或简单 JSON 文件
- [ ] **evals/ 填充** — 目录已建但内容空，需要实际的评测数据集和评分脚本

### P2 - 有时间再做

- [ ] **scripts/ingest.py** — 命令行批量导入文档，方便演示端到端流程
- [ ] **PyPDF2 -> pypdf** — PyPDF2 已 deprecated，有 deprecation warning
- [ ] **日志标准化** — 用 `logging` 模块替代 `print`，方便调试和生产部署

## v1.1 - 完善

- [ ] Prompt Injection 防护
- [ ] 错误处理完善
- [ ] 评测体系建立
- [ ] 性能优化

## v2.0 - 扩展

- [ ] Web UI 界面
- [ ] 更多文档格式支持 (Word, 网页)
- [ ] 联网搜索能力
- [ ] 对话历史持久化

## v3.0 - 多 Agent

- [ ] Planner Agent
- [ ] Executor Agent
- [ ] Critic Agent
- [ ] Agent 协作机制

## v4.0 - 企业级

- [ ] 分布式部署
- [ ] 权限管理
- [ ] 多租户支持
- [ ] 完善监控告警
