#!/usr/bin/env python3
"""
Test V4 Adaptive K Retrieval
=============================
Simulates SessionStart injection to verify adaptive K works correctly.
"""

import sys
import os
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "memory-hooks"))

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from sessionstart_memory_injector_v3 import (
        get_relevant_memories,
        get_important_recent_memories,
        MEMORY_DB_PATH
    )
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

def test_adaptive_k():
    """Test adaptive K retrieval with current session."""

    # Get current session ID
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    print(f"Testing with session: {session_id}\n")

    if not MEMORY_DB_PATH.exists():
        print("ERROR: Memory database not found")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))

    try:
        collection = client.get_collection("conversation_memories")
    except Exception as e:
        print(f"ERROR: Collection not found: {e}")
        sys.exit(1)

    # Test different queries
    test_queries = [
        ("current task work in progress bugs", "General query (should have medium-high relevance)"),
        ("memory preservation system adaptive K retrieval", "Highly relevant query (should have high relevance)"),
        ("unicorns flying spacecraft quantum physics", "Irrelevant query (should return 0-3 results)"),
        ("bugs errors fixes warnings", "Error-focused query"),
    ]

    print("=" * 80)
    print("V4 ADAPTIVE K RETRIEVAL TEST")
    print("=" * 80)
    print()

    for query_text, description in test_queries:
        print(f"📍 Query: \"{query_text}\"")
        print(f"   Description: {description}")
        print()

        memories = get_relevant_memories(collection, query_text, session_id, max_results=20)

        if not memories:
            print("   Result: 0 memories returned (nothing relevant)")
        else:
            print(f"   Result: {len(memories)} memories returned")

            # Show quality distribution
            high_count = sum(1 for m in memories if m.get("similarity", 0) >= 0.6)
            medium_count = sum(1 for m in memories if 0.4 <= m.get("similarity", 0) < 0.6)

            print(f"   Quality: {high_count} high (>=0.6), {medium_count} medium (0.4-0.6)")

            # Show top 3 with details
            for i, mem in enumerate(memories[:3], 1):
                summary = mem["summary"]
                similarity = mem.get("similarity", 0)
                importance = summary.get("importance", 0)

                print(f"   {i}. Similarity: {similarity:.2f} | Importance: {importance:.1f}")
                print(f"      {summary['text'][:100]}...")

        print()
        print("-" * 80)
        print()

    # Also test recent memories
    print("📍 Recent High-Importance Memories")
    recent = get_important_recent_memories(collection, session_id, n=4)
    print(f"   Result: {len(recent)} recent memories (>= 5.0 importance)")

    print()
    print("=" * 80)
    print("✅ Test complete! Check ~/.claude/memory_hooks_debug.log for detailed adaptive K logs")

if __name__ == "__main__":
    test_adaptive_k()
