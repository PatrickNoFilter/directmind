# Synthesis Examples

Worked examples of think/search/probe/brain modes.

---

## Example 1: think — "what's the status of Anggira training?"

### Step 1: Parallel Retrieval

```python
# Parallel calls:
fact_store(action="search", query="Anggira training status")
session_search(query="Anggira training", limit=5)
fact_store(action="probe", entity="Anggira")
fact_store(action="related", entity="Anggira")
fact_store(action="contradict")
```

### Step 2: Synthesize

**Expected context from retrieval:**
- `[fact:#1]` Anggira is a 125M parameter transformer model
- `[fact:#2]` Uses GGUF format with llama.cpp C API inference
- `[fact:#3]` Training script at `/root/anggira-train/`
- `[session:20260627_011719]` Discussed GGUF pipeline architecture
- `[session:20260627_021427]` Installed directmind skill

**Synthesized answer:**
```
## Answer

Anggira is a 125M parameter transformer model trained using a hybrid inference
approach — HF `tokenizers` for encode/decode and llama_cpp C API for the forward
pass [fact:#1][fact:#2]. The training script lives at `/root/anggira-train/infer_gguf.py`
[fact:#3] and achieves ~4 t/s on A55 cores [memory].

The GGUF pipeline was discussed in our June 27 sessions [session:20260627_011719]
and the directmind skill was installed around the same time [session:20260627_021427].

### Gaps
| Type | Detail |
|------|--------|
| Staleness | Training loss / checkpoint last verified in prior session — not current |
| Unknown | Current training epoch, batch size, learning rate not in brain |
```

### Step 3: Verify

| Claim | Check | Result |
|-------|-------|--------|
| Training script at /root/anggira-train/infer_gguf.py | read_file | ✅ Confirmed |
| ~4 t/s on A55 | Needs re-run | ⚠️ Unverifiable without running |

### Step 4: Learn

- `fact_feedback(helpful, id=1)` — Anggira fact confirmed accurate
- `fact_feedback(helpful, id=2)` — GGUF fact confirmed
- Offer to store new fact: "Anggira checkpoint last verified June 27, 2026"

---

## Example 2: search — "search brain for GGUF pipeline"

### Step 1: Parallel Retrieval

```python
fact_store(action="search", query="GGUF pipeline")
session_search(query="GGUF pipeline", limit=5)
```

### Step 2: Return Raw Results

No synthesis. Return organized by source:

```
## fact_store results
- [fact:#2] Anggira uses GGUF format with llama.cpp C API
- [fact:#4] llama_batch_init / llama_decode / llama_get_logits_ith API pattern

## session_search results
- [session:20260627_011719] "Evaluating GBrain Necessity" — discussed GGUF pipeline
- Excerpt: "...hybrid approach works. Use HF tokenizers for encode/decode..."
```

No verification, no learning.

---

## Example 3: probe — "what do we know about the Notion integration?"

### Step 1: Parallel Retrieval

```python
fact_store(action="probe", entity="Notion")
fact_store(action="related", entity="Notion")
fact_store(action="reason", entities=["Notion"])
session_search(query="Notion", limit=5)
```

### Step 2: Synthesize

```
## Answer

The Notion integration is configured through the MCP protocol [fact:#5].
- **Vault:** 3707b66e — the primary knowledge base [fact:#6]
- **Anggira log:** 3867b66e — training log database [fact:#7]
- **Preferred method:** MCP calls using heading_2 + bulleted_list_item blocks
  to avoid the rich_text bug [fact:#8]

**Key connections:** Notion ⇄ Anggira (logs), Notion ⇄ Vault (knowledge base),
Notion ⇄ Vikey (API key storage) [related]

**Recent activity:** [session:...] discussed Notion API version and page structure.
```

### Step 3: Verify

| Claim | Check | Result |
|-------|-------|--------|
| Vault page exists | notion MCP: retrieve page 3707b66e | ✅ Confirmed |
| MCP server running | process(list) | ✅ Confirmed |

---

## Example 4: brain — "what does my brain know?"

### Step 1: Parallel Retrieval

```python
fact_store(action="list")
session_search()  # browse
```

### Step 2: Return Inventory

```
## fact_store — by category

### project (3 facts)
- Anggira 125M GGUF inference - trust: 0.7
- Training script at /root/anggira-train/ - trust: 0.5
- Notion Vault: 3707b66e - trust: 0.9

### tool (3 facts)
- directmind skill installed at hermes/directmind - trust: 0.8
- firecrawl integration via Firecrawl skill - trust: 0.6
- Vikey provider active - trust: 0.7

### user_pref (2 facts)
- Prefers concise responses with status tables - trust: 0.9
- Indonesian language - trust: 1.0

### Low trust (<0.3) — flag for attention
- [fact:...] Old training config - trust: 0.2

## Recent Sessions
- 20260627_021427 — "Check installation status" - 30m ago
- 20260627_011719 — "Evaluating GBrain Necessity" - 2h ago
```
