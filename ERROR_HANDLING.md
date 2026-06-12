# 失败处理策略

## 1. 错误分类

### 1.1 工具调用错误

| 错误类型 | 错误码 | 处理策略 |
|----------|--------|----------|
| 工具不存在 | TOOL_NOT_FOUND | 返回错误，记录 Trace |
| 工具超时 | TOOL_TIMEOUT | 重试 1 次，失败返回错误 |
| 工具执行异常 | TOOL_EXECUTION_ERROR | 记录 Trace，返回通用错误 |
| 返回结果为空 | EMPTY_RESULT | 尝试不同查询，仍失败告知用户 |
| 参数错误 | INVALID_INPUT | 返回参数错误提示 |

### 1.2 LLM 调用错误

| 错误类型 | 错误码 | 处理策略 |
|----------|--------|----------|
| API 调用失败 | LLM_API_ERROR | 重试 1 次，失败返回预设回答 |
| Token 超限 | TOKEN_LIMIT_EXCEEDED | 截断上下文，重新调用 |
| 响应格式错误 | INVALID_RESPONSE | 重试 1 次，失败返回错误 |
| 内容过滤 | CONTENT_FILTERED | 返回安全提示 |

### 1.3 数据库错误

| 错误类型 | 错误码 | 处理策略 |
|----------|--------|----------|
| 连接失败 | DB_CONNECTION_ERROR | 返回系统错误，记录日志 |
| 查询超时 | DB_TIMEOUT | 重试 1 次，失败返回错误 |
| 数据损坏 | DB_CORRUPTION | 返回系统错误，告警 |

### 1.4 用户输入错误

| 错误类型 | 错误码 | 处理策略 |
|----------|--------|----------|
| 输入为空 | EMPTY_INPUT | 返回提示信息 |
| 输入过长 | INPUT_TOO_LONG | 截断并提示 |
| 格式错误 | INVALID_FORMAT | 返回格式提示 |

## 2. 错误处理流程

### 2.1 通用错误处理

```python
def handle_error(error: Exception, context: dict) -> dict:
    """通用错误处理"""
    # 1. 记录 Trace
    trace.log_error(error, context)

    # 2. 判断错误类型
    if isinstance(error, ToolError):
        return handle_tool_error(error)
    elif isinstance(error, LLMError):
        return handle_llm_error(error)
    elif isinstance(error, DatabaseError):
        return handle_db_error(error)
    else:
        return handle_unknown_error(error)
```

### 2.2 工具调用错误处理

```python
def handle_tool_error(error: ToolError) -> dict:
    """工具调用错误处理"""
    if error.code == "TOOL_TIMEOUT":
        # 重试 1 次
        try:
            return retry_tool_call()
        except ToolError:
            return {
                "success": False,
                "error": "工具调用超时，请稍后重试"
            }

    elif error.code == "EMPTY_RESULT":
        # 尝试不同查询
        try:
            return retry_with_different_query()
        except ToolError:
            return {
                "success": False,
                "error": "未找到相关内容"
            }

    else:
        return {
            "success": False,
            "error": "工具调用失败，请稍后重试"
        }
```

### 2.3 LLM 调用错误处理

```python
def handle_llm_error(error: LLMError) -> dict:
    """LLM 调用错误处理"""
    if error.code == "TOKEN_LIMIT_EXCEEDED":
        # 截断上下文
        truncated_messages = truncate_messages(messages)
        return retry_llm_call(truncated_messages)

    elif error.code == "LLM_API_ERROR":
        # 重试 1 次
        try:
            return retry_llm_call()
        except LLMError:
            return {
                "success": False,
                "error": "服务暂时不可用，请稍后重试"
            }

    else:
        return {
            "success": False,
            "error": "回答生成失败，请稍后重试"
        }
```

## 3. 重试策略

### 3.1 重试配置

```python
RETRY_CONFIG = {
    "tool_timeout": {
        "max_retries": 1,
        "backoff_factor": 1
    },
    "llm_api_error": {
        "max_retries": 1,
        "backoff_factor": 2
    },
    "db_timeout": {
        "max_retries": 1,
        "backoff_factor": 1
    }
}
```

### 3.2 重试实现

```python
def retry_with_backoff(func, max_retries=1, backoff_factor=1):
    """带退避的重试"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(backoff_factor * (2 ** attempt))
```

## 4. 降级策略

### 4.1 工具调用失败降级

```
主策略：调用 search_knowledge
    ↓ 失败
降级策略 1：尝试不同查询词
    ↓ 失败
降级策略 2：返回通用回答 + 说明
    ↓ 失败
最终策略：返回错误提示
```

### 4.2 LLM 调用失败降级

```
主策略：调用 Claude API
    ↓ 失败
降级策略 1：重试 1 次
    ↓ 失败
降级策略 2：返回预设回答模板
    ↓ 失败
最终策略：返回系统错误提示
```

## 5. 错误响应格式

### 5.1 API 错误响应

```json
{
    "error": {
        "code": "TOOL_TIMEOUT",
        "message": "工具调用超时",
        "details": {
            "tool": "search_knowledge",
            "timeout": 30
        },
        "suggestion": "请稍后重试"
    }
}
```

### 5.2 用户友好错误消息

```python
USER_FRIENDLY_MESSAGES = {
    "TOOL_TIMEOUT": "搜索超时，请稍后重试",
    "EMPTY_RESULT": "未找到相关内容，请尝试其他问题",
    "LLM_API_ERROR": "服务暂时不可用，请稍后重试",
    "TOKEN_LIMIT_EXCEEDED": "问题太复杂，请简化后重试",
    "EMPTY_INPUT": "请输入问题",
    "INPUT_TOO_LONG": "问题过长，请简化后重试"
}
```

## 6. 错误监控

### 6.1 错误统计

```python
class ErrorMetrics:
    total_requests: int
    error_count: int
    error_rate: float
    error_by_type: dict[str, int]
    retry_count: int
    fallback_count: int
```

### 6.2 错误告警

- 错误率 > 10% → 告警
- 连续 5 次相同错误 → 告警
- 工具调用失败率 > 20% → 告警

## 7. 错误恢复

### 7.1 自动恢复

```python
def auto_recovery(error: Exception) -> bool:
    """尝试自动恢复"""
    if isinstance(error, DatabaseConnectionError):
        # 尝试重新连接
        return reconnect_database()

    if isinstance(error, ToolTimeoutError):
        # 尝试重启工具
        return restart_tool()

    return False
```

### 7.2 手动恢复

- 数据库损坏 → 手动重建索引
- 工具配置错误 → 检查配置文件
- API Key 过期 → 更新环境变量

## 8. 错误日志

### 8.1 日志格式

```json
{
    "timestamp": "2026-06-10T10:30:00Z",
    "level": "ERROR",
    "trace_id": "trace_abc123",
    "error": {
        "type": "ToolTimeoutError",
        "message": "工具调用超时",
        "stack": "..."
    },
    "context": {
        "user_input": "什么是RAG?",
        "tool": "search_knowledge",
        "attempt": 2
    }
}
```

### 8.2 日志分析

```bash
# 查看错误统计
grep -c "ERROR" logs/app.log

# 查看特定错误
grep "TOOL_TIMEOUT" logs/app.log

# 查看错误趋势
awk '/ERROR/{print $1}' logs/app.log | sort | uniq -c
```
