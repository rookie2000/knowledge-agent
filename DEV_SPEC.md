# 开发规范文档 (DEV_SPEC)

## 1. API 接口设计

### 1.1 文档管理

```
POST /api/documents/upload
  - Content-Type: multipart/form-data
  - 参数: file (文件), chunk_size (可选, 默认1000)
  - 返回: { "doc_id": "uuid", "filename": "xxx.pdf", "chunks_count": 42, "status": "indexed" }
  - 错误: 400 (格式不支持), 413 (文件过大), 500 (处理失败)

GET /api/documents
  - 返回: { "documents": [{ "doc_id", "filename", "chunks_count", "created_at" }] }

DELETE /api/documents/{doc_id}
  - 返回: { "status": "deleted" }
  - 错误: 404 (文档不存在)
```

### 1.2 问答接口

```
POST /api/chat
  - Body: { "question": "什么是RAG?", "conversation_id": "uuid(可选)" }
  - 返回: {
      "answer": "RAG是...",
      "sources": [
        { "doc_id": "uuid", "filename": "rag_intro.pdf", "chunk_text": "...", "relevance_score": 0.92 }
      ],
      "tool_calls": [
        { "tool": "search_knowledge", "input": {...}, "output": {...} }
      ],
      "conversation_id": "uuid"
    }
  - 错误: 400 (问题为空), 500 (LLM调用失败)

GET /api/chat/{conversation_id}/history
  - 返回: { "messages": [{ "role", "content", "timestamp" }] }
```

### 1.3 健康检查

```
GET /api/health
  - 返回: { "status": "ok", "chroma_connected": true, "documents_count": 5 }
```

## 2. 数据模型

### 2.1 Document (文档)

```python
class Document:
    doc_id: str          # UUID
    filename: str        # 原始文件名
    file_path: str       # 存储路径
    file_type: str       # "pdf" | "markdown"
    chunks_count: int    # 分块数量
    created_at: datetime
    metadata: dict       # 扩展字段
```

### 2.2 Chunk (文档分块)

```python
class Chunk:
    chunk_id: str        # UUID
    doc_id: str          # 关联文档
    content: str         # 分块文本
    embedding: list[float]  # 向量 (ChromaDB 内部管理)
    chunk_index: int     # 在文档中的位置
    metadata: dict       # { "page": 1, "section": "引言" }
```

### 2.3 Message (对话消息)

```python
class Message:
    message_id: str      # UUID
    conversation_id: str # 会话ID
    role: str            # "user" | "assistant"
    content: str         # 消息内容
    sources: list        # 引用的文档片段 (仅 assistant)
    tool_calls: list     # 调用的工具 (仅 assistant)
    timestamp: datetime
```

## 3. 模块职责

### 3.1 src/config.py

- 读取 .env 配置
- 提供类型安全的配置访问
- 验证必要配置项存在

### 3.2 src/rag.py

```python
class RAGManager:
    def __init__(self):
        """初始化 ChromaDB 客户端和 embedding 函数"""

    def add_document(self, file_path: str, chunk_size: int = 1000) -> Document:
        """处理文档并建立索引
        流程: 读取文件 → 分块 → 生成 embedding → 存入 ChromaDB
        """

    def search(self, query: str, top_k: int = 5) -> list[Chunk]:
        """语义检索，返回最相关的 chunk"""

    def delete_document(self, doc_id: str) -> bool:
        """删除文档及其所有 chunk"""

    def get_document_info(self, doc_id: str) -> Document:
        """获取文档元信息"""
```

### 3.3 src/tools.py

```python
# 工具定义 - 符合 Claude Tool Use 规范
TOOLS = [
    {
        "name": "search_knowledge",
        "description": "搜索知识库中的相关文档片段",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": { "type": "string", "description": "搜索查询" },
                "top_k": { "type": "integer", "description": "返回结果数量", "default": 5 }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_document_info",
        "description": "获取指定文档的详细信息",
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_id": { "type": "string", "description": "文档ID" }
            },
            "required": ["doc_id"]
        }
    }
]

def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """执行工具并返回结果"""
```

### 3.4 src/agent.py

```python
class KnowledgeAgent:
    def __init__(self, rag_manager: RAGManager):
        """初始化 Agent，注入 RAG 依赖"""

    def chat(self, question: str, conversation_id: str = None) -> dict:
        """处理用户问题
        流程:
        1. 构建消息（含历史上下文）
        2. 调用 Claude API，传入工具定义
        3. 如果 Claude 返回 tool_use → 执行工具 → 将结果发回 Claude
        4. 循环直到 Claude 返回最终回答
        5. 保存对话历史
        """
```

### 3.5 src/api.py

- FastAPI 路由定义
- 请求验证
- 异常处理
- 依赖注入

## 4. 分块策略

```
分块方式: 按段落 + 重叠窗口
- chunk_size: 1000 字符 (可配置)
- chunk_overlap: 200 字符 (上下文重叠)
- 分隔符: \n\n (段落) → \n (句子) → 空格 (词)

特殊处理:
- PDF: 按页分块，保留页码信息
- Markdown: 按标题分块，保留层级信息
```

## 5. 错误处理策略

```python
# 自定义异常
class AgentError(Exception): pass
class DocumentNotFoundError(AgentError): pass
class UnsupportedFileTypeError(AgentError): fail
class LLMCallError(AgentError): pass
class VectorDBError(AgentError): pass

# 统一错误响应格式
{
    "error": {
        "code": "DOCUMENT_NOT_FOUND",
        "message": "文档不存在",
        "details": { "doc_id": "xxx" }
    }
}
```

## 6. 技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| 向量数据库 | ChromaDB | 本地部署、无需外部依赖、Python 原生支持 |
| Embedding 模型 | ChromaDB 默认 (all-MiniLM-L6-v2) | 够用、免费、本地运行 |
| 分块策略 | 按段落 + 重叠 | 保持语义完整性，重叠避免上下文断裂 |
| Agent 循环 | while True + tool_use | 符合 Claude Tool Use 规范，支持多步推理 |
| 对话存储 | 内存 dict | MVP 阶段够用，后续可换 Redis/DB |
