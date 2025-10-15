# Long-Horizon Task Benchmarks for V7

## Overview

This directory contains benchmarks inspired by industry standards:
- **OpenAI Evals Framework**: Long-horizon task completion
- **LongEval**: Context retention over 40-600 turns
- **Anthropic Contextual Retrieval**: Retrieval failure rate reduction

## Initial Benchmark Results (V7)

### Scenarios Tested

1. **Auth System Implementation** (3 sessions)
   - Session 1: Implement basic JWT auth
   - Session 2 (after compaction): Add OAuth
   - Session 3 (after compaction): Add rate limiting

2. **Bug Investigation** (3 sessions)
   - Session 1: Investigate timeout issue
   - Session 2 (after compaction): Identify root cause
   - Session 3 (after compaction): Implement fix

### Results

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Session Carryover | 70-80% | 33.3% | ❌ Needs Improvement |
| Memory Consistency | 60-70% | 38.3% | ❌ Needs Improvement |
| F1 Score | 50-60% | 63.7% | ✅ Good |
| Time to Completion | <120s | 6-8s | ✅ Excellent |

### Key Findings

#### ✅ What Works Well

1. **Fast Retrieval**: 0.7-4.6s per session (under budget)
2. **High F1 Score**: 63.7% average (above target)
3. **First Session**: 100% carryover in initial session
4. **Storage Pipeline**: Successfully stores memories with contextual embeddings

#### ❌ Issues Identified

1. **Cross-Session Retrieval**:
   - Problem: Sessions 2 and 3 show 0% carryover
   - Root Cause: Query filters by exact `session_id`, blocking cross-session retrieval
   - Impact: Defeats the purpose of memory system across compaction

2. **Precision Calculation**:
   - Problem: Precision > 100% (impossible)
   - Root Cause: Counting keyword matches in concatenated text, not per-memory relevance
   - Impact: Inflated precision metrics

3. **Session ID Model**:
   - Problem: Benchmark uses same session_id for all 3 sessions
   - Reality: Each compaction creates new session_id
   - Impact: Doesn't match production behavior

### Comparison to Industry Benchmarks

**Anthropic Contextual Retrieval (Sept 2024)**:
- Their reduction: 35% fewer retrieval failures with contextual embeddings
- Our V7: Uses same principle (session/time/file context in embeddings)
- Our metrics: Need cross-session test to properly measure

**OpenAI Evals Long-Horizon**:
- Their focus: Task completion across 40+ turns
- Our test: 3 sessions with realistic coding tasks
- Gap: Need longer scenarios (5-10 sessions)

## Next Steps

### Immediate Fixes

1. **Fix Cross-Session Queries**:
   ```python
   # Current (broken):
   results = collection.query(where={"session_id": session_id})

   # Fixed (retrieves from all sessions):
   results = collection.query(n_results=20)  # No session_id filter
   ```

2. **Simulate Real Session IDs**:
   - Session 1: `bench_auth_s1`
   - Session 2: `bench_auth_s2` (different ID after compaction)
   - Session 3: `bench_auth_s3` (different ID after compaction)

3. **Fix Metrics Calculation**:
   - Calculate precision per-memory, not per-text
   - Use proper relevance judgments

### Performance Improvements

1. **Add Baseline Comparison**:
   - Measure: V7 with memories vs no-memory baseline
   - Metrics: Task completion rate, time, accuracy

2. **Extend Scenarios**:
   - Add 5-session scenario (test longer-term memory)
   - Add 10-session scenario (stress test)
   - Add failure scenarios (incorrect memories, outdated info)

3. **Add BEIR-Style Metrics**:
   - NDCG (Normalized Discounted Cumulative Gain)
   - MRR (Mean Reciprocal Rank)
   - MAP (Mean Average Precision)

### Research Validation

Test against published baselines:
- **MTEB**: Compare nomic-embed-text-v1.5 performance
- **LongEval**: 40+ turn consistency test
- **Anthropic**: Measure retrieval failure rate reduction

## Running Benchmarks

```bash
# Run full benchmark suite
cd benchmarks
python3 long_horizon_benchmark.py

# Run with custom database path
python3 long_horizon_benchmark.py --db-path /path/to/test/db

# Run specific scenario
python3 long_horizon_benchmark.py --scenario auth_system
```

## Benchmark Design Principles

1. **Realistic Tasks**: Based on actual coding workflows
2. **Multi-Session**: Test memory across compaction boundaries
3. **Measurable**: Quantitative metrics (precision, recall, F1)
4. **Reproducible**: Fixed scenarios, seed for randomness
5. **Fast**: Complete in <5 minutes for rapid iteration

## Future Benchmarks

### Planned Scenarios

1. **Refactoring Project** (5 sessions)
   - Test: Architecture memory, file relationship tracking

2. **API Design and Implementation** (7 sessions)
   - Test: Decision memory, design pattern consistency

3. **Test Suite Creation** (4 sessions)
   - Test: Coverage gap memory, test strategy consistency

4. **Performance Optimization** (6 sessions)
   - Test: Measurement memory, optimization approach tracking

### Research Integration

- [ ] Implement BEIR-style evaluation
- [ ] Add MTEB benchmark comparison
- [ ] Create LongEval-inspired 40-turn test
- [ ] Measure against Anthropic's 35% improvement baseline

## References

- [OpenAI Evals](https://github.com/openai/evals)
- [BEIR Benchmark](https://github.com/beir-cellar/beir)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [LongEval Paper](https://arxiv.org/abs/2311.04711)
