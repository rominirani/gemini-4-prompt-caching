# Prompt Caching in Gemini 4: Live Python Experiments & Developer Guide

A beginner-friendly guide and companion Python codebase showing how **Implicit Prompt Caching** works across **Gemini 4 Carbon, Neon, and Hydrogen** — using a simple, original **SunnyMart Online Store Product Catalog** (`SKU-001` through `SKU-190`), real Google Cloud telemetry, exact token-level cost breakdowns, custom concept illustrations, and data charts.

Inspired by Google Cloud's official notebook ([gemini_4_per_model_prompt_caching.ipynb](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/context-caching/gemini_4_per_model_prompt_caching.ipynb)) and rebuilt from scratch as five clean, standalone Python programs with an everyday store-catalog example that any developer can read and run locally.

---

## What You Will Learn

- **What Prompt Caching (KV Caching) is** in plain English, and how Gemini 4 delivers an automatic **95% discount** on cached input tokens once a shared prefix hits **4,096 tokens** ([Context Caching Docs](https://aistudio.google.com/docs/caching)).
- **Why one timestamp at Token 0 kills your cache** — and how reordering your prompt cuts live Hydrogen input costs by **81.6%** (`$22.43` → `$4.13` per 1,000 calls) and drops latency from `3.39s` to `1.72s`.
- **Why KV caches are isolated per model** across Carbon, Neon, and Hydrogen — and how each model's cache stays warm when you switch back.
- **Why Output + Thinking dominates after caching** — dropping a 12-turn store support agent from **`$1.14` down to `$0.23` per run** (**`$1,140.00` → `$231.56`** per 1,000 runs / 12,000 API calls, **-79.7%**) using a *Neon Plan → Batched Hydrogen Workers → Neon Review* pattern.
- **How to use implicit caching with the stateful [Interactions API](https://aistudio.google.com/docs/interactions-overview)** (`previous_interaction_id`).

---

## Project Structure

```text
prompt-caching/
├── blog_post.md                          # Complete Medium-ready plain-English technical blog post
├── social_posts.md                       # SEO title ideas, LinkedIn post, and X/Twitter thread
├── generate_medium_html.py               # Converts blog_post.md -> semantic Medium HTML w/ 1-click copy
├── common.py                             # Shared Enterprise client setup, SunnyMart catalog builder, pricing math
├── requirements.txt                      # Pinned Python dependencies (google-genai 3.6.1, matplotlib)
├── examples/
│   ├── 01_explicit_cache_check.py        # Guardrail: explicit caches.create() returns HTTP 400 on Gemini 4
│   ├── 02_prefix_ordering.py             # Anti-pattern (dynamic-first) vs. best practice (static-first)
│   ├── 03_per_model_isolation.py         # 6-step Carbon -> Neon -> Hydrogen -> Hydrogen -> Neon -> Carbon run
│   ├── 04_12_turn_cost_simulator.py      # Local 12-turn store support agent cost simulator (no API calls)
│   └── 05_interactions_api_handoffs.py   # Stateful Interactions API batched handoffs + cleanup
├── results/
│   └── experiment_results.json           # Verbatim live telemetry captured from Google Cloud
├── scripts/
│   └── generate_charts.py                # Rebuilds Matplotlib PNG charts from experiment_results.json
└── images/
    ├── 01_what_is_prompt_caching.png     # Illustration: Cold Prefill vs. Warm KV Cache
    ├── 02_prefix_matching_rule.png       # Illustration: Token-0 Prefix Matching Rule (Store Catalog)
    ├── 03_per_model_kv_isolation.png     # Illustration: Per-Model KV Cache Vaults
    ├── 04_chart_live_experiments.png     # Live Data Chart: Experiments 2 & 3
    └── 05_chart_12_turn_tco.png          # Cost Chart: 12-Turn Store Support Agent Costs
```

---

## Quickstart

### 1. Prerequisites

- Python 3.10+
- An authenticated Google Cloud project with [Gemini Enterprise Agent Platform](https://docs.cloud.google.com/gemini-enterprise-agent-platform) access:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/rominirani/gemini-4-prompt-caching.git
cd gemini-4-prompt-caching

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Run the Five Python Experiments

```bash
# 1. Confirm Gemini 4 rejects explicit caches.create() with HTTP 400
.venv/bin/python examples/01_explicit_cache_check.py

# 2. Compare Dynamic-First (0% hit) vs. Static-First (85.9% hit) on Hydrogen
.venv/bin/python examples/02_prefix_ordering.py

# 3. Observe per-model KV cache isolation across Carbon, Neon, and Hydrogen
.venv/bin/python examples/03_per_model_isolation.py

# 4. Run the local 12-turn store support agent cost simulator (free — no API calls)
.venv/bin/python examples/04_12_turn_cost_simulator.py

# 5. Chain multi-model turns with the stateful Interactions API (+ automatic cleanup)
.venv/bin/python examples/05_interactions_api_handoffs.py
```

### 4. Regenerate Charts & Medium Export HTML

```bash
# Rebuild high-resolution charts from your live results/experiment_results.json
.venv/bin/python scripts/generate_charts.py

# Generate Medium-ready HTML pointing all 5 images to GitHub raw URLs
.venv/bin/python generate_medium_html.py \
  --github-raw-base https://raw.githubusercontent.com/rominirani/gemini-4-prompt-caching/main
```

> **Publishing Tip:** After pasting `medium_export.html` into Medium, delete the local `medium_export.html` file (already listed in `.gitignore`) before pushing to GitHub so search engines do not index duplicate HTML copies.

---

## Summary of Live Benchmark Results (SunnyMart Catalog)

| Experiment | Key Finding (Live Google Cloud Telemetry) |
| :--- | :--- |
| **1. Explicit Cache Check** | `client.caches.create()` on `gemini-4-neon` returns `HTTP 400` — implicit caching only. |
| **2. Prefix Ordering (`Hydrogen`)** | Dynamic header at Token 0: `0%` cached (`$22.37`–`$22.45/1K`). Static-first Turn 2: **`85.9%` cached (`12,846 / 14,955`)**, input drops to **`$4.13/1K` (-81.6%)**, latency drops `3.39s → 1.72s`. |
| **3. Per-Model Isolation** | Cold starts on Carbon (`$59.58/1K`), Neon (`$44.85/1K`), Hydrogen (`$22.50/1K`). Warm hits: Hydrogen **`52.0%` (`$11.96/1K`)**, Neon **`85.4%` (`$8.56/1K`)**, Carbon **`84.7%` (`$11.85/1K`, latency `7.76s → 4.52s`)**. |
| **4. 12-Turn Agent Costs** | All Carbon broken prefix (`$1.14/run` / `$1,140.00` per 1K runs) → All Carbon cached (`$408.50`, `-64.2%`) → All Neon cached (`$306.38`, `-73.1%`) → Neon Plan/Review + 10 Hydrogen Workers (**`$0.23/run`** / **`$231.56`**, **`-79.7%`**). |
| **5. Interactions API Handoffs** | `Neon → 3× Hydrogen → Neon` via `previous_interaction_id`: Hydrogen workers hit **`85.6%`** & **`85.8%`** (`$4.24`–`$4.21/1K`); Neon verify hit **`83.4%`** (`$9.61/1K`). |

## Official Documentation References

- [Context Caching](https://aistudio.google.com/docs/caching)
- [Understand and Count Tokens](https://aistudio.google.com/docs/tokens)
- [Gemini API Pricing](https://aistudio.google.com/docs/pricing)
- [Google Cloud Model Garden Pricing](https://cloud.google.com/model-garden/pricing)
- [Interactions API Overview](https://aistudio.google.com/docs/interactions-overview)
