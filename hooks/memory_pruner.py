#!/usr/bin/env python3
"""
Memory Pruner
=============
Automatically prunes low-importance, old, or redundant memories to keep the vector DB efficient.

Pruning strategies:
1. Age-based: Remove very old low-importance memories
2. Importance-based: Keep only high-value memories beyond certain age
3. Redundancy-based: Remove near-duplicate memories
4. Capacity-based: Keep total memory count under threshold
"""

import chromadb
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import numpy as np


class MemoryPruner:
    """Manages memory pruning policies."""

    # Pruning configuration
    MAX_MEMORIES_PER_SESSION = 500  # Maximum memories per session
    OLD_MEMORY_DAYS = 90  # Memories older than this are candidates for pruning
    LOW_IMPORTANCE_THRESHOLD = 3.0  # Below this score, old memories are pruned
    REDUNDANCY_THRESHOLD = 0.95  # Cosine similarity above this = redundant
    KEEP_CRITICAL_DAYS = 365  # Always keep critical memories for this long

    def __init__(self, db_path: str = None):
        db_path = db_path or str(Path.home() / ".claude" / "memory_db")
        self.client = chromadb.PersistentClient(path=db_path)
        try:
            self.collection = self.client.get_collection("conversation_memories")
        except Exception:
            self.collection = None

    def prune_session_memories(self, session_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Prune memories for a specific session."""
        if not self.collection:
            return {"error": "No memory collection found"}

        # Get all memories for this session
        results = self.collection.get(
            where={"session_id": session_id},
            include=["metadatas", "embeddings", "documents"]
        )

        if not results or not results.get("ids"):
            return {"pruned": 0, "kept": 0, "reason": "no memories found"}

        total_memories = len(results["ids"])
        memories_to_delete = []
        pruning_reasons = {}

        # Strategy 1: Age + Importance based pruning
        for i, metadata in enumerate(results["metadatas"]):
            memory_id = results["ids"][i]
            timestamp = metadata.get("timestamp")
            importance_score = metadata.get("importance_score", 0.0)
            importance_category = metadata.get("importance_category", "low")

            if timestamp:
                try:
                    memory_time = datetime.fromisoformat(timestamp)
                    age_days = (datetime.now() - memory_time).days

                    # Rule: Remove old low-importance memories
                    if age_days > self.OLD_MEMORY_DAYS and importance_score < self.LOW_IMPORTANCE_THRESHOLD:
                        if importance_category != "critical" or age_days > self.KEEP_CRITICAL_DAYS:
                            memories_to_delete.append(memory_id)
                            pruning_reasons[memory_id] = f"old ({age_days}d) + low importance ({importance_score:.1f})"

                except Exception:
                    pass

        # Strategy 2: Redundancy-based pruning
        if results.get("embeddings"):
            embeddings = np.array(results["embeddings"])

            # Find near-duplicate memories
            for i in range(len(embeddings)):
                if results["ids"][i] in memories_to_delete:
                    continue

                for j in range(i + 1, len(embeddings)):
                    if results["ids"][j] in memories_to_delete:
                        continue

                    # Calculate cosine similarity
                    similarity = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )

                    # Convert to scalar if array (fixes numpy boolean ambiguity error)
                    sim_value = float(similarity) if isinstance(similarity, (int, float, np.floating)) else float(similarity.item())

                    if sim_value > self.REDUNDANCY_THRESHOLD:
                        # Keep the one with higher importance
                        score_i = results["metadatas"][i].get("importance_score", 0.0)
                        score_j = results["metadatas"][j].get("importance_score", 0.0)

                        if score_i >= score_j:
                            to_delete = results["ids"][j]
                        else:
                            to_delete = results["ids"][i]

                        if to_delete not in memories_to_delete:
                            memories_to_delete.append(to_delete)
                            pruning_reasons[to_delete] = f"redundant (similarity: {sim_value:.2f})"

        # Strategy 3: Capacity-based pruning (if still over limit)
        remaining = total_memories - len(memories_to_delete)
        if remaining > self.MAX_MEMORIES_PER_SESSION:
            # Sort by importance score and keep only top MAX_MEMORIES
            scored_memories = [
                (results["ids"][i], results["metadatas"][i].get("importance_score", 0.0))
                for i in range(len(results["ids"]))
                if results["ids"][i] not in memories_to_delete
            ]
            scored_memories.sort(key=lambda x: x[1], reverse=True)

            # Delete lowest scoring memories beyond capacity
            for memory_id, score in scored_memories[self.MAX_MEMORIES_PER_SESSION:]:
                memories_to_delete.append(memory_id)
                pruning_reasons[memory_id] = f"capacity limit (score: {score:.1f})"

        # Perform deletion
        pruned_count = 0
        if memories_to_delete and not dry_run:
            try:
                self.collection.delete(ids=memories_to_delete)
                pruned_count = len(memories_to_delete)
            except Exception as e:
                return {"error": f"Failed to delete memories: {e}"}

        return {
            "total_memories": total_memories,
            "pruned": len(memories_to_delete) if dry_run else pruned_count,
            "kept": total_memories - len(memories_to_delete),
            "dry_run": dry_run,
            "reasons": pruning_reasons if dry_run else None
        }

    def prune_all_sessions(self, dry_run: bool = False) -> Dict[str, Any]:
        """Prune memories across all sessions."""
        if not self.collection:
            return {"error": "No memory collection found"}

        # Get unique session IDs
        all_results = self.collection.get(include=["metadatas"])
        if not all_results or not all_results.get("metadatas"):
            return {"total_pruned": 0, "sessions": 0}

        session_ids = set(meta.get("session_id") for meta in all_results["metadatas"] if meta.get("session_id"))

        total_pruned = 0
        session_results = {}

        for session_id in session_ids:
            result = self.prune_session_memories(session_id, dry_run=dry_run)
            session_results[session_id] = result
            total_pruned += result.get("pruned", 0)

        return {
            "total_pruned": total_pruned,
            "sessions_processed": len(session_ids),
            "session_details": session_results,
            "dry_run": dry_run
        }

    def get_pruning_statistics(self, session_id: str = None) -> Dict[str, Any]:
        """Get statistics about what would be pruned."""
        if session_id:
            return self.prune_session_memories(session_id, dry_run=True)
        else:
            return self.prune_all_sessions(dry_run=True)


if __name__ == "__main__":
    import sys
    import json

    pruner = MemoryPruner()

    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"Pruning statistics for session: {session_id}")
        stats = pruner.get_pruning_statistics(session_id)
    else:
        print("Pruning statistics for all sessions:")
        stats = pruner.get_pruning_statistics()

    print(json.dumps(stats, indent=2))

    if not stats.get("error"):
        print(f"\nWould prune {stats.get('total_pruned', stats.get('pruned', 0))} memories")
        print("Run with --execute to actually prune")

        if "--execute" in sys.argv:
            print("\nExecuting pruning...")
            result = pruner.prune_all_sessions(dry_run=False) if len(sys.argv) == 1 else pruner.prune_session_memories(sys.argv[1], dry_run=False)
            print(f"Pruned {result.get('pruned', 0)} memories")
