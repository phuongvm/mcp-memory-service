#!/usr/bin/env python3
"""
Prefetch the `sentence-transformers/all-MiniLM-L6-v2` model into the Hugging Face cache
so the service can run in offline mode.

Respects HF_HOME if set; otherwise uses ~/.cache/huggingface.
"""
import os
import sys
from pathlib import Path

def main() -> int:
    try:
        # Lazily import to ensure a clear error if the package is missing
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as e:
        print("ERROR: sentence-transformers is not installed.\n"
              "Install it with: pip install sentence-transformers", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 1

    repo_id = "sentence-transformers/all-MiniLM-L6-v2"
    print(f"Downloading and caching: {repo_id}")

    try:
        # Trigger model download/cache
        _ = SentenceTransformer(repo_id)
    except Exception as e:
        print("ERROR: Failed to download model from Hugging Face.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 2

    # Determine cache path your service checks
    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    # The service derives the cache folder name as models--sentence-transformers--<model>
    model_dir_name = f"models--sentence-transformers--all-MiniLM-L6-v2"
    expected_cache_path = Path(hf_home) / "hub" / model_dir_name

    print("\nModel cached. You can now enable offline mode in your service.")
    print(f"HF_HOME: {hf_home}")
    print(f"Expected cache folder: {expected_cache_path}")
    if expected_cache_path.exists():
        print("Status: FOUND ✅")
    else:
        print("Status: Not found in expected path — but the model is cached.\n"
              "If your service uses a different HF_HOME, set HF_HOME to the same value when running the service.")

    print("\nTo run offline, set:")
    print("  HF_HUB_OFFLINE=1")
    print("  TRANSFORMERS_OFFLINE=1")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

