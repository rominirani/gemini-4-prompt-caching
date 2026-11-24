"""Experiment 3: Per-Model KV Cache Isolation Across Carbon, Neon, and Hydrogen.

KV caches belong to each individual model — they are NOT shared across models.
This script runs a 6-step SunnyMart store support conversation across three
Gemini 4 models:
  1. Carbon   (cold miss -> warms Carbon cache)
  2. Neon     (cold miss -> warms Neon cache)
  3. Hydrogen (cold miss -> warms Hydrogen cache)
  4. Hydrogen (consecutive -> hits warm Hydrogen cache)
  5. Neon     (hand back   -> hits still-warm Neon cache)
  6. Carbon   (hand back   -> hits still-warm Carbon cache)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types

from common import (
    CARBON_MODEL,
    HYDROGEN_MODEL,
    NEON_MODEL,
    build_store_catalog_prefix,
    calculate_cost,
    create_client,
    save_experiment_result,
)


def main() -> None:
    print("=== Experiment 3: Per-Model KV Cache Isolation ===\n")
    client = create_client()
    catalog_prefix = build_store_catalog_prefix(
        "per-model isolation demo", sku_prefix="ITEM"
    )

    handoff_schedule = [
        (CARBON_MODEL, "Step 1 (Carbon cold start): check shipping weight for ITEM-005."),
        (NEON_MODEL, "Step 2 (Neon cold start): check shipping weight for ITEM-015."),
        (HYDROGEN_MODEL, "Step 3 (Hydrogen cold start): check shipping weight for ITEM-025."),
        (HYDROGEN_MODEL, "Step 4 (Hydrogen consecutive): check shipping weight for ITEM-035."),
        (NEON_MODEL, "Step 5 (Back to warm Neon): check shipping weight for ITEM-045."),
        (CARBON_MODEL, "Step 6 (Back to warm Carbon): check shipping weight for ITEM-055."),
    ]

    history: list[types.Content] = []
    rows: list[dict] = []

    header = (
        f"{'Step & Model':<22} | {'Prompt':>7} | {'Cached':>7} | {'Uncached':>8} | "
        f"{'Out+Thk':>7} | {'Hit %':>6} | {'Time':>6} | {'In $/1K':>9}"
    )
    print(header)
    print("-" * len(header))

    try:
        for idx, (model_id, user_msg) in enumerate(handoff_schedule, start=1):
            history.append(
                types.Content(role="user", parts=[types.Part.from_text(text=user_msg)])
            )

            start = time.perf_counter()
            resp = client.models.generate_content(
                model=model_id,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=catalog_prefix,
                    thinking_config=types.ThinkingConfig(thinking_level="LOW"),
                ),
            )
            elapsed_s = time.perf_counter() - start

            answer = (resp.text or "").strip()
            history.append(
                types.Content(role="model", parts=[types.Part.from_text(text=answer)])
            )

            u = resp.usage_metadata
            prompt_tok = u.prompt_token_count or 0
            cached_tok = u.cached_content_token_count or 0
            cand_tok = u.candidates_token_count or 0
            thought_tok = u.thoughts_token_count or 0
            out_tok = cand_tok + thought_tok

            cost = calculate_cost(model_id, prompt_tok, cached_tok, out_tok)
            label = f"{idx}. {model_id}"
            print(
                f"{label:<22} | {prompt_tok:>7,} | {cached_tok:>7,} | "
                f"{cost['uncached_tokens']:>8,} | {out_tok:>7,} | "
                f"{cost['hit_pct']:>5.1f}% | {elapsed_s:>5.2f}s | "
                f"${cost['input_cost_per_1k_usd']:>8.3f}"
            )

            rows.append(
                {
                    "step": idx,
                    "model": model_id,
                    "user_msg": user_msg,
                    "answer": answer,
                    "latency_s": round(elapsed_s, 3),
                    "candidates_tokens": cand_tok,
                    "thought_tokens": thought_tok,
                    **cost,
                }
            )

        save_experiment_result("03_per_model_isolation", rows)
    finally:
        client.close()


if __name__ == "__main__":
    main()
