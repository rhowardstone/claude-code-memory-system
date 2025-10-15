#!/usr/bin/env python3
"""Test SessionStart V5 - Task-Context Aware"""

import json
import subprocess
import sys

# Simulate SessionStart hook input
hook_input = {
    "session_id": "e58105f1-cf15-48f1-b0fc-00eddc952774",
    "trigger": "compact"
}

print("=" * 80)
print("TESTING SESSIONSTART V5 - TASK-CONTEXT AWARE")
print("=" * 80)
print()
print("Running SessionStart V5 hook...")
print()

# Run the hook
result = subprocess.run(
    ["python3", "/home/rye/.claude/memory-hooks/sessionstart_memory_injector_v5.py"],
    input=json.dumps(hook_input),
    capture_output=True,
    text=True,
    timeout=120
)

if result.returncode != 0:
    print("❌ Hook failed!")
    print(f"STDERR: {result.stderr}")
    sys.exit(1)

# Parse output
try:
    output = json.loads(result.stdout)
    context = output.get("hookSpecificOutput", {}).get("additionalContext", "")

    # Show first 2000 chars of context
    print("✅ Hook succeeded!")
    print()
    print("=" * 80)
    print("INJECTED CONTEXT (first 2000 chars):")
    print("=" * 80)
    print(context[:2000])
    print()
    print("..." if len(context) > 2000 else "")
    print()
    print(f"Total context length: {len(context)} characters")

except Exception as e:
    print(f"❌ Failed to parse output: {e}")
    print(f"STDOUT: {result.stdout}")
