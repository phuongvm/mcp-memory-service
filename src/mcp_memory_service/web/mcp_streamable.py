"""
Streamable HTTP MCP endpoint for mcp-memory-service using the MCP Python SDK.

This mounts a Streamable HTTPSessionManager at /mcp so MCP clients can connect
without JSON-RPC glue code. Tool handlers reuse the service's storage logic.
"""

from typing import Any, Dict

from mcp import server as mcp_server, types as mcp_types

from ..storage.sqlite_vec import SqliteVecMemoryStorage


def build_mcp_server(storage: SqliteVecMemoryStorage) -> mcp_server.Server[object]:
    app: mcp_server.Server[object] = mcp_server.Server(name="mcp-memory-service")

    # Tools: list
    async def _list_tools(_: Any) -> mcp_types.ServerResult:
        tools = [
            mcp_types.Tool(
                name="store_memory",
                description="Store a new memory with optional tags and metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "memory_type": {"type": "string"},
                    },
                    "required": ["content"],
                },
            ),
            mcp_types.Tool(
                name="retrieve_memory",
                description="Search and retrieve memories using semantic similarity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            mcp_types.Tool(
                name="search_by_tag",
                description="Search memories by specific tags",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "operation": {"type": "string", "enum": ["AND", "OR"], "default": "AND"},
                    },
                    "required": ["tags"],
                },
            ),
            mcp_types.Tool(
                name="delete_memory",
                description="Delete a specific memory by content hash",
                inputSchema={
                    "type": "object",
                    "properties": {"content_hash": {"type": "string"}},
                    "required": ["content_hash"],
                },
            ),
            mcp_types.Tool(
                name="check_database_health",
                description="Check the health and status of the memory database",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
        return mcp_types.ServerResult(mcp_types.ListToolsResult(tools=tools))

    app.request_handlers[mcp_types.ListToolsRequest] = _list_tools

    # Tools: call
    async def _call_tool(req: mcp_types.CallToolRequest) -> mcp_types.ServerResult:
        name = req.params.name
        args: Dict[str, Any] = req.params.arguments or {}

        if name == "store_memory":
            from ..models.memory import Memory  # type: ignore

            content = args.get("content")
            tags = args.get("tags", [])
            memory_type = args.get("memory_type")
            memory = Memory(content=content, tags=tags, memory_type=memory_type)
            success, message = await storage.store(memory)
            content_text = "stored" if success else "failed"
            return mcp_types.ServerResult(
                mcp_types.CallToolResult(
                    content=[mcp_types.TextContent(type="text", text=f"{content_text}: {message}")],
                )
            )

        if name == "retrieve_memory":
            query = args.get("query")
            limit = args.get("limit", 10)
            results = await storage.retrieve(query=query, n_results=limit)
            text = "\n".join(
                f"{r.relevance_score:.3f} {r.memory.content}" for r in results
            ) or "no results"
            return mcp_types.ServerResult(
                mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text=text)])
            )

        if name == "search_by_tag":
            tags = args.get("tags")
            operation = args.get("operation", "AND")
            results = await storage.search_by_tags(tags=tags, operation=operation)
            text = "\n".join(m.content for m in results) or "no results"
            return mcp_types.ServerResult(
                mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text=text)])
            )

        if name == "delete_memory":
            content_hash = args.get("content_hash")
            success = await storage.delete_memory(content_hash)
            msg = "deleted" if success else "not found"
            return mcp_types.ServerResult(
                mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text=msg)])
            )

        if name == "check_database_health":
            stats = storage.get_stats()
            return mcp_types.ServerResult(
                mcp_types.CallToolResult(content=[mcp_types.TextContent(type="text", text=str(stats))])
            )

        return mcp_types.ServerResult(
            mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")], isError=True
            )
        )

    app.request_handlers[mcp_types.CallToolRequest] = _call_tool

    return app

