# directmind

**Retrieve → Synthesize → Verify → Respond**

A unified brain query skill for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that hits all memory systems in parallel, synthesizes results into a coherent answer with citations, enumerates what the brain doesn't know (gap analysis), and verifies live system state before acting on any claim.

Inspired by GBrain's `think` command — built as a skill, not a separate tool.

## What This Does

Most AI memory tools give you back a list of raw results. `directmind` gives you **the answer**.

| Feature | Raw Tools | directmind |
|---------|-----------|------------|
| Retrieval | ✅ One source at a time | ✅ All sources in parallel |
| Synthesis | ❌ Dump raw results | ✅ Composed answer with citations |
| Gap Analysis | ❌ Silent about missing data | ✅ Explicit "what I don't know" |
| Verification | ❌ Trust stale memory | ✅ Verify live state before acting |
| Contradiction Detection | ❌ Ignore conflicts | ✅ Flag when sources disagree |

## Three Modes

| Mode | Trigger | What Happens |
|------|---------|-------------|
| **think** | "directmind X", "think about X" | Full pipeline: retrieve → synthesize → verify → respond |
| **search** | "search brain for X" | Raw retrieval only (fast, no LLM cost) |
| **probe** | "what do we know about [entity]" | Entity-focused deep dive with graph traversal |

## The Pipeline

```
User asks a question
        │
        ▼
   ┌─────────────┐
   │ 1. Retrieve  │  fact_store + session_search + memory (parallel)
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │ 2. Synthesize│  LLM composes prose answer with citations
   │  + Gaps      │  Enumerates: staleness, missing sources,
   └──────┬──────┘  contradictions, unverified claims, unknowns
          │
          ▼
   ┌──────────────┐
   │ 3. Verify    │  Check live state: files, crons, configs,
   │              │  processes, training metrics, Notion pages
   └──────┬──────┘
          │
          ▼
   ┌──────────────┐
   │ 4. Respond   │  Corrected answer + gaps table + verification table
   └──────────────┘
```

## Install

### Via Hermes Skills CLI (recommended)

```bash
hermes skills install https://raw.githubusercontent.com/PatrickNoFilter/directmind/main/SKILL.md
```

### Manual

```bash
git clone https://github.com/PatrickNoFilter/directmind.git
cp directmind/SKILL.md ~/.hermes/skills/directmind/
cp -r directmind/scripts ~/.hermes/skills/directmind/
```

## Usage

Just talk to Hermes naturally:

```
# Full brain query with synthesis + verification
"directmind what's the status of our training project?"

# Entity-focused probe
"what do we know about the GGUF pipeline?"

# Quick raw search (no synthesis)
"search brain for Modal deploy"
```

## How It Works

### Retrieval Layer
Hits all Hermes memory systems in parallel:
- **fact_store** — keyword search + entity probe + graph traversal + contradiction check
- **session_search** — FTS5 full-text search across all conversation history
- **memory** — persistent cross-session user/environment facts

Results are merged and deduplicated by content similarity.

### Synthesis Layer
The LLM reads all merged results and composes a prose answer where:
- Every claim cites its source: `[fact:#3]`, `[session:abc123]`, `[memory]`
- Related information is grouped thematically, not by source
- Contradictions are presented side-by-side, not silently resolved
- Inferred claims are marked `[inferred]`

### Gap Analysis
Every answer includes an explicit gaps table:

| Type | Detail |
|------|--------|
| 🕐 Staleness | Last data from June 22 (5 days ago) |
| 📭 Missing sources | No data from: email, Slack DMs |
| ⚡ Contradictions | Memory says loss=0.21, session says loss=0.18 |
| 🔍 Unverified | Inferred training still active (no cron check) |
| ❓ Unknown | No data on code fluency evaluation results |

### Verification Layer
Before presenting the answer, `directmind` checks live system state:

| Claim | Check | Result |
|-------|-------|--------|
| Training cron active | `cronjob list` | ✅ Still running (last: 2min ago) |
| GGUF at /root/anggira-train/ | `stat` | ✅ Exists (modified: June 22) |
| Loss was 0.2165 | read checkpoint | ❌ NOW 0.1843 (improved!) |
| Notion log updated | MCP last_edited | ⚠️ Cannot verify (MCP not connected) |

If verification shows a different value than memory, the answer is **corrected automatically**.

## Architecture

```
directmind/
├── SKILL.md                      # Main skill doc (Hermes reads this)
├── README.md                     # This file
├── LICENSE                       # MIT
└── scripts/
    ├── directmind.py             # Orchestrator (retrieval plan, verify plan, formatting)
    └── synthesis_prompt.md       # Gap analysis + verify prompt template
```

## Memory Systems Used

| System | Tool | What It Stores |
|--------|------|---------------|
| Fact Store | `fact_store` | Structured facts with entities, trust scores, graph edges |
| Session Search | `session_search` | Full conversation history (SQLite + FTS5) |
| Persistent Memory | `memory` | User profile + environment notes (~2200 chars) |
| Holographic Memory | `fact_store` (probe/related) | Entity resolution, trust scoring, graph traversal |

## FAQ

**Q: Does this need GBrain?**
No. GBrain is a separate tool with its own database. `directmind` uses Hermes' built-in memory systems and adds the synthesis + gap analysis pattern on top.

**Q: Does it work with any model?**
Yes. The retrieval uses Hermes tools (model-agnostic). The synthesis step is just a prompt — any capable model can do it.

**Q: Does verification make changes to my system?**
No. Verification only READS state (stat, ps, git log, curl health). It never writes or changes anything.

**Q: What if the brain has nothing about my query?**
You'll get: "Nothing found in brain about X" plus a gap entry: `❓ Unknown: zero data on this topic`. No hallucinated answers.

## License

MIT — do whatever you want with it.

## Credits

- Gap analysis pattern inspired by [GBrain](https://github.com/garrytan/gbrain) by Garry Tan
- Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- Created by [PatrickNoFilter](https://github.com/PatrickNoFilter)
