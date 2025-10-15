# Claude Code Memory System V7

**Intelligent memory preservation system with contextual embeddings, knowledge graphs, and task-context awareness.**

Stop losing context when your conversations get compacted! This system automatically extracts, scores, and preserves important memories from your coding sessions, then intelligently injects the most relevant ones back using contextual embeddings, knowledge graph traversal, and task-context scoring.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Features

### V7: Contextual Embeddings + Last Actions
- **🎯 "Where You Left Off"**: Shows last 5 actions, files, and status before compaction (the "50 First Dates" solution!)
- **📝 Contextual Embeddings**: Prepends session/time/file context to embeddings for better retrieval
- **⏰ Temporal Queries**: Find "yesterday's work" or "last week's changes" naturally
- **📁 File-Context Queries**: Search "auth.py changes" or "modifications to utils.py"
- **📊 Evaluation Framework**: Precision, Recall, F1, MRR metrics for measuring quality
- **✅ Test Suite**: 293 tests, 49% coverage across critical components

### V6: Clean Architecture + Centralized Versioning
- **📦 No Version Suffixes**: Clean filenames (precompact.py, not precompact_v2.py)
- **🔢 Centralized Versions**: All versions tracked in __version__.py
- **📋 Proper Semantic Versioning**: Major.Minor.Patch format

### V5: Knowledge Graph + Task-Context Awareness
- **🕸️ Knowledge Graph**: Automatically extracts entities (files, functions, bugs, features) and builds relationship graph
- **🎯 Task-Context Scoring**: Boosts memories relevant to current work (1.5-3x importance)
- **📈 PageRank Centrality**: Identifies most important entities across conversations
- **🔗 Multi-Hop Traversal**: Finds related memories through graph relationships (1-2 hops)
- **📊 Adaptive K Retrieval**: Returns 0-20 memories dynamically based on quality (not fixed top-K!)

### V4: Full Transcripts + Better Embeddings
- **📝 Full Transcript Storage**: No truncation! Complete intent/action/outcome preserved
- **🚀 nomic-embed-text-v1.5**: 768-dim embeddings with 8192 token context (16x better than old model!)
- **🎨 Hierarchical Display**: Short summaries for injection, full transcripts via query tool
- **⚡ 85% Relevance Improvement**: Task-relevant queries: 72% vs 39% with old system

### Core Memory System
- **🧠 Smart Chunking**: Automatically breaks conversations into Intent-Action-Outcome triplets
- **⭐ Importance Scoring**: 10+ signals identify critical memories (decisions, fixes, learnings)
- **🎯 Vector Search**: Fast semantic retrieval with HNSW indexing (ChromaDB)
- **🔄 Auto-Pruning**: Removes old/redundant memories based on age, similarity, and capacity
- **📊 Hierarchical Clustering**: Organizes related memories into topical groups

### Multi-Modal Artifacts
Automatically extracts and indexes:
- 💻 **Code snippets** with language tags
- 📁 **File paths** modified/created
- 🏗️ **Architecture discussions** and design decisions
- ⚙️ **Commands executed**
- ❌ **Error messages** and troubleshooting
- 🔧 **Tools used** (Read, Write, Edit, Bash, etc.)

### No API Costs
- **100% Local**: Uses sentence-transformers for embeddings (nomic-embed-text-v1.5)
- **No API calls**: Smart rule-based chunking (no LLM needed)
- **Offline-first**: Works without internet connection

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- Claude Code CLI
- ~500MB disk space (for dependencies)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/rhowardstone/claude-code-memory-system.git
cd claude-code-memory-system

# Run installer (safely updates settings.json)
./install.sh
```

The installer will:
1. Copy hooks to `~/.claude/memory-hooks/`
2. Install Python dependencies (chromadb, sentence-transformers, etc.)
3. Update `~/.claude/settings.json` with hook configuration
4. Create memory database directory

### Manual Installation

If you prefer manual setup, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## 🚀 How It Works

### The Memory Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Normal Coding Session                     │
│  You work with Claude Code, creating files, fixing bugs...  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Context fills up
                         ↓
                  ┌──────────────┐
                  │  /compact    │
                  │   triggers   │
                  └──────┬───────┘
                         │
                         ↓
        ┌────────────────────────────────────┐
        │     PreCompact Hook Fires          │
        │  • Loads conversation transcript   │
        │  • Smart chunking (IAO triplets)   │
        │  • Importance scoring              │
        │  • Multi-modal extraction          │
        │  • Stores in vector DB             │
        │  • Auto-prunes old memories        │
        │  • Creates hierarchical clusters   │
        └────────────────┬───────────────────┘
                         │
                         ↓
               ┌──────────────────┐
               │   Compaction     │
               │  (Claude Code's  │
               │   internal)      │
               └─────────┬────────┘
                         │
                         ↓
        ┌────────────────────────────────────┐
        │    SessionStart Hook Fires         │
        │  • Retrieves 5 recent important    │
        │  • Retrieves 10 relevant (vector)  │
        │  • Combines importance + relevance │
        │  • Injects via additionalContext   │
        └────────────────┬───────────────────┘
                         │
                         ↓
        ┌────────────────────────────────────┐
        │      New Session Starts            │
        │  Claude sees previous memories!    │
        │  Continuity preserved across gap   │
        └────────────────────────────────────┘
```

### What Gets Preserved?

**Automatically scored by importance:**
- 🔴 **Critical (20+)**: Architectural decisions, major bug fixes, key learnings
- 🟠 **High (10-20)**: File creations, test successes, important changes
- 🟡 **Medium (5-10)**: Code snippets, moderate edits, context
- 🟢 **Low (<5)**: Routine work, minor changes

**Example memories:**
```json
{
  "intent": "Fix authentication bug causing 401 errors",
  "action": "Modified auth.ts to properly handle token expiry, added refresh logic",
  "outcome": "Tests passing, bug resolved",
  "importance": 24.5,
  "artifacts": {
    "files": ["src/auth.ts", "tests/auth.test.ts"],
    "code_snippets": ["async function refreshToken() { ... }"],
    "architecture": ["token refresh flow"]
  }
}
```

---

## 🎯 Usage

### Automatic Usage (Recommended)

Just use Claude Code normally! Memories are automatically:
1. **Extracted** when compaction triggers (PreCompact hook)
2. **Injected** when session resumes after compaction (SessionStart hook)

### CLI Tools

Browse and search your memories anytime with `query_memories.py`:

```bash
# View statistics
python3 ~/.claude/memory-hooks/query_memories.py --stats

# Search by topic (semantic)
python3 ~/.claude/memory-hooks/query_memories.py --topic "authentication bug fix"

# Search by keywords
python3 ~/.claude/memory-hooks/query_memories.py --keywords error crash failed

# High importance only
python3 ~/.claude/memory-hooks/query_memories.py --min-importance 15

# Find files involved in errors
python3 ~/.claude/memory-hooks/query_memories.py --files-involved --keywords bug

# Date range search
python3 ~/.claude/memory-hooks/query_memories.py --since "2025-10-12" --until "2025-10-13"

# Session-specific
python3 ~/.claude/memory-hooks/query_memories.py --session current --topic "recent work"

# Detailed output
python3 ~/.claude/memory-hooks/query_memories.py --topic "testing" --format detailed

# JSON output for scripting
python3 ~/.claude/memory-hooks/query_memories.py --topic "bugs" --format json
```

### Example Output

```
📊 Memory Statistics
================================================================================
Total memories: 42
Average importance: 16.8

Importance Distribution:
  🟢 Low       :    3 (  7.1%) █
  🟡 Medium    :    5 ( 11.9%) ██
  🟠 High      :   28 ( 66.7%) █████████████
  🔴 Critical  :    6 ( 14.3%) ██

Multi-modal Content:
  💻 Has code: 18 (42.9%)
  📁 Has files: 32 (76.2%)
  🏗️  Has architecture: 8 (19.0%)
```

---

## ⚙️ Configuration

### Tuning Importance Scoring

Edit `~/.claude/memory-hooks/memory_scorer.py`:

```python
WEIGHTS = {
    "decision_marker": 10.0,      # "decided to", "chose"
    "error_resolution": 8.0,       # "fixed", "resolved"
    "file_creation": 6.0,          # New files created
    "test_success": 5.0,           # Tests passing
    "learning": 7.0,               # "learned", "discovered"
    # ... adjust as needed
}
```

### Tuning Memory Retrieval

Edit `~/.claude/memory-hooks/sessionstart_memory_injector.py`:

```python
TOP_K_MEMORIES = 20           # Maximum memories (adaptive returns 0-20)
RECENT_MEMORIES = 4            # Recent chronological
MIN_IMPORTANCE = 5.0           # Minimum score to inject
MIN_SIMILARITY = 0.35          # Minimum relevance threshold
KG_CACHE_TTL = 300            # Knowledge graph cache lifetime (seconds)
```

### Tuning Auto-Pruning

Edit `~/.claude/memory-hooks/memory_pruner.py`:

```python
MAX_MEMORIES_PER_SESSION = 500  # Capacity limit
OLD_MEMORY_DAYS = 90            # Age threshold
LOW_IMPORTANCE_THRESHOLD = 3.0  # Importance cutoff
REDUNDANCY_THRESHOLD = 0.95     # Similarity for dedup
```

### Tuning Chunking

Edit `~/.claude/memory-hooks/precompact_memory_extractor.py`:

```python
MAX_TRANSCRIPT_MESSAGES = 1000  # Max messages to process
AUTO_PRUNE = True               # Auto-prune on compaction
```

---

## 📊 Architecture

### Components

```
~/.claude/
├── memory-hooks/
│   ├── precompact_memory_extractor.py      # V4: Full transcript extraction
│   ├── sessionstart_memory_injector.py     # V5: Task-context aware injection
│   ├── entity_extractor.py                 # Entity extraction
│   ├── knowledge_graph.py                  # Graph construction
│   ├── task_context_scorer.py              # Task-context scoring
│   ├── query_memories.py                   # CLI query interface
│   ├── memory_scorer.py                    # Importance calculation
│   ├── multimodal_extractor.py             # Artifact extraction
│   ├── memory_pruner.py                    # Auto-pruning logic
│   ├── memory_clustering.py                # Hierarchical clustering
│   └── requirements.txt                    # Python dependencies
├── memory_db/                              # ChromaDB storage
│   └── (vector database files)
└── settings.json                           # Hook configuration
```

### Data Flow

1. **Extraction (PreCompact)**:
   - Transcript → Format → Smart chunk → Score → Extract artifacts → Embed → Store

2. **Retrieval (SessionStart)**:
   - Query → Vector search + Recent filter → Rank by importance × relevance → Format → Inject

3. **Pruning (Automatic)**:
   - Age-based: Old + low importance
   - Redundancy: Near-duplicates (>95% similarity)
   - Capacity: Keep top N by importance

---

## 🐛 Troubleshooting

### Debug Logs

All operations are logged to `~/.claude/memory_hooks_debug.log`:

```bash
tail -f ~/.claude/memory_hooks_debug.log
```

### Common Issues

**"No memories found"**
- Haven't run `/compact` yet
- Hooks not configured correctly in settings.json
- Check: `cat ~/.claude/settings.json | grep hooks`

**"Import errors"**
- Missing dependencies
- Fix: `pip install -r ~/.claude/memory-hooks/requirements.txt`

**"Hooks not firing"**
- Check settings.json format (must use array with matcher)
- Ensure scripts are executable: `chmod +x ~/.claude/memory-hooks/*.py`
- Check debug log for errors

**"Too few memories extracted"**
- Increase MAX_TRANSCRIPT_MESSAGES in precompact_memory_extractor.py
- Adjust chunking thresholds for more granular chunks

**"Too many memories"**
- Lower MAX_MEMORIES_PER_SESSION in memory_pruner.py
- Raise MIN_IMPORTANCE in sessionstart_memory_injector.py
- Run manual pruning (see memory_pruner.py)

---

## 🔬 Technical Details

### Embeddings (V4 Upgrade)
- **Model**: `nomic-ai/nomic-embed-text-v1.5` (768 dimensions)
- **Context**: 8192 tokens (16x better than old 512-token model!)
- **Size**: ~140MB
- **Speed**: ~500 embeddings/sec on CPU
- **Quality**: Ranks with top-10 models 70x bigger; perfect for code!
- **Upgrade**: 85% relevance improvement over old all-MiniLM-L6-v2

### Vector Database
- **Engine**: ChromaDB with HNSW indexing
- **Distance**: Cosine similarity
- **Indexing**: Automatic on insert
- **Storage**: Persistent local disk

### Importance Scoring Signals
1. Decision markers ("decided", "chose", "will use")
2. Error resolution ("fixed", "resolved", "debugged")
3. File operations (created, modified)
4. Test success (tests passing)
5. Learning indicators ("learned", "discovered")
6. Tool usage count
7. Code presence
8. Architecture discussions
9. Recency (exponential decay)
10. Session context

### Chunking Strategy
- Natural boundaries: File operations, decisions, topic changes
- Grouped operations: 3-5 related file writes
- Size limits: Intent (500 chars), Action (1000 chars), Outcome (300 chars)
- Deduplication: Skip empty/duplicate chunks

---

## 📚 Examples

See [examples/](examples/) directory for:
- Real conversation memory extracts
- CLI usage examples
- Integration patterns
- Custom scoring configurations

---

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

### Development Setup

```bash
# Clone and install in dev mode
git clone https://github.com/rhowardstone/claude-code-memory-system.git
cd claude-code-memory-system
pip install -r hooks/requirements.txt

# Test installation
./install.sh
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built for [Claude Code](https://claude.ai/claude-code)
- Uses [ChromaDB](https://www.trychroma.com/) for vector storage
- Embeddings from [sentence-transformers](https://www.sbert.net/)
- Inspired by human episodic memory systems

---

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/rhowardstone/claude-code-memory-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rhowardstone/claude-code-memory-system/discussions)
- **Documentation**: [docs/](docs/)

---

## 🗺️ Roadmap

- [ ] Cross-session memory (with explicit user permission)
- [ ] Memory visualization dashboard
- [ ] Custom scoring rules via config file
- [ ] Memory export formats (Markdown, HTML, PDF)
- [ ] Integration with external knowledge bases
- [ ] Multi-language support for code artifacts
- [ ] Compression for very old memories
- [ ] Collaborative memory sharing (team features)

---

**Built with ❤️ for the Claude Code community**
