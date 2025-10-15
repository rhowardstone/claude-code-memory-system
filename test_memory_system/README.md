# Memory System Integration Test

This directory contains a full integration test for the memory preservation system.

## What It Does

1. Runs a real `claude` session to build IronFlow (a workout app)
2. Captures the actual conversation transcript
3. Tests memory extraction with PreCompact hook
4. Analyzes memories with the CLI tool

## Run the Test

```bash
./test_memory_system/run_test.sh
```

The script will:
- Create a workspace in `test_memory_system/ironflow_workspace/`
- Run Claude interactively (you can respond to questions)
- After you Ctrl+C, automatically extract and analyze memories
- Show statistics, search results, and clusters

## Files

- `run_test.sh` - Main test script
- `ironflow_workspace/` - Working directory for Claude (created on first run)
- Results will be saved here after test completes

## Manual Testing

If you prefer to run Claude manually:

```bash
cd test_memory_system/ironflow_workspace
claude --print "$(cat ironflow_spec.txt)"
```

Then manually test memory extraction:

```bash
TRANSCRIPT=~/.claude/projects/*/path/to/transcript.jsonl
SESSION_ID=$(basename "$TRANSCRIPT" .jsonl)

cd ~/.claude/memory-hooks
python3 precompact_memory_extractor_v2.py << EOF
{
  "session_id": "$SESSION_ID",
  "transcript_path": "$TRANSCRIPT",
  "trigger": "manual"
}
EOF

python3 memory_cli.py stats --session $SESSION_ID
```
