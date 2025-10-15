#!/usr/bin/env python3
"""
Complete Memory Migration to nomic-embed-text-v1.5
===================================================
Re-embeds all existing memories from 384-dim to 768-dim.
Preserves all metadata, documents, and session associations.
"""

import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
import sys

OLD_DB_PATH = Path.home() / ".claude" / "memory_db.backup_384d_20251013_115613"
NEW_DB_PATH = Path.home() / ".claude" / "memory_db"
NEW_EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"  # 768d

def migrate_all():
    """Re-embed all memories with new model."""

    print("🔄 Starting complete memory migration...")
    print(f"📁 Source (old): {OLD_DB_PATH}")
    print(f"📁 Target (new): {NEW_DB_PATH}")
    print()

    if not OLD_DB_PATH.exists():
        print("❌ Backup database not found!")
        sys.exit(1)

    # Load old database
    print("📖 Loading old database (384-dim)...")
    old_client = chromadb.PersistentClient(path=str(OLD_DB_PATH))

    try:
        old_collection = old_client.get_collection("conversation_memories")
    except Exception as e:
        print(f"❌ Error loading old collection: {e}")
        sys.exit(1)

    old_count = old_collection.count()
    print(f"✅ Found {old_count} memories to migrate")
    print()

    # Get ALL memories from old DB
    print("🔍 Retrieving all memories...")
    results = old_collection.get(
        include=["documents", "metadatas"]
    )

    if not results or not results.get("ids"):
        print("❌ No memories found!")
        sys.exit(1)

    ids = results["ids"]
    documents = results["documents"]
    metadatas = results["metadatas"]

    print(f"✅ Retrieved {len(ids)} memories")
    print()

    # Load new embedding model
    print(f"🤖 Loading new embedding model: {NEW_EMBEDDING_MODEL}...")
    embedding_model = SentenceTransformer(NEW_EMBEDDING_MODEL, trust_remote_code=True)
    print("✅ Model loaded!")
    print()

    # Connect to new database
    print("📝 Connecting to new database...")
    new_client = chromadb.PersistentClient(path=str(NEW_DB_PATH))
    new_collection = new_client.get_or_create_collection(
        name="conversation_memories",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"✅ New collection ready (current count: {new_collection.count()})")
    print()

    # Re-embed and insert in batches
    batch_size = 50
    total = len(ids)

    print(f"🔄 Re-embedding and inserting {total} memories...")
    print()

    for i in range(0, total, batch_size):
        batch_end = min(i + batch_size, total)
        batch_ids = ids[i:batch_end]
        batch_docs = documents[i:batch_end]
        batch_metas = metadatas[i:batch_end]

        print(f"   Processing batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({i+1}-{batch_end}/{total})...", end=" ")

        # Create enhanced embedding text for each memory
        # Use action field which has full context
        embedding_texts = []
        for meta, doc in zip(batch_metas, batch_docs):
            # Build rich embedding text from metadata
            intent = meta.get("intent", "")
            action = meta.get("action", "")
            outcome = meta.get("outcome", "")

            # Combine for semantic richness
            embedding_text = f"{intent} {action} {outcome} {doc}"
            embedding_texts.append(embedding_text)

        # Generate new 768-dim embeddings
        batch_embeddings = embedding_model.encode(embedding_texts).tolist()

        # Insert into new collection
        new_collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=batch_embeddings
        )

        print("✅")

    print()
    final_count = new_collection.count()
    print(f"🎉 Migration complete!")
    print(f"   Migrated: {total} memories")
    print(f"   New DB count: {final_count}")
    print()
    print("✨ All memories now use nomic-embed-text-v1.5 (768-dim)")
    print("✨ Future compactions will seamlessly add to this collection")

if __name__ == "__main__":
    migrate_all()
