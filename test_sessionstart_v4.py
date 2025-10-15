#!/usr/bin/env python3
"""
Test SessionStart V4 - What Would It Inject Now?
=================================================
Simulates SessionStart hook to see what memories would be injected
for this session at this moment with V4 adaptive K retrieval.
"""

import sys
import os
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path.home() / ".claude" / "memory-hooks"))

try:
    from sessionstart_memory_injector_v3 import (
        get_relevant_memories,
        get_important_recent_memories,
        format_enhanced_context,
        MEMORY_DB_PATH
    )
    import chromadb
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

def test_sessionstart_now():
    """Simulate what SessionStart would inject RIGHT NOW."""

    # Current session ID
    session_id = "e58105f1-cf15-48f1-b0fc-00eddc952774"

    print("=" * 80)
    print("V4 SESSIONSTART SIMULATION")
    print("=" * 80)
    print(f"Session: {session_id}")
    print()

    if not MEMORY_DB_PATH.exists():
        print("❌ Memory database not found!")
        return

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))

    try:
        collection = client.get_collection("conversation_memories")
    except Exception as e:
        print(f"❌ Collection not found: {e}")
        return

    print(f"📊 Total memories in DB: {collection.count()}")
    print()

    # Get recent high-importance memories
    print("🔍 Getting recent high-importance memories (>= 5.0)...")
    recent_memories = get_important_recent_memories(collection, session_id, n=4)
    print(f"✅ Found {len(recent_memories)} recent memories")
    print()

    # Get relevant memories with adaptive K
    print("🔍 Getting relevant memories with adaptive K retrieval...")
    query_text = "V4 memory system adaptive K retrieval embedding migration full transcripts"
    relevant_memories = get_relevant_memories(collection, query_text, session_id, max_results=20)
    print(f"✅ Found {len(relevant_memories)} relevant memories (adaptive K)")
    print()

    if relevant_memories:
        print("📈 Relevance breakdown:")
        high_count = sum(1 for m in relevant_memories if m.get("similarity", 0) >= 0.6)
        medium_count = sum(1 for m in relevant_memories if 0.4 <= m.get("similarity", 0) < 0.6)
        print(f"   High quality (>=0.6): {high_count}")
        print(f"   Medium quality (0.4-0.6): {medium_count}")
        print()

        print("🎯 Top relevant memories:")
        for i, mem in enumerate(relevant_memories[:5], 1):
            summary = mem["summary"]
            similarity = mem.get("similarity", 0)
            importance = summary.get("importance", 0)
            text = summary["text"][:150]
            print(f"   {i}. Similarity: {similarity:.1%} | Importance: {importance:.1f}")
            print(f"      {text}...")
            print()

    # Format the actual context that would be injected
    print("=" * 80)
    print("ACTUAL SESSIONSTART INJECTION:")
    print("=" * 80)
    print()

    context = format_enhanced_context(recent_memories, relevant_memories)
    print(context)

if __name__ == "__main__":
    test_sessionstart_now()
