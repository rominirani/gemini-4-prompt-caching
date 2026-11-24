"""Shared configuration, client setup, pricing tables, and cost helpers.

Used across all prompt-caching demo scripts in examples/.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

# Gemini 4 model identifiers
CARBON_MODEL = "gemini-4-carbon"
NEON_MODEL = "gemini-4-neon"
HYDROGEN_MODEL = "gemini-4-hydrogen"

# Minimum shared prefix length required to trigger automatic implicit caching on Gemini 4
# Source: https://aistudio.google.com/docs/caching
MIN_CACHE_TOKENS = 4_096

# Standard per-1M input token rates in USD: (uncached_rate, cached_rate)
# Source: https://aistudio.google.com/docs/pricing
# Gemini 4 implicit caching grants a 95% discount on cached input tokens.
# Note: Gemini 4 Carbon has introductory promotional pricing ($2.00 / $0.10) through
# Nov 30, 2026; standard post-Dec 1 rates ($4.00 / $0.20) are used below.
INPUT_RATES_PER_1M: dict[str, tuple[float, float]] = {
    HYDROGEN_MODEL: (1.50, 0.075),
    NEON_MODEL: (3.00, 0.150),
    CARBON_MODEL: (4.00, 0.200),
}

# Standard per-1M output token rates in USD (includes both answer tokens and thinking tokens)
OUTPUT_RATES_PER_1M: dict[str, float] = {
    HYDROGEN_MODEL: 7.50,
    NEON_MODEL: 15.00,
    CARBON_MODEL: 20.00,
}

RESULTS_FILE = Path(__file__).resolve().parent / "results" / "experiment_results.json"

# Everyday sample products used to build a simple, original ~14,500-token store catalog
CATALOG_TEMPLATES: list[tuple[str, str]] = [
    ("Everyday Ceramic Mug", "Kitchen"),
    ("Insulated Travel Tumbler", "Kitchen"),
    ("Organic Cotton Tote Bag", "Accessories"),
    ("Compact Folding Umbrella", "Accessories"),
    ("Bamboo Desk Organizer", "Home Office"),
    ("Clip-On Reading Lamp", "Home Office"),
    ("Stainless Water Bottle", "Outdoors"),
    ("Lightweight Daypack", "Outdoors"),
    ("Soft Fleece Throw Blanket", "Home"),
    ("Scented Soy Desk Candle", "Home"),
]


def resolve_project_id() -> str:
    """Resolve the Google Cloud project ID from environment or active gcloud config."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        return project_id

    try:
        output = subprocess.check_output(
            ["gcloud", "config", "get-value", "project"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if output and output != "(unset)":
            return output
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    raise RuntimeError(
        "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT or run "
        "`gcloud config set project YOUR_PROJECT_ID`."
    )


def create_client() -> genai.Client:
    """Create a Google Gen AI client configured for Gemini Enterprise Agent Platform."""
    project_id = resolve_project_id()
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = location
    os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "True"

    return genai.Client(
        enterprise=True,
        project=project_id,
        location=location,
        http_options=types.HttpOptions(
            timeout=240_000,
            retry_options=types.HttpRetryOptions(attempts=3),
        ),
    )


def build_store_catalog_prefix(
    experiment_label: str,
    sku_prefix: str = "SKU",
) -> str:
    """Generate a simple ~15,000-token SunnyMart Online Store Product Catalog.

    Contains 190 everyday products (e.g., SKU-001 through SKU-190) so the prompt
    comfortably exceeds Gemini 4's 4,096-token implicit caching minimum without
    relying on complex distributed-systems jargon.
    """
    run_salt = os.environ.get("CACHE_RUN_SALT", "").strip()
    salt_note = f" [run={run_salt}]" if run_salt else ""

    header = (
        f"You are a friendly SunnyMart store support assistant ({experiment_label}){salt_note}. "
        "Use the product catalog below and answer concisely in 1 sentence.\n\n"
    )
    entries = []
    for i in range(1, 191):
        item_name, category = CATALOG_TEMPLATES[(i - 1) % len(CATALOG_TEMPLATES)]
        edition = ((i - 1) // len(CATALOG_TEMPLATES)) + 1
        unit_price = 10 + i
        weight_grams = 200 + i
        entries.append(
            f"## Item {sku_prefix}-{i:03d}: {item_name} (Edition {edition})\n"
            f"- Category: {category} | Unit Price: ${unit_price}.00 | Warranty: 12 months\n"
            f"- Return Window: 30 days | Shipping Weight: {weight_grams} grams\n"
            f"- Support Note: Free standard shipping on orders over $50; gift wrapping available."
        )
    return header + "\n".join(entries)


def calculate_cost(
    model: str,
    prompt_tokens: int,
    cached_tokens: int,
    output_tokens: int = 0,
) -> dict[str, float | int]:
    """Calculate exact single-call and per-1,000-call costs in USD."""
    uncached_rate, cached_rate = INPUT_RATES_PER_1M[model]
    output_rate = OUTPUT_RATES_PER_1M[model]

    uncached_tokens = max(0, prompt_tokens - cached_tokens)

    uncached_input_cost = (uncached_tokens * uncached_rate) / 1_000_000
    cached_input_cost = (cached_tokens * cached_rate) / 1_000_000
    total_input_cost = uncached_input_cost + cached_input_cost
    output_cost = (output_tokens * output_rate) / 1_000_000
    total_call_cost = total_input_cost + output_cost

    # What input would have cost with zero cache hits
    baseline_input_cost = (prompt_tokens * uncached_rate) / 1_000_000
    input_savings_pct = (
        100.0 * (baseline_input_cost - total_input_cost) / baseline_input_cost
        if baseline_input_cost > 0
        else 0.0
    )

    return {
        "prompt_tokens": prompt_tokens,
        "uncached_tokens": uncached_tokens,
        "cached_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "hit_pct": (100.0 * cached_tokens / prompt_tokens) if prompt_tokens else 0.0,
        "uncached_input_cost_usd": uncached_input_cost,
        "cached_input_cost_usd": cached_input_cost,
        "input_cost_usd": total_input_cost,
        "output_cost_usd": output_cost,
        "total_cost_usd": total_call_cost,
        "input_cost_per_1k_usd": total_input_cost * 1_000,
        "total_cost_per_1k_usd": total_call_cost * 1_000,
        "baseline_input_cost_per_1k_usd": baseline_input_cost * 1_000,
        "input_savings_pct": input_savings_pct,
    }


def save_experiment_result(experiment_key: str, payload: Any) -> None:
    """Persist live experiment outputs to results/experiment_results.json when enabled."""
    if os.environ.get("SAVE_RESULTS", "1") != "1":
        return

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if RESULTS_FILE.exists():
        existing = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))

    existing[experiment_key] = payload
    RESULTS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
