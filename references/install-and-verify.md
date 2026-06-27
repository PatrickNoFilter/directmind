# Install & Verify

Steps to install directmind and verify it's working, plus GitHub upload plan.

## Installation

Directmind is installed as a Hermes skill under `hermes/directmind/`:

```bash
# The skill lives at:
~/.hermes/skills/hermes/directmind/
├── SKILL.md
├── scripts/
│   ├── directmind.py
│   └── synthesis_prompt.md
└── references/
    ├── hermes-brain-architecture.md
    ├── gbrain-comparison.md
    ├── synthesis-examples.md
    └── install-and-verify.md
```

## Verify Installation

```bash
# Check skill is registered
hermes skills list | grep directmind

# Load skill
skill_view(name="hermes/directmind")

# Test scripts
cd /root/directmind && python3 scripts/directmind.py think "test query" --json

# Check no duplicate skills
ls ~/.hermes/skills/directmind/ 2>/dev/null && echo "DUPLICATE EXISTS" || echo "CLEAN"
```

## Usage

Once loaded, trigger via:

- "directmind what's the status of Anggira?"
- "think about the Notion integration"
- "search brain for GGUF pipeline"
- "probe the Vikey provider"
- "what does my brain know?"

## GitHub Upload Plan

Directmind source code lives at `/root/directmind/` and should be uploaded to GitHub:

**Repo:** `PatrickNoFilter/directmind`

### Files to upload:
```
directmind/
├── SKILL.md              # Skill definition (also synced to hermes/directmind/)
├── README.md             # Project documentation
├── LICENSE               # MIT
├── scripts/
│   ├── directmind.py     # Orchestrator script
│   └── synthesis_prompt.md  # Synthesis prompt template
└── references/           # Additional documentation
    ├── hermes-brain-architecture.md
    ├── gbrain-comparison.md
    └── synthesis-examples.md
```

### Steps:
1. Create repo on GitHub
2. `cd /root/directmind && git init && git add -A && git commit -m "Initial commit: directmind brain query skill"`
3. `git remote add origin https://github.com/PatrickNoFilter/directmind.git`
4. `git push -u origin main`

### Post-upload:
- Update SKILL.md homepage URL if different
- Consider publishing to Hermes skills hub
- Remove duplicate `/root/directmind/` source if only needed as repo
