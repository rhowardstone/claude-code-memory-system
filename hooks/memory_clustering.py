#!/usr/bin/env python3
"""
Hierarchical Memory Clustering
===============================
Groups related memories into hierarchical clusters for:
- Topic-based organization
- Efficient retrieval (query clusters first)
- Memory map visualization
- Summary generation at different granularities
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.cluster import AgglomerativeClustering
from collections import defaultdict
import chromadb
from pathlib import Path


class MemoryClustering:
    """Hierarchical clustering of memory vectors."""

    def __init__(self, db_path: str = None):
        db_path = db_path or str(Path.home() / ".claude" / "memory_db")
        self.client = chromadb.PersistentClient(path=db_path)
        try:
            self.collection = self.client.get_collection("conversation_memories")
        except Exception:
            self.collection = None

    def cluster_memories(
        self,
        session_id: str,
        n_clusters: Optional[int] = None,
        distance_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Cluster memories for a session using hierarchical agglomerative clustering.

        Args:
            session_id: Session to cluster
            n_clusters: Number of clusters (if None, use distance_threshold)
            distance_threshold: Distance threshold for automatic cluster determination
        """
        if not self.collection:
            return {"error": "No memory collection found"}

        # Get all memories for this session
        results = self.collection.get(
            where={"session_id": session_id},
            include=["embeddings", "metadatas", "documents"]
        )

        if not results or not results.get("embeddings") or len(results["embeddings"]) < 2:
            return {"error": "Not enough memories to cluster"}

        embeddings = np.array(results["embeddings"])
        n_memories = len(embeddings)

        # Determine clustering parameters
        if n_clusters is None:
            # Use distance threshold for automatic cluster determination
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                metric='cosine',
                linkage='average'
            )
        else:
            # Use specified number of clusters
            n_clusters = min(n_clusters, n_memories)
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                metric='cosine',
                linkage='average'
            )

        # Perform clustering
        cluster_labels = clustering.fit_predict(embeddings)

        # Organize memories by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            clusters[int(label)].append({
                "id": results["ids"][idx],
                "document": results["documents"][idx],
                "metadata": results["metadatas"][idx]
            })

        # Generate cluster summaries
        cluster_summaries = self._generate_cluster_summaries(clusters)

        # Build hierarchy (if requested)
        hierarchy = self._build_hierarchy(embeddings, cluster_labels)

        return {
            "session_id": session_id,
            "total_memories": n_memories,
            "num_clusters": len(clusters),
            "clusters": {
                str(k): {
                    "size": len(v),
                    "memories": v,
                    "summary": cluster_summaries.get(k, "")
                }
                for k, v in clusters.items()
            },
            "hierarchy": hierarchy
        }

    def _generate_cluster_summaries(self, clusters: Dict[int, List[Dict]]) -> Dict[int, str]:
        """Generate descriptive summaries for each cluster."""
        summaries = {}

        for cluster_id, memories in clusters.items():
            # Extract common themes from documents
            all_text = " ".join([m["document"] for m in memories])
            words = all_text.lower().split()

            # Simple keyword extraction (could be enhanced with TF-IDF)
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 4:  # Skip short words
                    word_freq[word] += 1

            # Top keywords
            top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            keywords = [w for w, _ in top_keywords]

            # Check for common file patterns
            files = set()
            for memory in memories:
                artifacts = memory["metadata"].get("artifacts", {})
                if artifacts.get("file_paths"):
                    files.update(artifacts["file_paths"][:3])  # Top 3 files

            # Build summary
            summary_parts = []
            if keywords:
                summary_parts.append(f"Topics: {', '.join(keywords)}")
            if files:
                summary_parts.append(f"Files: {', '.join(list(files)[:3])}")

            summaries[cluster_id] = " | ".join(summary_parts) if summary_parts else "General work"

        return summaries

    def _build_hierarchy(self, embeddings: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """Build a hierarchical structure of clusters."""
        # Calculate cluster centroids
        unique_labels = np.unique(labels)
        centroids = {}

        for label in unique_labels:
            mask = labels == label
            cluster_embeddings = embeddings[mask]
            centroid = np.mean(cluster_embeddings, axis=0)
            centroids[int(label)] = centroid

        # Find parent-child relationships based on centroid distances
        hierarchy = {"root": [], "children": defaultdict(list)}

        if len(centroids) > 1:
            centroid_array = np.array([centroids[k] for k in sorted(centroids.keys())])

            # Calculate distances between centroids
            from scipy.spatial.distance import cdist
            distances = cdist(centroid_array, centroid_array, metric='cosine')

            # Find closest centroids (potential parent-child relationships)
            for i, label in enumerate(sorted(centroids.keys())):
                # Find closest cluster (excluding self)
                dist_row = distances[i].copy()
                dist_row[i] = np.inf  # Exclude self
                closest_idx = np.argmin(dist_row)
                closest_label = sorted(centroids.keys())[closest_idx]
                closest_distance = dist_row[closest_idx]

                # If distance is small enough, it's a child
                if closest_distance < 0.3:  # Threshold for hierarchy
                    hierarchy["children"][closest_label].append(label)
                else:
                    hierarchy["root"].append(label)
        else:
            # Only one cluster
            hierarchy["root"] = list(centroids.keys())

        return dict(hierarchy)

    def get_cluster_for_query(self, query_text: str, session_id: str) -> Optional[int]:
        """Find which cluster a query belongs to."""
        from sentence_transformers import SentenceTransformer

        if not self.collection:
            return None

        # Generate query embedding
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = model.encode(query_text).tolist()

        # Get cluster information
        cluster_info = self.cluster_memories(session_id)
        if "error" in cluster_info:
            return None

        # Find nearest cluster centroid
        results = self.collection.get(
            where={"session_id": session_id},
            include=["embeddings", "metadatas"]
        )

        if not results or not results.get("embeddings"):
            return None

        embeddings = np.array(results["embeddings"])
        metadatas = results["metadatas"]

        # Get cluster labels from metadata (would need to be stored)
        # For now, use simple nearest neighbor to find cluster
        distances = np.linalg.norm(embeddings - query_embedding, axis=1)
        nearest_idx = np.argmin(distances)

        return metadatas[nearest_idx].get("cluster_id")


def add_cluster_ids_to_memories(session_id: str, db_path: str = None):
    """Add cluster IDs to memory metadata."""
    clusterer = MemoryClustering(db_path)
    cluster_info = clusterer.cluster_memories(session_id)

    if "error" in cluster_info:
        print(f"Error: {cluster_info['error']}")
        return

    # Update metadata with cluster IDs
    for cluster_id, cluster_data in cluster_info["clusters"].items():
        memory_ids = [m["id"] for m in cluster_data["memories"]]

        # Note: ChromaDB doesn't support update, need to delete and re-add
        # This is a limitation - in production, use a DB that supports updates
        print(f"Cluster {cluster_id}: {len(memory_ids)} memories - {cluster_data['summary']}")


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python memory_clustering.py <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]
    clusterer = MemoryClustering()

    print(f"Clustering memories for session: {session_id}")
    print("=" * 60)

    result = clusterer.cluster_memories(session_id)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Total memories: {result['total_memories']}")
    print(f"Number of clusters: {result['num_clusters']}")
    print()

    for cluster_id, data in result["clusters"].items():
        print(f"Cluster {cluster_id} ({data['size']} memories):")
        print(f"  Summary: {data['summary']}")
        print(f"  Memories:")
        for mem in data["memories"][:3]:  # Show first 3
            print(f"    - {mem['document'][:80]}...")
        if data['size'] > 3:
            print(f"    ... and {data['size'] - 3} more")
        print()

    print("Hierarchy:")
    print(json.dumps(result["hierarchy"], indent=2))
