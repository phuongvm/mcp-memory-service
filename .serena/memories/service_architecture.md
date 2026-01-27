# Service Architecture (MCP & UI)

The **MCP Memory Service** is designed as a standalone, multi-transport service providing memory capabilities to AI clients.

## Components
1.  **Core MCP Server** (`src/mcp_memory_service/server.py`)
    *   Built using the official Python `mcp` SDK.
    *   **Transports**: 
        *   **Stdio**: Default for local IDE integration (Claude Desktop).
        *   **SSE (Server-Sent Events)**: For HTTP-based remote access.
    *   **Core Tools**: `store_memory`, `recall_memory`, `search_by_tags`, `get_health`.
    *   **Natural Memory Triggers**: v7.1.0+ feature that intelligently detects when to surface memories based on conversation context.

2.  **Dashboard & Web API** (`src/mcp_memory_service/web/`)
    *   **Framework**: FastAPI & Uvicorn.
    *   **Dashboard**: A web interface (default port 8888) primarily for **Document Ingestion** (PDF, TXT, MD, JSON) and monitoring sync status.
    *   **Authentication**: Supports **OAuth 2.1** for team collaboration and API Keys for security.

3.  **Synchronization Layer**
    *   Handles data consistency between local SQLite and remote Cloudflare backends.
    *   Includes background sync services and maintenance scripts for database health.
