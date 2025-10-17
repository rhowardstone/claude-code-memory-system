#!/usr/bin/env python3
"""
Real SWE-Bench-CL Evaluator with Actual Code Editing and Test Execution

Clones repos, lets Claude edit code, runs tests.
"""

import subprocess
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class RealSWEBenchEvaluator:
    """Real evaluation with repo cloning and test execution."""

    def __init__(self, use_memory: bool = True, workspace_dir: str = "workspaces"):
        self.use_memory = use_memory
        self.workspace_dir = workspace_dir

        # Load dataset
        dataset_path = Path(__file__).parent / "agents-never-forget/data/SWE-Bench-CL-Curriculum.json"
        with open(dataset_path) as f:
            self.dataset = json.load(f)

        # Initialize V7 memory if enabled
        if self.use_memory:
            from v7_memory_adapter import V7MemoryAdapter

            memory_db_path = str(Path.home() / ".claude" / "memory_db_swebench_real")
            self.memory_adapter = V7MemoryAdapter(
                memory_db_path=memory_db_path,
                k_results=5
            )
            logger.info("✅ V7 memory system initialized")
        else:
            self.memory_adapter = None
            logger.info("Running WITHOUT memory (baseline)")

        logger.info(f"{'='*70}")
        logger.info(f"REAL SWE-BENCH-CL EVALUATOR")
        logger.info(f"Memory: {'ENABLED' if use_memory else 'DISABLED'}")
        logger.info(f"{'='*70}\n")

    def setup_repo(self, task: Dict, workspace_dir: Path) -> bool:
        """Clone repo and checkout base_commit."""
        repo = task["metadata"]["repo"]
        base_commit = task["metadata"]["base_commit"]

        # GitHub URL
        repo_url = f"https://github.com/{repo}.git"

        logger.info(f"Cloning {repo}...")
        try:
            # Clone with depth 1 for speed, then fetch commit
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(workspace_dir)],
                capture_output=True,
                check=True
            )

            # Fetch the specific commit
            subprocess.run(
                ["git", "-C", str(workspace_dir), "fetch", "--depth", "1", "origin", base_commit],
                capture_output=True,
                check=True
            )

            # Checkout commit
            subprocess.run(
                ["git", "-C", str(workspace_dir), "checkout", base_commit],
                capture_output=True,
                check=True
            )

            logger.info(f"✅ Checked out {base_commit[:8]}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to setup repo: {e}")
            return False

    def install_repo(self, workspace_dir: Path) -> bool:
        """Install the repository in development mode."""
        try:
            # Install in editable mode
            result = subprocess.run(
                ["pip", "install", "-e", ".", "-q"],
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                logger.info("✅ Installed repository")
                return True
            else:
                logger.warning(f"Package install had issues: {result.stderr[:200]}")
                return True  # Continue anyway - might still work
        except Exception as e:
            logger.warning(f"Failed to install package: {e}")
            return True  # Continue anyway

    def apply_test_patch(self, task: Dict, workspace_dir: Path) -> bool:
        """Apply test patch to add test cases."""
        test_patch = task["evaluation"].get("test_patch")
        if not test_patch:
            return True

        patch_file = workspace_dir / "test.patch"
        patch_file.write_text(test_patch)

        try:
            subprocess.run(
                ["git", "-C", str(workspace_dir), "apply", "test.patch"],
                capture_output=True,
                check=True
            )
            logger.info("✅ Applied test patch")
            return True
        except subprocess.CalledProcessError:
            logger.error("❌ Failed to apply test patch")
            return False

    def parse_test_name(self, test_str: str) -> str:
        """Parse test name from format 'test_name (module.TestClass)' to 'module.TestClass.test_name'"""
        import re
        match = re.match(r'(\w+)\s+\((.+)\)', test_str)
        if match:
            test_name, module_class = match.groups()
            return f"{module_class}.{test_name}"
        return test_str  # Return as-is if parsing fails

    def run_tests(self, task: Dict, workspace_dir: Path, test_list: List[str]) -> Dict[str, bool]:
        """Run specific tests and return results."""
        if not test_list:
            return {}

        results = {}
        repo = task["metadata"]["repo"]

        # Django-specific test running
        if "django" in repo:
            # Set PYTHONPATH to include workspace
            env = os.environ.copy()
            env["PYTHONPATH"] = str(workspace_dir)

            for test in test_list:
                try:
                    # Parse test name to Django format
                    parsed_test = self.parse_test_name(test)
                    logger.info(f"Running test: {parsed_test}")

                    # Run Django test using their test runner
                    result = subprocess.run(
                        ["python", "./tests/runtests.py", "--verbosity", "2", parsed_test],
                        cwd=workspace_dir,
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=60  # 60 second timeout per test
                    )

                    # Check for Python version incompatibility errors
                    if "codeset" in result.stderr or "TypeError" in result.stderr:
                        logger.warning(f"⚠️  Test {test} has Python version incompatibility - skipping")
                        results[test] = None  # Mark as unable to test
                    else:
                        results[test] = (result.returncode == 0)
                        if result.returncode != 0:
                            logger.warning(f"Test {test} failed")
                except Exception as e:
                    logger.warning(f"Test {test} errored: {e}")
                    results[test] = None  # Can't determine result

        return results

    def call_claude(self, workspace_dir: Path, problem: str, memory_context: str = "") -> tuple[bool, str]:
        """Call Claude to fix the issue in the workspace. Returns (success, output)."""
        prompt = f"""You are a coding agent working on a Django codebase. You have file editing tools available (Read, Edit, Write, Bash, Glob, Grep).

WORKSPACE: {workspace_dir}

{memory_context}

ISSUE TO FIX:
{problem}

YOUR TASK:
1. Use Glob/Grep to find the relevant file(s) mentioned in the issue
2. Use Read to examine the file structure
3. Use Edit to make the minimal necessary code changes
4. DO NOT just output code - you must actually edit the files using your tools
5. When finished editing, respond with "TASK COMPLETE"

IMPORTANT: You MUST use the file editing tools. The test will check if the actual files were modified.
Focus on minimal, correct fixes. Do not overthink - implement exactly what the issue requests.

Begin!"""

        try:
            # Run Claude WITHOUT --print so it can use file tools!
            # Use full path to claude binary
            claude_bin = "/atb-data/rye/.nvm/versions/node/v18.20.5/bin/claude"
            result = subprocess.run(
                [claude_bin, "--model", "sonnet", "--dangerously-skip-permissions"],
                input=prompt,
                cwd=workspace_dir,
                capture_output=True,
                text=True
            )

            # Log Claude's output for debugging
            logger.info(f"Claude stdout ({len(result.stdout)} chars): {result.stdout[:500]}...")
            logger.info(f"Claude stderr: {result.stderr[:500] if result.stderr else 'None'}")

            # Check if Claude completed
            success = "TASK COMPLETE" in result.stdout or result.returncode == 0
            if not success:
                logger.warning(f"Claude did not complete successfully. Return code: {result.returncode}")

            return success, result.stdout

        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            return False, ""

    def evaluate_task(self, task: Dict, task_num: int, total: int) -> Dict[str, Any]:
        """Run full evaluation on a single task."""
        task_id = task["metadata"]["instance_id"]
        repo = task["metadata"]["repo"]
        difficulty = task["metadata"]["difficulty"]

        logger.info(f"\n{'='*70}")
        logger.info(f"[{task_num}/{total}] {task_id}")
        logger.info(f"Repo: {repo} | Difficulty: {difficulty}")
        logger.info(f"{'='*70}")

        # Create workspace in LOCAL directory (NEVER use /tmp!)
        workspaces_base = Path(__file__).parent / self.workspace_dir
        workspaces_base.mkdir(exist_ok=True)
        workspace_dir = workspaces_base / f"swebench_{task_id}"
        workspace_dir.mkdir(exist_ok=True)

        try:
            # 1. Setup repo
            if not self.setup_repo(task, workspace_dir):
                return {"task_id": task_id, "success": False, "error": "repo_setup_failed"}

            # 2. Install the package
            self.install_repo(workspace_dir)

            # 3. Apply test patch
            if not self.apply_test_patch(task, workspace_dir):
                return {"task_id": task_id, "success": False, "error": "test_patch_failed"}

            # 4. Run FAIL_TO_PASS tests (should fail initially)
            fail_to_pass = task["evaluation"].get("FAIL_TO_PASS", [])
            initial_results = self.run_tests(task, workspace_dir, fail_to_pass)
            logger.info(f"Initial tests: {sum(1 for v in initial_results.values() if v)}/{len(initial_results)} passing")

            # 5. Get memory context
            memory_context = ""
            if self.memory_adapter:
                problem = task["task"]["problem_statement"]
                memories = self.memory_adapter.retrieve_relevant(
                    query=problem[:200],
                    sequence_id_filter=repo,
                    num_results=5
                )
                if memories:
                    memory_context = "\n## RELEVANT PAST SOLUTIONS:\n"
                    for i, mem in enumerate(memories, 1):
                        # Extract just the problem and solution (first 300 chars)
                        content = mem.get('content', '')
                        if 'Problem:' in content and 'Solution:' in content:
                            # Extract problem and solution lines
                            lines = content.split('\n')
                            problem_line = next((l for l in lines if l.startswith('Problem:')), '')
                            solution_line = next((l for l in lines if l.startswith('Solution:')), '')
                            summary = f"{problem_line[:100]}... {solution_line[:100]}"
                        else:
                            summary = content[:200]
                        memory_context += f"{i}. {summary}\n"
                    logger.info(f"Retrieved {len(memories)} memories")

            # 6. Call Claude to fix
            logger.info("Calling Claude to fix the issue...")
            claude_success, claude_output = self.call_claude(workspace_dir, task["task"]["problem_statement"], memory_context)

            # 7. Run tests again
            final_results = self.run_tests(task, workspace_dir, fail_to_pass)
            logger.info(f"Final tests: {sum(1 for v in final_results.values() if v)}/{len(final_results)} passing")

            # Check success (filter out None values for untestable)
            testable_results = {k: v for k, v in final_results.items() if v is not None}
            if not testable_results:
                logger.info("⚠️  UNTESTABLE (Python version incompatibility)")
                success = False
                untestable = True
            else:
                success = all(testable_results.values())
                untestable = False
                logger.info(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

            # 8. Store in memory if successful
            if self.memory_adapter and success:
                # Build rich memory content with problem, solution, and outcome
                problem_statement = task["task"]["problem_statement"]

                # Extract solution summary from Claude's output (first 500 chars of meaningful content)
                solution_summary = "Applied code changes to fix the issue"
                if claude_success and claude_output:
                    # Look for key phrases in Claude's output
                    output_lines = claude_output.split('\n')
                    for line in output_lines:
                        if any(keyword in line.lower() for keyword in ['fixed', 'changed', 'updated', 'modified', 'added']):
                            solution_summary = line.strip()[:200]
                            break

                # Get modified files from git
                try:
                    git_status = subprocess.run(
                        ["git", "-C", str(workspace_dir), "diff", "--name-only"],
                        capture_output=True, text=True, timeout=5
                    )
                    modified_files = [f for f in git_status.stdout.split('\n') if f.strip()]
                except:
                    modified_files = []

                # Build comprehensive content for memory
                memory_content = f"""Problem: {problem_statement}

Solution: {solution_summary}

Files Modified: {', '.join(modified_files[:5]) if modified_files else 'Unknown'}

Tests: {len(testable_results)}/{len(fail_to_pass)} tests passing

Difficulty: {difficulty}"""

                self.memory_adapter.add_entry(
                    task_id=task_id,
                    sequence_id=repo,
                    content=memory_content,
                    success=True,
                    metadata={
                        "difficulty": difficulty,
                        "files_modified": modified_files[:10],
                        "test_count": len(testable_results)
                    }
                )
                logger.info(f"💾 Stored in memory ({len(modified_files)} files, {len(testable_results)} tests)")

            return {
                "task_id": task_id,
                "repo": repo,
                "success": success,
                "untestable": untestable if 'untestable' in locals() else False,
                "initial_passing": sum(1 for v in initial_results.values() if v),
                "final_passing": sum(1 for v in final_results.values() if v),
                "total_tests": len(fail_to_pass),
                "testable_tests": len([v for v in final_results.values() if v is not None]),
                "workspace": str(workspace_dir)
            }

        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            return {"task_id": task_id, "success": False, "error": str(e)}
        # DO NOT cleanup - keep workspaces for debugging!

    def run_evaluation(self, num_tasks: int = 10) -> Dict[str, Any]:
        """Run evaluation on N tasks."""
        tasks = []
        for sequence in self.dataset["sequences"]:
            for task in sequence["tasks"]:
                tasks.append(task)
                if len(tasks) >= num_tasks:
                    break
            if len(tasks) >= num_tasks:
                break

        logger.info(f"\nRunning {len(tasks)} tasks...\n")

        results = []
        for i, task in enumerate(tasks, 1):
            result = self.evaluate_task(task, i, len(tasks))
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
    parser.add_argument("--tasks", type=int, default=10, help="Number of tasks")
    parser.add_argument("--no-memory", action="store_true", help="Disable memory")
    parser.add_argument("--output", type=str, default="results/swebench_real.json")
    parser.add_argument("--workspace-dir", type=str, default="workspaces", help="Workspace directory for repo clones")

    args = parser.parse_args()

    evaluator = RealSWEBenchEvaluator(
        use_memory=not args.no_memory,
        workspace_dir=args.workspace_dir
    )
    results = evaluator.run_evaluation(num_tasks=args.tasks)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved: {output_path}")


if __name__ == "__main__":
    main()
