# Memory Hygiene & Deduplication

**Principle:** every durable fact lives in EXACTLY 1 system. No fact appears in both MEMORY.md (or USER.md) AND fact_store.

## Why

| Reason | Impact |
|--------|--------|
| **Limited WM capacity** | MEMORY.md has 2,200 chars, USER.md has 1,375 chars. Duplicates waste precious space |
| **Stale divergence** | Same fact in two places drifts apart — one gets updated, the other doesn't |
| **Trust score bypass** | MEMORY.md facts have no trust score — they're injected frozen. fact_store facts have dynamic trust via fact_feedback |
| **Verification blindspot** | Agent checks fact_store during retrieval but may miss that MEMORY.md has stale copy of same fact |

## Detection Scan

Run this periodically (e.g., once per session) or when MEMORY.md/USER.md is near capacity:

```
1. fact_store(list, limit=50)   → cache all fact_store entries
2. Read system prompt memory     → MEMORY.md + USER.md injected at session start
3. Cross-reference each MEMORY/USER entry against fact_store
4. Flag any topic that appears in BOTH
```

### What's Overlap?

A MEMORY.md entry overlaps with fact_store if it describes the **same fact** about the **same entity or topic**. Examples:

| MEMORY.md entry | fact_store entry | Overlap? |
|-----------------|-------------------|----------|
| "Anggira 125M GGUF works via hybrid approach" | "Anggira 125M GGUF inference: hybrid approach works" | ✅ DUPLICATE |
| "Exynos 1280 cores: A55=0-5, A78=6-7" | "Exynos 1280 core mapping: Cores 0-5 A55, Cores 6-7 A78" | ✅ DUPLICATE |
| "Notion Vault=3707b66e" | "Notion Hermes Vault page ID: 3707b66e..." | ✅ DUPLICATE |
| "Hermes binary at /usr/local/lib/..." | (none) | OK — unique |
| "Terminal truncates long strings..." | (none) | OK — unique |

### Resolution per Data Type

| If both have... | Canonical source | Action |
|-----------------|------------------|--------|
| Environment fact (Exynos, Anggira, Scraping APIs, Notion IDs) | **fact_store** | Remove from MEMORY.md |
| User preference (Vikey AI, language, style) | **USER.md** (personality) or **fact_store** (system config) | Vikey config → fact_store (durable); remove from USER.md |
| Tool/command quirk (RTK path, terminal truncation) | **MEMORY.md** | Keep in MEMORY.md; do NOT add to fact_store |
| Access credential (git PAT location, API key location) | **MEMORY.md** or **USER.md** | Keep where it is; do NOT add to fact_store |

### Priority Canonical Map

| Data category | Canonical home | Why |
|---------------|----------------|-----|
| ML model config, training params, architecture | fact_store | Durable, trust-tagged, searchable |
| Hardware/environment specs (cores, GPU, OS) | fact_store | Durable, referenced across sessions |
| Tool paths, binary locations, config file paths | MEMORY.md | Session-execution context, not retro fact |
| Shell quirks, terminal behavior, reading tricks | MEMORY.md | Environment-specific, not general knowledge |
| API keys, token locations, credential storage | MEMORY.md | Security — injected fresh, not queryable |
| User language preference, communication style | USER.md | Injected every session, affects tone |
| User workflow patterns (verification style, iteration) | USER.md | Procedural, affects how agent operates |
| Provider configs (Vikey, OpenRouter, etc.) | fact_store | Durable, referenced by multiple skills |
| Session facts (Anggira Phase 19 progress, specific cron state) | fact_store | Queryable via search, trust-tracked |

## Removal Procedure

### Remove from MEMORY.md

```python
# Memory tool — batch remove
memory(
  target="memory",
  operations=[
    {"action": "remove", "old_text": "Exact text of the MEMORY entry to remove"},
    ...
  ]
)
```

### Remove from USER.md

```python
memory(
  target="user", 
  operations=[
    {"action": "remove", "old_text": "Exact text of the USER entry to remove"},
    ...
  ]
)
```

### Remove duplicate from fact_store

```python
fact_store(action="remove", fact_id=<id>)
```

## After Cleanup

| Metric | Target |
|--------|--------|
| MEMORY.md usage | <50% (under 1,100 chars) |
| USER.md usage | <60% (under 825 chars) |
| fact_store duplicates | Zero |
| fact_store internal overlap | Zero (run `fact_store(action="contradict")` to verify) |

## Prevention

- **Before adding to MEMORY.md:** search fact_store first. If the fact exists there, do NOT also add to MEMORY.md
- **Before adding to fact_store:** check if it's a tool quirk or env path — those belong in MEMORY.md, not fact_store
- **State-facts vs procedure-facts:** State facts (what IS) → fact_store. Procedure facts (how TO) → MEMORY.md/skills

## Example: Full Audit Output

```
Memory Hygiene Report — 2026-06-27

MEMORY.md: 7 entries, 1,626 chars (73%)
  ❌ DUPLICATE: "Exynos 1280 core mapping" ⊆ fact #4
  ❌ DUPLICATE: "Notion Vault ID" ⊆ fact #11, #13  
  ❌ DUPLICATE: "Anggira 125M GGUF" ⊆ fact #14
  ❌ DUPLICATE: "Scraping APIs" ⊆ fact #15
  ✅ UNIQUE: RTK path, Alpine env, directmind skill, terminal quirk

USER.md: 5 entries, 1,276 chars (92%)
  ❌ DUPLICATE: "Vikey AI provider" ⊆ fact #16
  ✅ UNIQUE: GitHub profile, PAT loc, language pref, verification style

fact_store: 16 facts (had 1 duplicate: #9≈#10)
  ❌ INTERNAL DUPLICATE: fact #10 removed (identical to #9)

After cleanup:
  MEMORY.md: 4 entries, 772 chars (35%) ✅
  USER.md: 4 entries, 1,038 chars (75%) ✅
  fact_store: 15 facts, zero duplicates ✅
```
