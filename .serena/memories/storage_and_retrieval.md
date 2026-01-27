# Storage & Retrieval Strategy

The service prioritizes speed and local privacy while offering cloud-based synchronization for teams.

## 1. Storage Backends
*   **Primary (Local)**: **SQLite-vec**. Fast, local-first vector search with 5ms read times. No external database server required.
*   **Edge/Cloud**: **Cloudflare D1 + Vectorize**. Enables global distribution and edge retrieval.
*   **Hybrid Mode**: Synchronizes local SQLite-vec with Cloudflare. *Note: "Hybrid" here refers to storage synchronization, not a keyword+vector search mix.*

## 2. Retrieval Mechanism
*   **Semantic Search**: Uses vector embeddings to find relevant memories.
*   **Recency Optimization**: Automatically prioritizes memories created within the last 7 days.
*   **Document Chunking**: Large files (PDFs, etc.) are automatically split into searchable chunks with metadata during ingestion.
*   **Advanced Search (Planned/Optional)**: Mentions of `sqlite-fts5` for full-text search integration are present in documentation for future enhancements.

## 3. Embedding Implementation
*   **Approach**: **Local-first Inference**.
*   **Default**: Uses `onnxruntime` for extremely fast, CPU-bound embedding generation without calling external APIs (like OpenAI).
*   **Advanced**: Supports `sentence-transformers` and `torch` (via `--with-ml` install flag) for more capable local models.
*   **GPUStack/API**: Not natively designed for API-based embedding providers; it is optimized for in-process execution to minimize latency.
