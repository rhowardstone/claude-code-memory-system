# Examples

Example outputs and usage patterns for the Claude Code Memory System.

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
python3 ~/.claude/memory-hooks/memory_cli.py stats

# Search for something specific
python3 ~/.claude/memory-hooks/memory_cli.py search "authentication"
```

### Reviewing Past Work

```bash
# What did I work on last week?
python3 ~/.claude/memory-hooks/memory_cli.py search "what did I implement"

# Find that bug fix
python3 ~/.claude/memory-hooks/memory_cli.py search "fixed race condition"

# View all critical decisions
python3 ~/.claude/memory-hooks/memory_cli.py list | grep "🔴"
```

### Memory Management

```bash
# Check memory usage
du -sh ~/.claude/memory_db

# Prune old memories (dry run first)
python3 ~/.claude/memory-hooks/memory_cli.py prune

# Actually prune
python3 ~/.claude/memory-hooks/memory_cli.py prune --execute

# Backup before major pruning
cp -r ~/.claude/memory_db ~/.claude/memory_db.backup
```

### Advanced Analysis

```bash
# Export to JSON
python3 ~/.claude/memory-hooks/memory_cli.py export --output memories.json

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
python3 ~/.claude/memory-hooks/memory_cli.py export \
  --session "$SESSION_ID" \
  --output "docs/memories/$(date +%Y%m%d).json"

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
python3 ~/.claude/memory-hooks/memory_cli.py export \
  --session project-abc \
  --output team-shared/project-decisions.json

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
python3 ~/.claude/memory-hooks/memory_cli.py search "keyword from that conversation"

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
# Edit sessionstart_memory_injector_v2.py:
MIN_IMPORTANCE = 5.0  # Was 3.0

# Prune existing low-importance
python3 ~/.claude/memory-hooks/memory_cli.py prune --execute
```

### Scenario 3: Slow Performance

```bash
# Check database size
du -sh ~/.claude/memory_db

# If too large, aggressive pruning
# Edit memory_pruner.py:
MAX_MEMORIES_PER_SESSION = 200  # Was 500
OLD_MEMORY_DAYS = 30  # Was 90

# Apply
python3 ~/.claude/memory-hooks/memory_cli.py prune --execute
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

### Use Case 2: Bug Hunting

Finding an intermittent bug:

**Session 1**: Noticed bug, added logging
**Session 2**: Found race condition in cache
**Session 3**: Implemented fix with mutex

After compaction between sessions, context is preserved. Session 3 starts knowing about the logging added in Session 1 and the race condition identified in Session 2.

### Use Case 3: Code Review

Reviewing large PR:

**Session 1**: Review authentication changes (200 lines)
**Session 2**: Review API endpoints (300 lines)
**Session 3**: Review frontend integration (400 lines)

After compactions, later sessions remember concerns from earlier reviews, ensuring consistent feedback.

---

## Performance Benchmarks

On typical hardware (i5 processor, 16GB RAM):

- **Extraction**: ~1-2 seconds for 600 messages
- **Embedding**: ~0.5 seconds for 50 chunks
- **Storage**: ~0.2 seconds for 50 chunks
- **Retrieval**: ~0.1 seconds for vector search
- **Total overhead**: ~2-3 seconds per compaction

**Storage:**
- Vector DB: ~1MB per 100 memories
- Typical session: 20-50 memories = ~500KB

---

## Tips for Maximum Benefit

1. **Be Explicit**: State decisions clearly in conversation
2. **Use Descriptive Names**: File and function names help chunking
3. **Document Why**: Explain reasoning, not just what
4. **Review Regularly**: Use CLI to refresh your memory too!
5. **Prune Wisely**: Keep important memories, prune routine work
