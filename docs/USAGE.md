# Usage Guide

How to use the Claude Code Memory System effectively.

---

## Quick Start

Once installed, the memory system works automatically! Just:

1. **Use Claude Code normally** - work on your projects
2. **Let compaction trigger naturally** - when context fills up
3. **Memories are preserved** - automatically extracted and stored
4. **Continue after compaction** - relevant memories are injected

No manual intervention needed!

---

## Understanding the Memory Cycle

### Phase 1: Normal Work

Work with Claude Code as usual:
- Write code
- Debug issues
- Discuss architecture
- Create files
- Run tests

### Phase 2: Compaction Triggers

When context window fills up (~150k tokens), Claude Code triggers compaction.

You'll see:
```
🔄 Running PreCompact hooks...
```

**Behind the scenes:**
1. Conversation transcript is loaded
2. Smart chunking breaks it into Intent-Action-Outcome groups
3. Each chunk is scored for importance (0-30+)
4. Multi-modal artifacts extracted (code, files, architecture)
5. Embeddings generated with local model
6. Stored in vector database
7. Old/redundant memories auto-pruned
8. Hierarchical clusters created

### Phase 3: New Session Starts

After compaction completes:
```
🚀 Running SessionStart hooks...
```

**Behind the scenes:**
1. Recent important memories retrieved (top 5)
2. Semantically relevant memories retrieved (top 10 by vector search)
3. Combined and ranked by importance × relevance
4. Injected into new session as additional context

### Phase 4: Continuity Preserved

Your new session starts with relevant memories!

Claude will see:
- Important decisions you made
- Files you created/modified
- Bugs you fixed
- Architecture discussions
- Code patterns you established

---

## CLI Tools

### View Statistics

```bash
python3 ~/.claude/memory-hooks/query_memories.py --stats
```

Output:
```
📊 Memory Statistics
================================================================================
Total memories: 42
Average importance: 16.8

Importance Distribution:
  🟢 Low       :    3 (  7.1%)
  🟡 Medium    :    5 ( 11.9%)
  🟠 High      :   28 ( 66.7%)
  🔴 Critical  :    6 ( 14.3%)

Multi-modal Content:
  💻 Has code: 18 (42.9%)
  📁 Has files: 32 (76.2%)
  🏗️  Has architecture: 8 (19.0%)
```

### Search Memories

Semantic search across all memories:

```bash
python3 ~/.claude/memory-hooks/query_memories.py --topic "authentication bug"
```

Output:
```
🔍 Search Results for: 'authentication bug'
================================================================================

1. 🔴 Fix authentication token expiry handling [Similarity: 0.89]
   Importance: CRITICAL (24.5)
   Intent: Fix 401 errors on API calls after 1 hour
   Action: Modified auth.ts to implement token refresh logic
   Outcome: Tests passing, bug resolved
   Artifacts: 📁 src/auth.ts, src/auth.test.ts | 💻 Code

2. 🟠 Add authentication middleware [Similarity: 0.72]
   Importance: HIGH (15.2)
   Intent: Protect API routes with JWT verification
   Action: Created middleware/auth.ts with token validation
   Outcome: All routes now require authentication
   Artifacts: 📁 middleware/auth.ts
```

### List All Memories

```bash
# All memories
python3 ~/.claude/memory-hooks/query_memories.py --session current

# Specific session
python3 ~/.claude/memory-hooks/query_memories.py --session current --session abc123
```

### View Clusters

See how memories are organized:

```bash
python3 ~/.claude/memory-hooks/query_memories.py --stats --session abc123
```

Output:
```
🗂️  Memory Clusters for Session: abc123
================================================================================
Total memories: 42
Number of clusters: 5

📦 Cluster 0 (12 memories)
   Summary: Authentication and authorization implementation
   Top memories:
      🔴 Fix authentication token expiry handling...
      🟠 Add authentication middleware...
      🟠 Implement OAuth2 login flow...

📦 Cluster 1 (8 memories)
   Summary: Database schema and migrations
   Top memories:
      🟠 Design user table schema...
      🟠 Add migration for sessions table...
      🟡 Create index on email column...
```

### Prune Memories

Remove old or low-importance memories:

```bash
# Dry run (see what would be pruned)
python3 ~/.claude/memory-hooks/# See memory_pruner.py for pruning

# Actually prune
python3 ~/.claude/memory-hooks/# See memory_pruner.py for pruning --execute

# Prune specific session
python3 ~/.claude/memory-hooks/# See memory_pruner.py for pruning --session abc123 --execute
```

### Export Memories

Export to JSON for backup or analysis:

```bash
# Export all
python3 ~/.claude/memory-hooks/# query_memories.py --format json --output all_memories.json

# Export specific session
python3 ~/.claude/memory-hooks/# query_memories.py --format json --session abc123 --output session_abc.json
```

---

## Understanding Importance Scores

Memories are automatically scored 0-30+ based on multiple signals:

### 🔴 Critical (20+)
- Major architectural decisions
- Critical bug fixes
- Key learnings/discoveries
- Production issues resolved
- Breaking changes

**Example**: "Decided to migrate from REST to GraphQL for better data fetching"

### 🟠 High (10-20)
- File creations
- Test implementations
- Important refactorings
- Feature completions
- API integrations

**Example**: "Implemented user authentication with JWT tokens"

### 🟡 Medium (5-10)
- Code snippets
- Minor bug fixes
- Documentation updates
- Configuration changes
- Utility functions

**Example**: "Added validation helper for email addresses"

### 🟢 Low (<5)
- Routine edits
- Formatting changes
- Minor updates
- Exploratory work
- General discussion

**Example**: "Fixed typo in comment"

---

## Best Practices

### 1. Let It Work Automatically

Don't manually trigger compaction unless necessary. Natural compaction works best because:
- Claude Code picks optimal compaction points
- Hook system has full context
- Memories are properly preserved

### 2. Review Memories Periodically

```bash
# Weekly review
python3 ~/.claude/memory-hooks/query_memories.py --stats
python3 ~/.claude/memory-hooks/query_memories.py --topic "what did I work on"

# Monthly cleanup
python3 ~/.claude/memory-hooks/# See memory_pruner.py for pruning --execute
```

### 3. Use Descriptive Commit Messages

The system extracts meaning from your conversations. Clear descriptions help:

**Good**: "Fix race condition in user registration flow causing duplicate accounts"
**Bad**: "fix bug"

### 4. Discuss Architecture Explicitly

When making decisions, state them clearly:

**Good**: "I decided to use Redis for caching because we need fast session lookups"
**Bad**: "ok using redis"

### 5. Monitor Debug Log

If something seems wrong:

```bash
tail -f ~/.claude/memory_hooks_debug.log
```

---

## Common Workflows

### Debugging a Bug

1. Work with Claude to debug
2. Compaction triggers → bug fix is preserved
3. Next session: "What was that authentication bug we fixed?"
4. Claude remembers the fix from injected memories

### Long-term Project

1. Build project over multiple sessions
2. Each compaction preserves architectural decisions
3. New sessions have continuity
4. CLI search helps find past decisions

### Learning a New Library

1. Explore library with Claude
2. Important learnings are scored high
3. After compaction, key insights preserved
4. Next session picks up with that knowledge

### Code Review

1. Review code with Claude
2. Important issues flagged and remembered
3. After compaction, can reference past reviews
4. Search: "What issues did we find in the API?"

---

## Advanced Usage

### Finding Session IDs

```bash
# List all sessions
ls ~/.claude/projects/

# Or from transcript files
ls ~/.claude/projects/*/*.jsonl | xargs -I {} basename {} .jsonl
```

### Manual Memory Extraction

Test extraction without compaction:

```bash
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

### Backup Memories

```bash
# Backup database
cp -r ~/.claude/memory_db ~/.claude/memory_db.backup

# Backup specific session export
python3 ~/.claude/memory-hooks/# query_memories.py --format json \
  --session abc123 \
  --output backups/session_abc123_$(date +%Y%m%d).json
```

### Restore Memories

```bash
# Restore from backup
rm -rf ~/.claude/memory_db
cp -r ~/.claude/memory_db.backup ~/.claude/memory_db
```

---

## Troubleshooting

### "No memories found"

**Cause**: Haven't triggered compaction yet
**Solution**: Continue working until natural compaction triggers

### Memories seem irrelevant

**Cause**: Scoring weights may need adjustment
**Solution**: See [CONFIGURATION.md](CONFIGURATION.md) for tuning

### Too many/few memories

**Cause**: Pruning thresholds
**Solution**: Adjust `MAX_MEMORIES_PER_SESSION` in memory_pruner.py

### Slow performance

**Cause**: Large memory database
**Solution**: Run pruning more aggressively or reduce MAX_TRANSCRIPT_MESSAGES

---

## Tips & Tricks

### 1. Use Search Effectively

Search supports semantic understanding:

```bash
# These will find similar results:
query_memories.py --topic "auth bug"
query_memories.py --topic "authentication issue"
query_memories.py --topic "login not working"
```

### 2. Combine Search with Session Filter

```bash
# Find in specific session
query_memories.py --topic "API endpoint" --session abc123
```

### 3. Export for Analysis

```bash
# Export and analyze with jq
# query_memories.py --format json --output mem.json
cat mem.json | jq '[.[] | select(.metadata.importance_score > 20)]'
```

### 4. Monitor Memory Growth

```bash
# Check database size
du -sh ~/.claude/memory_db

# Check memory count
query_memories.py --stats | grep "Total memories"
```

---

## Next Steps

- [Configuration Guide](CONFIGURATION.md) - Customize scoring and pruning
- [Architecture Documentation](ARCHITECTURE.md) - Understand the internals
- [Contributing Guide](../CONTRIBUTING.md) - Help improve the system
