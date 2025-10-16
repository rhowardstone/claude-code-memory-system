# Public Multi-Turn Coding Benchmarks - Quick Start Guide

**Purpose:** Guide to using established public benchmarks for evaluating the Claude Code V7 memory system

**Companion to:** `README.md` (internal custom benchmark) and `MULTI_TURN_CODING_BENCHMARKS.md` (detailed research)

---

## Quick Decision Guide

**Choose your benchmark based on your goal:**

### "I want to test memory TODAY" (5 minutes)
→ **DABstep** - Just download and run
```bash
python quick_start_dabstep.py
```

### "I want to test cross-session memory" (30 minutes) ⭐
→ **SWE-Bench-CL** - Explicitly designed for memory testing
```bash
./quick_start_swe_bench_cl.sh
```

### "I want comprehensive memory evaluation" (20 minutes)
→ **LongMemEval** - Tests 5 memory abilities
```bash
git clone https://github.com/xiaowu0162/LongMemEval
cd LongMemEval
conda create -n longmemeval python=3.9
pip install -r requirements-lite.txt
```

---

## Top 3 Public Benchmarks

### 1️⃣ SWE-Bench-CL (RECOMMENDED) ⭐

**Best for:** Testing cross-session memory retention

**What it tests:**
- Continual learning across chronological coding tasks
- Forgetting rate (catastrophic forgetting detection)
- Forward/backward transfer learning
- Memory-enabled vs memory-disabled comparison

**Dataset:**
- 273 tasks across 8 Python repositories
- Chronologically ordered (simulates real development)
- 24-59% inter-task dependencies
- Based on verified SWE-Bench issues

**Quick Start:**
```bash
./quick_start_swe_bench_cl.sh
# Then edit .env with API keys and run evaluation
```

**Resources:**
- GitHub: https://github.com/thomasjoshi/agents-never-forget
- Paper: https://arxiv.org/abs/2507.00014
- Published: June 2025

**Why it's perfect:**
- ✅ Explicitly tests memory across sessions
- ✅ Includes memory-enabled/disabled comparison framework
- ✅ Public dataset with clear setup
- ✅ Matches our use case exactly

---

### 2️⃣ LongMemEval

**Best for:** Comprehensive memory ability testing

**What it tests:**
- Information extraction from conversations
- Multi-session reasoning
- Temporal reasoning (when did X happen?)
- Knowledge updates (new info supersedes old)
- Abstention (knowing when not to answer)

**Dataset:**
- 500 curated questions
- Embedded in scalable chat histories
- Average 115,000 tokens per conversation
- ICLR 2025 accepted (peer-reviewed)

**Quick Start:**
```bash
git clone https://github.com/xiaowu0162/LongMemEval
cd LongMemEval
conda create -n longmemeval-lite python=3.9
pip install -r requirements-lite.txt
python evaluate.py --your-memory-system
```

**Resources:**
- GitHub: https://github.com/xiaowu0162/LongMemEval
- HuggingFace: https://huggingface.co/datasets/princeton-nlp/LongMemEval
- Paper: https://arxiv.org/abs/2410.10813

**Why it's excellent:**
- ✅ Tests 5 distinct memory abilities
- ✅ Actively maintained (Sept 2025 update)
- ✅ Well-documented with examples
- ✅ Public dataset, easy download

---

### 3️⃣ DABstep (Easiest!)

**Best for:** Quick validation, immediate results

**What it tests:**
- Multi-step reasoning (requires iterative problem-solving)
- Code-based data processing
- Contextual reasoning over documentation
- Real-world data analysis tasks

**Dataset:**
- 450+ tasks from Adyen's financial analytics
- None solvable with single-shot code
- Very challenging (best agents: 14-16% accuracy)
- 3.11 GB dataset

**Quick Start:**
```python
python quick_start_dabstep.py
# Or manually:
from datasets import load_dataset
ds = load_dataset("adyen/DABstep", name="tasks", split="default")
for task in ds:
    print(task)  # Your memory system solves the task
```

**Resources:**
- HuggingFace: https://huggingface.co/datasets/adyen/dabstep
- Space: https://huggingface.co/spaces/adyen/DABstep
- Paper: https://arxiv.org/abs/2506.23719
- Colab: https://colab.research.google.com/drive/1pXi5ffBFNJQ5nn1111SnIfjfKCOlunxu

**Why it's easiest:**
- ✅ 3 lines of code to start
- ✅ No complex setup, no Docker
- ✅ Public dataset, instant download
- ✅ Real-world tasks (not synthetic)

---

## Full Benchmark List (8 Total)

See `BENCHMARK_COMPARISON.md` for detailed comparison matrix.

**Tier 1 (Start Today):**
1. SWE-Bench-CL - Cross-session memory (30 min setup)
2. LongMemEval - Comprehensive memory (20 min setup)
3. DABstep - Quick validation (5 min setup)

**Tier 2 (Excellent Fit):**
4. InterCode - Interactive coding (45 min setup, requires Docker)
5. CodeAssistBench - Multi-turn chat (dataset pending)
6. τ-bench - Tool + conversation (10 min setup)

**Tier 3 (Advanced):**
7. SWE-Bench Pro - Enterprise complexity (2+ hrs setup)
8. StoryBench - Long-term planning (dataset pending)

---

## Comparison: Public vs Internal Benchmark

### Internal Benchmark (README.md)
**What we have:**
- Custom scenarios (auth system, bug investigation)
- 2-3 sessions per scenario
- Fast (2.7s average)
- Controlled ground truth
- Tests our specific use cases

**Results:**
- ✅ 55.6% session carryover
- ✅ 55.8% memory consistency
- ✅ 54.6% F1 score
- 🟡 Struggles with topic divergence

### Public Benchmarks
**What they offer:**
- Industry-standard metrics
- Peer-reviewed methodology
- Comparison against other systems
- Broader task coverage
- External validation

**Value:**
- ✅ Validate V7 approach against literature
- ✅ Compare to commercial systems
- ✅ Publish results for credibility
- ✅ Identify gaps in our approach

---

## Recommended Testing Strategy

### Phase 1: Internal Validation (DONE ✅)
**Current status:** Custom benchmark shows V7 improvements
- Session carryover: 55.6%
- Memory consistency: 55.8%
- Challenges identified: semantic similarity across topics

### Phase 2: Quick Public Validation (Week 1)
**Benchmark:** DABstep
**Goal:** Does memory help with multi-step tasks?
**Compare:** No memory vs V6 vs V7
**Metric:** Task completion rate

### Phase 3: Memory-Specific Testing (Week 2-3)
**Benchmark:** SWE-Bench-CL
**Goal:** Measure forgetting rate, transfer learning
**Compare:** Memory-disabled vs memory-enabled (use their framework)
**Metrics:** Accuracy, forgetting, forward/backward transfer

### Phase 4: Comprehensive Eval (Week 4)
**Benchmark:** LongMemEval
**Goal:** Test all 5 memory abilities
**Compare:** Against commercial assistants (paper has baselines)
**Metrics:** Information extraction, temporal reasoning, updates

### Phase 5: Real-World Coding (Week 5+)
**Benchmark:** InterCode
**Goal:** Interactive environments with execution feedback
**Compare:** Static agent vs memory-enabled
**Environments:** Bash, SQL, Python, CTF

---

## Key Metrics to Track

### From Public Benchmarks
- **Task Success Rate** - % tasks completed correctly
- **Forgetting Rate** - % information lost across sessions
- **Transfer Learning** - Did previous tasks help?
- **Mean Reciprocal Rank (MRR)** - Position of first relevant result
- **NDCG** - Rank-order quality

### From Internal Benchmark
- **Session Carryover** - % memories retrieved from previous sessions
- **Memory Consistency** - % queries with relevant memories
- **Precision/Recall/F1** - Retrieval quality
- **Time to Completion** - Speed

### Combined Analysis
Compare internal vs public results to:
- Validate that our custom benchmark predicts public performance
- Identify gaps in our testing
- Tune parameters for real-world use

---

## Files in This Directory

**Public Benchmark Research:**
- `PUBLIC_BENCHMARKS.md` - This file (quick start guide)
- `MULTI_TURN_CODING_BENCHMARKS.md` - Detailed research report (8,000 words)
- `BENCHMARK_COMPARISON.md` - Comparison matrix and decision tree
- `quick_start_swe_bench_cl.sh` - Automated SWE-Bench-CL setup
- `quick_start_dabstep.py` - Interactive DABstep exploration

**Internal Benchmark (Existing):**
- `README.md` - Custom long-horizon benchmark documentation
- `long_horizon_benchmark.py` - Custom benchmark implementation
- `benchmark_results.json` - Results from custom tests
- `EXISTING_BENCHMARK_PLAN.md` - Internal benchmark design
- `LITERATURE_COMPARISON.md` - Academic comparison

---

## Next Steps

1. **Choose your starting benchmark:**
   - Memory-focused: SWE-Bench-CL
   - Quick test: DABstep
   - Comprehensive: LongMemEval

2. **Run the quick start script:**
   ```bash
   ./quick_start_swe_bench_cl.sh  # Or
   python quick_start_dabstep.py
   ```

3. **Adapt to V7 memory system:**
   - Integrate benchmark harness with your hooks
   - Compare: no memory, V6, V7
   - Track both benchmark metrics and custom metrics

4. **Document results:**
   - Update CLAUDE.md with findings
   - Compare public vs internal results
   - Identify improvement opportunities

5. **Consider publishing:**
   - V7 validates Anthropic's contextual embedding approach
   - Local-first alternative to API-based RAG
   - Unique contribution: knowledge graphs for coding

---

## Citations

**Industry Research:**
- Anthropic (Sept 2024). "Introducing Contextual Retrieval" - V7 validates this
- OpenAI (2024). "Evals Framework" - Long-horizon task testing
- NVIDIA (2024). "Evaluating Retriever for Enterprise RAG" - Metrics guide

**Public Benchmarks:**
- SWE-Bench-CL: Joshi et al. (2025) - https://arxiv.org/abs/2507.00014
- LongMemEval: Wu et al. (2024, ICLR 2025) - https://arxiv.org/abs/2410.10813
- DABstep: Adyen + HuggingFace (2025) - https://arxiv.org/abs/2506.23719

**Full bibliography:** See `MULTI_TURN_CODING_BENCHMARKS.md`

---

**Last Updated:** 2025-10-15
**Version:** 1.0
**Researcher:** Claude Code Memory System Team
