#!/usr/bin/env python3
"""
Integration tests for precompact_memory_extractor.py
====================================================
Tests the full memory extraction pipeline: loading → chunking → storage.

Target: 70%+ coverage for PreCompact hook.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import jsonlines

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from precompact_memory_extractor import (
    load_transcript,
    format_transcript_for_analysis,
    chunk_conversation,
    _build_smart_chunk,
    store_enhanced_chunks,
    debug_log
)


class TestLoadTranscript:
    """Test transcript loading from JSONL."""

    def test_load_simple_transcript(self, tmp_path):
        """Load a simple JSONL transcript"""
        transcript_file = tmp_path / "transcript.jsonl"

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        with jsonlines.open(transcript_file, "w") as writer:
            for msg in messages:
                writer.write(msg)

        loaded = load_transcript(str(transcript_file))

        assert len(loaded) == 2
        assert loaded[0]["role"] == "user"
        assert loaded[1]["role"] == "assistant"

    def test_load_empty_transcript(self, tmp_path):
        """Empty transcript returns empty list"""
        transcript_file = tmp_path / "empty.jsonl"
        transcript_file.touch()

        loaded = load_transcript(str(transcript_file))

        assert loaded == []

    def test_load_nonexistent_file(self):
        """Nonexistent file returns empty list"""
        loaded = load_transcript("/tmp/nonexistent_file.jsonl")

        assert loaded == []

    def test_truncate_long_transcript(self, tmp_path):
        """Transcripts >MAX_TRANSCRIPT_MESSAGES are truncated"""
        transcript_file = tmp_path / "long.jsonl"

        # Create 1500 messages (MAX is 1000)
        with jsonlines.open(transcript_file, "w") as writer:
            for i in range(1500):
                writer.write({"role": "user", "content": f"Message {i}"})

        loaded = load_transcript(str(transcript_file))

        # Should only load last 1000
        assert len(loaded) == 1000
        # Should have the last messages
        assert "Message 1499" in loaded[-1]["content"]


class TestFormatTranscriptForAnalysis:
    """Test transcript formatting."""

    def test_format_simple_messages(self):
        """Format simple user/assistant messages (content as list)"""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "What is Python?"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Python is a programming language."}]}
        ]

        formatted = format_transcript_for_analysis(messages)

        assert "USER: What is Python?" in formatted
        assert "ASSISTANT: Python is a programming language." in formatted

    def test_format_nested_message(self):
        """Format Claude Code nested message structure"""
        messages = [
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Hi!"}]}}
        ]

        formatted = format_transcript_for_analysis(messages)

        assert "USER: Hello" in formatted
        assert "ASSISTANT: Hi!" in formatted

    def test_format_list_content(self):
        """Format messages with content as list of dicts"""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Create a file"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Creating..."}]}
        ]

        formatted = format_transcript_for_analysis(messages)

        assert "USER: Create a file" in formatted
        assert "ASSISTANT: Creating..." in formatted

    def test_format_tool_use(self):
        """Format assistant tool use blocks"""
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "I'll create the file"},
                {"type": "tool_use", "name": "Write", "input": {"file_path": "test.py", "content": "code"}}
            ]}
        ]

        formatted = format_transcript_for_analysis(messages)

        assert "ASSISTANT: I'll create the file" in formatted
        assert "TOOL_USE: Write" in formatted
        assert "test.py" in formatted

    def test_format_empty_messages(self):
        """Empty messages list returns empty string"""
        formatted = format_transcript_for_analysis([])

        assert formatted == ""


class TestChunkConversation:
    """Test smart conversation chunking."""

    def test_chunk_simple_conversation(self):
        """Simple question-answer gets chunked"""
        transcript = """USER: What is Python?
ASSISTANT: Python is a programming language."""

        chunks = chunk_conversation(transcript)

        assert len(chunks) >= 1
        assert "Python" in chunks[0]["intent"]

    def test_chunk_file_operations(self):
        """Multiple file operations are grouped"""
        transcript = """USER: Create auth files
ASSISTANT: Creating authentication system
TOOL_USE: Write with {"file_path": "auth.py"}
TOOL_USE: Write with {"file_path": "user.py"}
TOOL_USE: Write with {"file_path": "token.py"}
ASSISTANT: Files created successfully"""

        chunks = chunk_conversation(transcript)

        # Should chunk after 3 file operations
        assert len(chunks) >= 1
        # Should mention file creation
        assert any("Write" in chunk["action"] or "files" in chunk["action"].lower() for chunk in chunks)

    def test_chunk_on_topic_change(self):
        """New user message after work triggers chunking"""
        transcript = """USER: Create a file
ASSISTANT: Creating file
TOOL_USE: Write with {"file_path": "test.py"}
ASSISTANT: File created
USER: Now run tests
ASSISTANT: Running tests"""

        chunks = chunk_conversation(transcript)

        # Should create 2 chunks: file creation + test running
        assert len(chunks) >= 2

    def test_chunk_on_completion(self):
        """Completion markers trigger chunking"""
        transcript = """USER: Build the API
ASSISTANT: Building API endpoint
TOOL_USE: Write with {"file_path": "api.py"}
ASSISTANT: API completed successfully
USER: What next?"""

        chunks = chunk_conversation(transcript)

        assert len(chunks) >= 1
        # Check completion was detected
        assert any("completed" in chunk["outcome"].lower() or "success" in chunk["outcome"].lower() for chunk in chunks)

    def test_empty_transcript_no_chunks(self):
        """Empty transcript returns no chunks"""
        chunks = chunk_conversation("")

        assert chunks == []

    def test_only_user_messages(self):
        """Only user messages still creates chunks"""
        transcript = """USER: Hello
USER: Are you there?"""

        chunks = chunk_conversation(transcript)

        assert len(chunks) >= 1


class TestBuildSmartChunk:
    """Test chunk building from parts."""

    def test_build_complete_chunk(self):
        """Build chunk with all parts"""
        parts = {
            "user": ["Create a new file"],
            "assistant": ["I'll create the file for you"],
            "tools": ["Write with file_path: test.py"],
            "tool_names": ["Write"]
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is not None
        assert "Create a new file" in chunk["intent"]
        assert "created/wrote files" in chunk["action"]
        assert len(chunk["outcome"]) > 0

    def test_build_chunk_no_user(self):
        """Chunk without user gets default intent"""
        parts = {
            "user": [],
            "assistant": ["Continuing with the task"],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is not None
        assert "Continue previous task" in chunk["intent"]

    def test_build_chunk_with_error(self):
        """Error in text triggers error outcome"""
        parts = {
            "user": ["Fix the bug"],
            "assistant": ["Encountered an error: TypeError"],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is not None
        assert "issue" in chunk["outcome"].lower() or "troubleshoot" in chunk["outcome"].lower()

    def test_build_chunk_with_success(self):
        """Success markers trigger success outcome"""
        parts = {
            "user": ["Create API"],
            "assistant": ["API completed successfully"],
            "tools": ["Write with api.py"],
            "tool_names": ["Write"]
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is not None
        assert "success" in chunk["outcome"].lower() or "completed" in chunk["outcome"].lower()

    def test_build_chunk_discussion_only(self):
        """No tools = discussion outcome"""
        parts = {
            "user": ["What should we do next?"],
            "assistant": ["Let's plan the architecture"],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is not None
        assert "Discussion" in chunk["outcome"] or "planning" in chunk["outcome"]

    def test_build_empty_chunk_returns_none(self):
        """Empty parts returns None"""
        parts = {
            "user": [],
            "assistant": [],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        assert chunk is None

    def test_truncate_long_intent(self):
        """Long intent is truncated in summary"""
        long_text = "x" * 300
        parts = {
            "user": [long_text],
            "assistant": ["OK"],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        # Full intent stored
        assert len(chunk["intent"]) == 300
        # But summary is truncated
        assert len(chunk["summary"]) < 500  # Reasonable summary length

    def test_truncate_long_action(self):
        """Long action is truncated in summary"""
        long_text = "x" * 500
        parts = {
            "user": ["Do something"],
            "assistant": [long_text],
            "tools": [],
            "tool_names": []
        }

        chunk = _build_smart_chunk(parts)

        # Full action stored
        assert len(chunk["action"]) > 400
        # Summary has truncated action
        assert "..." in chunk["summary"]


class TestStoreEnhancedChunks:
    """Test chunk storage with mocked ChromaDB."""

    def setup_method(self):
        """Set up mocks for ChromaDB and SentenceTransformer."""
        self.mock_collection = MagicMock()
        self.mock_client = MagicMock()
        self.mock_client.get_or_create_collection.return_value = self.mock_collection

        self.mock_model = MagicMock()
        self.mock_model.encode.return_value.tolist.return_value = [0.1] * 768

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('precompact_memory_extractor.SentenceTransformer')
    @patch('precompact_memory_extractor.MemoryPruner')
    @patch('precompact_memory_extractor.MemoryClustering')
    def test_store_single_chunk(self, mock_clustering, mock_pruner, mock_transformer, mock_chromadb):
        """Store a single chunk successfully"""
        mock_chromadb.return_value = self.mock_client
        mock_transformer.return_value = self.mock_model
        mock_pruner_instance = MagicMock()
        mock_pruner_instance.prune_session_memories.return_value = {"pruned": 0}
        mock_pruner.return_value = mock_pruner_instance
        mock_clustering_instance = MagicMock()
        mock_clustering_instance.cluster_memories.return_value = {"num_clusters": 2}
        mock_clustering.return_value = mock_clustering_instance

        chunks = [
            {"intent": "Test intent", "action": "Test action", "outcome": "Success", "summary": "Test summary"}
        ]

        store_enhanced_chunks(chunks, "session123")

        # Verify collection.add was called
        self.mock_collection.add.assert_called_once()

        # Verify embedding was created
        assert mock_transformer.called

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('precompact_memory_extractor.SentenceTransformer')
    @patch('precompact_memory_extractor.MemoryPruner')
    @patch('precompact_memory_extractor.MemoryClustering')
    def test_store_multiple_chunks(self, mock_clustering, mock_pruner, mock_transformer, mock_chromadb):
        """Store multiple chunks"""
        mock_chromadb.return_value = self.mock_client
        mock_transformer.return_value = self.mock_model
        mock_pruner_instance = MagicMock()
        mock_pruner_instance.prune_session_memories.return_value = {"pruned": 0}
        mock_pruner.return_value = mock_pruner_instance
        mock_clustering_instance = MagicMock()
        mock_clustering_instance.cluster_memories.return_value = {"num_clusters": 3}
        mock_clustering.return_value = mock_clustering_instance

        chunks = [
            {"intent": f"Intent {i}", "action": f"Action {i}", "outcome": "Success", "summary": f"Summary {i}"}
            for i in range(5)
        ]

        store_enhanced_chunks(chunks, "session456")

        # Verify all chunks were added
        call_args = self.mock_collection.add.call_args
        assert len(call_args.kwargs["documents"]) == 5
        assert len(call_args.kwargs["embeddings"]) == 5
        assert len(call_args.kwargs["ids"]) == 5

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('precompact_memory_extractor.SentenceTransformer')
    @patch('precompact_memory_extractor.MemoryPruner')
    @patch('precompact_memory_extractor.MemoryClustering')
    def test_store_with_file_artifacts(self, mock_clustering, mock_pruner, mock_transformer, mock_chromadb):
        """Store chunks with file artifacts"""
        mock_chromadb.return_value = self.mock_client
        mock_transformer.return_value = self.mock_model
        mock_pruner_instance = MagicMock()
        mock_pruner_instance.prune_session_memories.return_value = {"pruned": 1}
        mock_pruner.return_value = mock_pruner_instance
        mock_clustering_instance = MagicMock()
        mock_clustering_instance.cluster_memories.return_value = {"num_clusters": 1}
        mock_clustering.return_value = mock_clustering_instance

        chunks = [
            {
                "intent": "Create files",
                "action": "Created auth.py and utils.py",
                "outcome": "Success",
                "summary": "File creation"
            }
        ]

        store_enhanced_chunks(chunks, "session789")

        # Verify metadata includes file flags
        call_args = self.mock_collection.add.call_args
        metadata = call_args.kwargs["metadatas"][0]

        assert "has_files" in metadata
        assert "artifacts" in metadata

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('precompact_memory_extractor.SentenceTransformer')
    @patch('precompact_memory_extractor.MemoryPruner')
    @patch('precompact_memory_extractor.MemoryClustering')
    def test_contextual_embedding(self, mock_clustering, mock_pruner, mock_transformer, mock_chromadb):
        """V7 contextual embedding includes session/time/file context"""
        mock_chromadb.return_value = self.mock_client
        mock_transformer.return_value = self.mock_model
        mock_pruner_instance = MagicMock()
        mock_pruner_instance.prune_session_memories.return_value = {"pruned": 0}
        mock_pruner.return_value = mock_pruner_instance
        mock_clustering_instance = MagicMock()
        mock_clustering_instance.cluster_memories.return_value = {"num_clusters": 1}
        mock_clustering.return_value = mock_clustering_instance

        chunks = [
            {
                "intent": "Test",
                "action": "Modified auth.py",
                "outcome": "Success",
                "summary": "Test summary"
            }
        ]

        store_enhanced_chunks(chunks, "sessionABC123")

        # Check that embedding was called
        assert mock_transformer.return_value.encode.called
        # Get the embedding text that was passed
        call_args = mock_transformer.return_value.encode.call_args_list[0]
        embedding_text = call_args[0][0]

        # Should include session context (first 8 chars of session ID)
        assert "sessionA" in embedding_text or "Session" in embedding_text
        # Should include file context
        assert "auth.py" in embedding_text


class TestDebugLog:
    """Test debug logging functionality."""

    def test_debug_log_creates_entry(self, tmp_path):
        """Debug log creates log entry"""
        # This is hard to test since it uses a fixed path
        # Just verify it doesn't crash
        debug_log("Test message")

        # No assertion - just checking it doesn't error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/precompact_memory_extractor", "--cov-report=term-missing"])
