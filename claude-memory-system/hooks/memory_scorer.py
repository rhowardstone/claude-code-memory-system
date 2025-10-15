#!/usr/bin/env python3
"""
Memory Importance Scorer
========================
Scores memory chunks by importance based on various signals:
- Tool usage frequency
- File modification patterns
- Error/success indicators
- User explicit markers (decisions, learnings)
- Recency decay
"""

import re
from typing import Dict, Any, List
from datetime import datetime, timedelta


class MemoryScorer:
    """Scores memory importance for prioritization."""

    # Importance weights for different signals
    WEIGHTS = {
        "decision_marker": 10.0,      # "decided to", "chose", "will use"
        "error_resolution": 8.0,       # Fixed bugs, solved problems
        "file_creation": 6.0,          # New files created
        "file_modification": 4.0,      # Files modified
        "test_success": 5.0,           # Tests passing
        "learning": 7.0,               # "learned", "discovered", "realized"
        "tool_use_frequency": 3.0,     # Multiple tool uses
        "user_directive": 9.0,         # Direct user instructions
        "code_snippet": 4.0,           # Contains code
        "diagram_reference": 5.0,      # References to architecture/design
    }

    # Recency decay factor (importance reduces over time)
    RECENCY_DECAY_DAYS = 30  # Half-life of 30 days

    @staticmethod
    def score_chunk(chunk: Dict[str, str], metadata: Dict[str, Any] = None) -> float:
        """Calculate importance score for a memory chunk."""
        score = 0.0
        metadata = metadata or {}

        intent = chunk.get("intent", "").lower()
        action = chunk.get("action", "").lower()
        outcome = chunk.get("outcome", "").lower()
        combined = f"{intent} {action} {outcome}"

        # 1. Decision markers
        decision_patterns = [
            r'\b(decided|chose|selected|picked|opted)\s+to\b',
            r'\bgoing\s+to\s+use\b',
            r'\bwill\s+use\b',
            r'\bdecision:\b',
        ]
        for pattern in decision_patterns:
            if re.search(pattern, combined):
                score += MemoryScorer.WEIGHTS["decision_marker"]
                break

        # 2. Error resolution indicators
        error_patterns = [
            r'\b(fixed|resolved|solved|debugged)\b',
            r'\berror.*resolved\b',
            r'\bbug.*fixed\b',
            r'\bissue.*solved\b',
        ]
        for pattern in error_patterns:
            if re.search(pattern, combined):
                score += MemoryScorer.WEIGHTS["error_resolution"]
                break

        # 3. File operations
        if re.search(r'\bcreated?\s+\w+\.(ts|js|py|go|rs|java|cpp|c|h)\b', action):
            score += MemoryScorer.WEIGHTS["file_creation"]

        if re.search(r'\bmodified?\s+\w+\.(ts|js|py|go|rs|java|cpp|c|h)\b', action):
            score += MemoryScorer.WEIGHTS["file_modification"]

        # 4. Test success
        if re.search(r'\btests?\s+(pass(ed|ing)?|succeed(ed)?)\b', outcome):
            score += MemoryScorer.WEIGHTS["test_success"]

        # 5. Learning indicators
        learning_patterns = [
            r'\b(learned|discovered|realized|found\s+that)\b',
            r'\bkey\s+insight\b',
            r'\bimportant:\b',
        ]
        for pattern in learning_patterns:
            if re.search(pattern, combined):
                score += MemoryScorer.WEIGHTS["learning"]
                break

        # 6. Tool use frequency
        tool_count = metadata.get("tool_count", 0)
        if tool_count > 0:
            score += min(tool_count * MemoryScorer.WEIGHTS["tool_use_frequency"], 15.0)

        # 7. User directive (from intent)
        if re.search(r'^(please|can\s+you|i\s+want|i\s+need|help\s+me)', intent):
            score += MemoryScorer.WEIGHTS["user_directive"]

        # 8. Code snippet
        if re.search(r'```|`\w+`|\bcode\b', combined):
            score += MemoryScorer.WEIGHTS["code_snippet"]

        # 9. Diagram/architecture reference
        if re.search(r'\b(architecture|diagram|design|flow|structure)\b', combined):
            score += MemoryScorer.WEIGHTS["diagram_reference"]

        # 10. Apply recency decay
        timestamp = metadata.get("timestamp")
        if timestamp:
            try:
                chunk_time = datetime.fromisoformat(timestamp)
                days_old = (datetime.now() - chunk_time).days
                decay_factor = 0.5 ** (days_old / MemoryScorer.RECENCY_DECAY_DAYS)
                score *= decay_factor
            except Exception:
                pass

        return score

    @staticmethod
    def categorize_importance(score: float) -> str:
        """Categorize importance into tiers."""
        if score >= 20.0:
            return "critical"
        elif score >= 10.0:
            return "high"
        elif score >= 5.0:
            return "medium"
        else:
            return "low"


def score_chunks(chunks: List[Dict[str, str]], metadatas: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Score a list of chunks and add importance metadata."""
    metadatas = metadatas or [{}] * len(chunks)
    scored = []

    for chunk, metadata in zip(chunks, metadatas):
        score = MemoryScorer.score_chunk(chunk, metadata)
        category = MemoryScorer.categorize_importance(score)

        scored_chunk = {
            "chunk": chunk,
            "metadata": {
                **metadata,
                "importance_score": score,
                "importance_category": category
            }
        }
        scored.append(scored_chunk)

    return scored


if __name__ == "__main__":
    # Test scoring
    test_chunks = [
        {
            "intent": "User wants to fix authentication bug",
            "action": "Modified auth.ts, debugged token validation",
            "outcome": "Bug fixed, tests passing, decided to use JWT refresh tokens"
        },
        {
            "intent": "Refactor variable names",
            "action": "Renamed variables in utils.ts",
            "outcome": "Code cleaner"
        },
        {
            "intent": "Create new API endpoint",
            "action": "Created api/users.ts, added tests",
            "outcome": "Endpoint working, learned about async error handling"
        }
    ]

    test_metadata = [
        {"tool_count": 5, "timestamp": datetime.now().isoformat()},
        {"tool_count": 1, "timestamp": (datetime.now() - timedelta(days=60)).isoformat()},
        {"tool_count": 3, "timestamp": datetime.now().isoformat()},
    ]

    scored = score_chunks(test_chunks, test_metadata)

    print("Memory Importance Scoring Test:")
    print("=" * 60)
    for i, item in enumerate(scored, 1):
        chunk = item["chunk"]
        meta = item["metadata"]
        print(f"\nChunk {i}:")
        print(f"  Intent: {chunk['intent']}")
        print(f"  Score: {meta['importance_score']:.2f}")
        print(f"  Category: {meta['importance_category']}")
