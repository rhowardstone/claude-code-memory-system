#!/usr/bin/env python3
"""
Memory CLI - Interactive Memory Management Tool
================================================
Browse, search, and manage your conversation memories.

Commands:
  list [session_id]           - List all memories
  search <query> [session_id] - Search memories
  clusters [session_id]       - View hierarchical clusters
  prune [session_id]          - Prune old/low-importance memories
  stats [session_id]          - Show memory statistics
  export [session_id]         - Export memories to JSON
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from memory_pruner import MemoryPruner
    from memory_clustering import MemoryClustering
except ImportError as e:
    print(f"ERROR: {e}")
    print("Run: pip install -r ~/.claude/memory-hooks/requirements.txt")
    sys.exit(1)

MEMORY_DB_PATH = Path.home() / ".claude" / "memory_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class MemoryCLI:
    """CLI for memory management."""

    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=str(MEMORY_DB_PATH))
            self.collection = self.client.get_collection("conversation_memories")
        except Exception as e:
            print(f"❌ Error: No memory database found ({e})")
            print("   Memories will be created after the first compaction.")
            sys.exit(1)

    def list_memories(self, session_id: Optional[str] = None):
        """List all memories."""
        where = {"session_id": session_id} if session_id else None

        results = self.collection.get(
            where=where,
            limit=1000,
            include=["metadatas", "documents"]
        )

        if not results or not results.get("ids"):
            print("No memories found")
            return

        print(f"\n📚 Total Memories: {len(results['ids'])}")
        print("=" * 80)

        # Group by session
        by_session = {}
        for i, metadata in enumerate(results["metadatas"]):
            sid = metadata.get("session_id", "unknown")
            if sid not in by_session:
                by_session[sid] = []
            by_session[sid].append({
                "id": results["ids"][i],
                "doc": results["documents"][i],
                "meta": metadata
            })

        for sid, memories in by_session.items():
            print(f"\n🔹 Session: {sid}")
            print(f"   Memories: {len(memories)}")

            for mem in memories[:5]:  # Show first 5
                meta = mem["meta"]
                importance = meta.get("importance_category", "low")
                score = meta.get("importance_score", 0.0)
                indicator = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(importance, "⚪")

                print(f"\n   {indicator} {mem['doc'][:70]}... [{importance.upper()}: {score:.1f}]")
                print(f"      Intent: {meta.get('intent', 'N/A')[:60]}...")
                print(f"      Action: {meta.get('action', 'N/A')[:60]}...")

                # Artifacts
                if meta.get("has_code"):
                    print(f"      💻 Has code snippets")
                if meta.get("has_files"):
                    artifacts = json.loads(meta.get("artifacts", "{}"))
                    files = artifacts.get("file_paths", [])[:2]
                    if files:
                        print(f"      📁 Files: {', '.join(files)}")

            if len(memories) > 5:
                print(f"\n   ... and {len(memories) - 5} more")

    def search_memories(self, query: str, session_id: Optional[str] = None, top_k: int = 10):
        """Search memories semantically."""
        model = SentenceTransformer(EMBEDDING_MODEL)
        query_embedding = model.encode(query).tolist()

        where = {"session_id": session_id} if session_id else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["metadatas", "documents", "distances"]
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            print("No results found")
            return

        print(f"\n🔍 Search Results for: '{query}'")
        print("=" * 80)

        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            doc = results["documents"][0][i]
            distance = results["distances"][0][i] if "distances" in results else 0
            similarity = 1 - distance

            importance = meta.get("importance_category", "low")
            score = meta.get("importance_score", 0.0)
            indicator = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(importance, "⚪")

            print(f"\n{i + 1}. {indicator} {doc} [Similarity: {similarity:.2f}]")
            print(f"   Importance: {importance.upper()} ({score:.1f})")
            print(f"   Intent: {meta.get('intent', 'N/A')}")
            print(f"   Action: {meta.get('action', 'N/A')}")
            print(f"   Outcome: {meta.get('outcome', 'N/A')}")

            # Artifacts
            artifacts_shown = []
            if meta.get("has_code"):
                artifacts_shown.append("💻 Code")
            if meta.get("has_files"):
                artifacts = json.loads(meta.get("artifacts", "{}"))
                files = artifacts.get("file_paths", [])[:2]
                if files:
                    artifacts_shown.append(f"📁 {', '.join(files)}")
            if meta.get("has_architecture"):
                artifacts_shown.append("🏗️ Architecture")

            if artifacts_shown:
                print(f"   Artifacts: {' | '.join(artifacts_shown)}")

    def show_clusters(self, session_id: str):
        """Display hierarchical clusters."""
        clusterer = MemoryClustering(str(MEMORY_DB_PATH))
        result = clusterer.cluster_memories(session_id)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return

        print(f"\n🗂️  Memory Clusters for Session: {session_id}")
        print("=" * 80)
        print(f"Total memories: {result['total_memories']}")
        print(f"Number of clusters: {result['num_clusters']}")
        print()

        for cluster_id, data in sorted(result["clusters"].items(), key=lambda x: x[1]["size"], reverse=True):
            print(f"📦 Cluster {cluster_id} ({data['size']} memories)")
            print(f"   Summary: {data['summary']}")
            print(f"   Top memories:")
            for mem in data["memories"][:3]:
                meta = mem["metadata"]
                importance = meta.get("importance_category", "low")
                indicator = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(importance, "⚪")
                print(f"      {indicator} {mem['document'][:65]}...")
            print()

        # Show hierarchy
        if result.get("hierarchy"):
            print("🌳 Hierarchy:")
            print(f"   Root clusters: {result['hierarchy'].get('root', [])}")
            if result['hierarchy'].get('children'):
                for parent, children in result['hierarchy']['children'].items():
                    print(f"   Cluster {parent} → {children}")

    def prune_memories(self, session_id: Optional[str] = None, dry_run: bool = True):
        """Prune old/low-importance memories."""
        pruner = MemoryPruner(str(MEMORY_DB_PATH))

        if session_id:
            result = pruner.prune_session_memories(session_id, dry_run=dry_run)
        else:
            result = pruner.prune_all_sessions(dry_run=dry_run)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return

        print(f"\n🗑️  Memory Pruning {'(DRY RUN)' if dry_run else ''}")
        print("=" * 80)

        if session_id:
            print(f"Session: {session_id}")
            print(f"Total memories: {result['total_memories']}")
            print(f"Would prune: {result['pruned']}")
            print(f"Would keep: {result['kept']}")

            if dry_run and result.get("reasons"):
                print("\nPruning reasons:")
                for mem_id, reason in list(result["reasons"].items())[:10]:
                    print(f"   • {mem_id}: {reason}")
                if len(result["reasons"]) > 10:
                    print(f"   ... and {len(result['reasons']) - 10} more")
        else:
            print(f"Sessions processed: {result['sessions_processed']}")
            print(f"Total would prune: {result['total_pruned']}")

        if dry_run:
            print("\nRun with --execute to actually prune")

    def show_stats(self, session_id: Optional[str] = None):
        """Show memory statistics."""
        where = {"session_id": session_id} if session_id else None

        results = self.collection.get(
            where=where,
            include=["metadatas"]
        )

        if not results or not results.get("metadatas"):
            print("No memories found")
            return

        print(f"\n📊 Memory Statistics")
        print("=" * 80)

        # Count by importance
        importance_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        code_count = 0
        file_count = 0
        architecture_count = 0
        total_importance = 0

        for meta in results["metadatas"]:
            category = meta.get("importance_category", "low")
            importance_counts[category] = importance_counts.get(category, 0) + 1
            total_importance += meta.get("importance_score", 0.0)

            if meta.get("has_code"):
                code_count += 1
            if meta.get("has_files"):
                file_count += 1
            if meta.get("has_architecture"):
                architecture_count += 1

        total = len(results["metadatas"])
        avg_importance = total_importance / total if total > 0 else 0

        print(f"Total memories: {total}")
        print(f"Average importance: {avg_importance:.2f}")
        print()

        print("Importance Distribution:")
        for category, count in sorted(importance_counts.items(), key=lambda x: ["low", "medium", "high", "critical"].index(x[0])):
            indicator = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(category, "⚪")
            pct = (count / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"  {indicator} {category.capitalize():10s}: {count:4d} ({pct:5.1f}%) {bar}")

        print()
        print("Multi-modal Content:")
        print(f"  💻 Has code: {code_count} ({code_count / total * 100:.1f}%)")
        print(f"  📁 Has files: {file_count} ({file_count / total * 100:.1f}%)")
        print(f"  🏗️  Has architecture: {architecture_count} ({architecture_count / total * 100:.1f}%)")

    def export_memories(self, session_id: Optional[str] = None, output_file: str = "memories.json"):
        """Export memories to JSON."""
        where = {"session_id": session_id} if session_id else None

        results = self.collection.get(
            where=where,
            include=["metadatas", "documents"]
        )

        if not results or not results.get("ids"):
            print("No memories to export")
            return

        export_data = []
        for i, mem_id in enumerate(results["ids"]):
            export_data.append({
                "id": mem_id,
                "document": results["documents"][i],
                "metadata": results["metadatas"][i]
            })

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Exported {len(export_data)} memories to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Memory Management CLI")
    parser.add_argument("command", choices=["list", "search", "clusters", "prune", "stats", "export"],
                        help="Command to execute")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--session", "-s", help="Session ID to filter by")
    parser.add_argument("--execute", action="store_true", help="Execute pruning (not dry-run)")
    parser.add_argument("--output", "-o", default="memories.json", help="Output file for export")

    args = parser.parse_args()

    cli = MemoryCLI()

    try:
        if args.command == "list":
            cli.list_memories(args.session)

        elif args.command == "search":
            if not args.args:
                print("Error: search requires a query")
                sys.exit(1)
            query = " ".join(args.args)
            cli.search_memories(query, args.session)

        elif args.command == "clusters":
            if not args.session:
                print("Error: clusters requires --session")
                sys.exit(1)
            cli.show_clusters(args.session)

        elif args.command == "prune":
            cli.prune_memories(args.session, dry_run=not args.execute)

        elif args.command == "stats":
            cli.show_stats(args.session)

        elif args.command == "export":
            cli.export_memories(args.session, args.output)

    except KeyboardInterrupt:
        print("\nAborted")
        sys.exit(0)


if __name__ == "__main__":
    main()
