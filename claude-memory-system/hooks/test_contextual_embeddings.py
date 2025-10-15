#!/usr/bin/env python3
"""
Test V7 Contextual Embeddings
==============================
Manually inject test memories with V7 contextual embeddings and measure improvement.

This script:
1. Creates test memories with V7 contextual format
2. Inserts them into ChromaDB
3. Queries with temporal/file-based queries
4. Compares V7 (contextual) vs V6 (non-contextual) retrieval
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Configuration
MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
TEST_SESSION_ID = "v7_test_contextual_embeddings"


def create_test_memories() -> List[Dict]:
    """
    Create test memories covering different scenarios:
    - Yesterday's work
    - Specific file changes
    - Bug fixes
    - Features implemented
    """
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(days=7)

    test_memories = [
        {
            "session_id": TEST_SESSION_ID,
            "timestamp": yesterday.isoformat(),
            "intent": "Fix authentication bug in login flow",
            "action": "Modified auth.py to handle token expiry correctly",
            "outcome": "Bug fixed, tests passing",
            "files": ["src/auth.py", "tests/auth.test.ts"],
            "importance_score": 18.0,
            "importance_category": "high"
        },
        {
            "session_id": TEST_SESSION_ID,
            "timestamp": yesterday.isoformat(),
            "intent": "Refactor database connection pooling",
            "action": "Updated database.py with connection pool limits",
            "outcome": "Performance improved by 40%",
            "files": ["src/database.py", "src/config.py"],
            "importance_score": 15.0,
            "importance_category": "high"
        },
        {
            "session_id": TEST_SESSION_ID,
            "timestamp": last_week.isoformat(),
            "intent": "Implement user profile page",
            "action": "Created profile.tsx with avatar upload",
            "outcome": "Feature complete, deployed to staging",
            "files": ["src/pages/profile.tsx", "src/components/Avatar.tsx"],
            "importance_score": 12.0,
            "importance_category": "high"
        },
        {
            "session_id": TEST_SESSION_ID,
            "timestamp": now.isoformat(),
            "intent": "Add logging to API endpoints",
            "action": "Instrumented routes.py with structured logging",
            "outcome": "All endpoints now log request/response",
            "files": ["src/routes.py", "src/logger.py"],
            "importance_score": 10.0,
            "importance_category": "medium"
        },
        {
            "session_id": TEST_SESSION_ID,
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "intent": "Fix TypeError in data validation",
            "action": "Fixed validator.py type checking logic",
            "outcome": "TypeError resolved, validation working",
            "files": ["src/validator.py"],
            "importance_score": 16.0,
            "importance_category": "high"
        }
    ]

    return test_memories


def create_v6_embedding(memory: Dict, model: SentenceTransformer) -> List[float]:
    """Create V6-style embedding (no contextual prefix)."""
    text = f"{memory['intent']} {memory['action']} {memory['outcome']}"
    return model.encode(text).tolist()


def create_v7_embedding(memory: Dict, model: SentenceTransformer) -> List[float]:
    """Create V7-style embedding (with contextual prefix)."""
    # Format timestamp
    try:
        ts = datetime.fromisoformat(memory['timestamp'])
        time_str = ts.strftime("%Y-%m-%d %H:%M")
    except:
        time_str = memory['timestamp'][:19]

    # Build contextual prefix
    session_short = memory['session_id'][:8]
    files_str = f"Files: {', '.join(memory['files'][:3])}" if memory['files'] else ""

    contextual_text = f"Session {session_short} at {time_str}. {files_str}. {memory['intent']} {memory['action']} {memory['outcome']}"

    return model.encode(contextual_text).tolist()


def insert_test_memories(memories: List[Dict], use_v7: bool = True):
    """Insert test memories into ChromaDB."""
    print(f"\n{'='*80}")
    print(f"INSERTING TEST MEMORIES ({'V7 Contextual' if use_v7 else 'V6 Non-Contextual'})")
    print(f"{'='*80}\n")

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))
    collection = client.get_or_create_collection(
        name="conversation_memories",
        metadata={"hnsw:space": "cosine"}
    )

    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

    documents = []
    metadatas = []
    ids = []
    embeddings = []

    for i, memory in enumerate(memories):
        # Create embedding (V6 or V7)
        if use_v7:
            embedding = create_v7_embedding(memory, model)
        else:
            embedding = create_v6_embedding(memory, model)

        # Prepare metadata
        doc = f"{memory['intent']} -> {memory['action']} -> {memory['outcome']}"
        metadata = {
            "session_id": memory['session_id'],
            "timestamp": memory['timestamp'],
            "intent": memory['intent'],
            "action": memory['action'],
            "outcome": memory['outcome'],
            "importance_score": memory['importance_score'],
            "importance_category": memory['importance_category'],
            "chunk_index": i,
            "has_code": False,
            "has_files": len(memory['files']) > 0,
            "has_architecture": False,
            "artifacts": json.dumps({
                "file_paths": memory['files'],
                "code_snippets": [],
                "commands": [],
                "error_messages": [],
                "architecture_mentions": []
            })
        }

        mem_id = f"{memory['session_id']}_{'v7' if use_v7 else 'v6'}_{i}"

        documents.append(doc)
        metadatas.append(metadata)
        ids.append(mem_id)
        embeddings.append(embedding)

        print(f"✓ Created memory {i+1}: {memory['intent'][:60]}...")

    # Insert into ChromaDB
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings
    )

    print(f"\n✅ Inserted {len(memories)} memories ({'V7 contextual' if use_v7 else 'V6 non-contextual'})")


def test_retrieval(query: str, expected_files: List[str] = None, expected_temporal: str = None):
    """Test retrieval for a query and analyze results."""
    print(f"\n{'='*80}")
    print(f"QUERY: \"{query}\"")
    print(f"{'='*80}")

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))
    collection = client.get_collection(name="conversation_memories")
    model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10,
        where={"session_id": TEST_SESSION_ID}  # Only test memories
    )

    if not results or not results["ids"]:
        print("❌ No results")
        return

    print(f"\nTop 5 Results:")
    print("-" * 80)

    v7_count = 0
    v6_count = 0

    for i in range(min(5, len(results["ids"][0]))):
        mem_id = results["ids"][0][i]
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i] if "distances" in results else None

        is_v7 = "_v7_" in mem_id
        if is_v7:
            v7_count += 1
        else:
            v6_count += 1

        version = "V7" if is_v7 else "V6"
        similarity = 1 - distance if distance else 0

        intent = metadata.get("intent", "")
        files = json.loads(metadata.get("artifacts", "{}")).get("file_paths", [])
        timestamp = metadata.get("timestamp", "")[:19]

        print(f"\n[{i+1}] {version} | Similarity: {similarity:.4f}")
        print(f"    Intent: {intent}")
        print(f"    Files: {', '.join(files) if files else 'None'}")
        print(f"    Time: {timestamp}")

    print(f"\n📊 Results Breakdown:")
    print(f"   V7 (contextual): {v7_count}/5")
    print(f"   V6 (non-contextual): {v6_count}/5")

    if expected_files:
        print(f"\n🎯 Expected files: {', '.join(expected_files)}")
    if expected_temporal:
        print(f"🎯 Expected temporal: {expected_temporal}")


def cleanup_test_memories():
    """Remove test memories from database."""
    print(f"\n{'='*80}")
    print("CLEANUP")
    print(f"{'='*80}\n")

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))
    collection = client.get_collection(name="conversation_memories")

    # Get all test memory IDs
    results = collection.get(
        where={"session_id": TEST_SESSION_ID}
    )

    if results and results["ids"]:
        collection.delete(ids=results["ids"])
        print(f"✅ Removed {len(results['ids'])} test memories")
    else:
        print("✅ No test memories to remove")


def main():
    """Main test script."""
    import argparse

    parser = argparse.ArgumentParser(description="Test V7 contextual embeddings")
    parser.add_argument("--cleanup", action="store_true", help="Remove test memories")
    parser.add_argument("--no-insert", action="store_true", help="Skip insertion, just query")

    args = parser.parse_args()

    if args.cleanup:
        cleanup_test_memories()
        return

    # Create test memories
    memories = create_test_memories()

    if not args.no_insert:
        # Insert V6 (non-contextual) memories
        insert_test_memories(memories, use_v7=False)

        # Insert V7 (contextual) memories
        insert_test_memories(memories, use_v7=True)

    print("\n" + "="*80)
    print("TESTING RETRIEVAL QUALITY")
    print("="*80)

    # Test 1: Temporal query
    print("\n" + "="*80)
    print("TEST 1: Temporal Query")
    print("="*80)
    test_retrieval(
        "what did I work on yesterday",
        expected_temporal="yesterday"
    )

    # Test 2: File-based query
    print("\n" + "="*80)
    print("TEST 2: File-Based Query")
    print("="*80)
    test_retrieval(
        "changes to auth.py authentication",
        expected_files=["src/auth.py"]
    )

    # Test 3: Bug fix query
    print("\n" + "="*80)
    print("TEST 3: Bug Fix Query")
    print("="*80)
    test_retrieval(
        "TypeError bugs fixed",
        expected_files=["src/validator.py"]
    )

    # Test 4: Feature query
    print("\n" + "="*80)
    print("TEST 4: Feature Implementation Query")
    print("="*80)
    test_retrieval(
        "user profile features implemented",
        expected_files=["src/pages/profile.tsx"]
    )

    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    print("\nIf V7 (contextual) appears more often in top results:")
    print("  ✅ Contextual embeddings are improving retrieval!")
    print("\nIf V6 (non-contextual) dominates:")
    print("  ⚠️  Contextual embeddings may need tuning")
    print("\nRun with --cleanup to remove test memories when done")


if __name__ == "__main__":
    main()
