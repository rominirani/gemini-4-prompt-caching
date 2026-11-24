# Publishing & Social Amplification Kit

## 5 High-Intent SEO Title Ideas (Medium / Dev.to)

1. **Prompt Caching Explained Simply: Cut Your Gemini 4 Bills by Up to 80% (With Real Python Examples)** *(Used in `blog_post.md` — beginner-friendly + concrete value)*
2. **One Timestamp Just Cost You 81% of Your LLM Bill: A Plain-English Guide to Gemini 4 Prompt Caching** *(High CTR curiosity hook)*
3. **How Prompt Caching Actually Works (Step-by-Step Store Catalog Example, Illustrations & Exact Token Math)** *(Strong beginner search intent)*
4. **Stop Re-Reading Your System Prompt: Per-Model Prompt Caching Across Gemini 4 Carbon, Neon, and Hydrogen** *(Architecture & agent builders)*
5. **From $1,140 to $231.56 per 1,000 Agent Runs: Prompt Caching + Multi-Model Batching in Gemini 4** *(Data-driven FinOps / engineering hook)*

---

## LinkedIn Post

Most developers building LLM apps are accidentally paying full price to have the model re-read the exact same 15,000-token system prompt and catalog on every single turn.

Even worse? A single `[Turn=1 | RequestTimestamp=...]` line at the top of your `system_instruction` silently breaks automatic prompt caching — dropping your cache hit rate straight to 0%.

I just published a plain-English, step-by-step guide to **Prompt Caching in Gemini 4** (Carbon, Neon, and Hydrogen) using an everyday **online store product catalog** — complete with 5 clean standalone Python scripts, custom illustrations, official doc citations, and real token + dollar numbers captured live on Google Cloud.

Here are 4 eye-opening findings from running the experiments live:

1. **No boilerplate required:** Gemini 4 uses automatic *Implicit Context Caching* exclusively (95% discount on cached input tokens once a shared prefix reaches 4,096 tokens). Old explicit `caches.create()` calls now return `HTTP 400`.
2. **Prefixes match strictly from Token 0:** Moving a changing turn timestamp from the start of `system_instruction` to the end of the user prompt took Gemini 4 Hydrogen from **0% cached ($22.43 / 1K calls)** to **85.9% cached ($4.13 / 1K calls)** — an **81.6% input cost drop** and **nearly 2× faster response** (`3.39s → 1.72s`).
3. **Caches are NOT shared across models:** Carbon, Neon, and Hydrogen each keep their own private memory. Switching models pays a one-time cold start, while the original model's cache stays warm when you switch back (Neon hit **85.4% cached**, and Carbon hit **84.7% cached**, cutting Carbon's latency from `7.76s` down to `4.52s`!).
4. **Once input is cached, Output + Thinking dominates your bill:** In a 12-turn store support agent loop (1,000 runs = 12,000 API calls), fixing prefix caching alone cut total cost from **$1,140.00 to $408.50 (-64.2%)**. Batching the 10 worker turns on Hydrogen while planning/reviewing on Neon cut it further to **$231.56 (-79.7%, or $0.23 per 12-turn run)**!

Bonus detail explained simply in the post: why your live cache hit sits at ~85% instead of 99.9% on short chats (Gemini 4's documented 2,050-token trailing window!).

Read the full illustrated walkthrough + grab the runnable Python code here: [LINK_TO_MEDIUM_ARTICLE]
Companion GitHub repo: https://github.com/rominirani/gemini-4-prompt-caching

#GoogleCloud #Gemini #LLM #PromptCaching #AIAgents #Python #DeveloperExperience

---

## X / Twitter Thread (6 Tweets)

**1/6**
Every time your AI support bot answers a 1-line shopper question, it quietly re-sends your entire 15,000-token store catalog.

Without prompt caching, you pay the model to re-read the whole catalog from Page 1 on every single turn.

Here's how Gemini 4 Prompt Caching works — in plain English, with 5 live Python scripts & exact dollar math 🧵👇

**2/6**
On Gemini 4 (Carbon, Neon, Hydrogen), manual `caches.create()` is gone (returns HTTP 400).

Instead, **Implicit Prompt Caching** runs automatically once your shared prefix hits **4,096 tokens** (~2,450–3,275 English words) — giving you **95% off** cached input tokens with zero storage fees:
- Hydrogen: $1.50 → $0.075 / 1M
- Neon: $3.00 → $0.150 / 1M
- Carbon: $4.00 → $0.200 / 1M (standard)

**3/6**
The #1 trap that silently destroys your cache: putting a timestamp or turn counter at Token 0 of `system_instruction`.

Implicit caching matches strictly left-to-right from Token 0.

Live run on `gemini-4-hydrogen` with a 190-item store catalog:
❌ Dynamic-first: 0% cached → $22.45 / 1K calls
✅ Static-first Turn 2: 85.9% cached (12,846 / 14,955 tokens) → **$4.13 / 1K calls** (-81.6% cost & 3.39s → 1.72s latency!)

*(Attach: `images/02_prefix_matching_rule.png`)*

**4/6**
Trap #2: Assuming multi-model agents share a cache.

They don't! Carbon, Neon, and Hydrogen each keep their own private notebook.

Live 6-step run (`Carbon → Neon → Hydrogen → Hydrogen → Neon → Carbon`):
- Steps 1–3: 0% cached (3 cold starts)
- Step 4 (Hydrogen): 52.0% hit ($22.50 → $11.96/1K)
- Step 5 (Neon): 85.4% hit ($44.85 → $8.56/1K)
- Step 6 (Carbon): 84.7% hit ($59.58 → $11.85/1K, 7.76s → 4.52s!)

*(Attach: `images/03_per_model_kv_isolation.png`)*

**5/6**
The biggest surprise on a 12-turn store support agent (per 1,000 runs = 12,000 calls):

- All Carbon (broken prefix): **$1,140.00** ($1.14/run)
- All Carbon (cached): **$408.50** (-64.2%)
- All Neon (cached): **$306.38** (-73.1%)
- Neon Plan/Review + 10 batched Hydrogen workers: **$231.56** (**-79.7% — $0.23/run!**)

Once input is cached, Output + Thinking becomes 70% of your bill — so batching worker turns on Hydrogen is huge.

*(Attach: `images/05_chart_12_turn_tco.png`)*

**6/6**
Also covered in the full plain-English guide:
- Why live hits sit around ~85% on tiny chats (Gemini 4's documented 2,050-token trailing window)
- Stateful batched handoffs on the Interactions API (`previous_interaction_id`: 85.6%, 85.8%, 83.4% hits!)
- All 5 simple, runnable Python scripts + official doc links

Full illustrated blog post: [LINK_TO_MEDIUM_ARTICLE]
Runnable Python repo: https://github.com/rominirani/gemini-4-prompt-caching
