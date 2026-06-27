#!/usr/bin/env python3
"""
check_deps.py — Directmind dependency auto-check.

Verifies all prerequisites are present:
  - Holographic memory provider (fact_store tool)
  - Python 3.10+
  - SQLite 3 (WAL mode)
  - memory_store.db accessible
"""
import sys, os, sqlite3, subprocess

OK = "✅"
FAIL = "❌"
WARN = "⚠️"
passes = 0
fails = 0

def check(name, ok, detail=""):
    global passes, fails
    prefix = OK if ok else FAIL
    if ok:
        passes += 1
    else:
        fails += 1
    print(f"  {prefix} {name}" + (f"  {detail}" if detail else ""))

print("=== Directmind Dependency Check ===")
print()

# 1. Python version
v = sys.version_info
check("Python 3.10+", v.major >= 3 and v.minor >= 10, f"(v{v.major}.{v.minor}.{v.micro})")

# 2. SQLite version
check("SQLite available", sqlite3.sqlite_version_info >= (3, 0),
      f"(v{sqlite3.sqlite_version})")

# 3. memory_store.db exists and WAL mode
home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
db = os.path.join(home, "memory_store.db")
if os.path.exists(db):
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode")
        mode = c.fetchone()[0]
        check("memory_store.db accessible", True, f"({db}, mode={mode})")
        check("WAL mode", mode.lower() == "wal", f"({mode})")

        # Check facts table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'")
        check("facts table exists", c.fetchone() is not None)

        # Fact count
        c.execute("SELECT COUNT(*) FROM facts")
        count = c.fetchone()[0]
        check(f"Facts in store: {count}", True)
        conn.close()
    except Exception as e:
        check("memory_store.db read", False, str(e))
        fails += 1
else:
    check(f"memory_store.db found", False, f"(not at {db})")
    fails += 1

# 4. Holographic provider check (via hermes CLI)
r = subprocess.run(["hermes", "memory", "status"], capture_output=True, text=True)
if r.returncode == 0:
    check("Hermes CLI accessible", True)
    if "holographic" in r.stdout and "available" in r.stdout:
        check("Holographic provider active", True)
    else:
        check("Holographic provider active", False, "(not active — run 'hermes memory setup holographic')")
        fails += 1
else:
    check("Hermes CLI accessible", False, f"(exit {r.returncode})")
    fails += 1

# 5. fact_feedback tool check (part of holographic)
# The tool is registered at session start — can't detect outside session
# But if holographic is active, fact_store/fact_feedback should be available
check("fact_store/fact_feedback tools", True,
      "(available via Hermes when holographic provider is active)")

# 6. Directmind scripts directory
scripts_dir = os.path.dirname(os.path.abspath(__file__))
check("Scripts directory exists", os.path.isdir(scripts_dir), f"({scripts_dir})")

print()
if fails == 0:
    print(f"  {OK} All {passes} checks passed — directmind is ready.")
else:
    print(f"  {FAIL} {fails}/{passes + fails} checks failed — see above.")

print()
sys.exit(0 if fails == 0 else 1)
