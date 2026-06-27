#!/usr/bin/env python3
"""
skill_patcher.py — Directmind Layer 4: Meta-Learning Skill Updater.

Detects when the directmind skill is outdated compared to GitHub,
reports drift between local git repo and active skill directory,
and can auto-patch when safe.

Usage:
  python3 scripts/skill_patcher.py                     # Check only (default)
  python3 scripts/skill_patcher.py --apply              # Auto-update skill from git repo
  python3 scripts/skill_patcher.py --force-from-github  # Fetch from GitHub instead of local git
  python3 scripts/skill_patcher.py --restore            # Restore skill from git repo backup
"""

import os, sys, re, json, urllib.request, hashlib
from datetime import datetime

SKILL_DIR = os.path.expanduser("~/.hermes/skills/hermes/directmind")
REPO_DIR = "/root/directmind"
GITHUB_RAW = "https://raw.githubusercontent.com/PatrickNoFilter/directmind/main"

CRITICAL_FILES = [
    "SKILL.md",
    "scripts/directmind.py",
    "scripts/self_review.py",
    "scripts/gap_learner.py",
]

BACKUP_DIR = os.path.expanduser("~/.hermes/skills/hermes/directmind/.backup")


def sha256_file(path):
    """Get SHA256 of a file (or empty string if not exists)."""
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:12]


def fetch_github_file(path):
    """Fetch a file from GitHub raw, return content or None."""
    url = f"{GITHUB_RAW}/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "directmind-skill-patcher"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return None


def get_local_version(path):
    """Extract version from YAML frontmatter of a SKILL.md file."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        content = f.read()
    m = re.search(r'^version:\s*([\w.]+)', content, re.MULTILINE)
    return m.group(1) if m else "unknown"


def check_drift():
    """Compare git repo files vs active skill directory files."""
    drift_items = []
    for rel in CRITICAL_FILES:
        repo_file = os.path.join(REPO_DIR, rel)
        skill_file = os.path.join(SKILL_DIR, rel)

        repo_hash = sha256_file(repo_file)
        skill_hash = sha256_file(skill_file)
        if repo_hash is None and skill_hash is None:
            continue

        if repo_hash != skill_hash:
            drift_items.append({
                "file": rel,
                "repo_hash": repo_hash,
                "skill_hash": skill_hash,
                "repo_exists": repo_hash is not None,
                "skill_exists": skill_hash is not None,
            })
    return drift_items


def check_github_version():
    """Check if GitHub has a newer version than local."""
    local_ver = get_local_version(os.path.join(SKILL_DIR, "SKILL.md"))
    gh_content = fetch_github_file("SKILL.md")

    if gh_content is None:
        return {"status": "unreachable", "local": local_ver}

    m = re.search(r'^version:\s*([\w.]+)', gh_content, re.MULTILINE)
    gh_ver = m.group(1) if m else "unknown"

    if local_ver is None:
        return {"status": "no_local", "github": gh_ver}

    if gh_ver == "unknown":
        return {"status": "no_github_version", "local": local_ver}

    # Simple version compare (tuple)
    def parse_ver(v):
        try:
            parts = v.replace("v", "").split(".")
            return tuple(int(x) for x in parts[:3])
        except:
            return (0, 0, 0)

    local_t = parse_ver(local_ver)
    gh_t = parse_ver(gh_ver)

    if gh_t > local_t:
        return {"status": "outdated", "local": local_ver, "github": gh_ver}
    elif gh_t < local_t:
        return {"status": "ahead", "local": local_ver, "github": gh_ver}
    else:
        return {"status": "synced", "version": local_ver}


def apply_update(dry_run=False, source="repo"):
    """Sync files from source (repo or github) to skill directory."""
    if source == "github":
        return apply_from_github(dry_run)
    return apply_from_repo(dry_run)


def apply_from_repo(dry_run=False):
    """Copy files from local git repo to skill directory."""
    results = []
    for rel in CRITICAL_FILES:
        repo_file = os.path.join(REPO_DIR, rel)
        skill_file = os.path.join(SKILL_DIR, rel)

        if not os.path.exists(repo_file):
            results.append({"file": rel, "action": "source_missing", "status": "⏭"})
            continue

        if dry_run:
            repo_hash = sha256_file(repo_file)
            skill_hash = sha256_file(skill_file)
            if repo_hash != skill_hash:
                results.append({"file": rel, "action": "needs_update", "status": "🔄"})
            else:
                results.append({"file": rel, "action": "up_to_date", "status": "✅"})
            continue

        # Backup existing skill file
        if os.path.exists(skill_file):
            backup_dir = os.path.join(SKILL_DIR, ".backup")
            os.makedirs(backup_dir, exist_ok=True)
            import shutil
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"{rel.replace('/', '_')}.{ts}.bak")
            shutil.copy2(skill_file, backup_path)

        # Copy from repo to skill
        import shutil
        os.makedirs(os.path.dirname(skill_file), exist_ok=True)
        shutil.copy2(repo_file, skill_file)
        results.append({"file": rel, "action": "updated", "status": "✅"})

    return results


def main():
    args = set(sys.argv[1:])
    apply_mode = "--apply" in args
    dry_run = "--dry-run" in args
    from_github = "--force-from-github" in args
    restore = "--restore" in args

    sep = "=" * 48
    print(f"{sep}")
    print(f"🛠️  Directmind Skill Patcher")
    print(f"📅  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{sep}\n")

    # 1. Check GitHub version
    print(f"📡 GitHub version check...")
    gh = check_github_version()
    if gh["status"] == "unreachable":
        print(f"   ⚠️  GitHub unreachable (no internet) — local check only\n")
    elif gh["status"] == "synced":
        print(f"   ✅ Local v{gh['version']} matches GitHub\n")
    elif gh["status"] == "outdated":
        print(f"   ⚠️  Local v{gh['local']} → GitHub v{gh['github']} (outdated!)\n")
    elif gh["status"] == "ahead":
        print(f"   🚀 Local v{gh['local']} ahead of GitHub v{gh['github']}\n")
    else:
        print(f"   ⚠️  Could not determine version status\n")

    # 2. Check drift between git repo and active skill
    print(f"🔍 Checking drift (git repo vs active skill)...")
    drift = check_drift()
    if not drift:
        print(f"   ✅ Skill is in sync with git repo\n")
    else:
        print(f"   ⚠️  {len(drift)} file(s) drifted:\n")
        for d in drift:
            file_status = []
            if not d["repo_exists"]:
                file_status.append("missing in repo")
            if not d["skill_exists"]:
                file_status.append("missing in skill dir")
            if d["repo_exists"] and d["skill_exists"]:
                file_status.append("content differs")
            print(f"   {d['file']}")
            print(f"     repo hash: {d['repo_hash']}")
            print(f"     skill hash: {d['skill_hash']}")
            print(f"     status: {', '.join(file_status)}")
        print()

    # 3. Apply update if requested
    if apply_mode:
        if dry_run:
            print(f"📋 Dry-run update preview:\n")
            results = apply_update(dry_run=True, source="github" if from_github else "repo")
            for r in results:
                print(f"   {r['status']} {r['file']} — {r['action']}")
        else:
            print(f"📦 Applying update from {'GitHub' if from_github else 'local repo'}...")
            results = apply_update(dry_run=False, source="github" if from_github else "repo")
            for r in results:
                print(f"   {r['status']} {r['file']} — {r['action']}")
            print()

            # Verify
            drift2 = check_drift()
            if not drift2:
                print(f"✅ Update complete — skill synced with repo")
            else:
                print(f"⚠️  {len(drift2)} file(s) still drifted after update")
                for d in drift2:
                    print(f"   ✗ {d['file']}")

    elif drift:
        print(f"💡 Run with --apply to sync skill from local git repo")
        print(f"   Or --apply --force-from-github to fetch from GitHub")
        print()

    # 4. Restore from backup
    if restore:
        backup_path = os.path.join(BACKUP_DIR)
        if os.path.exists(backup_path):
            backups = sorted(os.listdir(backup_path))
            if backups:
                print(f"📂 Available backups ({len(backups)}):")
                for b in backups[-5:]:
                    print(f"   {b}")
                print(f"   Manual restore: cp {backup_path}/<file> <skill_dir>/")
            else:
                print(f"   No backups found")
        else:
            print(f"   No backup directory found")

    # 5. Summary line
    drift_count = len(drift) if drift else 0
    if gh["status"] == "unreachable":
        gh_status = "offline"
    elif gh["status"] == "synced":
        gh_status = "synced"
    elif gh["status"] == "outdated":
        gh_status = f"behind ({gh['local']}→{gh['github']})"
    elif gh["status"] == "ahead":
        gh_status = f"ahead ({gh['local']}>local)"
    else:
        gh_status = gh.get("status", "unknown")

    print(f"PATCH_SUMMARY: github={gh_status} | drift={drift_count} | apply={'yes' if apply_mode else 'no'}")


if __name__ == "__main__":
    main()
