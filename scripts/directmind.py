#!/usr/bin/env python3
"""
directmind.py — Direct Brain Query Orchestrator for Hermes Agent.

Usage (standalone / dev):
  python3 scripts/directmind.py think "what's the status of Anggira training?"
  python3 scripts/directmind.py search "GGUF pipeline"
  python3 scripts/directmind.py probe "Notion"
  python3 scripts/directmind.py brain

Modes:
  think   — Full pipeline: retrieve → synthesize → verify → learn → respond
  search  — Raw retrieval only (zero LLM cost)
  probe   — Entity-focused deep dive (probe + related + reason + session_search)
  brain   — Inventory everything the brain knows

When invoked as a skill (loaded in Hermes), the orchestrator prints a structured
plan for the agent to execute — markers for parallel retrieval, synthesis rules,
verification checks, and learning steps.
"""

import sys
import json
import argparse
from typing import Any


def build_retrieval_plan(query: str, mode: str) -> dict[str, Any]:
    """Build a structured retrieval plan based on query and mode."""
    entities = _extract_entities(query)
    
    plan = {
        "mode": mode,
        "query": query,
        "entities": entities,
        "retrieval_steps": [],
        "synthesis_required": mode in ("think", "probe"),
        "verify_required": mode == "think",
        "learn_required": mode == "think",
    }
    
    # Always: fact_store search + session_search
    plan["retrieval_steps"].append({
        "tool": "fact_store",
        "action": "search",
        "query": query,
        "reason": "Primary knowledge graph retrieval"
    })
    plan["retrieval_steps"].append({
        "tool": "session_search",
        "action": "discovery",
        "query": query,
        "limit": 5,
        "reason": "Conversation history"
    })
    
    # Entity-aware steps
    if entities:
        for entity in entities:
            plan["retrieval_steps"].append({
                "tool": "fact_store",
                "action": "probe",
                "entity": entity,
                "reason": f"HRR entity recall for '{entity}'"
            })
            plan["retrieval_steps"].append({
                "tool": "fact_store",
                "action": "related",
                "entity": entity,
                "reason": f"Graph connections for '{entity}'"
            })
        if len(entities) > 1:
            plan["retrieval_steps"].append({
                "tool": "fact_store",
                "action": "reason",
                "entities": entities,
                "reason": "Compositional JOIN — multi-entity relationship"
            })
    
    # Mode-specific steps
    if mode == "think":
        plan["retrieval_steps"].append({
            "tool": "fact_store",
            "action": "contradict",
            "reason": "Memory hygiene — detect contradictions"
        })
    elif mode == "brain":
        plan["retrieval_steps"].append({
            "tool": "fact_store",
            "action": "list",
            "reason": "Full inventory"
        })
        plan["retrieval_steps"].append({
            "tool": "session_search",
            "action": "browse",
            "reason": "Recent sessions overview"
        })
    
    return plan


def build_synthesis_guide(plan: dict[str, Any]) -> str:
    """Build synthesis instructions for the agent."""
    guide = f"""## Synthesis Instructions ({plan['mode']} mode)

### Context Assembly
Merge all retrieval results into a single coherent context block.
Deduplicate by content similarity (not exact match — two sources may describe the same fact differently).

### Citation Format
- fact_store results: `[fact:#ID]` (include fact ID)
- session_search results: `[session:XXXX]` (include session ID)
- Working memory: `[memory]`
- Tasks: `[todo]`

### Trust Tiers
- ≥0.7: Authoritative — treat as confirmed
- 0.3–0.7: Moderate — may need verification
- <0.3: Uncertain — flag in gaps, do NOT treat as fact

### Composition Rules
1. Write in prose — group thematically, NOT by source
2. Lead with most current / impactful information
3. Include timeline when topic has history
4. Flag contradictions explicitly: present BOTH sides with citations
5. Mark inferred claims as `[inferred]`

### Mode-Specific
- **think**: Full synthesis + gaps + verification + learning
- **probe**: Entity-centered narrative — all connections to {plan['entities'] or 'the entity'}
- **search**: NO synthesis — return raw results grouped by source
- **brain**: Inventory-style — categorized overview

### Empty Context Rule
If ALL retrieval returns nothing: say "Nothing found in brain about {plan['query']}".
Do NOT hallucinate facts from unrelated knowledge.
"""
    return guide


def build_verify_guide(plan: dict[str, Any]) -> str:
    """Build verification instructions."""
    return """## Verification Instructions

After synthesis, identify every factual claim about **live system state** and verify:

| If synthesis mentions... | Verify by... |
|---|---|
| A file path | `read_file` or `search_files` — exists? content matches? |
| A cron job | `cronjob(action="list")` — still running? correct schedule? |
| A running process | `terminal("ps aux | grep X")` |
| A git state | `terminal("git log -1", workdir=path)` |
| A config value | Read the config file directly |
| A training metric | Read checkpoint/log file |
| A Notion page | MCP tool — check `last_edited_time` |
| An API endpoint | `curl` health check if safe |

**NOT verifiable:** past events, user preferences, design decisions.

**Critical:** If verify differs from memory → CORRECT the answer.
Also update stale facts in the brain (learning step).
"""


def build_learn_guide(plan: dict[str, Any]) -> str:
    """Build learning/feedback instructions with active feedback loop."""
    return f"""## Learning Instructions (Brain Feedback Loop)

### 1. AUTO-FEEDBACK — Monitor User Reaction
After delivering your answer, WATCH for these user signals and react:

**Confirmation signals** — user says "betul", "oke", "benar", "yes", "mantap", "👍", "terima kasih", "thanks":
→ For each fact_id that was used in the answer, call:
  `fact_feedback(action="helpful", fact_id=<ID>)`
  This boosts trust_score → e.g. 0.5 → 0.6

**Correction signals** — user says "salah", "bukan", "sebenarnya", "tidak", "kurang tepat":
→ Identify WHICH fact was wrong
→ `fact_feedback(action="unhelpful", fact_id=<ID>)`
→ Ask: "Koreksi yang benar apa?" → then `fact_store(action="add", content=<corrected>)`

**If user explicitly rates:**
→ If they say ✅ or "ya membantu" → helpful
→ If they say ❌ or "tidak membantu" → ask what's wrong, then fix

### 2. Fact Feedback — Manual (after response)
For every fact_store fact that contributed to the answer:
- `fact_feedback(action="helpful", fact_id=<ID>)` — for facts that proved accurate
- `fact_feedback(action="unhelpful", fact_id=<ID>)` — for stale/wrong facts

### 3. Correct Stale Facts
If verification found outdated data:
- `fact_store(action="update", fact_id=<ID>, content=<corrected>)`

### 4. Offer to Store New Knowledge
If synthesis produced genuinely new, durable knowledge:
- Ask user: "Found new info about X — save to brain?"
- If confirmed: `fact_store(action="add", content=..., category=..., tags=...)`
- Only store durable facts (not session-specific ephemera)

### 5. Gap Closed Detection
If this query was answering something the brain previously had NO knowledge about (gap):
→ After user confirms answer was correct:
  `fact_store(action="add", content="<the new knowledge>", category="general")`
  This means next time the brain KNOWS it without needing web search.
"""


def format_think_output(plan: dict[str, Any]) -> str:
    """Full think mode output."""
    return f"""# 🧠 Directmind: think

## Query
{plan['query']}

## Entities Detected
{', '.join(plan['entities']) if plan['entities'] else 'None detected'}

---

## Step 1: Parallel Retrieval (execute ALL together)

```json
{json.dumps(plan['retrieval_steps'], indent=2)}
```

{chr(10).join(f"[ ] `{s['tool']}` action={s['action']} — {s['reason']}" for s in plan['retrieval_steps'])}

---

## Step 2: Synthesize

{build_synthesis_guide(plan)}

---

## Step 3: Verify

{build_verify_guide()}

---

## Step 4: Learn

{build_learn_guide(plan)}

---

## Step 5: Respond (Format)

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
After sending the answer above, PAUSE and watch for user response:

| User says | Action |
|-----------|--------|
| "betul", "oke", "benar", "mantap", "👍" | `fact_feedback(action="helpful", fact_id=<ID>)` for each fact used |
| "salah", "bukan", "kurang tepat", "❌" | Identify wrong fact → `fact_feedback(action="unhelpful", fact_id=<ID>)` → ask for correction |
| Anything else | Ask: "Apakah jawaban ini membantu? ✅/❌" |

**This is how the brain learns.** Without feedback, trust scores stay at 0.5 forever.
```
"""


def format_search_output(plan: dict[str, Any]) -> str:
    """Search mode — raw retrieval only."""
    steps = [s for s in plan['retrieval_steps'] if s['tool'] != 'contradict']
    return f"""# 🔍 Directmind: search

## Query
{plan['query']}

## Entities Detected
{', '.join(plan['entities']) if plan['entities'] else 'None detected'}

---

## Retrieval Steps (execute ALL in parallel)

{chr(10).join(f"- `{s['tool']}` action={s['action']} — {s['reason']}" for s in steps)}

---

**Rules:**
- Return raw results grouped by source
- DO NOT synthesize or summarize
- DO NOT verify
- DO NOT learn/feedback
"""


def format_probe_output(plan: dict[str, Any]) -> str:
    """Probe mode — entity-focused deep dive."""
    return f"""# 🎯 Directmind: probe

## Entity
{plan['entities'][0] if plan['entities'] else plan['query']}

## Retrieval Steps (execute ALL in parallel)

```json
{json.dumps(plan['retrieval_steps'], indent=2)}
```

{chr(10).join(f"- `{s['tool']}` action={s['action']} — {s['reason']}" for s in plan['retrieval_steps'])}

---

## Synthesis (after retrieval)
Build a complete narrative around this entity:
- What is it? (description, purpose)
- Current status
- Key connections (related entities)
- History / decisions made
- Open questions or known issues

**Do NOT verify or learn in probe mode.**

## 💬 Feedback (after responding)
After answering, ask user: "Apakah info ini membantu? ✅/❌"
If helpful → `fact_feedback(action="helpful", fact_id=<ID>)` for facts used
If not → ask what's missing"""


def format_brain_output() -> str:
    """Brain dump mode."""
    return """# 📚 Directmind: brain

## Retrieval Steps (execute ALL in parallel)

- `fact_store` action=list — Full inventory
- `session_search` browse — Recent sessions overview

---

**Rules:**
- Return inventory organized by category and trust score
- Show recent session titles + previews
- NO synthesis needed — just catalog what the brain contains
- Flag low-trust facts (<0.3) for attention
"""


def _extract_entities(query: str) -> list[str]:
    """Simple entity extraction from query string."""
    import re
    
    entities = set()
    
    # Quoted phrases
    quoted = re.findall(r'"([^"]+)"', query)
    entities.update(q.strip() for q in quoted if len(q.strip()) > 2)
    
    # Capitalized multi-word phrases (potential proper nouns)
    caps = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', query)
    entities.update(c.strip() for c in caps if len(c.strip()) > 3)
    
    return list(entities)


def main():
    parser = argparse.ArgumentParser(description="Directmind — Brain Query Orchestrator")
    parser.add_argument("mode", choices=["think", "search", "probe", "brain"],
                        help="Operation mode")
    parser.add_argument("query", nargs="*", default="",
                        help="Query text (for think/search/probe)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON plan only")
    
    args = parser.parse_args()
    query = " ".join(args.query) if args.query else ""
    
    if args.mode == "brain":
        if args.json:
            print(json.dumps({"mode": "brain", "retrieval_steps": [
                {"tool": "fact_store", "action": "list"},
                {"tool": "session_search", "action": "browse"}
            ]}))
        else:
            print(format_brain_output())
        return
    
    if not query.strip():
        print("Error: query required for think/search/probe modes", file=sys.stderr)
        sys.exit(1)
    
    plan = build_retrieval_plan(query, args.mode)
    
    if args.json:
        print(json.dumps(plan, indent=2))
        return
    
    outputters = {
        "think": format_think_output,
        "search": format_search_output,
        "probe": format_probe_output,
    }
    
    print(outputters[args.mode](plan))


if __name__ == "__main__":
    main()
