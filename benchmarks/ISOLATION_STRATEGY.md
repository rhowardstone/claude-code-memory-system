# SWE-Bench-CL Testing: Isolation Strategy

## The Problem

**CRITICAL**: Testing multiple memory system variants can contaminate our production V7 system!

### Contamination Risks:

1. **Hook overwriting**: Installing test variants → overwrites `~/.claude/memory-hooks/`
2. **Memory DB pollution**: Test memories → mixed with production memories in `~/.claude/memory_db/`
3. **Config corruption**: Different test configs → overwrites `~/.claude/settings.json`
4. **Import conflicts**: Multiple hook versions in path → unpredictable behavior

**Example disaster scenario:**
```bash
# We have working V7 installed:
~/.claude/memory-hooks/precompact_memory_extractor.py  # V7 with contextual embeddings

# Run SWE-Bench test with V6 variant:
./install_v6_variant.sh  # OVERWRITES hooks with V6!

# Now our real Claude Code sessions use V6 instead of V7!
# Production memory DB corrupted with test data!
# Can't reproduce V7 results!
```

---

## Isolation Requirements

### 1. Memory Database Isolation

Each variant MUST use a separate ChromaDB:

```python
# BAD: Uses production DB
memory_db_path = Path.home() / ".claude" / "memory_db"  # ❌

# GOOD: Isolated test DBs
memory_db_path = Path.home() / ".claude" / "memory_db_swebench_faiss"     # ✅
memory_db_path = Path.home() / ".claude" / "memory_db_swebench_v6"        # ✅
memory_db_path = Path.home() / ".claude" / "memory_db_swebench_v7"        # ✅
```

### 2. Hook Installation Isolation

**DO NOT install hooks to ~/.claude/memory-hooks/ during testing!**

```python
# BAD: Overwrites production hooks
cp hooks/* ~/.claude/memory-hooks/  # ❌

# GOOD: Direct imports from source
sys.path.insert(0, "/path/to/test/variant/hooks")  # ✅
from precompact_memory_extractor import store_enhanced_chunks
```

### 3. Virtual Environment Isolation

Create separate venv for SWE-Bench testing:

```bash
# Production environment (current)
conda activate base  # Our V7 system

# Testing environment (isolated)
python3 -m venv ~/.swebench_test_env
source ~/.swebench_test_env/bin/activate
```

### 4. Session Isolation

Test runs should NOT trigger our production hooks:

```python
# BAD: Runs inside Claude Code with hooks active
claude-code # ❌ PreCompact/SessionStart hooks will fire!

# GOOD: Standalone Python scripts
python3 run_swebench_test.py  # ✅ No Claude Code, no hooks
```

---

## Proposed Testing Architecture

### Directory Structure

```
benchmarks/
├── swebench_test_env/           # Isolated venv (DO NOT COMMIT)
│   └── ...
│
├── test_variants/               # Different memory system versions
│   ├── v6_baseline/
│   │   ├── hooks/              # V6 hooks (no contextual embeddings)
│   │   └── config.json         # V6 configuration
│   │
│   ├── v7_current/
│   │   ├── hooks/              # V7 hooks (contextual embeddings)
│   │   └── config.json         # V7 configuration
│   │
│   └── faiss_original/
│       └── memory_adapter.py   # Their FAISS implementation
│
├── test_memory_dbs/             # Isolated memory databases
│   ├── faiss/                  # FAISS baseline memories
│   ├── v6/                     # V6 variant memories
│   └── v7/                     # V7 variant memories
│
└── results/                     # Test results
    ├── faiss_baseline.json
    ├── v6_results.json
    └── v7_results.json
```

### Variant Configuration

Each variant specifies its own isolated paths:

```json
{
  "variant_name": "v7_contextual",
  "memory_db_path": "/home/rye/.claude/memory_db_swebench_v7",
  "hooks_path": "/atb-data/claude-code/benchmarks/test_variants/v7_current/hooks",
  "config": {
    "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
    "contextual_embeddings": true,
    "task_context_aware": true,
    "adaptive_k": true
  }
}
```

---

## Testing Workflow

### Step 1: Create Isolated Environment

```bash
cd /atb-data/claude-code/claude-code/claude-memory-system/benchmarks

# Create test venv (separate from production)
python3 -m venv swebench_test_env
source swebench_test_env/bin/activate

# Install dependencies (isolated from conda base)
pip install chromadb sentence-transformers langchain langgraph faiss-cpu

# Verify isolation
which python3  # Should be: /atb-data/.../swebench_test_env/bin/python3
```

### Step 2: Prepare Test Variants

```bash
# Copy hooks to test variants (NOT to ~/.claude/)
mkdir -p test_variants/{faiss,v6,v7}/hooks

# V6 variant (no contextual embeddings)
git checkout v6.0.0  # Or copy from git history
cp hooks/* test_variants/v6/hooks/

# V7 variant (current)
git checkout main
cp hooks/* test_variants/v7/hooks/

# FAISS original (from SWE-Bench-CL)
# Already have this in agents-never-forget/
```

### Step 3: Run Isolated Tests

```bash
# Activate test environment
source swebench_test_env/bin/activate

# Run tests WITHOUT installing hooks
python3 run_isolated_comparison.py \
  --variants faiss,v6,v7 \
  --tasks 10 \
  --output results/

# This script:
# 1. Imports hooks from test_variants/ (not ~/.claude/)
# 2. Uses isolated memory DBs (test_memory_dbs/)
# 3. Saves results to results/
# 4. NEVER touches production system
```

### Step 4: Analyze Results

```bash
# Compare variants
python3 analyze_results.py \
  --baseline results/faiss_baseline.json \
  --variants results/v6_results.json results/v7_results.json

# Diagnose failures
python3 diagnose_failures.py \
  --variant v7 \
  --show-top-failures 20
```

---

## Safe Variant Comparison Script

```python
#!/usr/bin/env python3
"""
Isolated SWE-Bench Testing Framework

CRITICAL: Does NOT touch production system!
- No hook installation
- Separate memory DBs
- Direct imports
"""

import sys
from pathlib import Path
from typing import Dict, List

class IsolatedVariantTester:
    """
    Tests memory system variants in complete isolation.

    GUARANTEES:
    - Never modifies ~/.claude/memory-hooks/
    - Never uses ~/.claude/memory_db/
    - Never affects production system
    """

    def __init__(self, variant_name: str, config_path: Path):
        self.variant_name = variant_name

        # Load variant config
        with open(config_path) as f:
            self.config = json.load(f)

        # Isolated paths
        self.memory_db_path = Path(self.config["memory_db_path"])
        self.hooks_path = Path(self.config["hooks_path"])

        # Verify we're NOT using production paths
        assert "swebench" in str(self.memory_db_path), \
            f"Memory DB must be isolated! Got: {self.memory_db_path}"

        assert self.hooks_path != Path.home() / ".claude" / "memory-hooks", \
            f"Cannot use production hooks! Got: {self.hooks_path}"

        # Add variant hooks to path (isolated)
        sys.path.insert(0, str(self.hooks_path))

        print(f"✅ Isolated variant: {variant_name}")
        print(f"   Memory DB: {self.memory_db_path}")
        print(f"   Hooks: {self.hooks_path}")

    def run_evaluation(self, tasks: List[Dict]) -> Dict:
        """Run evaluation with this variant."""
        # Import hooks from ISOLATED path (not production!)
        if self.config.get("use_v7"):
            from v7_memory_adapter import V7MemoryAdapter
            memory = V7MemoryAdapter(
                memory_db_path=str(self.memory_db_path),
                k_results=5
            )
        else:
            # Use FAISS or other variant
            from eval_procedure import SemanticMemory
            # ...

        # Run tests...
        results = {}
        for task in tasks:
            # Test task with this variant's memory system
            result = self.run_task(task, memory)
            results[task["id"]] = result

        return results

    def cleanup(self):
        """Clean up this variant's memory DB."""
        import shutil
        if self.memory_db_path.exists():
            shutil.rmtree(self.memory_db_path)
            print(f"🗑️  Cleaned up: {self.memory_db_path}")


def run_isolated_comparison(variant_names: List[str], num_tasks: int):
    """
    Run comparison across variants in complete isolation.

    SAFETY GUARANTEE: Never touches production system!
    """
    print("="*70)
    print("ISOLATED VARIANT COMPARISON")
    print("="*70)
    print()

    # Verify we're in test environment, not production
    assert "swebench_test_env" in sys.executable, \
        f"Must run in isolated venv! Got: {sys.executable}"

    print(f"✅ Running in isolated environment: {sys.executable}")
    print()

    results = {}

    for variant_name in variant_names:
        print(f"\n{'='*70}")
        print(f"Testing variant: {variant_name}")
        print(f"{'='*70}\n")

        config_path = Path(f"test_variants/{variant_name}/config.json")

        # Create isolated tester
        tester = IsolatedVariantTester(variant_name, config_path)

        # Run evaluation
        variant_results = tester.run_evaluation(load_tasks(num_tasks))

        # Save results
        results[variant_name] = variant_results

        # Cleanup variant's memory DB
        tester.cleanup()

    # Save comparison
    output_path = Path(f"results/comparison_{num_tasks}_tasks.json")
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Comparison complete: {output_path}")

    return results


if __name__ == "__main__":
    # Verify safety
    assert Path.home() / ".claude" / "memory_db" not in sys.path, \
        "Production memory DB should not be in path!"

    # Run isolated comparison
    run_isolated_comparison(
        variant_names=["faiss", "v6_baseline", "v7_current"],
        num_tasks=10
    )
```

---

## Safety Checklist

Before running ANY SWE-Bench tests, verify:

- [ ] Using isolated venv (`swebench_test_env/bin/python3`)
- [ ] Memory DBs use `memory_db_swebench_*` paths (NOT `memory_db`)
- [ ] Hooks imported from `test_variants/` (NOT `~/.claude/memory-hooks/`)
- [ ] No `install.sh` or `cp hooks/*` commands during tests
- [ ] Production `~/.claude/` directory untouched
- [ ] Test results saved to `benchmarks/results/` (not mixed with production)

---

## Rollback Plan

If production system gets contaminated:

```bash
# 1. Stop all Claude Code instances
pkill -f claude-code

# 2. Restore V7 hooks from git
cd /atb-data/claude-code/claude-code/claude-memory-system
git checkout main
./install.sh  # Reinstall clean V7

# 3. Backup contaminated memory DB
mv ~/.claude/memory_db ~/.claude/memory_db.backup.$(date +%Y%m%d_%H%M%S)

# 4. Restore clean memory DB (if you have backup)
# OR start fresh
rm -rf ~/.claude/memory_db
mkdir ~/.claude/memory_db

# 5. Verify installation
ls -la ~/.claude/memory-hooks/  # Should show V7 hooks
cat ~/.claude/memory-hooks/__version__.py  # Should be V7.0.0
```

---

## Summary

**DO:**
- ✅ Use isolated venv
- ✅ Use separate memory DB paths with `swebench` in name
- ✅ Import hooks directly from `test_variants/`
- ✅ Run as standalone Python scripts
- ✅ Save results to `benchmarks/results/`

**DON'T:**
- ❌ Install hooks to `~/.claude/memory-hooks/` during testing
- ❌ Use production memory DB (`~/.claude/memory_db/`)
- ❌ Run tests inside Claude Code with hooks active
- ❌ Mix test data with production data
- ❌ Overwrite working V7 system

**The golden rule**: If it touches `~/.claude/`, it's NOT isolated enough!
