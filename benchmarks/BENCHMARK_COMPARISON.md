# Multi-Turn Coding Benchmark Comparison Matrix

**Quick Reference Guide** - Choose the right benchmark for your testing needs

---

## At-A-Glance Comparison

| Benchmark | Memory Focus | Setup Time | Public? | Tasks | Best For |
|-----------|--------------|------------|---------|-------|----------|
| **SWE-Bench-CL** ⭐ | ✅✅✅ Explicit | 30 min | ✅ Yes | 273 | Cross-session memory |
| **LongMemEval** | ✅✅✅ Explicit | 20 min | ✅ Yes | 500 | Multi-session reasoning |
| **DABstep** | ✅✅ Implicit | 5 min | ✅ Yes | 450+ | Quick validation |
| **InterCode** | ✅✅ Implicit | 45 min | ✅ Yes | 100+ | Interactive coding |
| **CodeAssistBench** | ✅✅ Implicit | TBD | ⚠️ Soon | 3,286 | Project-specific tasks |
| **SWE-Bench Pro** | ✅ Implicit | 2+ hrs | ⚠️ Partial | 1,865 | Enterprise complexity |
| **τ-bench** | ✅ Implicit | 10 min | ✅ Yes | ~100 | Tool use + conversation |
| **StoryBench** | ✅✅✅ Explicit | TBD | ⚠️ Soon | TBD | Backtracking/planning |

**Legend:**
- ✅✅✅ = Explicitly designed to test memory
- ✅✅ = Multi-turn requires memory
- ✅ = Memory helpful but not core
- ⭐ = Top recommendation

---

## Detailed Comparison

### 1. Memory Testing Focus

**Explicitly Tests Memory Retention:**
1. **SWE-Bench-CL** - Continual learning, forgetting rate, transfer learning
2. **LongMemEval** - 5 memory abilities (extraction, reasoning, updates, etc.)
3. **StoryBench** - Long-term causal reasoning, backtracking

**Implicitly Requires Memory (Multi-Turn):**
4. **DABstep** - Multi-step reasoning (memory helps but not tracked)
5. **InterCode** - Execution feedback loops (agent must remember context)
6. **CodeAssistBench** - Project-specific Q&A (codebase context needed)

**Memory Nice-to-Have:**
7. **SWE-Bench Pro** - Long-horizon tasks (memory helps with complexity)
8. **τ-bench** - Multi-turn conversation (memory helps with consistency)

---

### 2. Setup Complexity

**EASIEST (Start in <10 minutes):**
```python
# DABstep - 3 lines of code!
from datasets import load_dataset
ds = load_dataset("adyen/DABstep", name="tasks", split="default")
for task in ds: print(task)
```

**EASY (Start in 10-30 minutes):**
- **LongMemEval** - Clone repo, pip install, download from HuggingFace
- **τ-bench** - Single pip install command

**MEDIUM (Start in 30-60 minutes):**
- **SWE-Bench-CL** - Clone, setup venv, configure API keys, install FAISS
- **InterCode** - Docker setup, conda environment, run demo script

**HARD (Start in 1-3+ hours):**
- **SWE-Bench Pro** - Docker + Modal + cloud credentials + config
- **CodeAssistBench** - Containerization (when available)

**TBD (Not yet available):**
- **StoryBench** - Paper published, dataset release pending

---

### 3. Dataset Size & Availability

| Benchmark | Tasks | Public Dataset | Download Method | Size |
|-----------|-------|----------------|-----------------|------|
| SWE-Bench-CL | 273 | ✅ Full | GitHub clone | ~500 MB |
| LongMemEval | 500 | ✅ Full | HuggingFace | ~100 MB |
| DABstep | 450+ | ✅ Full | HuggingFace | 3.11 GB |
| InterCode | 100+ | ✅ Full | GitHub clone | ~200 MB |
| CodeAssistBench | 3,286 | ⚠️ Pending | TBD | TBD |
| SWE-Bench Pro | 1,865 | ⚠️ ~500 public | HuggingFace | ~2 GB |
| τ-bench | ~100 | ✅ Full | pip install | <100 MB |
| StoryBench | TBD | ⚠️ Pending | TBD | TBD |

---

### 4. Task Characteristics

**Coding-Focused Benchmarks:**
- **SWE-Bench-CL** - Real GitHub issues, chronological order, Python repos
- **SWE-Bench Pro** - Enterprise bugs, multi-file patches, very hard
- **CodeAssistBench** - Project-specific Q&A, 7 languages, real codebases
- **InterCode** - Interactive environments (Bash, SQL, Python, CTF)
- **DABstep** - Data analysis tasks (data wrangling, ML, EDA)

**Conversational/Tool Use:**
- **LongMemEval** - Multi-session chat, memory-centric questions
- **τ-bench** - Customer service scenarios, API tools, policy adherence
- **StoryBench** - Interactive fiction, branching decisions, backtracking

---

### 5. Metrics Provided

**Comprehensive Memory Metrics:**
- **SWE-Bench-CL**: Accuracy, forgetting rate, forward/backward transfer, tool efficiency
- **LongMemEval**: Information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention

**Task Performance Metrics:**
- **DABstep**: Accuracy (% correct answers), leaderboard ranking
- **InterCode**: Success rate, turns to completion
- **SWE-Bench Pro**: Resolve rate (% issues fixed)
- **CodeAssistBench**: Resolution rate, language-specific performance

**Conversation Metrics:**
- **τ-bench**: Task success, policy adherence, tool usage

---

### 6. Baseline Performance (Difficulty)

**Very Hard (Best models <20%):**
- DABstep: 14-16% (best agents)
- SWE-Bench Pro: 23% (GPT-5, Claude Opus 4.1)

**Hard (Best models 20-50%):**
- τ-bench: <50% (GPT-4o)
- InterCode CTF: 40% (GPT-4)

**Medium (Best models 50-80%):**
- SWE-Bench-CL: TBD (new benchmark)
- LongMemEval: 70% (30% drop from baseline)

**Easier (Best models >80%):**
- CodeAssistBench Stack Overflow: 70-83% (but CAB issues: 16%)

---

### 7. Use Case Recommendations

#### "I want to test cross-session memory TODAY"
→ **SWE-Bench-CL** (30 min setup, explicit memory testing)

#### "I want the quickest validation of my memory system"
→ **DABstep** (5 min setup, 450 tasks ready to go)

#### "I want comprehensive memory evaluation"
→ **LongMemEval** (20 min setup, 5 memory abilities tested)

#### "I want realistic coding environments"
→ **InterCode** (45 min setup, 5 environments with execution feedback)

#### "I want maximum challenge and complexity"
→ **SWE-Bench Pro** (2+ hrs setup, enterprise-level bugs)

#### "I want to test tool use + conversation + memory"
→ **τ-bench** (10 min setup, customer service scenarios)

#### "I want to wait for the perfect multi-turn coding benchmark"
→ **CodeAssistBench** (watch for release, 3,286 project-specific tasks)

---

## Recommended Testing Sequence

### Week 1: Quick Validation
**Benchmark:** DABstep
**Why:** Easiest setup, immediate results
**Test:** Does memory improve multi-step task success?
**Baseline:** No memory vs V6 vs V7

### Week 2-3: Memory-Specific Testing
**Benchmark:** SWE-Bench-CL
**Why:** Explicitly tests memory retention
**Test:** Forgetting rate, transfer learning
**Baseline:** Memory-disabled vs memory-enabled (framework provided)

### Week 4: Deep Memory Evaluation
**Benchmark:** LongMemEval
**Why:** Comprehensive memory ability testing
**Test:** Multi-session reasoning, temporal queries
**Baseline:** Compare against commercial assistants

### Week 5+: Real-World Validation
**Benchmark:** InterCode
**Why:** Realistic coding environments with feedback
**Test:** Bash, SQL, Python, CTF tasks
**Baseline:** Static agent vs memory-enabled

---

## Command Cheat Sheet

### DABstep (Easiest)
```python
python quick_start_dabstep.py
# Or manually:
from datasets import load_dataset
ds = load_dataset("adyen/DABstep", name="tasks", split="default")
```

### SWE-Bench-CL (Best for Memory)
```bash
./quick_start_swe_bench_cl.sh
# Or manually:
git clone https://github.com/thomasjoshi/agents-never-forget
cd agents-never-forget
pip install -r requirements.txt
# Edit .env with API keys
```

### LongMemEval (Comprehensive)
```bash
git clone https://github.com/xiaowu0162/LongMemEval
cd LongMemEval
conda create -n longmemeval-lite python=3.9
pip install -r requirements-lite.txt
# Download dataset from HuggingFace (automatic in repo)
python evaluate.py
```

### InterCode (Interactive)
```bash
pip install intercode-bench
# Or from source:
git clone https://github.com/princeton-nlp/intercode
cd intercode
conda env create -f environment.yml
conda activate intercode
./setup.sh
python run_demo.py sql
```

### τ-bench (Tool Use)
```bash
pip install git+https://github.com/sierra-research/tau-bench
```

### SWE-Bench Pro (Hard Mode)
```python
from datasets import load_dataset
swebench = load_dataset('ScaleAI/SWE-bench_Pro', split='test')
# Then: Docker + Modal setup for evaluation (see repo docs)
```

---

## Decision Tree

```
START HERE
    |
    ├─ Need quick validation (today)?
    |   └─> DABstep (5 min setup)
    |
    ├─ Testing cross-session memory?
    |   └─> SWE-Bench-CL (30 min setup) ⭐
    |
    ├─ Want comprehensive memory eval?
    |   └─> LongMemEval (20 min setup)
    |
    ├─ Need interactive code environments?
    |   └─> InterCode (45 min setup)
    |
    ├─ Want maximum challenge?
    |   └─> SWE-Bench Pro (2+ hrs setup)
    |
    └─ Testing tool use + conversation?
        └─> τ-bench (10 min setup)
```

---

## Key Resources

**Top 3 Recommendations:**
1. **SWE-Bench-CL**: https://github.com/thomasjoshi/agents-never-forget
2. **LongMemEval**: https://github.com/xiaowu0162/LongMemEval
3. **DABstep**: https://huggingface.co/datasets/adyen/dabstep

**Full List:**
- InterCode: https://github.com/princeton-nlp/intercode
- SWE-Bench Pro: https://github.com/scaleapi/SWE-bench_Pro-os
- τ-bench: https://github.com/sierra-research/tau-bench
- CodeAssistBench: https://arxiv.org/abs/2507.10646 (paper only, dataset pending)
- StoryBench: https://arxiv.org/abs/2506.13356 (paper only, dataset pending)

**Aggregators:**
- 10 AI Agent Benchmarks: https://www.evidentlyai.com/blog/ai-agent-benchmarks
- Papers with Code: https://paperswithcode.com/task/agent-benchmarks

---

**Last Updated:** 2025-10-15
**Version:** 1.0
