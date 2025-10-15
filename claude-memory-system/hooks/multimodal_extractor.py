#!/usr/bin/env python3
"""
Multi-Modal Memory Extractor
============================
Extracts and stores multi-modal artifacts from conversations:
- Code snippets (with language and context)
- File paths and modifications
- Diagrams and architecture descriptions
- Command sequences
- Error messages and stack traces

These are stored alongside text embeddings for rich retrieval.
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class MultiModalExtractor:
    """Extracts multi-modal artifacts from conversation chunks."""

    # Code block patterns
    CODE_BLOCK_PATTERN = r'```(\w+)?\n(.*?)```'
    INLINE_CODE_PATTERN = r'`([^`]+)`'

    # File path patterns
    FILE_PATH_PATTERN = r'\b[\w/\-\.]+\.(ts|js|py|go|rs|java|cpp|c|h|json|yaml|yml|md|txt|sh)\b'

    # Command patterns
    COMMAND_PATTERN = r'(?:^|\n)\$\s+(.+?)(?:\n|$)'

    # Architecture/diagram keywords
    ARCHITECTURE_KEYWORDS = [
        'architecture', 'diagram', 'flow', 'design', 'structure',
        'pipeline', 'workflow', 'sequence', 'hierarchy'
    ]

    @staticmethod
    def extract_code_snippets(text: str) -> List[Dict[str, str]]:
        """Extract code blocks from text."""
        snippets = []

        # Extract code blocks
        for match in re.finditer(MultiModalExtractor.CODE_BLOCK_PATTERN, text, re.DOTALL):
            language = match.group(1) or 'plaintext'
            code = match.group(2).strip()

            if code:
                snippet_id = hashlib.md5(code.encode()).hexdigest()[:12]
                snippets.append({
                    "type": "code_block",
                    "language": language,
                    "code": code,
                    "snippet_id": snippet_id,
                    "lines": len(code.split('\n'))
                })

        # Extract inline code
        for match in re.finditer(MultiModalExtractor.INLINE_CODE_PATTERN, text):
            code = match.group(1).strip()
            if len(code) > 5:  # Only meaningful inline code
                snippet_id = hashlib.md5(code.encode()).hexdigest()[:12]
                snippets.append({
                    "type": "inline_code",
                    "code": code,
                    "snippet_id": snippet_id
                })

        return snippets

    @staticmethod
    def extract_file_paths(text: str) -> List[str]:
        """Extract file paths from text."""
        paths = set()

        for match in re.finditer(MultiModalExtractor.FILE_PATH_PATTERN, text):
            path = match.group(0)
            # Filter out likely false positives
            if not re.match(r'^\d+\.\w+$', path):  # Not just "123.ts"
                paths.add(path)

        return sorted(list(paths))

    @staticmethod
    def extract_commands(text: str) -> List[str]:
        """Extract shell commands from text."""
        commands = []

        for match in re.finditer(MultiModalExtractor.COMMAND_PATTERN, text, re.MULTILINE):
            cmd = match.group(1).strip()
            if cmd and len(cmd) < 200:  # Reasonable command length
                commands.append(cmd)

        return commands

    @staticmethod
    def extract_architecture_mentions(text: str) -> List[Dict[str, str]]:
        """Extract architecture/diagram descriptions."""
        mentions = []
        text_lower = text.lower()

        for keyword in MultiModalExtractor.ARCHITECTURE_KEYWORDS:
            # Find sentences containing architecture keywords
            pattern = rf'([^.!?]*\b{keyword}\b[^.!?]*[.!?])'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                sentence = match.group(1).strip()
                if len(sentence) > 20:  # Meaningful sentence
                    mentions.append({
                        "type": "architecture",
                        "keyword": keyword,
                        "description": sentence
                    })

        return mentions

    @staticmethod
    def extract_error_messages(text: str) -> List[Dict[str, str]]:
        """Extract error messages and stack traces."""
        errors = []

        # Common error patterns
        error_patterns = [
            (r'Error:\s*(.+?)(?:\n|$)', 'error'),
            (r'Exception:\s*(.+?)(?:\n|$)', 'exception'),
            (r'FAILED:\s*(.+?)(?:\n|$)', 'test_failure'),
            (r'Traceback.*?(?=\n\S|\Z)', 'stack_trace')
        ]

        for pattern, error_type in error_patterns:
            for match in re.finditer(pattern, text, re.DOTALL):
                error_text = match.group(1).strip() if error_type != 'stack_trace' else match.group(0).strip()
                if error_text and len(error_text) < 500:  # Reasonable error length
                    errors.append({
                        "type": error_type,
                        "message": error_text[:200]  # Truncate
                    })

        return errors

    @staticmethod
    def extract_all_artifacts(chunk: Dict[str, str]) -> Dict[str, Any]:
        """Extract all multi-modal artifacts from a chunk."""
        combined_text = f"{chunk.get('intent', '')} {chunk.get('action', '')} {chunk.get('outcome', '')}"

        artifacts = {
            "code_snippets": MultiModalExtractor.extract_code_snippets(combined_text),
            "file_paths": MultiModalExtractor.extract_file_paths(combined_text),
            "commands": MultiModalExtractor.extract_commands(combined_text),
            "architecture_mentions": MultiModalExtractor.extract_architecture_mentions(combined_text),
            "error_messages": MultiModalExtractor.extract_error_messages(combined_text),
        }

        # Add counts for quick filtering
        artifacts["counts"] = {
            "code_snippets": len(artifacts["code_snippets"]),
            "file_paths": len(artifacts["file_paths"]),
            "commands": len(artifacts["commands"]),
            "architecture_mentions": len(artifacts["architecture_mentions"]),
            "errors": len(artifacts["error_messages"]),
        }

        return artifacts

    @staticmethod
    def create_searchable_artifact_text(artifacts: Dict[str, Any]) -> str:
        """Create a searchable text representation of artifacts."""
        parts = []

        # Add code languages
        if artifacts.get("code_snippets"):
            languages = set(s["language"] for s in artifacts["code_snippets"] if s.get("language"))
            if languages:
                parts.append(f"CODE_LANGUAGES: {', '.join(languages)}")

        # Add file paths
        if artifacts.get("file_paths"):
            parts.append(f"FILES: {', '.join(artifacts['file_paths'][:10])}")  # Limit to 10

        # Add commands
        if artifacts.get("commands"):
            parts.append(f"COMMANDS: {'; '.join(artifacts['commands'][:5])}")  # Limit to 5

        # Add architecture keywords
        if artifacts.get("architecture_mentions"):
            keywords = set(m["keyword"] for m in artifacts["architecture_mentions"])
            parts.append(f"ARCHITECTURE: {', '.join(keywords)}")

        return " | ".join(parts)


def enrich_chunk_with_artifacts(chunk: Dict[str, str], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Enrich a memory chunk with multi-modal artifacts."""
    metadata = metadata or {}

    # Extract artifacts
    artifacts = MultiModalExtractor.extract_all_artifacts(chunk)

    # Create searchable artifact text (for embedding)
    artifact_text = MultiModalExtractor.create_searchable_artifact_text(artifacts)

    # Combine with original summary for embedding
    enhanced_summary = chunk.get("summary", "")
    if artifact_text:
        enhanced_summary = f"{enhanced_summary} [{artifact_text}]"

    return {
        "chunk": chunk,
        "metadata": {
            **metadata,
            "artifacts": artifacts,
            "has_code": artifacts["counts"]["code_snippets"] > 0,
            "has_files": artifacts["counts"]["file_paths"] > 0,
            "has_architecture": artifacts["counts"]["architecture_mentions"] > 0,
        },
        "enhanced_summary": enhanced_summary
    }


if __name__ == "__main__":
    # Test artifact extraction
    test_chunk = {
        "intent": "User wants to implement API endpoint",
        "action": "Created api/users.ts, added authentication middleware, ran tests with `npm test`",
        "outcome": """Endpoint working. Architecture: RESTful design with JWT auth.
        Code example:
        ```typescript
        async function getUser(req: Request) {
          const user = await db.users.find(req.params.id);
          return user;
        }
        ```
        Error initially: TypeError: Cannot read property 'id' of undefined - fixed by adding null check.""",
        "summary": "Implemented user API endpoint with authentication"
    }

    enriched = enrich_chunk_with_artifacts(test_chunk)

    print("Multi-Modal Artifact Extraction Test:")
    print("=" * 60)
    print("\nOriginal chunk:")
    print(json.dumps(test_chunk, indent=2))
    print("\nExtracted artifacts:")
    print(json.dumps(enriched["metadata"]["artifacts"], indent=2))
    print("\nEnhanced summary for embedding:")
    print(enriched["enhanced_summary"])
