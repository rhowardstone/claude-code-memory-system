#!/usr/bin/env python3
"""
SessionStart Memory Injector - Task-Context Aware with Knowledge Graph
=======================================================================
Version: See __version__.py

Features:
- nomic-embed-text-v1.5 (768-dim, 8192 token context)
- Adaptive K retrieval (0-20 memories based on quality)
- Full transcript storage with proper framing
- Knowledge graph integration
- Task-context aware scoring
- Entity extraction from query
- Graph traversal to related entities
- Importance boosting for task-relevant memories

How it works:
1. Extract query entities from SessionStart context
2. Find related entities in knowledge graph (1-2 hops)
3. Score memories based on task relevance
4. Apply adaptive K retrieval
5. Return 0-20 highest-quality, most-relevant memories
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import time

try:
    from __version__ import __version__, SESSIONSTART_VERSION
    import chromadb
    from sentence_transformers import SentenceTransformer
    from knowledge_graph import MemoryKnowledgeGraph
    from task_context_scorer import TaskContextScorer
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Configuration
MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"  # 768d, 8192 token context
TOP_K_MEMORIES = 20  # Maximum memories (adaptive will return 0-20)
RECENT_MEMORIES = 4
MIN_IMPORTANCE = 5.0  # Only show medium+ importance
MIN_SIMILARITY = 0.35  # Higher similarity threshold
MAX_CONTENT_LENGTH = 1000  # Don't truncate too aggressively
DEBUG_LOG = Path.home() / ".claude" / "memory_hooks_debug.log"

# Knowledge graph cache (built once per session)
_kg_cache = None
_kg_cache_time = 0
KG_CACHE_TTL = 300  # Rebuild graph every 5 minutes


def debug_log(msg: str):
    """Append debug message to log."""
    try:
        with open(DEBUG_LOG, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [SessionStart-{SESSIONSTART_VERSION}] {msg}\n")
    except Exception:
        pass


def get_or_build_knowledge_graph() -> MemoryKnowledgeGraph:
    """Get cached knowledge graph or build new one."""
    global _kg_cache, _kg_cache_time

    current_time = time.time()

    # Use cache if recent
    if _kg_cache and (current_time - _kg_cache_time) < KG_CACHE_TTL:
        return _kg_cache

    # Build new graph
    debug_log("Building knowledge graph...")
    kg = MemoryKnowledgeGraph(str(MEMORY_DB_PATH))
    kg.build_from_memories(session_id="all")
    kg.compute_centrality()

    _kg_cache = kg
    _kg_cache_time = current_time

    debug_log(f"Knowledge graph built: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")

    return kg


def extract_smart_summary(metadata: Dict[str, Any], document: str) -> Dict[str, Any]:
    """Extract smart summary from memory with artifact details."""
    summary = {
        "text": document,
        "importance": metadata.get("importance_score", 0.0),
        "category": metadata.get("importance_category", "unknown"),
        "timestamp": metadata.get("timestamp", ""),
        "files": [],
        "bugs_fixed": [],
        "decisions": [],
        "functions": []
    }

    # Extract artifacts
    artifacts_json = metadata.get("artifacts", "{}")
    try:
        artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json

        # Files involved
        if artifacts.get("file_paths"):
            summary["files"] = artifacts["file_paths"][:5]

        # Extract bug/error info
        error_msgs = artifacts.get("error_messages", [])
        if error_msgs:
            summary["bugs_fixed"] = error_msgs[:3]

        # Extract code snippets for function names
        code_snippets = artifacts.get("code_snippets", [])
        for snippet in code_snippets[:3]:
            if snippet.get("type") == "block":
                code = snippet.get("code", "")
                import re
                func_matches = re.findall(r'(?:def|function|const|let|class)\s+(\w+)', code)
                summary["functions"].extend(func_matches[:3])

    except (json.JSONDecodeError, KeyError, Exception) as e:
        debug_log(f"Error parsing artifacts: {e}")

    # Extract decisions from action text
    action = metadata.get("action", "")
    decision_keywords = ["decided to", "chose", "selected", "will use", "strategy:", "approach:"]
    for keyword in decision_keywords:
        if keyword in action.lower():
            sentences = action.split(". ")
            for sent in sentences:
                if keyword in sent.lower():
                    summary["decisions"].append(sent.strip()[:200])
                    break

    return summary


def get_important_recent_memories(collection, session_id: str, n: int = RECENT_MEMORIES) -> List[Dict[str, Any]]:
    """Get recent high-importance memories."""
    try:
        results = collection.get(
            where={"session_id": session_id},
            limit=1000
        )

        if not results or not results.get("metadatas"):
            return []

        memories = []
        for i, metadata in enumerate(results["metadatas"]):
            importance = metadata.get("importance_score", 0.0)
            if importance >= MIN_IMPORTANCE:
                summary = extract_smart_summary(metadata, results["documents"][i])
                memories.append({
                    "id": results["ids"][i],
                    "summary": summary
                })

        memories.sort(key=lambda x: x["summary"]["timestamp"], reverse=True)
        return memories[:n]

    except Exception as e:
        debug_log(f"Error getting recent memories: {e}")
        return []


def get_relevant_memories_with_task_context(
    collection,
    query_text: str,
    session_id: str,
    kg: MemoryKnowledgeGraph,
    max_results: int = TOP_K_MEMORIES
) -> List[Dict[str, Any]]:
    """
    Adaptive K retrieval WITH task-context scoring.

    Steps:
    1. Semantic search to get candidates (using nomic-embed)
    2. Extract task entities from query
    3. Score candidates with task-context boost
    4. Apply adaptive K based on quality
    5. Return 0-max_results memories
    """
    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
        query_embedding = embedding_model.encode(query_text).tolist()

        # Get candidates with semantic search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=50,  # Get plenty of candidates
            where={"session_id": session_id}
        )

        if not results or not results.get("metadatas") or not results["metadatas"][0]:
            return []

        # Create task-context scorer
        scorer = TaskContextScorer(kg)

        # Extract task entities from query
        task_entities = scorer.extract_task_entities(query_text)
        related_entities = scorer.find_related_entities(task_entities, max_hops=2) if task_entities else {}

        debug_log(f"Task entities: {task_entities[:5] if task_entities else 'None'}")
        debug_log(f"Related entities: {len(related_entities)}")

        # Process and categorize by quality (with task-context boost)
        high_quality = []  # >= 0.6 similarity
        medium_quality = []  # 0.4-0.6 similarity
        seen_documents = set()

        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]
            base_importance = metadata.get("importance_score", 0.0)
            distance = results["distances"][0][i] if "distances" in results else 0.5
            similarity = 1 - distance

            # Skip if too low importance or similarity
            if base_importance < MIN_IMPORTANCE or similarity < 0.4:
                continue

            # Deduplicate
            doc_key = document.strip().lower()
            if doc_key in seen_documents:
                continue
            seen_documents.add(doc_key)

            # Apply task-context scoring
            task_importance, matched_entities = scorer.score_memory_for_task(
                document, metadata, related_entities, base_importance
            )

            summary = extract_smart_summary(metadata, document)
            combined_score = similarity * task_importance  # Use task_importance instead of base

            memory = {
                "id": results["ids"][0][i],
                "summary": summary,
                "similarity": similarity,
                "base_importance": base_importance,
                "task_importance": task_importance,
                "task_boost": task_importance / base_importance if base_importance > 0 else 1.0,
                "matched_entities": matched_entities,
                "combined_score": combined_score
            }

            # Categorize by similarity quality
            if similarity >= 0.6:
                high_quality.append(memory)
            elif similarity >= 0.4:
                medium_quality.append(memory)

        # Sort each category by combined score (similarity * task_importance)
        high_quality.sort(key=lambda x: x["combined_score"], reverse=True)
        medium_quality.sort(key=lambda x: x["combined_score"], reverse=True)

        # Adaptive logic
        if len(high_quality) >= 5:
            result = high_quality[:max_results]
            debug_log(f"Adaptive K: {len(result)} high-quality memories (>= 0.6 similarity)")
        elif len(high_quality) > 0:
            result = (high_quality + medium_quality[:5])[:max_results]
            debug_log(f"Adaptive K: {len(high_quality)} high + {len(result) - len(high_quality)} medium")
        elif len(medium_quality) > 0:
            result = medium_quality[:3]
            debug_log(f"Adaptive K: {len(result)} medium-quality memories (0.4-0.6 similarity)")
        else:
            debug_log("Adaptive K: No relevant memories found (all < 0.4 similarity)")
            return []

        # Log task-boosted memories
        boosted = [m for m in result if m["task_boost"] > 1.5]
        if boosted:
            debug_log(f"Task-boosted: {len(boosted)} memories (boost > 1.5x)")

        return result

    except Exception as e:
        debug_log(f"Error querying memories: {e}")
        import traceback
        debug_log(traceback.format_exc())
        return []


def format_memory_entry(mem: Dict[str, Any], index: int, show_similarity: bool = False) -> str:
    """Format a single memory entry with smart details."""
    summary = mem["summary"]
    parts = []

    indicator = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }.get(summary["category"], "⚪")

    # Header with importance
    header = f"### {index}. {indicator} {summary['category'].upper()}:{summary['importance']:.1f}"

    if show_similarity:
        header += f" | Relevance: {mem['similarity']:.0%}"

        # Show task boost if significant
        if mem.get("task_boost", 1.0) > 1.5:
            header += f" | Task-Boost: {mem['task_boost']:.1f}x"

    parts.append(header)

    # Main content
    text = summary["text"]
    if len(text) > MAX_CONTENT_LENGTH:
        parts.append(f"{text[:MAX_CONTENT_LENGTH]}... [truncated]")
    else:
        parts.append(text)

    parts.append("")

    # Add artifact details if available
    details = []

    if summary["files"]:
        files_str = ", ".join(f"`{f}`" for f in summary["files"][:3])
        if len(summary["files"]) > 3:
            files_str += f" +{len(summary['files']) - 3} more"
        details.append(f"**Files**: {files_str}")

    if summary["functions"]:
        funcs = list(set(summary["functions"]))[:3]
        details.append(f"**Functions**: {', '.join(f'`{f}()`' for f in funcs)}")

    if summary["bugs_fixed"]:
        details.append(f"**Bugs Fixed**: {len(summary['bugs_fixed'])} errors resolved")

    if summary["decisions"]:
        for decision in summary["decisions"][:2]:
            details.append(f"**Decision**: {decision}")

    # Show matched task entities if any
    if show_similarity and mem.get("matched_entities"):
        matched_str = ", ".join([f"`{e[0]}`" for e in mem["matched_entities"][:3]])
        if matched_str:
            details.append(f"**Task-Relevant**: {matched_str}")

    if details:
        parts.extend(details)
        parts.append("")

    return "\n".join(parts)


def format_enhanced_context(recent_memories: List[Dict], relevant_memories: List[Dict]) -> str:
    """Format with query tool availability and smart summaries."""
    parts = []

    parts.append(f"# 🧠 Memory Context Restored ({SESSIONSTART_VERSION}: Task-Context Aware)")
    parts.append("")
    parts.append("## 🔍 Memory Query Tools Available")
    parts.append("")
    parts.append("You can query the memory database proactively using:")
    parts.append("")
    parts.append("```bash")
    parts.append("# Search by topic (semantic)")
    parts.append("python3 ~/.claude/memory-hooks/query_memories.py --topic \"bugs errors fixes\"")
    parts.append("")
    parts.append("# Find by keywords")
    parts.append("python3 ~/.claude/memory-hooks/query_memories.py --keywords TypeError crash")
    parts.append("")
    parts.append("# High importance only")
    parts.append("python3 ~/.claude/memory-hooks/query_memories.py --min-importance 15")
    parts.append("")
    parts.append("# Find files involved in errors")
    parts.append("python3 ~/.claude/memory-hooks/query_memories.py --files-involved --keywords error")
    parts.append("")
    parts.append("# Get statistics")
    parts.append("python3 ~/.claude/memory-hooks/query_memories.py --stats")
    parts.append("```")
    parts.append("")
    parts.append("**Use these tools to understand past work without asking me!**")
    parts.append("")
    parts.append("---")
    parts.append("")

    # Recent memories
    if recent_memories:
        parts.append("## 📋 Recent High-Importance Work")
        parts.append("")

        for i, mem in enumerate(recent_memories, 1):
            parts.append(format_memory_entry(mem, i, show_similarity=False))

    # Relevant memories
    if relevant_memories:
        recent_ids = {m["id"] for m in recent_memories}
        unique_relevant = [m for m in relevant_memories if m["id"] not in recent_ids]

        if unique_relevant:
            parts.append("## 🔍 Related Context (Task-Aware Semantic Match)")
            parts.append("")

            for i, mem in enumerate(unique_relevant, 1):
                parts.append(format_memory_entry(mem, i, show_similarity=True))

    parts.append("---")
    parts.append(f"*Memory System {SESSIONSTART_VERSION}: Task-context aware with knowledge graph*")

    return "\n".join(parts)


def main():
    """SessionStart injection with task-context awareness."""
    try:
        input_data = json.load(sys.stdin)

        session_id = input_data.get("session_id", "unknown")
        trigger = input_data.get("trigger", "compact")

        debug_log(f"SessionStart-{SESSIONSTART_VERSION} triggered: session={session_id}, trigger={trigger}")

        if not MEMORY_DB_PATH.exists():
            debug_log("No memory database found")
            sys.exit(0)

        client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))

        try:
            collection = client.get_collection(name="conversation_memories")
        except Exception:
            debug_log("Memory collection not found")
            sys.exit(0)

        # Build/get knowledge graph
        kg = get_or_build_knowledge_graph()

        # Get high-quality memories
        recent_memories = get_important_recent_memories(collection, session_id, RECENT_MEMORIES)
        debug_log(f"Retrieved {len(recent_memories)} important recent memories")

        # Query with task-context awareness
        query_text = "current task work in progress bugs architecture decisions files functions features tools"
        relevant_memories = get_relevant_memories_with_task_context(
            collection, query_text, session_id, kg, TOP_K_MEMORIES
        )
        debug_log(f"Retrieved {len(relevant_memories)} relevant memories with task-context scoring")

        if not recent_memories and not relevant_memories:
            debug_log("No high-importance memories to inject")
            sys.exit(0)

        # Format smart context
        additional_context = format_enhanced_context(recent_memories, relevant_memories)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": additional_context
            }
        }

        print(json.dumps(output))
        debug_log(f"Injected {len(recent_memories)} recent + {len(relevant_memories)} relevant ({SESSIONSTART_VERSION} task-aware)")

    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        import traceback
        debug_log(traceback.format_exc())

    sys.exit(0)


if __name__ == "__main__":
    main()
