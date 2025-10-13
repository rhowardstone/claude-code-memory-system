#!/bin/bash
# Verification script - Check if memory system is properly installed and working

echo "========================================================================="
echo "Claude Code Memory System - Verification"
echo "========================================================================="
echo ""

PASS=0
FAIL=0

check_pass() {
    echo "✓ $1"
    ((PASS++))
}

check_fail() {
    echo "✗ $1"
    ((FAIL++))
}

# Check Python
echo "Checking prerequisites..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    check_pass "Python 3 found (version $PYTHON_VERSION)"
else
    check_fail "Python 3 not found"
fi
echo ""

# Check installation directory
echo "Checking installation..."
if [ -d "$HOME/.claude/memory-hooks" ]; then
    check_pass "Installation directory exists"

    # Check hook files (V5)
    REQUIRED_FILES=(
        "precompact_memory_extractor_v2.py"
        "sessionstart_memory_injector_v5.py"
        "entity_extractor.py"
        "knowledge_graph.py"
        "task_context_scorer.py"
        "query_memories.py"
        "memory_scorer.py"
        "multimodal_extractor.py"
        "memory_pruner.py"
        "memory_clustering.py"
        "requirements.txt"
    )

    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$HOME/.claude/memory-hooks/$file" ]; then
            check_pass "Hook file: $file"
        else
            check_fail "Missing file: $file"
        fi
    done
else
    check_fail "Installation directory not found"
fi
echo ""

# Check Python dependencies
echo "Checking Python dependencies..."
# Map package names to import names
declare -A DEPS=(
    ["chromadb"]="chromadb"
    ["sentence-transformers"]="sentence_transformers"
    ["jsonlines"]="jsonlines"
    ["scikit-learn"]="sklearn"
    ["scipy"]="scipy"
    ["numpy"]="numpy"
)
for pkg in "${!DEPS[@]}"; do
    import="${DEPS[$pkg]}"
    if python3 -c "import $import" 2>/dev/null; then
        check_pass "Dependency: $pkg"
    else
        check_fail "Missing dependency: $pkg"
    fi
done
echo ""

# Check settings.json
echo "Checking Claude Code configuration..."
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    check_pass "settings.json exists"

    # Check if hooks are configured
    if grep -q "PreCompact" "$SETTINGS" && grep -q "SessionStart" "$SETTINGS"; then
        check_pass "Hooks configured in settings.json"
    else
        check_fail "Hooks not found in settings.json"
    fi
else
    check_fail "settings.json not found"
fi
echo ""

# Check query tool
echo "Checking CLI tools..."
if python3 "$HOME/.claude/memory-hooks/query_memories.py" --help &>/dev/null; then
    check_pass "Query tool working"
else
    check_fail "Query tool not working"
fi
echo ""

# Check memory database
echo "Checking memory database..."
if [ -d "$HOME/.claude/memory_db" ]; then
    check_pass "Memory database directory exists"

    # Check if there are any memories
    MEMORY_COUNT=$(python3 -c "
import chromadb
try:
    client = chromadb.PersistentClient(path='$HOME/.claude/memory_db')
    collection = client.get_collection('conversation_memories')
    print(collection.count())
except:
    print(0)
" 2>/dev/null)

    if [ -n "$MEMORY_COUNT" ] && [ "$MEMORY_COUNT" -gt 0 ]; then
        check_pass "Memory database contains $MEMORY_COUNT memories"
    else
        echo "  ℹ  Memory database is empty (expected if no compactions yet)"
    fi
else
    echo "  ℹ  Memory database will be created on first compaction"
fi
echo ""

# Summary
echo "========================================================================="
echo "Verification Complete"
echo "========================================================================="
echo ""
echo "Results: $PASS passed, $FAIL failed"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ All checks passed! Memory System V5 is properly installed."
    echo ""
    echo "Next steps:"
    echo "  1. Use Claude Code normally"
    echo "  2. When compaction triggers, memories will be automatically extracted"
    echo "  3. Use CLI tools to browse: python3 ~/.claude/memory-hooks/query_memories.py --help"
    echo "  4. V5 features include knowledge graph and task-context aware retrieval!"
    exit 0
else
    echo "⚠️  Some checks failed. Please review the issues above."
    echo ""
    echo "Common fixes:"
    echo "  • Missing files: Run ./install.sh again"
    echo "  • Missing dependencies: pip install -r ~/.claude/memory-hooks/requirements.txt"
    echo "  • Missing hooks config: Manually add hooks to ~/.claude/settings.json"
    echo ""
    echo "For help, see: docs/INSTALLATION.md"
    exit 1
fi
