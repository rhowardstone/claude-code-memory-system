#!/usr/bin/env python3
"""
Test Task-Context Scoring with Real Session Data
=================================================
Simulates SessionStart with accumulated context from recent conversation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "memory-hooks"))

from task_context_scorer import TaskContextScorer
from knowledge_graph import MemoryKnowledgeGraph

def test_real_session_context():
    """Test with accumulated context from THIS session."""

    MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"

    print("=" * 80)
    print("TASK-CONTEXT SCORING - REAL SESSION TEST")
    print("=" * 80)
    print()

    # Build knowledge graph
    print("🔍 Building knowledge graph...")
    kg = MemoryKnowledgeGraph(str(MEMORY_DB_PATH))
    kg.build_from_memories(session_id="all")
    kg.compute_centrality()
    print()

    scorer = TaskContextScorer(kg)

    # REALISTIC accumulated context - last several exchanges about our work
    accumulated_context = """
    Yeah central to *the current task at hand* is kinda the idea yeah

    Great! And what would you do next? What's working, what isn't?
    Were those memories more relevant to your query? Does that mirror the sessionStart hook?
    Can you trigger a compaction? IF not, can you check manually what the new "relevant memories"
    *would* be to say, this moment in the convo, or up to the last compaction, if that's allowed?

    Yeah you'll need to clear and re-establish all memories, then shouldn't the hooks do that for
    future sessions? What about sessions I have already running?

    Yeah those like 'what it gives' for the transcript for the relevant memories isn't all too useful,
    it's like fragments

    hierarchical information -- like.. imaging we are "the human" just scrolling through and trying
    to navigate for any individual task -- but we want yeah some kind of *access* to the full transcript,
    even if that's not what the model auto-gets, but with the query system could easily access,
    based on what the sessionstart provides

    adaptive K retrieval memory preservation embedding migration full transcripts knowledge graph
    """

    print("📝 Accumulated Context (simulating recent conversation):")
    print(accumulated_context[:300] + "...")
    print()

    # Get task context
    context = scorer.get_task_context_summary(accumulated_context, max_hops=2)

    print("=" * 80)
    print("TASK CONTEXT ANALYSIS")
    print("=" * 80)
    print()

    print(f"📌 Task entities extracted ({len(context['task_entities'])}):")
    for entity in context['task_entities'][:15]:
        print(f"   - {entity}")
    print()

    print(f"🕸️  Total related entities in graph: {context['total_related']}")
    print()

    print("🎯 Top 15 task-relevant entities (ranked by relevance + PageRank):")
    for i, entity in enumerate(context['related_entities'][:15], 1):
        entity_type = entity['type']
        name = entity['name'][:60]
        relevance = entity['relevance']
        pagerank = entity['pagerank']

        # Calculate combined score
        combined = relevance * (1 + pagerank * 10)

        type_emoji = {
            "FILE": "📄",
            "FUNCTION": "⚙️",
            "FEATURE": "✨",
            "TOOL": "🔧",
            "BUG": "🐛",
            "DECISION": "🎯"
        }.get(entity_type, "📌")

        print(f"   {i}. {type_emoji} {name}")
        print(f"      Type: {entity_type} | Relevance: {relevance:.2f} | PageRank: {pagerank:.6f} | Combined: {combined:.3f}")

    print()
    print("=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print()
    print("✅ Memories mentioning these entities will get boosted importance!")
    print("✅ High relevance (1.0) = exact match with query entities")
    print("✅ Medium relevance (0.5) = 1 hop away in knowledge graph")
    print("✅ Low relevance (0.25) = 2 hops away in knowledge graph")
    print()
    print("Example: Memory about 'nomic-embed migration' would get:")
    print("   - Base importance: 15.0")
    print("   - Task boost: 1.0 (nomic-embed) + 1.0 (migration) = 2.0")
    print("   - Task importance: 15.0 * (1 + 2.0) = 45.0 (3x boost!)")

if __name__ == "__main__":
    test_real_session_context()
