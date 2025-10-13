#!/usr/bin/env python3
"""
PreCompact Memory Extractor V2 - Enhanced with all features
============================================================
Integrates:
- Importance scoring
- Multi-modal artifact extraction
- Hierarchical clustering
- Automatic pruning
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import jsonlines

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from memory_scorer import MemoryScorer, score_chunks
    from multimodal_extractor import MultiModalExtractor, enrich_chunk_with_artifacts
    from memory_pruner import MemoryPruner
    from memory_clustering import MemoryClustering
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    print("Run: pip install -r ~/.claude/memory-hooks/requirements.txt", file=sys.stderr)
    sys.exit(1)

# Configuration
MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MAX_TRANSCRIPT_MESSAGES = 1000  # Increased from 100 to capture full conversations
DEBUG_LOG = Path.home() / ".claude" / "memory_hooks_debug.log"
AUTO_PRUNE = True  # Auto-prune on each compaction


def debug_log(msg: str):
    """Append debug message to log."""
    try:
        with open(DEBUG_LOG, "a") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"[{timestamp}] [PreCompact-V2] {msg}\n")
    except Exception:
        pass


def load_transcript(transcript_path: str) -> List[Dict[str, Any]]:
    """Load and parse the conversation transcript."""
    messages = []
    try:
        with jsonlines.open(transcript_path) as reader:
            for entry in reader:
                messages.append(entry)

        if len(messages) > MAX_TRANSCRIPT_MESSAGES:
            messages = messages[-MAX_TRANSCRIPT_MESSAGES:]

        debug_log(f"Loaded {len(messages)} messages from transcript")
        return messages
    except Exception as e:
        debug_log(f"Error loading transcript: {e}")
        return []


def format_transcript_for_analysis(messages: List[Dict[str, Any]]) -> str:
    """Format transcript for Claude API analysis."""
    formatted = []

    for msg in messages:
        # Handle Claude Code format: {type: "user", message: {role: "user", content: "..."}}
        # Extract nested message if present
        actual_msg = msg.get("message", msg)
        role = actual_msg.get("role", "unknown")

        if role == "user":
            content = actual_msg.get("content", [])
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                formatted.append(f"USER: {' '.join(text_parts)}")
            else:
                formatted.append(f"USER: {content}")

        elif role == "assistant":
            content = actual_msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        formatted.append(f"ASSISTANT: {block.get('text', '')}")
                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})
                        formatted.append(f"TOOL_USE: {tool_name} with {json.dumps(tool_input)}")

    return "\n".join(formatted)


def chunk_conversation(transcript_text: str) -> List[Dict[str, str]]:
    """Smart rule-based conversation chunking."""
    lines = transcript_text.strip().split("\n")
    chunks = []
    current_chunk = {"user": [], "assistant": [], "tools": [], "tool_names": []}

    # Decision/outcome markers for smart chunking
    decision_markers = ["decided", "chose", "will use", "going with", "selected"]
    completion_markers = ["completed", "done", "finished", "success", "working", "created", "implemented"]
    error_markers = ["error", "failed", "issue", "problem", "warning"]
    file_markers = ["Write", "Edit", "Read", "created file", "modified"]

    def should_chunk_here(line: str, current: Dict) -> bool:
        """Detect natural chunk boundaries."""
        # Chunk after 3-5 file operations (group related file creations)
        file_op_count = sum(1 for tool in current["tool_names"] if tool in ["Write", "Edit"])
        if file_op_count >= 3 and len(current["assistant"]) > 2:
            return True

        # Chunk after significant single file operations with explanation
        if any(marker in current["tool_names"] for marker in ["Write", "Edit"]):
            if len(current["assistant"]) > 5:  # Substantial explanation
                return True

        # Chunk after decisions/completions
        text = " ".join(current["assistant"][-3:]).lower()
        if any(marker in text for marker in completion_markers + decision_markers):
            if len(current["tools"]) > 0:  # And some action taken
                return True

        # Chunk on topic changes (new user message after work)
        if line.startswith("USER:") and (len(current["assistant"]) > 3 or len(current["tools"]) > 2):
            return True

        return False

    for i, line in enumerate(lines):
        if line.startswith("USER:"):
            # Check if we should chunk before adding new user message
            if should_chunk_here(line, current_chunk):
                chunk = _build_smart_chunk(current_chunk)
                if chunk:
                    chunks.append(chunk)
                current_chunk = {"user": [], "assistant": [], "tools": [], "tool_names": []}

            current_chunk["user"].append(line[5:].strip())

        elif line.startswith("ASSISTANT:"):
            current_chunk["assistant"].append(line[10:].strip())

        elif line.startswith("TOOL_USE:"):
            tool_text = line[9:].strip()
            current_chunk["tools"].append(tool_text)
            # Extract tool name
            if " with " in tool_text:
                tool_name = tool_text.split(" with ")[0].strip()
                current_chunk["tool_names"].append(tool_name)

    # Add final chunk
    if current_chunk["user"] or current_chunk["assistant"]:
        chunk = _build_smart_chunk(current_chunk)
        if chunk:
            chunks.append(chunk)

    debug_log(f"Generated {len(chunks)} smart chunks")
    return chunks


def _build_smart_chunk(parts: Dict[str, List[str]]) -> Dict[str, str]:
    """Build intelligent chunk from conversation parts."""
    if not parts["user"] and not parts["assistant"]:
        return None

    # Extract intent from user messages
    user_text = " ".join(parts["user"])
    if not user_text:
        intent = "Continue previous task"
    elif len(user_text) < 100:
        intent = user_text
    else:
        # Extract first sentence or question
        sentences = user_text.split(".")
        intent = sentences[0][:200] if sentences else user_text[:200]

    # Build action from assistant responses and tools
    assistant_text = " ".join(parts["assistant"])
    tools_text = " ".join(parts["tools"])

    # Detect what was actually done
    action_parts = []
    if "Write" in parts["tool_names"]:
        action_parts.append("Created/wrote files")
    if "Edit" in parts["tool_names"]:
        action_parts.append("Modified files")
    if "Read" in parts["tool_names"]:
        action_parts.append("Analyzed code")
    if "Bash" in parts["tool_names"]:
        action_parts.append("Executed commands")

    # Add key explanation from assistant
    if assistant_text:
        # Find decision/explanation sentences
        key_phrases = []
        for sentence in assistant_text.split("."):
            lower = sentence.lower()
            if any(marker in lower for marker in ["decided", "implement", "create", "will", "let me", "I'll"]):
                key_phrases.append(sentence.strip())
                if len(key_phrases) >= 2:
                    break

        if key_phrases:
            action_parts.extend(key_phrases[:2])
        elif len(assistant_text) < 300:
            action_parts.append(assistant_text)
        else:
            action_parts.append(assistant_text[:300] + "...")

    action = " - ".join(action_parts) if action_parts else tools_text[:500]

    # Detect outcome
    combined_text = (assistant_text + " " + tools_text).lower()
    if any(marker in combined_text for marker in ["error", "failed", "issue"]):
        outcome = "Encountered issues, troubleshooting"
    elif any(marker in combined_text for marker in ["success", "completed", "done", "working"]):
        outcome = "Task completed successfully"
    elif len(parts["tools"]) > 0:
        outcome = f"Executed {len(parts['tools'])} operations"
    else:
        outcome = "Discussion/planning"

    # Build summary
    summary = f"{intent[:150]}"
    if action_parts:
        summary += f" → {action_parts[0][:150]}"

    return {
        "intent": intent[:500],
        "action": action[:1000],
        "outcome": outcome[:300],
        "summary": summary[:500]
    }


def store_enhanced_chunks(chunks: List[Dict[str, str]], session_id: str):
    """Store chunks with all enhancements: importance, artifacts, embeddings."""
    try:
        client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))
        collection = client.get_or_create_collection(
            name="conversation_memories",
            metadata={"hnsw:space": "cosine"}
        )

        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        timestamp = datetime.now().isoformat()

        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for i, chunk in enumerate(chunks):
            # Step 1: Extract multi-modal artifacts
            enriched = enrich_chunk_with_artifacts(chunk)

            # Step 2: Calculate importance score
            score = MemoryScorer.score_chunk(chunk, {"timestamp": timestamp, "tool_count": i + 1})
            importance_category = MemoryScorer.categorize_importance(score)

            # Step 3: Create enhanced embedding text
            embedding_text = enriched["enhanced_summary"]
            embedding = embedding_model.encode(embedding_text).tolist()

            # Step 4: Prepare for storage
            chunk_id = f"{session_id}_{timestamp}_{i}"

            documents.append(chunk["summary"])
            metadatas.append({
                "session_id": session_id,
                "timestamp": timestamp,
                "intent": chunk["intent"],
                "action": chunk["action"],
                "outcome": chunk["outcome"],
                "chunk_index": i,
                "importance_score": score,
                "importance_category": importance_category,
                "artifacts": json.dumps(enriched["metadata"]["artifacts"]),  # Serialize to JSON
                "has_code": enriched["metadata"]["has_code"],
                "has_files": enriched["metadata"]["has_files"],
                "has_architecture": enriched["metadata"]["has_architecture"],
            })
            ids.append(chunk_id)
            embeddings.append(embedding)

        # Add to ChromaDB
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

        debug_log(f"Stored {len(chunks)} enhanced chunks")

        # Auto-prune if enabled
        if AUTO_PRUNE:
            pruner = MemoryPruner(str(MEMORY_DB_PATH))
            prune_result = pruner.prune_session_memories(session_id, dry_run=False)
            debug_log(f"Auto-pruned: {prune_result.get('pruned', 0)} memories")

        # Perform clustering (for hierarchy)
        clusterer = MemoryClustering(str(MEMORY_DB_PATH))
        cluster_result = clusterer.cluster_memories(session_id)
        if "error" not in cluster_result:
            debug_log(f"Clustered into {cluster_result['num_clusters']} groups")

    except Exception as e:
        debug_log(f"Error storing chunks: {e}")


def main():
    """Main PreCompact hook logic with all enhancements."""
    try:
        input_data = json.load(sys.stdin)

        session_id = input_data.get("session_id", "unknown")
        transcript_path = input_data.get("transcript_path", "")
        trigger = input_data.get("trigger", "unknown")

        debug_log(f"PreCompact-V2 triggered: session={session_id}, trigger={trigger}")

        if not transcript_path:
            debug_log("No transcript path")
            sys.exit(0)

        transcript_path = os.path.expanduser(transcript_path)

        if not os.path.exists(transcript_path):
            debug_log(f"Transcript not found: {transcript_path}")
            sys.exit(0)

        # Load transcript
        messages = load_transcript(transcript_path)
        if not messages:
            sys.exit(0)

        # Chunk conversation smartly
        transcript_text = format_transcript_for_analysis(messages)
        chunks = chunk_conversation(transcript_text)

        if not chunks:
            debug_log("No chunks generated")
            sys.exit(0)

        # Store with all enhancements
        store_enhanced_chunks(chunks, session_id)

        # Show message to user
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreCompact",
                "systemMessage": f"🧠 Memory preserved: {len(chunks)} chunks stored with importance scoring, multi-modal artifacts, and clustering"
            }
        }
        print(json.dumps(output))

    except Exception as e:
        debug_log(f"Unexpected error: {e}")
        import traceback
        debug_log(traceback.format_exc())

    sys.exit(0)


if __name__ == "__main__":
    main()
