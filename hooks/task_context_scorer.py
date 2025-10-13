#!/usr/bin/env python3
"""
Task-Context Aware Importance Scoring
======================================
Dynamically boosts importance of memories based on current task context.

Instead of static global PageRank, this computes TASK-SPECIFIC importance:
- Extract entities from current query/task
- Find those entities in knowledge graph
- Traverse to related entities (1-2 hops)
- Boost memories containing task-relevant entities

Example:
    Query: "fix bugs in adaptive K retrieval"

    Entities extracted: ["adaptive K", "retrieval", "bugs"]

    Graph traversal finds related:
    - sessionstart_memory_injector_v5.py (implements adaptive K + task-context)
    - nomic-embed (used by retrieval)
    - ChromaDB (storage for retrieval)

    Result: Memories about these files/tools get 2-3x importance boost!

This makes retrieval task-aware: "working on auth.py" surfaces auth memories,
"fixing retrieval bugs" surfaces retrieval memories.
"""

from typing import Dict, List, Set, Tuple
from entity_extractor import EntityExtractor
from knowledge_graph import MemoryKnowledgeGraph


class TaskContextScorer:
    """Compute task-specific importance scores using knowledge graph."""

    def __init__(self, knowledge_graph: MemoryKnowledgeGraph):
        """Initialize with pre-built knowledge graph."""
        self.kg = knowledge_graph

    def extract_task_entities(self, query_text: str) -> List[str]:
        """Extract entities from current query/task."""

        # Use entity extractor to parse query
        entities = EntityExtractor.extract_entities(query_text)

        # Return unique entity names
        return list(set([e.name for e in entities]))

    def find_related_entities(self, task_entities: List[str], max_hops: int = 2) -> Dict[str, float]:
        """
        Find entities related to task entities in knowledge graph.

        Returns dict of {entity_name: relevance_score}
        where relevance_score decreases with graph distance:
        - 0 hops (exact match): 1.0
        - 1 hop away: 0.5
        - 2 hops away: 0.25
        """

        related = {}

        for task_entity in task_entities:
            # Exact match gets highest score
            if task_entity in self.kg.graph:
                related[task_entity] = 1.0

                # Get 1-hop neighbors
                neighbors_1hop = self.kg.get_related_entities(task_entity, max_hops=1)
                for neighbor in neighbors_1hop:
                    if neighbor not in related or related[neighbor] < 0.5:
                        related[neighbor] = 0.5

                # Get 2-hop neighbors
                neighbors_2hop = self.kg.get_related_entities(task_entity, max_hops=2)
                for neighbor in neighbors_2hop:
                    if neighbor not in related or related[neighbor] < 0.25:
                        related[neighbor] = 0.25

        return related

    def score_memory_for_task(
        self,
        memory_text: str,
        memory_metadata: Dict,
        task_entities: Dict[str, float],
        base_importance: float
    ) -> float:
        """
        Compute task-specific importance for a memory.

        Formula:
            task_importance = base_importance * (1 + task_boost)

        where task_boost = sum of relevance scores for entities in memory

        Example:
            - Memory contains "adaptive K" (relevance 1.0) and "nomic-embed" (relevance 0.5)
            - task_boost = 1.0 + 0.5 = 1.5
            - base_importance = 15.0
            - task_importance = 15.0 * (1 + 1.5) = 37.5 (2.5x boost!)
        """

        # Combine memory text with metadata for entity extraction
        full_text = f"{memory_text} {memory_metadata.get('intent', '')} {memory_metadata.get('action', '')}"

        # Extract entities from memory
        memory_entities = EntityExtractor.extract_entities(full_text)
        memory_entity_names = set([e.name for e in memory_entities])

        # Calculate task boost based on overlap with task-relevant entities
        task_boost = 0.0
        matched_entities = []

        for entity_name, relevance_score in task_entities.items():
            if entity_name in memory_entity_names:
                task_boost += relevance_score
                matched_entities.append((entity_name, relevance_score))

        # Apply boost to base importance
        task_importance = base_importance * (1 + task_boost)

        return task_importance, matched_entities

    def score_memories_for_task(
        self,
        query_text: str,
        memories: List[Tuple[str, Dict, float]],
        max_hops: int = 2
    ) -> List[Tuple[str, Dict, float, float, List]]:
        """
        Score all memories for given task/query.

        Args:
            query_text: Current query/task description
            memories: List of (document, metadata, base_importance)
            max_hops: How far to traverse graph

        Returns:
            List of (document, metadata, base_importance, task_importance, matched_entities)
            sorted by task_importance descending
        """

        # Extract entities from query
        task_entity_list = self.extract_task_entities(query_text)

        if not task_entity_list:
            # No entities extracted, return with base importance
            return [(doc, meta, base_imp, base_imp, []) for doc, meta, base_imp in memories]

        # Find related entities in graph
        task_entities = self.find_related_entities(task_entity_list, max_hops=max_hops)

        # Score each memory
        scored = []
        for doc, meta, base_imp in memories:
            task_imp, matched = self.score_memory_for_task(doc, meta, task_entities, base_imp)
            scored.append((doc, meta, base_imp, task_imp, matched))

        # Sort by task importance descending
        scored.sort(key=lambda x: x[3], reverse=True)

        return scored

    def get_task_context_summary(self, query_text: str, max_hops: int = 2) -> Dict:
        """
        Get summary of task context for debugging/display.

        Returns info about what entities were extracted and what's related.
        """

        task_entities = self.extract_task_entities(query_text)
        related_entities = self.find_related_entities(task_entities, max_hops=max_hops)

        # Get PageRank scores for context
        entity_scores = []
        for entity, relevance in related_entities.items():
            pagerank = self.kg.pagerank_scores.get(entity, 0.0)
            entity_scores.append({
                "name": entity,
                "relevance": relevance,
                "pagerank": pagerank,
                "type": self.kg.graph.nodes[entity].get('entity_type', 'unknown') if entity in self.kg.graph else 'unknown'
            })

        # Sort by relevance
        entity_scores.sort(key=lambda x: x['relevance'], reverse=True)

        return {
            "query": query_text,
            "task_entities": task_entities,
            "related_entities": entity_scores[:20],  # Top 20
            "total_related": len(related_entities)
        }


def demo_task_context_scoring():
    """Demo task-context scoring with example queries."""

    from pathlib import Path

    MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"

    print("=" * 80)
    print("TASK-CONTEXT SCORING DEMO")
    print("=" * 80)
    print()

    # Build knowledge graph
    print("🔍 Building knowledge graph...")
    kg = MemoryKnowledgeGraph(str(MEMORY_DB_PATH))
    kg.build_from_memories(session_id="all")
    kg.compute_centrality()
    print()

    # Create task scorer
    scorer = TaskContextScorer(kg)

    # Test different queries
    test_queries = [
        "improve adaptive K retrieval system",
        "fix bugs in memory migration",
        "update CLAUDE.md documentation",
        "query memories about embedding model"
    ]

    for query in test_queries:
        print("=" * 80)
        print(f"Query: '{query}'")
        print("=" * 80)

        context = scorer.get_task_context_summary(query, max_hops=2)

        print(f"\n📌 Task entities extracted: {', '.join(context['task_entities']) if context['task_entities'] else 'None'}")
        print(f"🕸️  Related entities found: {context['total_related']}")
        print()

        if context['related_entities']:
            print("🎯 Top related entities:")
            for i, entity in enumerate(context['related_entities'][:10], 1):
                print(f"   {i}. {entity['name'][:50]} ({entity['type']})")
                print(f"      Relevance: {entity['relevance']:.2f} | PageRank: {entity['pagerank']:.6f}")

        print()


if __name__ == "__main__":
    demo_task_context_scoring()
