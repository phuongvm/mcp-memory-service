#!/usr/bin/env python3
"""
FastAPI MCP Server for Memory Service

This module implements a native MCP server using the FastAPI MCP framework,
replacing the Node.js HTTP-to-MCP bridge to resolve SSL connectivity issues
and provide direct MCP protocol support.

Features:
- Native MCP protocol implementation using FastMCP
- Direct integration with existing memory storage backends
- Streamable HTTP transport for remote access
- All 22 core memory operations (excluding dashboard tools)
- SSL/HTTPS support with proper certificate handling
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
import os
import sys
import socket
from pathlib import Path

# Add src to path for imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent.parent
sys.path.insert(0, str(src_dir))

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent

# Import existing memory service components
from .config import (
    CHROMA_PATH, COLLECTION_METADATA, STORAGE_BACKEND, 
    CONSOLIDATION_ENABLED, EMBEDDING_MODEL_NAME, INCLUDE_HOSTNAME,
    CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_VECTORIZE_INDEX,
    CLOUDFLARE_D1_DATABASE_ID, CLOUDFLARE_R2_BUCKET, CLOUDFLARE_EMBEDDING_MODEL,
    CLOUDFLARE_LARGE_CONTENT_THRESHOLD, CLOUDFLARE_MAX_RETRIES, CLOUDFLARE_BASE_DELAY
)
from .storage.base import MemoryStorage

def get_storage_backend():
    """Dynamically select and import storage backend based on configuration and availability."""
    backend = STORAGE_BACKEND.lower()
    
    if backend == "sqlite-vec" or backend == "sqlite_vec":
        try:
            from .storage.sqlite_vec import SqliteVecMemoryStorage
            return SqliteVecMemoryStorage
        except ImportError as e:
            logger.error(f"Failed to import SQLite-vec storage: {e}")
            raise
    elif backend == "chroma":
        try:
            from .storage.chroma import ChromaStorage
            return ChromaStorage
        except ImportError:
            logger.warning("ChromaDB not available, falling back to SQLite-vec")
            try:
                from .storage.sqlite_vec import SqliteVecStorage
                return SqliteVecStorage
            except ImportError as e:
                logger.error(f"Failed to import fallback SQLite-vec storage: {e}")
                raise
    elif backend == "cloudflare":
        try:
            from .storage.cloudflare import CloudflareStorage
            return CloudflareStorage
        except ImportError as e:
            logger.error(f"Failed to import Cloudflare storage: {e}")
            raise
    else:
        logger.warning(f"Unknown storage backend '{backend}', defaulting to SQLite-vec")
        try:
            from .storage.sqlite_vec import SqliteVecMemoryStorage
            return SqliteVecMemoryStorage
        except ImportError as e:
            logger.error(f"Failed to import default SQLite-vec storage: {e}")
            raise
from .models.memory import Memory

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)
logger.info(f"Logging level set to: {log_level}")

@dataclass
class MCPServerContext:
    """Application context for the MCP server with all required components."""
    storage: MemoryStorage

@asynccontextmanager
async def mcp_server_lifespan(server: FastMCP) -> AsyncIterator[MCPServerContext]:
    """Manage MCP server lifecycle with proper resource initialization and cleanup."""
    logger.info("Initializing MCP Memory Service components...")
    
    # Initialize storage backend based on configuration and availability
    StorageClass = get_storage_backend()
    
    if StorageClass.__name__ == "SqliteVecMemoryStorage":
        storage = StorageClass(
            db_path=CHROMA_PATH / "memory.db",
            embedding_manager=None  # Will be set after creation
        )
    elif StorageClass.__name__ == "CloudflareStorage":
        storage = StorageClass(
            api_token=CLOUDFLARE_API_TOKEN,
            account_id=CLOUDFLARE_ACCOUNT_ID,
            vectorize_index=CLOUDFLARE_VECTORIZE_INDEX,
            d1_database_id=CLOUDFLARE_D1_DATABASE_ID,
            r2_bucket=CLOUDFLARE_R2_BUCKET,
            embedding_model=CLOUDFLARE_EMBEDDING_MODEL,
            large_content_threshold=CLOUDFLARE_LARGE_CONTENT_THRESHOLD,
            max_retries=CLOUDFLARE_MAX_RETRIES,
            base_delay=CLOUDFLARE_BASE_DELAY
        )
    else:  # ChromaStorage
        storage = StorageClass(
            path=str(CHROMA_PATH),
            collection_name=COLLECTION_METADATA.get("name", "memories")
        )
    
    # Initialize storage backend
    await storage.initialize()
    
    try:
        yield MCPServerContext(
            storage=storage
        )
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down MCP Memory Service components...")
        if hasattr(storage, 'close'):
            await storage.close()

# Create FastMCP server instance
mcp = FastMCP(
    name="MCP Memory Service", 
    host="0.0.0.0",  # Listen on all interfaces for remote access
    port=8000,       # Default port
    lifespan=mcp_server_lifespan,
    stateless_http=True  # Enable stateless HTTP for Claude Code compatibility
)

# =============================================================================
# CORE MEMORY OPERATIONS
# =============================================================================

@mcp.tool()
async def store_memory(
    content: str,
    ctx: Context,
    tags: Optional[List[str]] = None,
    memory_type: str = "note",
    metadata: Optional[Dict[str, Any]] = None,
    client_hostname: Optional[str] = None
) -> Dict[str, Union[bool, str]]:
    """
    Store a new memory with content and optional metadata.
    
    Args:
        content: The content to store as memory
        tags: Optional tags to categorize the memory
        memory_type: Type of memory (note, decision, task, reference)
        metadata: Additional metadata for the memory
        client_hostname: Client machine hostname for source tracking
    
    Returns:
        Dictionary with success status and message
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.store_memory(
            content=content,
            tags=tags,
            memory_type=memory_type,
            metadata=metadata,
            client_hostname=client_hostname
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "content_hash": result["content_hash"]
        }
        
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {
            "success": False,
            "message": f"Failed to store memory: {str(e)}"
        }

@mcp.tool()
async def retrieve_memory(
    query: str,
    ctx: Context,
    n_results: int = 5,
    min_similarity: float = 0.0
) -> Dict[str, Any]:
    """
    Retrieve memories based on semantic similarity to a query.
    
    Args:
        query: Search query for semantic similarity
        n_results: Maximum number of results to return
        min_similarity: Minimum similarity score threshold
    
    Returns:
        Dictionary with retrieved memories and metadata
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.retrieve_memory(
            query=query,
            n_results=n_results,
            similarity_threshold=min_similarity if min_similarity > 0 else None
        )
        
        # Convert service result to MCP format
        memories = []
        for item in result["results"]:
            memories.append({
                "content": item["memory"]["content"],
                "content_hash": item["memory"]["content_hash"],
                "tags": item["memory"]["tags"],
                "memory_type": item["memory"]["memory_type"],
                "created_at": item["memory"]["created_at"],
                "similarity_score": item["similarity_score"],
                "relevance_reason": item["relevance_reason"]
            })
        
        return {
            "memories": memories,
            "query": result["query"],
            "total_results": result["total_found"]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        return {
            "memories": [],
            "query": query,
            "error": f"Failed to retrieve memories: {str(e)}"
        }

@mcp.tool()
async def search_by_tag(
    tags: Union[str, List[str]],
    ctx: Context,
    match_all: bool = False
) -> Dict[str, Any]:
    """
    Search memories by tags.
    
    Args:
        tags: Tag or list of tags to search for
        match_all: If True, memory must have ALL tags; if False, ANY tag
    
    Returns:
        Dictionary with matching memories
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        memory_service = MemoryService(storage)
        
        # Normalize tags to list
        if isinstance(tags, str):
            tags = [tags]
        
        # Use shared service for consistent logic
        result = await memory_service.search_by_tag(
            tags=tags,
            match_all=match_all
        )
        
        # Check for errors from service
        if "error" in result:
            return {
                "memories": [],
                "search_tags": tags,
                "match_all": match_all,
                "error": result["error"]
            }
        
        # Convert service result to MCP format
        mcp_memories = []
        for item in result["results"]:
            mcp_memories.append({
                "content": item["memory"]["content"],
                "content_hash": item["memory"]["content_hash"],
                "tags": item["memory"]["tags"],
                "memory_type": item["memory"]["memory_type"],
                "created_at": item["memory"]["created_at"]
            })
        
        return {
            "memories": mcp_memories,
            "search_tags": tags,
            "match_all": match_all,
            "total_results": result["total_found"]
        }
        
    except Exception as e:
        logger.error(f"Error searching by tags: {e}")
        return {
            "memories": [],
            "search_tags": tags,
            "match_all": match_all,
            "error": f"Failed to search by tags: {str(e)}"
        }

@mcp.tool()
async def delete_memory(
    content_hash: str,
    ctx: Context
) -> Dict[str, Union[bool, str]]:
    """
    Delete a specific memory by its content hash.
    
    Args:
        content_hash: Hash of the memory content to delete
    
    Returns:
        Dictionary with success status and message
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.delete_memory(content_hash)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "content_hash": result["content_hash"]
        }
        
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return {
            "success": False,
            "message": f"Failed to delete memory: {str(e)}",
            "content_hash": content_hash
        }

@mcp.tool()
async def check_database_health(ctx: Context) -> Dict[str, Any]:
    """
    Check the health and status of the memory database.
    
    Returns:
        Dictionary with health status and statistics
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.check_database_health()
        
        return result
        
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        return {
            "status": "error",
            "backend": "unknown",
            "error": f"Health check failed: {str(e)}"
        }

@mcp.tool()
async def list_memories(
    ctx: Context,
    page: int = 1,
    page_size: int = 10,
    tag: Optional[str] = None,
    memory_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    List memories with pagination and optional filtering.
    
    Args:
        page: Page number (1-based)
        page_size: Number of memories per page
        tag: Filter by specific tag
        memory_type: Filter by memory type
    
    Returns:
        Dictionary with memories and pagination info
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.list_memories(
            page=page,
            page_size=page_size,
            tag=tag,
            memory_type=memory_type
        )
        
        # Format for MCP response
        return memory_service.format_mcp_response(result)
        
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        return {
            "memories": [],
            "page": page,
            "page_size": page_size,
            "error": f"Failed to list memories: {str(e)}"
        }

@mcp.tool()
async def search_by_time(
    query: str,
    ctx: Context,
    n_results: int = 10
) -> Dict[str, Any]:
    """
    Search memories by time-based queries using natural language.
    
    Args:
        query: Natural language time query (e.g., 'last week', 'yesterday', 'this month')
        n_results: Maximum number of memories to return
    
    Returns:
        Dictionary with matching memories
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_by_time(
            query=query,
            n_results=n_results
        )
        
        # Check for errors from service
        if "error" in result:
            return {
                "memories": [],
                "query": query,
                "error": result["error"]
            }
        
        # Convert service result to MCP format
        memories = []
        for item in result["results"]:
            memories.append({
                "content": item["memory"]["content"],
                "content_hash": item["memory"]["content_hash"],
                "tags": item["memory"]["tags"],
                "memory_type": item["memory"]["memory_type"],
                "created_at": item["memory"]["created_at_iso"],
                "updated_at": item["memory"]["updated_at_iso"]
            })
        
        return {
            "memories": memories,
            "query": query,
            "total_found": result["total_found"]
        }
        
    except Exception as e:
        logger.error(f"Error searching by time: {e}")
        return {
            "memories": [],
            "query": query,
            "error": f"Failed to search by time: {str(e)}"
        }

@mcp.tool()
async def search_similar(
    content_hash: str,
    ctx: Context,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search for memories similar to a given memory by content hash.
    
    Args:
        content_hash: Content hash of the memory to find similar ones for
        limit: Maximum number of similar memories to return
    
    Returns:
        Dictionary with similar memories
    """
    try:
        from .services.memory_service import MemoryService
        
        storage = ctx.request_context.lifespan_context.storage
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_similar(
            content_hash=content_hash,
            limit=limit
        )
        
        # Check for service-level errors
        if not result.get("success", True):
            return {
                "success": False,
                "message": result.get("message", "Unknown error occurred")
            }
        
        # Convert service result to MCP format
        similar_memories = []
        for item in result["results"]:
            similar_memories.append({
                "content": item["memory"]["content"],
                "content_hash": item["memory"]["content_hash"],
                "tags": item["memory"]["tags"],
                "similarity_score": item["similarity_score"],
                "created_at": item["memory"]["created_at_iso"]
            })
        
        return {
            "success": True,
            "target_memory": result["target_memory"],
            "similar_memories": similar_memories,
            "total_found": result["total_found"]
        }
        
    except Exception as e:
        logger.error(f"Error searching similar memories: {e}")
        return {
            "success": False,
            "message": f"Failed to search similar memories: {str(e)}"
        }

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the FastAPI MCP server."""
    # Configure for Claude Code integration
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    
    logger.info(f"Starting MCP Memory Service FastAPI server on {host}:{port}")
    logger.info(f"Storage backend: {STORAGE_BACKEND}")
    logger.info(f"Data path: {CHROMA_PATH}")
    
    # Run server with streamable HTTP transport
    mcp.run("streamable-http")

if __name__ == "__main__":
    main()