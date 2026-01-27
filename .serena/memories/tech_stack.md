# Tech Stack

## Core Language
- **Python**: Version 3.10+ required (3.12 recommended).

## Frameworks & Libraries
- **MCP SDK**: `mcp` (Model Context Protocol).
- **API Framework**: `FastAPI`, `Uvicorn` (for HTTP transport).
- **Async I/O**: `aiohttp`, `asyncio`.
- **Vector Database**:
    - `sqlite-vec`: Local, fast, lightweight vector search (default).
    - `Cloudflare D1 + Vectorize`: For edge deployment.
- **Embeddings**:
    - `sentence-transformers`, `torch` (with `--with-ml`).
    - `onnxruntime` (default, lightweight).
- **Document Processing**: `pypdf2`, `chardet`.

## Build & Dependency Management
- **Build Backend**: `hatchling`.
- **Package Manager**: `uv` (recommended), `pip`.
- **Environment**: Virtual environments managed by `uv` or `venv`.

## Testing
- **Runner**: `pytest`.
- **Async Support**: `pytest-asyncio`.
- **Coverage**: `pytest-cov`.

## Deployment
- **Docker**: `docker-compose`.
- **Service**: Systemd / Windows Service support via installation scripts.
