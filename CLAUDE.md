# Knowledge Agent

个人知识库问答 Agent - 基于 RAG + Tool Use 的智能文档助手

## 技术栈

- Python 3.11+
- Claude API (anthropic SDK)
- ChromaDB (向量数据库，本地部署)
- FastAPI (Web API)
- Uvicorn (ASGI 服务器)

## 项目结构

```
knowledge-agent/
├── src/
│   ├── agent.py          # Agent 核心逻辑
│   ├── rag.py            # RAG 检索模块
│   ├── tools.py          # 工具定义
│   ├── api.py            # FastAPI 路由
│   └── config.py         # 配置管理
├── data/                 # 文档存储目录
├── tests/                # 测试文件
├── requirements.txt
├── .env.example          # 环境变量模板
└── main.py               # 入口文件
```

## 开发规范

- 代码注释用英文
- 函数和变量用 snake_case
- 类名用 PascalCase
- 关键逻辑必须有类型注解
- 错误处理要明确，不吞异常

## 运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py

# 运行测试
pytest tests/
```

## 关键约束

- API Key 必须从环境变量读取，禁止硬编码
- 向量数据库使用本地存储，不依赖云服务
- 单次对话上下文不超过 4000 tokens
- 文档处理支持 PDF 和 Markdown 格式
- 响应时间目标：简单问题 < 2s，复杂问题 < 5s
