# Multi-Turn Coding Benchmarks for Memory System Evaluation

**Research Date:** 2025-10-15
**Purpose:** Identify publicly available multi-turn coding benchmarks to test the Claude Code memory preservation system

---

## Executive Summary

I identified **8 viable benchmarks** for testing memory systems, with 3 ready to start TODAY. The top recommendation is **SWE-Bench-CL** (Continual Learning variant) because it explicitly tests memory retention across chronological coding tasks and is publicly available with clear setup instructions.

**Quick Start Priority:**
1. **SWE-Bench-CL** - Best fit, public, memory-focused
2. **LongMemEval** - Actively maintained, well-documented
3. **DABstep** - Easiest setup (3 lines of code)

---

## TIER 1: START TODAY (Highest Priority)

### 1. SWE-Bench-CL (Continual Learning for Coding Agents) ⭐ TOP PICK

**Why it's perfect for memory systems:**
- Explicitly designed to test "accumulate experience, transfer knowledge across tasks, and resist catastrophic forgetting"
- Chronologically ordered GitHub issues simulating real repository evolution
- Built-in memory comparison (memory-enabled vs memory-disabled agents)
- Tests across multiple sessions with task dependencies

**Availability:** ✅ Fully Public
- GitHub: https://github.com/thomasjoshi/agents-never-forget
- Paper: https://arxiv.org/abs/2507.00014
- Published: June 2025

**Dataset Details:**
- 273 tasks across 8 repositories (Django, SymPy, Sphinx, Matplotlib, etc.)
- Chronologically organized with 24-59% inter-task dependencies
- Difficulty categories: easy (<15 min) to very hard (>4 hours)
- Built on SWE-Bench Verified (human-verified issues)

**Metrics Provided:**
- Average accuracy
- Forgetting rate (catastrophic forgetting detection)
- Forward/backward transfer
- Tool-use efficiency
- Composite scoring for stability-plasticity trade-offs

**Setup Complexity:** ⚡ Medium
- Requires: Python, FAISS (for semantic memory), API keys for LLM
- Documentation: Good (has README, requirements.txt)
- Active: Yes (created May 2025, 52 commits, 3 contributors)

**Quick Start:**
```bash
git clone https://github.com/thomasjoshi/agents-never-forget
cd agents-never-forget
pip install -r requirements.txt
# Configure .env with API keys
# Run evaluation scripts from eval_v3_swe-agent/
```

**Why START TODAY:**
- Public dataset, no access requests needed
- Explicitly tests memory across sessions (our exact use case!)
- Recent (2025), actively maintained
- Built on proven SWE-Bench foundation
- Includes baseline memory implementation (FAISS-backed semantic memory)

---

### 2. LongMemEval (Long-Term Interactive Memory Benchmark)

**Why it's great for memory systems:**
- Tests 5 core memory abilities: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention
- 500 questions embedded in scalable chat histories
- ICLR 2025 accepted (peer-reviewed, high quality)

**Availability:** ✅ Fully Public
- GitHub: https://github.com/xiaowu0162/LongMemEval
- HuggingFace: https://huggingface.co/datasets/princeton-nlp/LongMemEval
- Paper: https://arxiv.org/abs/2410.10813
- Published: October 2024, accepted ICLR 2025

**Dataset Details:**
- 500 curated questions across chat histories
- Tests multi-session reasoning (not just single-session)
- Average context: 115,000 tokens per conversation
- Unified framework: indexing → retrieval → reading

**Performance Baseline:**
- Commercial assistants show 30% accuracy drop across sustained interactions
- Tests memory degradation explicitly

**Setup Complexity:** ⚡ Easy-Medium
- Two install paths: minimal (eval only) or full (with experiments)
- Well-documented with extensive README
- GPU recommended but not required for basic eval
- Active maintenance (last update September 2025)

**Quick Start:**
```bash
git clone https://github.com/xiaowu0162/LongMemEval
cd LongMemEval
conda create -n longmemeval-lite python=3.9
pip install -r requirements-lite.txt
# Download dataset from HuggingFace (automated in repo)
python evaluate.py --your-memory-system
```

**Why START TODAY:**
- Actively maintained (updates in Sept 2025)
- Excellent documentation
- Public dataset on HuggingFace
- Specifically designed for memory system evaluation
- No complex dependencies for basic evaluation

---

### 3. DABstep (Data Agent Benchmark for Multi-step Reasoning)

**Why it's relevant:**
- 450+ real-world tasks requiring iterative multi-step problem-solving
- None solvable with single-shot code (forces multi-turn interaction)
- Tests code-based data processing with contextual reasoning

**Availability:** ✅ Fully Public
- HuggingFace: https://huggingface.co/datasets/adyen/dabstep
- Space: https://huggingface.co/spaces/adyen/DABstep
- Paper: https://arxiv.org/abs/2506.23719
- Colab: https://colab.research.google.com/drive/1pXi5ffBFNJQ5nn1111SnIfjfKCOlunxu

**Dataset Details:**
- 460 tasks (450 default, 10 dev split)
- Real-world tasks from Adyen's financial analytics platform
- Requires sequential multi-step problem-solving
- 3.11 GB dataset (730 MB Parquet)

**Performance Baseline:**
- Best reasoning agents: 14-16% accuracy (very challenging!)

**Setup Complexity:** ⚡⚡⚡ EASIEST
- 3 lines of code to download and start
- No special dependencies beyond HuggingFace datasets

**Quick Start:**
```python
from datasets import load_dataset
ds = load_dataset("adyen/DABstep", name="tasks", split="default")
for task in ds:
    print(task)
    # Your memory system solves task
```

**Why START TODAY:**
- Easiest setup (literally 3 lines)
- Public dataset, instant access
- Real-world tasks (not synthetic)
- Clear baseline for comparison

**Note:** Not explicitly "multi-session" but requires multi-turn reasoning within tasks. Less ideal for testing cross-session memory but excellent for testing multi-turn task continuity.

---

## TIER 2: EXCELLENT FIT (Requires Moderate Setup)

### 4. InterCode (Interactive Coding with Execution Feedback)

**Why it's good for memory:**
- 5 environments: Bash, SQL, Python, CTF, SWE
- Multi-turn by design (12-turn limit for CTF tasks)
- Execution feedback loop (agent gets results, must iterate)
- Reinforcement learning environment structure

**Availability:** ✅ Public
- GitHub: https://github.com/princeton-nlp/intercode
- Paper: https://arxiv.org/abs/2306.14898
- Published: NeurIPS 2023

**Dataset Details:**
- 5 environments with different task types
- Bash: 24+ test points
- CTF: 100 tasks (GPT-4 solves 40%)
- Python, SQL: hundreds of tasks from static benchmarks
- Multi-language, multi-domain

**Setup Complexity:** ⚡⚡ Medium
- Requires Docker (all environments run in containers)
- Python >= 3.8
- Available via PyPI or source installation

**Quick Start:**
```bash
pip install intercode-bench
# OR from source:
git clone https://github.com/princeton-nlp/intercode.git
cd intercode
conda env create -f environment.yml
conda activate intercode
./setup.sh
python run_demo.py sql  # Interactive demo
```

**Maintenance Status:** ⚠️ Unclear
- Last major update: October 2023
- 227 stars, 48 forks (community interest)
- No explicit maintenance statement
- May need to verify compatibility with latest tools

**Why TIER 2:**
- Public and well-designed
- Multi-turn by nature
- Docker dependency adds complexity
- Maintenance status unclear (2023 last update)

---

### 5. CodeAssistBench (CAB) - Multi-turn Chat-Based Code Assistance

**Why it's excellent:**
- First benchmark for multi-turn programming assistance
- 3,286 real-world questions across 231 repositories
- 7 programming languages
- Tests project-specific assistance (requires understanding codebase context)

**Availability:** ⚠️ Partial
- Paper: https://arxiv.org/abs/2507.10646
- Published: July 2025 (very recent!)
- **GitHub not yet public** (paper published, dataset may be coming)

**Dataset Details:**
- 3,286 questions from real GitHub issues
- 231 repositories across 7 languages
- Automatic containerization of codebases
- Two cohorts: all-time (700 repos) and recent (3,500 repos)

**Performance Baseline:**
- Models: 70-83% on Stack Overflow
- Models: 16.49% on CAB recent issues (much harder!)

**Setup Complexity:** ⚡⚡ Medium (when available)
- Requires containerization (Docker-based)
- Automatic dataset generation from GitHub issues
- Likely similar complexity to SWE-Bench

**Quick Start:** ⚠️ NOT YET AVAILABLE
- Wait for official GitHub release
- Paper is public, dataset/code may follow

**Why TIER 2:**
- Perfect fit for memory testing (multi-turn, project-specific)
- Very recent (July 2025)
- **Not yet publicly available** (paper only)
- Wait for official release or contact authors

---

### 6. τ-bench (Tau-Bench) - Tool-Agent-User Interaction

**Why it's interesting:**
- Emulates dynamic conversations between user and agent
- Agent has domain-specific API tools and policy guidelines
- Two domains: retail and airline (customer service scenarios)

**Availability:** ✅ Public
- GitHub: https://github.com/sierra-research/tau-bench
- Paper: https://arxiv.org/abs/2406.12045
- Published: 2024
- Also: τ²-bench (v2) at https://github.com/sierra-research/tau2-bench

**Dataset Details:**
- Retail and airline domains
- Multi-turn conversations (user simulator + agent)
- Tool usage evaluation
- Policy guideline adherence

**Performance Baseline:**
- GPT-4o: <50% success rate
- Pass@8: <25% in retail (inconsistent even with retries)

**Setup Complexity:** ⚡ Easy
```bash
pip install git+https://github.com/sierra-research/tau-bench
```

**Why TIER 2:**
- Interesting for tool use + memory
- Less focused on coding (more on customer service)
- Public and easy to install
- Better for conversational agents than coding agents

---

## TIER 3: PROMISING BUT COMPLEX/LIMITED

### 7. SWE-Bench Pro (Long-Horizon Software Engineering Tasks)

**Why it's challenging:**
- Explicitly tests long-horizon tasks (hours to days for humans)
- Enterprise-level complexity
- 1,865 problems across 41 repositories
- Average: 107.4 lines of code across 4.1 files

**Availability:** ✅ Public + 🔒 Commercial
- Public dataset: 11 repositories (open access)
- Held-out set: 12 repositories
- Commercial set: 18 proprietary repositories (partner access only)
- HuggingFace: https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro
- GitHub: https://github.com/scaleapi/SWE-bench_Pro-os
- Leaderboard: https://scale.com/leaderboard/swe_bench_pro_public

**Dataset Details:**
- 1,865 problems (only ~500 public)
- Business applications, B2B services, developer tools
- Much harder than SWE-Bench (top models: 23% vs 70%)

**Setup Complexity:** ⚡⚡⚡ Advanced
- Requires Docker (prebuilt images available)
- Requires Modal (distributed evaluation platform)
- Modal setup: API keys, cloud authentication
- Not trivial for quick testing

**Quick Start:**
```python
from datasets import load_dataset
swebench = load_dataset('ScaleAI/SWE-bench_Pro', split='test')
# Then: Docker + Modal setup for evaluation
```

**Performance Baseline:**
- GPT-5: 23.3%
- Claude Opus 4.1: 23.1%
- (Compare: 70%+ on SWE-Bench Verified)

**Why TIER 3:**
- Excellent quality, very challenging
- Complex setup (Docker + Modal + cloud)
- Partially public (many repos are held-out/commercial)
- Overkill for initial memory testing (start simpler)

---

### 8. StoryBench (Long-Term Memory with Multi-Turn)

**Why it's unique:**
- Interactive fiction games with branching storylines
- Tests long-term causal reasoning and memory retention
- Two modes: Immediate Feedback and Self Recovery

**Availability:** ⚠️ Paper Only
- Paper: https://arxiv.org/abs/2506.13356
- Published: June 2025
- **Dataset availability unclear** (paper recently published)

**Dataset Details:**
- Dynamically branching storylines
- Complex reasoning structures (hierarchical decision trees)
- Cascading dependencies across multi-turn interactions
- Tests backtracking and error correction

**Setup Complexity:** ❓ Unknown
- Paper published June 2025 (very recent)
- No GitHub repo found yet
- May require contacting authors

**Why TIER 3:**
- Very interesting for long-term memory testing
- Not coding-focused (interactive fiction)
- Dataset availability unclear
- Too new (may not be ready for use)

---

## OTHER BENCHMARKS (Not Prioritized)

### GAIA (General AI Assistants)
- 466 questions (450 public, 300 test)
- Multi-modal, web browsing, tool use
- ❌ **Not coding-focused** (general assistant tasks)
- Available: https://huggingface.co/spaces/gaia-benchmark/leaderboard

### AgentBench
- 8 environments (OS, Database, Web, etc.)
- Multi-turn, open-ended generation
- ❌ **Only 1 coding environment** (rest are general tasks)
- Available: https://github.com/THUDM/AgentBench

### MemoryCode (From "From Tools to Teammates")
- Synthetic multi-session dataset
- Tests instruction tracking across sessions
- ⚠️ **GitHub not found** (paper published Feb 2025)
- Paper: https://arxiv.org/abs/2502.13791

### MT-Bench (Multi-Turn Benchmark)
- Multi-turn conversation benchmark
- ❌ **Not coding-focused** (general conversation)

---

## Recommendations by Use Case

### For Testing Cross-Session Memory (Top Priority):
1. **SWE-Bench-CL** - Explicit continual learning, chronological tasks
2. **LongMemEval** - Multi-session reasoning, well-documented
3. **CodeAssistBench** - When available (project-specific multi-turn)

### For Testing Multi-Turn Reasoning (Single Session):
1. **DABstep** - Easiest setup, real-world tasks
2. **InterCode** - Interactive environments, execution feedback
3. **τ-bench** - Tool use + conversation

### For Maximum Challenge:
1. **SWE-Bench Pro** - Enterprise complexity, long-horizon
2. **StoryBench** - When available (complex branching, backtracking)

---

## Next Steps: Recommended Testing Plan

### Phase 1: Quick Validation (Week 1)
**Start with DABstep** - 3 lines of code, immediate results
- Test: Does our memory system improve multi-step task performance?
- Baseline: No memory vs V6 vs V7
- Metric: Task completion rate

### Phase 2: Memory-Specific Testing (Week 2-3)
**SWE-Bench-CL** - The gold standard for memory evaluation
- Test: Memory retention across chronological coding tasks
- Baseline: Memory-disabled vs memory-enabled (they provide framework!)
- Metrics: Forgetting rate, forward/backward transfer, accuracy

### Phase 3: Long-Term Memory (Week 4)
**LongMemEval** - Deep memory evaluation
- Test: Multi-session reasoning, temporal queries
- Baseline: Compare against commercial assistants (paper provides baselines)
- Metrics: Information extraction, knowledge updates, temporal reasoning

### Phase 4: Real-World Validation (Week 5+)
**InterCode** - Realistic coding environments
- Test: Bash, SQL, Python, CTF tasks with execution feedback
- Baseline: Static agents vs memory-enabled agents
- Metrics: Task success, turns to completion

---

## Key Metrics to Track Across All Benchmarks

### Task Performance:
- Success rate (% tasks completed correctly)
- Turns to completion (efficiency)
- Error rate / hallucination rate

### Memory-Specific:
- Recall accuracy (did agent remember relevant context?)
- Forgetting rate (did agent lose information across turns/sessions?)
- Transfer learning (did previous tasks help with new tasks?)

### Quality Metrics:
- Precision/Recall of retrieved memories
- Temporal accuracy (did agent remember when things happened?)
- Contextual relevance (were retrieved memories actually helpful?)

---

## Citations & Resources

**Primary Sources:**
- SWE-Bench-CL: Joshi et al. (2025) - https://arxiv.org/abs/2507.00014
- LongMemEval: Wu et al. (2024, ICLR 2025) - https://arxiv.org/abs/2410.10813
- DABstep: Adyen + HuggingFace (2025) - https://arxiv.org/abs/2506.23719
- InterCode: Yang et al. (2023, NeurIPS) - https://arxiv.org/abs/2306.14898
- CodeAssistBench: Kim et al. (2025) - https://arxiv.org/abs/2507.10646
- SWE-Bench Pro: Scale AI (2025) - https://arxiv.org/abs/2509.16941

**Benchmark Aggregators:**
- 10 AI Agent Benchmarks: https://www.evidentlyai.com/blog/ai-agent-benchmarks
- Papers with Code (Agent Benchmarks): https://paperswithcode.com/task/agent-benchmarks

---

**Last Updated:** 2025-10-15
**Researcher:** Claude Code Memory System Team
**Purpose:** Identify multi-turn coding benchmarks for V7 memory system evaluation
