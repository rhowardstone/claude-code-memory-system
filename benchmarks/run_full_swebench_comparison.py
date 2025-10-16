#!/usr/bin/env python3
"""
Run Full SWE-Bench-CL Comparison: FAISS vs V7 Memory

This script modifies their eval_v3_swe-agent framework to:
1. Run with THEIR FAISS memory system (baseline)
2. Run with OUR V7 memory system
3. Compare results on the full 273-task dataset

Usage:
    # Run both methods on full dataset (273 tasks)
    python3 run_full_swebench_comparison.py --full

    # Run pilot (first 10 tasks of each sequence)
    python3 run_full_swebench_comparison.py --pilot 10

    # Run specific sequence only
    python3 run_full_swebench_comparison.py --sequence "django/django" --num-tasks 20
"""

import sys
import json
import argparse
from pathlib import Path
import logging

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def modify_eval_script_for_v7():
    """
    Creates a modified version of eval_procedure.py that uses V7 memory.

    Strategy:
    1. Import our V7MemoryAdapter
    2. Replace SemanticMemory instantiation (line ~1199)
    3. Keep everything else the same
    """
    eval_script_path = Path("agents-never-forget/eval_v3_swe-agent/eval_procedure.py")

    if not eval_script_path.exists():
        raise FileNotFoundError(f"Evaluation script not found: {eval_script_path}")

    with open(eval_script_path, 'r') as f:
        content = f.read()

    # Create V7 version
    v7_content = content

    # 1. Add V7 imports after other imports
    import_insertion = """
# === V7 MEMORY SYSTEM INTEGRATION ===
import sys
from pathlib import Path as PathV7
sys.path.insert(0, str(PathV7(__file__).parent.parent.parent))
from v7_memory_adapter import V7MemoryAdapter, V7MemorySystem
# === END V7 INTEGRATION ===
"""

    # Find where to insert (after the embedding imports)
    insert_after = "from langchain_ollama import OllamaEmbeddings"
    v7_content = v7_content.replace(
        insert_after,
        insert_after + "\n" + import_insertion
    )

    # 2. Replace memory system initialization
    # Original:
    # if active_embedding_model:
    #     semantic_memory_instance = SemanticMemory(embedding_model=active_embedding_model)
    #     memory_system = MemorySystem(semantic_memory_instance)

    # New V7 version:
    v7_memory_init = """    # V7 MEMORY SYSTEM (replaces FAISS)
    logger.info("Initializing V7 Memory System (ChromaDB + Task-Context Aware)")
    v7_adapter = V7MemoryAdapter(
        memory_db_path=str(PathV7.home() / ".claude" / "memory_db_swebench"),
        k_results=5
    )
    memory_system = V7MemorySystem(v7_adapter)
    logger.info("Memory system initialized with V7 (contextual embeddings + knowledge graph).")
"""

    # Replace the original memory initialization
    faiss_init_pattern = """    if active_embedding_model:
        semantic_memory_instance = SemanticMemory(embedding_model=active_embedding_model)
        memory_system = MemorySystem(semantic_memory_instance)
        logger.info(f"Memory system initialized with {embedding_model_name}.")"""

    v7_content = v7_content.replace(faiss_init_pattern, v7_memory_init)

    # 3. Disable USE_DUMMY_DATA (use real dataset)
    v7_content = v7_content.replace(
        "USE_DUMMY_DATA = True",
        "USE_DUMMY_DATA = False  # V7: Use real dataset, not dummy"
    )

    # Save V7 version
    v7_script_path = Path("agents-never-forget/eval_v3_swe-agent/eval_procedure_v7.py")
    with open(v7_script_path, 'w') as f:
        f.write(v7_content)

    logger.info(f"Created V7 evaluation script: {v7_script_path}")
    return v7_script_path


def create_comparison_runner():
    """
    Creates a Python script that runs both FAISS and V7 evaluations.
    """
    runner_script = Path("agents-never-forget/eval_v3_swe-agent/run_comparison.py")

    runner_content = """#!/usr/bin/env python3
'''
Comparison Runner: FAISS vs V7 Memory

This script executes both evaluation procedures and compares results.
'''

import sys
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_faiss_baseline(sequence_ids=None, num_tasks_per_seq=None):
    '''Run evaluation with FAISS memory (their baseline)'''
    logger.info("="*70)
    logger.info("RUNNING BASELINE: FAISS Memory System")
    logger.info("="*70)

    # Import original evaluation script
    from eval_procedure import (
        swe_bench_cl, agent_workflow, memory_system,
        SWEAgentCLEvaluator, initialized_models
    )

    if not memory_system:
        logger.error("FAISS memory system not initialized!")
        return None

    evaluator = SWEAgentCLEvaluator(swe_bench_cl, agent_workflow, memory_system)

    # Run evaluation
    model_id = next(iter(initialized_models.keys()))
    results = evaluator.run_evaluation(
        model_id=model_id,
        sequence_ids=sequence_ids,
        memory_enabled=True
    )

    # Save results
    output_file = "results_faiss_baseline.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"FAISS baseline results saved to: {output_file}")
    return results


def run_v7_memory(sequence_ids=None, num_tasks_per_seq=None):
    '''Run evaluation with V7 memory system'''
    logger.info("="*70)
    logger.info("RUNNING V7: Task-Context Aware Memory System")
    logger.info("="*70)

    # Import V7 evaluation script
    sys.path.insert(0, str(Path(__file__).parent))
    from eval_procedure_v7 import (
        swe_bench_cl, agent_workflow, memory_system,
        SWEAgentCLEvaluator, initialized_models
    )

    if not memory_system:
        logger.error("V7 memory system not initialized!")
        return None

    evaluator = SWEAgentCLEvaluator(swe_bench_cl, agent_workflow, memory_system)

    # Run evaluation
    model_id = next(iter(initialized_models.keys()))
    results = evaluator.run_evaluation(
        model_id=model_id,
        sequence_ids=sequence_ids,
        memory_enabled=True
    )

    # Save results
    output_file = "results_v7_memory.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"V7 memory results saved to: {output_file}")
    return results


def compare_results(faiss_results, v7_results):
    '''Compare FAISS vs V7 results'''
    print("\\n" + "="*70)
    print("COMPARISON: FAISS vs V7")
    print("="*70 + "\\n")

    # TODO: Extract and compare metrics
    # - Success rate
    # - Forgetting rate
    # - Tool use efficiency
    # - Memory efficiency

    print("Results saved:")
    print("  FAISS: results_faiss_baseline.json")
    print("  V7:    results_v7_memory.json")
    print("\\nUse analysis scripts to compute detailed metrics.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sequence", type=str, help="Specific sequence to run")
    parser.add_argument("--pilot", type=int, help="Run pilot with N tasks per sequence")
    parser.add_argument("--faiss-only", action="store_true", help="Run FAISS only")
    parser.add_argument("--v7-only", action="store_true", help="Run V7 only")
    args = parser.parse_args()

    sequence_ids = [args.sequence] if args.sequence else None

    # Run FAISS baseline
    if not args.v7_only:
        faiss_results = run_faiss_baseline(sequence_ids=sequence_ids)

    # Run V7
    if not args.faiss_only:
        v7_results = run_v7_memory(sequence_ids=sequence_ids)

    # Compare
    if not args.faiss_only and not args.v7_only:
        compare_results(faiss_results, v7_results)
"""

    with open(runner_script, 'w') as f:
        f.write(runner_content)

    runner_script.chmod(0o755)
    logger.info(f"Created comparison runner: {runner_script}")
    return runner_script


def main():
    parser = argparse.ArgumentParser(description="Run SWE-Bench-CL: FAISS vs V7")
    parser.add_argument("--full", action="store_true", help="Run full dataset (273 tasks)")
    parser.add_argument("--pilot", type=int, help="Run pilot with N tasks")
    parser.add_argument("--sequence", type=str, help="Specific sequence (e.g., django/django)")
    parser.add_argument("--setup-only", action="store_true", help="Just create modified scripts")

    args = parser.parse_args()

    print("="*70)
    print("SWE-Bench-CL Comparison: FAISS vs V7 Memory")
    print("="*70)
    print()

    # Step 1: Create modified V7 evaluation script
    print("[1/3] Creating V7-modified evaluation script...")
    v7_script = modify_eval_script_for_v7()
    print(f"✓ Created: {v7_script}")

    # Step 2: Create comparison runner
    print("\n[2/3] Creating comparison runner...")
    runner = create_comparison_runner()
    print(f"✓ Created: {runner}")

    if args.setup_only:
        print("\n✓ Setup complete! Scripts created but not executed.")
        print("\nTo run comparison:")
        print(f"  cd agents-never-forget/eval_v3_swe-agent")
        print(f"  python3 run_comparison.py")
        return

    # Step 3: Run comparison
    print("\n[3/3] Running evaluation...")
    print("\n⚠️  IMPORTANT: This requires:")
    print("  - API keys set in .env (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
    print("  - Ollama running with nomic-embed-text model")
    print("  - Significant compute time (hours for full dataset)")
    print()
    response = input("Continue? [y/N]: ")

    if response.lower() != 'y':
        print("Aborted. Run with --setup-only to just create scripts.")
        return

    # TODO: Actually execute the comparison runner
    print("\nExecution not yet implemented. Please run manually:")
    print(f"  cd agents-never-forget/eval_v3_swe-agent")
    print(f"  python3 run_comparison.py")


if __name__ == "__main__":
    main()
