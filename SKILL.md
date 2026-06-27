---
name: directmind
description: "Direct brain queries for Hermes — unified retrieval across all memory systems (fact_store, session_search, memory, skills, todos), synthesis with gap analysis, live verification, and brain learning via fact feedback."
version: 2.1.0
author: PatrickNoFilter
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memory, brain, synthesis, retrieval, gap-analysis, verify, holographic, fact-store, session-search]
    homepage: https://github.com/PatrickNoFilter/directmind
    related_skills: [hermes-agent]
---

# directmind

**Retrieve → Synthesize → Verify → Learn → Respond**

A unified brain query skill for Hermes Agent that hits ALL memory systems in parallel, synthesizes results with citations, verifies live state, and feeds back into the brain so it gets smarter over time.

**GitHub:** `PatrickNoFilter/directmind`

## Hermes Brain Architecture

Before using this skill, understand what the brain consists of:

| Layer | Tool | What It Holds | Capacity |
|-------|------|---------------|----------|
| **Working Memory** | `memory` (MEMORY.md + USER.md) | Agent notes + user profile | ~2,200 + ~1,375 chars (in system prompt) |
| **Long-Term Facts** | `fact_store` (holographic) | Facts with trust scores, entity graphs, HRR vectors | Unlimited (SQLite) |
| **Conversation History** | `session_search` (FTS5) | All past sessions, message-level indexed | Unlimited (SQLite) |
| **Procedural Memory** | `skills_list`/`skill_view` | Reusable workflows and how-tos | Per-skill files |
| **Task Context** | `todo` | Current session's task list | In-session only |
| **Scheduled Work** | `cronjob(list)` | Cron jobs and their outputs | Persistent |

### Holographic Memory (fact_store) — Full Capability Map

| Action | What It Does | When to Use |
|--------|-------------|-------------|
| `search` | FTS5 keyword search, trust-weighted | Always — primary retrieval |
| `probe` | Entity-focused recall via HRR algebra | When query has a named entity |
| `related` | Graph connections between entities | When exploring an entity's network |
| `reason` | **Multi-entity compositional JOIN** — finds facts connected to ALL entities simultaneously | "What connects X and Y?" — HRR's killer feature |
| `contradict` | Finds facts with same entities but divergent content | Memory hygiene, trust validation |
| `list` | Browse all facts by category/trust | "What does my brain know?" |
| `add` | Store a new fact with category + tags | Auto-store new discoveries |
| `update` | Modify fact content, trust, tags | After verify finds stale data |
| `remove` | Delete a fact | When verify finds false data |

**Trust scores**: 0.0–1.0. `fact_feedback(helpful)` → +0.05, `fact_feedback(unhelpful)` → -0.10. Facts < 0.3 are uncertain — flag in gaps.

**Entity resolution**: Automatic — capitalized phrases, quoted terms, AKA patterns extracted on store. Case-insensitive alias matching.

---

## When to Load This Skill

| Trigger | Example |
|---------|---------|
| User asks about past work, decisions, context | "what do we know about Anggira?", "what happened with the training?" |
| User wants a synthesized answer, not raw dumps | "directmind X", "think about X", "brain query X" |
| User wants entity-focused recall | "what do we know about [person/thing/project]?" |
| User wants to explore connections | "how are X and Y related?", "what connects A and B?" |
| User wants to know what the brain knows | "list all facts about X", "brain dump" |
| Before acting on remembered facts | "update the cron job for training" (verify first!) |
| User wants brain health | "how's the brain?", "what does the brain know about X?" |

---

## Four Modes

### 1. `think` — Full Pipeline (default)

Retrieve from ALL sources → synthesize → verify → learn → respond with gaps.

```
User: "what's the status of Anggira training?"
→ Parallel retrieval: fact_store search + probe + reason + session_search + memory
→ Synthesize: current status, history, key decisions (with citations)
→ Verify: checkpoint file exists? cron still running? loss current?
→ Learn: fact_feedback on facts used, offer to store new discoveries
→ Returns: answer + citations + gaps table + verification table
```

### 2. `search` — Raw Retrieval Only

Hit all memory sources, return merged results without synthesis. **Zero LLM cost.**

```
User: "search brain for GGUF pipeline"
→ Returns: raw facts + session excerpts + memory entries
→ No synthesis, no verification (fast)
```

### 3. `probe` — Entity-Focused Recall

Deep dive on a specific entity (person, project, tool, concept).

```
User: "what do we know about the Notion integration?"
→ fact_store probe("Notion") + related("Notion") + reason(["Notion"]) + session_search("Notion")
→ Synthesizes everything about that entity
→ Verifies: MCP server running? page still exists?
```

### 4. `brain` — Brain Dump

Inventory of everything the brain knows. No synthesis needed.

```
User: "what does my brain know?"
→ fact_store(list) + session_search(browse)
→ Shows inventory organized by category/trust
```

---

## Workflow (Execute in Order)

### Step 1: Parallel Retrieval

Run ALL of these in a SINGLE turn (parallel tool calls). Pick the set based on mode:

**Always (all modes):**
```
1. fact_store(action="search", query=<user_query>)
2. session_search(query=<user_query>, limit=5)
```

**When query has named entities** (probe mode, or entity detected in think):
```
3. fact_store(action="probe", entity=<entity>)
4. fact_store(action="related", entity=<entity>)
5. fact_store(action="reason", entities=<all_detected_entities>)  ← KILLER FEATURE
```

**In think mode:**
```
6. fact_store(action="contradict")  # memory hygiene check
```

**Brain dump mode:**
```
3. fact_store(action="list", category=<if_category_specified>)
4. session_search()  # no args = browse recent sessions
```

**System prompt already contains** MEMORY.md + USER.md — use that context directly.

**Also consider** (contextual):
- `session_search()` (no args = BROWSE recent sessions) for "what have we been working on"
- `todo()` for current task context if query is about ongoing work

### Step 2: Synthesize

Using the merged context, compose a structured answer. Key rules:
- Every claim MUST cite its source: `[fact:#ID]`, `[session:XXXX]`, `[memory]`
- Write in prose, not bullet dumps — the user wants THE ANSWER
- Group thematically, not by source
- Lead with most important/current information
- Flag contradictions explicitly — present BOTH sides
- Mark inferred claims as `[inferred]`
- Trust tiers: ≥0.7 authoritative, 0.3–0.7 moderate, <0.3 uncertain

### Step 3: Verify

After synthesis, verify every claim about **live system state**:

| If synthesis mentions... | Verify by... |
|---|---|
| A file path | `read_file` or `search_files` |
| A cron job | `cronjob(action="list")` |
| A running process | `terminal("ps aux | grep X")` |
| A git state | `terminal("git log -1", workdir=path)` |
| A config value | Read config file |
| A Notion page | MCP tool call |

**NOT verifiable** (historical): past events, user preferences, design decisions.

**If verify differs from memory → CORRECT the answer.**

### Step 4: Learn (Brain Feedback Loop)

**4a. AUTO-FEEDBACK — Monitor User Reaction** (added Layer 1)

After delivering the answer, PAUSE and watch for these user signals:

| User says | Action |
|-----------|--------|
| "betul", "oke", "benar", "mantap", "👍", "terima kasih", "thanks" | `fact_feedback(action="helpful", fact_id=<ID>)` for each fact used — boosts trust_score +0.05 |
| "salah", "bukan", "sebenarnya", "tidak", "kurang tepat", "❌" | Identify the wrong fact → `fact_feedback(action="unhelpful", fact_id=<ID>)` → ask "Koreksi yang benar apa?" → `fact_store(action="add", content=<corrected>)` |
| Explicit ✅ | Helpful |
| Explicit ❌ | Ask what's wrong, then fix |
| Anything else | Ask: "Apakah jawaban ini membantu? ✅/❌" |

Without feedback, trust scores stay at 0.5 forever.

**4b. Gap Closed Detection** — if this query answered something the brain had NO knowledge about:
```
# After user confirms answer was correct:
fact_store(action="add", content="<new durable knowledge>", category="general", tags=["auto-gap-closed"])
```

**4c. Fact Feedback** — for every fact cited in the answer:
```
fact_feedback(action="helpful", fact_id=<ID>)
```

**4d. Correct Stale Facts** — if verify found outdated data:
```
fact_store(action="update", fact_id=<ID>, content=<corrected>)
```

**4e. Auto-Store** — if synthesis found new knowledge, OFFER to store:
```
fact_store(action="add", content=<new_fact>, category=<appropriate>, tags=<relevant>)
```

### Layer 2 — Cron Self-Review (terjadwal)

A weekly cron job that automatically reviews brain health by reading the fact_store database directly.

**Schedule:** Setiap Senin 09:00 via `directmind-weekly-review` cron job.

**What it checks:**
| Metric | What it means |
|--------|-------------|
| 📊 Trust distribution | How many facts are high/medium/low trust |
| ⚠️ Low-trust facts | Facts with trust < 0.3 — need attention |
| ⚡ Contradictions | Same entity with conflicting trust or duplicate content |
| ⏳ Stale facts | Facts not touched in >60 days |
| 🏥 Health score | 0–100 overall brain health index |
| 💡 Recommendations | Action items to improve brain quality |

**Cron job info:**
- `no_agent=True` — runs script directly, no LLM cost
- Output delivered to origin chat
- Script: `scripts/self_review.py` (reads `~/.hermes/memory_store.db` read-only)

**Manual trigger:**
```
cronjob(action="run", job_id="26102aaf089b")
```

Or run standalone:
```
python3 ~/.hermes/skills/hermes/directmind/scripts/self_review.py
```

### Layer 3 — Gap Learner (proaktif)

A weekly cron job that scans recent conversations for entities the user asked about but that have NO corresponding facts in the brain.

**How it works:**
| Step | What it does |
|------|-------------|
| 1 | Reads last 7 days of session history from `state.db` |
| 2 | Extracts capitalized entities (phrases, acronyms, quoted terms) |
| 3 | Cross-references against all entities registered in `fact_store` |
| 4 | Reports entities mentioned 2+ times but missing from brain |
| 5 | Flags orphan facts (facts with no entity link) |

**Cron job:** Runs every Monday 09:00 as part of `directmind-weekly-brain-health`.

**Also flags orphan facts** — facts stored in brain but with NO entity link, making them invisible to `probe`/`reason`.

**Manual run:**
```
cronjob(action="run", job_id="26102aaf089b")
```
or
```
python3 ~/.hermes/skills/hermes/directmind/scripts/gap_learner.py
python3 ~/.hermes/skills/hermes/directmind/scripts/gap_learner.py --days 30
python3 ~/.hermes/skills/hermes/directmind/scripts/gap_learner.py --verbose
```

### Step 5: Respond

```markdown
## Answer
[Synthesized prose with inline citations]

## ⚠️ Gaps
| Type | Detail |
|------|--------|
| 🕐 Staleness | ... |
| 📭 Missing sources | ... |
| ⚡ Contradictions | ... |
| 🔍 Unverified | ... |
| ❓ Unknown | ... |

## ✅ Verification
| Claim | Check | Result |
|-------|-------|--------|
| ... | ... | ✅/❌/⚠️ |

## 🧠 Brain Learning
[N facts feedback] [N stale corrected] [N new suggested]

## 💬 Feedback (WAIT for user reaction)
After sending, PAUSE and watch:

| User says | Action |
|-----------|--------|
| "betul", "oke", "mantap", "👍" | `fact_feedback(helpful)` for each fact used |
| "salah", "bukan", "❌" | `fact_feedback(unhelpful)` → ask koreksi |
| Anything else | "Apakah jawaban ini membantu? ✅/❌" |
```

---

## Skip Rules

| Skip... | When... |
|---------|---------|
| **verify** | Mode is `search`, pure history query, user says "quick" |
| **learn** | Mode is `search` |
| **synthesis** | Mode is `search` or `brain` |
| **probe/reason** | Query has no named entities |
| **contradict** | Mode is `search` or `probe` |

---

## Pitfalls

1. **Don't synthesize empty context.** If all retrieval returns nothing, say "nothing found in brain about X".

2. **`reason` vs `probe` vs `search`.** `search` = keyword (FTS5). `probe` = entity algebra (HRR, single entity). `reason` = compositional JOIN (HRR, multiple entities). Use `reason` for relationship questions.

3. **session_search bookends.** `bookend_start`/`bookend_end` show first/last messages — use for context.

4. **Memory is in system prompt.** MEMORY.md + USER.md frozen at session start — don't re-read.

5. **Verify reads, learn writes.** Never modify state during verify step. Write only in learn step.

6. **Trust scores matter.** <0.3 = uncertain, >0.7 = well-confirmed. Don't treat low-trust as authoritative.

7. **`fact_feedback` is the learning loop.** Every answer should feedback on facts used.

8. **Contradict is O(n²).** Capped at 500 facts. Think mode only.

9. **Entity extraction is imperfect.** Regex-based. If probe returns empty, try search.

10. **Don't flood the brain.** Only auto-store durable, factual, genuinely new knowledge.

11. **Large gap tables are noise.** Max 3-5 gap rows, prioritize by impact.

12. **`skill_manage patch` hanya update skill dir, bukan git repo.** Kalau skill juga di-track di repo GitHub, copy manual:
    ```
    cp ~/.hermes/skills/hermes/<skill>/scripts/<file> /repo/path/scripts/<file>
    ```
    Lupa sync → repo punya kode lama.

13. **`cronjob(script=)` tidak menerima absolute path.** Taruh wrapper di `~/.hermes/scripts/`:
    ```
    # ~/.hermes/scripts/directmind-review.sh
    #!/bin/sh
    python3 ~/.hermes/skills/hermes/directmind/scripts/self_review.py
    ```
    Detail skema DB ada di `references/fact_store_schema.md`.

## Pitfalls (continued)

14. **Memory overlap wastes capacity and causes staleness.** MEMORY.md (2,200 chars) and USER.md (1,375 chars) are limited. Never store facts there that already exist in fact_store — the fact_store copy is canonical and trust-tracked. Run a memory hygiene scan periodically: cross-reference every MEMORY/USER entry against fact_store, remove duplicates from the limited stores. See `references/memory-hygiene.md` for the full methodology.

15. **One fact, one place — always.** Before adding to MEMORY.md, check fact_store first. Before adding to fact_store, ask: "is this a tool/environment quirk?" — those belong in MEMORY.md. State facts → fact_store. Procedure facts → MEMORY.md or skills.

## References

- `references/hermes-brain-architecture.md` — Complete inventory of all Hermes memory/brain systems, HRR details, trust scoring, entity resolution, retrieval pipeline internals
- `references/gbrain-comparison.md` — Feature comparison with GBrain's `think` command
- `references/synthesis-examples.md` — Worked examples of think/search/probe modes
- `references/install-and-verify.md` — Install/verify steps and GitHub upload plan
- `references/memory-hygiene.md` — Memory deduplication audit: detect, resolve, and prevent overlap between MEMORY.md, USER.md, and fact_store
