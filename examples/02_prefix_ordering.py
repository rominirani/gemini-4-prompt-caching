"""Experiment 2: Prefix Ordering — Dynamic-First vs. Static-First.

Implicit caching matches tokens strictly from Token 0 of the request:
  system_instruction -> tools -> contents

If a changing value (like a timestamp or turn counter) appears at the very
start of `system_instruction`, the prefix never matches and you get 0 cached
tokens every turn. Keeping the SunnyMart product catalog fixed at the start
and placing changing text at the end unlocks automatic cache hits and savings.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types

from common import (
    HYDROGEN_MODEL,
    build_store_catalog_prefix,
    calculate_cost,
    create_client,
    save_experiment_result,
)


def run_dynamic_first() -> list[dict]:
    """Anti-pattern: put changing metadata at index 0 of system_instruction."""
    print("--- Part A: Dynamic Header at the Start (Anti-Pattern) ---")
    catalog_prefix = build_store_catalog_prefix("dynamic-first demo")
    history: list[types.Content] = []
    results = []
    client = create_client()
    try:
        for turn in (1, 2):
            # BAD: changing timestamp/turn at Token 0 breaks prefix matching every turn
            bad_system_instruction = (
                f"[Turn={turn} | RequestTimestamp={int(time.time())}]\n"
                + catalog_prefix
            )
            history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"What is the shipping weight for SKU-0{turn}0?"
                        )
                    ],
                )
            )

            start = time.perf_counter()
            resp = client.models.generate_content(
                model=HYDROGEN_MODEL,
                contents=history,
                config=types.GenerateContentConfig(
                    system_instruction=bad_system_instruction,
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

            cost = calculate_cost(HYDROGEN_MODEL, prompt_tok, cached_tok, out_tok)

            print(
                f"Dynamic-first Turn {turn}: "
                f"prompt={prompt_tok:,}, cached={cached_tok:,} ({cost['hit_pct']:4.1f}%), "
                f"out+think={out_tok}, latency={elapsed_s:.2f}s | "
                f"input=${cost['input_cost_usd']:.5f}/call (${cost['input_cost_per_1k_usd']:.2f}/1K calls)"
            )
            print(f"  Answer: {answer}")

            results.append(
                {
                    "mode": "dynamic_first",
                    "turn": turn,
                    "model": HYDROGEN_MODEL,
                    "latency_s": round(elapsed_s, 3),
                    "candidates_tokens": cand_tok,
                    "thought_tokens": thought_tok,
                    "answer": answer,
                    **cost,
                }
            )
    finally:
        client.close()

    return results


def run_static_first() -> list[dict]:
    """Best practice: keep system_instruction static and put dynamic text at the end."""
    print("\n--- Part B: Static Catalog First, Dynamic Text at End (Best Practice) ---")
    catalog_prefix = build_store_catalog_prefix("static-first demo")
    history: list[types.Content] = []
    results = []
    client = create_client()
    try:
        for turn in (1, 2, 3):
            # GOOD: put changing metadata (turn number) at the END in the user turn
            history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"[Turn={turn}] What is the shipping weight for SKU-0{turn}0?"
                        )
                    ],
                )
            )

            start = time.perf_counter()
            resp = client.models.generate_content(
                model=HYDROGEN_MODEL,
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

            cost = calculate_cost(HYDROGEN_MODEL, prompt_tok, cached_tok, out_tok)

            print(
                f"Static-first  Turn {turn}: "
                f"prompt={prompt_tok:,}, cached={cached_tok:,} ({cost['hit_pct']:4.1f}%), "
                f"out+think={out_tok}, latency={elapsed_s:.2f}s | "
                f"input=${cost['input_cost_usd']:.5f}/call (${cost['input_cost_per_1k_usd']:.2f}/1K calls, "
                f"saves {cost['input_savings_pct']:.1f}%)"
            )
            print(f"  Answer: {answer}")

            results.append(
                {
                    "mode": "static_first",
                    "turn": turn,
                    "model": HYDROGEN_MODEL,
                    "latency_s": round(elapsed_s, 3),
                    "candidates_tokens": cand_tok,
                    "thought_tokens": thought_tok,
                    "answer": answer,
                    **cost,
                }
            )
    finally:
        client.close()

    return results


def main() -> None:
    print("=== Experiment 2: Prefix Ordering (Dynamic-First vs. Static-First) ===\n")
    dynamic_results = run_dynamic_first()
    static_results = run_static_first()
    save_experiment_result(
        "02_prefix_ordering",
        {
            "dynamic_first": dynamic_results,
            "static_first": static_results,
        },
    )


if __name__ == "__main__":
    main()
