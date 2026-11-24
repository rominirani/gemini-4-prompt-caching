"""Experiment 1: Explicit Caching Check on Gemini 4.

Gemini 4 models use automatic implicit caching exclusively. Attempting to
manually create an explicit cache resource via `client.caches.create()`
returns HTTP 400. Developers migrating from Gemini 2.5 or 3.x should remove
manual cache creation code and let implicit caching work automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types
from google.genai.errors import APIError

from common import (
    NEON_MODEL,
    build_store_catalog_prefix,
    create_client,
    save_experiment_result,
)


def main() -> None:
    client = create_client()
    catalog = build_store_catalog_prefix("explicit check")

    print("=== Experiment 1: Explicit Context Caching Check (Gemini 4) ===")
    print(f"Attempting client.caches.create() on model: {NEON_MODEL}\n")

    try:
        client.caches.create(
            model=NEON_MODEL,
            config=types.CreateCachedContentConfig(
                contents=[catalog],
                ttl="300s",
            ),
        )
        print("Unexpected: explicit cache creation succeeded.")
        save_experiment_result("01_explicit_cache_check", {"status": "unexpected_success"})
    except APIError as err:
        print(f"Expected guardrail -> HTTP {err.code}: {err.message}")
        save_experiment_result(
            "01_explicit_cache_check",
            {
                "model": NEON_MODEL,
                "http_code": err.code,
                "message": err.message,
            },
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
