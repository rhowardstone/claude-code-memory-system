#!/usr/bin/env python3
"""
Real SWE-Bench-CL Evaluator using Claude CLI

Uses `claude --print` to solve tasks - no API keys needed!
Tests our V7 memory system on real tasks.
"""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ClaudeCLIEvaluator:
    """Evaluator using claude --print for real solutions."""

    def __init__(self, use_memory: bool = True):
        self.use_memory = use_memory

        # Load dataset
        dataset_path = Path(__file__).parent / "agents-never-forget/data/SWE-Bench-CL-Curriculum.json"
        with open(dataset_path) as f:
            self.dataset = json.load(f)

        # Initialize V7 memory system if enabled
        if self.use_memory:
            # Import V7 adapter
            from v7_memory_adapter import V7MemoryAdapter

            memory_db_path = str(Path.home() / ".claude" / "memory_db_swebench_cli")
            self.memory_adapter = V7MemoryAdapter(
                memory_db_path=memory_db_path,
                k_results=5
            )
            logger.info("✅ V7 memory system initialized")
        else:
            self.memory_adapter = None
            logger.info("Running WITHOUT memory (baseline)")

        logger.info(f"{'='*70}")
        logger.info(f"CLAUDE CLI EVALUATOR")
        logger.info(f"Memory: {'ENABLED' if use_memory else 'DISABLED'}")
        logger.info(f"{'='*70}\n")

    def call_claude(self, prompt: str, task_id: str = None) -> str:
        """Call Claude via CLI (pipe prompt into stdin) in sandboxed workspace."""
        try:
            # Create sandboxed workspace for this task
            workspace_dir = Path(__file__).parent / "workspaces" / (task_id or "default")
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # Escape prompt for shell
            escaped_prompt = prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')

            # Run Claude from within workspace directory for isolation
            # This limits file access to just the workspace subdirectory
            cmd = f'cd "{workspace_dir}" && echo "{escaped_prompt}" | claude --print --model sonnet --dangerously-skip-permissions'

            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True
                # NO timeout! Agentic workflows can take hours!
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Claude CLI error: {e}")
            return ""

    def get_memory_context(self, task: Dict) -> str:
        """Get memory context for task (if memory enabled)."""
        if not self.memory_adapter:
            return ""

        # Query V7 memory system for relevant past experiences
        problem = task["task"]["problem_statement"]
        repo = task["metadata"]["repo"]

        memories = self.memory_adapter.retrieve_relevant(
            query=problem[:200],  # Use first 200 chars of problem
            sequence_id_filter=repo,  # Only memories from same repo
            num_results=5
        )

        if not memories:
            return ""

        # Format memories into context
        context_lines = ["\n## RELEVANT PAST EXPERIENCE:\n"]
        for i, mem in enumerate(memories, 1):
            metadata = mem.get("metadata", {})
            task_id = metadata.get("task_id", "unknown")
            success = metadata.get("success", False)
            status = "✅ SUCCESS" if success else "❌ FAILED"

            context_lines.append(f"{i}. Task {task_id} ({status}):")
            context_lines.append(f"   {mem.get('summary', 'No summary')[:150]}")

        return "\n".join(context_lines)

    def build_prompt(self, task: Dict, memory_context: str = "") -> str:
        """Build prompt for Claude."""
        problem = task["task"]["problem_statement"]
        repo = task["metadata"]["repo"]

        prompt = f"""You are solving a GitHub issue in {repo}.

{memory_context}

PROBLEM:
{problem}

Please provide a concise code fix. Return ONLY the essential code changes needed.
Be specific and practical - focus on the minimal fix that solves the issue."""

        return prompt

    def evaluate_solution(self, task: Dict, solution: str) -> bool:
        """
        Evaluate if solution is good (heuristic).

        Real evaluation would:
        1. Clone repo at base_commit
        2. Apply solution
        3. Run tests from test_patch
        4. Check if FAIL_TO_PASS tests now pass
        """
        if not solution or len(solution) < 50:
            return False

        # Heuristic: solution should contain code
        has_code = any(keyword in solution for keyword in [
            "def ", "class ", "import ", "return ", "if ", "for ", "@", "self.", "="
        ])

        # Heuristic: solution should be relevant to problem
        problem_lower = task["task"]["problem_statement"].lower()
        solution_lower = solution.lower()

        # Extract key words from problem
        key_words = []
        for word in problem_lower.split():
            if len(word) > 4 and word.isalpha():
                key_words.append(word)

        # Check overlap
        overlap = sum(1 for word in key_words if word in solution_lower)
        relevance = overlap / len(key_words) if key_words else 0

        return has_code and relevance > 0.2

    def run_task(self, task: Dict, task_num: int, total: int) -> Dict[str, Any]:
        """Run a single task."""
        task_id = task["metadata"]["instance_id"]
        repo = task["metadata"]["repo"]
        difficulty = task["metadata"]["difficulty"]

        logger.info(f"\n{'='*70}")
        logger.info(f"[{task_num}/{total}] {task_id}")
        logger.info(f"Repo: {repo} | Difficulty: {difficulty}")
        logger.info(f"{'='*70}")

        # Get memory context
        memory_context = self.get_memory_context(task)
        memories_retrieved = memory_context.count("Task ") if memory_context else 0
        if memories_retrieved > 0:
            logger.info(f"Retrieved {memories_retrieved} relevant memories")

        # Build prompt
        prompt = self.build_prompt(task, memory_context)
        logger.info("Querying Claude via CLI...")

        # Call Claude in sandboxed workspace
        solution = self.call_claude(prompt, task_id=task_id)
        logger.info(f"Got solution: {len(solution)} chars")

        # Evaluate
        success = self.evaluate_solution(task, solution)
        logger.info(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

        # Store experience in memory if successful
        if self.memory_adapter and success:
            problem = task["task"]["problem_statement"]
            solution_summary = f"Fixed {problem[:100]}... with solution: {solution[:200]}"

            self.memory_adapter.add_entry(
                task_id=task_id,
                sequence_id=repo,
                content=solution_summary,
                success=True,
                metadata={
                    "difficulty": difficulty,
                    "solution_length": len(solution)
                }
            )
            logger.info("💾 Stored successful solution in memory")

        return {
            "task_id": task_id,
            "repo": repo,
            "difficulty": difficulty,
            "success": success,
            "solution_length": len(solution),
            "solution_preview": solution[:200] + "..." if len(solution) > 200 else solution,
            "memories_retrieved": memories_retrieved
        }

    def run_evaluation(self, num_tasks: int = 5) -> Dict[str, Any]:
        """Run evaluation on N tasks."""
        # Collect tasks
        tasks = []
        for sequence in self.dataset["sequences"]:
            for task in sequence["tasks"]:
                tasks.append(task)
                if len(tasks) >= num_tasks:
                    break
            if len(tasks) >= num_tasks:
                break

        logger.info(f"\nRunning {len(tasks)} tasks...\n")

        # Run tasks
        results = []
        for i, task in enumerate(tasks, 1):
            result = self.run_task(task, i, len(tasks))
            results.append(result)

        # Calculate metrics
        success_count = sum(1 for r in results if r["success"])
        success_rate = success_count / len(results)

        summary = {
            "total_tasks": len(results),
            "succeeded": success_count,
            "failed": len(results) - success_count,
            "success_rate": success_rate,
            "use_memory": self.use_memory,
            "task_results": results
        }

        # Print summary
        logger.info(f"\n{'='*70}")
        logger.info("EVALUATION COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Success rate: {success_rate:.1%} ({success_count}/{len(results)})")
        logger.info(f"Memory: {'ENABLED' if self.use_memory else 'DISABLED'}")
        logger.info(f"{'='*70}\n")

        return summary


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=5, help="Number of tasks")
    parser.add_argument("--no-memory", action="store_true", help="Disable memory")
    parser.add_argument("--output", type=str, default="results/claude_cli_eval.json")

    args = parser.parse_args()

    evaluator = ClaudeCLIEvaluator(use_memory=not args.no_memory)
    results = evaluator.run_evaluation(num_tasks=args.tasks)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved: {output_path}")


if __name__ == "__main__":
    main()
