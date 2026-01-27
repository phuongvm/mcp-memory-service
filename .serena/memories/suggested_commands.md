# Suggested Commands

## Installation & Setup
- `python install.py`: Default installation (SQLite-vec + ONNX).
- `python install.py --with-ml`: Install with full ML support (Torch).
- `uv run memory server`: Start the MCP server (stdio mode).
- `uv run memory server --http`: Start server with HTTP API & Dashboard (port 8000/8888).

## Development
- `pytest tests/`: Run all tests.
- `pytest tests/test_sqlite_vec_storage.py`: Test specific storage backend.
- `uv run memory store "content"`: CLI command to store memory.
- `uv run memory recall "query"`: CLI command to search memory.

## Docker
- `docker-compose up -d`: Start standard MCP service.
- `docker-compose -f docker-compose.http.yml up -d`: Start HTTP/OAuth service.

## Maintenance
- `python scripts/maintenance/regenerate_embeddings.py`: Regenerate embeddings.
- `python scripts/maintenance/fast_cleanup_duplicates.sh`: Remove duplicate memories.
