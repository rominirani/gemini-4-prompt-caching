"""Generate publication-grade PNG charts from live experiment results.

Reads `results/experiment_results.json` and writes:
  - images/04_chart_live_experiments.png
  - images/05_chart_12_turn_tco.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "results" / "experiment_results.json"
IMAGES_DIR = ROOT / "images"

# Cohesive palette matching the editorial illustrations
SLATE = "#1E293B"
MUTED = "#64748B"
GRID = "#E2E8F0"
CORAL = "#EF4444"
EMERALD = "#10B981"
BLUE = "#3B82F6"
INDIGO = "#6366F1"
AMBER = "#F59E0B"
BG = "#FFFFFF"

MODEL_COLORS = {
    "gemini-4-carbon": INDIGO,
    "gemini-4-neon": BLUE,
    "gemini-4-hydrogen": EMERALD,
}

MODEL_SHORT = {
    "gemini-4-carbon": "Carbon",
    "gemini-4-neon": "Neon",
    "gemini-4-hydrogen": "Hydrogen",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "axes.edgecolor": GRID,
            "axes.labelcolor": SLATE,
            "text.color": SLATE,
            "xtick.color": SLATE,
            "ytick.color": MUTED,
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def plot_live_experiments(data: dict) -> None:
    """Two-panel chart: Prefix Ordering tokens/cost + Per-Model Isolation cost."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), dpi=240)
    fig.patch.set_facecolor(BG)

    # --- Panel 1: Experiment 2 (Prefix Ordering) ---
    exp2 = data["02_prefix_ordering"]
    dyn = exp2["dynamic_first"]
    sta = exp2["static_first"]

    labels = [f"Dynamic\nTurn {r['turn']}" for r in dyn] + [
        f"Static\nTurn {r['turn']}" for r in sta
    ]
    all_runs = dyn + sta
    uncached = [r["uncached_tokens"] / 1000.0 for r in all_runs]
    cached = [r["cached_tokens"] / 1000.0 for r in all_runs]
    costs_1k = [r["input_cost_per_1k_usd"] for r in all_runs]
    hit_pcts = [r["hit_pct"] for r in all_runs]

    x = np.arange(len(labels))
    bar_w = 0.58

    ax1.bar(x, cached, width=bar_w, color=EMERALD, label="Cached Tokens (95% Off)", zorder=3)
    ax1.bar(
        x,
        uncached,
        width=bar_w,
        bottom=cached,
        color=CORAL,
        alpha=0.88,
        label="Uncached Tokens (Full Price)",
        zorder=3,
    )

    # Visual divider between Dynamic-First and Static-First
    split_x = len(dyn) - 0.5
    ax1.axvline(split_x, color="#CBD5E1", linestyle="--", linewidth=1.3, zorder=2)
    ax1.text((len(dyn) - 1) / 2.0, 17.8, "Anti-Pattern (0% Hit)", ha="center", va="center", fontsize=9.2, fontweight="bold", color=CORAL)
    ax1.text(len(dyn) + (len(sta) - 1) / 2.0, 17.8, "Best Practice (Static First)", ha="center", va="center", fontsize=9.2, fontweight="bold", color="#059669")

    for i, (u_k, c_k, cost_1k, hit) in enumerate(zip(uncached, cached, costs_1k, hit_pcts)):
        total_k = u_k + c_k
        badge = f"${cost_1k:.2f}\n({hit:.1f}%)"
        ax1.text(
            i,
            total_k + 0.35,
            badge,
            ha="center",
            va="bottom",
            fontsize=8.2,
            fontweight="bold",
            color="#059669" if hit > 0 else SLATE,
        )

    ax1.set_title(
        "Experiment 2: Prefix Ordering (Gemini 4 Hydrogen — Input $/1K Calls)",
        fontsize=11.8,
        fontweight="bold",
        pad=16,
        color=SLATE,
    )
    ax1.set_ylabel("Input Prompt Tokens (Thousands)", fontsize=10, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=8.8)
    ax1.set_ylim(0, 19.6)
    ax1.yaxis.grid(True, color=GRID, linestyle="-", linewidth=0.8, zorder=0)
    ax1.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=2,
        frameon=True,
        facecolor=BG,
        edgecolor=GRID,
        fontsize=9,
    )

    # --- Panel 2: Experiment 3 (Per-Model KV Cache Isolation) ---
    exp3 = data["03_per_model_isolation"]
    steps_labels = [f"Step {r['step']}\n{MODEL_SHORT[r['model']]}" for r in exp3]
    step_costs = [r["input_cost_per_1k_usd"] for r in exp3]
    step_hits = [r["hit_pct"] for r in exp3]
    step_colors = [MODEL_COLORS[r["model"]] for r in exp3]
    is_hit = [r["cached_tokens"] > 0 for r in exp3]

    x2 = np.arange(len(steps_labels))
    bars = ax2.bar(x2, step_costs, width=0.58, color=step_colors, zorder=3)

    # Hatch cold misses lightly to distinguish Cold Miss vs Warm Hit
    for bar, hit_flag in zip(bars, is_hit):
        if not hit_flag:
            bar.set_alpha(0.55)
            bar.set_hatch("//")
            bar.set_edgecolor(SLATE)
            bar.set_linewidth(0.8)
        else:
            bar.set_alpha(0.95)
            bar.set_edgecolor(SLATE)
            bar.set_linewidth(0.8)

    max_cost = max(step_costs) if step_costs else 60
    for i, (cost_val, hit_val, hit_flag) in enumerate(zip(step_costs, step_hits, is_hit)):
        status = f"HIT ({hit_val:.1f}%)" if hit_flag else "COLD MISS"
        color_txt = "#059669" if hit_flag else CORAL
        ax2.text(
            i,
            cost_val + max_cost * 0.025,
            f"${cost_val:.2f}\n{status}",
            ha="center",
            va="bottom",
            fontsize=8.3,
            fontweight="bold",
            color=color_txt,
        )

    ax2.set_title(
        "Experiment 3: Per-Model Cache Isolation (Input $/1K Calls)",
        fontsize=12.5,
        fontweight="bold",
        pad=16,
        color=SLATE,
    )
    ax2.set_ylabel("Input Cost per 1,000 Calls (USD)", fontsize=10, fontweight="bold")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(steps_labels, fontsize=9.5)
    ax2.set_ylim(0, max_cost * 1.25)
    ax2.yaxis.grid(True, color=GRID, linestyle="-", linewidth=0.8, zorder=0)

    # Custom legend for Panel 2
    from matplotlib.patches import Patch

    legend_handles = [
        Patch(facecolor=INDIGO, edgecolor=SLATE, label=r"Gemini 4 Carbon (\$4.00 → \$0.20/1M)"),
        Patch(facecolor=BLUE, edgecolor=SLATE, label=r"Gemini 4 Neon (\$3.00 → \$0.15/1M)"),
        Patch(facecolor=EMERALD, edgecolor=SLATE, label=r"Gemini 4 Hydrogen (\$1.50 → \$0.075/1M)"),
        Patch(facecolor="#CBD5E1", edgecolor=SLATE, hatch="//", label="Hatched = Cold Cache Miss"),
    ]
    ax2.legend(handles=legend_handles, loc="upper right", frameon=True, facecolor=BG, edgecolor=GRID, fontsize=8.3)

    fig.suptitle(
        "Live Gemini 4 Prompt Caching Benchmarks (Google Cloud Enterprise Agent Platform)",
        fontsize=14.2,
        fontweight="bold",
        y=0.98,
        color=SLATE,
    )
    plt.tight_layout(rect=[0, 0.04, 1, 0.93])
    out_path = IMAGES_DIR / "04_chart_live_experiments.png"
    fig.savefig(out_path, dpi=240, facecolor=BG)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_12_turn_tco(data: dict) -> None:
    """Horizontal stacked bar chart showing Input vs Output/Thinking TCO per 1,000 agent runs."""
    exp4 = data["04_12_turn_cost_simulator"]
    labels = list(exp4.keys())
    short_labels = [
        "A. All Carbon\n(Broken Prefix, 0% Cache)",
        "B. All Carbon\n(Stable Prefix, 95% Cache)",
        "C. All Neon\n(Stable Prefix, 95% Cache)",
        "D. Neon Plan/Review +\n10 Batched Hydrogen",
    ]
    in_costs = [exp4[k]["input_cost_per_1k_runs_usd"] for k in labels]
    out_costs = [exp4[k]["output_cost_per_1k_runs_usd"] for k in labels]
    totals = [exp4[k]["total_per_1k_runs_usd"] for k in labels]
    savings = [exp4[k]["savings_vs_baseline_pct"] for k in labels]

    fig, ax = plt.subplots(figsize=(12.5, 5.6), dpi=240)
    fig.patch.set_facecolor(BG)

    y = np.arange(len(short_labels))[::-1]
    bar_h = 0.56

    ax.barh(y, in_costs, height=bar_h, color=BLUE, label="Input Token Cost (Uncached + Cached)", zorder=3)
    ax.barh(
        y,
        out_costs,
        left=in_costs,
        height=bar_h,
        color=AMBER,
        label="Output + Thinking Token Cost",
        zorder=3,
    )

    max_total = max(totals)
    for yi, inc, outc, tot, sav in zip(y, in_costs, out_costs, totals, savings):
        # Segment labels
        if inc >= 80:
            in_lbl = f"In: ${inc:.0f}" if inc >= 200 else f"${inc:.1f}"
            ax.text(inc / 2, yi, in_lbl, ha="center", va="center", color="white", fontsize=8.8, fontweight="bold", zorder=4)
        if outc >= 100:
            ax.text(inc + outc / 2, yi, f"Out: ${outc:.0f}", ha="center", va="center", color=SLATE, fontsize=9.0, fontweight="bold", zorder=4)

        sav_tag = "Baseline" if sav == 0 else f"-{sav:.1f}% vs. Baseline"
        tag_color = CORAL if sav == 0 else "#059669"
        ax.text(
            tot + max_total * 0.018,
            yi,
            f"${tot:,.2f}  ({sav_tag})",
            ha="left",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=tag_color,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(short_labels, fontsize=10, fontweight="bold", color=SLATE)
    ax.set_xlabel("Total Cost per 1,000 12-Turn Agent Runs (USD)", fontsize=10.5, fontweight="bold")
    ax.set_xlim(0, max_total * 1.34)
    ax.xaxis.grid(True, color=GRID, linestyle="-", linewidth=0.8, zorder=0)

    ax.set_title(
        "12-Turn Store Support Agent Cost Comparison: Caching + Smart Routing Saves 80.9%",
        fontsize=12.8,
        fontweight="bold",
        pad=26,
        loc="left",
        color=SLATE,
    )
    ax.text(
        0.0,
        1.025,
        "15K starting prefix, +500 input tokens/turn, 1,200 output+thinking tokens/turn — notice how Output dominates once Input is cached",
        transform=ax.transAxes,
        fontsize=9.2,
        color=MUTED,
    )
    ax.legend(loc="lower right", frameon=True, facecolor=BG, edgecolor=GRID, fontsize=9.5)

    plt.tight_layout()
    out_path = IMAGES_DIR / "05_chart_12_turn_tco.png"
    fig.savefig(out_path, dpi=240, facecolor=BG)
    plt.close(fig)
    print(f"Saved {out_path}")


def main() -> None:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(f"Missing {RESULTS_PATH}. Run the live experiments first.")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    plot_live_experiments(data)
    plot_12_turn_tco(data)


if __name__ == "__main__":
    main()
