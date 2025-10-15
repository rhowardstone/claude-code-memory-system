#!/usr/bin/env python3
"""
Memory Retrieval Evaluation Framework (V7)
===========================================
Measures quality of memory retrieval using standard IR and RAG metrics.

Standard IR Metrics:
- Precision: % of retrieved memories that are relevant
- Recall: % of relevant memories that were retrieved
- F1 Score: Harmonic mean of precision and recall
- MRR (Mean Reciprocal Rank): Average of 1/rank for first relevant result
- NDCG (Normalized Discounted Cumulative Gain): Ranking quality with position bias

RAG-Specific Metrics (Anthropic, OpenAI, NVIDIA 2024):
- Context Recall: % of relevant context actually retrieved (sensitive to missing info)
- Context Precision: % of retrieved context that's relevant (penalizes noise)
- Faithfulness: % of claims in response grounded in retrieved context (requires response)

References:
- Anthropic (Sept 2024): "Introducing Contextual Retrieval"
- NVIDIA (2024): "Evaluating Retriever for Enterprise-Grade RAG"
- Qdrant (2024): "RAG Evaluation Guide"
- ArXiv: "Evaluation of Retrieval-Augmented Generation: A Survey"

Usage:
    python3 evaluate_retrieval.py              # Run full evaluation
    python3 evaluate_retrieval.py --query "..."  # Evaluate single query
    python3 evaluate_retrieval.py --build-testset  # Build test set interactively
"""

import sys
import json
import math
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from datetime import datetime

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    print("Run: pip install chromadb sentence-transformers numpy", file=sys.stderr)
    sys.exit(1)

# Configuration
MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
TEST_SET_FILE = Path(__file__).parent / "test_queries.json"


class RetrievalEvaluator:
    """Evaluate memory retrieval quality."""

    def __init__(self, db_path: str):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name="conversation_memories")
        self.model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

    def retrieve_memories(self, query: str, top_k: int = 20) -> List[str]:
        """
        Retrieve memories for query using vector search.
        Returns list of memory IDs in ranked order.
        """
        query_embedding = self.model.encode(query).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        if not results or not results["ids"]:
            return []

        return results["ids"][0]  # Return list of IDs

    def calculate_precision(self, retrieved: List[str], relevant: Set[str]) -> float:
        """
        Precision = (# relevant retrieved) / (# retrieved)
        """
        if not retrieved:
            return 0.0

        relevant_retrieved = sum(1 for mem_id in retrieved if mem_id in relevant)
        return relevant_retrieved / len(retrieved)

    def calculate_recall(self, retrieved: List[str], relevant: Set[str]) -> float:
        """
        Recall = (# relevant retrieved) / (# relevant)
        """
        if not relevant:
            return 0.0

        relevant_retrieved = sum(1 for mem_id in retrieved if mem_id in relevant)
        return relevant_retrieved / len(relevant)

    def calculate_f1(self, precision: float, recall: float) -> float:
        """
        F1 = 2 * (precision * recall) / (precision + recall)
        """
        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    def calculate_mrr(self, retrieved: List[str], relevant: Set[str]) -> float:
        """
        MRR (Mean Reciprocal Rank) = 1 / rank of first relevant result
        """
        for rank, mem_id in enumerate(retrieved, start=1):
            if mem_id in relevant:
                return 1.0 / rank

        return 0.0  # No relevant results found

    def calculate_ndcg(self, retrieved: List[str], relevant: Set[str], k: Optional[int] = None) -> float:
        """
        NDCG@k (Normalized Discounted Cumulative Gain)

        Measures ranking quality with position bias - highly relevant results at top = better score.
        Standard metric in IR since 2002 (Järvelin & Kekäläinen).

        DCG = sum(rel_i / log2(i+1)) for i in 1..k
        IDCG = DCG for perfect ranking
        NDCG = DCG / IDCG

        Args:
            retrieved: Ranked list of memory IDs
            relevant: Set of relevant memory IDs
            k: Cutoff rank (default: all retrieved)

        Returns:
            NDCG score in [0, 1], where 1 = perfect ranking
        """
        if not retrieved or not relevant:
            return 0.0

        k = k or len(retrieved)
        retrieved_k = retrieved[:k]

        # Binary relevance: 1 if relevant, 0 otherwise
        relevance_scores = [1.0 if mem_id in relevant else 0.0 for mem_id in retrieved_k]

        # Calculate DCG (Discounted Cumulative Gain)
        dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(relevance_scores))

        # Calculate IDCG (Ideal DCG) - perfect ranking
        ideal_relevance = sorted(relevance_scores, reverse=True)
        idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_relevance))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def calculate_context_recall(
        self,
        retrieved: List[str],
        relevant: Set[str],
        ground_truth_context: Optional[Set[str]] = None
    ) -> float:
        """
        Context Recall (RAG Metric)

        Measures: "Did we retrieve all the relevant context needed?"
        Sensitive to missing information - penalizes incomplete retrieval.

        Standard definition (Anthropic 2024, NVIDIA 2024):
        Context Recall = |statements in ground_truth ∩ retrieved| / |statements in ground_truth|

        Simplified binary version:
        Context Recall = |relevant ∩ retrieved| / |relevant|

        Note: This is equivalent to Recall but emphasized in RAG literature
        as focusing on "did we get the needed context" vs "did we get relevant results".

        Returns:
            Context recall score in [0, 1]
        """
        # Binary version: same as recall
        if not relevant:
            return 0.0

        relevant_retrieved = sum(1 for mem_id in retrieved if mem_id in relevant)
        return relevant_retrieved / len(relevant)

    def calculate_context_precision(
        self,
        retrieved: List[str],
        relevant: Set[str]
    ) -> float:
        """
        Context Precision (RAG Metric)

        Measures: "Is the retrieved context actually relevant?"
        Penalizes noisy retrieval - too much irrelevant context.

        Standard definition (Anthropic 2024, NVIDIA 2024):
        Context Precision = |relevant statements in retrieved| / |all statements in retrieved|

        Simplified binary version:
        Context Precision = |relevant ∩ retrieved| / |retrieved|

        Note: This is equivalent to Precision but emphasized in RAG literature
        as focusing on "how much noise did we add" vs "how accurate is retrieval".

        Returns:
            Context precision score in [0, 1]
        """
        # Binary version: same as precision
        if not retrieved:
            return 0.0

        relevant_retrieved = sum(1 for mem_id in retrieved if mem_id in relevant)
        return relevant_retrieved / len(retrieved)

    def calculate_faithfulness(
        self,
        response: str,
        retrieved_docs: List[str]
    ) -> float:
        """
        Faithfulness (RAG Metric)

        Measures: "Are claims in the response grounded in retrieved context?"
        Detects hallucination - agent making stuff up vs using actual memories.

        Standard definition (OpenAI, NVIDIA 2024):
        Faithfulness = |claims in response grounded in context| / |total claims in response|

        Implementation requires:
        1. Decompose response into atomic claims
        2. Check each claim against retrieved context
        3. LLM-as-judge or NLI model for verification

        Returns:
            Faithfulness score in [0, 1], or None if not implemented

        Note: This requires the agent's actual response text, which is not
        available during pure retrieval evaluation. Implement when evaluating
        end-to-end RAG pipeline (retrieval → generation → evaluation).
        """
        # Placeholder - requires response text and claim verification
        # TODO: Implement with LLM-as-judge or NLI model
        return None

    def evaluate_query(
        self,
        query: str,
        relevant_ids: List[str],
        top_k: int = 20
    ) -> Dict:
        """
        Evaluate retrieval for a single query with comprehensive metrics.

        Returns:
            {
                "query": str,
                "retrieved_count": int,
                "relevant_count": int,

                # Standard IR Metrics
                "precision": float,
                "recall": float,
                "f1": float,
                "mrr": float,
                "ndcg": float,
                "ndcg@5": float,
                "ndcg@10": float,

                # RAG-Specific Metrics
                "context_recall": float,
                "context_precision": float,

                "retrieved_ids": List[str]
            }
        """
        retrieved = self.retrieve_memories(query, top_k=top_k)
        relevant = set(relevant_ids)

        # Standard IR metrics
        precision = self.calculate_precision(retrieved, relevant)
        recall = self.calculate_recall(retrieved, relevant)
        f1 = self.calculate_f1(precision, recall)
        mrr = self.calculate_mrr(retrieved, relevant)

        # NDCG at different cutoffs
        ndcg_full = self.calculate_ndcg(retrieved, relevant)
        ndcg_5 = self.calculate_ndcg(retrieved, relevant, k=5)
        ndcg_10 = self.calculate_ndcg(retrieved, relevant, k=10)

        # RAG-specific metrics
        context_recall = self.calculate_context_recall(retrieved, relevant)
        context_precision = self.calculate_context_precision(retrieved, relevant)

        return {
            "query": query,
            "retrieved_count": len(retrieved),
            "relevant_count": len(relevant),

            # Standard IR
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "mrr": round(mrr, 4),
            "ndcg": round(ndcg_full, 4),
            "ndcg@5": round(ndcg_5, 4),
            "ndcg@10": round(ndcg_10, 4),

            # RAG-specific
            "context_recall": round(context_recall, 4),
            "context_precision": round(context_precision, 4),

            "retrieved_ids": retrieved[:10]  # Top 10 for inspection
        }

    def evaluate_testset(self, test_queries: List[Dict]) -> Dict:
        """
        Evaluate all queries in test set with comprehensive metrics.

        Args:
            test_queries: List of {"query": str, "relevant_ids": List[str]}

        Returns:
            {
                "total_queries": int,

                # Standard IR Metrics (averages)
                "avg_precision": float,
                "avg_recall": float,
                "avg_f1": float,
                "avg_mrr": float,
                "avg_ndcg": float,
                "avg_ndcg@5": float,
                "avg_ndcg@10": float,

                # RAG-Specific Metrics (averages)
                "avg_context_recall": float,
                "avg_context_precision": float,

                "per_query_results": List[Dict]
            }
        """
        results = []

        for test_query in test_queries:
            query = test_query["query"]
            relevant_ids = test_query["relevant_ids"]

            result = self.evaluate_query(query, relevant_ids)
            results.append(result)

        if not results:
            return {
                "total_queries": 0,
                "avg_precision": 0,
                "avg_recall": 0,
                "avg_f1": 0,
                "avg_mrr": 0,
                "avg_ndcg": 0,
                "avg_ndcg@5": 0,
                "avg_ndcg@10": 0,
                "avg_context_recall": 0,
                "avg_context_precision": 0,
                "per_query_results": []
            }

        # Calculate averages
        n = len(results)
        avg_precision = sum(r["precision"] for r in results) / n
        avg_recall = sum(r["recall"] for r in results) / n
        avg_f1 = sum(r["f1"] for r in results) / n
        avg_mrr = sum(r["mrr"] for r in results) / n
        avg_ndcg = sum(r["ndcg"] for r in results) / n
        avg_ndcg_5 = sum(r["ndcg@5"] for r in results) / n
        avg_ndcg_10 = sum(r["ndcg@10"] for r in results) / n
        avg_context_recall = sum(r["context_recall"] for r in results) / n
        avg_context_precision = sum(r["context_precision"] for r in results) / n

        return {
            "total_queries": n,

            # Standard IR
            "avg_precision": round(avg_precision, 4),
            "avg_recall": round(avg_recall, 4),
            "avg_f1": round(avg_f1, 4),
            "avg_mrr": round(avg_mrr, 4),
            "avg_ndcg": round(avg_ndcg, 4),
            "avg_ndcg@5": round(avg_ndcg_5, 4),
            "avg_ndcg@10": round(avg_ndcg_10, 4),

            # RAG-specific
            "avg_context_recall": round(avg_context_recall, 4),
            "avg_context_precision": round(avg_context_precision, 4),

            "per_query_results": results
        }


def load_test_set(filepath: Path) -> List[Dict]:
    """Load test queries from JSON file."""
    if not filepath.exists():
        return []

    with open(filepath) as f:
        return json.load(f)


def save_test_set(test_queries: List[Dict], filepath: Path):
    """Save test queries to JSON file."""
    with open(filepath, "w") as f:
        json.dump(test_queries, f, indent=2)


def build_test_set_interactive():
    """Build test set interactively by querying and selecting relevant results."""
    print("=" * 80)
    print("INTERACTIVE TEST SET BUILDER")
    print("=" * 80)
    print()
    print("Build a test set by entering queries and marking relevant results.")
    print("Type 'done' when finished.")
    print()

    evaluator = RetrievalEvaluator(str(MEMORY_DB_PATH))
    test_queries = []

    while True:
        query = input("\nEnter test query (or 'done'): ").strip()
        if query.lower() == "done":
            break

        if not query:
            continue

        # Retrieve candidates
        retrieved = evaluator.retrieve_memories(query, top_k=20)

        if not retrieved:
            print("  ❌ No memories retrieved for this query")
            continue

        # Show top 10 results
        print(f"\n  Retrieved {len(retrieved)} memories. Top 10:")
        results = evaluator.collection.get(ids=retrieved[:10], include=["metadatas", "documents"])

        for i, (mem_id, doc, meta) in enumerate(zip(results["ids"], results["documents"], results["metadatas"]), 1):
            importance = meta.get("importance_score", 0)
            intent = meta.get("intent", "")[:80]
            print(f"\n  [{i}] ID: {mem_id[:16]}...")
            print(f"      Importance: {importance}")
            print(f"      Intent: {intent}")

        # Ask which are relevant
        relevant_indices = input("\n  Which are relevant? (comma-separated indices, e.g., '1,3,5'): ").strip()

        if not relevant_indices:
            print("  ⚠️  No relevant results marked, skipping query")
            continue

        try:
            indices = [int(i.strip()) - 1 for i in relevant_indices.split(",")]
            relevant_ids = [retrieved[i] for i in indices if 0 <= i < len(retrieved)]

            if relevant_ids:
                test_queries.append({
                    "query": query,
                    "relevant_ids": relevant_ids,
                    "notes": f"Added {datetime.now().strftime('%Y-%m-%d')}"
                })
                print(f"  ✓ Added test query with {len(relevant_ids)} relevant memories")
            else:
                print("  ⚠️  Invalid indices, skipping")

        except ValueError:
            print("  ⚠️  Invalid input format, skipping")

    # Save test set
    if test_queries:
        save_test_set(test_queries, TEST_SET_FILE)
        print(f"\n✅ Saved {len(test_queries)} test queries to {TEST_SET_FILE}")
    else:
        print("\n❌ No test queries created")


def print_evaluation_results(results: Dict):
    """Pretty-print comprehensive evaluation results."""
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS (V7 - Industry Standard Metrics)")
    print("=" * 80)
    print()
    print(f"📊 Overall Metrics ({results['total_queries']} queries):")
    print()
    print("Standard IR Metrics:")
    print(f"   Precision:       {results['avg_precision']:.2%}")
    print(f"   Recall:          {results['avg_recall']:.2%}")
    print(f"   F1 Score:        {results['avg_f1']:.2%}")
    print(f"   MRR:             {results['avg_mrr']:.4f}")
    print(f"   NDCG:            {results['avg_ndcg']:.4f}")
    print(f"   NDCG@5:          {results['avg_ndcg@5']:.4f}")
    print(f"   NDCG@10:         {results['avg_ndcg@10']:.4f}")
    print()
    print("RAG-Specific Metrics (Anthropic, OpenAI, NVIDIA 2024):")
    print(f"   Context Recall:     {results['avg_context_recall']:.2%}")
    print(f"   Context Precision:  {results['avg_context_precision']:.2%}")
    print()
    print("-" * 80)
    print("Per-Query Breakdown:")
    print("-" * 80)

    for i, query_result in enumerate(results["per_query_results"], 1):
        print(f"\n{i}. Query: \"{query_result['query']}\"")
        print(f"   Retrieved: {query_result['retrieved_count']} | Relevant: {query_result['relevant_count']}")
        print(f"   IR:  P={query_result['precision']:.2%} R={query_result['recall']:.2%} F1={query_result['f1']:.2%} MRR={query_result['mrr']:.4f}")
        print(f"   NDCG: Full={query_result['ndcg']:.4f} @5={query_result['ndcg@5']:.4f} @10={query_result['ndcg@10']:.4f}")
        print(f"   RAG: CtxRecall={query_result['context_recall']:.2%} CtxPrecision={query_result['context_precision']:.2%}")


def main():
    """Main evaluation script."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate memory retrieval quality")
    parser.add_argument("--query", help="Evaluate single query")
    parser.add_argument("--relevant-ids", nargs="+", help="Relevant memory IDs for single query")
    parser.add_argument("--build-testset", action="store_true", help="Build test set interactively")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    evaluator = RetrievalEvaluator(str(MEMORY_DB_PATH))

    # Build test set
    if args.build_testset:
        build_test_set_interactive()
        return

    # Single query evaluation
    if args.query:
        if not args.relevant_ids:
            print("ERROR: --relevant-ids required for single query evaluation", file=sys.stderr)
            sys.exit(1)

        result = evaluator.evaluate_query(args.query, args.relevant_ids)
        print("\n" + "=" * 80)
        print(f"Query: \"{args.query}\"")
        print("=" * 80)
        print(f"\nRetrieved: {result['retrieved_count']} | Relevant: {result['relevant_count']}")
        print()
        print("Standard IR Metrics:")
        print(f"   Precision:       {result['precision']:.2%}")
        print(f"   Recall:          {result['recall']:.2%}")
        print(f"   F1 Score:        {result['f1']:.2%}")
        print(f"   MRR:             {result['mrr']:.4f}")
        print(f"   NDCG:            {result['ndcg']:.4f}")
        print(f"   NDCG@5:          {result['ndcg@5']:.4f}")
        print(f"   NDCG@10:         {result['ndcg@10']:.4f}")
        print()
        print("RAG-Specific Metrics:")
        print(f"   Context Recall:     {result['context_recall']:.2%}")
        print(f"   Context Precision:  {result['context_precision']:.2%}")
        return

    # Full test set evaluation
    test_queries = load_test_set(TEST_SET_FILE)

    if not test_queries:
        print(f"ERROR: No test set found at {TEST_SET_FILE}", file=sys.stderr)
        print("Run with --build-testset to create one", file=sys.stderr)
        sys.exit(1)

    results = evaluator.evaluate_testset(test_queries)
    print_evaluation_results(results)

    # Save results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Results saved to {args.output}")


if __name__ == "__main__":
    main()
