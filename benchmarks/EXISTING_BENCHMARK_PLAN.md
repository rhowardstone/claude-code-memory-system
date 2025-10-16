# Running Our Memory System Through Existing Benchmarks

**Goal**: Test our memory system on standardized benchmarks to measure real performance on long-horizon tasks.

---

## 🎯 Best Candidate Benchmarks

### 1. **LongMemEval** (PERFECT FIT!)

**Why it's perfect**:
- ✅ Specifically tests **long-term memory** across chat sessions
- ✅ 500 high-quality questions designed for memory evaluation
- ✅ Tests our exact use case: multi-session memory retention
- ✅ Freely downloadable from HuggingFace
- ✅ MIT licensed

**What it tests**:
1. **Information Extraction** - retrieve specific facts from history
2. **Multi-Session Reasoning** - connect info across conversations
3. **Knowledge Updates** - handle contradictory/evolving information
4. **Temporal Reasoning** - understand time-based relationships
5. **Abstention** - recognize when answers can't be determined

**Dataset variants**:
- `LongMemEval_S` - ~115k tokens
- `LongMemEval_M` - ~500 sessions (most realistic)
- Oracle version - only evidence sessions

**How to run**:
```bash
# 1. Install
pip install datasets

# 2. Download from HuggingFace
from datasets import load_dataset
dataset = load_dataset("xiaowu0162/LongMemEval", "LongMemEval_M")

# 3. Feed timestamped chat histories to Claude Code + our memory system
# 4. Collect outputs in JSONL (question_id + hypothesis)
# 5. Run evaluation script with GPT-4o as judge
```

**Metrics**:
- QA correctness (LLM-judged)
- Session-level memory recall accuracy
- Turn-level memory recall accuracy
- Retrieval performance

**GitHub**: https://github.com/xiaowu0162/LongMemEval
**Paper**: ICLR 2025

---

### 2. **SWE-bench** (GREAT FOR CODING)

**Why it's relevant**:
- ✅ Real-world GitHub issues (2,294 problems)
- ✅ Tests multi-step problem solving
- ✅ Requires maintaining context across investigation/implementation
- ✅ Publicly available on HuggingFace

**What it tests**:
- Given a codebase + issue, generate a patch that resolves the problem
- Requires understanding codebase, identifying root cause, implementing fix
- Very similar to our "Bug Investigation" scenario but at scale

**Dataset variants**:
- `SWE-bench` - Full 2,294 problems
- `SWE-bench Lite` - 300 curated instances
- `SWE-bench Verified` - 500 engineer-confirmed solvable problems

**How to run**:
```bash
# 1. Install Docker (required)
# 2. Clone repo
git clone git@github.com:princeton-nlp/SWE-bench.git
cd SWE-bench
pip install -e .

# 3. Run with our agent
python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path <our_agent_predictions> \
    --max_workers 4
```

**Requirements**:
- 120GB storage, 16GB RAM, 8 CPU cores
- Docker for reproducible evaluations

**Metrics**:
- % of issues successfully resolved
- Comparison to SOTA (Claude Sonnet 3.5: 49% on Verified)

**GitHub**: https://github.com/SWE-bench/SWE-bench
**Leaderboard**: https://www.swebench.com/

---

### 3. **LongBench** (ALTERNATIVE)

**Why it's relevant**:
- Tests long-context understanding (bilingual, multitask)
- Multiple task types: QA, summarization, code completion
- Freely available on HuggingFace

**Less ideal because**:
- More about "single long context" than "memory across sessions"
- Doesn't directly test our compaction survival use case

**GitHub**: https://github.com/THUDM/LongBench

---

## 📋 Implementation Plan

### Phase 1: LongMemEval (Most Aligned)

**Week 1: Setup & Baseline**
1. Download LongMemEval_M dataset
2. Create adapter to feed chat histories to Claude Code
3. Run **baseline** (Claude Code WITHOUT memory system)
4. Record: QA correctness, session recall, turn recall

**Week 2: Memory System Testing**
1. Run with **our memory system enabled**
2. Record same metrics
3. Compare: Memory vs No-Memory

**Week 3: Analysis**
1. Calculate improvement percentages
2. Error analysis: where does memory help most?
3. Identify failure modes

**Expected Results**:
- Baseline (no memory): ~30-40% accuracy (wild guess)
- With memory: Target 50-60% accuracy (+20-30% improvement)
- Best on: Multi-session reasoning, temporal reasoning
- Worst on: Knowledge updates (contradictory info)

---

### Phase 2: SWE-bench Lite (Coding Tasks)

**Week 4: Setup**
1. Install SWE-bench + Docker
2. Create agent wrapper for Claude Code
3. Test on 10 sample issues

**Week 5-6: Evaluation**
1. Run on SWE-bench Lite (300 instances)
2. Compare with/without memory
3. Measure % resolved

**Expected Results**:
- Baseline: ~15-20% (Claude Code solo)
- With memory: Target 25-30% (+10% improvement)
- SOTA: 49% (Claude Sonnet 3.5)

---

## 🔬 Experimental Design

### A/B Test Structure

**Condition A: No Memory**
- Disable PreCompact/SessionStart hooks
- Run Claude Code normally
- Record performance

**Condition B: With Memory (V7)**
- Enable full memory system
- Contextual embeddings + knowledge graph + task-context scoring
- Record performance

**Metrics to Measure**:
1. **Task Success Rate** - % of tasks completed correctly
2. **Efficiency** - Tokens used, time taken
3. **Error Types** - Where does each system fail?
4. **Memory Utility** - How often are retrieved memories actually used?

---

## 📊 Success Criteria

### Minimum Viable Success

**LongMemEval**:
- ✅ Memory system shows **+10% improvement** over baseline
- ✅ Statistical significance (p < 0.05)
- ✅ Strongest improvement on multi-session reasoning

**SWE-bench Lite**:
- ✅ Memory system shows **+5% improvement** over baseline
- ✅ Helps on issues requiring investigation across files
- ✅ Doesn't harm performance (no negative transfer)

### Aspirational Success

**LongMemEval**:
- 🌟 **+20-30% improvement** over baseline
- 🌟 Competitive with purpose-built memory systems
- 🌟 Published results on benchmark leaderboard

**SWE-bench Lite**:
- 🌟 **+10-15% improvement**
- 🌟 Approach SOTA performance (40%+)
- 🌟 First memory-augmented system on leaderboard

---

## 🚧 Challenges & Solutions

### Challenge 1: Dataset Format Mismatch

**Problem**: LongMemEval uses chat format, Claude Code uses tool calls.

**Solution**:
- Create adapter layer to convert LongMemEval chats → Claude Code sessions
- Simulate compaction at natural breakpoints (session boundaries)
- Inject memories via SessionStart hook

### Challenge 2: Evaluation Time

**Problem**: SWE-bench Lite has 300 instances, could take days.

**Solution**:
- Start with 10-sample pilot
- Use `max_workers` parallelization
- Focus on SWE-bench Verified (500 instances, higher quality)

### Challenge 3: API Costs

**Problem**: Running 500+ tasks could cost $$$.

**Solution**:
- Use Claude Code (no API costs, already have access)
- Start with smaller subsets
- Only run full benchmark once we have promising pilot results

### Challenge 4: Docker/Infrastructure

**Problem**: SWE-bench requires Docker, 120GB storage.

**Solution**:
- Test locally first
- Consider cloud VM if needed
- Start with SWE-bench Lite (smaller footprint)

---

## 🎯 Next Steps (Immediate)

### This Week:

1. **Download LongMemEval** (30 min)
   ```bash
   pip install datasets
   python -c "from datasets import load_dataset; load_dataset('xiaowu0162/LongMemEval', 'LongMemEval_M')"
   ```

2. **Create Adapter Script** (2-3 hours)
   - Read LongMemEval format
   - Convert to Claude Code session format
   - Simulate compaction at session boundaries

3. **Run Pilot Test** (1-2 hours)
   - Test on 10 questions
   - Validate adapter works
   - Measure baseline performance

4. **Decision Point**:
   - If pilot shows promise → proceed with full benchmark
   - If adapter too complex → try simpler benchmark first
   - If baseline terrible → investigate why

---

## 📚 References

**LongMemEval**:
- GitHub: https://github.com/xiaowu0162/LongMemEval
- Paper: https://arxiv.org/abs/2410.10813
- Dataset: https://huggingface.co/datasets/xiaowu0162/LongMemEval

**SWE-bench**:
- GitHub: https://github.com/SWE-bench/SWE-bench
- Leaderboard: https://www.swebench.com/
- Dataset: https://huggingface.co/datasets/princeton-nlp/SWE-bench

**Comparison**:
| Benchmark | Best For | Difficulty | Time to Run | Our Match |
|-----------|----------|------------|-------------|-----------|
| LongMemEval | Memory testing | Medium | 1-2 days | ⭐⭐⭐⭐⭐ Perfect |
| SWE-bench Lite | Coding tasks | High | 3-5 days | ⭐⭐⭐⭐ Great |
| LongBench | General long-context | Medium | 1-2 days | ⭐⭐⭐ Good |

**Recommendation**: Start with **LongMemEval** (perfect alignment with our use case).
