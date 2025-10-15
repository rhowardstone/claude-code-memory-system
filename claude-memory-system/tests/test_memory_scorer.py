#!/usr/bin/env python3
"""
Unit tests for memory_scorer.py
================================
Tests importance scoring logic with all 10 signals.

Target: 100% coverage for memory scoring.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from memory_scorer import MemoryScorer, score_chunks


class TestDecisionMarkers:
    """Test scoring of decision-making indicators."""

    def test_decided_to(self):
        """'decided to' triggers decision marker"""
        chunk = {"intent": "decided to use React", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["decision_marker"]

    def test_chose_to(self):
        """'chose to' triggers decision marker"""
        chunk = {"intent": "chose to use TypeScript over JavaScript", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["decision_marker"]

    def test_will_use(self):
        """'will use' triggers decision marker"""
        chunk = {"intent": "", "action": "will use PostgreSQL for database", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["decision_marker"]

    def test_decision_explicit(self):
        """'decision:' triggers decision marker"""
        chunk = {"intent": "decision: decided to migrate to Docker", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["decision_marker"]

    def test_no_decision(self):
        """No decision markers → no decision score"""
        chunk = {"intent": "normal work", "action": "did stuff", "outcome": "ok"}
        score = MemoryScorer.score_chunk(chunk)
        assert score < MemoryScorer.WEIGHTS["decision_marker"]


class TestErrorResolution:
    """Test scoring of error/bug resolution indicators."""

    def test_fixed_bug(self):
        """'fixed' triggers error resolution"""
        chunk = {"intent": "", "action": "fixed the authentication bug", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["error_resolution"]

    def test_resolved_error(self):
        """'resolved error' triggers resolution"""
        chunk = {"intent": "", "action": "", "outcome": "error resolved successfully"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["error_resolution"]

    def test_debugged(self):
        """'debugged' triggers resolution"""
        chunk = {"intent": "", "action": "debugged the memory leak", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["error_resolution"]

    def test_bug_fixed(self):
        """'bug fixed' triggers resolution"""
        chunk = {"intent": "", "action": "", "outcome": "bug fixed in production"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["error_resolution"]


class TestFileOperations:
    """Test scoring of file creation and modification."""

    def test_created_python_file(self):
        """'created utils.py' triggers file creation"""
        chunk = {"intent": "", "action": "created utils.py with helpers", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["file_creation"]

    def test_created_typescript_file(self):
        """'created auth.ts' triggers file creation"""
        chunk = {"intent": "", "action": "created auth.ts module", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["file_creation"]

    def test_modified_file(self):
        """'modified app.js' triggers file modification"""
        chunk = {"intent": "", "action": "modified app.js to add logging", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["file_modification"]

    def test_multiple_file_types(self):
        """Test various file extensions"""
        extensions = ["py", "js", "ts", "go", "rs", "java", "cpp", "c", "h"]
        for ext in extensions:
            chunk = {"intent": "", "action": f"created test.{ext}", "outcome": ""}
            score = MemoryScorer.score_chunk(chunk)
            assert score >= MemoryScorer.WEIGHTS["file_creation"], f"Failed for .{ext}"


class TestTestSuccess:
    """Test scoring of test success indicators."""

    def test_tests_passing(self):
        """'tests passing' triggers test success"""
        chunk = {"intent": "", "action": "", "outcome": "all tests passing"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["test_success"]

    def test_test_passed(self):
        """'test passed' triggers test success"""
        chunk = {"intent": "", "action": "", "outcome": "integration test passed"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["test_success"]

    def test_tests_succeeded(self):
        """'tests succeeded' triggers test success"""
        chunk = {"intent": "", "action": "", "outcome": "all tests succeeded"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["test_success"]


class TestLearningIndicators:
    """Test scoring of learning and insight indicators."""

    def test_learned(self):
        """'learned' triggers learning"""
        chunk = {"intent": "", "action": "", "outcome": "learned about async patterns"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["learning"]

    def test_discovered(self):
        """'discovered' triggers learning"""
        chunk = {"intent": "", "action": "discovered a better approach", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["learning"]

    def test_realized(self):
        """'realized' triggers learning"""
        chunk = {"intent": "realized the issue was in caching", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["learning"]

    def test_key_insight(self):
        """'key insight' triggers learning"""
        chunk = {"intent": "key insight: use connection pooling", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["learning"]


class TestToolUseFrequency:
    """Test scoring based on tool usage count."""

    def test_no_tools(self):
        """No tools → no tool score"""
        chunk = {"intent": "", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk, {"tool_count": 0})
        assert score == 0

    def test_one_tool(self):
        """1 tool → 1x tool weight"""
        chunk = {"intent": "", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk, {"tool_count": 1})
        assert score == 1 * MemoryScorer.WEIGHTS["tool_use_frequency"]

    def test_multiple_tools(self):
        """5 tools → 5x tool weight"""
        chunk = {"intent": "", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk, {"tool_count": 5})
        expected = 5 * MemoryScorer.WEIGHTS["tool_use_frequency"]
        assert score == expected

    def test_tool_cap(self):
        """Tool score capped at 15.0"""
        chunk = {"intent": "", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk, {"tool_count": 100})
        # Should be capped at 15.0
        assert score <= 15.0


class TestUserDirective:
    """Test scoring of explicit user directives."""

    def test_please(self):
        """'please' triggers user directive"""
        chunk = {"intent": "please fix the bug", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["user_directive"]

    def test_can_you(self):
        """'can you' triggers user directive"""
        chunk = {"intent": "can you help with authentication", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["user_directive"]

    def test_i_want(self):
        """'i want' triggers user directive"""
        chunk = {"intent": "i want to add OAuth", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["user_directive"]

    def test_i_need(self):
        """'i need' triggers user directive"""
        chunk = {"intent": "i need this feature implemented", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["user_directive"]


class TestCodeSnippet:
    """Test scoring of code snippet presence."""

    def test_triple_backticks(self):
        """Code blocks with ``` trigger code snippet"""
        chunk = {"intent": "", "action": "added ```python code```", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["code_snippet"]

    def test_inline_code(self):
        """Inline backtick code triggers code snippet"""
        chunk = {"intent": "", "action": "used `function()` and `variable` here", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["code_snippet"]

    def test_code_word(self):
        """Word 'code' triggers code snippet"""
        chunk = {"intent": "", "action": "wrote code for validation", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["code_snippet"]


class TestArchitectureReference:
    """Test scoring of architecture/design discussion."""

    def test_architecture(self):
        """'architecture' triggers diagram reference"""
        chunk = {"intent": "discussed system architecture", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["diagram_reference"]

    def test_design(self):
        """'design' triggers diagram reference"""
        chunk = {"intent": "", "action": "created API design", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["diagram_reference"]

    def test_flow(self):
        """'flow' triggers diagram reference"""
        chunk = {"intent": "", "action": "", "outcome": "documented the auth flow"}
        score = MemoryScorer.score_chunk(chunk)
        assert score >= MemoryScorer.WEIGHTS["diagram_reference"]


class TestRecencyDecay:
    """Test time-based importance decay."""

    def test_recent_memory(self):
        """Recent memories maintain full score"""
        chunk = {"intent": "decided to use React framework", "action": "", "outcome": ""}
        now = datetime.now().isoformat()
        score = MemoryScorer.score_chunk(chunk, {"timestamp": now})
        assert score > 0

    def test_old_memory_decay(self):
        """Old memories decay in importance"""
        chunk = {"intent": "decided to use React framework", "action": "", "outcome": ""}

        # Recent memory
        recent = datetime.now().isoformat()
        recent_score = MemoryScorer.score_chunk(chunk, {"timestamp": recent})

        # 30-day old memory (one half-life)
        old = (datetime.now() - timedelta(days=30)).isoformat()
        old_score = MemoryScorer.score_chunk(chunk, {"timestamp": old})

        # Old score should be ~50% of recent score
        assert old_score < recent_score
        assert 0.4 < (old_score / recent_score) < 0.6  # Allow some margin

    def test_very_old_memory(self):
        """Very old memories decay significantly"""
        chunk = {"intent": "decided to use React framework", "action": "", "outcome": ""}

        recent = datetime.now().isoformat()
        very_old = (datetime.now() - timedelta(days=120)).isoformat()  # 4 half-lives

        recent_score = MemoryScorer.score_chunk(chunk, {"timestamp": recent})
        very_old_score = MemoryScorer.score_chunk(chunk, {"timestamp": very_old})

        # After 4 half-lives: 0.5^4 = 0.0625 (6.25%)
        assert very_old_score < recent_score * 0.1

    def test_invalid_timestamp(self):
        """Invalid timestamp doesn't crash, just skips decay"""
        chunk = {"intent": "test", "action": "", "outcome": ""}
        score = MemoryScorer.score_chunk(chunk, {"timestamp": "invalid"})
        # Should not crash, just return base score
        assert score >= 0


class TestCategorizeImportance:
    """Test importance categorization tiers."""

    def test_critical_tier(self):
        """Score >= 20 → critical"""
        assert MemoryScorer.categorize_importance(25.0) == "critical"
        assert MemoryScorer.categorize_importance(20.0) == "critical"

    def test_high_tier(self):
        """10 <= score < 20 → high"""
        assert MemoryScorer.categorize_importance(15.0) == "high"
        assert MemoryScorer.categorize_importance(10.0) == "high"
        assert MemoryScorer.categorize_importance(19.9) == "high"

    def test_medium_tier(self):
        """5 <= score < 10 → medium"""
        assert MemoryScorer.categorize_importance(7.0) == "medium"
        assert MemoryScorer.categorize_importance(5.0) == "medium"
        assert MemoryScorer.categorize_importance(9.9) == "medium"

    def test_low_tier(self):
        """score < 5 → low"""
        assert MemoryScorer.categorize_importance(3.0) == "low"
        assert MemoryScorer.categorize_importance(0.0) == "low"
        assert MemoryScorer.categorize_importance(4.9) == "low"


class TestScoreChunks:
    """Test batch scoring helper function."""

    def test_score_multiple_chunks(self):
        """Score list of chunks"""
        chunks = [
            {"intent": "decided to use React", "action": "", "outcome": ""},
            {"intent": "", "action": "fixed bug", "outcome": ""},
        ]
        scored = score_chunks(chunks)

        assert len(scored) == 2
        assert "importance_score" in scored[0]["metadata"]
        assert "importance_category" in scored[0]["metadata"]

    def test_score_with_metadata(self):
        """Score with provided metadata"""
        chunks = [{"intent": "", "action": "", "outcome": ""}]
        metadatas = [{"tool_count": 5}]

        scored = score_chunks(chunks, metadatas)

        assert scored[0]["metadata"]["tool_count"] == 5
        assert scored[0]["metadata"]["importance_score"] > 0

    def test_score_preserves_metadata(self):
        """Original metadata is preserved"""
        chunks = [{"intent": "test", "action": "", "outcome": ""}]
        metadatas = [{"custom_field": "value", "tool_count": 1}]

        scored = score_chunks(chunks, metadatas)

        assert scored[0]["metadata"]["custom_field"] == "value"
        assert "importance_score" in scored[0]["metadata"]

    def test_score_no_metadata(self):
        """Works without metadata"""
        chunks = [{"intent": "test", "action": "", "outcome": ""}]
        scored = score_chunks(chunks)

        assert len(scored) == 1
        assert "importance_score" in scored[0]["metadata"]


class TestCombinedSignals:
    """Test scoring with multiple signals combined."""

    def test_high_importance_chunk(self):
        """Multiple signals → high score"""
        chunk = {
            "intent": "decided to fix critical bug",
            "action": "created auth.py, modified login.ts, debugged token validation",
            "outcome": "bug fixed, tests passing, learned about JWT security"
        }
        metadata = {"tool_count": 8, "timestamp": datetime.now().isoformat()}

        score = MemoryScorer.score_chunk(chunk, metadata)

        # Should have: decision(10) + file_creation(6) + file_modification(4) +
        #              error_resolution(8) + test_success(5) + learning(7) + tools(15 capped)
        assert score >= 40  # High importance

    def test_low_importance_chunk(self):
        """No special signals → low score"""
        chunk = {
            "intent": "routine work",
            "action": "updated comments",
            "outcome": "ok"
        }
        metadata = {"tool_count": 1}

        score = MemoryScorer.score_chunk(chunk, metadata)
        category = MemoryScorer.categorize_importance(score)

        assert category in ["low", "medium"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/memory_scorer", "--cov-report=term-missing"])
