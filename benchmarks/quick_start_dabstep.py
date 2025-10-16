#!/usr/bin/env python3
"""
Quick Start Script for DABstep (Data Agent Benchmark for Multi-step Reasoning)

This is the EASIEST benchmark to get started with - just 3 lines of code!

DABstep tests multi-step reasoning across 450+ real-world data analysis tasks.
None of the tasks can be solved with single-shot code, forcing multi-turn interaction.

Usage:
    python quick_start_dabstep.py [--dev]

Options:
    --dev    Use the dev split (10 tasks) instead of default (450 tasks)
"""

import sys
from datasets import load_dataset

def main():
    # Determine which split to use
    split = "dev" if "--dev" in sys.argv else "default"

    print("=" * 60)
    print("DABstep Quick Start")
    print("Data Agent Benchmark for Multi-step Reasoning")
    print("=" * 60)
    print()
    print(f"Loading dataset (split: {split})...")
    print("This may take a moment on first run (downloads ~730 MB)...")
    print()

    # Load the dataset (this is it - 3 lines!)
    ds = load_dataset("adyen/DABstep", name="tasks", split=split)

    print(f"✅ Dataset loaded: {len(ds)} tasks")
    print()
    print("=" * 60)
    print("Dataset Structure")
    print("=" * 60)
    print()

    # Show first task as example
    if len(ds) > 0:
        first_task = ds[0]
        print("Example task (first in dataset):")
        print()
        print(f"Task ID: {first_task.get('task_id', 'N/A')}")
        print(f"Difficulty: {first_task.get('difficulty', 'N/A')}")
        print()
        print("Question:")
        print("-" * 60)
        question = first_task.get('question', 'N/A')
        print(question[:500] + "..." if len(question) > 500 else question)
        print("-" * 60)
        print()

        if 'answer' in first_task:
            answer = first_task['answer']
            print("Answer:")
            print("-" * 60)
            print(answer[:200] + "..." if len(answer) > 200 else answer)
            print("-" * 60)
            print()

    print("=" * 60)
    print("Dataset Statistics")
    print("=" * 60)
    print()
    print(f"Total tasks: {len(ds)}")
    print(f"Dataset size: ~730 MB (Parquet)")
    print(f"Source: Adyen's real-world financial analytics tasks")
    print()

    # Show difficulty distribution if available
    if len(ds) > 0 and 'difficulty' in ds[0]:
        difficulties = {}
        for task in ds:
            diff = task.get('difficulty', 'unknown')
            difficulties[diff] = difficulties.get(diff, 0) + 1

        print("Difficulty distribution:")
        for diff, count in sorted(difficulties.items()):
            print(f"  {diff}: {count} tasks")
        print()

    print("=" * 60)
    print("Next Steps")
    print("=" * 60)
    print()
    print("1. Iterate through tasks and solve with your memory system:")
    print()
    print("   from datasets import load_dataset")
    print("   ds = load_dataset('adyen/DABstep', name='tasks', split='default')")
    print()
    print("   for task in ds:")
    print("       question = task['question']")
    print("       # Your memory-enabled agent solves the task")
    print("       answer = your_agent.solve(question)")
    print("       # Compare with ground truth")
    print("       correct = (answer == task['answer'])")
    print()
    print("2. Track metrics:")
    print("   • Success rate (% correct answers)")
    print("   • Steps to completion (multi-turn efficiency)")
    print("   • Memory retrieval accuracy")
    print()
    print("3. Compare baselines:")
    print("   • No memory (fresh agent each task)")
    print("   • V6 memory system")
    print("   • V7 contextual embeddings")
    print()
    print("4. Submit to leaderboard:")
    print("   https://huggingface.co/spaces/adyen/DABstep")
    print()
    print("Performance baseline:")
    print("  Best reasoning agents: 14-16% accuracy (very challenging!)")
    print()
    print("=" * 60)
    print("Resources")
    print("=" * 60)
    print()
    print("Dataset: https://huggingface.co/datasets/adyen/dabstep")
    print("Paper:   https://arxiv.org/abs/2506.23719")
    print("Colab:   https://colab.research.google.com/drive/1pXi5ffBFNJQ5nn1111SnIfjfKCOlunxu")
    print()
    print("=" * 60)

    return ds

if __name__ == "__main__":
    try:
        dataset = main()
        print()
        print("✅ Setup complete! Dataset is ready to use.")
        print()
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print()
        print("Make sure you have the datasets library installed:")
        print("  pip install datasets")
        print()
        sys.exit(1)
