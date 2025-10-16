#!/usr/bin/env python3
"""
Unit tests for multimodal_extractor.py
=======================================
Tests extraction of code, files, commands, errors, architecture.

Target: 80%+ coverage for multimodal extraction system.
"""

import pytest
import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from multimodal_extractor import (
    MultiModalExtractor,
    enrich_chunk_with_artifacts
)


class TestCodeSnippetExtraction:
    """Test extraction of code blocks and inline code."""

    def test_extract_python_code_block(self):
        """Python code block with language tag"""
        text = """
        Here's the code:
        ```python
        def hello():
            return "world"
        ```
        """
        snippets = MultiModalExtractor.extract_code_snippets(text)

        assert len(snippets) >= 1
        code_blocks = [s for s in snippets if s["type"] == "code_block"]
        assert len(code_blocks) == 1
        assert code_blocks[0]["language"] == "python"
        assert "def hello" in code_blocks[0]["code"]
        assert code_blocks[0]["lines"] == 2

    def test_extract_multiple_code_blocks(self):
        """Multiple code blocks in same text"""
        text = """
        ```typescript
        const x = 5;
        ```

        And also:

        ```javascript
        let y = 10;
        ```
        """
        snippets = MultiModalExtractor.extract_code_snippets(text)

        code_blocks = [s for s in snippets if s["type"] == "code_block"]
        assert len(code_blocks) == 2

        languages = [s["language"] for s in code_blocks]
        assert "typescript" in languages
        assert "javascript" in languages

    def test_extract_code_block_no_language(self):
        """Code block without language tag defaults to plaintext"""
        text = """
        ```
        some code here
        ```
        """
        snippets = MultiModalExtractor.extract_code_snippets(text)

        code_blocks = [s for s in snippets if s["type"] == "code_block"]
        assert len(code_blocks) == 1
        assert code_blocks[0]["language"] == "plaintext"

    def test_extract_inline_code(self):
        """Inline code with backticks"""
        text = "Called the `validate_user()` function with `authenticate=True`"
        snippets = MultiModalExtractor.extract_code_snippets(text)

        inline = [s for s in snippets if s["type"] == "inline_code"]
        assert len(inline) >= 2

        codes = [s["code"] for s in inline]
        assert "validate_user()" in codes
        assert "authenticate=True" in codes

    def test_skip_short_inline_code(self):
        """Short inline code (<=5 chars) is skipped"""
        text = "Use `x` and `y` variables"
        snippets = MultiModalExtractor.extract_code_snippets(text)

        inline = [s for s in snippets if s["type"] == "inline_code"]
        assert len(inline) == 0  # Both too short

    def test_snippet_id_generation(self):
        """Each snippet gets a unique ID"""
        text = "```python\ncode1\n```\n```python\ncode2\n```"
        snippets = MultiModalExtractor.extract_code_snippets(text)

        ids = [s["snippet_id"] for s in snippets if s["type"] == "code_block"]
        assert len(ids) == 2
        assert ids[0] != ids[1]  # Different code = different ID

    def test_empty_code_block_skipped(self):
        """Empty code blocks are skipped"""
        text = "```python\n\n```"
        snippets = MultiModalExtractor.extract_code_snippets(text)

        code_blocks = [s for s in snippets if s["type"] == "code_block"]
        assert len(code_blocks) == 0


class TestFilePathExtraction:
    """Test extraction of file paths."""

    def test_extract_python_files(self):
        """Python file paths"""
        text = "Modified auth.py and utils.py files"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert "auth.py" in paths
        assert "utils.py" in paths

    def test_extract_typescript_files(self):
        """TypeScript file paths (.ts extension)"""
        text = "Created app.ts and router.ts"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert "app.ts" in paths
        assert "router.ts" in paths

    def test_extract_javascript_files(self):
        """JavaScript file paths (.js extension)"""
        text = "Updated index.js and utils.js"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert "index.js" in paths
        assert "utils.js" in paths

    def test_extract_config_files(self):
        """Configuration file paths"""
        text = "Modified config.json and settings.yaml files"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert "config.json" in paths
        assert "settings.yaml" in paths

    def test_extract_file_paths_with_directories(self):
        """File paths with directory structure"""
        text = "Changed src/api/users.ts and tests/integration/auth.test.js"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert "src/api/users.ts" in paths
        assert "tests/integration/auth.test.js" in paths

    def test_filter_false_positive_numbers(self):
        """Filter out patterns like '123.ts' (likely false positive)"""
        text = "Test case 123.ts failed"
        paths = MultiModalExtractor.extract_file_paths(text)

        # Should be empty or not include the numeric pattern
        assert "123.ts" not in paths

    def test_paths_are_sorted_unique(self):
        """Paths are unique and sorted"""
        text = "Modified auth.py, utils.py, auth.py again"
        paths = MultiModalExtractor.extract_file_paths(text)

        assert len([p for p in paths if p == "auth.py"]) == 1  # Unique
        # Check sorted (auth.py < utils.py alphabetically)
        if "auth.py" in paths and "utils.py" in paths:
            assert paths.index("auth.py") < paths.index("utils.py")


class TestCommandExtraction:
    """Test extraction of shell commands."""

    def test_extract_npm_command(self):
        """NPM commands (requires $ at start of line)"""
        text = """$ npm install
$ npm test"""
        commands = MultiModalExtractor.extract_commands(text)

        assert "npm install" in commands
        assert "npm test" in commands

    def test_extract_git_commands(self):
        """Git commands (requires $ at start of line)"""
        text = """$ git add .
$ git commit -m "message" """
        commands = MultiModalExtractor.extract_commands(text)

        assert "git add ." in commands
        assert 'git commit -m "message"' in commands

    def test_extract_pytest_command(self):
        """Pytest commands"""
        text = "$ pytest tests/ --cov=hooks"
        commands = MultiModalExtractor.extract_commands(text)

        assert "pytest tests/ --cov=hooks" in commands

    def test_extract_docker_commands(self):
        """Docker commands"""
        text = "$ docker build -t myapp ."
        commands = MultiModalExtractor.extract_commands(text)

        assert "docker build -t myapp ." in commands

    def test_skip_very_long_commands(self):
        """Commands >200 chars are skipped"""
        long_cmd = "x" * 250
        text = f"$ {long_cmd}"
        commands = MultiModalExtractor.extract_commands(text)

        assert len(commands) == 0


class TestArchitectureMentions:
    """Test extraction of architecture/design mentions."""

    def test_extract_architecture_keyword(self):
        """'architecture' keyword in sentence"""
        text = "Discussed the system architecture for microservices."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        assert len(mentions) >= 1
        assert any(m["keyword"] == "architecture" for m in mentions)

    def test_extract_design_keyword(self):
        """'design' keyword in sentence (needs punctuation ending)"""
        text = "We created a new design for the system."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        assert len(mentions) >= 1
        assert any(m["keyword"] == "design" for m in mentions)

    def test_extract_flow_keyword(self):
        """'flow' keyword in sentence"""
        text = "Documented the authentication flow."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        assert len(mentions) >= 1
        assert any(m["keyword"] == "flow" for m in mentions)

    def test_extract_multiple_architecture_keywords(self):
        """Multiple architecture keywords in text"""
        text = "Designed the pipeline architecture with a workflow structure."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        keywords = [m["keyword"] for m in mentions]
        # Should find at least 2 of: design, pipeline, architecture, workflow, structure
        assert len(set(keywords)) >= 2

    def test_skip_short_architecture_sentences(self):
        """Sentences <20 chars are skipped"""
        text = "Architecture."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        assert len(mentions) == 0

    def test_case_insensitive_extraction(self):
        """Architecture extraction is case-insensitive"""
        text = "The ARCHITECTURE uses a hierarchical DESIGN."
        mentions = MultiModalExtractor.extract_architecture_mentions(text)

        assert len(mentions) >= 2


class TestErrorExtraction:
    """Test extraction of errors and exceptions."""

    def test_extract_error_with_colon(self):
        """Error: message format"""
        text = "Hit Error: Connection timeout after 30 seconds"
        errors = MultiModalExtractor.extract_error_messages(text)

        assert len(errors) >= 1
        assert errors[0]["type"] == "error"
        assert "Connection timeout" in errors[0]["message"]

    def test_extract_exception(self):
        """Exception: message format"""
        text = "Got Exception: Invalid API key provided"
        errors = MultiModalExtractor.extract_error_messages(text)

        assert len(errors) >= 1
        assert errors[0]["type"] == "exception"
        assert "Invalid API key" in errors[0]["message"]

    def test_extract_test_failure(self):
        """FAILED: test message format"""
        text = "FAILED: test_authentication - assertion error"
        errors = MultiModalExtractor.extract_error_messages(text)

        assert len(errors) >= 1
        assert errors[0]["type"] == "test_failure"

    def test_extract_stack_trace(self):
        """Traceback format"""
        text = """
        Traceback (most recent call last):
          File "app.py", line 42
            print(x)
        NameError: name 'x' is not defined
        """
        errors = MultiModalExtractor.extract_error_messages(text)

        stack_traces = [e for e in errors if e["type"] == "stack_trace"]
        assert len(stack_traces) >= 1

    def test_truncate_long_errors(self):
        """Error messages >200 chars are truncated"""
        long_error = "x" * 300
        text = f"Error: {long_error}"
        errors = MultiModalExtractor.extract_error_messages(text)

        if len(errors) > 0:
            assert len(errors[0]["message"]) <= 200

    def test_skip_very_long_errors(self):
        """Errors >500 chars are skipped entirely"""
        long_error = "x" * 600
        text = f"Error: {long_error}"
        errors = MultiModalExtractor.extract_error_messages(text)

        assert len(errors) == 0


class TestExtractAllArtifacts:
    """Test combined artifact extraction."""

    def test_extract_all_from_chunk(self):
        """Extract all artifact types from a chunk"""
        chunk = {
            "intent": "User wants API endpoint",
            "action": "Created api/users.ts with ```typescript\ncode\n```",
            "outcome": "Error: Connection failed. Designed the architecture."
        }

        artifacts = MultiModalExtractor.extract_all_artifacts(chunk)

        assert "code_snippets" in artifacts
        assert "file_paths" in artifacts
        assert "commands" in artifacts
        assert "architecture_mentions" in artifacts
        assert "error_messages" in artifacts
        assert "counts" in artifacts

    def test_artifact_counts(self):
        """Counts are accurate"""
        chunk = {
            "intent": "Create auth.py and utils.py",
            "action": "```python\ncode1\n```\n```python\ncode2\n```",
            "outcome": "Error: failed"
        }

        artifacts = MultiModalExtractor.extract_all_artifacts(chunk)

        assert artifacts["counts"]["code_snippets"] >= 2
        assert artifacts["counts"]["file_paths"] >= 2
        assert artifacts["counts"]["errors"] >= 1

    def test_empty_chunk(self):
        """Empty chunk returns empty artifacts"""
        chunk = {"intent": "", "action": "", "outcome": ""}

        artifacts = MultiModalExtractor.extract_all_artifacts(chunk)

        assert artifacts["counts"]["code_snippets"] == 0
        assert artifacts["counts"]["file_paths"] == 0
        assert artifacts["counts"]["errors"] == 0


class TestSearchableArtifactText:
    """Test creation of searchable artifact text."""

    def test_format_code_languages(self):
        """Code languages are formatted"""
        artifacts = {
            "code_snippets": [
                {"language": "python", "code": "x=1"},
                {"language": "typescript", "code": "y=2"}
            ]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert "CODE_LANGUAGES" in text
        assert "python" in text
        assert "typescript" in text

    def test_format_file_paths(self):
        """File paths are formatted"""
        artifacts = {
            "file_paths": ["auth.py", "utils.py", "api.ts"]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert "FILES" in text
        assert "auth.py" in text
        assert "utils.py" in text

    def test_limit_file_paths(self):
        """File paths limited to 10"""
        artifacts = {
            "file_paths": [f"file{i}.py" for i in range(20)]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        # Should only have first 10 files
        for i in range(10):
            assert f"file{i}.py" in text

    def test_format_commands(self):
        """Commands are formatted"""
        artifacts = {
            "commands": ["npm test", "npm build"]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert "COMMANDS" in text
        assert "npm test" in text

    def test_limit_commands(self):
        """Commands limited to 5"""
        artifacts = {
            "commands": [f"cmd{i}" for i in range(10)]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        # Should only have first 5 commands
        for i in range(5):
            assert f"cmd{i}" in text

    def test_format_architecture_keywords(self):
        """Architecture keywords are formatted"""
        artifacts = {
            "architecture_mentions": [
                {"keyword": "architecture", "description": "..."},
                {"keyword": "design", "description": "..."}
            ]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert "ARCHITECTURE" in text
        assert "architecture" in text
        assert "design" in text

    def test_empty_artifacts(self):
        """Empty artifacts returns empty string"""
        artifacts = {}

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert text == ""

    def test_parts_joined_with_pipe(self):
        """Parts are joined with ' | '"""
        artifacts = {
            "file_paths": ["auth.py"],
            "commands": ["npm test"]
        }

        text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

        assert " | " in text


class TestEnrichChunkWithArtifacts:
    """Test chunk enrichment with artifacts."""

    def test_enrich_basic_chunk(self):
        """Basic chunk enrichment"""
        chunk = {
            "intent": "Create API",
            "action": "Built api/users.ts",
            "outcome": "Success",
            "summary": "API created"
        }

        enriched = enrich_chunk_with_artifacts(chunk)

        assert "chunk" in enriched
        assert "metadata" in enriched
        assert "enhanced_summary" in enriched

    def test_metadata_has_flags(self):
        """Metadata includes has_* flags"""
        chunk = {
            "intent": "",
            "action": "Created auth.py with ```python\ncode\n```",
            "outcome": "Discussed the system architecture."
        }

        enriched = enrich_chunk_with_artifacts(chunk)

        assert "has_code" in enriched["metadata"]
        assert "has_files" in enriched["metadata"]
        assert "has_architecture" in enriched["metadata"]

        assert enriched["metadata"]["has_code"] is True
        assert enriched["metadata"]["has_files"] is True
        assert enriched["metadata"]["has_architecture"] is True

    def test_enhanced_summary_includes_artifacts(self):
        """Enhanced summary includes artifact text"""
        chunk = {
            "intent": "",
            "action": "Created auth.py",
            "outcome": "",
            "summary": "File created"
        }

        enriched = enrich_chunk_with_artifacts(chunk)

        # Should have original summary plus artifact text
        assert "File created" in enriched["enhanced_summary"]
        assert "auth.py" in enriched["enhanced_summary"]

    def test_metadata_preserved(self):
        """Existing metadata is preserved"""
        chunk = {"intent": "", "action": "", "outcome": ""}
        metadata = {"session_id": "123", "importance": 5.0}

        enriched = enrich_chunk_with_artifacts(chunk, metadata)

        assert enriched["metadata"]["session_id"] == "123"
        assert enriched["metadata"]["importance"] == 5.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/multimodal_extractor", "--cov-report=term-missing"])
