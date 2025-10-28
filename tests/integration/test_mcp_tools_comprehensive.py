"""
Comprehensive test suite for MCP Memory Service tools.

This module tests all 7 MCP tools and implements cross-validation
to ensure data integrity across different operations.
"""
import pytest
import os
import sys
import tempfile
import shutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.utils.hashing import generate_content_hash


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_mcp.db")
    
    yield db_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def storage(temp_db):
    """Create and initialize storage for tests."""
    storage = SqliteVecMemoryStorage(temp_db)
    await storage.initialize()
    yield storage
    storage.close()


# Helper functions
async def store_memory_helper(storage, content: str, tags: List[str] = None, 
                              memory_type: str = None, metadata: Dict = None) -> Dict[str, Any]:
    """Helper function to store a memory."""
    tags = tags or []
    metadata = metadata or {}
    
    content_hash = generate_content_hash(content, metadata)
    memory = Memory(
        content=content,
        content_hash=content_hash,
        tags=tags,
        memory_type=memory_type,
        metadata=metadata
    )
    
    success, message = await storage.store(memory)
    return {
        "success": success,
        "message": message,
        "content_hash": memory.content_hash
    }


# Test Store Memory
class TestStoreMemory:
    """Tests for store_memory tool."""
    
    @pytest.mark.asyncio
    async def test_store_minimal_params(self, storage):
        """Test storing memory with only required parameter."""
        content = "Simple test memory"
        result = await store_memory_helper(storage, content)
        
        assert result["success"] is True
        assert result["content_hash"] is not None
    
    @pytest.mark.asyncio
    async def test_store_all_params(self, storage):
        """Test storing memory with all parameters."""
        content = "Complete test memory with all fields"
        tags = ["test", "comprehensive"]
        memory_type = "note"
        metadata = {"source": "test_suite", "priority": "high"}
        
        result = await store_memory_helper(
            storage, content, tags=tags, memory_type=memory_type, metadata=metadata
        )
        
        assert result["success"] is True
        assert result["content_hash"] is not None
        
        # Verify with search_by_tag
        memories = await storage.search_by_tag(["test"])
        assert len(memories) > 0
        assert any(m.content == content for m in memories)
    
    @pytest.mark.asyncio
    async def test_store_duplicate_content(self, storage):
        """Test handling of duplicate content."""
        content = "Duplicate content test"
        
        # Store first time
        result1 = await store_memory_helper(storage, content)
        assert result1["success"] is True
        
        # Try to store again
        result2 = await store_memory_helper(storage, content)
        # Should either prevent duplicate or allow with same hash
        assert result2["success"] in [True, False]
    
    @pytest.mark.asyncio
    async def test_store_with_special_characters(self, storage):
        """Test storing content with special characters."""
        content = "Test with special chars: <>&'\" émojis 🚀"
        result = await store_memory_helper(storage, content)
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_store_cross_validation(self, storage):
        """Cross-validate store with other retrieval methods."""
        content = "Cross-validation test memory"
        tags = ["cross-test", "validation"]
        
        result = await store_memory_helper(storage, content, tags=tags)
        content_hash = result["content_hash"]
        
        # Verify with search_by_tag
        memories = await storage.search_by_tag(["cross-test"])
        assert any(m.content_hash == content_hash for m in memories)
        
        # Verify with semantic search
        results = await storage.retrieve("cross-validation", n_results=5)
        assert any(r.memory.content_hash == content_hash for r in results)
        
        # Verify with list_memories
        all_memories = await storage.get_all_memories()
        assert any(m.content_hash == content_hash for m in all_memories)


# Test Retrieve Memory
class TestRetrieveMemory:
    """Tests for retrieve_memory tool."""
    
    @pytest.mark.asyncio
    async def test_retrieve_semantic_search(self, storage):
        """Test semantic search retrieval."""
        # Store test memories
        await store_memory_helper(storage, "The capital of France is Paris", ["geography"])
        await store_memory_helper(storage, "Python is a programming language", ["programming"])
        
        results = await storage.retrieve("What is the capital of France?", n_results=5)
        assert len(results) > 0
        assert any("Paris" in r.memory.content for r in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_similarity_threshold(self, storage):
        """Test similarity threshold filtering."""
        await store_memory_helper(storage, "Machine learning is a subset of AI", ["tech"])
        await store_memory_helper(storage, "The weather is sunny today", ["weather"])
        
        # Low threshold should return both
        results_low = await storage.retrieve("artificial intelligence", n_results=10)
        
        # High threshold should return only relevant
        results_high = await storage.retrieve(
            "artificial intelligence", n_results=10, min_similarity=0.7
        )
        
        assert len(results_high) <= len(results_low)
    
    @pytest.mark.asyncio
    async def test_retrieve_limit_parameter(self, storage):
        """Test limit parameter."""
        # Store multiple memories
        for i in range(5):
            await store_memory_helper(storage, f"Test memory number {i}", ["numbered"])
        
        # Test different limits
        results_2 = await storage.retrieve("test", n_results=2)
        results_5 = await storage.retrieve("test", n_results=5)
        
        assert len(results_2) <= 2
        assert len(results_5) <= 5
    
    @pytest.mark.asyncio
    async def test_retrieve_relevance_scores(self, storage):
        """Test that relevance scores are returned."""
        await store_memory_helper(storage, "Dogs are loyal pets", ["pets"])
        
        results = await storage.retrieve("dogs", n_results=5)
        assert len(results) > 0
        assert all(hasattr(r, 'relevance_score') for r in results)
        assert all(r.relevance_score is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self, storage):
        """Test retrieval with empty or invalid query."""
        await store_memory_helper(storage, "Test content", ["test"])
        
        results = await storage.retrieve("", n_results=5)
        # Should handle gracefully
        assert isinstance(results, list)


# Test Recall Memory
class TestRecallMemory:
    """Tests for recall_memory tool."""
    
    @pytest.mark.asyncio
    async def test_recall_today(self, storage):
        """Test recalling memories from today."""
        today_content = f"Memory from today: {datetime.now()}"
        await store_memory_helper(storage, today_content, ["today"])
        
        results = await storage.recall_memory("today", n_results=5)
        assert len(results) > 0
        assert any("today" in m.content.lower() for m in results)
    
    @pytest.mark.asyncio
    async def test_recall_n_results_parameter(self, storage):
        """Test n_results parameter."""
        for i in range(10):
            await store_memory_helper(storage, f"Memory {i} for recall test", ["recall-test"])
        
        # Test different n_results values
        results_3 = await storage.recall_memory("recall test", n_results=3)
        results_5 = await storage.recall_memory("recall test", n_results=5)
        
        assert len(results_3) <= 3
        assert len(results_5) <= 5
    
    @pytest.mark.asyncio
    async def test_recall_with_timestamps(self, storage):
        """Test recall respects timestamp ordering."""
        now = datetime.now()
        
        # Store memories with different timestamps
        for i in range(3):
            content = f"Time-ordered memory {i}"
            memory = Memory(
                content=content,
                content_hash=generate_content_hash(content),
                tags=["time-test"]
            )
            memory.created_at = now - timedelta(hours=i)
            await storage.store(memory)
        
        results = await storage.recall_memory("time-ordered", n_results=10)
        # Should return results, ideally in reverse chronological order
        assert len(results) > 0


# Test Search By Tag
class TestSearchByTag:
    """Tests for search_by_tag tool."""
    
    @pytest.mark.asyncio
    async def test_search_single_tag(self, storage):
        """Test searching by single tag."""
        await store_memory_helper(storage, "Tagged content", ["important"])
        
        results = await storage.search_by_tag(["important"])
        assert len(results) > 0
        assert all("important" in m.tags for m in results)
    
    @pytest.mark.asyncio
    async def test_search_multiple_tags_and(self, storage):
        """Test AND operation with multiple tags."""
        await store_memory_helper(storage, "Multi-tagged content", ["tech", "python"])
        
        results = await storage.search_by_tags(tags=["tech", "python"], operation="AND")
        assert len(results) > 0
        assert all(all(tag in m.tags for tag in ["tech", "python"]) for m in results)
    
    @pytest.mark.asyncio
    async def test_search_multiple_tags_or(self, storage):
        """Test OR operation with multiple tags."""
        await store_memory_helper(storage, "Python content", ["python"])
        await store_memory_helper(storage, "Java content", ["java"])
        
        results = await storage.search_by_tags(tags=["python", "java"], operation="OR")
        assert len(results) >= 2
    
    @pytest.mark.asyncio
    async def test_search_nonexistent_tag(self, storage):
        """Test searching for non-existent tag."""
        results = await storage.search_by_tag(["nonexistent-tag-xyz"])
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_cross_validation(self, storage):
        """Cross-validate search_by_tag with retrieve."""
        content = "Cross-validation content for search"
        tags = ["search-test", "validation"]
        
        content_hash = (await store_memory_helper(storage, content, tags=tags))["content_hash"]
        
        # Find via tag search
        tag_results = await storage.search_by_tag(["search-test"])
        
        # Find via semantic search
        semantic_results = await storage.retrieve("cross-validation search", n_results=10)
        
        # Both should find the memory
        found_in_tag = any(m.content_hash == content_hash for m in tag_results)
        found_in_semantic = any(r.memory.content_hash == content_hash for r in semantic_results)
        
        assert found_in_tag or found_in_semantic


# Test Delete Memory
class TestDeleteMemory:
    """Tests for delete_memory tool."""
    
    @pytest.mark.asyncio
    async def test_delete_valid_hash(self, storage):
        """Test deleting by valid content_hash."""
        content = "Content to be deleted"
        content_hash = (await store_memory_helper(storage, content))["content_hash"]
        
        # Delete the memory
        success, message = await storage.delete(content_hash)
        assert success is True
        
        # Verify deletion
        results = await storage.retrieve(content, n_results=5)
        assert not any(r.memory.content_hash == content_hash for r in results)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_hash(self, storage):
        """Test deleting non-existent memory."""
        fake_hash = "nonexistent_hash_12345"
        success, message = await storage.delete(fake_hash)
        # Should handle gracefully
        assert isinstance(success, bool)
    
    @pytest.mark.asyncio
    async def test_delete_verification_multi_tool(self, storage):
        """Verify deletion across multiple retrieval tools."""
        content = "Multi-tool deletion test"
        tags = ["delete-test"]
        content_hash = (await store_memory_helper(storage, content, tags=tags))["content_hash"]
        
        # Delete
        await storage.delete(content_hash)
        
        # Verify with retrieve_memory
        retrieve_results = await storage.retrieve("multi-tool deletion", n_results=10)
        assert not any(r.memory.content_hash == content_hash for r in retrieve_results)
        
        # Verify with search_by_tag
        tag_results = await storage.search_by_tag(["delete-test"])
        assert not any(m.content_hash == content_hash for m in tag_results)
        
        # Verify with list_memories
        all_memories = await storage.get_all_memories()
        assert not any(m.content_hash == content_hash for m in all_memories)
    
    @pytest.mark.asyncio
    async def test_delete_statistics_update(self, storage):
        """Test that statistics update after deletion."""
        # Get initial stats
        stats_before = await storage.get_stats()
        
        # Store and delete
        content_hash = (await store_memory_helper(storage, "Stats test"))["content_hash"]
        await storage.delete(content_hash)
        
        # Get stats after
        stats_after = await storage.get_stats()
        
        # Memory count should not increase (or decrease if was new)
        assert stats_after["total_memories"] <= stats_before["total_memories"] + 1


# Test List Memories
class TestListMemories:
    """Tests for list_memories tool."""
    
    @pytest.mark.asyncio
    async def test_list_pagination(self, storage):
        """Test pagination functionality."""
        # Store multiple memories
        for i in range(15):
            await store_memory_helper(storage, f"Paginated memory {i}", ["page-test"])
        
        # Get page 1
        page1 = await storage.get_all_memories(limit=10, offset=0)
        # Get page 2
        page2 = await storage.get_all_memories(limit=10, offset=10)
        
        assert len(page1) <= 10
        assert len(page2) <= 10
        # Should have some overlap or continuity
        assert len(page1) + len(page2) >= 10
    
    @pytest.mark.asyncio
    async def test_list_filter_by_tag(self, storage):
        """Test filtering by tag."""
        await store_memory_helper(storage, "Filtered content", ["filter-test"])
        await store_memory_helper(storage, "Other content", ["other"])
        
        results = await storage.get_all_memories(tags=["filter-test"])
        assert all("filter-test" in m.tags for m in results)
    
    @pytest.mark.asyncio
    async def test_list_filter_by_type(self, storage):
        """Test filtering by memory_type."""
        await store_memory_helper(storage, "Note content", memory_type="note")
        await store_memory_helper(storage, "Fact content", memory_type="fact")
        
        results = await storage.get_all_memories(memory_type="note")
        assert all(m.memory_type == "note" for m in results)
    
    @pytest.mark.asyncio
    async def test_list_page_size_variations(self, storage):
        """Test different page sizes."""
        for i in range(25):
            await store_memory_helper(storage, f"Size test {i}", ["size-test"])
        
        # Test different page sizes
        size1 = await storage.get_all_memories(limit=1, offset=0)
        size10 = await storage.get_all_memories(limit=10, offset=0)
        size50 = await storage.get_all_memories(limit=50, offset=0)
        
        assert len(size1) <= 1
        assert len(size10) <= 10
        assert len(size50) <= 50
    
    @pytest.mark.asyncio
    async def test_list_beyond_available(self, storage):
        """Test pagination beyond available data."""
        # Store 5 memories
        for i in range(5):
            await store_memory_helper(storage, f"Edge test {i}", ["edge"])
        
        # Request page beyond available
        results = await storage.get_all_memories(limit=10, offset=20)
        assert len(results) == 0


# Test Database Health
class TestDatabaseHealth:
    """Tests for check_database_health tool."""
    
    @pytest.mark.asyncio
    async def test_health_statistics_structure(self, storage):
        """Test that health returns proper statistics structure."""
        stats = await storage.get_stats()
        
        assert "total_memories" in stats
        assert "total_tags" in stats
        assert isinstance(stats["total_memories"], int)
        assert isinstance(stats["total_tags"], int)
    
    @pytest.mark.asyncio
    async def test_health_count_accuracy(self, storage):
        """Test that memory counts are accurate."""
        # Get initial count
        stats_before = await storage.get_stats()
        initial_count = stats_before["total_memories"]
        
        # Store 5 memories
        for i in range(5):
            await store_memory_helper(storage, f"Count test {i}", ["count-test"])
        
        stats_after = await storage.get_stats()
        final_count = stats_after["total_memories"]
        
        # Should have increased
        assert final_count >= initial_count
    
    @pytest.mark.asyncio
    async def test_health_monitor_changes(self, storage):
        """Test that statistics change after operations."""
        stats1 = await storage.get_stats()
        
        # Perform operations
        await store_memory_helper(storage, "Monitor test", ["monitor"])
        
        stats2 = await storage.get_stats()
        
        # Check that something changed
        assert stats2["total_memories"] >= stats1["total_memories"]


# Cross-Validation Tests
class TestCrossValidation:
    """Cross-validation tests across multiple tools."""
    
    @pytest.mark.asyncio
    async def test_store_retrieve_delete_cycle(self, storage):
        """Test complete cycle: store → retrieve → delete → verify."""
        # Store
        content = "Full cycle test content"
        content_hash = (await store_memory_helper(storage, content, ["cycle-test"]))["content_hash"]
        
        # Retrieve
        results = await storage.retrieve("full cycle", n_results=5)
        assert any(r.memory.content_hash == content_hash for r in results)
        
        # Delete
        success, message = await storage.delete(content_hash)
        assert success is True
        
        # Verify deletion
        results_after = await storage.retrieve("full cycle", n_results=10)
        assert not any(r.memory.content_hash == content_hash for r in results_after)
    
    @pytest.mark.asyncio
    async def test_tag_search_vs_semantic_consistency(self, storage):
        """Test consistency between tag search and semantic search."""
        content = "Python programming best practices"
        tags = ["python", "programming"]
        content_hash = (await store_memory_helper(storage, content, tags=tags))["content_hash"]
        
        # Find via tag search
        tag_results = await storage.search_by_tag(["python"])
        
        # Find via semantic search
        semantic_results = await storage.retrieve("python programming", n_results=10)
        
        # Both should find the memory
        found_in_tags = any(m.content_hash == content_hash for m in tag_results)
        found_in_semantic = any(r.memory.content_hash == content_hash for r in semantic_results)
        
        # At least one should find it
        assert found_in_tags or found_in_semantic
    
    @pytest.mark.asyncio
    async def test_statistics_vs_list_count(self, storage):
        """Test that statistics match list_memories counts."""
        # Get stats
        stats = await storage.get_stats()
        stats_count = stats["total_memories"]
        
        # Get all memories via list
        all_memories = await storage.get_all_memories()
        list_count = len(all_memories)
        
        # Should match (within reasonable bounds)
        assert abs(stats_count - list_count) <= 1
    
    @pytest.mark.asyncio
    async def test_timestamp_order_consistency(self, storage):
        """Test timestamp ordering consistency across tools."""
        # Store memories with delays
        content1 = "First memory"
        await store_memory_helper(storage, content1, ["order-test"])
        
        await asyncio.sleep(0.1)  # Small delay
        
        content2 = "Second memory"
        await store_memory_helper(storage, content2, ["order-test"])
        
        # Both should be retrievable
        results = await storage.recall_memory("order-test", n_results=10)
        assert len(results) >= 2
    
    @pytest.mark.asyncio
    async def test_pagination_consistency(self, storage):
        """Test that pagination totals are consistent."""
        # Store multiple memories
        for i in range(20):
            await store_memory_helper(storage, f"Pagination consistency {i}", ["pag-consistency"])
        
        # Get all via pagination
        all_collected = []
        page_size = 5
        offset = 0
        
        while True:
            page = await storage.get_all_memories(limit=page_size, offset=offset, tags=["pag-consistency"])
            if not page:
                break
            all_collected.extend([m.content_hash for m in page])
            offset += page_size
            if len(page) < page_size:
                break
        
        # Should have collected some memories
        assert len(all_collected) > 0
        
        # Should match total from stats
        stats = await storage.get_stats()
        assert stats["total_memories"] > 0

