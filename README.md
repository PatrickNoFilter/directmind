# directmind

**Retrieve → Synthesize → Verify → Respond → Evolve**

A unified brain query skill for [Hermes Agent](https://github.com/NousResearch/hermes-agent) with a **self-evolving architecture** — learns from feedback, reviews itself periodically, detects knowledge gaps, and auto-updates its own skill files.

## 4-Layer Self-Evolving Architecture

| Layer | Name | Type | Description |
|-------|------|------|-------------|
| **1** | **Feedback Loop** | 🔄 Realtime | When user says "betul"/"oke" → `fact_feedback(helpful)` boosts trust; "salah" → asks for correction |
| **2** | **Cron Self-Review** | 📅 Weekly (Mon 09:00) | Brain health check: trust distribution, contradictions, stale facts |
| **3** | **Gap Learner** | 📅 Weekly (Mon 09:00) | Scans recent sessions for entities user asked about but missing from brain |
| **4** | **Skill Patcher** | 📅 Weekly (Mon 09:00) | Detects drift between active skill and git repo, can auto-sync |

Each layer feeds into the next — feedback trains trust, review finds gaps, gaps trigger learning, learning updates the skill itself.

## Four Modes

| Mode | Command | What Happens |
|------|---------|-------------|
| **think** | `directmind X` / `think about X` | Full pipeline: retrieve → synthesize → verify → respond + feedback loop |
| **search** | `search brain for X` | Raw retrieval only (fast, no LLM cost) |
| **probe** | `what do we know about [entity]` | Entity-focused deep dive with graph traversal |
| **brain** | `directmind brain` | Inventory all stored facts + recent sessions |

## The Pipeline (Layer 1 — Think Mode)

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
   │ 3. Verify    │  Check live state: files, crons, configs, processes
   │              │  If value changed → auto-correct answer
   └──────┬──────┘
          │
          ▼
   ┌──────────────┐
   │ 4. Respond   │  Answer + gaps table + verification table
   │  + Feedback  │  Detect "betul"/"salah" → fact_feedback / koreksi
   └──────────────┘
          │
          ▼
   ╔══════════════════════╗
   ║  5. Auto-Learn       ║  If response had no brain data on topic
   ║  (Gap Closed)        ║  → offer to save new knowledge to fact_store
   ╚══════════════════════╝
```

## Weekly Brain Health (Layers 2–4 — Cron)

Every Monday at 09:00, the `directmind-weekly-brain-health` cron job runs three checks:

### Layer 2: Self-Review
```
📊 Mental Health Report
   Total facts | avg trust | low-trust | contradictions | stale facts | health score
   💡 Recommendations: which facts need attention
```

### Layer 3: Gap Learner
```
🔍 Gap Analysis
   Sessions scanned | entities extracted | brain entities | knowledge gaps
   🔴 Top gaps: entities user asked about but brain doesn't know
   👻 Orphan facts: stored facts with no entity link
```

### Layer 4: Skill Patcher
```
🛠️  Skill Health
   Version check (local vs GitHub) | drift detection | backup availability
   💡 Run --apply to sync if drifted
```

All three are `no_agent=True` scripts — zero LLM cost, run in <1 second.

### Via Hermes Skills CLI (recommended)

```bash
hermes skills install https://raw.githubusercontent.com/PatrickNoFilter/directmind/main/SKILL.md
```

### Prerequisites

Directmind relies on Hermes' **Holographic Memory Provider** which provides the `fact_store` tool. Verify it's active:

```bash
hermes memory status
# Should show: Provider: holographic, Status: available ✓
```

If holographic is not set up:

```bash
hermes memory setup holographic
# Then restart Hermes session (/reset in TUI)
```

All other dependencies are built-in (SQLite, Python 3).

### Dependency Auto-Check

```bash
python3 scripts/check_deps.py
# → Holographic: ✅ | fact_store: ✅ | Python: ✅ | SQLite: ✅
```

### Manual Install
```bash
git clone https://github.com/PatrickNoFilter/directmind.git
hermes skills install directmind/SKILL.md
```

## Usage

Just talk to Hermes naturally:

```markdown
# Full brain query with synthesis + feedback loop
"directmind what's the status of our training project?"
  → Answer + gaps + verification + feedback prompt

# Entity-focused probe
"what do we know about the GGUF pipeline?"
  → Deep dive: all facts about that entity + related entities

# Quick raw search (no synthesis)
"search brain for Modal deploy"
  → Raw fact matches with trust scores

# Brain inventory
"directmind brain"
  → All facts + recent sessions

# Feedback (automatic — just respond)
"betul"  → trust score boosted for cited facts
"salah"  → agent asks: "what's the right answer?"
```

## Scripts Reference

```
scripts/
├── directmind.py       # Layer 1: think/probe/search/brain modes
├── self_review.py      # Layer 2: brain health + trust analysis
├── gap_learner.py      # Layer 3: cross-session gap detection
└── skill_patcher.py    # Layer 4: version check + auto-sync
```

### Manual script runs

```bash
# Self-Review
python3 scripts/self_review.py

# Gap Learner
python3 scripts/gap_learner.py
python3 scripts/gap_learner.py --days 30
python3 scripts/gap_learner.py --verbose

# Skill Patcher (dry-run)
python3 scripts/skill_patcher.py

# Apply update from local git repo
python3 scripts/skill_patcher.py --apply

# Force update from GitHub raw
python3 scripts/skill_patcher.py --apply --force-from-github
```

### Cron job

```bash
# Weekly health check (Mon 09:00)
cronjob(action="run", job_id="26102aaf089b")
```

## Key Design Decisions

- **No containers needed** — runs directly in Hermes on Android PRoot, Linux, macOS
- **WAL mode SQLite** — unlimited concurrent readers, cron never blocks Hermes
- **Read-only scripts** — Layer 2/3/4 scripts never write outside backup dir
- **No LLM cost for cron** — `no_agent=True` scripts produce output directly
- **Backups before update** — skill_patcher creates `.backup/` timestamps before overwriting
- **Overlap-safe** — mutual exclusion via SQLite WAL mode + read-only connections
- **Self-verifying** — after every conclusion, directmind runs verification against its own claims, checks live system state, and auto-corrects any discrepancy before finalizing the answer

## Architecture

```
directmind/
├── SKILL.md                       # Main skill doc
├── README.md                      # This file
├── LICENSE                        # MIT
└── scripts/
    ├── directmind.py              # Layer 1: think/probe/search/brain + feedback
    ├── self_review.py             # Layer 2: brain health (trust/distribution)
    ├── gap_learner.py             # Layer 3: knowledge gap detection
    └── skill_patcher.py           # Layer 4: version/drift + auto-sync
```

## License

MIT — do whatever you want with it.

## Credits

- Gap analysis pattern inspired by [GBrain](https://github.com/garrytan/gbrain) by Garry Tan
- **Holographic Memory / fact_store** — built on Hermes Agent's [memory infrastructure](https://hermes-agent.nousresearch.com/docs) with entity resolution, trust scoring, and graph traversal
- Built for [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research
- Created by [PatrickNoFilter](https://github.com/PatrickNoFilter)
