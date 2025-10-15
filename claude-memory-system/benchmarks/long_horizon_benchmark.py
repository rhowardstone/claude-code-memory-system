#!/usr/bin/env python3
"""
Long-Horizon Task Benchmark for Memory System V7
================================================
Based on research from OpenAI Evals and LongEval frameworks.

Tests memory system effectiveness across multiple sessions with compaction.

Metrics (inspired by OpenAI Evals):
- Task Completion Rate: Can agent complete multi-session tasks?
- Session Carryover: Does agent remember previous work?
- Memory Consistency: Are memories accurate across 40+ turns?
- Time to Completion: Does memory system improve efficiency?
- Retrieval Quality: Precision, Recall, F1 for memory retrieval

Scenarios (realistic coding tasks):
1. Multi-file feature implementation (auth system)
2. Bug investigation and fix (across multiple files)
3. Refactoring project (maintaining consistency)
4. API design and implementation (architecture memory)
5. Test suite creation (remembering coverage gaps)
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add hooks to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from precompact_memory_extractor import (
        chunk_conversation,
        store_enhanced_chunks,
        extract_last_actions,
        store_last_actions
    )
    from sessionstart_memory_injector import (
        retrieve_last_actions,
        get_relevant_memories_with_task_context,
        get_important_recent_memories,
        get_or_build_knowledge_graph
    )
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)


@dataclass
class BenchmarkScenario:
    """A multi-session coding task scenario."""
    name: str
    description: str
    sessions: List[Dict[str, Any]]  # Each session has: query, expected_memories, ground_truth_actions
    success_criteria: Dict[str, Any]


@dataclass
class BenchmarkResult:
    """Results from running a benchmark scenario."""
    scenario_name: str
    task_completed: bool
    session_carryover_rate: float  # % of sessions where previous work was remembered
    memory_consistency_score: float  # % of expected memories retrieved
    avg_retrieval_precision: float
    avg_retrieval_recall: float
    avg_retrieval_f1: float
    total_time_seconds: float
    sessions_completed: int
    errors: List[str]


class LongHorizonBenchmark:
    """Benchmark suite for long-horizon task evaluation."""

    def __init__(self, db_path: str = None):
        """Initialize benchmark with test database."""
        if db_path is None:
            db_path = str(Path.home() / ".claude" / "memory_db_benchmark")

        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.embedding_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

        # Create fresh collection for benchmark
        try:
            self.client.delete_collection("conversation_memories")
        except:
            pass
        self.collection = self.client.get_or_create_collection("conversation_memories")

    def create_scenario_auth_system(self) -> BenchmarkScenario:
        """
        Scenario 1: Multi-file authentication system implementation.

        Session 1: Implement basic auth
        Session 2 (after compaction): Add OAuth
        Session 3 (after compaction): Add rate limiting

        Tests: Memory of file structure, previous decisions, architecture
        """
        return BenchmarkScenario(
            name="Auth System Implementation",
            description="Implement authentication system across 3 sessions with compaction",
            sessions=[
                {
                    "session_id": "bench_auth_s1",
                    "query": "Implement basic authentication system",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "Create authentication system with JWT"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "I'll create auth system with JWT tokens"},
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "auth/jwt_handler.py", "content": "JWT code"}}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "auth/user_model.py", "content": "User model"}}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "auth/middleware.py", "content": "Auth middleware"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Create authentication system with JWT",
                        "action": "Created jwt_handler.py, user_model.py, middleware.py",
                        "outcome": "Basic JWT authentication implemented successfully",
                        "summary": "Implemented JWT-based authentication with user model and middleware",
                        "artifacts": json.dumps({
                            "file_paths": ["auth/jwt_handler.py", "auth/user_model.py", "auth/middleware.py"],
                            "architecture_mentions": [{"keyword": "architecture", "description": "JWT token-based architecture"}]
                        })
                    }],
                    "expected_memories": ["JWT", "auth", "jwt_handler.py", "user_model.py"],
                    "ground_truth_actions": ["Write auth/jwt_handler.py", "Write auth/user_model.py", "Write auth/middleware.py"]
                },
                {
                    "session_id": "bench_auth_s2",
                    "query": "Add OAuth support to existing auth system",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "Add OAuth support to the auth system"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "I'll add OAuth to the existing JWT system"},
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "auth/oauth_handler.py", "content": "OAuth code"}}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Edit", "input": {"file_path": "auth/middleware.py", "old_string": "JWT only", "new_string": "JWT and OAuth"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Add OAuth support to existing auth system",
                        "action": "Created oauth_handler.py, modified middleware.py to support OAuth",
                        "outcome": "OAuth integration complete, works alongside JWT",
                        "summary": "Extended auth system with OAuth support",
                        "artifacts": json.dumps({
                            "file_paths": ["auth/oauth_handler.py", "auth/middleware.py"]
                        })
                    }],
                    "expected_memories": ["JWT", "auth", "middleware.py", "OAuth"],
                    "expected_from_previous": ["jwt_handler.py", "user_model.py", "JWT architecture"],
                    "ground_truth_actions": ["Write auth/oauth_handler.py", "Edit auth/middleware.py"]
                },
                {
                    "session_id": "bench_auth_s3",
                    "query": "Add rate limiting to prevent abuse",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "Add rate limiting to auth endpoints"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "I'll add rate limiting to the auth system"},
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "auth/rate_limiter.py", "content": "Rate limiting code"}}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Edit", "input": {"file_path": "auth/middleware.py", "old_string": "no limits", "new_string": "with rate limits"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Add rate limiting to auth endpoints",
                        "action": "Created rate_limiter.py, integrated into middleware.py",
                        "outcome": "Rate limiting active, prevents brute force attacks",
                        "summary": "Added rate limiting protection to authentication",
                        "artifacts": json.dumps({
                            "file_paths": ["auth/rate_limiter.py", "auth/middleware.py"]
                        })
                    }],
                    "expected_memories": ["OAuth", "JWT", "middleware.py", "rate limiting"],
                    "expected_from_previous": ["jwt_handler.py", "oauth_handler.py", "JWT and OAuth architecture"],
                    "ground_truth_actions": ["Write auth/rate_limiter.py", "Edit auth/middleware.py"]
                }
            ],
            success_criteria={
                "min_carryover_rate": 0.7,  # 70% of sessions should remember previous work
                "min_memory_consistency": 0.6,  # 60% of expected memories retrieved
                "min_avg_recall": 0.5,  # 50% recall for memory retrieval
                "max_time_seconds": 120  # Should complete in under 2 minutes
            }
        )

    def create_scenario_bug_investigation(self) -> BenchmarkScenario:
        """
        Scenario 2: Bug investigation and fix across multiple files.

        Session 1: Reproduce and investigate bug
        Session 2 (after compaction): Identify root cause
        Session 3 (after compaction): Implement fix and test

        Tests: Memory of error messages, file relationships, investigation steps
        """
        return BenchmarkScenario(
            name="Multi-Session Bug Investigation",
            description="Investigate and fix bug across 3 sessions with compaction",
            sessions=[
                {
                    "session_id": "bench_bug_s1",
                    "query": "Investigate login timeout issue",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "Users reporting login timeouts after 5 minutes"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "Let me investigate the login flow"},
                            {"type": "tool_use", "name": "Read", "input": {"file_path": "auth/session.py"}}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "Found potential issue in session timeout config"},
                            {"type": "tool_use", "name": "Read", "input": {"file_path": "config/timeout_settings.py"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Investigate login timeout issue",
                        "action": "Read session.py and timeout_settings.py to understand issue",
                        "outcome": "Identified timeout configuration as potential cause",
                        "summary": "Investigating login timeout: examined session.py and timeout_settings.py",
                        "artifacts": json.dumps({
                            "file_paths": ["auth/session.py", "config/timeout_settings.py"],
                            "error_messages": [{"type": "error", "message": "Login timeout after 5 minutes"}]
                        })
                    }],
                    "expected_memories": ["timeout", "session.py", "login", "5 minutes"],
                    "ground_truth_actions": ["Read auth/session.py", "Read config/timeout_settings.py"]
                },
                {
                    "session_id": "bench_bug_s2",
                    "query": "Continue investigating timeout issue",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "What's the root cause of the timeout?"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "The timeout is hardcoded to 300 seconds (5 min) in settings"},
                            {"type": "tool_use", "name": "Read", "input": {"file_path": "config/timeout_settings.py"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Identify root cause of timeout",
                        "action": "Confirmed timeout is hardcoded to 300 seconds",
                        "outcome": "Root cause identified: timeout_settings.py has hardcoded 300s limit",
                        "summary": "Root cause: hardcoded 300 second timeout in timeout_settings.py",
                        "artifacts": json.dumps({
                            "file_paths": ["config/timeout_settings.py"],
                            "bugs_fixed": [{"type": "bug", "description": "Hardcoded timeout"}]
                        })
                    }],
                    "expected_memories": ["timeout", "300 seconds", "timeout_settings.py"],
                    "expected_from_previous": ["session.py", "5 minutes", "login timeout"],
                    "ground_truth_actions": ["Read config/timeout_settings.py"]
                },
                {
                    "session_id": "bench_bug_s3",
                    "query": "Fix the timeout issue",
                    "transcript": [
                        {"role": "user", "content": [{"type": "text", "text": "Fix the timeout to be 30 minutes"}]},
                        {"role": "assistant", "content": [
                            {"type": "text", "text": "I'll update the timeout to 1800 seconds (30 min)"},
                            {"type": "tool_use", "name": "Edit", "input": {
                                "file_path": "config/timeout_settings.py",
                                "old_string": "TIMEOUT = 300",
                                "new_string": "TIMEOUT = 1800"
                            }}
                        ]},
                        {"role": "assistant", "content": [
                            {"type": "tool_use", "name": "Write", "input": {"file_path": "tests/test_timeout.py", "content": "Test code"}}
                        ]},
                    ],
                    "chunks": [{
                        "intent": "Fix timeout to be 30 minutes",
                        "action": "Changed timeout from 300s to 1800s, added test",
                        "outcome": "Bug fixed, timeout now 30 minutes, tests passing",
                        "summary": "Fixed timeout bug: changed to 1800s (30 min) and added tests",
                        "artifacts": json.dumps({
                            "file_paths": ["config/timeout_settings.py", "tests/test_timeout.py"],
                            "bugs_fixed": [{"type": "bug", "description": "Timeout fixed"}]
                        })
                    }],
                    "expected_memories": ["timeout", "1800", "30 minutes", "test_timeout.py"],
                    "expected_from_previous": ["timeout_settings.py", "300 seconds", "hardcoded"],
                    "ground_truth_actions": ["Edit config/timeout_settings.py", "Write tests/test_timeout.py"]
                }
            ],
            success_criteria={
                "min_carryover_rate": 0.8,  # 80% - bug investigation requires strong memory
                "min_memory_consistency": 0.7,  # 70% - need to remember investigation steps
                "min_avg_recall": 0.6,  # 60% recall
                "max_time_seconds": 120
            }
        )

    def run_session(self, session: Dict[str, Any], scenario_name: str) -> Tuple[Dict[str, Any], float]:
        """
        Run a single session: store memories and measure retrieval quality.

        Returns: (metrics, elapsed_time)
        """
        start_time = time.time()
        session_id = session["session_id"]

        # === STEP 1: Store memories (simulate PreCompact) ===
        chunks = session["chunks"]

        # Store chunks with embeddings
        for i, chunk in enumerate(chunks):
            chunk_id = f"{session_id}_chunk{i}"
            enhanced_summary = chunk["summary"]

            # Create contextual embedding (V7 feature)
            embedding_text = f"Session {session_id[:8]} at {datetime.now().strftime('%Y-%m-%d %H:%M')}. Files: {', '.join(json.loads(chunk['artifacts']).get('file_paths', []))}. {enhanced_summary}"
            embedding = self.embedding_model.encode(embedding_text).tolist()

            self.collection.add(
                documents=[enhanced_summary],
                embeddings=[embedding],
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "importance_score": 15.0,  # High importance for benchmark
                    "importance_category": "critical",
                    "intent": chunk["intent"],
                    "action": chunk["action"],
                    "outcome": chunk["outcome"],
                    "artifacts": chunk["artifacts"],
                    "chunk_index": i
                }],
                ids=[chunk_id]
            )

        # Store last actions
        transcript = session["transcript"]
        last_actions = extract_last_actions(transcript, chunks)
        if last_actions:
            # Create session_state collection
            state_collection = self.client.get_or_create_collection("session_state")
            state_collection.upsert(
                documents=[json.dumps(last_actions)],
                metadatas=[{
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "type": "last_actions"
                }],
                ids=[f"last_actions_{session_id}"]
            )

        # === STEP 2: Retrieve memories (simulate SessionStart) ===
        query = session["query"]
        query_embedding = self.embedding_model.encode(query).tolist()

        # CRITICAL: No session_id filter! This simulates cross-session retrieval after compaction
        # Each compaction creates a NEW session, so we MUST retrieve from previous sessions
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=10  # Retrieve from ALL sessions
        )

        retrieved_texts = results["documents"][0] if results["documents"] else []

        # === STEP 3: Calculate metrics ===
        expected_keywords = session.get("expected_memories", [])
        expected_from_prev = session.get("expected_from_previous", [])
        all_expected = expected_keywords + expected_from_prev

        # FIXED: Proper precision/recall calculation (per-document relevance)
        # Precision: % of retrieved documents that are relevant
        # Recall: % of relevant keywords found in any retrieved document
        # F1: Harmonic mean

        # Check which retrieved documents contain expected keywords
        relevant_docs = 0
        keywords_found = set()

        for doc in retrieved_texts:
            doc_lower = doc.lower()
            # Check if this document is relevant (contains any expected keyword)
            is_relevant = any(kw.lower() in doc_lower for kw in all_expected)
            if is_relevant:
                relevant_docs += 1

            # Track which keywords we found (for recall calculation)
            for kw in all_expected:
                if kw.lower() in doc_lower:
                    keywords_found.add(kw.lower())

        # Precision: fraction of retrieved docs that are relevant
        precision = relevant_docs / len(retrieved_texts) if retrieved_texts else 0.0

        # Recall: fraction of expected keywords that were found
        recall = len(keywords_found) / len(all_expected) if all_expected else 1.0

        # F1: harmonic mean
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Session carryover: Did we retrieve memories from previous sessions?
        prev_keywords_found = set()
        for doc in retrieved_texts:
            doc_lower = doc.lower()
            for kw in expected_from_prev:
                if kw.lower() in doc_lower:
                    prev_keywords_found.add(kw.lower())

        carryover_rate = len(prev_keywords_found) / len(expected_from_prev) if expected_from_prev else 1.0

        elapsed = time.time() - start_time

        metrics = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "carryover_rate": carryover_rate,
            "retrieved_count": len(retrieved_texts),
            "expected_count": len(all_expected),
            "relevant_retrieved": relevant_docs,  # Number of relevant documents retrieved
            "keywords_found": len(keywords_found)  # Number of unique keywords found
        }

        return metrics, elapsed

    def run_scenario(self, scenario: BenchmarkScenario, verbose: bool = True) -> BenchmarkResult:
        """Run a complete benchmark scenario across multiple sessions."""
        if verbose:
            print(f"\n{'='*70}")
            print(f"Running Scenario: {scenario.name}")
            print(f"Description: {scenario.description}")
            print(f"Sessions: {len(scenario.sessions)}")
            print(f"{'='*70}\n")

        total_time = 0
        session_metrics = []
        errors = []

        for i, session in enumerate(scenario.sessions, 1):
            if verbose:
                print(f"Session {i}/{len(scenario.sessions)}: {session['query'][:60]}...")

            try:
                metrics, elapsed = self.run_session(session, scenario.name)
                session_metrics.append(metrics)
                total_time += elapsed

                if verbose:
                    print(f"  ✓ Precision: {metrics['precision']:.2%}")
                    print(f"  ✓ Recall: {metrics['recall']:.2%}")
                    print(f"  ✓ F1: {metrics['f1']:.2%}")
                    print(f"  ✓ Carryover: {metrics['carryover_rate']:.2%}")
                    print(f"  ✓ Time: {elapsed:.2f}s\n")

            except Exception as e:
                errors.append(f"Session {i} error: {str(e)}")
                if verbose:
                    print(f"  ✗ Error: {str(e)}\n")

        # Calculate aggregate metrics
        if session_metrics:
            avg_precision = sum(m["precision"] for m in session_metrics) / len(session_metrics)
            avg_recall = sum(m["recall"] for m in session_metrics) / len(session_metrics)
            avg_f1 = sum(m["f1"] for m in session_metrics) / len(session_metrics)
            avg_carryover = sum(m["carryover_rate"] for m in session_metrics) / len(session_metrics)
            memory_consistency = avg_recall  # Use recall as proxy for consistency
        else:
            avg_precision = avg_recall = avg_f1 = avg_carryover = memory_consistency = 0.0

        # Check success criteria
        criteria = scenario.success_criteria
        task_completed = (
            avg_carryover >= criteria["min_carryover_rate"] and
            memory_consistency >= criteria["min_memory_consistency"] and
            avg_recall >= criteria["min_avg_recall"] and
            total_time <= criteria["max_time_seconds"]
        )

        result = BenchmarkResult(
            scenario_name=scenario.name,
            task_completed=task_completed,
            session_carryover_rate=avg_carryover,
            memory_consistency_score=memory_consistency,
            avg_retrieval_precision=avg_precision,
            avg_retrieval_recall=avg_recall,
            avg_retrieval_f1=avg_f1,
            total_time_seconds=total_time,
            sessions_completed=len(session_metrics),
            errors=errors
        )

        if verbose:
            self.print_result(result)

        return result

    def print_result(self, result: BenchmarkResult):
        """Print formatted benchmark results."""
        print(f"\n{'='*70}")
        print(f"RESULTS: {result.scenario_name}")
        print(f"{'='*70}")
        print(f"Task Completed: {'✅ PASS' if result.task_completed else '❌ FAIL'}")
        print(f"Sessions: {result.sessions_completed}")
        print(f"Total Time: {result.total_time_seconds:.2f}s")
        print(f"\nMemory Metrics:")
        print(f"  Session Carryover: {result.session_carryover_rate:.1%}")
        print(f"  Memory Consistency: {result.memory_consistency_score:.1%}")
        print(f"\nRetrieval Quality:")
        print(f"  Precision: {result.avg_retrieval_precision:.1%}")
        print(f"  Recall: {result.avg_retrieval_recall:.1%}")
        print(f"  F1 Score: {result.avg_retrieval_f1:.1%}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  • {err}")

        print(f"{'='*70}\n")

    def run_all_scenarios(self) -> List[BenchmarkResult]:
        """Run all benchmark scenarios."""
        scenarios = [
            self.create_scenario_auth_system(),
            self.create_scenario_bug_investigation()
        ]

        results = []
        for scenario in scenarios:
            result = self.run_scenario(scenario, verbose=True)
            results.append(result)

        # Print summary
        print(f"\n{'='*70}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*70}")
        total_passed = sum(1 for r in results if r.task_completed)
        print(f"Scenarios Passed: {total_passed}/{len(results)}")

        avg_carryover = sum(r.session_carryover_rate for r in results) / len(results)
        avg_consistency = sum(r.memory_consistency_score for r in results) / len(results)
        avg_f1 = sum(r.avg_retrieval_f1 for r in results) / len(results)

        print(f"Average Session Carryover: {avg_carryover:.1%}")
        print(f"Average Memory Consistency: {avg_consistency:.1%}")
        print(f"Average F1 Score: {avg_f1:.1%}")
        print(f"{'='*70}\n")

        return results


def main():
    """Run benchmark suite."""
    print("Long-Horizon Task Benchmark for Claude Code Memory System V7")
    print("Based on OpenAI Evals and LongEval frameworks\n")

    benchmark = LongHorizonBenchmark()
    results = benchmark.run_all_scenarios()

    # Save results to JSON
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump([{
            "scenario": r.scenario_name,
            "passed": r.task_completed,
            "carryover": r.session_carryover_rate,
            "consistency": r.memory_consistency_score,
            "precision": r.avg_retrieval_precision,
            "recall": r.avg_retrieval_recall,
            "f1": r.avg_retrieval_f1,
            "time": r.total_time_seconds
        } for r in results], f, indent=2)

    print(f"✅ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
