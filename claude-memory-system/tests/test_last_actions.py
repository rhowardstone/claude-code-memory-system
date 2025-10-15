#!/usr/bin/env python3
"""
Unit tests for Last Actions feature (V7)
=========================================
Tests extract_last_actions, store_last_actions, retrieve_last_actions,
and formatting functions.

Target: 80%+ coverage for new V7 features.
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from precompact_memory_extractor import (
    extract_last_actions,
    store_last_actions
)

from sessionstart_memory_injector import (
    retrieve_last_actions,
    format_last_actions_section,
    get_memory_statistics,
    format_statistics_section
)


class TestExtractLastActions:
    """Test extraction of last actions from transcript."""

    def test_extract_basic_actions(self):
        """Extract last actions from simple transcript"""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Create a file"}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": "I'll create the file"},
                {"type": "tool_use", "name": "Write", "input": {"file_path": "test.py", "content": "code"}}
            ]},
            {"role": "user", "content": [{"type": "text", "text": "Run tests"}]}
        ]

        chunks = [{
            "intent": "Create a file",
            "action": "Created test.py",
            "outcome": "Success",
            "artifacts": json.dumps({"file_paths": ["test.py"]})
        }]

        last_actions = extract_last_actions(messages, chunks, max_actions=5)

        assert last_actions is not None
        assert last_actions["last_user_message"] == "Run tests"
        assert len(last_actions["last_tool_calls"]) == 1
        assert last_actions["last_tool_calls"][0]["tool"] == "Write"
        assert last_actions["last_tool_calls"][0]["file"] == "test.py"
        assert last_actions["last_outcome"] == "Success"
        assert "test.py" in last_actions["files_modified"]

    def test_extract_multiple_tool_calls(self):
        """Extract multiple tool calls (up to max_actions)"""
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Write", "input": {"file_path": "file1.py"}},
            ]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Write", "input": {"file_path": "file2.py"}},
            ]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "file3.py"}},
            ]},
        ]

        chunks = [{"intent": "", "action": "", "outcome": "", "artifacts": "{}"}]

        last_actions = extract_last_actions(messages, chunks, max_actions=2)

        # Should only get last 2 actions
        assert len(last_actions["last_tool_calls"]) == 2
        assert last_actions["last_tool_calls"][0]["file"] == "file2.py"
        assert last_actions["last_tool_calls"][1]["file"] == "file3.py"

    def test_extract_nested_message_structure(self):
        """Handle nested message structure (Claude Code format)"""
        messages = [
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "Hello"}]}},
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "test.py"}}
            ]}}
        ]

        chunks = [{"intent": "", "action": "", "outcome": "", "artifacts": "{}"}]

        last_actions = extract_last_actions(messages, chunks)

        assert last_actions["last_user_message"] == "Hello"
        assert len(last_actions["last_tool_calls"]) == 1
        assert last_actions["last_tool_calls"][0]["tool"] == "Read"

    def test_extract_empty_messages(self):
        """Empty messages returns empty dict"""
        last_actions = extract_last_actions([], [])
        assert last_actions == {}

    def test_truncate_long_user_message(self):
        """Long user message is truncated to 200 chars"""
        long_message = "x" * 300
        messages = [
            {"role": "user", "content": [{"type": "text", "text": long_message}]}
        ]
        chunks = [{"intent": "", "action": "", "outcome": "", "artifacts": "{}"}]

        last_actions = extract_last_actions(messages, chunks)

        assert len(last_actions["last_user_message"]) == 200

    def test_extract_files_from_chunk_artifacts(self):
        """Extract file paths from last chunk's artifacts"""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Test"}]}
        ]
        chunks = [{
            "intent": "",
            "action": "",
            "outcome": "",
            "artifacts": json.dumps({"file_paths": ["auth.py", "utils.py", "api.ts"]})
        }]

        last_actions = extract_last_actions(messages, chunks)

        assert len(last_actions["files_modified"]) == 3
        assert "auth.py" in last_actions["files_modified"]

    def test_include_timestamp(self):
        """Last actions includes timestamp"""
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Test"}]}
        ]
        chunks = [{"intent": "", "action": "", "outcome": "", "artifacts": "{}"}]

        last_actions = extract_last_actions(messages, chunks)

        assert "timestamp" in last_actions
        # Should be ISO 8601 format
        datetime.fromisoformat(last_actions["timestamp"])


class TestStoreLastActions:
    """Test storing last actions in ChromaDB."""

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    def test_store_last_actions_success(self, mock_chromadb):
        """Store last actions successfully"""
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.return_value = mock_client

        last_actions = {
            "last_user_message": "Test",
            "last_tool_calls": [{"tool": "Write", "file": "test.py"}],
            "files_modified": ["test.py"],
            "last_outcome": "Success",
            "timestamp": datetime.now().isoformat()
        }

        store_last_actions("session123", last_actions)

        # Verify collection was created
        mock_client.get_or_create_collection.assert_called_once_with(
            name="session_state",
            metadata={"description": "Last actions before compaction for each session"}
        )

        # Verify upsert was called
        mock_collection.upsert.assert_called_once()
        call_args = mock_collection.upsert.call_args
        assert call_args.kwargs["ids"] == ["last_actions_session123"]

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    def test_store_empty_actions(self, mock_chromadb):
        """Empty actions dict is not stored"""
        store_last_actions("session456", {})

        # Should not create collection or store
        mock_chromadb.assert_not_called()


class TestRetrieveLastActions:
    """Test retrieving last actions from ChromaDB."""

    def test_retrieve_existing_actions(self):
        """Retrieve last actions that exist"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        stored_actions = {
            "last_user_message": "Previous work",
            "last_tool_calls": [{"tool": "Edit", "file": "app.py"}],
            "files_modified": ["app.py"],
            "last_outcome": "Completed",
            "timestamp": "2025-10-15T12:00:00"
        }

        mock_collection.get.return_value = {
            "documents": [json.dumps(stored_actions)],
            "ids": ["last_actions_session789"]
        }

        result = retrieve_last_actions(mock_client, "session789")

        assert result == stored_actions
        mock_collection.get.assert_called_once_with(
            ids=["last_actions_session789"],
            limit=1
        )

    def test_retrieve_nonexistent_actions(self):
        """Return empty dict when no actions found"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_collection.get.return_value = {"documents": [], "ids": []}

        result = retrieve_last_actions(mock_client, "session999")

        assert result == {}


class TestFormatLastActionsSection:
    """Test formatting last actions for display."""

    def test_format_complete_section(self):
        """Format section with all components"""
        last_actions = {
            "last_user_message": "Fix the bug",
            "last_tool_calls": [
                {"tool": "Edit", "file": "auth.py"},
                {"tool": "Write", "file": "test.py"}
            ],
            "files_modified": ["auth.py", "test.py"],
            "last_outcome": "Bug fixed successfully",
            "timestamp": "2025-10-15T12:00:00"
        }

        formatted = format_last_actions_section(last_actions)

        assert "## 🎯 Where You Left Off" in formatted
        assert "**Your Last Request**: Fix the bug" in formatted
        assert "**Recent Actions**:" in formatted
        assert "`Edit` → `auth.py`" in formatted
        assert "`Write` → `test.py`" in formatted
        assert "**Files Modified**: `auth.py`, `test.py`" in formatted
        assert "**Status**: Bug fixed successfully" in formatted

    def test_format_empty_actions(self):
        """Empty actions returns empty string"""
        formatted = format_last_actions_section({})
        assert formatted == ""

    def test_format_partial_actions(self):
        """Format with only some components"""
        last_actions = {
            "last_user_message": "Test",
            "last_tool_calls": [],
            "files_modified": [],
            "last_outcome": "",
            "timestamp": "2025-10-15T12:00:00"
        }

        formatted = format_last_actions_section(last_actions)

        assert "**Your Last Request**: Test" in formatted
        assert "**Recent Actions**:" not in formatted
        assert "**Files Modified**:" not in formatted
        assert "**Status**:" not in formatted

    def test_truncate_many_files(self):
        """Truncate file list if > 5 files"""
        last_actions = {
            "last_user_message": "",
            "last_tool_calls": [],
            "files_modified": [f"file{i}.py" for i in range(10)],
            "last_outcome": "",
            "timestamp": "2025-10-15T12:00:00"
        }

        formatted = format_last_actions_section(last_actions)

        assert "file0.py" in formatted
        assert "file4.py" in formatted
        assert "+5 more" in formatted


class TestGetMemoryStatistics:
    """Test gathering memory database statistics."""

    def test_gather_basic_stats(self):
        """Gather statistics from collection and graph"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_kg = MagicMock()

        # Mock collection.get for all memories
        mock_collection.get.side_effect = [
            {"ids": [f"mem{i}" for i in range(100)]},  # Total memories
            {"ids": [f"session_mem{i}" for i in range(20)],  # Session memories
             "metadatas": [{"importance_score": 10.0 if i < 5 else 20.0} for i in range(20)]}
        ]

        # Mock knowledge graph
        mock_kg.graph.number_of_nodes.return_value = 500
        mock_kg.graph.number_of_edges.return_value = 150

        stats = get_memory_statistics(mock_client, mock_collection, mock_kg, "session123")

        assert stats["total_memories"] == 100
        assert stats["session_memories"] == 20
        assert stats["high_importance"] == 15  # 15 memories >= 15.0
        assert stats["graph_nodes"] == 500
        assert stats["graph_edges"] == 150


class TestFormatStatisticsSection:
    """Test formatting statistics for display."""

    def test_format_stats_section(self):
        """Format statistics section"""
        stats = {
            "total_memories": 725,
            "session_memories": 50,
            "high_importance": 12,
            "graph_nodes": 881,
            "graph_edges": 177
        }

        formatted = format_statistics_section(stats)

        assert "## 📊 Memory Database Status" in formatted
        assert "**Total Memories**: 725 stored" in formatted
        assert "**This Session**: 50 memories" in formatted
        assert "**High Priority**: 12 critical memories" in formatted
        assert "**Knowledge Graph**: 881 entities, 177 relationships" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks", "--cov-report=term-missing"])
