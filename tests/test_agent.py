"""
Tests for KnowledgeAgent core logic.
Covers: conversation management, agent loop, history trimming.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from src.agent import KnowledgeAgent, Message, TraceRecord


# --- Mock Anthropic response objects ---

@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = "test answer"


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    id: str = "tool_1"
    name: str = "search_knowledge"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {"query": "test"}


@dataclass
class MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class MockResponse:
    content: list = None
    usage: MockUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [MockTextBlock()]
        if self.usage is None:
            self.usage = MockUsage()


@pytest.fixture
def mock_rag():
    return MagicMock()


@pytest.fixture
def agent(mock_rag):
    with patch("src.agent.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        agent = KnowledgeAgent(mock_rag)
        agent._mock_client = mock_client
        return agent


# --- Message and TraceRecord dataclasses ---

class TestDataclasses:
    def test_message_creation(self):
        msg = Message(
            message_id="m1", conversation_id="c1",
            role="user", content="hello"
        )
        assert msg.role == "user"
        assert msg.sources == []
        assert msg.tool_calls == []

    def test_trace_record(self):
        trace = TraceRecord(trace_id="t1", user_input="question")
        assert trace.model_calls == 0
        assert trace.error is None


# --- Conversation management ---

class TestConversation:
    def test_new_conversation_created(self, agent):
        result = agent.chat("hello")
        assert "conversation_id" in result
        assert len(result["conversation_id"]) > 0

    def test_existing_conversation_reused(self, agent):
        r1 = agent.chat("first", conversation_id="conv-1")
        r2 = agent.chat("second", conversation_id="conv-1")
        assert r1["conversation_id"] == r2["conversation_id"]

    def test_get_history(self, agent):
        agent.chat("hello", conversation_id="conv-hist")
        history = agent.get_history("conv-hist")
        assert len(history) >= 2  # user + assistant
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_history_nonexistent(self, agent):
        assert agent.get_history("no-such-id") == []

    def test_empty_question_raises(self, agent):
        with pytest.raises(ValueError, match="empty"):
            agent.chat("")

    def test_whitespace_question_raises(self, agent):
        with pytest.raises(ValueError, match="empty"):
            agent.chat("   ")


# --- Agent loop ---

class TestAgentLoop:
    def test_simple_answer_no_tools(self, agent):
        """Agent returns text directly when no tool is called."""
        agent._mock_client.messages.create.return_value = MockResponse(
            content=[MockTextBlock(text="direct answer")]
        )

        result = agent.chat("simple question")
        assert result["answer"] == "direct answer"
        assert result["tool_calls"] == []

    def test_tool_call_then_answer(self, agent, mock_rag):
        """Agent calls a tool, gets results, then answers."""
        # First call: tool use; Second call: final text
        tool_response = MockResponse(
            content=[MockToolUseBlock()],
            usage=MockUsage()
        )
        text_response = MockResponse(
            content=[MockTextBlock(text="tool-based answer")],
            usage=MockUsage()
        )
        agent._mock_client.messages.create.side_effect = [
            tool_response, text_response
        ]

        # Mock tool execution
        mock_rag.search.return_value = []
        mock_rag.get_document_info.return_value = None

        result = agent.chat("search question")
        assert result["answer"] == "tool-based answer"
        assert agent._mock_client.messages.create.call_count == 2

    def test_sources_collected(self, agent, mock_rag):
        """Sources are collected from search tool results."""
        from src.rag import Chunk, Document

        tool_response = MockResponse(content=[MockToolUseBlock()])
        text_response = MockResponse(content=[MockTextBlock(text="answer")])
        agent._mock_client.messages.create.side_effect = [
            tool_response, text_response
        ]

        mock_rag.search.return_value = [
            Chunk(chunk_id="c1", doc_id="d1", content="relevant text",
                  chunk_index=0, relevance_score=0.85)
        ]
        mock_rag.get_document_info.return_value = Document(
            doc_id="d1", filename="doc.md", file_path="/doc.md",
            file_type="markdown", chunks_count=1
        )

        result = agent.chat("search question")
        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "doc.md"
        assert result["sources"][0]["relevance_score"] == 0.85

    def test_max_tool_calls_limit(self, agent):
        """Agent stops after MAX_TOOL_CALLS iterations."""
        tool_response = MockResponse(content=[MockToolUseBlock()])
        agent._mock_client.messages.create.return_value = tool_response
        agent.rag.search.return_value = []
        agent.rag.get_document_info.return_value = None

        result = agent.chat("infinite loop question")
        # MAX_TOOL_CALLS is 5, so 5+1 = 6 calls max (5 tool rounds + 1 final)
        assert agent._mock_client.messages.create.call_count <= 6


# --- History trimming ---

class TestHistoryTrimming:
    def test_trim_when_exceeds_max(self, agent):
        """Conversation is trimmed when exceeding MAX_CONVERSATION_HISTORY."""
        agent._mock_client.messages.create.return_value = MockResponse(
            content=[MockTextBlock(text="reply")]
        )

        # MAX_CONVERSATION_HISTORY is 10, so 21 messages should trigger trim
        for i in range(21):
            agent.chat(f"message {i}", conversation_id="trim-test")

        history = agent.get_history("trim-test")
        # Should be capped at 20 messages (10 pairs)
        assert len(history) <= 20
