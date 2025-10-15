# Contributing to Claude Code Memory System

Thank you for your interest in contributing! This project aims to make Claude Code conversations more continuous and productive.

---

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check existing [GitHub Issues](https://github.com/rhowardstone/claude-code-memory-system/issues)
2. If not found, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment (OS, Python version, Claude Code version)
   - Debug log excerpt if relevant

### Suggesting Features

Feature requests are welcome! Please:

1. Explain the use case
2. Describe the proposed solution
3. Consider alternatives
4. Discuss potential drawbacks

### Code Contributions

We welcome pull requests! Please:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Write/update tests** if applicable
5. **Update documentation** if needed
6. **Commit with clear messages**: `git commit -m "Add amazing feature"`
7. **Push to your fork**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

---

## Development Setup

### Clone and Install

```bash
# Clone your fork
git clone https://github.com/rhowardstone/claude-code-memory-system.git
cd claude-memory-system

# Install dependencies
pip install -r hooks/requirements.txt

# Install in development mode (if using setuptools)
pip install -e .
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=hooks tests/

# Run specific test
pytest tests/test_memory_scorer.py -v
```

### Code Style

We follow PEP 8 with some flexibility:

```bash
# Format code
black hooks/

# Check linting
flake8 hooks/

# Type checking
mypy hooks/
```

### Testing Your Changes

1. **Unit tests**: Add tests for new functionality
2. **Integration tests**: Test with real Claude Code sessions
3. **Manual testing**: Run install.sh and verify hooks work

### Debug During Development

```bash
# Enable verbose logging
export MEMORY_DEBUG=1

# Watch debug log
tail -f ~/.claude/memory_hooks_debug.log

# Test individual components
python3 hooks/memory_scorer.py
python3 hooks/memory_clustering.py
```

---

## Project Structure

```
claude-code-memory-system/
├── hooks/                      # Core hook implementations
│   ├── __version__.py
│   ├── precompact_memory_extractor.py
│   ├── sessionstart_memory_injector.py
│   ├── memory_scorer.py
│   ├── multimodal_extractor.py
│   ├── memory_pruner.py
│   ├── memory_clustering.py
│   ├── query_memories.py
│   └── requirements.txt
├── docs/                       # Documentation
│   ├── INSTALLATION.md
│   ├── USAGE.md
│   └── ARCHITECTURE.md
├── examples/                   # Example outputs and usage
├── tests/                      # Test suite
├── install.sh                  # Installation script
├── README.md                   # Main documentation
├── LICENSE                     # MIT License
└── CONTRIBUTING.md            # This file
```

---

## Areas for Contribution

### High Priority

- [ ] Cross-platform testing (Windows, macOS, Linux)
- [ ] Performance optimization for large conversations
- [ ] Better error handling and recovery
- [ ] More comprehensive test suite
- [ ] Documentation improvements

### Medium Priority

- [ ] Memory visualization dashboard
- [ ] Custom scoring rules via config file
- [ ] Export to different formats (Markdown, HTML)
- [ ] Integration with external knowledge bases
- [ ] Memory compression for old data

### Nice to Have

- [ ] Multi-language support for code artifacts
- [ ] Collaborative memory sharing (team features)
- [ ] Memory analytics and insights
- [ ] Web UI for memory browsing
- [ ] Plugin system for custom extractors

---

## Coding Guidelines

### Python Style

- Follow PEP 8
- Use type hints where practical
- Write docstrings for public functions
- Keep functions focused and small
- Prefer clarity over cleverness

### Naming Conventions

- `snake_case` for functions and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Descriptive names over abbreviations

### Error Handling

- Use specific exception types
- Log errors to debug log
- Provide helpful error messages
- Don't silence exceptions without good reason

### Comments

- Explain **why**, not **what**
- Update comments when code changes
- Use inline comments sparingly
- Prefer self-documenting code

### Testing

- Write tests for new features
- Maintain test coverage >80%
- Test edge cases and error paths
- Use descriptive test names

---

## Pull Request Process

1. **Update documentation** if you've changed functionality
2. **Add tests** for new code
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** with your changes
5. **Request review** from maintainers

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] Commits are clear and atomic

---

## Code Review Process

All submissions require review before merging:

1. **Automated checks** must pass (tests, linting)
2. **Maintainer review** for code quality and design
3. **Discussion** if changes needed
4. **Approval** and merge

Reviews typically take 1-3 days. Please be patient!

---

## Community Guidelines

### Be Respectful

- Be kind and courteous
- Accept constructive criticism
- Focus on what's best for the project
- Welcome newcomers

### Be Collaborative

- Share knowledge and help others
- Give credit where it's due
- Ask for help when needed
- Celebrate successes together

### Be Professional

- Stick to technical discussions
- No personal attacks or harassment
- Respect different viewpoints
- Keep discussions on-topic

---

## Getting Help

Need help contributing?

- **Documentation**: Read [docs/](docs/)
- **Issues**: Ask in an issue or discussion
- **Chat**: [GitHub Discussions](https://github.com/rhowardstone/claude-code-memory-system/discussions)
- **Email**: [your-email@example.com]

---

## Recognition

Contributors are recognized in:
- README.md contributors section
- CHANGELOG.md for each release
- GitHub contributors page

Significant contributions may lead to maintainer status!

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making Claude Code Memory System better! 🙏
