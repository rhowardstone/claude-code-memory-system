"""
Claude Code Memory System - Version Information
================================================
Central version tracking for all components.
"""

__version__ = "7.0.0"
__version_info__ = (7, 0, 0)

# Component versions (for reference)
PRECOMPACT_VERSION = "5.0"  # V5: Contextual embeddings
SESSIONSTART_VERSION = "5.0"  # V5: Task-context aware with knowledge graph
QUERY_TOOL_VERSION = "1.0"
KNOWLEDGE_GRAPH_VERSION = "1.0"
EVALUATION_VERSION = "1.0"  # V7: New evaluation framework

# Release notes
RELEASE_NOTES = """
V7.0.0 - Contextual Embeddings + Evaluation
- Added contextual embeddings (session, time, file context)
- Embeddings now include metadata: session_id, timestamp, file_paths
- Better temporal and contextual retrieval ("yesterday's work", "auth.py changes")
- Built evaluation framework (Precision, Recall, F1, MRR)
- Test set for measuring retrieval quality
- Baseline metrics for future improvements
- All V6 features maintained

V6.0.0 - Clean Architecture Release
- Removed version suffixes from filenames
- Centralized version tracking in __version__.py
- Proper semantic versioning
- Knowledge graph with entity extraction
- Task-context aware importance scoring
- Adaptive K retrieval (0-20 memories)
- nomic-embed-text-v1.5 (768-dim, 8k context)
"""

def get_version():
    """Return version string."""
    return __version__

def get_version_info():
    """Return version tuple."""
    return __version_info__
