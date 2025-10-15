#!/usr/bin/env python3
"""
Knowledge Graph Builder for Memory System
==========================================
Builds a knowledge graph from extracted entities and computes
PageRank-based importance scores.

Graph Structure:
- Nodes: Entities (files, functions, bugs, features, decisions, tools)
- Edges: Relationships (MODIFIES, FIXES, USES, IMPLEMENTS, etc.)
- Node Properties: type, name, importance, pagerank, access_count
- Edge Properties: relation_type, confidence, co_occurrence_count

Usage:
    from knowledge_graph import MemoryKnowledgeGraph

    graph = MemoryKnowledgeGraph(memory_db_path)
    graph.build_from_memories(session_id="all")
    graph.compute_centrality()

    # Get boosted importance for an entity
    boosted_score = graph.get_entity_importance("adaptive K retrieval")
"""

import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import chromadb
from entity_extractor import extract_entities_from_memory, Entity, Relationship


class MemoryKnowledgeGraph:
    """Knowledge graph built from memory entities."""

    def __init__(self, memory_db_path: str):
        """Initialize with path to ChromaDB memory database."""
        self.memory_db_path = Path(memory_db_path)
        self.graph = nx.DiGraph()  # Directed graph for relationships
        self.entity_to_memories = {}  # Map entity -> memory IDs
        self.pagerank_scores = {}

    def build_from_memories(self, session_id: Optional[str] = None, limit: Optional[int] = None):
        """Build graph from all memories (or specific session)."""

        print(f"🔍 Loading memories from {self.memory_db_path}...")

        # Connect to ChromaDB
        client = chromadb.PersistentClient(path=str(self.memory_db_path))
        try:
            collection = client.get_collection("conversation_memories")
        except Exception as e:
            print(f"❌ Error loading collection: {e}")
            return

        # Get memories
        if session_id and session_id != "all":
            results = collection.get(
                where={"session_id": session_id},
                include=["documents", "metadatas"]
            )
        else:
            results = collection.get(
                include=["documents", "metadatas"],
                limit=limit
            )

        if not results or not results.get("ids"):
            print("❌ No memories found!")
            return

        total = len(results["ids"])
        print(f"✅ Found {total} memories")
        print()

        # Extract entities from each memory
        print("🔬 Extracting entities...")
        all_entities = []
        all_relationships = []

        for i, (mem_id, doc, meta) in enumerate(zip(results["ids"], results["documents"], results["metadatas"])):
            entities, relationships = extract_entities_from_memory(doc, meta)

            # Track which memories contain which entities
            for entity in entities:
                if entity.name not in self.entity_to_memories:
                    self.entity_to_memories[entity.name] = []
                self.entity_to_memories[entity.name].append(mem_id)

            all_entities.extend(entities)
            all_relationships.extend(relationships)

            if (i + 1) % 50 == 0:
                print(f"   Processed {i+1}/{total} memories...")

        print(f"✅ Extracted {len(all_entities)} entities")
        print(f"✅ Extracted {len(all_relationships)} relationships")
        print()

        # Build graph
        print("🕸️  Building knowledge graph...")
        self._build_graph_from_entities(all_entities, all_relationships)

        print(f"✅ Graph built:")
        print(f"   Nodes: {self.graph.number_of_nodes()}")
        print(f"   Edges: {self.graph.number_of_edges()}")
        print()

    def _build_graph_from_entities(self, entities: List[Entity], relationships: List[Relationship]):
        """Build NetworkX graph from entities and relationships."""

        # Add nodes (entities)
        for entity in entities:
            if not self.graph.has_node(entity.name):
                self.graph.add_node(
                    entity.name,
                    entity_type=entity.entity_type,
                    confidence=entity.confidence,
                    access_count=len(self.entity_to_memories.get(entity.name, [])),
                )
            else:
                # Update access count if entity appears multiple times
                current_count = self.graph.nodes[entity.name].get('access_count', 0)
                self.graph.nodes[entity.name]['access_count'] = current_count + 1

        # Add edges (relationships)
        for rel in relationships:
            if self.graph.has_node(rel.source) and self.graph.has_node(rel.target):
                if self.graph.has_edge(rel.source, rel.target):
                    # Increase co-occurrence count
                    self.graph[rel.source][rel.target]['co_occurrence'] += 1
                else:
                    self.graph.add_edge(
                        rel.source,
                        rel.target,
                        relation_type=rel.relation_type,
                        confidence=rel.confidence,
                        co_occurrence=1
                    )

    def compute_centrality(self):
        """Compute PageRank and other centrality metrics."""

        print("📊 Computing centrality metrics...")

        if self.graph.number_of_nodes() == 0:
            print("⚠️  Empty graph, skipping centrality")
            return

        # PageRank (importance based on connections)
        try:
            self.pagerank_scores = nx.pagerank(self.graph, alpha=0.85, max_iter=100)
            print(f"✅ PageRank computed for {len(self.pagerank_scores)} nodes")
        except Exception as e:
            print(f"⚠️  PageRank failed: {e}")
            self.pagerank_scores = {node: 1.0 for node in self.graph.nodes()}

        # Betweenness centrality (importance as bridge between concepts)
        try:
            betweenness = nx.betweenness_centrality(self.graph)
            for node, score in betweenness.items():
                self.graph.nodes[node]['betweenness'] = score
            print(f"✅ Betweenness centrality computed")
        except Exception as e:
            print(f"⚠️  Betweenness failed: {e}")

        # Degree centrality (number of connections)
        try:
            degree_cent = nx.degree_centrality(self.graph)
            for node, score in degree_cent.items():
                self.graph.nodes[node]['degree_centrality'] = score
            print(f"✅ Degree centrality computed")
        except Exception as e:
            print(f"⚠️  Degree centrality failed: {e}")

        print()

    def get_entity_importance(self, entity_name: str, base_importance: float = 10.0) -> float:
        """
        Get boosted importance score for an entity based on graph centrality.

        Formula: boosted_importance = base_importance * (1 + pagerank * 10)

        This means:
        - Low pagerank (0.001): ~1% boost
        - Medium pagerank (0.01): ~10% boost
        - High pagerank (0.1): ~100% boost (doubles importance!)
        """

        if entity_name not in self.pagerank_scores:
            return base_importance

        pagerank = self.pagerank_scores[entity_name]
        boost_factor = 1 + (pagerank * 10)

        return base_importance * boost_factor

    def get_top_entities(self, entity_type: Optional[str] = None, limit: int = 20) -> List[Tuple[str, float]]:
        """Get top entities by PageRank (optionally filtered by type)."""

        if not self.pagerank_scores:
            return []

        # Filter by type if specified
        if entity_type:
            filtered = [
                (node, score) for node, score in self.pagerank_scores.items()
                if self.graph.nodes[node].get('entity_type') == entity_type
            ]
        else:
            filtered = list(self.pagerank_scores.items())

        # Sort by PageRank descending
        filtered.sort(key=lambda x: x[1], reverse=True)

        return filtered[:limit]

    def get_related_entities(self, entity_name: str, max_hops: int = 2) -> List[str]:
        """Get entities related to the given entity within max_hops."""

        if entity_name not in self.graph:
            return []

        # BFS to find all nodes within max_hops
        related = set()
        visited = {entity_name}
        queue = [(entity_name, 0)]

        while queue:
            current, hops = queue.pop(0)

            if hops >= max_hops:
                continue

            # Get successors and predecessors
            neighbors = list(self.graph.successors(current)) + list(self.graph.predecessors(current))

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    related.add(neighbor)
                    queue.append((neighbor, hops + 1))

        return list(related)

    def save_graph(self, output_path: str):
        """Save graph to file for visualization."""
        nx.write_graphml(self.graph, output_path)
        print(f"💾 Graph saved to: {output_path}")

    def get_statistics(self) -> Dict:
        """Get graph statistics."""

        if self.graph.number_of_nodes() == 0:
            return {"error": "Empty graph"}

        # Entity type distribution
        type_counts = {}
        for node in self.graph.nodes():
            entity_type = self.graph.nodes[node].get('entity_type', 'unknown')
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "entity_types": type_counts,
            "avg_degree": sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes(),
            "density": nx.density(self.graph),
        }


if __name__ == "__main__":
    """Test knowledge graph building."""
    from pathlib import Path

    MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"

    # Build graph
    kg = MemoryKnowledgeGraph(str(MEMORY_DB_PATH))
    kg.build_from_memories(session_id="all")
    kg.compute_centrality()

    # Show statistics
    print("=" * 80)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("=" * 80)
    stats = kg.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    print()

    # Show top entities by type
    print("=" * 80)
    print("TOP ENTITIES BY TYPE")
    print("=" * 80)

    for entity_type in ["FILE", "FUNCTION", "FEATURE", "TOOL", "BUG"]:
        print(f"\n🏆 Top {entity_type}s by PageRank:")
        top = kg.get_top_entities(entity_type=entity_type, limit=5)
        for i, (name, score) in enumerate(top, 1):
            access_count = kg.graph.nodes[name].get('access_count', 0)
            print(f"   {i}. {name[:60]}")
            print(f"      PageRank: {score:.6f} | Appears in {access_count} memories")
