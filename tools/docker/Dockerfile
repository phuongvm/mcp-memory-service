## Slim (CPU-only) Docker image optimized for sqlite-vec + ONNX
## Consolidated as the primary Dockerfile to avoid confusion.
FROM python:3.10-slim

# Build arguments for conditional features
ARG SKIP_MODEL_DOWNLOAD=false
ARG PLATFORM=linux/amd64

# Optimized runtime environment
ENV PYTHONUNBUFFERED=1 \
    MCP_MEMORY_STORAGE_BACKEND=sqlite_vec \
    MCP_MEMORY_USE_ONNX=1 \
    MCP_MEMORY_SQLITE_PATH=/app/sqlite_db \
    MCP_MEMORY_BACKUPS_PATH=/app/backups \
    PYTHONPATH=/app/src \
    DOCKER_CONTAINER=1 \
    CHROMA_TELEMETRY_IMPL=none \
    ANONYMIZED_TELEMETRY=false \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app

# Minimal system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy essentials
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY scripts/install_uv.py .

# Install UV
RUN python install_uv.py

# Data dirs
RUN mkdir -p /app/sqlite_db /app/backups

# Copy source
COPY src/ /app/src/
COPY run_server.py ./

# Optional utils
COPY scripts/utils/uv_wrapper.py ./uv_wrapper.py
COPY scripts/utils/memory_wrapper_uv.py ./memory_wrapper_uv.py

# Entrypoints
COPY tools/docker/docker-entrypoint.sh /usr/local/bin/
COPY tools/docker/docker-entrypoint-persistent.sh /usr/local/bin/
COPY tools/docker/docker-entrypoint-unified.sh /usr/local/bin/

# Normalize line endings
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    sed -i 's/\r$//' /usr/local/bin/docker-entrypoint-persistent.sh && \
    sed -i 's/\r$//' /usr/local/bin/docker-entrypoint-unified.sh

# Install minimal deps (no torch/CUDA); then install package in editable mode without deps
RUN python -m uv pip install \
    "mcp>=1.0.0,<2.0.0" \
    "sqlite-vec>=0.1.0" \
    "onnxruntime>=1.15.0" \
    "tokenizers==0.20.3" \
    "build>=0.10.0" \
    "aiohttp>=3.8.0" \
    "fastapi>=0.115.0" \
    "uvicorn>=0.30.0" \
    "python-multipart>=0.0.9" \
    "sse-starlette>=2.1.0" \
    "aiofiles>=23.2.1" \
    "psutil>=5.9.0" \
    "zeroconf>=0.130.0" \
    "PyPDF2>=3.0.0" \
    "chardet>=5.0.0" \
    "click>=8.0.0" \
    && python -m uv pip install -e . --no-deps

# Prefetch ONNX model optionally
RUN if [ "$SKIP_MODEL_DOWNLOAD" != "true" ]; then \
        echo "Pre-downloading ONNX embedding models..." && \
        python -c "try:\
            from mcp_memory_service.embeddings.onnx_embeddings import ONNXEmbeddingModel; \
            print('Initializing ONNX embedding model...'); \
            model = ONNXEmbeddingModel(); \
            print('ONNX models cached successfully')\
        except Exception as e:\
            print(f'Warning: Could not pre-download ONNX models: {e}'); \
            print('Models will be downloaded at runtime')" || echo "ONNX model download failed, continuing..."; \
    else \
        echo "Skipping ONNX model download (SKIP_MODEL_DOWNLOAD=true)"; \
    fi

# Entrypoint perms
RUN chmod a+rw /dev/stdin /dev/stdout /dev/stderr && \
    chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint-persistent.sh && \
    chmod +x /usr/local/bin/docker-entrypoint-unified.sh

VOLUME ["/app/sqlite_db", "/app/backups"]
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint-unified.sh"]
