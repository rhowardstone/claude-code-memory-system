#!/usr/bin/env python3
"""
Diagnostic Analysis of SWE-Bench-CL Results

Analyzes test results to understand:
- Where did we fail? Why?
- Did memory help or hurt?
- What patterns exist in failures?
- Are certain repos/difficulties harder?
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any


class ResultsDiagnoser:
    """Diagnoses test results to find patterns and issues."""

    def __init__(self, results_path: Path):
        with open(results_path) as f:
            self.results = json.load(f)

        self.variant_name = list(self.results.keys())[0]
        self.variant_data = self.results[self.variant_name]
        self.task_results = self.variant_data["task_results"]

    def print_summary(self):
        """Print high-level summary."""
        print("="*70)
        print(f"DIAGNOSTIC ANALYSIS: {self.variant_name}")
        print("="*70)
        print()

        # Overall metrics
        total = self.variant_data["tasks_run"]
        succeeded = self.variant_data["tasks_succeeded"]
        success_rate = self.variant_data["success_rate"]

        print(f"Overall Performance:")
        print(f"  Tasks run: {total}")
        print(f"  Succeeded: {succeeded}")
        print(f"  Failed: {total - succeeded}")
        print(f"  Success rate: {success_rate:.1%}")
        print()

    def analyze_by_difficulty(self):
        """Analyze success rate by difficulty."""
        print("="*70)
        print("ANALYSIS BY DIFFICULTY")
        print("="*70)
        print()

        by_difficulty = defaultdict(lambda: {"total": 0, "succeeded": 0})

        for task in self.task_results:
            diff = task["difficulty"]
            by_difficulty[diff]["total"] += 1
            if task["success"]:
                by_difficulty[diff]["succeeded"] += 1

        for diff in sorted(by_difficulty.keys()):
            stats = by_difficulty[diff]
            rate = stats["succeeded"] / stats["total"] if stats["total"] > 0 else 0
            print(f"Difficulty '{diff}':")
            print(f"  Success rate: {rate:.1%} ({stats['succeeded']}/{stats['total']})")

        print()

    def analyze_by_repo(self):
        """Analyze success rate by repository."""
        print("="*70)
        print("ANALYSIS BY REPOSITORY")
        print("="*70)
        print()

        by_repo = defaultdict(lambda: {"total": 0, "succeeded": 0})

        for task in self.task_results:
            repo = task["repo"]
            by_repo[repo]["total"] += 1
            if task["success"]:
                by_repo[repo]["succeeded"] += 1

        for repo in sorted(by_repo.keys()):
            stats = by_repo[repo]
            rate = stats["succeeded"] / stats["total"] if stats["total"] > 0 else 0
            print(f"{repo:30s}: {rate:.1%} ({stats['succeeded']}/{stats['total']})")

        print()

    def analyze_memory_impact(self):
        """Analyze whether memory retrieval helped."""
        print("="*70)
        print("MEMORY IMPACT ANALYSIS")
        print("="*70)
        print()

        with_memory = {"total": 0, "succeeded": 0}
        without_memory = {"total": 0, "succeeded": 0}

        for task in self.task_results:
            if task["memories_retrieved"] > 0:
                with_memory["total"] += 1
                if task["success"]:
                    with_memory["succeeded"] += 1
            else:
                without_memory["total"] += 1
                if task["success"]:
                    without_memory["succeeded"] += 1

        if with_memory["total"] > 0:
            rate_with = with_memory["succeeded"] / with_memory["total"]
            print(f"Tasks with memory retrieved:")
            print(f"  Success rate: {rate_with:.1%} ({with_memory['succeeded']}/{with_memory['total']})")
            print(f"  Avg memories: {sum(t['memories_retrieved'] for t in self.task_results if t['memories_retrieved'] > 0) / with_memory['total']:.1f}")
        else:
            print("No tasks had memory retrieved")

        print()

        if without_memory["total"] > 0:
            rate_without = without_memory["succeeded"] / without_memory["total"]
            print(f"Tasks without memory:")
            print(f"  Success rate: {rate_without:.1%} ({without_memory['succeeded']}/{without_memory['total']})")
        else:
            print("All tasks had memory retrieved")

        print()

        if with_memory["total"] > 0 and without_memory["total"] > 0:
            diff = rate_with - rate_without
            if diff > 0:
                print(f"✅ Memory HELPED: +{diff:.1%} success rate improvement")
            elif diff < 0:
                print(f"❌ Memory HURT: {diff:.1%} success rate decrease")
            else:
                print(f"🤷 Memory had NO IMPACT")

        print()

    def show_failures(self, limit: int = 10):
        """Show detailed failure analysis."""
        print("="*70)
        print(f"TOP {limit} FAILURES (for diagnosis)")
        print("="*70)
        print()

        failures = [t for t in self.task_results if not t["success"]]

        if not failures:
            print("No failures! 🎉")
            return

        for i, task in enumerate(failures[:limit], 1):
            print(f"\n{i}. {task['task_id']}")
            print(f"   Repository: {task['repo']}")
            print(f"   Difficulty: {task['difficulty']}")
            print(f"   Memories retrieved: {task['memories_retrieved']}")
            print(f"   Problem length: {task['problem_length']} chars")

            # In real implementation, would show:
            # - Retrieved memory details
            # - Agent actions taken
            # - Why tests failed
            # - Comparison with baseline

        print()

    def show_successes(self, limit: int = 5):
        """Show successful tasks for comparison."""
        print("="*70)
        print(f"TOP {limit} SUCCESSES (what worked)")
        print("="*70)
        print()

        successes = [t for t in self.task_results if t["success"]]

        if not successes:
            print("No successes yet 😞")
            return

        for i, task in enumerate(successes[:limit], 1):
            print(f"\n{i}. {task['task_id']}")
            print(f"   Repository: {task['repo']}")
            print(f"   Difficulty: {task['difficulty']}")
            print(f"   Memories retrieved: {task['memories_retrieved']}")
            print(f"   Problem length: {task['problem_length']} chars")

        print()

    def compare_variants(self, other_results_path: Path):
        """Compare this variant with another (e.g., baseline)."""
        print("="*70)
        print("VARIANT COMPARISON")
        print("="*70)
        print()

        with open(other_results_path) as f:
            other_results = json.load(f)

        # TODO: Implement comparison logic
        print("Comparison not yet implemented")
        print()

    def export_analysis(self, output_path: Path):
        """Export detailed analysis to JSON."""
        analysis = {
            "variant": self.variant_name,
            "summary": {
                "total_tasks": self.variant_data["tasks_run"],
                "succeeded": self.variant_data["tasks_succeeded"],
                "failed": self.variant_data["tasks_run"] - self.variant_data["tasks_succeeded"],
                "success_rate": self.variant_data["success_rate"]
            },
            "by_difficulty": {},
            "by_repo": {},
            "memory_impact": {},
            "failures": [t for t in self.task_results if not t["success"]],
            "successes": [t for t in self.task_results if t["success"]]
        }

        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"✅ Detailed analysis exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Diagnose SWE-Bench-CL results")
    parser.add_argument("results", type=str, help="Path to results JSON")
    parser.add_argument("--compare", type=str, help="Compare with another results file")
    parser.add_argument("--show-failures", type=int, default=10, help="Number of failures to show")
    parser.add_argument("--show-successes", type=int, default=5, help="Number of successes to show")
    parser.add_argument("--export", type=str, help="Export detailed analysis to file")

    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"❌ Results file not found: {results_path}")
        return

    diagnoser = ResultsDiagnoser(results_path)

    # Run analyses
    diagnoser.print_summary()
    diagnoser.analyze_by_difficulty()
    diagnoser.analyze_by_repo()
    diagnoser.analyze_memory_impact()
    diagnoser.show_failures(args.show_failures)
    diagnoser.show_successes(args.show_successes)

    if args.compare:
        diagnoser.compare_variants(Path(args.compare))

    if args.export:
        diagnoser.export_analysis(Path(args.export))


if __name__ == "__main__":
    main()
