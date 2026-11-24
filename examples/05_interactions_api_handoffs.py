"""Experiment 5: Batched Handoffs on the Stateful Interactions API.

Demonstrates implicit prompt caching when chaining turns server-side using
`previous_interaction_id` (`store=True`) on the modern Interactions API with
our SunnyMart Online Store Product Catalog:
  - Turn 1: gemini-4-neon     (Plan: look up SKU-001 and SKU-002 prices)
  - Turn 2: gemini-4-hydrogen (Worker 1: calculate subtotal — warms Hydrogen cache)
  - Turn 3: gemini-4-hydrogen (Worker 2: calculate price difference — hits cache!)
  - Turn 4: gemini-4-hydrogen (Worker 3: format both as JSON — hits cache!)
  - Turn 5: gemini-4-neon     (Verify: confirm JSON matches catalog — back to Neon)

Always deletes stored interactions at the end to keep the project clean.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (
    HYDROGEN_MODEL,
    NEON_MODEL,
    build_store_catalog_prefix,
    calculate_cost,
    create_client,
    save_experiment_result,
)


def main() -> None:
    print("=== Experiment 5: Batched Handoffs on the Interactions API ===\n")
    client = create_client()
    catalog_prefix = build_store_catalog_prefix("interactions-api demo")
    stored_ids: list[str] = []

    turns_spec = [
        (NEON_MODEL, "low", "Plan: list the unit prices for SKU-001 and SKU-002."),
        (HYDROGEN_MODEL, "low", "Worker 1: calculate the subtotal if a customer buys both items."),
        (HYDROGEN_MODEL, "low", "Worker 2: calculate the price difference between the two items."),
        (HYDROGEN_MODEL, "low", "Worker 3: format the subtotal and price difference as JSON."),
        (NEON_MODEL, "low", "Verify: confirm the JSON matches the catalog prices for SKU-001 and SKU-002."),
    ]

    prev_id: str | None = None
    rows: list[dict] = []

    header = (
        f"{'Turn & Model':<22} | {'Input':>7} | {'Cached':>7} | {'Uncached':>8} | "
        f"{'Out+Thk':>7} | {'Hit %':>6} | {'Time':>6} | {'In $/1K':>9}"
    )
    print(header)
    print("-" * len(header))

    try:
        for idx, (model_id, level, prompt) in enumerate(turns_spec, start=1):
            kwargs: dict[str, Any] = {
                "model": model_id,
                "system_instruction": catalog_prefix,
                "input": prompt,
                "generation_config": {"thinking_level": level},
                "store": True,
                "timeout": 180,
            }
            if prev_id is not None:
                kwargs["previous_interaction_id"] = prev_id

            start = time.perf_counter()
            inter = client.interactions.create(**kwargs)
            elapsed_s = time.perf_counter() - start

            stored_ids.append(inter.id)
            prev_id = inter.id

            in_tok = inter.usage.total_input_tokens or 0
            cached_tok = inter.usage.total_cached_tokens or 0
            out_only = inter.usage.total_output_tokens or 0
            thought_tok = getattr(inter.usage, "total_thought_tokens", None) or 0
            out_tok = out_only + thought_tok

            cost = calculate_cost(model_id, in_tok, cached_tok, out_tok)
            label = f"{idx}. {model_id}"
            print(
                f"{label:<22} | {in_tok:>7,} | {cached_tok:>7,} | "
                f"{cost['uncached_tokens']:>8,} | {out_tok:>7,} | "
                f"{cost['hit_pct']:>5.1f}% | {elapsed_s:>5.2f}s | "
                f"${cost['input_cost_per_1k_usd']:>8.3f}"
            )

            rows.append(
                {
                    "turn": idx,
                    "model": model_id,
                    "prompt": prompt,
                    "answer": (inter.output_text or "").strip(),
                    "latency_s": round(elapsed_s, 3),
                    "output_only_tokens": out_only,
                    "thought_tokens": thought_tok,
                    **cost,
                }
            )

        save_experiment_result(
            "05_interactions_api_handoffs",
            {"turns": rows, "deleted_count": len(stored_ids)},
        )
    finally:
        for interaction_id in stored_ids:
            try:
                client.interactions.delete(interaction_id)
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: could not delete {interaction_id}: {exc}")
        print(f"\nCleaned up {len(stored_ids)} stored interactions.")
        client.close()


if __name__ == "__main__":
    main()
