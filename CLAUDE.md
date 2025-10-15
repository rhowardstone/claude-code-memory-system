# Claude Code Memory Preservation System

**V7 - Contextual Embeddings + Evaluation**

This `CLAUDE.md` file tracks system architecture and key learnings across compaction cycles.

---

## The Task

Build a **vector-based memory preservation system** for Claude Code that survives compaction cycles by:
1. **PreCompact Hook**: Extract important memories before compaction, store in ChromaDB
2. **SessionStart Hook**: Inject relevant memories after compaction to restore context
3. **Memory Query Tools**: Allow semantic/keyword search across all stored memories
4. **Memory Pruning**: Auto-prune old, low-importance, or redundant memories

**Goal**: Never lose context across compaction cycles. Claude should "wake up" with journals, not post-it notes.

---

## Directives

**General Principles:**
- Proceed in an orderly fashion, making a FULL plan in your todos
- Always use the best available tool for the job
- NO placeholder code! No dead functions!
- Stay organized using your todo list
- Always update the scratchpad below after significant progress

**Code Quality:**
- Do NOT change ANY *existing* tests to make them pass
- You may create *additional* tests
- Be organized in attempts and filenames
- Keep everything in subdirectories, appropriately named

**Problem Solving:**
- Do not "fall back" to "simpler" methods when the going gets rough!
- That's a red flag - think it through with fresh eyes
- Check this file first to see if things have been done already

**Documentation:**
- Use this file (CLAUDE.md) to track anything you need to know
- Quirks, bugs, how you fixed them
- Where files are, what functions are called
- Anything that, if we lost all context except this document, you would need to know

**Versioning (V6+):**
- Version numbers in `__version__.py` ONLY
- NO version suffixes in filenames (e.g., `precompact.py`, not `precompact_v2.py`)
- Update `__version__.py` when making significant changes
- Import version constants: `from __version__ import __version__, PRECOMPACT_VERSION`

---

## Scratchpad
------------- DO NOT WRITE ABOVE THIS LINE --------------

### ⚠️ CRITICAL REMINDERS

**Git Repository**: `https://github.com/rhowardstone/claude-code-memory-system`
- ❌ NOT claude-code (that's just a reference copy)
- ✅ The actual repo is: `claude-code-memory-system`

**Git Identity**:
- Name: Rye Howard-Stone
- Email: Rye.Howard-Stone@UConn.edu

---

### System Architecture (V7)

**Location**: `/atb-data/claude-code/claude-code/claude-memory-system/`

**Core Components**:
1. `hooks/__version__.py` - Centralized version tracking (V7.0.0)
2. `hooks/precompact_memory_extractor.py` - Extracts memories with contextual embeddings
3. `hooks/sessionstart_memory_injector.py` - Task-context aware injection with knowledge graph
4. `hooks/knowledge_graph.py` - Builds entity graph and computes PageRank
5. `hooks/task_context_scorer.py` - Task-specific importance scoring
6. `hooks/entity_extractor.py` - Extracts FILES, FUNCTIONS, BUGS, etc.
7. `hooks/memory_pruner.py` - Prunes old/redundant memories
8. `hooks/query_memories.py` - Comprehensive search CLI

**Installed Location**: `~/.claude/memory-hooks/` (via install.sh)

**Memory Database**: `~/.claude/memory_db/` (ChromaDB persistent store)

---

### Key Features

**V7 (Current - Contextual Embeddings + Evaluation)**:
- ✅ **Contextual embeddings**: Prepends session, time, file context before embedding
  - Format: `"Session {id[:8]} at {time}. Files: {files}. {intent/action/outcome}"`
  - Better temporal queries ("yesterday's work") and file-based queries ("auth.py changes")
- ✅ **Evaluation framework**: Precision, Recall, F1, MRR metrics
- ✅ **Test sets**: Ground-truth query/memory pairs for measuring quality

**V6 (Clean Architecture)**:
- ✅ Removed version suffixes from all filenames
- ✅ Centralized version tracking in `__version__.py`
- ✅ Proper semantic versioning

**V5 (Task-Context Aware)**:
- ✅ Knowledge graph with entity extraction (FILES, FUNCTIONS, BUGS, etc.)
- ✅ PageRank centrality for entity importance
- ✅ Task-context scoring: Boosts memories relevant to current work
- ✅ Multi-hop graph traversal (1-2 hops)
- ✅ Adaptive K retrieval (0-20 memories based on quality)

**V4 (Nomic Embeddings)**:
- ✅ Switched to nomic-embed-text-v1.5 (768-dim, 8192 token context)
- ✅ Full transcript storage (no truncation!)
- ✅ Hierarchical display: summaries for SessionStart, full transcripts via CLI

**Embedding Model**: `nomic-ai/nomic-embed-text-v1.5`
- 768 dimensions (vs 384 with MiniLM)
- 8192 token context window (vs 512!)
- Outperforms OpenAI ada-002
- Open source, reproducible

---

### Key Files and Functions

**precompact_memory_extractor.py**:
- `chunk_conversation()` - Splits conversation into semantic chunks (Intent-Action-Outcome)
- `store_enhanced_chunks()` - Stores chunks with contextual embeddings (V7!)
- Lines 269-285: **Contextual embedding logic** - prepends session/time/file context
- `score_chunk()` - Importance scoring (0-30) based on keywords, actions
- `enrich_chunk_with_artifacts()` - Extracts code, files, errors, architecture

**sessionstart_memory_injector.py**:
- `get_relevant_memories_with_task_context()` - Adaptive K retrieval WITH task-context scoring
- `get_or_build_knowledge_graph()` - Builds/caches knowledge graph (5-min TTL)
- `format_memory_entry()` - Smart formatting with task-boost indicator
- Adaptive K: Returns 0-20 memories based on similarity quality

**query_memories.py**:
- `MemoryQuery` class - Full query interface
- `semantic_search()` - Vector-based topic search
- `keyword_search()` - Text-based keyword matching
- `date_range_search()` - Temporal filtering
- `files_involved_search()` - Cross-reference files with memories

**knowledge_graph.py**:
- `MemoryKnowledgeGraph` - NetworkX-based entity graph
- `build_from_memories()` - Extracts entities and builds graph
- `compute_centrality()` - Computes PageRank, Betweenness, Degree centrality
- `get_related_entities()` - Traverses graph to find related entities

**task_context_scorer.py**:
- `TaskContextScorer` - Computes task-specific importance scores
- `extract_task_entities()` - Extracts entities from current query
- `find_related_entities()` - Traverses graph with relevance scores
- Formula: `task_importance = base_importance * (1 + task_boost)`
- Relevance: 1.0 (exact match), 0.5 (1-hop), 0.25 (2-hop)

---

### Memory Schema (ChromaDB Metadata)

```python
{
    "session_id": "uuid",
    "timestamp": "2025-10-13T12:20:15.123456",  # ISO 8601
    "importance_score": 15.0,                    # 0-30
    "importance_category": "high",               # low/medium/high/critical
    "intent": "User's question or intent (FULL)",
    "action": "What was done in response (FULL)",
    "outcome": "Result of the action",
    "chunk_index": 0,
    "has_code": true,
    "has_files": true,
    "has_architecture": false,
    "artifacts": "{...}"  # JSON serialized: code_snippets, file_paths, commands, error_messages
}
```

**V7 Contextual Embedding** (what gets embedded):
```
Session {id[:8]} at {YYYY-MM-DD HH:MM}. Files: file1.py, file2.ts. {enhanced_summary}
```

This allows queries like:
- "work from yesterday" (temporal context)
- "changes to auth.py" (file context)
- "session abc123" (session context)

---

### Installation

```bash
# Run automated installer
cd claude-memory-system
./install.sh

# Or manual installation
pip install -r hooks/requirements.txt
cp hooks/* ~/.claude/memory-hooks/
# Update ~/.claude/settings.json with PreCompact/SessionStart hooks
```

**Dependencies**:
- chromadb>=0.4.0
- sentence-transformers>=2.2.0
- jsonlines>=3.0.0
- networkx>=3.0
- scikit-learn>=1.3.0
- einops (for nomic-embed)

---

### Memory Query Tool Usage

```bash
# Get database statistics
python3 ~/.claude/memory-hooks/query_memories.py --stats

# Search by topic (semantic)
python3 ~/.claude/memory-hooks/query_memories.py --topic "bugs errors fixes"

# Keyword search
python3 ~/.claude/memory-hooks/query_memories.py --keywords TypeError crash failed

# Date range
python3 ~/.claude/memory-hooks/query_memories.py --since "2025-10-12" --until "2025-10-13"

# High importance only
python3 ~/.claude/memory-hooks/query_memories.py --min-importance 15 --topic "architecture"

# Find files involved
python3 ~/.claude/memory-hooks/query_memories.py --files-involved --keywords error bug

# Session-specific
python3 ~/.claude/memory-hooks/query_memories.py --session current

# JSON output for scripting
python3 ~/.claude/memory-hooks/query_memories.py --topic "bugs" --format json
```

---

### Configuration

**Tuning Memory Retrieval** (`sessionstart_memory_injector.py`):
```python
TOP_K_MEMORIES = 20           # Maximum memories (adaptive returns 0-20)
RECENT_MEMORIES = 4            # Recent chronological
MIN_IMPORTANCE = 5.0           # Minimum score to inject
MIN_SIMILARITY = 0.35          # Minimum relevance threshold
KG_CACHE_TTL = 300            # Knowledge graph cache lifetime (seconds)
```

**Tuning Auto-Pruning** (`memory_pruner.py`):
```python
MAX_MEMORIES_PER_SESSION = 500  # Capacity limit
OLD_MEMORY_DAYS = 90            # Age threshold
LOW_IMPORTANCE_THRESHOLD = 3.0  # Importance cutoff
REDUNDANCY_THRESHOLD = 0.95     # Similarity for dedup
```

**Tuning Chunking** (`precompact_memory_extractor.py`):
```python
MAX_TRANSCRIPT_MESSAGES = 1000  # Max messages to process
AUTO_PRUNE = True               # Auto-prune on compaction
```

---

### Key Learnings

**What Works Well**:
- ✅ Nomic-embed-text-v1.5 is excellent for code (768d, 8k context)
- ✅ Task-context scoring significantly improves retrieval relevance
- ✅ Adaptive K prevents low-quality result spam
- ✅ Knowledge graphs capture entity relationships naturally
- ✅ Full transcript storage (no truncation) maintains context

**What to Avoid**:
- ❌ Claude API reranking (too slow, costs $$, breaks "local-first" philosophy)
- ❌ Version suffixes in filenames (use __version__.py instead)
- ❌ Fixed top-K retrieval (use adaptive K based on quality)
- ❌ Truncating transcripts (lose important details)

**Improvement Opportunities**:
- ⏳ Temporal decay (age-based importance reduction)
- ⏳ Access count tracking (frequently-accessed = more important)
- ⏳ Entity quality filtering (remove junk entities)
- ⏳ Multi-hop chain retrieval (reconstruct conversation chains)

---

### Research Sources

**Anthropic**:
- [Context Management](https://www.anthropic.com/news/context-management)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [RAG Cookbook](https://github.com/anthropics/claude-cookbooks/blob/main/skills/retrieval_augmented_generation/guide.ipynb)

**Academic**:
- LexRank (Erkan & Radev, 2004) - Graph-based lexical centrality
- TextRank (Mihalcea & Tarau, 2004) - PageRank for text
- Entity Salience (Dunietz & Gillick, 2014) - Knowledge graph importance

**Embedding Models**:
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Nomic Embed](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)

---

### Industry Research Findings (2024-2025)

**🎯 V7 Validates Industry Best Practices!**

#### Anthropic's Contextual Retrieval (Sept 2024)

**Source**: [Contextual Retrieval announcement](https://www.anthropic.com/news/contextual-retrieval)

**Their Approach:**
- Prepend 50-100 token context to chunks before embedding
- Format: `"{session context}. {file context}. {content}"`
- Use Claude to auto-generate contextual prefixes

**Their Results:**
- **35% reduction** in retrieval failures (contextual embeddings alone)
- **67% reduction** with contextual embeddings + reranking
- Tested on proprietary benchmark (top-20 chunk retrieval)

**Our V7 Implementation:**
- ✅ Prepend ~20-30 token context before embedding
- ✅ Format: `"Session {id[:8]} at {time}. Files: {files}. {content}"`
- ✅ **Same principle as Anthropic!**
- ❌ No reranking (local-first constraint)

**Key Metric: Top-K Retrieval Failure Rate**
- Anthropic: 5.7% → 3.7% (contextual only)
- Our V7 test: 80% temporal success vs 20% V6 success

---

#### Standard RAG Metrics (2024 Literature)

**Sources**:
- NVIDIA: [Evaluating Retriever for Enterprise RAG](https://developer.nvidia.com/blog/evaluating-retriever-for-enterprise-grade-rag/)
- Qdrant: [RAG Evaluation Guide](https://qdrant.tech/blog/rag-evaluation-guide/)
- ArXiv: [Evaluation of Retrieval-Augmented Generation Survey](https://arxiv.org/html/2405.07437v2)

**Retrieval Metrics (What We Have):**
- ✅ **Precision@k**: % of retrieved memories that are relevant
- ✅ **Recall@k**: % of relevant memories that were retrieved
- ✅ **F1@k**: Harmonic mean of precision and recall
- ✅ **MRR** (Mean Reciprocal Rank): 1/rank of first relevant result

**RAG-Specific Metrics (To Add):**
- ❌ **NDCG** (Normalized Discounted Cumulative Gain): Rank-order quality
- ❌ **Context Recall**: % of relevant context actually retrieved
- ❌ **Context Precision**: % of retrieved context that's relevant
- ❌ **Faithfulness**: Did response use retrieved context (not hallucinate)?
- ❌ **Answer Relevancy**: How well does response answer query?

---

#### Public Benchmarks

**BEIR** (Benchmarking Information Retrieval):
- 18 datasets covering 9 IR tasks
- Includes: fact-checking, QA, bio-medical IR, news retrieval
- Standard for general retrieval evaluation
- [Paper: Thakur et al., 2021](https://arxiv.org/abs/2104.08663)

**MTEB** (Massive Text Embedding Benchmark):
- 58 datasets across 8 embedding tasks
- 112 languages
- Used for embedding model comparison
- Our model (nomic-embed-text-v1.5) ranks top-10
- [Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

**LongEval & SocialBench**:
- Test context retention over 40-600 turns
- Measure memory consistency in long conversations
- Published: 2024
- Relevant for our multi-session scenarios

---

#### Long-Horizon Task Evaluation (OpenAI)

**Source**: [OpenAI Evals Framework](https://github.com/openai/evals)

**Key Insights:**
- Manual evaluation is hard for multi-turn scenarios
- Need automated metrics for task completion
- Memory consistency crucial for long-horizon agents

**Metrics for Long-Horizon:**
- **Task Completion Rate**: Binary success/fail across sessions
- **Memory Consistency**: Do agents maintain context across 40+ turns?
- **Session Carryover**: Can agent resume work from previous session?

**Example Scenario (from OpenAI Cookbook):**
```
Session 1: Implement auth.py
→ Compaction
Session 2: "Add OAuth to auth system"
→ Measure: Did memories help? Faster? More correct?
```

**To Build:**
- Multi-session benchmark with real coding tasks
- Measure: baseline (no memories) vs V6 vs V7
- Track: task success, time to completion, hallucination rate

---

#### V7 Alignment with Industry Standards

| Aspect | Industry Standard | Our V7 Implementation | Status |
|--------|------------------|----------------------|--------|
| **Contextual Embeddings** | Anthropic (50-100 tokens) | 20-30 token prefix | ✅ Implemented |
| **Retrieval Metrics** | Precision, Recall, F1, MRR | All 4 metrics | ✅ Complete |
| **RAG Metrics** | NDCG, Context Recall/Precision | Missing | ❌ To Add |
| **Faithfulness** | Industry standard | Not implemented | ❌ To Add |
| **Long-Horizon** | OpenAI Evals approach | Not implemented | ❌ To Build |
| **Embedding Model** | MTEB top-10 | nomic-embed (top-10) | ✅ Validated |
| **Local-First** | N/A (most use APIs) | 100% local, no API | ✅ Unique |

---

#### Citations & Further Reading

**Academic Papers:**
- Thakur et al. (2021). "BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models" - ArXiv:2104.08663
- Erkan & Radev (2004). "LexRank: Graph-based Lexical Centrality" - Used in our knowledge graph approach
- Dunietz & Gillick (2014). "A New Entity Salience Task" - Inspired our entity importance scoring

**Industry Research:**
- Anthropic (Sept 2024). "Introducing Contextual Retrieval" - Our V7 validates this approach
- OpenAI (2024). "Evals Framework" - Standard for LLM evaluation
- NVIDIA (2024). "Evaluating Retriever for Enterprise-Grade RAG" - Comprehensive metric guide

**Benchmarks:**
- BEIR: https://github.com/beir-cellar/beir
- MTEB: https://huggingface.co/spaces/mteb/leaderboard
- OpenAI Evals: https://github.com/openai/evals

---

### Notes

- Memory DB: `~/.claude/memory_db/`
- Debug logs: `~/.claude/memory_hooks_debug.log`
- ChromaDB collection: `conversation_memories`
- Current version: **V7.0.0** (check `hooks/__version__.py`)
- Compaction triggers at ~80-95% context usage (not user-configurable)
- Manual compaction: `/compact` command

---

### Evaluation Framework (V7)

**Test Set Structure**:
- Ground-truth queries with expected relevant memories
- Measures: Precision, Recall, F1, MRR (Mean Reciprocal Rank)
- Baseline: V6 system (before contextual embeddings)
- Target: V7 system (with contextual embeddings)

**Test Queries** (examples):
- "work from yesterday" (temporal)
- "changes to auth.py" (file-specific)
- "bug fixes" (semantic)
- "IronFlow project" (project-specific)

**Evaluation Script**: `hooks/evaluate_retrieval.py` (V7)

---

### Test Suite (V7)

**Comprehensive test coverage** for the memory system with focus on critical paths.

**Test Statistics**:
- **293 tests** across 8 test files
- **49% overall coverage** (940 of 1,930 statements)
- All tests passing with pytest + pytest-cov

**Module Coverage Highlights**:
| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| multimodal_extractor.py | **90%** | 46 | ✅ Excellent |
| memory_scorer.py | **86%** | 48 | ✅ Excellent |
| knowledge_graph.py | **82%** | 53 | ✅ Excellent |
| precompact_memory_extractor.py | **79%** | 28 | ✅ Strong |
| sessionstart_memory_injector.py | **75%** | 21 | ✅ Strong |
| entity_extractor.py | **70%** | 23 | ✅ Good |
| task_context_scorer.py | **67%** | 43 | ✅ Good |
| evaluate_retrieval.py | **43%** | 31 | ⚠️  Moderate |

**Test Files**:
1. `tests/test_memory_scorer.py` - All 10 importance scoring signals
2. `tests/test_evaluate_retrieval.py` - Precision, Recall, F1, MRR, NDCG metrics
3. `tests/test_knowledge_graph.py` - Graph building, PageRank, traversal
4. `tests/test_entity_extractor.py` - FILE, FUNCTION, BUG entity extraction
5. `tests/test_task_context_scorer.py` - Task-aware importance boosting
6. `tests/test_multimodal_extractor.py` - Code, file, command, error extraction
7. `tests/test_precompact_integration.py` - Full PreCompact hook pipeline
8. `tests/test_sessionstart_integration.py` - SessionStart with task-context

**Running Tests**:
```bash
# All tests with coverage
pytest tests/ --cov=hooks --cov-report=term-missing

# Specific module
pytest tests/test_memory_scorer.py -v

# With HTML coverage report
pytest tests/ --cov=hooks --cov-report=html:htmlcov

# Fast run (no coverage)
pytest tests/ -q
```

**Test Configuration**:
- `pytest.ini` - Test discovery, coverage settings
- `requirements-dev.txt` - Testing dependencies (pytest, pytest-cov, faker, etc.)
- `.gitignore` - Excludes .coverage, htmlcov/, __pycache__/

**Key Testing Patterns**:
- **Mock ChromaDB**: All database tests use mocked collections
- **Mock SentenceTransformer**: Avoid loading 768MB model in tests
- **Integration tests**: Test full PreCompact → SessionStart flow
- **Edge cases**: Empty inputs, malformed data, error conditions
- **Realistic data**: Use actual memory structures from production system

**Testing Philosophy**:
- ✅ Test critical paths first (hooks, scoring, retrieval)
- ✅ Focus on behavior, not implementation details
- ✅ Integration tests > unit tests for complex flows
- ✅ Tests as living documentation of system behavior
- ⚠️  Tests may need updates as system evolves (e.g., LLM-based entity extraction)
