#!/usr/bin/env python3
"""
Download and explore LongMemEval benchmark dataset.

This script downloads the LongMemEval dataset and examines its structure
to understand how to adapt it for our memory system testing.
"""

from datasets import load_dataset
import json

print("Downloading LongMemEval dataset...")
print("This may take a few minutes for the first download...")

# Try different approaches to load the dataset
try:
    # Try without trust_remote_code
    dataset = load_dataset("xiaowu0162/LongMemEval", "LongMemEval_M")
except Exception as e:
    print(f"First attempt failed: {e}")
    print("\nTrying alternative configurations...")
    try:
        # Try default config
        dataset = load_dataset("xiaowu0162/LongMemEval")
    except Exception as e2:
        print(f"Second attempt failed: {e2}")
        # Try loading from GitHub release instead
        import urllib.request
        print("\nAttempting to download from GitHub releases...")
        url = "https://github.com/xiaowu0162/LongMemEval/releases/download/v1.0/longmemeval_m.jsonl"
        urllib.request.urlretrieve(url, "longmemeval_m.jsonl")
        print("Downloaded longmemeval_m.jsonl")
        # Load manually
        import pandas as pd
        data = []
        with open("longmemeval_m.jsonl", 'r') as f:
            for line in f:
                data.append(json.loads(line))
        dataset = {'test': data}
        print(f"Manually loaded {len(data)} examples")

print(f"\n✅ Dataset downloaded successfully!")
print(f"Dataset structure: {type(dataset)}")

# Examine the first example
print("\n" + "="*70)
print("First Example Structure:")
print("="*70)

# Handle both dict and dataset formats
if isinstance(dataset, dict):
    first_example = dataset['test'][0]
    total_examples = len(dataset['test'])
else:
    first_example = dataset['test'][0]
    total_examples = len(dataset['test'])

print(f"\nKeys: {first_example.keys() if hasattr(first_example, 'keys') else list(first_example.keys())}")

print(f"\n📝 Question ID: {first_example['question_id']}")
print(f"📋 Question: {first_example['question'][:200]}...")

if 'chat_history' in first_example:
    print(f"\n💬 Chat History Length: {len(first_example['chat_history'])} messages")
    print(f"First few messages:")
    for i, msg in enumerate(first_example['chat_history'][:3]):
        print(f"  {i+1}. {msg[:100]}...")

if 'answer' in first_example:
    print(f"\n✅ Answer: {first_example['answer'][:200]}...")

# Save sample to file for inspection
sample_file = "longmemeval_sample.json"
with open(sample_file, 'w') as f:
    json.dump(first_example, f, indent=2)

print(f"\n💾 Saved first example to: {sample_file}")

# Get statistics
print("\n" + "="*70)
print("Dataset Statistics:")
print("="*70)
print(f"Total examples: {total_examples}")

# Examine multiple examples to understand variety
print("\n" + "="*70)
print("Sample Questions:")
print("="*70)
test_data = dataset['test'] if isinstance(dataset, dict) else dataset['test']
for i in range(min(5, total_examples)):
    ex = test_data[i]
    print(f"\n{i+1}. ID: {ex['question_id']}")
    print(f"   Q: {ex['question'][:150]}...")

print("\n" + "="*70)
print("Next Steps:")
print("="*70)
print("1. Examine longmemeval_sample.json to understand data structure")
print("2. Create adapter to convert chat history → Claude Code sessions")
print("3. Run pilot test with 10 questions")
print("="*70)
