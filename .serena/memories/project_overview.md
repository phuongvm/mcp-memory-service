# Project Overview: MCP Memory Service

**MCP Memory Service** is a universal memory service for AI assistants, built on the **Model Context Protocol (MCP)**. It provides persistent, semantic memory storage and retrieval, enabling AI agents to "remember" context across sessions.

## Key Goals
- Provide a standardized memory layer for MCP-compatible AI clients (Claude, Cursor, VS Code, etc.).
- Enable semantic search and intelligent retrieval of past interactions.
- Support multi-client collaboration with team-based memory sharing.
- Offer a robust document ingestion system for building knowledge bases.

## Core Features
- **Universal MCP Support**: Works with any MCP client.
- **Semantic Search**: Uses vector embeddings (SQLite-vec or Cloudflare Vectorize) for meaning-based retrieval.
- **Natural Memory Triggers**: Automatically detects when to store or recall memories with high accuracy.
- **Document Ingestion**: Upload PDF, TXT, MD, JSON files via Web UI or API.
- **OAuth 2.1 & Team Sync**: Secure collaboration features for teams.
- **Flexible Storage**: Local (SQLite-vec), Edge (Cloudflare), or Hybrid modes.

## Use Cases
- **Personal AI Assistant**: Remembers user preferences, project details, and past decisions.
- **Team Knowledge Base**: Shared memory for development teams using Claude Code or Cursor.
- **Documentation Search**: Ingest project docs and allow AI to query them semantically.

## Project Status
- **Production Ready** (v8.9.0).
- Active development with frequent updates.
- widely used by the MCP community.
