#!/usr/bin/env python3
"""
Unit tests for knowledge_graph.py
==================================
Tests MemoryKnowledgeGraph class with comprehensive coverage.

Target: 80%+ coverage for knowledge graph construction and traversal.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import networkx as nx

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from knowledge_graph import MemoryKnowledgeGraph
from entity_extractor import Entity, Relationship


class TestGraphInitialization:
    """Test graph initialization and setup."""

    def test_init_creates_empty_graph(self):
        """Initialize creates empty directed graph"""
        kg = MemoryKnowledgeGraph("/fake/path")

        assert isinstance(kg.graph, nx.DiGraph)
        assert kg.graph.number_of_nodes() == 0
        assert kg.graph.number_of_edges() == 0
        assert kg.entity_to_memories == {}
        assert kg.pagerank_scores == {}

    def test_init_stores_db_path(self):
        """Initialize stores memory database path"""
        kg = MemoryKnowledgeGraph("/test/db/path")

        assert str(kg.memory_db_path) == "/test/db/path"
        assert isinstance(kg.memory_db_path, Path)


class TestGraphBuilding:
    """Test building graph from entities and relationships."""

    def test_build_graph_single_entity(self):
        """Build graph with single entity"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="auth.py", context="context", confidence=0.9)
        ]
        relationships = []

        kg.entity_to_memories = {"auth.py": ["mem1", "mem2"]}
        kg._build_graph_from_entities(entities, relationships)

        assert kg.graph.number_of_nodes() == 1
        assert kg.graph.has_node("auth.py")
        assert kg.graph.nodes["auth.py"]["entity_type"] == "FILE"
        assert kg.graph.nodes["auth.py"]["confidence"] == 0.9
        assert kg.graph.nodes["auth.py"]["access_count"] == 2

    def test_build_graph_multiple_entities(self):
        """Build graph with multiple different entities"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9),
            Entity(entity_type="FUNCTION", name="login", context="ctx", confidence=0.8),
            Entity(entity_type="BUG", name="TypeError", context="ctx", confidence=0.7),
        ]
        relationships = []

        kg.entity_to_memories = {
            "auth.py": ["mem1"],
            "login": ["mem1"],
            "TypeError": ["mem2"]
        }
        kg._build_graph_from_entities(entities, relationships)

        assert kg.graph.number_of_nodes() == 3
        assert kg.graph.has_node("auth.py")
        assert kg.graph.has_node("login")
        assert kg.graph.has_node("TypeError")

    def test_build_graph_duplicate_entities(self):
        """Duplicate entities increment access count"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="auth.py", context="ctx1", confidence=0.9),
            Entity(entity_type="FILE", name="auth.py", context="ctx2", confidence=0.9),
        ]
        relationships = []

        kg.entity_to_memories = {"auth.py": ["mem1", "mem2"]}
        kg._build_graph_from_entities(entities, relationships)

        # Should have 1 node, not 2
        assert kg.graph.number_of_nodes() == 1
        # Access count should be updated (starts at 2, then +1)
        assert kg.graph.nodes["auth.py"]["access_count"] == 3

    def test_build_graph_single_relationship(self):
        """Build graph with single relationship"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FUNCTION", name="login", context="ctx", confidence=0.8),
            Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9),
        ]
        relationships = [
            Relationship(source="login", relation_type="MODIFIES", target="auth.py", confidence=0.7)
        ]

        kg.entity_to_memories = {"login": ["mem1"], "auth.py": ["mem1"]}
        kg._build_graph_from_entities(entities, relationships)

        assert kg.graph.number_of_edges() == 1
        assert kg.graph.has_edge("login", "auth.py")
        assert kg.graph["login"]["auth.py"]["relation_type"] == "MODIFIES"
        assert kg.graph["login"]["auth.py"]["confidence"] == 0.7
        assert kg.graph["login"]["auth.py"]["co_occurrence"] == 1

    def test_build_graph_duplicate_relationships(self):
        """Duplicate relationships increment co-occurrence"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FUNCTION", name="login", context="ctx", confidence=0.8),
            Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9),
        ]
        relationships = [
            Relationship(source="login", relation_type="MODIFIES", target="auth.py", confidence=0.7),
            Relationship(source="login", relation_type="MODIFIES", target="auth.py", confidence=0.8),
        ]

        kg.entity_to_memories = {"login": ["mem1"], "auth.py": ["mem1"]}
        kg._build_graph_from_entities(entities, relationships)

        # Should have 1 edge, not 2
        assert kg.graph.number_of_edges() == 1
        # Co-occurrence should increment
        assert kg.graph["login"]["auth.py"]["co_occurrence"] == 2

    def test_build_graph_orphan_relationship(self):
        """Relationships without entities are ignored"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9),
        ]
        # Relationship referencing non-existent entity
        relationships = [
            Relationship(source="login", relation_type="MODIFIES", target="auth.py", confidence=0.7),
            Relationship(source="auth.py", relation_type="USES", target="jwt", confidence=0.8),
        ]

        kg.entity_to_memories = {"auth.py": ["mem1"]}
        kg._build_graph_from_entities(entities, relationships)

        # No edges should be created (missing source/target nodes)
        assert kg.graph.number_of_edges() == 0

    def test_build_graph_complex_network(self):
        """Build complex graph with multiple relationships"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9),
            Entity(entity_type="FUNCTION", name="login", context="ctx", confidence=0.8),
            Entity(entity_type="FEATURE", name="OAuth", context="ctx", confidence=0.7),
            Entity(entity_type="TOOL", name="jwt", context="ctx", confidence=0.9),
        ]
        relationships = [
            Relationship(source="login", relation_type="MODIFIES", target="auth.py", confidence=0.7),
            Relationship(source="login", relation_type="IMPLEMENTS", target="OAuth", confidence=0.6),
            Relationship(source="auth.py", relation_type="USES", target="jwt", confidence=0.8),
        ]

        kg.entity_to_memories = {
            "auth.py": ["mem1"],
            "login": ["mem1"],
            "OAuth": ["mem1"],
            "jwt": ["mem1"]
        }
        kg._build_graph_from_entities(entities, relationships)

        assert kg.graph.number_of_nodes() == 4
        assert kg.graph.number_of_edges() == 3


class TestBuildFromMemories:
    """Test building graph from ChromaDB memories."""

    @patch('knowledge_graph.chromadb.PersistentClient')
    @patch('knowledge_graph.extract_entities_from_memory')
    def test_build_from_memories_all_sessions(self, mock_extract, mock_client):
        """Build from all sessions"""
        # Mock ChromaDB
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1", "mem2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{"intent": "test1"}, {"intent": "test2"}]
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance

        # Mock entity extraction
        mock_extract.return_value = (
            [Entity(entity_type="FILE", name="test.py", context="ctx", confidence=0.9)],
            []
        )

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="all")

        # Check ChromaDB was called correctly
        mock_collection.get.assert_called_once()
        assert mock_extract.call_count == 2

        # Check graph was built
        assert kg.graph.number_of_nodes() > 0

    @patch('knowledge_graph.chromadb.PersistentClient')
    @patch('knowledge_graph.extract_entities_from_memory')
    def test_build_from_memories_specific_session(self, mock_extract, mock_client):
        """Build from specific session ID"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1"],
            "documents": ["doc1"],
            "metadatas": [{"intent": "test"}]
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance

        mock_extract.return_value = ([], [])

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="session123")

        # Check WHERE clause was used
        call_args = mock_collection.get.call_args
        assert call_args[1]["where"] == {"session_id": "session123"}

    @patch('knowledge_graph.chromadb.PersistentClient')
    @patch('knowledge_graph.extract_entities_from_memory')
    def test_build_from_memories_with_limit(self, mock_extract, mock_client):
        """Build from memories with limit"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1"],
            "documents": ["doc1"],
            "metadatas": [{"intent": "test"}]
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance

        mock_extract.return_value = ([], [])

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="all", limit=100)

        # Check limit was passed
        call_args = mock_collection.get.call_args
        assert call_args[1]["limit"] == 100

    @patch('knowledge_graph.chromadb.PersistentClient')
    def test_build_from_memories_no_results(self, mock_client):
        """Handle no memories gracefully"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="all")

        # Should not crash, just return empty graph
        assert kg.graph.number_of_nodes() == 0

    @patch('knowledge_graph.chromadb.PersistentClient')
    def test_build_from_memories_collection_error(self, mock_client):
        """Handle collection not found error"""
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.side_effect = Exception("Collection not found")
        mock_client.return_value = mock_client_instance

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="all")

        # Should not crash
        assert kg.graph.number_of_nodes() == 0

    @patch('knowledge_graph.chromadb.PersistentClient')
    @patch('knowledge_graph.extract_entities_from_memory')
    def test_build_from_memories_tracks_entity_memories(self, mock_extract, mock_client):
        """Entity to memories mapping is tracked"""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["mem1", "mem2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{"intent": "test1"}, {"intent": "test2"}]
        }
        mock_client_instance = MagicMock()
        mock_client_instance.get_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance

        # Same entity in both memories
        mock_extract.return_value = (
            [Entity(entity_type="FILE", name="auth.py", context="ctx", confidence=0.9)],
            []
        )

        kg = MemoryKnowledgeGraph("/fake/path")
        kg.build_from_memories(session_id="all")

        # Check entity_to_memories mapping
        assert "auth.py" in kg.entity_to_memories
        assert kg.entity_to_memories["auth.py"] == ["mem1", "mem2"]


class TestCentralityComputation:
    """Test centrality metrics computation."""

    def test_compute_centrality_empty_graph(self):
        """Empty graph skips centrality computation"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.compute_centrality()

        assert kg.pagerank_scores == {}

    def test_compute_centrality_single_node(self):
        """Single node gets PageRank = 1.0"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("auth.py", entity_type="FILE", confidence=0.9)

        kg.compute_centrality()

        assert "auth.py" in kg.pagerank_scores
        assert kg.pagerank_scores["auth.py"] == 1.0

    def test_compute_centrality_pagerank(self):
        """PageRank scores distributed correctly"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Create simple graph: A -> B -> C
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_node("C", entity_type="FILE")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("B", "C")

        kg.compute_centrality()

        # All nodes should have PageRank scores
        assert len(kg.pagerank_scores) == 3
        assert all(0 < score <= 1.0 for score in kg.pagerank_scores.values())
        # Sum should be approximately 1.0
        assert abs(sum(kg.pagerank_scores.values()) - 1.0) < 0.01

    def test_compute_centrality_hub_node(self):
        """Hub node gets higher PageRank"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Create hub graph: A, B, C -> Hub
        kg.graph.add_node("Hub", entity_type="FILE")
        for node in ["A", "B", "C"]:
            kg.graph.add_node(node, entity_type="FILE")
            kg.graph.add_edge(node, "Hub")

        kg.compute_centrality()

        # Hub should have highest PageRank
        hub_rank = kg.pagerank_scores["Hub"]
        other_ranks = [kg.pagerank_scores[n] for n in ["A", "B", "C"]]
        assert all(hub_rank > rank for rank in other_ranks)

    def test_compute_centrality_betweenness(self):
        """Betweenness centrality computed for bridge nodes"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Create graph with bridge: A -> Bridge -> B
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("Bridge", entity_type="FUNCTION")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_edge("A", "Bridge")
        kg.graph.add_edge("Bridge", "B")

        kg.compute_centrality()

        # Bridge should have high betweenness
        assert "betweenness" in kg.graph.nodes["Bridge"]
        assert kg.graph.nodes["Bridge"]["betweenness"] > 0

    def test_compute_centrality_degree(self):
        """Degree centrality computed for all nodes"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_edge("A", "B")

        kg.compute_centrality()

        # Both nodes should have degree centrality
        assert "degree_centrality" in kg.graph.nodes["A"]
        assert "degree_centrality" in kg.graph.nodes["B"]

    def test_compute_centrality_error_handling(self):
        """Centrality computation handles errors gracefully"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("A", entity_type="FILE")

        # Should not crash even if centrality computation fails
        with patch('networkx.pagerank', side_effect=Exception("PageRank failed")):
            kg.compute_centrality()
            # Should fall back to default scores
            assert "A" in kg.pagerank_scores
            assert kg.pagerank_scores["A"] == 1.0


class TestEntityImportance:
    """Test entity importance boosting."""

    def test_get_entity_importance_not_in_graph(self):
        """Unknown entity returns base importance"""
        kg = MemoryKnowledgeGraph("/fake/path")

        importance = kg.get_entity_importance("unknown_entity", base_importance=10.0)
        assert importance == 10.0

    def test_get_entity_importance_low_pagerank(self):
        """Low PageRank gives small boost"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.pagerank_scores = {"auth.py": 0.001}

        importance = kg.get_entity_importance("auth.py", base_importance=10.0)
        # boost = 1 + (0.001 * 10) = 1.01
        expected = 10.0 * 1.01
        assert abs(importance - expected) < 0.01

    def test_get_entity_importance_medium_pagerank(self):
        """Medium PageRank gives ~10% boost"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.pagerank_scores = {"auth.py": 0.01}

        importance = kg.get_entity_importance("auth.py", base_importance=10.0)
        # boost = 1 + (0.01 * 10) = 1.1
        expected = 10.0 * 1.1
        assert abs(importance - expected) < 0.01

    def test_get_entity_importance_high_pagerank(self):
        """High PageRank doubles importance"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.pagerank_scores = {"auth.py": 0.1}

        importance = kg.get_entity_importance("auth.py", base_importance=10.0)
        # boost = 1 + (0.1 * 10) = 2.0
        expected = 10.0 * 2.0
        assert abs(importance - expected) < 0.01


class TestTopEntities:
    """Test retrieving top entities by PageRank."""

    def test_get_top_entities_empty_graph(self):
        """Empty PageRank returns empty list"""
        kg = MemoryKnowledgeGraph("/fake/path")

        top = kg.get_top_entities(limit=10)
        assert top == []

    def test_get_top_entities_all_types(self):
        """Get top entities across all types"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_node("C", entity_type="TOOL")
        kg.pagerank_scores = {"A": 0.5, "B": 0.3, "C": 0.2}

        top = kg.get_top_entities(limit=10)

        assert len(top) == 3
        assert top[0] == ("A", 0.5)
        assert top[1] == ("B", 0.3)
        assert top[2] == ("C", 0.2)

    def test_get_top_entities_filtered_by_type(self):
        """Filter top entities by type"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("file1.py", entity_type="FILE")
        kg.graph.add_node("file2.py", entity_type="FILE")
        kg.graph.add_node("func", entity_type="FUNCTION")
        kg.pagerank_scores = {"file1.py": 0.5, "file2.py": 0.3, "func": 0.2}

        top = kg.get_top_entities(entity_type="FILE", limit=10)

        assert len(top) == 2
        assert top[0][0] == "file1.py"
        assert top[1][0] == "file2.py"

    def test_get_top_entities_limit(self):
        """Respect limit parameter"""
        kg = MemoryKnowledgeGraph("/fake/path")
        for i in range(10):
            kg.graph.add_node(f"node{i}", entity_type="FILE")
            kg.pagerank_scores[f"node{i}"] = 1.0 / (i + 1)

        top = kg.get_top_entities(limit=3)

        assert len(top) == 3

    def test_get_top_entities_sorted_descending(self):
        """Results sorted by PageRank descending"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("low", entity_type="FILE")
        kg.graph.add_node("high", entity_type="FILE")
        kg.graph.add_node("medium", entity_type="FILE")
        kg.pagerank_scores = {"low": 0.1, "high": 0.9, "medium": 0.5}

        top = kg.get_top_entities(limit=10)

        assert top[0][0] == "high"
        assert top[1][0] == "medium"
        assert top[2][0] == "low"


class TestGraphTraversal:
    """Test graph traversal and entity relationships."""

    def test_get_related_entities_not_in_graph(self):
        """Unknown entity returns empty list"""
        kg = MemoryKnowledgeGraph("/fake/path")

        related = kg.get_related_entities("unknown_entity", max_hops=2)
        assert related == []

    def test_get_related_entities_isolated_node(self):
        """Isolated node has no related entities"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("isolated", entity_type="FILE")

        related = kg.get_related_entities("isolated", max_hops=2)
        assert related == []

    def test_get_related_entities_one_hop(self):
        """Get entities 1 hop away"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Graph: A -> B -> C
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_node("C", entity_type="TOOL")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("B", "C")

        related = kg.get_related_entities("A", max_hops=1)

        # Should get only B (1 hop away)
        assert len(related) == 1
        assert "B" in related

    def test_get_related_entities_two_hops(self):
        """Get entities within 2 hops"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Graph: A -> B -> C
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_node("C", entity_type="TOOL")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("B", "C")

        related = kg.get_related_entities("A", max_hops=2)

        # Should get B (1 hop) and C (2 hops)
        assert len(related) == 2
        assert "B" in related
        assert "C" in related

    def test_get_related_entities_bidirectional(self):
        """Traversal follows both directions"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Graph: A -> B <- C
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_node("C", entity_type="FILE")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("C", "B")

        related = kg.get_related_entities("B", max_hops=1)

        # Should get both A and C (predecessors and successors)
        assert len(related) == 2
        assert "A" in related
        assert "C" in related

    def test_get_related_entities_no_duplicates(self):
        """No duplicate entities in results"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Graph with multiple paths: A -> B, A -> C -> B
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_node("C", entity_type="FILE")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("A", "C")
        kg.graph.add_edge("C", "B")

        related = kg.get_related_entities("A", max_hops=2)

        # B is reachable via 2 paths, but should appear only once
        assert related.count("B") == 1
        assert related.count("C") == 1

    def test_get_related_entities_excludes_self(self):
        """Starting entity not in results"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("B", "A")  # Cycle

        related = kg.get_related_entities("A", max_hops=2)

        # Should not include A itself
        assert "A" not in related
        assert "B" in related

    def test_get_related_entities_complex_graph(self):
        """Complex graph with multiple paths"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Star topology: A is center
        kg.graph.add_node("A", entity_type="FILE")
        for node in ["B", "C", "D", "E"]:
            kg.graph.add_node(node, entity_type="FUNCTION")
            kg.graph.add_edge("A", node)

        related = kg.get_related_entities("A", max_hops=1)

        assert len(related) == 4
        assert all(n in related for n in ["B", "C", "D", "E"])

    def test_get_related_entities_zero_hops(self):
        """Zero hops returns empty list"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_edge("A", "B")

        related = kg.get_related_entities("A", max_hops=0)

        assert related == []


class TestGraphStatistics:
    """Test graph statistics computation."""

    def test_get_statistics_empty_graph(self):
        """Empty graph returns error"""
        kg = MemoryKnowledgeGraph("/fake/path")

        stats = kg.get_statistics()
        assert stats == {"error": "Empty graph"}

    def test_get_statistics_single_node(self):
        """Single node statistics"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("A", entity_type="FILE")

        stats = kg.get_statistics()

        assert stats["nodes"] == 1
        assert stats["edges"] == 0
        assert stats["entity_types"] == {"FILE": 1}
        assert stats["avg_degree"] == 0
        assert stats["density"] == 0

    def test_get_statistics_basic_graph(self):
        """Basic graph statistics"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_edge("A", "B")

        stats = kg.get_statistics()

        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["entity_types"]["FILE"] == 1
        assert stats["entity_types"]["FUNCTION"] == 1

    def test_get_statistics_entity_type_counts(self):
        """Entity type distribution"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("file1", entity_type="FILE")
        kg.graph.add_node("file2", entity_type="FILE")
        kg.graph.add_node("func1", entity_type="FUNCTION")
        kg.graph.add_node("bug1", entity_type="BUG")

        stats = kg.get_statistics()

        assert stats["entity_types"]["FILE"] == 2
        assert stats["entity_types"]["FUNCTION"] == 1
        assert stats["entity_types"]["BUG"] == 1

    def test_get_statistics_density(self):
        """Graph density calculation"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Complete graph: all nodes connected
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_node("C", entity_type="FILE")
        kg.graph.add_edge("A", "B")
        kg.graph.add_edge("B", "C")
        kg.graph.add_edge("A", "C")

        stats = kg.get_statistics()

        # Density should be high (close to 1)
        assert stats["density"] > 0


class TestSaveGraph:
    """Test graph serialization."""

    def test_save_graph_creates_file(self, tmp_path):
        """Save graph to GraphML file"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FUNCTION")
        kg.graph.add_edge("A", "B")

        output_file = tmp_path / "graph.graphml"
        kg.save_graph(str(output_file))

        assert output_file.exists()

    def test_save_graph_can_be_loaded(self, tmp_path):
        """Saved graph can be loaded back"""
        kg = MemoryKnowledgeGraph("/fake/path")
        kg.graph.add_node("A", entity_type="FILE", confidence=0.9)
        kg.graph.add_node("B", entity_type="FUNCTION", confidence=0.8)
        kg.graph.add_edge("A", "B", relation_type="MODIFIES")

        output_file = tmp_path / "graph.graphml"
        kg.save_graph(str(output_file))

        # Load graph back
        loaded = nx.read_graphml(str(output_file))
        assert loaded.number_of_nodes() == 2
        assert loaded.number_of_edges() == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_graph_operations(self):
        """All operations safe on empty graph"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Should not crash
        kg.compute_centrality()
        assert kg.get_top_entities() == []
        assert kg.get_related_entities("anything") == []
        assert kg.get_entity_importance("anything") == 10.0

    def test_disconnected_components(self):
        """Graph with disconnected components"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Component 1: A -> B
        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_node("B", entity_type="FILE")
        kg.graph.add_edge("A", "B")

        # Component 2: C -> D
        kg.graph.add_node("C", entity_type="FILE")
        kg.graph.add_node("D", entity_type="FILE")
        kg.graph.add_edge("C", "D")

        kg.compute_centrality()

        # All nodes should have PageRank
        assert len(kg.pagerank_scores) == 4

        # Traversal should not cross components
        related = kg.get_related_entities("A", max_hops=10)
        assert "B" in related
        assert "C" not in related
        assert "D" not in related

    def test_self_loops(self):
        """Handle self-loops in graph"""
        kg = MemoryKnowledgeGraph("/fake/path")

        kg.graph.add_node("A", entity_type="FILE")
        kg.graph.add_edge("A", "A")  # Self-loop

        kg.compute_centrality()

        # Should not crash
        assert "A" in kg.pagerank_scores

    def test_very_large_co_occurrence(self):
        """Handle very large co-occurrence counts"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="A", context="ctx", confidence=0.9),
            Entity(entity_type="FILE", name="B", context="ctx", confidence=0.9),
        ]

        # Create 100 duplicate relationships
        relationships = [
            Relationship(source="A", relation_type="MODIFIES", target="B", confidence=0.7)
            for _ in range(100)
        ]

        kg.entity_to_memories = {"A": ["mem1"], "B": ["mem1"]}
        kg._build_graph_from_entities(entities, relationships)

        # Should have single edge with high co-occurrence
        assert kg.graph.number_of_edges() == 1
        assert kg.graph["A"]["B"]["co_occurrence"] == 100

    def test_special_characters_in_names(self):
        """Handle special characters in entity names"""
        kg = MemoryKnowledgeGraph("/fake/path")

        entities = [
            Entity(entity_type="FILE", name="file with spaces.py", context="ctx", confidence=0.9),
            Entity(entity_type="BUG", name="error: invalid (parsing)", context="ctx", confidence=0.7),
        ]

        kg.entity_to_memories = {
            "file with spaces.py": ["mem1"],
            "error: invalid (parsing)": ["mem2"]
        }
        kg._build_graph_from_entities(entities, [])

        assert kg.graph.has_node("file with spaces.py")
        assert kg.graph.has_node("error: invalid (parsing)")

    def test_missing_entity_type(self):
        """Handle entities without type gracefully"""
        kg = MemoryKnowledgeGraph("/fake/path")

        # Manually add node without entity_type
        kg.graph.add_node("orphan")

        stats = kg.get_statistics()

        # Should handle unknown type
        assert "unknown" in stats["entity_types"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hooks/knowledge_graph", "--cov-report=term-missing"])
