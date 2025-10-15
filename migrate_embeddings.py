#!/usr/bin/env python3
"""
Migrate Memory DB to New Embeddings
====================================
Clears the old 384-dim collection and recreates with 768-dim nomic-embed.
Future PreCompact runs will automatically populate with new embeddings.
"""

import chromadb
from pathlib import Path

MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"

def migrate():
    """Clear old collection, let PreCompact rebuild with new embeddings."""

    print("🔄 Starting embedding migration...")
    print(f"📁 Database: {MEMORY_DB_PATH}")

    if not MEMORY_DB_PATH.exists():
        print("❌ No memory database found!")
        return

    client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))

    # Check existing collection
    try:
        collection = client.get_collection("conversation_memories")
        count = collection.count()
        print(f"📊 Found {count} memories in old collection (384-dim embeddings)")

        # Delete old collection
        print("🗑️  Deleting old collection...")
        client.delete_collection("conversation_memories")
        print("✅ Old collection deleted!")

    except Exception as e:
        print(f"⚠️  Collection doesn't exist or error: {e}")

    # Create new collection (will auto-detect 768-dim on first insert)
    print("🆕 Creating new collection (will use 768-dim embeddings)...")
    new_collection = client.get_or_create_collection(
        name="conversation_memories",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"✅ New collection created! Count: {new_collection.count()}")
    print()
    print("🎯 Next steps:")
    print("   1. Currently running sessions will auto-populate on next compaction")
    print("   2. PreCompact hook will use nomic-embed-text-v1.5 (768d)")
    print("   3. SessionStart hook will retrieve with matching 768d embeddings")
    print()
    print("📝 To force compaction for this session: /compact")

if __name__ == "__main__":
    migrate()
