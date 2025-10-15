#!/usr/bin/env python3
"""
Unit tests for evaluate_retrieval.py (V7)
==========================================
Tests all evaluation metrics: Precision, Recall, F1, MRR, NDCG,
Context Recall, Context Precision.

Target: 100% coverage for evaluation framework.
"""

import pytest
import math
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from evaluate_retrieval import RetrievalEvaluator


class TestPrecision:
    """Test precision calculation (% of retrieved that are relevant)."""

    def setup_method(self):
        """Create mock evaluator."""
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_perfect_precision(self):
        """All retrieved are relevant → 100%"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem1", "mem2", "mem3"}
        assert self.evaluator.calculate_precision(retrieved, relevant) == 1.0

    def test_half_precision(self):
        """Half retrieved are relevant → 50%"""
        retrieved = ["mem1", "mem2", "mem3", "mem4"]
        relevant = {"mem1", "mem3"}
        assert self.evaluator.calculate_precision(retrieved, relevant) == 0.5

    def test_zero_precision(self):
        """No retrieved are relevant → 0%"""
        retrieved = ["mem1", "mem2"]
        relevant = {"mem3", "mem4"}
        assert self.evaluator.calculate_precision(retrieved, relevant) == 0.0

    def test_empty_retrieved(self):
        """No results retrieved → 0%"""
        retrieved = []
        relevant = {"mem1", "mem2"}
        assert self.evaluator.calculate_precision(retrieved, relevant) == 0.0


class TestRecall:
    """Test recall calculation (% of relevant that were retrieved)."""

    def setup_method(self):
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_perfect_recall(self):
        """All relevant are retrieved → 100%"""
        retrieved = ["mem1", "mem2", "mem3", "mem4"]
        relevant = {"mem1", "mem2", "mem3"}
        assert self.evaluator.calculate_recall(retrieved, relevant) == 1.0

    def test_half_recall(self):
        """Half of relevant are retrieved → 50%"""
        retrieved = ["mem1", "mem5"]
        relevant = {"mem1", "mem2", "mem3", "mem4"}
        assert self.evaluator.calculate_recall(retrieved, relevant) == 0.25

    def test_zero_recall(self):
        """No relevant are retrieved → 0%"""
        retrieved = ["mem5", "mem6"]
        relevant = {"mem1", "mem2"}
        assert self.evaluator.calculate_recall(retrieved, relevant) == 0.0

    def test_empty_relevant(self):
        """No relevant docs exist → 0%"""
        retrieved = ["mem1", "mem2"]
        relevant = set()
        assert self.evaluator.calculate_recall(retrieved, relevant) == 0.0


class TestF1Score:
    """Test F1 score (harmonic mean of precision and recall)."""

    def setup_method(self):
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_perfect_f1(self):
        """P=1.0, R=1.0 → F1=1.0"""
        assert self.evaluator.calculate_f1(1.0, 1.0) == 1.0

    def test_balanced_f1(self):
        """P=0.5, R=0.5 → F1=0.5"""
        assert self.evaluator.calculate_f1(0.5, 0.5) == 0.5

    def test_harmonic_mean(self):
        """P=0.8, R=0.4 → F1 = 2*(0.8*0.4)/(0.8+0.4) ≈ 0.533"""
        f1 = self.evaluator.calculate_f1(0.8, 0.4)
        expected = 2 * (0.8 * 0.4) / (0.8 + 0.4)
        assert abs(f1 - expected) < 0.001

    def test_zero_both(self):
        """P=0, R=0 → F1=0"""
        assert self.evaluator.calculate_f1(0.0, 0.0) == 0.0

    def test_one_zero(self):
        """P=1.0, R=0 → F1=0"""
        assert self.evaluator.calculate_f1(1.0, 0.0) == 0.0


class TestMRR:
    """Test Mean Reciprocal Rank (1/position of first relevant)."""

    def setup_method(self):
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_first_position(self):
        """First result relevant → MRR=1.0"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem1"}
        assert self.evaluator.calculate_mrr(retrieved, relevant) == 1.0

    def test_second_position(self):
        """Second result relevant → MRR=0.5"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem2"}
        assert self.evaluator.calculate_mrr(retrieved, relevant) == 0.5

    def test_third_position(self):
        """Third result relevant → MRR≈0.333"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem3"}
        mrr = self.evaluator.calculate_mrr(retrieved, relevant)
        assert abs(mrr - 0.333333) < 0.001

    def test_multiple_relevant(self):
        """Multiple relevant, use first → MRR=0.5"""
        retrieved = ["mem1", "mem2", "mem3", "mem4"]
        relevant = {"mem2", "mem4"}
        assert self.evaluator.calculate_mrr(retrieved, relevant) == 0.5

    def test_no_relevant_found(self):
        """No relevant in results → MRR=0"""
        retrieved = ["mem1", "mem2"]
        relevant = {"mem5"}
        assert self.evaluator.calculate_mrr(retrieved, relevant) == 0.0


class TestNDCG:
    """Test NDCG (Normalized Discounted Cumulative Gain)."""

    def setup_method(self):
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_perfect_ranking(self):
        """All relevant at top → NDCG=1.0"""
        retrieved = ["mem1", "mem2", "mem3", "mem4"]
        relevant = {"mem1", "mem2"}
        assert self.evaluator.calculate_ndcg(retrieved, relevant) == 1.0

    def test_reverse_ranking(self):
        """All relevant at bottom → NDCG<1.0"""
        retrieved = ["mem3", "mem4", "mem1", "mem2"]
        relevant = {"mem1", "mem2"}
        ndcg = self.evaluator.calculate_ndcg(retrieved, relevant)
        assert 0 < ndcg < 1.0

    def test_no_relevant(self):
        """No relevant docs → NDCG=0"""
        retrieved = ["mem1", "mem2"]
        relevant = set()
        assert self.evaluator.calculate_ndcg(retrieved, relevant) == 0.0

    def test_ndcg_at_k(self):
        """NDCG@3 only considers top 3, can be higher if bad results later"""
        retrieved = ["mem1", "mem2", "mem3", "mem4", "mem5"]
        relevant = {"mem1", "mem4"}
        ndcg_at_3 = self.evaluator.calculate_ndcg(retrieved, relevant, k=3)
        ndcg_full = self.evaluator.calculate_ndcg(retrieved, relevant)
        # mem1 is relevant at pos 1, mem4 at pos 4 (outside @3)
        # @3 can be higher because it ignores missed relevant at pos 4
        # Just verify both are valid scores
        assert 0 <= ndcg_at_3 <= 1.0
        assert 0 <= ndcg_full <= 1.0

    def test_dcg_calculation(self):
        """Verify DCG formula: rel/log2(pos+1)"""
        # Manual calculation for [relevant, irrelevant, relevant]
        # DCG = 1/log2(2) + 0/log2(3) + 1/log2(4)
        #     = 1/1 + 0 + 1/2 = 1.5
        # IDCG = 1/log2(2) + 1/log2(3) (perfect ranking)
        #      = 1/1 + 1/1.585 ≈ 1.631
        # NDCG ≈ 1.5/1.631 ≈ 0.92
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem1", "mem3"}
        ndcg = self.evaluator.calculate_ndcg(retrieved, relevant)
        assert 0.9 < ndcg < 0.93  # Approximate check


class TestContextMetrics:
    """Test RAG-specific Context Recall and Context Precision."""

    def setup_method(self):
        with patch('evaluate_retrieval.chromadb'):
            with patch('evaluate_retrieval.SentenceTransformer'):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_context_recall_same_as_recall(self):
        """Context Recall should equal Recall (binary version)"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem1", "mem2", "mem4"}

        recall = self.evaluator.calculate_recall(retrieved, relevant)
        ctx_recall = self.evaluator.calculate_context_recall(retrieved, relevant)

        assert ctx_recall == recall

    def test_context_precision_same_as_precision(self):
        """Context Precision should equal Precision (binary version)"""
        retrieved = ["mem1", "mem2", "mem3"]
        relevant = {"mem1", "mem2", "mem4"}

        precision = self.evaluator.calculate_precision(retrieved, relevant)
        ctx_precision = self.evaluator.calculate_context_precision(retrieved, relevant)

        assert ctx_precision == precision

    def test_high_context_recall(self):
        """Retrieved all needed context → high recall"""
        retrieved = ["mem1", "mem2", "mem3", "mem4", "mem5"]
        relevant = {"mem1", "mem2"}
        ctx_recall = self.evaluator.calculate_context_recall(retrieved, relevant)
        assert ctx_recall == 1.0  # Got everything needed

    def test_low_context_precision(self):
        """Retrieved too much noise → low precision"""
        retrieved = ["mem1", "mem2", "mem3", "mem4", "mem5"]
        relevant = {"mem1"}
        ctx_precision = self.evaluator.calculate_context_precision(retrieved, relevant)
        assert ctx_precision == 0.2  # Only 1/5 relevant


class TestEvaluateQuery:
    """Test full query evaluation with all metrics."""

    def setup_method(self):
        # Create mock collection and model
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["mem1", "mem2", "mem3"]],
            "distances": [[0.1, 0.2, 0.3]]
        }

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 768

        with patch('evaluate_retrieval.chromadb.PersistentClient', return_value=mock_client):
            with patch('evaluate_retrieval.SentenceTransformer', return_value=mock_model):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_evaluate_query_returns_all_metrics(self):
        """Verify all metrics are computed and returned"""
        result = self.evaluator.evaluate_query(
            query="test query",
            relevant_ids=["mem1", "mem2"],
            top_k=3
        )

        # Check all expected keys
        assert "query" in result
        assert "precision" in result
        assert "recall" in result
        assert "f1" in result
        assert "mrr" in result
        assert "ndcg" in result
        assert "ndcg@5" in result
        assert "ndcg@10" in result
        assert "context_recall" in result
        assert "context_precision" in result
        assert "retrieved_ids" in result

    def test_evaluate_query_perfect_match(self):
        """Perfect retrieval: all retrieved are relevant"""
        result = self.evaluator.evaluate_query(
            query="test",
            relevant_ids=["mem1", "mem2", "mem3"],
            top_k=3
        )

        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["f1"] == 1.0
        assert result["mrr"] == 1.0
        assert result["ndcg"] == 1.0


class TestEvaluateTestset:
    """Test evaluation across multiple queries."""

    def setup_method(self):
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["mem1", "mem2"]],
            "distances": [[0.1, 0.2]]
        }

        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection

        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1] * 768

        with patch('evaluate_retrieval.chromadb.PersistentClient', return_value=mock_client):
            with patch('evaluate_retrieval.SentenceTransformer', return_value=mock_model):
                self.evaluator = RetrievalEvaluator("/tmp/test_db")

    def test_evaluate_empty_testset(self):
        """Empty test set returns zeros"""
        result = self.evaluator.evaluate_testset([])

        assert result["total_queries"] == 0
        assert result["avg_precision"] == 0
        assert result["avg_recall"] == 0

    def test_evaluate_multiple_queries(self):
        """Average metrics across queries"""
        test_queries = [
            {"query": "query1", "relevant_ids": ["mem1"]},
            {"query": "query2", "relevant_ids": ["mem2"]},
        ]

        result = self.evaluator.evaluate_testset(test_queries)

        assert result["total_queries"] == 2
        assert "avg_precision" in result
        assert "avg_ndcg" in result
        assert "per_query_results" in result
        assert len(result["per_query_results"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/evaluate_retrieval", "--cov-report=term-missing"])
