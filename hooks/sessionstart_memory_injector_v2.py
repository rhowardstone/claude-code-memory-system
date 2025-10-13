#!/usr/bin/env python3
"""
SessionStart Memory Injector V2 - Enhanced retrieval
=====================================================
Uses importance scoring and hierarchical clustering for smarter memory injection.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Configuration
MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_MEMORIES = 10
RECENT_MEMORIES = 5
MIN_IMPORTANCE = 3.0  # Only inject memories above this importance
DEBUG_LOG = Path.home() / ".claude" / "memory_hooks_debug.log"


def debug_log(msg: str):
    """Append debug message to log."""
    try:
        with open(DEBUG_LOG, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [SessionStart-V2] {msg}\n")
    except Exception:
        pass


def get_important_recent_memories(collection, session_id: str, n: int = RECENT_MEMORIES) -> List[Dict[str, Any]]:
    """Get recent memories, filtered by importance."""
    try:
        results = collection.get(
            where={"session_id": session_id},
            limit=1000
        )

        if not results or not results.get("metadatas"):
            return []

        # Sort by timestamp and filter by importance
        memories = []
        for i, metadata in enumerate(results["metadatas"]):
            importance = metadata.get("importance_score", 0.0)
            if importance >= MIN_IMPORTANCE:
                memories.append({
                    "id": results["ids"][i],
                    "document": results["documents"][i],
                    "metadata": metadata
                })

        memories.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
        return memories[:n]

    except Exception as e:
        debug_log(f"Error getting recent memories: {e}")
        return []


def get_relevant_memories(collection, query_text: str, session_id: str, n: int = TOP_K_MEMORIES) -> List[Dict[str, Any]]:
    """Query with importance-weighted results and deduplication."""
    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        query_embedding = embedding_model.encode(query_text).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n * 3,  # Get extra for filtering and deduplication
            where={"session_id": session_id}
        )

        if not results or not results.get("metadatas") or not results["metadatas"][0]:
            return []

        # Filter by importance and similarity threshold
        MIN_SIMILARITY = 0.3  # Skip memories with low semantic similarity
        memories = []
        seen_documents = set()  # Track seen documents for deduplication

        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]
            importance = metadata.get("importance_score", 0.0)
            distance = results["distances"][0][i] if "distances" in results else 0.5
            similarity = 1 - distance

            # Skip if too dissimilar, low importance, or duplicate
            if similarity < MIN_SIMILARITY or importance < MIN_IMPORTANCE:
                continue

            # Deduplicate by document content (exact match)
            doc_key = document.strip().lower()
            if doc_key in seen_documents:
                debug_log(f"Skipping duplicate memory: {document[:50]}...")
                continue
            seen_documents.add(doc_key)

            memories.append({
                "id": results["ids"][0][i],
                "document": document,
                "metadata": metadata,
                "distance": distance,
                "similarity": similarity
            })

        # Sort by combined score: similarity * importance
        for mem in memories:
            importance = mem["metadata"].get("importance_score", 0.0)
            mem["combined_score"] = mem["similarity"] * importance

        memories.sort(key=lambda x: x["combined_score"], reverse=True)
        return memories[:n]

    except Exception as e:
        debug_log(f"Error querying memories: {e}")
        return []


def format_enhanced_context(recent_memories: List[Dict], relevant_memories: List[Dict]) -> str:
    """Format with importance levels and multi-modal artifacts."""
    parts = []

    parts.append("# 🧠 Memory Preserved from Pre-Compaction Context")
    parts.append("")
    parts.append("*Enhanced with importance scoring, multi-modal artifacts, and hierarchical clustering*")
    parts.append("")

    # Recent memories
    if recent_memories:
        parts.append("## 📋 Recent Actions (Chronological)")
        parts.append("")

        for i, mem in enumerate(recent_memories, 1):
            meta = mem["metadata"]
            importance = meta.get("importance_category", "low")
            score = meta.get("importance_score", 0.0)

            # Importance indicator
            indicator = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(importance, "⚪")

            parts.append(f"### {i}. {indicator} {mem['document']} [{importance.upper()}: {score:.1f}]")
            parts.append(f"- **Intent**: {meta.get('intent', 'N/A')}")
            parts.append(f"- **Action**: {meta.get('action', 'N/A')}")
            parts.append(f"- **Outcome**: {meta.get('outcome', 'N/A')}")

            # Add artifact info if present (deserialize JSON)
            artifacts_json = meta.get("artifacts", "{}")
            try:
                artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json
                if artifacts:
                    artifact_lines = []
                    if meta.get("has_code") and "counts" in artifacts:
                        artifact_lines.append(f"Code: {artifacts['counts']['code_snippets']} snippets")
                    if meta.get("has_files") and "file_paths" in artifacts:
                        files = artifacts.get("file_paths", [])[:3]
                        artifact_lines.append(f"Files: {', '.join(files)}")
                    if meta.get("has_architecture"):
                        artifact_lines.append("Architecture/Design discussed")

                    if artifact_lines:
                        parts.append(f"- **Artifacts**: {' | '.join(artifact_lines)}")
            except (json.JSONDecodeError, KeyError):
                pass  # Skip malformed artifacts

            parts.append("")

    # Relevant memories
    if relevant_memories:
        recent_ids = {m["id"] for m in recent_memories}
        unique_relevant = [m for m in relevant_memories if m["id"] not in recent_ids]

        if unique_relevant:
            parts.append("## 🔍 Related Context (Semantic Search)")
            parts.append("")

            for i, mem in enumerate(unique_relevant[:5], 1):
                meta = mem["metadata"]
                importance = meta.get("importance_category", "low")
                score = meta.get("importance_score", 0.0)
                combined = mem.get("combined_score", 0.0)

                indicator = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(importance, "⚪")

                parts.append(f"### {i}. {indicator} {mem['document']} [Score: {combined:.2f}]")
                parts.append(f"- **Intent**: {meta.get('intent', 'N/A')}")
                parts.append(f"- **Action**: {meta.get('action', 'N/A')}")
                parts.append(f"- **Outcome**: {meta.get('outcome', 'N/A')}")

                # Deserialize artifacts JSON
                artifacts_json = meta.get("artifacts", "{}")
                try:
                    artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json
                    if artifacts and (meta.get("has_code") or meta.get("has_files")):
                        artifact_lines = []
                        if meta.get("has_files") and "file_paths" in artifacts:
                            files = artifacts.get("file_paths", [])[:2]
                            artifact_lines.append(f"Files: {', '.join(files)}")
                        if artifact_lines:
                            parts.append(f"- **Artifacts**: {' | '.join(artifact_lines)}")
                except (json.JSONDecodeError, KeyError):
                    pass  # Skip malformed artifacts

                parts.append("")

    parts.append("---")
    parts.append("*Generated by Memory Preservation System V2 with importance weighting and multi-modal support*")

    return "\n".join(parts)


def main():
    """Enhanced SessionStart injection."""
    try:
        input_data = json.load(sys.stdin)

        session_id = input_data.get("session_id", "unknown")
        trigger = input_data.get("trigger", "compact")  # Default to compact since matcher filters it

        debug_log(f"SessionStart-V2 triggered: session={session_id}, trigger={trigger}")

        # No need to check trigger - matcher already ensures this is compact-only

        if not MEMORY_DB_PATH.exists():
            debug_log("No memory database found")
            sys.exit(0)

        client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))

        try:
            collection = client.get_collection(name="conversation_memories")
        except Exception:
            debug_log("Memory collection not found")
            sys.exit(0)

        # Get memories with importance filtering
        recent_memories = get_important_recent_memories(collection, session_id, RECENT_MEMORIES)
        debug_log(f"Retrieved {len(recent_memories)} important recent memories")

        query_text = "current task and recent work"
        relevant_memories = get_relevant_memories(collection, query_text, session_id, TOP_K_MEMORIES)
        debug_log(f"Retrieved {len(relevant_memories)} relevant memories")

        if not recent_memories and not relevant_memories:
            debug_log("No memories to inject")
            sys.exit(0)

        # Format enhanced context
        additional_context = format_enhanced_context(recent_memories, relevant_memories)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional_context
            }
        }

        print(json.dumps(output))
        debug_log(f"Injected {len(recent_memories)} recent + {len(relevant_memories)} relevant (importance-weighted)")

    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        import traceback
        debug_log(traceback.format_exc())

    sys.exit(0)


if __name__ == "__main__":
    main()
