#!/usr/bin/env python3
"""
End-to-End Integration Test for Last Actions Feature (V7)
==========================================================
Tests the complete flow: PreCompact → Storage → SessionStart → Display

This test simulates a real compaction cycle:
1. PreCompact extracts last actions from transcript
2. Stores them in session_state collection
3. SessionStart retrieves them
4. Formats and displays them

Target: Verify the complete user-facing feature works.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from precompact_memory_extractor import extract_last_actions, store_last_actions
from sessionstart_memory_injector import (
    retrieve_last_actions,
    format_last_actions_section,
    format_enhanced_context
)


class TestLastActionsEndToEnd:
    """End-to-end integration tests for Last Actions feature."""

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('sessionstart_memory_injector.chromadb.PersistentClient')
    def test_complete_flow(self, mock_ss_chromadb, mock_pc_chromadb):
        """
        Test complete flow: Extract → Store → Retrieve → Format → Display

        Simulates:
        1. User works on a feature (tool calls, file edits)
        2. Compaction triggers
        3. PreCompact extracts last actions
        4. Stores in ChromaDB
        5. SessionStart retrieves them
        6. Formats for display
        """

        # === SETUP: Simulate a real transcript ===
        transcript_messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Add authentication to the API"}]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll add authentication"},
                    {"type": "tool_use", "name": "Write", "input": {
                        "file_path": "api/auth.py",
                        "content": "# Auth code"
                    }}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Edit", "input": {
                        "file_path": "api/routes.py",
                        "old_string": "# Routes",
                        "new_string": "# Routes with auth"
                    }}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "name": "Write", "input": {
                        "file_path": "tests/test_auth.py",
                        "content": "# Tests"
                    }}
                ]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "Great! Now run the tests"}]
            }
        ]

        chunks = [{
            "intent": "Add authentication to the API",
            "action": "Created auth.py, modified routes.py, added tests",
            "outcome": "Authentication system completed successfully",
            "artifacts": json.dumps({
                "file_paths": ["api/auth.py", "api/routes.py", "tests/test_auth.py"]
            })
        }]

        session_id = "test_session_123"

        # === STEP 1: PreCompact extracts last actions ===
        last_actions = extract_last_actions(transcript_messages, chunks, max_actions=5)

        # Verify extraction worked
        assert last_actions is not None
        assert last_actions["last_user_message"] == "Great! Now run the tests"
        assert len(last_actions["last_tool_calls"]) == 3
        assert last_actions["last_tool_calls"][0]["tool"] == "Write"
        assert last_actions["last_tool_calls"][0]["file"] == "api/auth.py"
        assert last_actions["last_outcome"] == "Authentication system completed successfully"
        assert len(last_actions["files_modified"]) == 3

        # === STEP 2: PreCompact stores last actions ===
        mock_pc_collection = MagicMock()
        mock_pc_client = MagicMock()
        mock_pc_client.get_or_create_collection.return_value = mock_pc_collection
        mock_pc_chromadb.return_value = mock_pc_client

        store_last_actions(session_id, last_actions)

        # Verify storage was called correctly
        mock_pc_client.get_or_create_collection.assert_called_once_with(
            name="session_state",
            metadata={"description": "Last actions before compaction for each session"}
        )
        mock_pc_collection.upsert.assert_called_once()

        # Get the stored data
        upsert_call = mock_pc_collection.upsert.call_args
        stored_doc = upsert_call.kwargs["documents"][0]
        stored_metadata = upsert_call.kwargs["metadatas"][0]
        stored_id = upsert_call.kwargs["ids"][0]

        assert stored_id == f"last_actions_{session_id}"
        assert stored_metadata["session_id"] == session_id
        assert stored_metadata["type"] == "last_actions"

        # === STEP 3: SessionStart retrieves last actions ===
        mock_ss_collection = MagicMock()
        mock_ss_client = MagicMock()
        mock_ss_client.get_or_create_collection.return_value = mock_ss_collection
        mock_ss_chromadb.return_value = mock_ss_client

        # Mock the retrieval to return what was stored
        mock_ss_collection.get.return_value = {
            "documents": [stored_doc],
            "ids": [stored_id]
        }

        retrieved = retrieve_last_actions(mock_ss_client, session_id)

        # Verify retrieval worked
        assert retrieved == last_actions
        assert retrieved["last_user_message"] == "Great! Now run the tests"
        assert len(retrieved["last_tool_calls"]) == 3

        # === STEP 4: SessionStart formats for display ===
        formatted_section = format_last_actions_section(retrieved)

        # Verify formatting
        assert "## 🎯 Where You Left Off" in formatted_section
        assert "**Your Last Request**: Great! Now run the tests" in formatted_section
        assert "**Recent Actions**:" in formatted_section
        assert "`Write` → `api/auth.py`" in formatted_section
        assert "`Edit` → `api/routes.py`" in formatted_section
        assert "`Write` → `tests/test_auth.py`" in formatted_section
        assert "**Files Modified**: `api/auth.py`, `api/routes.py`, `tests/test_auth.py`" in formatted_section
        assert "**Status**: Authentication system completed successfully" in formatted_section

        # === STEP 5: Full context formatting ===
        # Test that last actions integrate properly with full context
        recent_memories = []  # Empty for this test
        relevant_memories = []  # Empty for this test

        full_context = format_enhanced_context(
            recent_memories,
            relevant_memories,
            last_actions=retrieved,
            stats=None
        )

        # Verify last actions appear in full context
        assert "🎯 Where You Left Off" in full_context
        assert "Great! Now run the tests" in full_context
        assert "api/auth.py" in full_context

    @patch('precompact_memory_extractor.chromadb.PersistentClient')
    @patch('sessionstart_memory_injector.chromadb.PersistentClient')
    def test_no_last_actions_graceful(self, mock_ss_chromadb, mock_pc_chromadb):
        """
        Test graceful handling when no last actions exist.

        Scenario: First session, no previous actions stored.
        """
        session_id = "new_session_456"

        # === SessionStart tries to retrieve, finds nothing ===
        mock_ss_collection = MagicMock()
        mock_ss_client = MagicMock()
        mock_ss_client.get_or_create_collection.return_value = mock_ss_collection
        mock_ss_chromadb.return_value = mock_ss_client

        # No documents found
        mock_ss_collection.get.return_value = {
            "documents": [],
            "ids": []
        }

        retrieved = retrieve_last_actions(mock_ss_client, session_id)

        # Should return empty dict
        assert retrieved == {}

        # === Formatting handles empty gracefully ===
        formatted_section = format_last_actions_section(retrieved)

        # Should return empty string
        assert formatted_section == ""

        # === Full context still works without last actions ===
        full_context = format_enhanced_context(
            recent_memories=[],
            relevant_memories=[],
            last_actions=retrieved,
            stats=None
        )

        # Should not include "Where You Left Off" section
        assert "🎯 Where You Left Off" not in full_context
        # But should still have other sections
        assert "🔍 Memory Query Tools" in full_context

    def test_realistic_tool_sequence(self):
        """
        Test with a realistic sequence of developer actions.

        Simulates: bug fix workflow with multiple file edits.
        """

        messages = [
            {"role": "user", "content": [{"type": "text", "text": "Fix the login bug"}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Let me investigate"},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "auth/login.py"}}
            ]},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Found the issue, fixing it now"},
                {"type": "tool_use", "name": "Edit", "input": {
                    "file_path": "auth/login.py",
                    "old_string": "if user:",
                    "new_string": "if user and user.active:"
                }}
            ]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Write", "input": {
                    "file_path": "tests/test_login_fix.py",
                    "content": "test code"
                }}
            ]},
            {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "pytest tests/test_login_fix.py"}}
            ]},
            {"role": "user", "content": [{"type": "text", "text": "Perfect! Commit the fix"}]}
        ]

        chunks = [{
            "intent": "Fix the login bug",
            "action": "Fixed login.py to check user.active, added tests",
            "outcome": "Bug fixed, tests passing",
            "artifacts": json.dumps({
                "file_paths": ["auth/login.py", "tests/test_login_fix.py"],
                "error_messages": [{"type": "error", "message": "Login accepts inactive users"}]
            })
        }]

        last_actions = extract_last_actions(messages, chunks, max_actions=5)

        # Verify realistic extraction
        assert last_actions["last_user_message"] == "Perfect! Commit the fix"
        assert len(last_actions["last_tool_calls"]) == 4  # Read, Edit, Write, Bash

        # Verify tools in order (reversed, so most recent first)
        tools = [t["tool"] for t in last_actions["last_tool_calls"]]
        assert "Read" in tools
        assert "Edit" in tools
        assert "Write" in tools
        assert "Bash" in tools

        # Verify file references
        assert any("login.py" in t.get("file", "") for t in last_actions["last_tool_calls"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
