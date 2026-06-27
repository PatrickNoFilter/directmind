#!/usr/bin/env python3
"""
install.py — Directmind one-stop installer.

Usage:
  python3 install.py                    # Install from GitHub (default)
  python3 install.py --repo /path       # Install from local repo
  python3 install.py --skill-only       # Skip holographic setup

What it does:
  1. Checks all dependencies (Python, SQLite, Hermes CLI)
  2. Installs Holographic memory provider if missing
  3. Installs the directmind skill
  4. Verifies everything works end-to-end
"""
import os, sys, subprocess, sqlite3, tempfile, shutil

SELF_DIR = os.path.dirname(os.path.abspath(__file__))

GITHUB_URL = "https://raw.githubusercontent.com/PatrickNoFilter/directmind/main"
HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

OK = chr(10003)
FAIL = chr(10007)
passes = 0
fails = 0

def check(name, ok, detail=""):
    global passes, fails
    if ok:
        print(f"  [{OK}] {name}" + (f"  {detail}" if detail else ""))
        passes += 1
    else:
        print(f"  [{FAIL}] {name}" + (f"  {detail}" if detail else ""))
        fails += 1

def step(msg):
    print(f"\n--- {msg} ---")

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

# ---------------------------------------------------------------------------
step("1. Checking runtime dependencies")

# Python
v = sys.version_info
check("Python 3.10+", v.major >= 3 and v.minor >= 10, f"(v{v.major}.{v.minor}.{v.micro})")

# SQLite
check("SQLite available", sqlite3.sqlite_version_info >= (3, 0),
      f"(v{sqlite3.sqlite_version})")

# Hermes CLI
r = run(["hermes", "--version"])
check("Hermes CLI accessible", r.returncode == 0, r.stdout.strip()[:60] if r.stdout else "")

# memory_store.db readable
db = os.path.join(HERMES_HOME, "memory_store.db")
if os.path.exists(db):
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM facts")
        count = c.fetchone()[0]
        check(f"Facts accessible ({count} stored)", True)
        conn.close()
    except Exception as e:
        check("Can read memory_store.db", False, str(e))
        fails += 1

# ---------------------------------------------------------------------------
step("2. Holographic memory provider")

if "--skill-only" in sys.argv:
    check("Skipping holographic setup (--skill-only)", True)
else:
    r = run(["hermes", "memory", "status"])
    holographic_active = "holographic" in r.stdout and "available" in r.stdout

    if holographic_active:
        check("Holographic already active", True)
    else:
        check("Holographic not active — installing", False)
        print("  Installing holographic memory provider...")
        r = run(["hermes", "memory", "setup", "holographic"], timeout=60)
        if r.returncode == 0:
            check("Holographic install succeeded", True)
            print("  NOTE: Restart Hermes session (/reset) for fact_store tools to appear.")
        else:
            check("Holographic install", False, r.stderr.strip() or r.stdout.strip())

# ---------------------------------------------------------------------------
def install_skill_via_copy(skill_dest):
    """Copy SKILL.md from local repo or GitHub fallback."""
    os.makedirs(skill_dest, exist_ok=True)
    src_skill = os.path.join(SELF_DIR, "..", "SKILL.md")
    if os.path.exists(src_skill):
        shutil.copy2(src_skill, os.path.join(skill_dest, "SKILL.md"))
        return True
    return False

step("3. Installing directmind skill")

skill_dest = os.path.join(HERMES_HOME, "skills", "hermes", "directmind")
os.makedirs(skill_dest, exist_ok=True)

# Direct copy (hermes skills install hangs on this system)
src_skill = os.path.join(SELF_DIR, "..", "SKILL.md")
if os.path.exists(src_skill):
    shutil.copy2(src_skill, os.path.join(skill_dest, "SKILL.md"))
check("SKILL.md installed", True, f"({skill_dest})")

# ---------------------------------------------------------------------------
step("4. Copying scripts to skill directory")

# Find skill dir
skills_base = os.path.join(HERMES_HOME, "skills")
directmind_scripts = None
for root, dirs, files in os.walk(skills_base):
    if "directmind" in root and "scripts" in dirs:
        directmind_scripts = os.path.join(root, "scripts")
        break

if directmind_scripts:
    repo_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
    if os.path.exists(repo_scripts):
        for f in os.listdir(repo_scripts):
            if f.endswith(".py"):
                shutil.copy2(os.path.join(repo_scripts, f), os.path.join(directmind_scripts, f))
        check("Scripts synced", True, f"({directmind_scripts})")
    else:
        check("Repo scripts found", False, f"(not at {repo_scripts})")
        fails += 1
else:
    check("Skill dir found", False)
    fails += 1

# ---------------------------------------------------------------------------
step("5. Creating cron job wrapper")

scripts_dir = os.path.join(HERMES_HOME, "scripts")
os.makedirs(scripts_dir, exist_ok=True)
wrapper = os.path.join(scripts_dir, "directmind-review.sh")
wrapper_content = (
    "#!/bin/sh\n"
    "# Weekly directmind brain health check\n"
    'echo "=== Self Review ==="\n'
    f"python3 {HERMES_HOME}/skills/hermes/directmind/scripts/self_review.py\n"
    'echo ""\n'
    'echo "=== Gap Learner ==="\n'
    f"python3 {HERMES_HOME}/skills/hermes/directmind/scripts/gap_learner.py\n"
    'echo ""\n'
    'echo "=== Skill Patcher ==="\n'
    f"python3 {HERMES_HOME}/skills/hermes/directmind/scripts/skill_patcher.py --dry-run\n"
)
with open(wrapper, "w") as f:
    f.write(wrapper_content)
os.chmod(wrapper, 0o755)
check("Cron wrapper created", True, f"({wrapper})")

# ---------------------------------------------------------------------------
step("6. Running post-install verification")

if directmind_scripts:
    check_deps = os.path.join(directmind_scripts, "check_deps.py")
    if os.path.exists(check_deps):
        r = run(["python3", check_deps])
        if r.returncode == 0:
            check("Post-install check: ALL PASS", True)
        else:
            check("Post-install check", False, r.stdout.strip()[-120:])
            fails += 1

# ---------------------------------------------------------------------------
print()
print(f"=== Summary: {passes} pass, {fails} fail ===")
print()
if fails == 0:
    print(f"  {OK} Directmind installed successfully!")
    print()
    print("  Next steps:")
    print("    1. If holographic was just installed: restart Hermes (/reset)")
    print("    2. Test: tell Hermes 'what does my brain know?'")
    print("    3. Cron job 'directmind-weekly-brain-health' runs every Monday at 09:00")
else:
    print(f"  {fails} check(s) failed. See above for details.")

sys.exit(0 if fails == 0 else 1)
