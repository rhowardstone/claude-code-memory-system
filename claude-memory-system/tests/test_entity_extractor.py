#!/usr/bin/env python3
"""
Unit tests for entity_extractor.py
===================================
Tests entity extraction, relationship detection, and deduplication logic.

Target: 80%+ coverage for entity extraction system.
"""

import pytest
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from entity_extractor import (
    Entity,
    Relationship,
    EntityExtractor,
    extract_entities_from_memory
)


class TestEntityExtraction:
    """Test the main extract_entities function."""

    def test_extract_empty_text(self):
        """Empty text returns empty list"""
        entities = EntityExtractor.extract_entities("")
        assert entities == []

    def test_extract_multiple_entity_types(self):
        """Text with multiple entity types extracts all"""
        text = """
        We modified auth.py to fix TypeError: missing token.
        Created UserAuth class with validate() function.
        Using ChromaDB for storage. Decided to: use JWT tokens for authentication.
        """
        entities = EntityExtractor.extract_entities(text)

        types = {e.entity_type for e in entities}
        assert "FILE" in types
        assert "FUNCTION" in types
        assert "CLASS" in types
        assert "BUG" in types
        assert "TOOL" in types
        assert "DECISION" in types

    def test_entity_has_context(self):
        """Extracted entities include surrounding context"""
        text = "We modified auth.py to add validation logic"
        entities = EntityExtractor.extract_entities(text)

        file_entities = [e for e in entities if e.entity_type == "FILE"]
        assert len(file_entities) > 0
        assert "modified" in file_entities[0].context
        assert "validation" in file_entities[0].context

    def test_entity_has_confidence(self):
        """All entities have confidence scores"""
        text = "Created utils.py with helper() function using NetworkX"
        entities = EntityExtractor.extract_entities(text)

        for entity in entities:
            assert hasattr(entity, "confidence")
            assert 0.0 <= entity.confidence <= 1.0


class TestFileEntityExtraction:
    """Test FILE entity extraction with various patterns."""

    def test_backtick_python_file(self):
        """Backtick Python files: `auth.py`"""
        text = "Modified `auth.py` to add validation"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 1
        assert any("auth.py" in f.name for f in files)

    def test_plain_python_file(self):
        """Plain Python files: auth.py"""
        text = "Modified auth.py to add validation"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 1
        assert any("auth.py" in f.name for f in files)

    def test_absolute_path(self):
        """Absolute paths: /home/user/auth.py"""
        text = "Modified /home/user/project/auth.py"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 1
        assert any("auth.py" in f.name for f in files)

    def test_relative_path(self):
        """Relative paths: src/utils/auth.py"""
        text = "Modified src/utils/auth.py"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 1
        assert any("auth.py" in f.name for f in files)

    def test_tilde_path(self):
        """Tilde paths: ~/.config/settings.json"""
        text = "Read ~/.config/settings.json"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 1
        assert any("settings.json" in f.name for f in files)

    def test_javascript_files(self):
        """JavaScript files: app.js, index.jsx"""
        text = "Modified app.js and index.jsx"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 2
        names = [f.name for f in files]
        assert any("app.js" in n for n in names)
        assert any("index.jsx" in n for n in names)

    def test_typescript_files(self):
        """TypeScript files: auth.ts, components.tsx"""
        text = "Created auth.ts and components.tsx"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 2

    def test_config_files(self):
        """Config files: config.json, settings.yaml, .env"""
        text = "Modified config.json and settings.yaml files"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 2

    def test_markdown_files(self):
        """Markdown files: README.md"""
        text = "Updated README.md documentation"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert any("README.md" in f.name for f in files)

    def test_compiled_language_files(self):
        """C++/Java files: main.cpp, App.java"""
        text = "Modified main.cpp and App.java"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert len(files) >= 2

    def test_file_with_hyphens(self):
        """Files with hyphens: test-utils.py"""
        text = "Created test-utils.py"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert any("test-utils.py" in f.name for f in files)

    def test_file_with_underscores(self):
        """Files with underscores: entity_extractor.py"""
        text = "Modified entity_extractor.py"
        entities = EntityExtractor.extract_entities(text)

        files = [e for e in entities if e.entity_type == "FILE"]
        assert any("entity_extractor.py" in f.name for f in files)


class TestFunctionEntityExtraction:
    """Test FUNCTION entity extraction."""

    def test_backtick_function(self):
        """Backtick functions: `validate()`"""
        text = "Called `validate()` to check tokens"
        entities = EntityExtractor.extract_entities(text)

        funcs = [e for e in entities if e.entity_type == "FUNCTION"]
        assert len(funcs) >= 1
        assert any("validate" in f.name for f in funcs)

    def test_python_def(self):
        """Python def: def authenticate(user)"""
        text = "Created def authenticate(user) to handle login"
        entities = EntityExtractor.extract_entities(text)

        funcs = [e for e in entities if e.entity_type == "FUNCTION"]
        assert any("authenticate" in f.name for f in funcs)

    def test_javascript_function(self):
        """JavaScript function: function login()"""
        text = "Added function login() for authentication"
        entities = EntityExtractor.extract_entities(text)

        funcs = [e for e in entities if e.entity_type == "FUNCTION"]
        assert any("login" in f.name for f in funcs)


class TestBugEntityExtraction:
    """Test BUG entity extraction."""

    def test_type_error(self):
        """TypeError: message"""
        text = "Hit TypeError: 'NoneType' object is not subscriptable"
        entities = EntityExtractor.extract_entities(text)

        bugs = [e for e in entities if e.entity_type == "BUG"]
        assert len(bugs) >= 1
        assert "TypeError" in bugs[0].name

    def test_value_error(self):
        """ValueError: message"""
        text = "Encountered ValueError: invalid literal for int()"
        entities = EntityExtractor.extract_entities(text)

        bugs = [e for e in entities if e.entity_type == "BUG"]
        assert any("ValueError" in b.name for b in bugs)


class TestEntityDeduplication:
    """Test entity deduplication logic."""

    def test_dedupe_identical_entities(self):
        """Identical entities (type + name) are deduped"""
        entities = [
            Entity("FILE", "auth.py", "context1", 0.9),
            Entity("FILE", "auth.py", "context2", 0.9),
            Entity("FILE", "auth.py", "context3", 0.9),
        ]

        unique = EntityExtractor.deduplicate_entities(entities)
        assert len(unique) == 1
        assert unique[0].name == "auth.py"

    def test_dedupe_case_insensitive(self):
        """Deduplication is case-insensitive for names"""
        entities = [
            Entity("FUNCTION", "validate", "context1", 0.8),
            Entity("FUNCTION", "Validate", "context2", 0.8),
            Entity("FUNCTION", "VALIDATE", "context3", 0.8),
        ]

        unique = EntityExtractor.deduplicate_entities(entities)
        assert len(unique) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/entity_extractor", "--cov-report=term-missing"])
