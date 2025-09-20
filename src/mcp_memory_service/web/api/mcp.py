"""
MCP (Model Context Protocol) endpoints for Claude Code integration.

This module provides MCP protocol endpoints that allow Claude Code clients
to directly access memory operations using the MCP standard.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..dependencies import get_storage
from ...utils.hashing import generate_content_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPRequest(BaseModel):
    """MCP protocol request structure."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP protocol response structure."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


# Define MCP tools available
MCP_TOOLS = [
    MCPTool(
        name="store_memory",
        description="Store a new memory with optional tags, metadata, and client information",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory content to store"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags for the memory"},
                "memory_type": {"type": "string", "description": "Optional memory type (e.g., 'note', 'reminder', 'fact')"},
                "metadata": {"type": "object", "description": "Additional metadata for the memory"},
                "client_hostname": {"type": "string", "description": "Client machine hostname for source tracking"}
            },
            "required": ["content"]
        }
    ),
    MCPTool(
        name="retrieve_memory", 
        description="Search and retrieve memories using semantic similarity",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for finding relevant memories"},
                "limit": {"type": "integer", "description": "Maximum number of memories to return", "default": 10},
                "similarity_threshold": {"type": "number", "description": "Minimum similarity score threshold (0.0-1.0)", "default": 0.7, "minimum": 0.0, "maximum": 1.0}
            },
            "required": ["query"]
        }
    ),
    MCPTool(
        name="search_by_tag",
        description="Search memories by specific tags",
        inputSchema={
            "type": "object", 
            "properties": {
                "tags": {
                    "oneOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "string"}
                    ],
                    "description": "Tags to search for (array of strings or comma-separated string)"
                },
                "operation": {"type": "string", "enum": ["AND", "OR"], "description": "Tag search operation", "default": "AND"}
            },
            "required": ["tags"]
        }
    ),
    MCPTool(
        name="delete_memory",
        description="Delete a specific memory by content hash",
        inputSchema={
            "type": "object",
            "properties": {
                "content_hash": {"type": "string", "description": "Hash of the memory to delete"}
            },
            "required": ["content_hash"]
        }
    ),
    MCPTool(
        name="check_database_health",
        description="Check the health and status of the memory database",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    MCPTool(
        name="list_memories",
        description="List memories with pagination and optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "page": {"type": "integer", "description": "Page number (1-based)", "default": 1, "minimum": 1},
                "page_size": {"type": "integer", "description": "Number of memories per page", "default": 10, "minimum": 1, "maximum": 100},
                "tag": {"type": "string", "description": "Filter by specific tag"},
                "memory_type": {"type": "string", "description": "Filter by memory type"}
            }
        }
    ),
    MCPTool(
        name="search_by_time",
        description="Search memories by time-based queries using natural language",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language time query (e.g., 'last week', 'yesterday', 'this month')"},
                "n_results": {"type": "integer", "description": "Maximum number of memories to return", "default": 10, "minimum": 1, "maximum": 100}
            },
            "required": ["query"]
        }
    ),
    MCPTool(
        name="search_similar",
        description="Search for memories similar to a given memory by content hash",
        inputSchema={
            "type": "object",
            "properties": {
                "content_hash": {"type": "string", "description": "Content hash of the memory to find similar ones for"},
                "limit": {"type": "integer", "description": "Maximum number of similar memories to return", "default": 5}
            },
            "required": ["content_hash"]
        }
    )
]


@router.post("/")
@router.post("")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP protocol endpoint for processing MCP requests."""
    try:
        storage = get_storage()
        
        if request.method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mcp-memory-service",
                        "version": "4.1.1"
                    }
                }
            )
        
        elif request.method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={
                    "tools": [tool.dict() for tool in MCP_TOOLS]
                }
            )
        
        elif request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            arguments = request.params.get("arguments", {}) if request.params else {}
            
            # Log detailed request information for debugging
            logger.info(f"Tool call: {tool_name} with arguments: {arguments}")
            
            try:
                result = await handle_tool_call(storage, tool_name, arguments)
                logger.debug(f"Tool call {tool_name} completed successfully: {result}")
                
                return MCPResponse(
                    id=request.id,
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                )
            except Exception as tool_error:
                logger.error(f"Tool call {tool_name} failed with arguments {arguments}: {str(tool_error)}")
                logger.error(f"Tool error traceback: {tool_error}", exc_info=True)
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": f"Tool execution failed: {str(tool_error)}"
                    }
                )
        
        else:
            # Handle unknown methods
            if request.id is None:
                # Notification - return HTTP 202 Accepted as per MCP spec
                from fastapi import status
                from fastapi.responses import Response
                return Response(status_code=status.HTTP_202_ACCEPTED)
            else:
                # Request - return error response
                return MCPResponse(
                    id=request.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    }
                )
            
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )


async def handle_tool_call(storage, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tool calls and route to appropriate memory operations."""
    
    if tool_name == "store_memory":
        from ...services.memory_service import MemoryService
        
        content = arguments.get("content")
        tags = arguments.get("tags", [])
        memory_type = arguments.get("memory_type")
        metadata = arguments.get("metadata", {})
        client_hostname = arguments.get("client_hostname")
        
        # Ensure metadata is a dict
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif not isinstance(metadata, dict):
            metadata = {}
        
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
    
    elif tool_name == "retrieve_memory":
        from ...services.memory_service import MemoryService
        
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        similarity_threshold = arguments.get("similarity_threshold", 0.7)
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.retrieve_memory(
            query=query,
            n_results=limit,
            similarity_threshold=similarity_threshold
        )
        
        # Convert service result to MCP API format
        results = []
        for item in result["results"]:
            results.append({
                "content": item["memory"]["content"],
                "content_hash": item["memory"]["content_hash"],
                "tags": item["memory"]["tags"],
                "similarity_score": item["similarity_score"],
                "created_at": item["memory"]["created_at"]
            })
        
        return {
            "results": results,
            "total_found": result["total_found"]
        }
    
    elif tool_name == "search_by_tag":
        tags = arguments.get("tags")
        operation = arguments.get("operation", "AND")
        
        # Use shared service for consistent logic
        from ...services.memory_service import MemoryService
        memory_service = MemoryService(storage)
        
        # Validate and normalize tags parameter
        if not tags:
            logger.error(f"search_by_tag: missing required parameter 'tags'. Arguments: {arguments}")
            raise ValueError("Missing required parameter 'tags'")
        
        # Handle string input - convert to array (preserve existing logic for compatibility)
        if isinstance(tags, str):
            logger.info(f"search_by_tag: converting string tags to array: '{tags}'")
            # Handle different string formats
            if tags.startswith('[') and tags.endswith(']'):
                # Handle "['docker', 'testing']" format
                try:
                    import ast
                    tags = ast.literal_eval(tags)
                    if not isinstance(tags, list):
                        tags = [str(tags)]
                except:
                    # Fallback: treat as comma-separated
                    tags = [tag.strip().strip("'\"") for tag in tags.strip('[]').split(',') if tag.strip()]
            else:
                # Handle comma-separated format
                tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        if not isinstance(tags, list):
            logger.error(f"search_by_tag: 'tags' parameter must be an array or string, got {type(tags).__name__}: {tags}. Arguments: {arguments}")
            raise ValueError(f"Parameter 'tags' must be an array or string, got {type(tags).__name__}")
        
        # Ensure all tags are strings
        tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        
        if not tags:
            logger.error(f"search_by_tag: no valid tags found after processing. Arguments: {arguments}")
            raise ValueError("No valid tags provided")
        
        logger.debug(f"search_by_tag: validated and normalized tags={tags}, operation={operation}")
        
        # Convert operation to match_all boolean (AND=True, OR=False)
        match_all = (operation == "AND")
        
        # Use service method for consistent logic
        result = await memory_service.search_by_tag(
            tags=tags,
            match_all=match_all
        )
        
        # Check for errors from service
        if "error" in result:
            raise ValueError(result["error"])
        
        # Convert service result to MCP API format
        return {
            "results": [
                {
                    "content": item["memory"]["content"],
                    "content_hash": item["memory"]["content_hash"],
                    "tags": item["memory"]["tags"],
                    "created_at": item["memory"]["created_at"]
                }
                for item in result["results"]
            ],
            "total_found": result["total_found"]
        }
    
    elif tool_name == "delete_memory":
        from ...services.memory_service import MemoryService
        
        content_hash = arguments.get("content_hash")
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.delete_memory(content_hash)
        
        return {
            "success": result["success"],
            "message": result["message"]
        }
    
    elif tool_name == "check_database_health":
        from ...services.memory_service import MemoryService
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.check_database_health()
        
        return result
    
    elif tool_name == "list_memories":
        from ...services.memory_service import MemoryService
        
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 10)
        tag = arguments.get("tag")
        memory_type = arguments.get("memory_type")
        
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
    
    elif tool_name == "search_by_time":
        from ...services.memory_service import MemoryService
        
        query = arguments.get("query")
        n_results = arguments.get("n_results", 10)
        
        # Use shared service for consistent logic
        memory_service = MemoryService(storage)
        result = await memory_service.search_by_time(
            query=query,
            n_results=n_results
        )
        
        # Check for errors from service
        if "error" in result:
            return {
                "success": False,
                "message": result["error"]
            }
        
        # Convert service result to MCP API format
        return {
            "results": [
                {
                    "content": item["memory"]["content"],
                    "content_hash": item["memory"]["content_hash"],
                    "tags": item["memory"]["tags"],
                    "memory_type": item["memory"]["memory_type"],
                    "created_at": item["memory"]["created_at_iso"],
                    "updated_at": item["memory"]["updated_at_iso"]
                }
                for item in result["results"]
            ],
            "total_found": result["total_found"]
        }
    
    elif tool_name == "search_similar":
        from ...services.memory_service import MemoryService
        
        content_hash = arguments.get("content_hash")
        limit = arguments.get("limit", 5)
        
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
        
        # Convert service result to MCP API format
        return {
            "success": True,
            "target_memory": result["target_memory"],
            "similar_memories": [
                {
                    "content": item["memory"]["content"],
                    "content_hash": item["memory"]["content_hash"],
                    "tags": item["memory"]["tags"],
                    "similarity_score": item["similarity_score"],
                    "created_at": item["memory"]["created_at_iso"]
                }
                for item in result["results"]
            ],
            "total_found": result["total_found"]
        }
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


@router.get("/tools")
async def list_mcp_tools():
    """List available MCP tools for discovery."""
    return {
        "tools": [tool.dict() for tool in MCP_TOOLS],
        "protocol": "mcp",
        "version": "1.0"
    }


@router.get("/health")
async def mcp_health():
    """MCP-specific health check."""
    storage = get_storage()
    
    # Check if get_stats is async or sync
    import asyncio
    import inspect
    
    if inspect.iscoroutinefunction(storage.get_stats):
        stats = await storage.get_stats()
    else:
        stats = storage.get_stats()
    
    return {
        "status": "healthy",
        "protocol": "mcp",
        "tools_available": len(MCP_TOOLS),
        "storage_backend": "sqlite-vec",
        "statistics": stats
    }
