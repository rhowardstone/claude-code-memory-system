#!/bin/bash
#
# Quick Start Script for SWE-Bench-CL (Continual Learning for Coding Agents)
#
# This benchmark explicitly tests memory retention across coding sessions,
# making it perfect for evaluating our Claude Code memory system.
#
# Usage: ./quick_start_swe_bench_cl.sh
#

set -e  # Exit on error

echo "=================================================="
echo "SWE-Bench-CL Quick Start"
echo "Testing memory system across chronological coding tasks"
echo "=================================================="
echo ""

# Step 1: Clone repository
echo "[1/5] Cloning SWE-Bench-CL repository..."
if [ -d "agents-never-forget" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd agents-never-forget
    git pull
    cd ..
else
    git clone https://github.com/thomasjoshi/agents-never-forget.git
fi
cd agents-never-forget

# Step 2: Create virtual environment
echo ""
echo "[2/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Step 3: Install dependencies
echo ""
echo "[3/5] Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found. Installing common dependencies..."
    pip install langchain langgraph faiss-cpu openai anthropic python-dotenv
fi

# Step 4: Configuration
echo ""
echo "[4/5] Configuration setup..."
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# API Keys for LLM evaluation
# Uncomment and fill in the keys you need

# OpenAI (if testing with GPT models)
# OPENAI_API_KEY=your_key_here

# Anthropic (if testing with Claude models)
# ANTHROPIC_API_KEY=your_key_here

# Other settings
# MODEL_NAME=gpt-4
# TEMPERATURE=0.0
EOF
    echo "✅ Created .env file - PLEASE EDIT IT with your API keys!"
    echo "   Location: $(pwd)/.env"
else
    echo "✅ .env file already exists"
fi

# Step 5: Verify setup
echo ""
echo "[5/5] Verifying installation..."
python3 -c "import langchain, faiss" 2>/dev/null && echo "✅ Python dependencies OK" || echo "⚠️  Some dependencies missing"

# Final instructions
echo ""
echo "=================================================="
echo "✅ SWE-Bench-CL setup complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit the .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Explore the benchmark structure:"
echo "   ls -la"
echo "   cat README.md"
echo ""
echo "3. Run evaluation (check repo for exact command):"
echo "   cd eval_v3_swe-agent/"
echo "   python run_evaluation.py --memory-system YOUR_SYSTEM"
echo ""
echo "4. Compare against baselines:"
echo "   - Memory-disabled baseline"
echo "   - Memory-enabled (FAISS) baseline"
echo "   - Your V7 memory system"
echo ""
echo "Key metrics to track:"
echo "  • Average accuracy"
echo "  • Forgetting rate"
echo "  • Forward/backward transfer"
echo "  • Tool-use efficiency"
echo ""
echo "Dataset: 273 chronological tasks across 8 repositories"
echo "Repository: https://github.com/thomasjoshi/agents-never-forget"
echo "Paper: https://arxiv.org/abs/2507.00014"
echo ""
echo "=================================================="
