# SWE-Bench-CL: Paper Analysis & Benchmark Readiness

## Paper Credibility Assessment

### Publication Details
- **ArXiv ID**: 2507.00014
- **Title**: "SWE-Bench-CL: Continual Learning for Coding Agents"
- **Authors**: Thomas Joshi, Shayan Chowdhury, Fatih Uysal
- **Affiliation**: Columbia University (inferred from project metadata)
- **Submission Date**: June 13, 2025
- **Status**: ArXiv preprint (not peer-reviewed)
- **License**: CC-BY-4.0 (Creative Commons Attribution)

### Citation Count
**Estimated: 0-1 citations**

**Why so few?**
- Paper is only ~4 months old (submitted June 2025)
- ArXiv preprints typically take 6-12 months to accumulate citations
- Not yet accepted to a peer-reviewed venue (likely submitted to NeurIPS/ICML)

### Credibility Factors

**✅ POSITIVE:**
1. **Built on SWE-Bench Verified** - OpenAI/Princeton's human-verified dataset (highly credible)
2. **Full code + data release** - All 273 tasks, evaluation framework, and baseline results publicly available
3. **Production-quality implementation** - 2804-line evaluation framework with complete LangGraph agent
4. **Uses standard tools** - FAISS, nomic-embed-text, LangChain (reproducible)
5. **Clear methodology** - Chronological ordering, curriculum learning, dependency tracking
6. **Standardized metrics** - Success rate, forgetting rate, forward/backward transfer

**⚠️ CONCERNS:**
1. **Not peer-reviewed yet** - No external validation of methods/claims
2. **Very new authors** - No established track record in continual learning or LLM research (based on web search)
3. **Zero citations** - No community validation yet
4. **Limited baselines** - Only compares memory-enabled vs memory-disabled (no comparison with other memory systems)

### Overall Assessment

**Credibility Score: 6.5/10**

- **Strengths**: Builds on established work (SWE-Bench), full reproducibility, clear metrics
- **Weaknesses**: No peer review, unknown authors, no community validation

**Recommendation:** **Use with caution, but valuable for our purposes**

This is a NEW benchmark (June 2025), so low citations are expected. The fact that they:
- Built on SWE-Bench Verified (credible foundation)
- Released full code/data under open license
- Provide complete evaluation framework

...makes it suitable for testing our V7 system, even though it's not yet peer-reviewed.

---

## Why This Benchmark Is Perfect for Us

1. **Explicitly tests memory** - The ENTIRE point is measuring memory retention
2. **Real coding tasks** - 273 actual GitHub issues, not synthetic
3. **Has baseline** - Their FAISS memory vs no-memory comparison
4. **Standardized metrics** - Forgetting rate, transfer learning, success rate
5. **Complete framework** - Can run their method vs ours apples-to-apples

**Most importantly**: They use **nomic-embed-text** (same as us!), so embedding model is controlled variable.

---

## Their Evaluation Framework Analysis

### Framework Structure

**Location**: `agents-never-forget/eval_v3_swe-agent/eval_procedure.py`

**Size**: 2,804 lines of production-ready Python

**Key Components:**
```python
Line 1004:  class SemanticMemory (FAISS-based)
  - add_entry()        # Store task experience
  - retrieve_relevant() # Query with similarity search

Line 1098:  class MemorySystem (Context builder)
  - add_experience_to_memory()  # After each task
  - get_relevant_context_for_prompt()  # Before each task

Line 2344:  class SWEAgentCLEvaluator (Main benchmark runner)
  - run_evaluation()   # Run full 273-task benchmark
  - Supports per-sequence evaluation
  - Tracks all CL metrics

Line 1175:  embedding_model = "ollama/nomic-embed-text"  # SAME AS OURS!
```

**Agent Tools** (SWE-agent inspired):
- `open`, `scroll_up`, `scroll_down`, `goto` - File navigation
- `find_file`, `search_file`, `search_dir` - Code search
- `edit` - Code editing with linter integration
- `run_tests` - Execute test suites

**Evaluation Pipeline:**
1. Load dataset (273 tasks across 8 repos)
2. For each task in chronological order:
   a. Set up repository at `base_commit`
   b. Retrieve relevant memories (if enabled)
   c. Run agent with memory context
   d. Let agent explore code, make edits
   e. Apply `test_patch` and run tests
   f. Check if tests pass (success metric)
   g. Store experience in memory
3. Calculate CL metrics (success rate, forgetting, transfer)

---

## How to Run: THEIR Method vs OURS

### Prerequisites

1. **API Keys** (in `agents-never-forget/.env`):
   ```bash
   ANTHROPIC_API_KEY=your_key_here
   # OR
   OPENAI_API_KEY=your_key_here
   ```

2. **Ollama** (for embeddings):
   ```bash
   # Install ollama
   curl -fsSL https://ollama.com/install.sh | sh

   # Pull embedding model
   ollama pull nomic-embed-text
   ```

3. **Python Dependencies** (already installed in their venv):
   - LangChain, LangGraph
   - FAISS
   - sentence-transformers
   - chromadb (for our V7 system)

### Option 1: Automated Comparison (Recommended)

```bash
cd /atb-data/claude-code/claude-code/claude-memory-system/benchmarks

# Create modified scripts for V7 integration
python3 run_full_swebench_comparison.py --setup-only

# This creates:
# - agents-never-forget/eval_v3_swe-agent/eval_procedure_v7.py  (V7 version)
# - agents-never-forget/eval_v3_swe-agent/run_comparison.py     (Runner script)

# Run comparison (requires API keys!)
cd agents-never-forget/eval_v3_swe-agent
python3 run_comparison.py

# Or run specific sequence only
python3 run_comparison.py --sequence "django/django" --pilot 10
```

### Option 2: Manual Integration

**Step 1: Modify their eval_procedure.py**

Find line ~1199:
```python
# ORIGINAL (FAISS):
if active_embedding_model:
    semantic_memory_instance = SemanticMemory(embedding_model=active_embedding_model)
    memory_system = MemorySystem(semantic_memory_instance)
```

Replace with:
```python
# V7 INTEGRATION:
import sys
from pathlib import Path as PathV7
sys.path.insert(0, str(PathV7(__file__).parent.parent.parent))
from v7_memory_adapter import V7MemoryAdapter, V7MemorySystem

# Initialize V7 memory
v7_adapter = V7MemoryAdapter(
    memory_db_path=str(PathV7.home() / ".claude" / "memory_db_swebench"),
    k_results=5
)
memory_system = V7MemorySystem(v7_adapter)
```

**Step 2: Disable dummy mode**

Find line 233:
```python
USE_DUMMY_DATA = True  # CHANGE TO False
```

**Step 3: Run evaluation**

```python
# In eval_procedure.py (as Jupyter cells or script):
evaluator = SWEAgentCLEvaluator(swe_bench_cl, agent_workflow, memory_system)

# Run on first sequence (django)
results = evaluator.run_evaluation(
    model_id="claude-3-5-sonnet",  # or your model
    sequence_ids=["django/django"],
    memory_enabled=True
)

# Save results
import json
with open("results_v7.json", "w") as f:
    json.dump(results, f, indent=2)
```

---

## Expected Runtime

**Pilot (10 tasks per sequence):**
- Time per task: ~2-5 minutes (depends on LLM speed)
- Total tasks: 10 tasks × 8 sequences = 80 tasks
- **Estimated time: 3-7 hours**

**Full Benchmark (273 tasks):**
- 273 tasks × 3 minutes average = **~14 hours**
- With our 190 CPUs, could parallelize to **~2-3 hours** if we implement parallel execution

---

## Comparison Metrics

### Primary Metrics (from their paper)

1. **Success Rate**: % of tasks where agent's solution passes all tests
2. **Forgetting Rate**: How much performance drops on previously solved tasks
3. **Forward Transfer**: Does learning on early tasks help with later tasks?
4. **Backward Transfer**: Does learning new tasks improve old task performance?
5. **Tool Use Efficiency**: successful_tool_calls / total_tool_calls

### Expected V7 Improvements

Based on Anthropic's contextual retrieval findings (35% reduction in failures):

| Metric | FAISS Baseline | V7 Expected | Improvement |
|--------|---------------|-------------|-------------|
| Success Rate | ~20-30% | ~25-40% | +10-15% |
| Forgetting Rate | ~0.3-0.5 | ~0.2-0.3 | -33% |
| Memory Efficiency | Fixed top-5 | Adaptive 0-20 | Variable |
| Context Quality | Similarity-only | Task-context aware | +30-50% |

**Key V7 Advantages:**
- **Contextual embeddings**: Better temporal/file-based queries
- **Knowledge graph**: Captures FILE/FUNCTION relationships
- **Adaptive K**: Reduces low-quality memory spam
- **Task-context scoring**: Boosts relevant entities

---

## Current Status

**✅ READY TO RUN:**
1. V7MemoryAdapter implemented and tested
2. Integration script created (`run_full_swebench_comparison.py`)
3. SWE-Bench-CL dataset downloaded (273 tasks)
4. Their evaluation framework analyzed and understood
5. Comparison methodology defined

**⏳ PENDING:**
1. Set up API keys in `.env`
2. Verify Ollama is running with nomic-embed-text
3. Execute pilot comparison (10 tasks)
4. Analyze results
5. Scale to full benchmark (273 tasks)

---

## Recommendation

**YES, this benchmark is worth running for the following reasons:**

1. ✅ **Novel**: Only benchmark explicitly testing memory for coding agents
2. ✅ **Complete**: Full evaluation framework + 273 real tasks
3. ✅ **Reproducible**: Open source, clear methodology
4. ✅ **Relevant**: Tests exactly what our V7 system is designed for
5. ✅ **Fair comparison**: Same embedding model, controlled variables

**But acknowledge limitations:**
- ⚠️ Not peer-reviewed (yet)
- ⚠️ Zero citations (too new)
- ⚠️ Authors unknown in community

**Overall verdict: Run it, but report results as "evaluation on unpublished SWE-Bench-CL benchmark" rather than "published benchmark".**

The fact that it's built on SWE-Bench Verified (credible) and provides full reproducibility makes it valuable for our purposes, even if the paper itself isn't validated yet.
