# Examples

Example outputs and usage patterns for the Claude Code Memory System V5.

---

## Example Memory Export

See [example_memory_export.json](example_memory_export.json) for a sample of what extracted memories look like.

This shows:
- Intent-Action-Outcome structure
- Importance scoring (critical to high)
- Multi-modal artifacts (code, files, architecture)
- Metadata and timestamps

---

## CLI Usage Examples

### Basic Workflow

```bash
# Start with a fresh project
cd my-project
claude

# ... work on the project ...
# ... compaction triggers naturally ...

# View what was preserved
python3 ~/.claude/memory-hooks/query_memories.py --stats

# Search for something specific
python3 ~/.claude/memory-hooks/query_memories.py --topic "authentication"
```

### Reviewing Past Work

```bash
# What did I work on last week?
python3 ~/.claude/memory-hooks/query_memories.py --topic "what did I implement"

# Find that bug fix
python3 ~/.claude/memory-hooks/query_memories.py --keywords "race condition" fix

# View all critical decisions
python3 ~/.claude/memory-hooks/query_memories.py --min-importance 20
```

### Memory Management

```bash
# Check memory usage
du -sh ~/.claude/memory_db

# View database statistics
python3 ~/.claude/memory-hooks/query_memories.py --stats

# Backup before major operations
cp -r ~/.claude/memory_db ~/.claude/memory_db.backup
```

### Advanced Analysis

```bash
# Export to JSON
python3 ~/.claude/memory-hooks/query_memories.py --format json > memories.json

# Find high-importance memories with jq
cat memories.json | jq '[.[] | select(.metadata.importance_score > 20)]'

# Count by importance category
cat memories.json | jq '[.[] | .metadata.importance_category] | group_by(.) | map({category: .[0], count: length})'

# Find memories with code
cat memories.json | jq '[.[] | select(.metadata.has_code == true)]'

# Extract all file paths
cat memories.json | jq -r '[.[] | .metadata.artifacts | fromjson | .file_paths[]] | unique | .[]'
```

---

## Integration Patterns

### Pre-Commit Hook

Add memory export to git pre-commit:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Export important memories for this session
SESSION_ID=$(ls -t ~/.claude/projects/*/*.jsonl | head -1 | xargs basename -s .jsonl)
python3 ~/.claude/memory-hooks/query_memories.py \
  --session "$SESSION_ID" \
  --format json \
  --min-importance 15 > "docs/memories/$(date +%Y%m%d).json"

git add docs/memories/
```

### Periodic Backup

Cron job for daily backup:

```bash
# Add to crontab (crontab -e)
0 0 * * * cp -r ~/.claude/memory_db ~/backups/memory_db_$(date +%Y%m%d)
0 0 * * 0 find ~/backups/memory_db_* -mtime +30 -delete
```

### Team Sharing

Export and share memories with your team:

```bash
# Export important project decisions
python3 ~/.claude/memory-hooks/query_memories.py \
  --session project-abc \
  --min-importance 15 \
  --format json > team-shared/project-decisions.json

# Filter to critical only
cat team-shared/project-decisions.json | \
  jq '[.[] | select(.metadata.importance_score > 20)]' > \
  team-shared/critical-decisions.json
```

---

## Custom Scoring Examples

### Adjust for Your Project

Edit `~/.claude/memory-hooks/memory_scorer.py`:

```python
# For documentation-heavy projects
WEIGHTS = {
    "decision_marker": 10.0,
    "documentation": 9.0,  # Boost documentation importance
    "file_creation": 6.0,
    # ... rest
}

# For test-driven development
WEIGHTS = {
    "test_success": 10.0,  # Boost test importance
    "test_coverage": 8.0,
    "error_resolution": 7.0,
    # ... rest
}
```

---

## Troubleshooting Scenarios

### Scenario 1: Missing Important Memory

```bash
# Check if it was extracted
python3 ~/.claude/memory-hooks/query_memories.py --keywords "keyword from conversation"

# If not found, check debug log
tail -100 ~/.claude/memory_hooks_debug.log | grep "session-id"

# Manually re-extract if needed
cd ~/.claude/memory-hooks
cat << EOF | python3 precompact_memory_extractor_v2.py
{
  "session_id": "your-session-id",
  "transcript_path": "/path/to/transcript.jsonl",
  "hook_event_name": "PreCompact",
  "trigger": "manual"
}
EOF
```

### Scenario 2: Too Many Low-Quality Memories

```bash
# Increase minimum importance threshold
# Edit sessionstart_memory_injector_v5.py:
MIN_IMPORTANCE = 5.0  # Was 3.0

# Run pruning (see memory_pruner.py for configuration)
```

### Scenario 3: Slow Performance

```bash
# Check database size
du -sh ~/.claude/memory_db

# If too large, aggressive pruning
# Edit memory_pruner.py:
MAX_MEMORIES_PER_SESSION = 200  # Was 500
OLD_MEMORY_DAYS = 30  # Was 90

# Then run PreCompact on next compaction
```

### Scenario 4: V5 Knowledge Graph Performance

```bash
# Knowledge graph builds on first query after compaction
# Check cache TTL in sessionstart_memory_injector_v5.py:
KG_CACHE_TTL = 300  # seconds (5 minutes)

# For faster startup, increase cache lifetime:
KG_CACHE_TTL = 1800  # 30 minutes

# Or rebuild manually:
python3 << EOF
from knowledge_graph import MemoryKnowledgeGraph
kg = MemoryKnowledgeGraph("/home/user/.claude/memory_db")
kg.build_from_memories(session_id="all")
kg.compute_centrality()
print(f"Graph: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
EOF
```

---

## Real-World Use Cases

### Use Case 1: Multi-Week Project

Developer building e-commerce platform:

**Week 1**: Set up architecture, chose tech stack
**Week 2**: Implement user auth
**Week 3**: Build product catalog
**Week 4**: Add cart and checkout

Each compaction preserves key decisions. In Week 4, when building checkout, Claude remembers the auth patterns from Week 2 without you needing to explain again.

**V5 Benefit**: Knowledge graph connects auth.ts → user.ts → cart.ts, boosting relevant memories automatically!

### Use Case 2: Bug Hunting

Finding an intermittent bug:

**Session 1**: Noticed bug, added logging
**Session 2**: Found race condition in cache
**Session 3**: Implemented fix with mutex

After compaction between sessions, context is preserved. Session 3 starts knowing about the logging added in Session 1 and the race condition identified in Session 2.

**V5 Benefit**: Task-context scoring boosts memories about "race condition" + "cache" when working on fix!

### Use Case 3: Code Review

Reviewing large PR:

**Session 1**: Review authentication changes (200 lines)
**Session 2**: Review API endpoints (300 lines)
**Session 3**: Review frontend integration (400 lines)

After compactions, later sessions remember concerns from earlier reviews, ensuring consistent feedback.

**V5 Benefit**: Graph traversal finds related memories: auth.ts FIXES → USES → api/routes.ts USES → frontend/auth.tsx

---

## Performance Benchmarks

On typical hardware (i5 processor, 16GB RAM):

**V5 (nomic-embed-text-v1.5):**
- **Extraction**: ~1-2 seconds for 600 messages
- **Embedding**: ~1 second for 50 chunks (768-dim, slower but better quality)
- **Knowledge Graph Build**: ~5-10 seconds for 400 memories (cached for 5 min)
- **Entity Extraction**: ~2-3 seconds for 50 chunks
- **Storage**: ~0.3 seconds for 50 chunks
- **Retrieval with Task-Context**: ~0.5 seconds (includes graph traversal)
- **Total overhead**: ~5-8 seconds per compaction (one-time), ~0.5s per query

**Storage:**
- Vector DB (768-dim): ~1.5MB per 100 memories
- Knowledge Graph: ~50KB per 100 entities
- Typical session: 20-50 memories = ~1MB

---

## V5-Specific Features

### Knowledge Graph Inspection

```bash
# View entities and relationships
python3 << EOF
import sys
sys.path.insert(0, "/home/user/.claude/memory-hooks")
from knowledge_graph import MemoryKnowledgeGraph

kg = MemoryKnowledgeGraph("/home/user/.claude/memory_db")
kg.build_from_memories(session_id="all")
kg.compute_centrality()

# Top entities by PageRank
top_entities = kg.get_top_entities(limit=10)
for entity, score in top_entities:
    print(f"{entity}: {score:.6f}")

# Entity relationships
entity = "auth.ts"
related = kg.get_related_entities(entity, max_hops=2)
print(f"\n{entity} is related to: {related[:10]}")
EOF
```

### Task-Context Query Example

```bash
# Query for bug fix work - task-context automatically boosts relevant memories
python3 ~/.claude/memory-hooks/query_memories.py \
  --topic "fix authentication bug" \
  --min-importance 10 \
  --format detailed

# V5 will boost memories containing entities like:
# - auth.ts (direct match)
# - login.tsx (1-hop: auth.ts USES login.tsx)
# - jwt.ts (1-hop: auth.ts USES jwt.ts)
# - database.ts (2-hop: auth.ts → user.ts → database.ts)
```

### Adaptive K in Action

```bash
# Same query, different result counts based on quality!

# High-quality matches available → returns many
python3 ~/.claude/memory-hooks/query_memories.py --topic "authentication implementation"
# Returns: 15 memories (all > 0.6 similarity)

# Medium-quality matches only → returns few
python3 ~/.claude/memory-hooks/query_memories.py --topic "random unrelated topic"
# Returns: 3 memories (0.4-0.6 similarity)

# No good matches → returns none
python3 ~/.claude/memory-hooks/query_memories.py --topic "completely irrelevant query"
# Returns: 0 memories (all < 0.4 similarity)
```

---

## Tips for Maximum Benefit

1. **Be Explicit**: State decisions clearly in conversation
2. **Use Descriptive Names**: File and function names help entity extraction (V5!)
3. **Document Why**: Explain reasoning, not just what
4. **Review Regularly**: Use CLI to refresh your memory too!
5. **Let V5 Work**: The knowledge graph and task-context scoring work automatically - just code naturally!
6. **Trust Adaptive K**: If no memories returned, that's intentional - none were relevant!
7. **Entity-Rich Conversations**: Mention files, functions, features explicitly for better graph construction
