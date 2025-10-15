#!/usr/bin/env python3
"""
Entity Extractor for Knowledge Graph
=====================================
Extracts structured entities from memory transcripts for graph construction.

Entity Types:
- FILES: Python files, config files (*.py, *.json, *.md)
- FUNCTIONS: function definitions, method calls
- CLASSES: class definitions
- BUGS: errors, exceptions, issues
- FEATURES: capabilities, improvements
- DECISIONS: architectural choices, approaches
- TOOLS: technologies, libraries, frameworks

Relationships:
- MODIFIES: entity changes a file
- FIXES: entity resolves a bug
- IMPLEMENTS: code implements a feature
- USES: file/function uses a tool
- DEPENDS_ON: entity depends on another
- RELATES_TO: general semantic relationship
"""

import re
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    """Structured entity with metadata."""
    entity_type: str  # FILES, FUNCTIONS, CLASSES, BUGS, FEATURES, DECISIONS, TOOLS
    name: str
    context: str  # Surrounding text for disambiguation
    confidence: float  # 0-1 extraction confidence


@dataclass
class Relationship:
    """Relationship between two entities."""
    source: str
    relation_type: str
    target: str
    confidence: float


class EntityExtractor:
    """Extract structured entities from memory transcripts."""

    # File patterns
    FILE_PATTERNS = [
        r'`([a-zA-Z0-9_/\-\.]+\.(py|js|ts|jsx|tsx|java|cpp|h|json|yaml|yml|md|txt))`',  # Backtick files
        r'([a-zA-Z0-9_/\-]+\.(py|js|ts|jsx|tsx|java|cpp|h|json|yaml|yml|md|txt))\b',  # Plain files
        r'(~?/[a-zA-Z0-9_/\-\.]+\.(py|js|ts|jsx|tsx|java|cpp|h|json|yaml|yml|md|txt))',  # Absolute paths
    ]

    # Function/method patterns
    FUNCTION_PATTERNS = [
        r'`([a-zA-Z_][a-zA-Z0-9_]*)\(\)`',  # Backtick functions
        r'\b(def|function|const|let|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Definitions
        r'([a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\)\s*:',  # Python type hints
    ]

    # Class patterns
    CLASS_PATTERNS = [
        r'\bclass\s+([A-Z][a-zA-Z0-9_]*)',
        r'`([A-Z][a-zA-Z0-9_]*)`\s+class',
    ]

    # Bug/error patterns
    BUG_PATTERNS = [
        r'(TypeError|ValueError|AttributeError|KeyError|IndexError|ImportError|RuntimeError|Exception):\s*([^\.]+)',
        r'(error|bug|issue|problem|failure|crash):\s*([^\.]{10,100})',
        r'(fixed|resolved|solved):\s*([^\.]{10,100})',
    ]

    # Feature patterns
    FEATURE_PATTERNS = [
        r'(adaptive K|knowledge graph|temporal decay|embedding|retrieval|migration|extraction|pruning|clustering)',
        r'implemented\s+([^\.]{10,80})',
        r'added\s+([^\.]{10,80})',
        r'built\s+([^\.]{10,80})',
    ]

    # Decision patterns
    DECISION_PATTERNS = [
        r'(decided to|chose|selected|will use|strategy|approach):\s*([^\.]{10,100})',
        r'switched to\s+([^\.]{10,80})',
    ]

    # Tool/technology patterns
    TOOL_PATTERNS = [
        r'\b(ChromaDB|nomic-embed|SentenceTransformer|NetworkX|numpy|pandas|transformers|langchain)\b',
        r'`([a-z\-]+(?:-[a-z]+)+)`',  # Package names like nomic-embed-text-v1.5
    ]

    @staticmethod
    def extract_entities(text: str) -> List[Entity]:
        """Extract all entities from text."""
        entities = []

        # Extract files
        for pattern in EntityExtractor.FILE_PATTERNS:
            for match in re.finditer(pattern, text):
                file_name = match.group(1) if '(' in pattern and pattern.count('(') > 1 else match.group(0)
                file_name = file_name.strip('`')
                entities.append(Entity(
                    entity_type="FILE",
                    name=file_name,
                    context=text[max(0, match.start()-50):min(len(text), match.end()+50)],
                    confidence=0.9
                ))

        # Extract functions
        for pattern in EntityExtractor.FUNCTION_PATTERNS:
            for match in re.finditer(pattern, text):
                if 'def|function|const' in pattern:
                    func_name = match.group(2)
                else:
                    func_name = match.group(1)
                func_name = func_name.strip('`')
                entities.append(Entity(
                    entity_type="FUNCTION",
                    name=func_name,
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                    confidence=0.8
                ))

        # Extract classes
        for pattern in EntityExtractor.CLASS_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                class_name = match.group(1)
                entities.append(Entity(
                    entity_type="CLASS",
                    name=class_name,
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                    confidence=0.85
                ))

        # Extract bugs/errors
        for pattern in EntityExtractor.BUG_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                bug_desc = match.group(0)
                entities.append(Entity(
                    entity_type="BUG",
                    name=bug_desc[:100],
                    context=text[max(0, match.start()-40):min(len(text), match.end()+40)],
                    confidence=0.75
                ))

        # Extract features
        for pattern in EntityExtractor.FEATURE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                feature = match.group(1) if match.lastindex else match.group(0)
                entities.append(Entity(
                    entity_type="FEATURE",
                    name=feature.strip(),
                    context=text[max(0, match.start()-40):min(len(text), match.end()+40)],
                    confidence=0.7
                ))

        # Extract decisions
        for pattern in EntityExtractor.DECISION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                decision = match.group(0)
                entities.append(Entity(
                    entity_type="DECISION",
                    name=decision[:100],
                    context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                    confidence=0.8
                ))

        # Extract tools
        for pattern in EntityExtractor.TOOL_PATTERNS:
            for match in re.finditer(pattern, text):
                tool = match.group(1) if match.lastindex else match.group(0)
                tool = tool.strip('`')
                entities.append(Entity(
                    entity_type="TOOL",
                    name=tool,
                    context=text[max(0, match.start()-20):min(len(text), match.end()+20)],
                    confidence=0.9
                ))

        return entities

    @staticmethod
    def extract_relationships(text: str, entities: List[Entity]) -> List[Relationship]:
        """Extract relationships between entities based on context."""
        relationships = []

        # Create entity lookup by name
        entity_map = {e.name: e for e in entities}

        # MODIFIES relationship (file modifications)
        for entity in entities:
            if entity.entity_type == "FILE":
                # Check if any feature/function mentions this file
                for other in entities:
                    if other.entity_type in ["FEATURE", "FUNCTION"] and entity.name in other.context:
                        relationships.append(Relationship(
                            source=other.name,
                            relation_type="MODIFIES",
                            target=entity.name,
                            confidence=0.7
                        ))

        # FIXES relationship (bugs fixed by features)
        for entity in entities:
            if entity.entity_type == "BUG":
                for other in entities:
                    if other.entity_type == "FEATURE":
                        # Check if bug and feature co-occur in text
                        if entity.name[:30] in other.context or other.name in entity.context:
                            relationships.append(Relationship(
                                source=other.name,
                                relation_type="FIXES",
                                target=entity.name[:50],
                                confidence=0.6
                            ))

        # USES relationship (tools used by files/features)
        for entity in entities:
            if entity.entity_type == "TOOL":
                for other in entities:
                    if other.entity_type in ["FILE", "FEATURE", "FUNCTION"]:
                        if entity.name in other.context:
                            relationships.append(Relationship(
                                source=other.name,
                                relation_type="USES",
                                target=entity.name,
                                confidence=0.8
                            ))

        # IMPLEMENTS relationship (functions implement features)
        for entity in entities:
            if entity.entity_type == "FUNCTION":
                for other in entities:
                    if other.entity_type == "FEATURE":
                        if entity.name in other.context or other.name.lower() in entity.context.lower():
                            relationships.append(Relationship(
                                source=entity.name,
                                relation_type="IMPLEMENTS",
                                target=other.name,
                                confidence=0.65
                            ))

        return relationships

    @staticmethod
    def deduplicate_entities(entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities (same type + name)."""
        seen = set()
        unique = []

        for entity in entities:
            key = (entity.entity_type, entity.name.lower())
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique


def extract_entities_from_memory(memory_doc: str, memory_metadata: Dict) -> Tuple[List[Entity], List[Relationship]]:
    """Extract entities from a single memory (document + metadata)."""

    # Combine document with intent/action/outcome for full context
    full_text = f"{memory_doc} {memory_metadata.get('intent', '')} {memory_metadata.get('action', '')} {memory_metadata.get('outcome', '')}"

    # Extract entities
    entities = EntityExtractor.extract_entities(full_text)
    entities = EntityExtractor.deduplicate_entities(entities)

    # Extract relationships
    relationships = EntityExtractor.extract_relationships(full_text, entities)

    return entities, relationships
