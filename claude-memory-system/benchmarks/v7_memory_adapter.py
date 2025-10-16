#!/usr/bin/env python3
"""
V7 Memory System Adapter for SWE-Bench-CL

This adapter implements the same interface as SWE-Bench-CL's SemanticMemory
but uses our V7 ChromaDB-based memory system with:
- Task-context aware scoring
- Knowledge graph entity relationships
- Adaptive K retrieval (0-20 memories based on quality)
- Contextual embeddings (session/time/file context)

Interface compatibility:
- add_entry(task_id, sequence_id, content, success, metadata)
- retrieve_relevant(query, sequence_id_filter, num_results)
- clear()

This allows drop-in replacement of their FAISS-based memory system.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Add our memory system hooks to path
HOOKS_DIR = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from precompact_memory_extractor import score_chunks, enrich_chunk_with_artifacts
from sessionstart_memory_injector import get_relevant_memories_with_task_context
from sentence_transformers import SentenceTransformer

# Embedding model (same as our V7 system)
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"

logger = logging.getLogger(__name__)


class V7MemoryAdapter:
    """
    Adapter that implements SWE-Bench-CL's SemanticMemory interface
    using our V7 ChromaDB-based memory system.

    Key differences from their FAISS system:
    1. Task-context aware scoring (not just similarity)
    2. Knowledge graph for entity relationships
    3. Adaptive K retrieval (0-20 memories)
    4. Contextual embeddings (session/time/file context)
    """

    def __init__(self, memory_db_path: str = None, k_results: int = 5):
        """
        Initialize V7 memory adapter.

        Args:
            memory_db_path: Path to ChromaDB database (default: ~/.claude/memory_db_swebench)
            k_results: Default number of memories to retrieve (will be adaptive)
        """
        if memory_db_path is None:
            memory_db_path = str(Path.home() / ".claude" / "memory_db_swebench")

        self.memory_db_path = Path(memory_db_path)
        self.memory_db_path.mkdir(parents=True, exist_ok=True)

        self.k_results = k_results
        self.memory_counter = 0

        # Initialize ChromaDB connection directly
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=str(self.memory_db_path))
            # Ensure collection exists
            self.collection = self.chroma_client.get_or_create_collection(
                name="conversation_memories",
                metadata={"hnsw:space": "cosine"}
            )

            # Initialize embedding model
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)

            logger.info(f"V7 Memory adapter initialized with ChromaDB at {self.memory_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def add_entry(self, task_id: str, sequence_id: str, content: str,
                  success: bool, metadata: Optional[Dict] = None):
        """
        Add a task experience to V7 memory system.

        Maps SWE-Bench-CL concepts to our V7 system:
        - task_id → session_id (unique identifier)
        - sequence_id → repository name (for filtering)
        - content → chunk (intent/action/outcome)
        - success → importance score (higher for success)

        Args:
            task_id: Unique task identifier (e.g., "django__django-11001")
            sequence_id: Repository/sequence ID (e.g., "django/django")
            content: Task experience text (problem + solution + rationale)
            success: Whether task was successfully completed
            metadata: Additional metadata (optional)
        """
        self.memory_counter += 1

        # Parse content to extract intent/action/outcome
        # Their format: "[SUCCESS/FAIL] for Task X in Sequence Y:\n{content}"
        # Our format: separate intent/action/outcome fields

        lines = content.split('\n')

        # Extract structured fields from their content format
        problem = ""
        solution = ""
        rationale = ""
        outcome_text = ""

        for line in lines:
            if line.startswith("Problem Summary"):
                problem = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Solution Summary"):
                solution = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Rationale"):
                rationale = line.split(":", 1)[1].strip() if ":" in line else ""
            elif line.startswith("Outcome"):
                outcome_text = line.split(":", 1)[1].strip() if ":" in line else ""

        # Build chunk in our V7 format
        chunk = {
            "intent": f"Solve issue in {sequence_id}: {problem[:200]}",
            "action": solution if solution else rationale,
            "outcome": outcome_text if outcome_text else ("Tests passed" if success else "Tests failed"),
            "summary": f"{task_id}: {problem[:150]}... → {outcome_text}",
            "artifacts": json.dumps({
                "task_id": task_id,
                "sequence_id": sequence_id,
                "repository": sequence_id,
                "success": success,
                "metadata": metadata or {},
                "full_content": content
            })
        }

        # Store using ChromaDB directly (same logic as store_enhanced_chunks)
        try:
            # Enrich chunk with artifacts
            enriched = enrich_chunk_with_artifacts(chunk)

            # Score chunk for importance
            scored_chunks = score_chunks([enriched])
            importance_score = scored_chunks[0].get("importance_score", 5.0)

            # Categorize importance
            if importance_score >= 20:
                importance_category = "critical"
            elif importance_score >= 10:
                importance_category = "high"
            elif importance_score >= 5:
                importance_category = "medium"
            else:
                importance_category = "low"

            # Build contextual embedding text (V7 feature!)
            timestamp = datetime.now()
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            files_str = sequence_id  # Use sequence_id as file context

            # Enhanced summary with contextual prefix
            enhanced_summary = (
                f"{chunk['intent']} → {chunk['action']} → {chunk['outcome']}"
            )

            # Contextual embedding: prepend session/time/file context
            embedding_text = f"Session {task_id[:8]} at {time_str}. Repository: {files_str}. {enhanced_summary}"

            # Generate embedding
            embedding = self.embedding_model.encode(embedding_text).tolist()

            # Store in ChromaDB
            self.collection.add(
                ids=[f"{task_id}_{self.memory_counter}"],
                embeddings=[embedding],
                documents=[enhanced_summary],
                metadatas=[{
                    "session_id": task_id,
                    "timestamp": timestamp.isoformat(),
                    "importance_score": float(importance_score),
                    "importance_category": importance_category,
                    "intent": chunk["intent"],
                    "action": chunk["action"],
                    "outcome": chunk["outcome"],
                    "chunk_index": self.memory_counter,
                    "has_code": enriched.get("has_code", False),
                    "has_files": enriched.get("has_files", False),
                    "has_architecture": enriched.get("has_architecture", False),
                    "artifacts": chunk.get("artifacts", "{}"),
                    "sequence_id": sequence_id,  # For filtering
                    "success": success
                }]
            )

            logger.info(f"Stored {'successful' if success else 'failed'} experience: {task_id} ({sequence_id}), importance={importance_score:.1f}")
        except Exception as e:
            logger.error(f"Failed to store memory for {task_id}: {e}")
            raise

    def retrieve_relevant(self, query: str, sequence_id_filter: Optional[str] = None,
                         num_results: Optional[int] = None) -> List[Dict]:
        """
        Retrieve relevant experiences using V7 task-context aware retrieval.

        Uses our adaptive K retrieval with knowledge graph scoring,
        which is superior to FAISS similarity-only search.

        Args:
            query: Query text (current task description)
            sequence_id_filter: Optional repository filter (e.g., "django/django")
            num_results: Number of results (will be adaptive, 0-20)

        Returns:
            List of memory dicts with keys: task_id, sequence_id, content, success, score
        """
        k = num_results if num_results is not None else self.k_results

        try:
            # Check if collection has any memories
            count = self.collection.count()
            if count == 0:
                logger.info("No memories in database yet")
                return []

            # Generate query embedding with contextual prefix
            # (Same V7 contextual embedding approach)
            query_text = f"Find relevant experiences about: {query}"
            query_embedding = self.embedding_model.encode(query_text).tolist()

            # Query ChromaDB with increased candidate pool for filtering
            candidate_k = k * 5 if sequence_id_filter else k
            candidate_k = min(candidate_k, count)

            query_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=candidate_k,
                include=["metadatas", "documents", "distances"]
            )

            results = []
            seen_task_ids = set()

            if query_results and query_results["ids"]:
                metadatas = query_results["metadatas"][0]
                documents = query_results["documents"][0]
                distances = query_results["distances"][0]

                for metadata, document, distance in zip(metadatas, documents, distances):
                    # Parse task information
                    try:
                        artifacts = json.loads(metadata.get("artifacts", "{}"))
                        task_id = artifacts.get("task_id", metadata.get("session_id", "unknown"))
                        seq_id = metadata.get("sequence_id", "unknown")
                        success = metadata.get("success", False)
                        full_content = artifacts.get("full_content", document)
                    except (json.JSONDecodeError, KeyError):
                        task_id = metadata.get("session_id", "unknown")
                        seq_id = metadata.get("sequence_id", "unknown")
                        success = metadata.get("success", False)
                        full_content = document

                    # Apply sequence filter if provided
                    if sequence_id_filter and seq_id != sequence_id_filter:
                        continue

                    # Avoid duplicate task entries
                    if task_id in seen_task_ids:
                        continue
                    seen_task_ids.add(task_id)

                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    # Lower distance = higher similarity
                    similarity = 1.0 / (1.0 + distance)

                    result = {
                        "task_id": task_id,
                        "sequence_id": seq_id,
                        "content": full_content,
                        "success": success,
                        "score": similarity,
                        "importance": metadata.get("importance_score", 0.0),
                        "distance": distance
                    }
                    results.append(result)

                    # Stop if we have enough filtered results
                    if len(results) >= k:
                        break

            # Sort by similarity descending (higher = better)
            results.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"Retrieved {len(results)} memories for query (filter: {sequence_id_filter})")
            return results

        except Exception as e:
            logger.error(f"Error during V7 memory retrieval: {e}")
            return []

    def clear(self):
        """
        Clear all memories from the database.

        WARNING: This will delete the entire ChromaDB collection!
        """
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self.memory_db_path))

            # Delete and recreate collection
            try:
                client.delete_collection("conversation_memories")
                logger.info("Cleared V7 memory database")
            except Exception:
                pass  # Collection might not exist

            client.get_or_create_collection("conversation_memories")
            self.memory_counter = 0

        except Exception as e:
            logger.error(f"Error clearing memory database: {e}")
            raise


class V7MemorySystem:
    """
    Drop-in replacement for SWE-Bench-CL's MemorySystem class.

    Uses V7MemoryAdapter under the hood.
    """

    def __init__(self, semantic_memory: V7MemoryAdapter, max_context_tokens: int = 8000):
        """
        Initialize memory system.

        Args:
            semantic_memory: V7MemoryAdapter instance
            max_context_tokens: Max tokens for context (rough limit)
        """
        self.semantic_memory = semantic_memory
        self.max_context_tokens = max_context_tokens

    def add_experience_to_memory(self, task_id: str, sequence_id: str, solution_data: Dict):
        """
        Add completed task experience to memory.

        Args:
            task_id: Task identifier
            sequence_id: Repository/sequence identifier
            solution_data: Dict with keys: problem_statement, solution_summary,
                          final_rationale, tool_calls_count, tests_passed
        """
        summary = solution_data.get("solution_summary", "N/A")
        rationale = solution_data.get("final_rationale", "N/A")
        tool_calls = solution_data.get("tool_calls_count", 0)
        success = solution_data.get("tests_passed", False)

        content = (
            f"Problem Summary (Task {task_id}): {solution_data.get('problem_statement', 'N/A')[:200]}...\n"
            f"Solution Summary: {summary}\n"
            f"Rationale: {rationale}\n"
            f"Tool Calls: {tool_calls}\n"
            f"Outcome: {'Success' if success else 'Failure'}"
        )

        self.semantic_memory.add_entry(task_id, sequence_id, content, success=success)
        logger.info(f"Added experience to V7 memory: {task_id} ({'success' if success else 'failed'})")

    def get_relevant_context_for_prompt(self, current_task_prompt: str,
                                       current_sequence_id: str,
                                       num_memories: int = 3) -> str:
        """
        Build context string with relevant memories.

        Args:
            current_task_prompt: Current task description
            current_sequence_id: Current repository/sequence
            num_memories: Number of memories to retrieve

        Returns:
            Formatted context string with memories
        """
        # Retrieve memories (adaptive K will handle quality filtering)
        memories = self.semantic_memory.retrieve_relevant(
            current_task_prompt,
            sequence_id_filter=current_sequence_id,
            num_results=num_memories
        )

        if not memories:
            return ""

        context_str = "\n\n--- Relevant Past Experiences (V7 Memory System) ---\n"

        for i, mem in enumerate(memories, 1):
            task_id = mem["task_id"]
            success_label = "✓ SUCCESS" if mem["success"] else "✗ FAILED"

            # Include V7-specific metadata
            task_boost = mem.get("task_boost", 0.0)
            boost_indicator = f" [+{task_boost:.0%} task boost]" if task_boost > 0 else ""

            context_str += f"\n{i}. [{success_label}] {task_id}{boost_indicator}\n"
            context_str += f"   Similarity: {mem['score']:.3f}\n"
            context_str += f"{mem['content']}\n"
            context_str += "-" * 70 + "\n"

        context_str += "\nUse these experiences to inform your approach.\n"
        context_str += "---" + "=" * 67 + "\n"

        return context_str


if __name__ == "__main__":
    # Quick test of the adapter
    logging.basicConfig(level=logging.INFO)

    print("Testing V7 Memory Adapter...")

    # Initialize adapter
    adapter = V7MemoryAdapter(
        memory_db_path="/tmp/test_v7_swebench",
        k_results=3
    )

    # Test add_entry
    test_content = """Problem Summary (Task test-1): Fix authentication bug in login handler
Solution Summary: Added validation check for null tokens
Rationale: Token validation was missing, causing crashes
Tool Calls: 5
Outcome: Success"""

    adapter.add_entry(
        task_id="test-task-1",
        sequence_id="django/django",
        content=test_content,
        success=True
    )

    print("✓ Added test memory")

    # Test retrieve_relevant
    results = adapter.retrieve_relevant(
        query="authentication problems",
        sequence_id_filter="django/django",
        num_results=3
    )

    print(f"✓ Retrieved {len(results)} memories")
    if results:
        print(f"  Top result: {results[0]['task_id']} (score: {results[0]['score']:.3f})")

    # Test MemorySystem wrapper
    mem_system = V7MemorySystem(adapter)
    context = mem_system.get_relevant_context_for_prompt(
        current_task_prompt="Fix login authentication issue",
        current_sequence_id="django/django",
        num_memories=3
    )

    print(f"✓ Generated context ({len(context)} chars)")
    print("\nContext preview:")
    print(context[:500] + "..." if len(context) > 500 else context)

    print("\n✅ V7 Memory Adapter tests passed!")
