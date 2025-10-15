#!/usr/bin/env python3
"""
Memory Query Tool
=================
Comprehensive search and analysis tool for the memory preservation system.

Usage:
    # Semantic search by topic
    python3 query_memories.py --topic "bugs errors fixes"

    # Keyword search
    python3 query_memories.py --keywords "TypeError" "crash" "failed"

    # Date range
    python3 query_memories.py --since "2025-10-12" --until "2025-10-13"

    # High importance only
    python3 query_memories.py --min-importance 15 --topic "architecture design"

    # Find files involved in errors
    python3 query_memories.py --files-involved --keywords "error" "bug"

    # Session-specific
    python3 query_memories.py --session current --topic "recent work"

    # JSON output for scripting
    python3 query_memories.py --topic "testing" --format json
"""

import argparse
import chromadb
from pathlib import Path
from datetime import datetime
import json
import os
import sys
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed", file=sys.stderr)
    print("Run: pip install sentence-transformers", file=sys.stderr)
    sys.exit(1)


MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"  # 768d, 8192 token context


class MemoryQuery:
    """Query interface for the memory database."""

    def __init__(self, db_path: str = None):
        db_path = db_path or str(MEMORY_DB_PATH)

        if not Path(db_path).exists():
            print(f"ERROR: Memory database not found at {db_path}", file=sys.stderr)
            sys.exit(1)

        self.client = chromadb.PersistentClient(path=db_path)

        try:
            self.collection = self.client.get_collection("conversation_memories")
        except Exception as e:
            print(f"ERROR: Memory collection not found: {e}", file=sys.stderr)
            sys.exit(1)

        self.embedding_model = None  # Lazy load

    def _get_embedding_model(self):
        """Lazy load embedding model."""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
        return self.embedding_model

    def get_current_session_id(self) -> str:
        """Get current session ID from environment."""
        return os.environ.get('CLAUDE_SESSION_ID', 'unknown')

    def semantic_search(
        self,
        query_text: str,
        session_id: Optional[str] = None,
        n_results: int = 20,
        min_similarity: float = 0.3,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Semantic search using vector embeddings."""
        model = self._get_embedding_model()
        query_embedding = model.encode(query_text).tolist()

        where_filter = {}
        if session_id:
            where_filter["session_id"] = session_id

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2,  # Get extra for filtering
            where=where_filter if where_filter else None
        )

        if not results or not results.get("metadatas") or not results["metadatas"][0]:
            return []

        memories = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]
            distance = results["distances"][0][i]
            similarity = 1 - distance
            importance = metadata.get("importance_score", 0.0)

            if similarity >= min_similarity and importance >= min_importance:
                memories.append({
                    "id": results["ids"][0][i],
                    "document": document,
                    "metadata": metadata,
                    "similarity": similarity,
                    "importance": importance,
                    "timestamp": metadata.get("timestamp", "")
                })

        memories.sort(key=lambda x: x["similarity"] * x["importance"], reverse=True)
        return memories[:n_results]

    def keyword_search(
        self,
        keywords: List[str],
        session_id: Optional[str] = None,
        min_importance: float = 0.0,
        match_all: bool = False
    ) -> List[Dict[str, Any]]:
        """Keyword search across all text fields."""
        where_filter = {}
        if session_id:
            where_filter["session_id"] = session_id

        results = self.collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas", "documents"]
        )

        if not results or not results.get("ids"):
            return []

        memories = []
        for i in range(len(results["ids"])):
            metadata = results["metadatas"][i]
            document = results["documents"][i]
            importance = metadata.get("importance_score", 0.0)

            if importance < min_importance:
                continue

            # Search in document, intent, action, outcome
            search_text = f"{document} {metadata.get('intent', '')} {metadata.get('action', '')} {metadata.get('outcome', '')}".lower()

            matched_keywords = [kw for kw in keywords if kw.lower() in search_text]

            if match_all:
                if len(matched_keywords) == len(keywords):
                    memories.append({
                        "id": results["ids"][i],
                        "document": document,
                        "metadata": metadata,
                        "keywords_matched": matched_keywords,
                        "importance": importance,
                        "timestamp": metadata.get("timestamp", "")
                    })
            else:
                if matched_keywords:
                    memories.append({
                        "id": results["ids"][i],
                        "document": document,
                        "metadata": metadata,
                        "keywords_matched": matched_keywords,
                        "importance": importance,
                        "timestamp": metadata.get("timestamp", "")
                    })

        memories.sort(key=lambda x: (len(x["keywords_matched"]), x["importance"]), reverse=True)
        return memories

    def date_range_search(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        session_id: Optional[str] = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search within date range."""
        where_filter = {}
        if session_id:
            where_filter["session_id"] = session_id

        results = self.collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas", "documents"]
        )

        if not results or not results.get("ids"):
            return []

        memories = []
        for i in range(len(results["ids"])):
            metadata = results["metadatas"][i]
            document = results["documents"][i]
            timestamp = metadata.get("timestamp", "")
            importance = metadata.get("importance_score", 0.0)

            if importance < min_importance:
                continue

            if not timestamp:
                continue

            try:
                memory_date = datetime.fromisoformat(timestamp)

                if since:
                    since_date = datetime.fromisoformat(since)
                    if memory_date < since_date:
                        continue

                if until:
                    until_date = datetime.fromisoformat(until)
                    if memory_date > until_date:
                        continue

                memories.append({
                    "id": results["ids"][i],
                    "document": document,
                    "metadata": metadata,
                    "importance": importance,
                    "timestamp": timestamp
                })
            except:
                continue

        memories.sort(key=lambda x: x["timestamp"], reverse=True)
        return memories

    def files_involved_search(
        self,
        query_text: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Find all files mentioned in matching memories."""
        if query_text:
            memories = self.semantic_search(query_text, session_id, n_results=50)
        elif keywords:
            memories = self.keyword_search(keywords, session_id)
        else:
            # Get all memories
            where_filter = {}
            if session_id:
                where_filter["session_id"] = session_id

            results = self.collection.get(
                where=where_filter if where_filter else None,
                include=["metadatas", "documents"]
            )

            memories = []
            for i in range(len(results["ids"])):
                memories.append({
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "timestamp": results["metadatas"][i].get("timestamp", "")
                })

        files_map = {}
        for mem in memories:
            metadata = mem["metadata"]
            artifacts_json = metadata.get("artifacts", "{}")

            try:
                artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json
                file_paths = artifacts.get("file_paths", [])

                for file_path in file_paths:
                    if file_path not in files_map:
                        files_map[file_path] = []

                    files_map[file_path].append({
                        "document": mem["document"][:150],
                        "importance": metadata.get("importance_score", 0.0),
                        "timestamp": mem["timestamp"]
                    })
            except:
                continue

        # Sort each file's memories by timestamp
        for file_path in files_map:
            files_map[file_path].sort(key=lambda x: x["timestamp"], reverse=True)

        return files_map

    def get_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get database statistics."""
        where_filter = {}
        if session_id:
            where_filter["session_id"] = session_id

        results = self.collection.get(
            where=where_filter if where_filter else None,
            include=["metadatas"]
        )

        if not results or not results.get("metadatas"):
            return {"total": 0}

        total = len(results["metadatas"])

        importance_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        has_code = 0
        has_files = 0
        has_errors = 0

        for metadata in results["metadatas"]:
            cat = metadata.get("importance_category", "low")
            importance_dist[cat] = importance_dist.get(cat, 0) + 1

            if metadata.get("has_code"):
                has_code += 1
            if metadata.get("has_files"):
                has_files += 1

            artifacts_json = metadata.get("artifacts", "{}")
            try:
                artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json
                if artifacts.get("error_messages"):
                    has_errors += 1
            except:
                pass

        return {
            "total": total,
            "importance_distribution": importance_dist,
            "has_code": has_code,
            "has_files": has_files,
            "has_errors": has_errors
        }


def format_memory_output(memories: List[Dict[str, Any]], format_type: str = "summary"):
    """Format memories for display."""
    if format_type == "json":
        print(json.dumps(memories, indent=2))
        return

    if not memories:
        print("No memories found matching criteria.")
        return

    print(f"\nFound {len(memories)} memories:")
    print("=" * 80)
    print()

    for i, mem in enumerate(memories, 1):
        metadata = mem["metadata"]
        timestamp = mem["timestamp"]
        importance = mem.get("importance", metadata.get("importance_score", 0.0))
        importance_cat = metadata.get("importance_category", "unknown")

        # Extract date and time
        if "T" in timestamp:
            date, time_part = timestamp.split("T")
            time = time_part.split(".")[0]
        else:
            date, time = "N/A", "N/A"

        indicator = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(importance_cat, "⚪")

        print(f"{indicator} Memory #{i} | {importance_cat.upper()}:{importance:.1f} | {date} {time}")

        if "similarity" in mem:
            print(f"   Similarity: {mem['similarity']:.1%}")

        if "keywords_matched" in mem:
            print(f"   Keywords: {', '.join(mem['keywords_matched'])}")

        document = mem["document"]
        if len(document) > 200 and format_type == "summary":
            print(f"   {document[:200]}...")
        else:
            print(f"   {document}")

        if format_type == "detailed":
            print(f"   Intent: {metadata.get('intent', 'N/A')[:150]}")
            print(f"   Action: {metadata.get('action', 'N/A')[:200]}")
            print(f"   Outcome: {metadata.get('outcome', 'N/A')}")

            # Show artifacts
            artifacts_json = metadata.get("artifacts", "{}")
            try:
                artifacts = json.loads(artifacts_json) if isinstance(artifacts_json, str) else artifacts_json
                if artifacts.get("file_paths"):
                    files = artifacts["file_paths"][:3]
                    print(f"   Files: {', '.join(files)}")
                if artifacts.get("error_messages"):
                    print(f"   Errors: {len(artifacts['error_messages'])} captured")
            except:
                pass

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Query the Claude Code memory preservation system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Semantic search
  %(prog)s --topic "bugs errors fixes"

  # Keyword search
  %(prog)s --keywords TypeError crash failed

  # Date range
  %(prog)s --since "2025-10-12" --until "2025-10-13"

  # High importance only
  %(prog)s --min-importance 15 --topic "architecture"

  # Find files involved
  %(prog)s --files-involved --keywords error bug

  # Session-specific
  %(prog)s --session current --topic "recent work"

  # Statistics
  %(prog)s --stats
        """
    )

    parser.add_argument("--topic", help="Semantic search by topic")
    parser.add_argument("--keywords", nargs="+", help="Keyword search")
    parser.add_argument("--match-all", action="store_true", help="Match all keywords (AND)")
    parser.add_argument("--since", help="Start date (YYYY-MM-DD or ISO 8601)")
    parser.add_argument("--until", help="End date (YYYY-MM-DD or ISO 8601)")
    parser.add_argument("--session", choices=["current", "all"], default="all", help="Session filter")
    parser.add_argument("--session-id", help="Specific session ID")
    parser.add_argument("--min-importance", type=float, default=0.0, help="Minimum importance score")
    parser.add_argument("--min-similarity", type=float, default=0.3, help="Minimum similarity (0-1)")
    parser.add_argument("--files-involved", action="store_true", help="Show files involved in matching memories")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--format", choices=["summary", "detailed", "json"], default="summary", help="Output format")
    parser.add_argument("--limit", type=int, default=20, help="Maximum results")

    args = parser.parse_args()

    # Initialize query interface
    query = MemoryQuery()

    # Determine session ID
    session_id = None
    if args.session == "current":
        session_id = query.get_current_session_id()
        if session_id == "unknown":
            print("WARNING: Could not determine current session ID", file=sys.stderr)
    elif args.session_id:
        session_id = args.session_id

    # Statistics mode
    if args.stats:
        stats = query.get_statistics(session_id)
        print(json.dumps(stats, indent=2))
        return

    # Files involved mode
    if args.files_involved:
        files_map = query.files_involved_search(
            query_text=args.topic,
            keywords=args.keywords,
            session_id=session_id
        )

        if not files_map:
            print("No files found in matching memories.")
            return

        print(f"\n📁 Files Involved in Matching Memories")
        print("=" * 80)
        print()

        for file_path, memories in sorted(files_map.items()):
            print(f"📄 {file_path}")
            print(f"   {len(memories)} memory event(s):")
            for mem in memories[:3]:
                ts = mem["timestamp"].split("T")[1][:8] if "T" in mem["timestamp"] else "N/A"
                print(f"   - [{ts}] {mem['document']}")
            if len(memories) > 3:
                print(f"   ... and {len(memories) - 3} more")
            print()

        return

    # Execute query
    memories = []

    if args.topic:
        memories = query.semantic_search(
            query_text=args.topic,
            session_id=session_id,
            n_results=args.limit,
            min_similarity=args.min_similarity,
            min_importance=args.min_importance
        )
    elif args.keywords:
        memories = query.keyword_search(
            keywords=args.keywords,
            session_id=session_id,
            min_importance=args.min_importance,
            match_all=args.match_all
        )[:args.limit]
    elif args.since or args.until:
        memories = query.date_range_search(
            since=args.since,
            until=args.until,
            session_id=session_id,
            min_importance=args.min_importance
        )[:args.limit]
    else:
        parser.print_help()
        return

    format_memory_output(memories, args.format)


if __name__ == "__main__":
    main()
