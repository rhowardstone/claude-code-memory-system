#!/bin/bash
# Claude Code Memory System V7 - Installation Script
# Installs memory hooks and updates settings without overwriting existing config

set -e

echo "========================================================================="
echo "Claude Code Memory System V7 - Installer"
echo "========================================================================="
echo ""
echo "This will install:"
echo "  • Memory extraction with FULL transcripts (PreCompact)"
echo "  • Task-context aware memory injection (SessionStart)"
echo "  • Knowledge graph with entity extraction"
echo "  • Smart importance scoring and adaptive K retrieval"
echo "  • Vector database with nomic-embed (768d, 8k token context)"
echo "  • CLI tools for browsing and searching memories"
echo "  • Centralized version tracking (__version__.py)"
echo ""

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found"
    exit 1
fi

# Check Python version (need 3.8+)
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python 3.8+ required, found $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION found"
echo ""

# Determine installation directory
INSTALL_DIR="$HOME/.claude/memory-hooks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create installation directory
echo "📁 Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Copy hooks - V7 complete system
echo "📋 Installing hooks..."
cp "$SCRIPT_DIR/hooks/__version__.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/precompact_memory_extractor.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/sessionstart_memory_injector.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/entity_extractor.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/knowledge_graph.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/task_context_scorer.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/query_memories.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/memory_scorer.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/multimodal_extractor.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/memory_pruner.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/memory_clustering.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/hooks/requirements.txt" "$INSTALL_DIR/"

# Make scripts executable
chmod +x "$INSTALL_DIR"/*.py

echo "✓ Hooks installed to $INSTALL_DIR"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
echo "   (This may take a few minutes for first-time install)"
python3 -m pip install --user -r "$INSTALL_DIR/requirements.txt" --quiet

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed"
else
    echo "⚠️  Warning: Some dependencies may have failed to install"
    echo "   You can manually install with: pip install -r $INSTALL_DIR/requirements.txt"
fi
echo ""

# Install additional requirements for nomic-embed
echo "📦 Installing nomic-embed dependencies..."
python3 -m pip install --user einops --quiet
if [ $? -eq 0 ]; then
    echo "✓ Nomic-embed dependencies installed"
fi
echo ""

# Update Claude Code settings
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "⚙️  Updating Claude Code settings..."

if [ ! -f "$SETTINGS_FILE" ]; then
    echo "Creating new settings.json..."
    cat > "$SETTINGS_FILE" << 'EOF'
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/memory-hooks/precompact_memory_extractor.py"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact|resume|startup",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/memory-hooks/sessionstart_memory_injector.py"
          }
        ]
      }
    ]
  }
}
EOF
    echo "✓ Created settings.json with memory hooks (V7)"
else
    echo "Updating existing settings.json..."

    # Use Python to safely merge hooks into existing settings
    python3 << 'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path.home() / ".claude" / "settings.json"

try:
    with open(settings_path) as f:
        settings = json.load(f)
except json.JSONDecodeError:
    print("❌ Error: settings.json exists but is not valid JSON")
    sys.exit(1)

# Add or update hooks
if "hooks" not in settings:
    settings["hooks"] = {}

settings["hooks"]["PreCompact"] = [
    {
        "hooks": [
            {
                "type": "command",
                "command": "python3 ~/.claude/memory-hooks/precompact_memory_extractor.py"
            }
        ]
    }
]

settings["hooks"]["SessionStart"] = [
    {
        "matcher": "compact|resume|startup",
        "hooks": [
            {
                "type": "command",
                "command": "python3 ~/.claude/memory-hooks/sessionstart_memory_injector.py"
            }
        ]
    }
]

# Write back
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)

print("✓ Settings updated successfully (V7)")
PYEOF

    if [ $? -ne 0 ]; then
        echo "⚠️  Warning: Could not automatically update settings.json"
        echo "   Please manually add the hooks configuration (see docs/INSTALLATION.md)"
    fi
fi

echo ""
echo "========================================================================="
echo "✅ Installation Complete - V7 with Contextual Embeddings + Last Actions!"
echo "========================================================================="
echo ""
echo "Memory system installed successfully!"
echo ""
echo "📊 What's been installed:"
echo "  • PreCompact: Extracts FULL transcripts + last actions before compaction"
echo "  • SessionStart: Shows 'Where You Left Off' + task-context aware retrieval"
echo "  • Entity extraction: FILES, FUNCTIONS, BUGS, FEATURES, etc."
echo "  • Knowledge graph: NetworkX with PageRank centrality"
echo "  • Task-context scoring: Boosts memories relevant to current work"
echo "  • Adaptive K retrieval: Returns 0-20 memories based on quality"
echo "  • Vector database: ChromaDB with HNSW indexing"
echo "  • Embeddings: nomic-embed-text-v1.5 (768d, 8192 token context)"
echo "  • Smart chunking: Intent-Action-Outcome structure"
echo "  • Importance scoring: 10+ signals (decisions, fixes, learnings)"
echo "  • Multi-modal artifacts: code, files, errors, architecture"
echo "  • Auto-pruning: age, redundancy, capacity-based"
echo "  • Centralized versioning: All versions tracked in __version__.py"
echo ""
echo "🚀 Next steps:"
echo "  1. Continue using Claude Code normally"
echo "  2. When compaction triggers, memories will be automatically extracted"
echo "  3. After compaction, task-relevant memories will be injected"
echo ""
echo "🔍 Query your memories anytime:"
echo "  python3 ~/.claude/memory-hooks/query_memories.py --stats"
echo "  python3 ~/.claude/memory-hooks/query_memories.py --topic \"bugs fixes\""
echo "  python3 ~/.claude/memory-hooks/query_memories.py --keywords error crash"
echo "  python3 ~/.claude/memory-hooks/query_memories.py --files-involved"
echo ""
echo "📚 Documentation: $SCRIPT_DIR/docs/"
echo "🐛 Debug log: ~/.claude/memory_hooks_debug.log"
echo "💾 Memory database: ~/.claude/memory_db/"
echo ""
echo "For detailed usage instructions, see: $SCRIPT_DIR/README.md"
echo ""
