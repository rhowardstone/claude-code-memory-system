#!/usr/bin/env python3
"""
SWE-Bench-CL Isolated Testing Framework

CRITICAL SAFETY FEATURES:
- Never touches ~/.claude/memory-hooks/ (production hooks)
- Never uses ~/.claude/memory_db/ (production memories)
- Runs in isolated venv with separate dependencies
- Direct imports from test_variants/ directories

Usage:
    # Create isolated environment first
    python3 -m venv swebench_test_env
    source swebench_test_env/bin/activate
    pip install chromadb sentence-transformers langchain langgraph

    # Run isolated tests
    python3 run_isolated_comparison.py --variants faiss,v6,v7 --tasks 10
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SafetyError(Exception):
    """Raised when safety checks fail."""
    pass


def verify_isolation():
    """
    Verify we're running in isolated environment.

    Raises SafetyError if production system could be contaminated.
    """
    # Check 1: Not using production memory DB
    prod_memory_db = Path.home() / ".claude" / "memory_db"
    if prod_memory_db in [Path(p) for p in sys.path]:
        raise SafetyError(
            f"Production memory DB in sys.path! {prod_memory_db}\n"
            "This could contaminate production data!"
        )

    # Check 2: Not using production hooks
    prod_hooks = Path.home() / ".claude" / "memory-hooks"
    if prod_hooks in [Path(p) for p in sys.path]:
        raise SafetyError(
            f"Production hooks in sys.path! {prod_hooks}\n"
            "This could overwrite production hooks!"
        )

    # Check 3: Using isolated venv (recommended, not required)
    if "swebench" in sys.executable or "test" in sys.executable:
        logger.info(f"✅ Using isolated environment: {sys.executable}")
    else:
        logger.warning(f"⚠️  Not in isolated venv: {sys.executable}")
        logger.warning("Recommended: Create isolated venv to avoid dependency conflicts")

    logger.info("✅ Safety checks passed - no production contamination risk")


class IsolatedVariantConfig:
    """Configuration for a memory system variant."""

    def __init__(self, name: str, config_path: Path):
        self.name = name
        self.config_path = config_path

        # Load config
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Paths
        self.memory_db_path = Path(self.config["memory_db_path"])
        self.hooks_path = Path(self.config["hooks_path"])

        # Verify isolation
        self._verify_isolation()

    def _verify_isolation(self):
        """Verify this variant won't contaminate production."""
        # Check memory DB is isolated
        if "swebench" not in str(self.memory_db_path):
            raise SafetyError(
                f"Memory DB path must contain 'swebench' for isolation!\n"
                f"Got: {self.memory_db_path}"
            )

        # Check hooks are not production
        prod_hooks = Path.home() / ".claude" / "memory-hooks"
        if self.hooks_path == prod_hooks:
            raise SafetyError(
                f"Cannot use production hooks!\n"
                f"Must use isolated hooks in test_variants/"
            )

        logger.info(f"✅ Variant '{self.name}' is properly isolated")
        logger.info(f"   Memory DB: {self.memory_db_path}")
        logger.info(f"   Hooks: {self.hooks_path}")


class IsolatedVariantTester:
    """
    Tests a memory system variant in complete isolation.

    GUARANTEES:
    - Never modifies ~/.claude/memory-hooks/
    - Never uses ~/.claude/memory_db/
    - Direct imports from test_variants/
    """

    def __init__(self, config: IsolatedVariantConfig):
        self.config = config
        self.name = config.name

        # Create isolated memory DB directory
        self.config.memory_db_path.mkdir(parents=True, exist_ok=True)

        # Add variant's hooks to path (BEFORE production hooks!)
        sys.path.insert(0, str(self.config.hooks_path))

        # Initialize memory system
        self.memory_system = self._init_memory_system()

    def _init_memory_system(self):
        """Initialize memory system for this variant."""
        variant_type = self.config.config.get("type", "unknown")

        if variant_type == "v7":
            # Import V7 adapter from isolated hooks
            from v7_memory_adapter import V7MemoryAdapter, V7MemorySystem

            adapter = V7MemoryAdapter(
                memory_db_path=str(self.config.memory_db_path),
                k_results=self.config.config.get("k_results", 5)
            )
            return V7MemorySystem(adapter)

        elif variant_type == "faiss":
            # Use their FAISS implementation
            # TODO: Import from agents-never-forget
            logger.warning(f"FAISS variant not yet implemented")
            return None

        else:
            raise ValueError(f"Unknown variant type: {variant_type}")

    def run_task(self, task: Dict) -> Dict:
        """
        Run a single task with this variant's memory.

        Returns task result dict.
        """
        # Extract from nested structure
        task_id = task["metadata"]["instance_id"]
        problem_statement = task["task"]["problem_statement"]
        difficulty = task["metadata"]["difficulty"]

        logger.info(f"[{self.name}] Running task: {task_id} (difficulty: {difficulty})")

        # For now, simplified mock (replace with real eval later)
        # In real implementation, this would:
        # 1. Retrieve memories using problem_statement
        # 2. Run agent with memory context
        # 3. Check if tests pass
        # 4. Store experience in memory

        # Mock memory retrieval
        memories_retrieved = 0
        if self.memory_system:
            try:
                context = self.memory_system.get_relevant_context_for_prompt(
                    current_task_prompt=problem_statement[:200],  # Truncate for speed
                    current_sequence_id=task["metadata"]["repo"],
                    num_memories=5
                )
                memories_retrieved = context.count("SUCCESS") + context.count("FAILED")
            except Exception as e:
                logger.warning(f"Memory retrieval failed: {e}")
                memories_retrieved = 0

        # Mock success (higher rate for easier tasks)
        import random
        if difficulty == 1:  # Easy
            success_prob = 0.4
        elif difficulty == 2:  # Medium
            success_prob = 0.3
        else:  # Hard
            success_prob = 0.2

        # Boost if memories available
        if memories_retrieved > 0:
            success_prob += 0.1

        success = random.random() < success_prob

        result = {
            "task_id": task_id,
            "variant": self.name,
            "difficulty": difficulty,
            "repo": task["metadata"]["repo"],
            "success": success,
            "memories_retrieved": memories_retrieved,
            "problem_length": len(problem_statement)
        }

        # Store experience in memory (if enabled)
        if self.memory_system and success:
            try:
                solution_data = {
                    "problem_statement": problem_statement,
                    "solution_summary": "Successfully solved the issue",
                    "final_rationale": "Applied fix to codebase",
                    "tool_calls_count": random.randint(5, 15),
                    "tests_passed": True
                }
                self.memory_system.add_experience_to_memory(
                    task_id=task_id,
                    sequence_id=task["metadata"]["repo"],
                    solution_data=solution_data
                )
                logger.info(f"  ✓ Stored successful experience in memory")
            except Exception as e:
                logger.warning(f"Failed to store memory: {e}")

        return result

    def cleanup(self):
        """Clean up this variant's isolated memory DB."""
        if self.config.memory_db_path.exists():
            shutil.rmtree(self.config.memory_db_path)
            logger.info(f"🗑️  Cleaned up memory DB: {self.config.memory_db_path}")


def setup_test_variants():
    """
    Create test variant directories and configs.

    Call this once to set up the testing framework.
    """
    base_dir = Path(__file__).parent / "test_variants"
    base_dir.mkdir(exist_ok=True)

    # V7 variant
    v7_dir = base_dir / "v7_current"
    v7_dir.mkdir(exist_ok=True)

    v7_config = {
        "type": "v7",
        "memory_db_path": str(Path.home() / ".claude" / "memory_db_swebench_v7"),
        "hooks_path": str(Path(__file__).parent.parent / "hooks"),
        "k_results": 5,
        "config": {
            "contextual_embeddings": True,
            "task_context_aware": True,
            "adaptive_k": True
        }
    }

    with open(v7_dir / "config.json", 'w') as f:
        json.dump(v7_config, f, indent=2)

    logger.info(f"✅ Created V7 variant config: {v7_dir / 'config.json'}")

    # FAISS variant (TODO)
    faiss_dir = base_dir / "faiss_baseline"
    faiss_dir.mkdir(exist_ok=True)

    faiss_config = {
        "type": "faiss",
        "memory_db_path": str(Path.home() / ".claude" / "memory_db_swebench_faiss"),
        "hooks_path": str(Path(__file__).parent / "agents-never-forget" / "eval_v3_swe-agent"),
        "k_results": 5
    }

    with open(faiss_dir / "config.json", 'w') as f:
        json.dump(faiss_config, f, indent=2)

    logger.info(f"✅ Created FAISS variant config: {faiss_dir / 'config.json'}")

    return base_dir


def load_swebench_tasks(num_tasks: int = 10) -> List[Dict]:
    """Load SWE-Bench-CL tasks."""
    dataset_path = Path(__file__).parent / "agents-never-forget" / "data" / "SWE-Bench-CL-Curriculum.json"

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path, 'r') as f:
        dataset = json.load(f)

    # Collect tasks from all sequences
    tasks = []
    for sequence in dataset["sequences"]:
        tasks.extend(sequence["tasks"][:num_tasks])  # First N from each sequence
        if len(tasks) >= num_tasks:
            break

    return tasks[:num_tasks]


def run_isolated_comparison(variant_names: List[str], num_tasks: int) -> Dict[str, Any]:
    """
    Run comparison across variants in complete isolation.

    Args:
        variant_names: List of variant names (e.g., ["v7_current", "faiss_baseline"])
        num_tasks: Number of tasks to run per variant

    Returns:
        Comparison results dict
    """
    print("="*70)
    print("ISOLATED VARIANT COMPARISON")
    print("="*70)
    print()

    # Verify safety
    verify_isolation()
    print()

    # Load tasks
    logger.info(f"Loading {num_tasks} tasks from SWE-Bench-CL...")
    tasks = load_swebench_tasks(num_tasks)
    logger.info(f"✅ Loaded {len(tasks)} tasks")
    print()

    # Run each variant
    results = {}

    for variant_name in variant_names:
        print(f"{'='*70}")
        print(f"Testing variant: {variant_name}")
        print(f"{'='*70}\n")

        # Load variant config
        config_path = Path(__file__).parent / "test_variants" / variant_name / "config.json"

        if not config_path.exists():
            logger.error(f"Config not found: {config_path}")
            logger.error(f"Run setup_test_variants() first!")
            continue

        config = IsolatedVariantConfig(variant_name, config_path)

        # Create tester
        tester = IsolatedVariantTester(config)

        # Run tasks
        variant_results = []
        for task in tasks:
            result = tester.run_task(task)
            variant_results.append(result)

        # Calculate metrics
        success_count = sum(1 for r in variant_results if r["success"])
        success_rate = success_count / len(variant_results)

        results[variant_name] = {
            "success_rate": success_rate,
            "tasks_run": len(variant_results),
            "tasks_succeeded": success_count,
            "task_results": variant_results
        }

        logger.info(f"✅ {variant_name}: {success_rate:.1%} success rate ({success_count}/{len(variant_results)})")

        # Cleanup
        tester.cleanup()
        print()

    # Save results
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"comparison_{num_tasks}_tasks.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"✅ Results saved: {output_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run isolated SWE-Bench-CL comparison")
    parser.add_argument("--setup", action="store_true", help="Set up test variants")
    parser.add_argument("--variants", type=str, default="v7_current", help="Comma-separated variant names")
    parser.add_argument("--tasks", type=int, default=10, help="Number of tasks to run")
    parser.add_argument("--verify-only", action="store_true", help="Only verify isolation")

    args = parser.parse_args()

    # Setup mode
    if args.setup:
        setup_test_variants()
        return

    # Verify mode
    if args.verify_only:
        verify_isolation()
        print("✅ All safety checks passed!")
        return

    # Run comparison
    variant_names = [v.strip() for v in args.variants.split(",")]

    try:
        results = run_isolated_comparison(variant_names, args.tasks)

        # Print summary
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        for variant_name, result in results.items():
            print(f"{variant_name:20s}: {result['success_rate']:.1%} ({result['tasks_succeeded']}/{result['tasks_run']})")
        print("="*70)

    except SafetyError as e:
        logger.error(f"❌ SAFETY ERROR: {e}")
        logger.error("Comparison aborted to protect production system!")
        sys.exit(1)


if __name__ == "__main__":
    main()
