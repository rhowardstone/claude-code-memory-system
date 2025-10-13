# Installation Guide

Complete installation instructions for the Claude Code Memory System V5.

---

## Automatic Installation (Recommended)

```bash
git clone https://github.com/rhowardstone/claude-code-memory-system.git
cd claude-code-memory-system
./install.sh
```

The install script will:
1. Copy hooks to `~/.claude/memory-hooks/`
2. Install Python dependencies
3. Safely merge hooks into `~/.claude/settings.json`
4. Create necessary directories

---

## Manual Installation

### 1. Prerequisites

Ensure you have:
- Python 3.8 or higher
- pip (Python package manager)
- Claude Code CLI installed

Verify Python version:
```bash
python3 --version
```

### 2. Create Installation Directory

```bash
mkdir -p ~/.claude/memory-hooks
```

### 3. Copy Hook Files

```bash
cp hooks/*.py ~/.claude/memory-hooks/
cp hooks/requirements.txt ~/.claude/memory-hooks/
chmod +x ~/.claude/memory-hooks/*.py
```

### 4. Install Dependencies

```bash
pip install -r ~/.claude/memory-hooks/requirements.txt
```

Required packages:
- `chromadb>=0.4.0` - Vector database
- `sentence-transformers>=2.2.0` - Local embeddings
- `jsonlines>=3.0.0` - JSONL parsing
- `scikit-learn>=1.3.0` - Clustering
- `scipy>=1.11.0` - Scientific computing
- `numpy>=1.24.0` - Numerical operations

### 5. Configure Claude Code Settings

Edit `~/.claude/settings.json` to add hooks:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/memory-hooks/precompact_memory_extractor_v2.py"
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
            "command": "python3 ~/.claude/memory-hooks/sessionstart_memory_injector_v5.py"
          }
        ]
      }
    ]
  }
}
```

**Important**: If you already have hooks configured, merge carefully! The hooks field should be an object containing arrays.

### 6. Verify Installation

Check that hooks are recognized:

```bash
# This should not show any validation errors
claude
```

Check that memory query tool works:

```bash
python3 ~/.claude/memory-hooks/query_memories.py --stats
```

Expected output (if no memories yet):
```
{
  "total": 0,
  ...
}
```

---

## Upgrading

To upgrade to a new version:

```bash
cd claude-code-memory-system
git pull
./install.sh
```

The install script safely overwrites hook files while preserving your settings.json.

---

## Uninstallation

To completely remove the memory system:

```bash
# Remove hooks directory
rm -rf ~/.claude/memory-hooks

# Remove memory database
rm -rf ~/.claude/memory_db

# Remove debug log
rm ~/.claude/memory_hooks_debug.log

# Remove hooks from settings.json
# Edit ~/.claude/settings.json and remove the "hooks" section
```

---

## Platform-Specific Notes

### macOS

If you encounter permission issues:

```bash
# Grant full disk access to Terminal in System Preferences
# Security & Privacy → Privacy → Full Disk Access
```

### Linux

Ensure Python 3 is the default:

```bash
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3 1
```

### Windows (WSL)

Install in WSL (Windows Subsystem for Linux):

```bash
# Ensure WSL is set up
wsl --install

# Run installation in WSL
./install.sh
```

---

## Troubleshooting Installation

### Python Dependencies Fail

If pip install fails:

```bash
# Try with user flag
pip install --user -r ~/.claude/memory-hooks/requirements.txt

# Or use pip3 explicitly
pip3 install -r ~/.claude/memory-hooks/requirements.txt

# Update pip first
python3 -m pip install --upgrade pip
```

### Settings.json Validation Error

If Claude Code shows a settings error:

```bash
# Validate JSON syntax
python3 -m json.tool ~/.claude/settings.json

# If invalid, backup and start fresh
cp ~/.claude/settings.json ~/.claude/settings.json.backup
```

Then manually edit settings.json with correct hook format.

### Permission Denied

If scripts can't execute:

```bash
chmod +x ~/.claude/memory-hooks/*.py
```

### Module Not Found

If you get "ModuleNotFoundError":

```bash
# Ensure correct Python is used
which python3

# Check installed packages
pip list | grep -E "chromadb|sentence-transformers|jsonlines"

# Reinstall if missing
pip install chromadb sentence-transformers jsonlines
```

---

## Verifying Installation

After installation, verify everything works:

### 1. Check Hook Configuration

```bash
cat ~/.claude/settings.json | python3 -m json.tool | grep -A 10 hooks
```

Should show PreCompact and SessionStart hooks.

### 2. Test Memory Query Tool

```bash
python3 ~/.claude/memory-hooks/query_memories.py --help
```

Should show available query options.

### 3. Check Dependencies

```bash
python3 << EOF
try:
    import chromadb
    import sentence_transformers
    import jsonlines
    print("✓ All dependencies installed")
except ImportError as e:
    print(f"✗ Missing: {e}")
EOF
```

### 4. Run Test Session

Start a new Claude session and trigger compaction manually:

```bash
# In a Claude session
/compact
```

Check debug log:

```bash
tail ~/.claude/memory_hooks_debug.log
```

Should see "PreCompact-V2 triggered" messages.

---

## Next Steps

After successful installation:

1. **Read the Usage Guide**: See [USAGE.md](USAGE.md) for detailed usage instructions
2. **Explore CLI Tools**: Try `query_memories.py` commands (--stats, --topic, --keywords)
3. **Customize Configuration**: Adjust scoring/pruning thresholds in hook files
4. **Start Using**: Just use Claude Code normally - memories will be preserved automatically!

---

## Getting Help

If installation issues persist:

1. Check debug log: `tail ~/.claude/memory_hooks_debug.log`
2. File an issue: [GitHub Issues](https://github.com/rhowardstone/claude-code-memory-system/issues)
3. Include:
   - OS and Python version
   - Error messages
   - Debug log excerpt
   - Output of `pip list | grep -E "chromadb|sentence|einops"`
