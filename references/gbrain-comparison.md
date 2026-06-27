# GBrain Comparison

Feature comparison between Hermes directmind and GBrain (garrytan/gbrain).

## What is GBrain?

GBrain is a personal/company "brain" layer for AI agents — a knowledge graph + synthesis + retrieval tool built by Garry Tan (YC CEO). It ingests notes, meetings, emails, etc. into a searchable knowledge base with entity graphs and citation-backed synthesis.

**Stack:** Bun + TypeScript, PGLite (in-browser Postgres), MCP server.

## Feature Comparison

| Feature | GBrain | directmind (Hermes) |
|---------|--------|---------------------|
| Knowledge Graph | ✅ Typed edges (works_at, invested_in, etc.) — no LLM calls for wiring | ✅ HRR vector algebra (probe, related, reason) — no LLM calls |
| Raw Retrieval | `gbrain search` | `search` mode (zero LLM cost) |
| Synthesis | `gbrain think` — synthesized answer + gap analysis | `think` mode — full pipeline with citations |
| Gap Analysis | ✅ Explicit: "what the brain doesn't know" | ✅ Gaps table: staleness, missing sources, contradictions, unknowns |
| Entity Deep Dive | Via graph queries | `probe` mode — entity-centered recall |
| Multi-Entity Reasoning | Graph traversal | `reason` mode — compositional JOIN (HRR algebra) |
| Verification | ❌ No live verification | ✅ Verify phase — checks files, crons, configs, processes |
| Learning Loop | ❌ No built-in feedback | ✅ `fact_feedback` + `fact_store(update)` + auto-store |
| MCP Server | ✅ stdio + HTTP | Via Hermes' MCP server |
| "Dream Cycle" | ✅ Overnight enrichment cron | ⏳ Can be replicated via cronjob |
| Pre-built Skills | 43 skills | Skill system (directmind + others) |
| Install Complexity | Bun + API keys, ~30 min | Already part of Hermes |
| Data Ingestion | Notes, meetings, emails, tweets | Memory + fact_store + session_search |
| Cross-Platform | MCP client needed | Native Hermes gateway (Telegram, Discord, etc.) |
| Trust Scoring | ❌ None | ✅ 0.0–1.0 trust scores + `fact_feedback` training |

## What directmind Does Better

1. **Live verification** — GBrain trusts what you put in; directmind checks the real system state
2. **Learning loop** — `fact_feedback` trains trust scores over time
3. **Lower overhead** — no extra daemon or database to run
4. **Trust scoring** — not all facts are equal; directmind surfaces uncertainty
5. **Multi-entity JOIN** — HRR `reason` action finds compositional relationships without graph traversal

## What GBrain Does Better

1. **Knowledge graph schema** — typed edges provide clearer semantics for structured relationships
2. **Batch ingestion** — designed for 100K+ pages from meetings, emails, tweets
3. **Dream cycle** — autonomous overnight enrichment
4. **43 pre-built skills** — ready-to-use templates
5. **Independent** — works with any MCP client, not tied to Hermes

## Verdict

Directmind is **better for Hermes users** — it leverages existing Hermes infrastructure (memory, fact_store, session_search, cron) without adding a new daemon, database, or runtime. The live verification and learning loop are unique advantages.

GBrain makes sense if you need:
- A standalone brain not tied to an agent framework
- Large-scale batch ingestion (100K+ docs)
- Typed, schema-driven knowledge graphs with explicit relationship types

For Patrick's workflow (Hermes + Notion + fact_store), directmind is the right choice.
