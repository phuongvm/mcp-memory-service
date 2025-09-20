"""
Shared memory service layer for consistent business logic.

This module provides a unified service layer that both the API and MCP tools
can use to ensure consistent behavior and avoid code duplication.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from ..models.memory import Memory
from ..storage.base import MemoryStorage

logger = logging.getLogger(__name__)


class MemoryService:
    """Shared service for memory operations with consistent business logic."""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
    
    async def list_memories(
        self,
        page: int = 1,
        page_size: int = 10,
        tag: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List memories with pagination and filtering.
        
        This is the single source of truth for memory listing logic,
        used by both API and MCP tools.
        """
        try:
            # Calculate offset for pagination
            offset = (page - 1) * page_size
            
            if tag:
                # Filter by tag - get all matching memories then paginate
                all_tag_memories = await self.storage.search_by_tag([tag])
                
                # Apply memory_type filter if specified
                if memory_type:
                    all_tag_memories = [m for m in all_tag_memories if m.memory_type == memory_type]
                
                # Calculate pagination for tag results
                total = len(all_tag_memories)
                page_memories = all_tag_memories[offset:offset + page_size]
                has_more = offset + page_size < total
            else:
                # Get total count for accurate pagination
                total = await self.storage.count_all_memories()
                
                # Get page of memories using proper pagination
                all_memories = await self.storage.get_all_memories(limit=page_size, offset=offset)
                
                # Apply memory_type filter if specified
                if memory_type:
                    all_memories = [m for m in all_memories if m.memory_type == memory_type]
                    # If filtering by memory_type, we need to adjust total count
                    # This is less efficient but necessary for accurate pagination with filters
                    if memory_type:
                        all_type_memories = await self.storage.get_all_memories()
                        total = len([m for m in all_type_memories if m.memory_type == memory_type])
                
                page_memories = all_memories
                has_more = offset + len(page_memories) < total
            
            return {
                "memories": page_memories,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_more": has_more
            }
            
        except Exception as e:
            logger.error(f"Error in memory service list_memories: {e}")
            raise
    
    def format_memory_response(self, memory: Memory) -> Dict[str, Any]:
        """Format memory for API response."""
        return {
            "content": memory.content,
            "content_hash": memory.content_hash,
            "tags": memory.tags,
            "memory_type": memory.memory_type,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
            "created_at_iso": memory.created_at_iso,
            "updated_at": memory.updated_at,
            "updated_at_iso": memory.updated_at_iso
        }
    
    def format_memory_list_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format memory list response for API."""
        return {
            "memories": [self.format_memory_response(m) for m in result["memories"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "has_more": result["has_more"]
        }
    
    def format_mcp_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format memory list response for MCP tool."""
        return {
            "memories": [self.format_memory_response(m) for m in result["memories"]],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_found": len(result["memories"])  # MCP uses total_found instead of total
        }
    
    async def store_memory(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client_hostname: Optional[str] = None,
        http_request_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Store a new memory with content and optional metadata.
        
        This is the single source of truth for memory storage logic,
        based on the API implementation and used by all interfaces.
        
        Args:
            content: The content to store as memory
            tags: Optional tags to categorize the memory
            memory_type: Type of memory (note, decision, task, reference)
            metadata: Additional metadata for the memory
            client_hostname: Client machine hostname for source tracking
            http_request_headers: Optional HTTP headers for hostname detection
            
        Returns:
            Dictionary with success status, message, content_hash, and memory object
        """
        try:
            from ..utils.hashing import generate_content_hash
            from ..config import INCLUDE_HOSTNAME
            import socket
            
            # Generate content hash (API approach)
            content_hash = generate_content_hash(content)
            
            # Prepare tags and metadata with optional hostname (API approach)
            final_tags = tags or []
            final_metadata = metadata or {}
            
            if INCLUDE_HOSTNAME:
                # Prioritize client-provided hostname, then header, then fallback to server (API approach)
                hostname = None
                
                # 1. Check if client provided hostname in request body
                if client_hostname:
                    hostname = client_hostname
                    
                # 2. Check for X-Client-Hostname header
                elif http_request_headers and http_request_headers.get('X-Client-Hostname'):
                    hostname = http_request_headers.get('X-Client-Hostname')
                    
                # 3. Fallback to server hostname (original behavior)
                else:
                    hostname = socket.gethostname()
                
                source_tag = f"source:{hostname}"
                if source_tag not in final_tags:
                    final_tags.append(source_tag)
                final_metadata["hostname"] = hostname
            
            # Create memory object (API approach)
            memory = Memory(
                content=content,
                content_hash=content_hash,
                tags=final_tags,
                memory_type=memory_type,
                metadata=final_metadata
            )
            
            # Store the memory (API approach)
            success, message = await self.storage.store(memory)
            
            return {
                "success": success,
                "message": message,
                "content_hash": content_hash,
                "memory": memory  # Include memory object for API responses
            }
            
        except Exception as e:
            logger.error(f"Error in memory service store_memory: {e}")
            return {
                "success": False,
                "message": f"Failed to store memory: {str(e)}",
                "content_hash": None,
                "memory": None
            }
    
    async def retrieve_memory(
        self,
        query: str,
        n_results: int = 10,
        similarity_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Retrieve memories based on semantic similarity to a query.
        
        This is the single source of truth for memory retrieval logic,
        based on the API implementation (/api/search) and used by all interfaces.
        
        Args:
            query: Search query for semantic similarity
            n_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold (0.0-1.0)
            
        Returns:
            Dictionary with retrieved memories and metadata
        """
        try:
            import time
            start_time = time.time()
            
            # Perform semantic search using the storage layer (API approach)
            query_results = await self.storage.retrieve(
                query=query,
                n_results=n_results
            )
            
            # Filter by similarity threshold if specified (API approach)
            if similarity_threshold is not None:
                query_results = [
                    result for result in query_results
                    if result.relevance_score and result.relevance_score >= similarity_threshold
                ]
            
            # Convert to search results (API approach - using memory_query_result_to_search_result logic)
            search_results = []
            for result in query_results:
                # Convert MemoryQueryResult to SearchResult format (API approach)
                memory_response = {
                    "content": result.memory.content,
                    "content_hash": result.memory.content_hash,
                    "tags": result.memory.tags,
                    "memory_type": result.memory.memory_type,
                    "created_at": result.memory.created_at,
                    "created_at_iso": result.memory.created_at_iso,
                    "updated_at": result.memory.updated_at,
                    "updated_at_iso": result.memory.updated_at_iso,
                    "metadata": result.memory.metadata
                }
                
                search_result = {
                    "memory": memory_response,
                    "similarity_score": result.relevance_score,
                    "relevance_reason": f"Semantic similarity: {result.relevance_score:.3f}" if result.relevance_score else None
                }
                search_results.append(search_result)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "results": search_results,
                "total_found": len(search_results),
                "query": query,
                "search_type": "semantic",
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in memory service retrieve_memory: {e}")
            return {
                "results": [],
                "total_found": 0,
                "query": query,
                "search_type": "semantic",
                "error": f"Failed to retrieve memories: {str(e)}"
            }
    
    async def search_by_tag(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> Dict[str, Any]:
        """
        Search memories by tags.
        
        This is the single source of truth for tag-based search logic,
        based on the API implementation (/search/by-tag) and used by all interfaces.
        
        Args:
            tags: List of tags to search for
            match_all: If True, memory must have ALL tags; if False, ANY tag
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            import time
            start_time = time.time()
            
            # Validate input (API approach)
            if not tags:
                raise ValueError("At least one tag must be specified")
            
            # Use the storage layer's tag search (API approach)
            memories = await self.storage.search_by_tag(tags)
            
            # If match_all is True, filter to only memories that have ALL tags (API approach)
            if match_all and len(tags) > 1:
                tag_set = set(tags)
                memories = [
                    memory for memory in memories
                    if tag_set.issubset(set(memory.tags))
                ]
            
            # Convert to search results (API approach)
            match_type = "ALL" if match_all else "ANY"
            search_results = []
            for memory in memories:
                # Convert Memory to SearchResult format (API approach)
                memory_response = {
                    "content": memory.content,
                    "content_hash": memory.content_hash,
                    "tags": memory.tags,
                    "memory_type": memory.memory_type,
                    "created_at": memory.created_at,
                    "created_at_iso": memory.created_at_iso,
                    "updated_at": memory.updated_at,
                    "updated_at_iso": memory.updated_at_iso,
                    "metadata": memory.metadata
                }
                
                # Calculate matched tags for relevance reason (API approach)
                matched_tags = set(memory.tags) & set(tags)
                search_result = {
                    "memory": memory_response,
                    "similarity_score": None,  # No similarity score for tag search
                    "relevance_reason": f"Tags match ({match_type}): {', '.join(matched_tags)}"
                }
                search_results.append(search_result)
            
            processing_time = (time.time() - start_time) * 1000
            query_string = f"Tags: {', '.join(tags)} ({match_type})"
            
            return {
                "results": search_results,
                "total_found": len(search_results),
                "query": query_string,
                "search_type": "tag",
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in memory service search_by_tag: {e}")
            match_type = "ALL" if match_all else "ANY"
            query_string = f"Tags: {', '.join(tags)} ({match_type})" if tags else "Tags: []"
            return {
                "results": [],
                "total_found": 0,
                "query": query_string,
                "search_type": "tag",
                "error": f"Failed to search by tags: {str(e)}"
            }
    
    async def delete_memory(
        self,
        content_hash: str
    ) -> Dict[str, Any]:
        """
        Delete a memory by its content hash.
        
        This is the single source of truth for memory deletion logic,
        based on the API implementation (/api/memories/{content_hash}) and used by all interfaces.
        
        Args:
            content_hash: Hash of the memory content to delete
            
        Returns:
            Dictionary with success status, message, and content_hash
        """
        try:
            # Validate input (API approach)
            if not content_hash:
                raise ValueError("Content hash must be specified")
            
            # Delete the memory using storage layer (API approach)
            success, message = await self.storage.delete(content_hash)
            
            return {
                "success": success,
                "message": message,
                "content_hash": content_hash
            }
            
        except Exception as e:
            logger.error(f"Error in memory service delete_memory: {e}")
            return {
                "success": False,
                "message": f"Failed to delete memory: {str(e)}",
                "content_hash": content_hash
            }
    
    async def search_by_time(
        self,
        query: str,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search memories by time-based queries using natural language.
        
        This is the single source of truth for time-based search logic,
        based on the API implementation (/api/search/by-time) and used by all interfaces.
        
        Args:
            query: Natural language time query (e.g., 'yesterday', 'last week', 'this month')
            n_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            import time
            from datetime import datetime
            start_time = time.time()
            
            # Parse time query using helper functions from API (API approach)
            time_filter = self._parse_time_query(query)
            
            if not time_filter:
                return {
                    "results": [],
                    "total_found": 0,
                    "query": query,
                    "search_type": "time",
                    "error": f"Could not parse time query: '{query}'. Try 'yesterday', 'last week', 'this month', etc."
                }
            
            # For now, we'll do a broad search and then filter by time (API approach)
            # TODO: Implement proper time-based search in storage layer
            query_results = await self.storage.retrieve("", n_results=1000)  # Get many results to filter
            
            # Filter by time (API approach)
            filtered_memories = []
            for result in query_results:
                memory_time = None
                if result.memory.created_at:
                    memory_time = datetime.fromtimestamp(result.memory.created_at)
                
                if memory_time and self._is_within_time_range(memory_time, time_filter):
                    filtered_memories.append(result)
            
            # Limit results (API approach)
            filtered_memories = filtered_memories[:n_results]
            
            # Convert to search results (API approach - using memory_query_result_to_search_result logic)
            search_results = []
            for result in filtered_memories:
                # Convert MemoryQueryResult to SearchResult format (API approach)
                memory_response = {
                    "content": result.memory.content,
                    "content_hash": result.memory.content_hash,
                    "tags": result.memory.tags,
                    "memory_type": result.memory.memory_type,
                    "created_at": result.memory.created_at,
                    "created_at_iso": result.memory.created_at_iso,
                    "updated_at": result.memory.updated_at,
                    "updated_at_iso": result.memory.updated_at_iso,
                    "metadata": result.memory.metadata
                }
                
                search_result = {
                    "memory": memory_response,
                    "similarity_score": result.relevance_score,
                    "relevance_reason": f"Time match: {query}"
                }
                search_results.append(search_result)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "results": search_results,
                "total_found": len(search_results),
                "query": query,
                "search_type": "time",
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in memory service search_by_time: {e}")
            return {
                "results": [],
                "total_found": 0,
                "query": query,
                "search_type": "time",
                "error": f"Failed to search by time: {str(e)}"
            }
    
    def _parse_time_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural language time queries into time ranges.
        
        This is a basic implementation based on the API implementation.
        Can be enhanced with more sophisticated natural language processing later.
        """
        from datetime import datetime, timedelta
        
        query_lower = query.lower().strip()
        now = datetime.now()
        
        # Define time mappings (API approach)
        if query_lower in ['yesterday']:
            start = now - timedelta(days=1)
            end = now
            return {'start': start.replace(hour=0, minute=0, second=0), 'end': start.replace(hour=23, minute=59, second=59)}
        
        elif query_lower in ['today']:
            return {'start': now.replace(hour=0, minute=0, second=0), 'end': now}
        
        elif query_lower in ['last week', 'past week']:
            start = now - timedelta(weeks=1)
            return {'start': start, 'end': now}
        
        elif query_lower in ['last month', 'past month']:
            start = now - timedelta(days=30)
            return {'start': start, 'end': now}
        
        elif query_lower in ['this week']:
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            start = now - timedelta(days=days_since_monday)
            return {'start': start.replace(hour=0, minute=0, second=0), 'end': now}
        
        elif query_lower in ['this month']:
            start = now.replace(day=1, hour=0, minute=0, second=0)
            return {'start': start, 'end': now}
        
        # Add more time expressions as needed
        return None
    
    def _is_within_time_range(self, memory_time: datetime, time_filter: Dict[str, Any]) -> bool:
        """Check if a memory's timestamp falls within the specified time range."""
        start_time = time_filter.get('start')
        end_time = time_filter.get('end')
        
        if start_time and end_time:
            return start_time <= memory_time <= end_time
        elif start_time:
            return memory_time >= start_time
        elif end_time:
            return memory_time <= end_time
        
        return True
    
    async def search_similar(
        self,
        content_hash: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search for memories similar to a given memory by content hash.
        
        This is the single source of truth for similar memory search logic,
        based on the API implementation (/api/search/similar/{content_hash}) and used by all interfaces.
        
        Args:
            content_hash: Content hash of the memory to find similar ones for
            limit: Maximum number of similar memories to return
            
        Returns:
            Dictionary with similar memories and metadata
        """
        try:
            import time
            start_time = time.time()
            
            # Get the target memory first (API approach)
            target_memory = await self.storage.get_by_hash(content_hash)
            if not target_memory:
                return {
                    "success": False,
                    "message": "Memory not found",
                    "target_memory": None,
                    "similar_memories": [],
                    "total_found": 0
                }
            
            # Find similar memories using the target memory's content (API approach)
            similar_results = await self.storage.retrieve(
                query=target_memory.content,
                n_results=limit + 1  # +1 because the original will be included
            )
            
            # Filter out the original memory (API approach)
            filtered_results = [
                result for result in similar_results
                if result.memory.content_hash != content_hash
            ][:limit]
            
            # Convert to search results (API approach - using memory_query_result_to_search_result logic)
            search_results = []
            for result in filtered_results:
                # Convert MemoryQueryResult to SearchResult format (API approach)
                memory_response = {
                    "content": result.memory.content,
                    "content_hash": result.memory.content_hash,
                    "tags": result.memory.tags,
                    "memory_type": result.memory.memory_type,
                    "created_at": result.memory.created_at,
                    "created_at_iso": result.memory.created_at_iso,
                    "updated_at": result.memory.updated_at,
                    "updated_at_iso": result.memory.updated_at_iso,
                    "metadata": result.memory.metadata
                }
                
                search_result = {
                    "memory": memory_response,
                    "similarity_score": result.relevance_score,
                    "relevance_reason": f"Similar to target memory: {result.relevance_score:.3f}" if result.relevance_score else None
                }
                search_results.append(search_result)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "target_memory": {
                    "content": target_memory.content,
                    "content_hash": target_memory.content_hash,
                    "tags": target_memory.tags,
                    "memory_type": target_memory.memory_type,
                    "created_at": target_memory.created_at_iso
                },
                "results": search_results,
                "total_found": len(search_results),
                "query": f"Similar to: {target_memory.content[:50]}...",
                "search_type": "similar",
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in memory service search_similar: {e}")
            return {
                "success": False,
                "message": f"Failed to search similar memories: {str(e)}",
                "target_memory": None,
                "results": [],
                "total_found": 0,
                "query": f"Similar to content_hash: {content_hash}",
                "search_type": "similar",
                "error": f"Failed to search similar memories: {str(e)}"
            }
    
    async def check_database_health(self) -> Dict[str, Any]:
        """
        Check the health and status of the memory database.
        
        This is the single source of truth for database health logic,
        based on the MCP Server implementation and used by all interfaces.
        
        Returns:
            Dictionary with health status, backend info, and statistics
        """
        try:
            import inspect
            from datetime import datetime
            
            # Get health status and statistics (handle both async and sync get_stats)
            if inspect.iscoroutinefunction(self.storage.get_stats):
                stats = await self.storage.get_stats()
            else:
                stats = self.storage.get_stats()
            
            # Check for error in stats
            if "error" in stats:
                return {
                    "status": "error",
                    "backend": self.storage.__class__.__name__,
                    "error": f"Storage backend error: {stats['error']}"
                }
            
            # Map storage backend fields to consistent health check format
            storage_size = "unknown"
            if "database_size_mb" in stats:
                storage_size = f"{stats['database_size_mb']} MB"
            elif "storage_size" in stats:
                storage_size = stats["storage_size"]
            
            total_tags = stats.get("total_tags", stats.get("unique_tags", 0))
            
            return {
                "status": "healthy",
                "backend": self.storage.__class__.__name__,
                "statistics": {
                    "total_memories": stats.get("total_memories", 0),
                    "total_tags": total_tags,
                    "storage_size": storage_size,
                    "last_backup": stats.get("last_backup", "never"),
                    "embedding_model": stats.get("embedding_model"),
                    "embedding_dimension": stats.get("embedding_dimension")
                },
                "timestamp": stats.get("timestamp", datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Error in memory service check_database_health: {e}")
            return {
                "status": "error",
                "backend": "unknown",
                "error": f"Health check failed: {str(e)}"
            }