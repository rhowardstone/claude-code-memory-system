#!/usr/bin/env python3
"""
Integration tests for sessionstart_memory_injector.py
=====================================================
Tests task-aware memory injection, adaptive K retrieval,
knowledge graph integration.

Target: 60%+ coverage for SessionStart hook.
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from sessionstart_memory_injector import (
    get_or_build_knowledge_graph,
    extract_smart_summary,
    get_important_recent_memories,
    get_relevant_memories_with_task_context,
    format_memory_entry,
    format_enhanced_context,
    debug_log,
    _kg_cache,
    _kg_cache_time
)


class TestKnowledgeGraphCaching:
    """Test knowledge graph caching logic."""

    @patch('sessionstart_memory_injector.MemoryKnowledgeGraph')
    def test_build_new_graph(self, mock_kg_class):
        """Build new graph when cache is empty"""
        import sessionstart_memory_injector
        # Reset cache
        sessionstart_memory_injector._kg_cache = None
        sessionstart_memory_injector._kg_cache_time = 0

        mock_kg = MagicMock()
        mock_kg.graph.number_of_nodes.return_value = 100
        mock_kg.graph.number_of_edges.return_value = 50
        mock_kg_class.return_value = mock_kg

        result = get_or_build_knowledge_graph()

        # Verify graph was built
        assert mock_kg.build_from_memories.called
        assert mock_kg.compute_centrality.called
        assert result == mock_kg

    @patch('sessionstart_memory_injector.MemoryKnowledgeGraph')
    def test_use_cached_graph(self, mock_kg_class):
        """Use cached graph when available and fresh"""
        import sessionstart_memory_injector
        import time

        # Set up cache
        mock_kg = MagicMock()
        sessionstart_memory_injector._kg_cache = mock_kg
        sessionstart_memory_injector._kg_cache_time = time.time()

        result = get_or_build_knowledge_graph()

        # Should return cached instance, not create new one
        assert result == mock_kg
        assert not mock_kg_class.called


class TestExtractSmartSummary:
    """Test smart summary extraction from metadata."""

    def test_extract_basic_summary(self):
        """Extract basic summary with no artifacts"""
        metadata = {
            "importance_score": 10.0,
            "importance_category": "high",
            "timestamp": "2025-10-15T12:00:00",
            "artifacts": "{}"
        }
        document = "Test memory document"

        summary = extract_smart_summary(metadata, document)

        assert summary["text"] == "Test memory document"
        assert summary["importance"] == 10.0
        assert summary["category"] == "high"
        assert summary["files"] == []

    def test_extract_with_file_artifacts(self):
        """Extract summary with file artifacts"""
        artifacts = {"file_paths": ["auth.py", "utils.py", "api.ts"]}
        metadata = {
            "importance_score": 15.0,
            "importance_category": "critical",
            "timestamp": "2025-10-15T12:00:00",
            "artifacts": json.dumps(artifacts)
        }
        document = "Created authentication files"

        summary = extract_smart_summary(metadata, document)

        assert len(summary["files"]) == 3
        assert "auth.py" in summary["files"]

    def test_extract_with_error_artifacts(self):
        """Extract summary with error artifacts"""
        artifacts = {
            "error_messages": [
                {"type": "error", "message": "TypeError: undefined"},
                {"type": "exception", "message": "Failed to connect"}
            ]
        }
        metadata = {
            "importance_score": 12.0,
            "importance_category": "high",
            "timestamp": "2025-10-15T12:00:00",
            "artifacts": json.dumps(artifacts)
        }
        document = "Fixed bugs"

        summary = extract_smart_summary(metadata, document)

        assert len(summary["bugs_fixed"]) == 2

    def test_extract_decisions_from_action(self):
        """Extract decisions from action metadata"""
        metadata = {
            "importance_score": 10.0,
            "importance_category": "high",
            "timestamp": "2025-10-15T12:00:00",
            "action": "We decided to use PostgreSQL for the database. This approach will scale better.",
            "artifacts": "{}"
        }
        document = "Database decision"

        summary = extract_smart_summary(metadata, document)

        assert len(summary["decisions"]) > 0
        assert "PostgreSQL" in summary["decisions"][0]

    def test_handle_invalid_artifacts_json(self):
        """Handle invalid JSON in artifacts gracefully"""
        metadata = {
            "importance_score": 5.0,
            "importance_category": "medium",
            "timestamp": "2025-10-15T12:00:00",
            "artifacts": "invalid json {"
        }
        document = "Test"

        # Should not crash
        summary = extract_smart_summary(metadata, document)

        assert summary["text"] == "Test"
        assert summary["files"] == []


class TestGetImportantRecentMemories:
    """Test retrieval of recent high-importance memories."""

    def test_get_recent_memories(self):
        """Get recent high-importance memories"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1", "mem2", "mem3"],
            "documents": ["Doc 1", "Doc 2", "Doc 3"],
            "metadatas": [
                {"importance_score": 15.0, "timestamp": "2025-10-15T12:00:00", "artifacts": "{}"},
                {"importance_score": 10.0, "timestamp": "2025-10-15T11:00:00", "artifacts": "{}"},
                {"importance_score": 3.0, "timestamp": "2025-10-15T10:00:00", "artifacts": "{}"}
            ]
        }

        memories = get_important_recent_memories(mock_collection, "session123", n=2)

        # Should return 2 memories (3rd is below MIN_IMPORTANCE=5.0)
        assert len(memories) == 2
        # Should be sorted by timestamp (most recent first)
        assert memories[0]["id"] == "mem1"

    def test_no_memories_found(self):
        """Handle case with no memories"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

        memories = get_important_recent_memories(mock_collection, "session456")

        assert memories == []

    def test_filter_low_importance(self):
        """Filter out memories below MIN_IMPORTANCE"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1", "mem2"],
            "documents": ["Doc 1", "Doc 2"],
            "metadatas": [
                {"importance_score": 2.0, "timestamp": "2025-10-15T12:00:00", "artifacts": "{}"},
                {"importance_score": 3.0, "timestamp": "2025-10-15T11:00:00", "artifacts": "{}"}
            ]
        }

        memories = get_important_recent_memories(mock_collection, "session789")

        # Both below MIN_IMPORTANCE=5.0
        assert len(memories) == 0


class TestGetRelevantMemoriesWithTaskContext:
    """Test adaptive K retrieval with task-context scoring."""

    def setup_method(self):
        """Set up mock knowledge graph"""
        self.mock_kg = MagicMock()
        self.mock_kg.get_related_entities.return_value = {}

    @patch('sessionstart_memory_injector.SentenceTransformer')
    @patch('sessionstart_memory_injector.TaskContextScorer')
    def test_retrieve_high_quality_memories(self, mock_scorer_class, mock_transformer):
        """Retrieve high-quality memories (>= 0.6 similarity)"""
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 768
        mock_transformer.return_value = mock_model

        mock_scorer = MagicMock()
        mock_scorer.extract_task_entities.return_value = []
        mock_scorer.find_related_entities.return_value = {}
        mock_scorer.score_memory_for_task.return_value = (10.0, [])
        mock_scorer_class.return_value = mock_scorer

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["mem1", "mem2"]],
            "documents": [["High quality doc", "Another good doc"]],
            "metadatas": [[
                {"importance_score": 12.0, "artifacts": "{}"},
                {"importance_score": 10.0, "artifacts": "{}"}
            ]],
            "distances": [[0.1, 0.2]]  # High similarity (0.9, 0.8)
        }

        memories = get_relevant_memories_with_task_context(
            mock_collection, "test query", "session123", self.mock_kg, max_results=10
        )

        # Should return high-quality memories
        assert len(memories) > 0
        assert memories[0]["similarity"] >= 0.6

    @patch('sessionstart_memory_injector.SentenceTransformer')
    @patch('sessionstart_memory_injector.TaskContextScorer')
    def test_no_memories_below_threshold(self, mock_scorer_class, mock_transformer):
        """Return empty list when no memories meet threshold"""
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 768
        mock_transformer.return_value = mock_model

        mock_scorer = MagicMock()
        mock_scorer.extract_task_entities.return_value = []
        mock_scorer.find_related_entities.return_value = {}
        mock_scorer_class.return_value = mock_scorer

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["mem1"]],
            "documents": [["Low quality"]],
            "metadatas": [[{"importance_score": 2.0, "artifacts": "{}"}]],
            "distances": [[0.8]]  # Low similarity (0.2)
        }

        memories = get_relevant_memories_with_task_context(
            mock_collection, "test query", "session123", self.mock_kg
        )

        # Should return empty (below MIN_IMPORTANCE and MIN_SIMILARITY)
        assert len(memories) == 0

    @patch('sessionstart_memory_injector.SentenceTransformer')
    @patch('sessionstart_memory_injector.TaskContextScorer')
    def test_task_boost_applied(self, mock_scorer_class, mock_transformer):
        """Task-context boost is applied to relevant memories"""
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 768
        mock_transformer.return_value = mock_model

        mock_scorer = MagicMock()
        mock_scorer.extract_task_entities.return_value = ["auth.py"]
        mock_scorer.find_related_entities.return_value = {"auth.py": 1.0}
        # Task boost: base 10.0 → 20.0 (2x boost)
        mock_scorer.score_memory_for_task.return_value = (20.0, [("auth.py", 1.0)])
        mock_scorer_class.return_value = mock_scorer

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["mem1"]],
            "documents": [["Modified auth.py"]],
            "metadatas": [[{"importance_score": 10.0, "artifacts": "{}"}]],
            "distances": [[0.3]]  # 0.7 similarity
        }

        memories = get_relevant_memories_with_task_context(
            mock_collection, "auth bugs", "session123", self.mock_kg
        )

        assert len(memories) == 1
        # Check task boost was applied
        assert memories[0]["task_boost"] == 2.0  # 20.0 / 10.0
        assert len(memories[0]["matched_entities"]) > 0


class TestFormatMemoryEntry:
    """Test memory entry formatting."""

    def test_format_basic_entry(self):
        """Format basic memory entry"""
        mem = {
            "summary": {
                "text": "Test memory",
                "importance": 10.0,
                "category": "high",
                "timestamp": "2025-10-15T12:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.8
        }

        formatted = format_memory_entry(mem, 1, show_similarity=True)

        assert "HIGH:10.0" in formatted
        assert "Relevance: 80%" in formatted
        assert "Test memory" in formatted

    def test_format_with_files(self):
        """Format entry with file artifacts"""
        mem = {
            "summary": {
                "text": "Created files",
                "importance": 12.0,
                "category": "high",
                "timestamp": "2025-10-15T12:00:00",
                "files": ["auth.py", "utils.py"],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.7
        }

        formatted = format_memory_entry(mem, 1, show_similarity=False)

        assert "**Files**" in formatted
        assert "auth.py" in formatted

    def test_format_with_task_boost(self):
        """Format entry with task boost indicator"""
        mem = {
            "summary": {
                "text": "Task-relevant memory",
                "importance": 10.0,
                "category": "high",
                "timestamp": "2025-10-15T12:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.8,
            "task_boost": 2.5,  # 2.5x boost
            "matched_entities": [("auth.py", 1.0)]
        }

        formatted = format_memory_entry(mem, 1, show_similarity=True)

        assert "Task-Boost: 2.5x" in formatted
        assert "**Task-Relevant**" in formatted

    def test_truncate_long_content(self):
        """Truncate very long content"""
        long_text = "x" * 2000
        mem = {
            "summary": {
                "text": long_text,
                "importance": 10.0,
                "category": "medium",
                "timestamp": "2025-10-15T12:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.5
        }

        formatted = format_memory_entry(mem, 1)

        assert "[truncated]" in formatted
        assert len(formatted) < 2500  # Should be truncated


class TestFormatEnhancedContext:
    """Test full context formatting."""

    def test_format_with_recent_and_relevant(self):
        """Format context with both recent and relevant memories"""
        recent = [{
            "id": "mem1",
            "summary": {
                "text": "Recent work",
                "importance": 15.0,
                "category": "critical",
                "timestamp": "2025-10-15T12:00:00",
                "files": ["auth.py"],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            }
        }]

        relevant = [{
            "id": "mem2",
            "summary": {
                "text": "Related work",
                "importance": 10.0,
                "category": "high",
                "timestamp": "2025-10-14T10:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.8,
            "task_boost": 1.0,
            "matched_entities": []
        }]

        context = format_enhanced_context(recent, relevant)

        assert "Memory Context Restored" in context
        assert "Recent High-Importance Work" in context
        assert "Related Context" in context
        assert "Task-Aware Semantic Match" in context

    def test_format_only_recent(self):
        """Format with only recent memories"""
        recent = [{
            "id": "mem1",
            "summary": {
                "text": "Recent",
                "importance": 10.0,
                "category": "high",
                "timestamp": "2025-10-15T12:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            }
        }]

        context = format_enhanced_context(recent, [])

        assert "Recent High-Importance Work" in context
        assert "Related Context" not in context

    def test_deduplicate_memories(self):
        """Deduplicate memories that appear in both recent and relevant"""
        shared_mem = {
            "id": "mem1",
            "summary": {
                "text": "Shared",
                "importance": 10.0,
                "category": "high",
                "timestamp": "2025-10-15T12:00:00",
                "files": [],
                "bugs_fixed": [],
                "decisions": [],
                "functions": []
            },
            "similarity": 0.9,
            "task_boost": 1.0,
            "matched_entities": []
        }

        recent = [shared_mem]
        relevant = [shared_mem]  # Same memory

        context = format_enhanced_context(recent, relevant)

        # Should not duplicate - memory appears only in recent section
        assert context.count("Shared") == 1


class TestDebugLog:
    """Test debug logging."""

    def test_debug_log_no_crash(self):
        """Debug log doesn't crash on write"""
        # Just verify it doesn't error
        debug_log("Test message")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/sessionstart_memory_injector", "--cov-report=term-missing"])
