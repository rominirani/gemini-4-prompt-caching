"""Experiment 4: 12-Turn Store Support Agent Cost Comparison (Local Simulator).

Models a realistic 12-turn SunnyMart order-support agent loop:
  - Turn 1: Plan the troubleshooting steps
  - Turns 2-11: 10 worker turns (check SKUs, compare warranties, verify shipping)
  - Turn 12: Final quality review
  - Starting input catalog prefix: 15,000 tokens
  - Context growth per turn: +500 input tokens
  - Thinking + output per turn: 1,200 tokens

Compares four deployment setups across 1,000 agent runs (no live API calls).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import (
    CARBON_MODEL,
    HYDROGEN_MODEL,
    NEON_MODEL,
    calculate_cost,
    save_experiment_result,
)


def simulate_12_turn_cost(
    schedule: list[tuple[str, bool]],
    base_in: int = 15_000,
    turn_growth: int = 500,
    out_per_turn: int = 1_200,
) -> dict:
    """Simulate token counts and total cost per 1,000 12-turn agent runs."""
    seen_models: set[str] = set()
    total_input_per_1k = 0.0
    total_output_per_1k = 0.0
    turns: list[dict] = []

    for idx, (model_id, stable_prefix) in enumerate(schedule):
        in_tok = base_in + idx * turn_growth
        cached_tok = (
            (base_in + max(0, idx - 1) * turn_growth)
            if (stable_prefix and model_id in seen_models)
            else 0
        )
        if stable_prefix:
            seen_models.add(model_id)

        cost = calculate_cost(model_id, in_tok, cached_tok, out_per_turn)
        in_cost_1k = cost["input_cost_per_1k_usd"]
        out_cost_1k = cost["output_cost_usd"] * 1_000

        total_input_per_1k += in_cost_1k
        total_output_per_1k += out_cost_1k

        turns.append(
            {
                "turn": idx + 1,
                "model": model_id,
                "input_tokens": in_tok,
                "cached_tokens": cached_tok,
                "uncached_tokens": in_tok - cached_tok,
                "output_tokens": out_per_turn,
                "input_cost_per_1k_usd": round(in_cost_1k, 4),
                "output_cost_per_1k_usd": round(out_cost_1k, 4),
                "turn_total_per_1k_usd": round(in_cost_1k + out_cost_1k, 4),
            }
        )

    total_per_1k = total_input_per_1k + total_output_per_1k
    return {
        "total_per_1k_runs_usd": round(total_per_1k, 2),
        "single_run_cost_usd": round(total_per_1k / 1_000, 5),
        "input_cost_per_1k_runs_usd": round(total_input_per_1k, 2),
        "output_cost_per_1k_runs_usd": round(total_output_per_1k, 2),
        "turns": turns,
    }


def main() -> None:
    print("=== Experiment 4: 12-Turn Store Support Agent Cost Comparison ===\n")

    schedules = {
        "A. All Carbon (broken prefix, 0% cache)": [(CARBON_MODEL, False)] * 12,
        "B. All Carbon (stable prefix, 95% cache)": [(CARBON_MODEL, True)] * 12,
        "C. All Neon (stable prefix, 95% cache)": [(NEON_MODEL, True)] * 12,
        "D. Neon plan/review + 10 batched Hydrogen": (
            [(NEON_MODEL, True)]
            + [(HYDROGEN_MODEL, True)] * 10
            + [(NEON_MODEL, True)]
        ),
    }

    summary: dict[str, dict] = {}
    baseline_cost = None

    for label, sched in schedules.items():
        sim = simulate_12_turn_cost(sched)
        if baseline_cost is None:
            baseline_cost = sim["total_per_1k_runs_usd"]
        savings_pct = 100.0 * (baseline_cost - sim["total_per_1k_runs_usd"]) / baseline_cost
        sim["savings_vs_baseline_pct"] = round(savings_pct, 1)
        summary[label] = sim

        print(
            f"{label:<43} -> ${sim['total_per_1k_runs_usd']:>7.2f} / 1,000 runs "
            f"(${sim['single_run_cost_usd']:.4f}/run | "
            f"in=${sim['input_cost_per_1k_runs_usd']:>6.2f}, "
            f"out=${sim['output_cost_per_1k_runs_usd']:>6.2f} | "
            f"saves {savings_pct:4.1f}%)"
        )

    print("\n--- Turn-by-Turn Breakdown: Setup D (Neon Plan/Review + 10 Hydrogen) ---")
    print(f"{'Turn':>4} | {'Model':<17} | {'Input':>6} | {'Cached':>6} | {'Uncached':>8} | {'In $/1K':>8} | {'Out $/1K':>8}")
    print("-" * 73)
    for t in summary["D. Neon plan/review + 10 batched Hydrogen"]["turns"]:
        print(
            f"{t['turn']:>4} | {t['model']:<17} | {t['input_tokens']:>6,} | "
            f"{t['cached_tokens']:>6,} | {t['uncached_tokens']:>8,} | "
            f"${t['input_cost_per_1k_usd']:>7.2f} | ${t['output_cost_per_1k_usd']:>7.2f}"
        )

    save_experiment_result("04_12_turn_cost_simulator", summary)


if __name__ == "__main__":
    main()
