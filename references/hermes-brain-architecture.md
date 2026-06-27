# Hermes Brain Architecture

Complete inventory of all Hermes memory/brain systems, HRR details, trust scoring, entity resolution, and retrieval pipeline internals.

## Overview

Hermes has **six layers** of memory/brain, each with different characteristics:

| Layer | Tool | Capacity | Persistence | Search |
|-------|------|----------|-------------|--------|
| Working Memory | `memory` tool (MEMORY.md + USER.md) | ~2,200 + ~1,375 chars | Cross-session | Injected into every system prompt |
| Long-Term Facts | `fact_store` (holographic plugin) | Unlimited (SQLite) | Cross-session | FTS5 + HRR vector algebra |
| Conversation History | `session_search` (FTS5) | Unlimited (SQLite) | Cross-session | FTS5 full-text search |
| Procedural Memory | `skills_list` / `skill_view` | Per-skill files | Cross-session | Skill name / tag lookup |
| Task Context | `todo` | In-session only | Session-only | In-session list |
| Scheduled Work | `cronjob(list)` | Persistent SQLite | Cross-session | Cron job list |

---

## 1. Working Memory (memory tool)

Two files stored at `~/.hermes/memory/` (or `~/.hermes/profiles/<name>/memory/`):

- **MEMORY.md** — Agent's persistent notes about environment, conventions, tool quirks
- **USER.md** — User profile: preferences, personal info, style, corrections

Both are injected into **every system prompt** at session start. Changes via the `memory` tool take effect on the *next* session (they are read once at startup).

**Capacity:** ~2,200 chars (MEMORY.md) + ~1,375 chars (USER.md) combined. When full, use the `operations` batch shape to remove stale entries before adding new ones.

---

## 2. Long-Term Facts (fact_store / Holographic Memory)

The `fact_store` tool is backed by the **holographic memory plugin** (`plugins/memory/holographic/`), which uses Holographic Reduced Representations (HRR) for entity-attribute associative recall.

### Architecture

```
fact_store
  └── holographic.py
       ├── HRRVector        # Holographic Reduced Representation (vector binding/bundling)
       ├── FactStore         # SQLite store + FTS5 index + HRR algebra
       │    ├── facts table  # id, content, category, tags, entities (JSON), trust, created_at, updated_at
       │    ├── ft5 index    # FTS5 virtual table for keyword search
       │    └── fact_embeddings  # HRR entity vectors
       └── EntityResolver    # Automatic entity extraction + alias matching
```

### Fact Store Actions

| Action | Method | Description |
|--------|--------|-------------|
| `search` | FTS5 keyword + trust-weighted ranking | Primary retrieval — use for any query |
| `probe` | HRR entity vector recall | Single-entity deep dive |
| `related` | Graph adjacency traversal | Find entities connected to this one |
| `reason` | HRR compositional JOIN (multi-entity) | Find facts connecting ALL specified entities |
| `contradict` | O(n²) comparison of entities | Find facts with same entities but divergent content |
| `list` | Browse all facts | Organized by category, trust, or age |
| `add` | Store new fact | With category + tags + auto entity extraction |
| `update` | Modify fact | Change content, trust, tags |
| `remove` | Delete fact | Irreversible |

### Trust Scores

- **Range:** 0.0 (untrusted) to 1.0 (fully trusted)
- **Default:** 0.5 (neutral)
- **Adjustment:** `fact_feedback(helpful)` → +0.05; `fact_feedback(unhelpful)` → -0.10
- **Tiers:**
  - ≥0.7: Authoritative — well-confirmed, treat as fact
  - 0.3–0.7: Moderate — may need verification
  - <0.3: Uncertain — flag in gaps, don't assert
- Facts below `min_trust` threshold (default 0.3) are filtered from search results

### Entity Resolution

- **Automatic extraction** on store via regex: capitalized phrases, quoted terms, AKA/hamed-as patterns
- **Case-insensitive alias matching** — "Anggira" matches "anggira", "ANGGIRA"
- Stored as JSON array in the `entities` column
- Used for HRR vector binding (probe/related/reason/contradict)

### HRR Details

Holographic Reduced Representations use:
- **Vector binding** (⊙): Associates entity with attribute — `entity ⊗ attribute`
- **Vector bundling** (+): Combines multiple associations — `(entity₁ ⊗ attr₁) + (entity₂ ⊗ attr₂)`
- **Probe**: `store ⊗ entity†` — unbinds entity from store to find associated attributes
- **Reason**: Finds facts where ALL queried entities play structural roles
- **Contradiction**: Compares entities of all facts for same-entity divergent content

---

## 3. Conversation History (session_search)

Backed by SQLite FTS5 at `~/.hermes/state.db`.

### Calling Shapes

| Shape | Parameters | Returns |
|-------|------------|---------|
| **Discovery** | `query` (FTS5) | Top-N sessions with FTS5-highlighted snippets + bookends + ±5 message window |
| **Scroll** | `session_id` + `around_message_id` + `window` | Window of ±N messages centered on anchor |
| **Read** | `session_id` only | Full session dump (first 20 + last 10) |
| **Browse** | No args | Recent sessions chronologically |

### FTS5 Syntax
- AND is default (multi-word = all terms)
- OR for broader recall: `alpha OR beta`
- Quoted phrases: `"docker networking"`
- Boolean: `python NOT java`
- Prefix wildcards: `deploy*`

### Source-First Limit

session_search searches conversation history only. For current state of external sources (files, URLs, repos), verify the actual source directly.

---

## 4. Brain Query Pipeline (directmind)

The unified retrieval pattern:

```
┌─────────────┐    ┌──────────────┐    ┌────────┐    ┌───────┐    ┌─────────┐
│   Retrieve   │───▶│  Synthesize   │───▶│ Verify │───▶│ Learn │───▶│ Respond │
│ (all layers) │    │ (with cit.)   │    │ (live) │    │ (fb)   │    │         │
└─────────────┘    └──────────────┘    └────────┘    └───────┘    └─────────┘
```

### Retrie Phase (parallel)
1. `fact_store(search)` + `session_search(discovery)` — always
2. `fact_store(probe)` + `fact_store(related)` + `fact_store(reason)` — when entity detected
3. `fact_store(contradict)` — think mode only
4. `fact_store(list)` + `session_search(browse)` — brain dump mode

### Synthesis Phase
- Every claim cited: `[fact:#ID]`, `[session:XXXX]`, `[memory]`
- Group thematically, not by source
- Flag contradictions, mark inferred claims
- Trust-aware presentation

### Verification Phase
Live system checks for every mutable claim (files, crons, processes, configs, Notion pages).

### Learning Phase
`fact_feedback` → `fact_store(update)` → offer `fact_store(add)` for new knowledge.
