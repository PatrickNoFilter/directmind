#!/usr/bin/env python3
"""
self_review.py — Directmind Layer 2: Cron Self-Review.

Reads the fact_store database directly and produces a brain health report.
Designed to run as a cron job (no_agent=True) or standalone.

Usage:
  python3 scripts/self_review.py
  python3 scripts/self_review.py --verbose
"""

import sqlite3
import os
import sys
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.hermes/memory_store.db")


def get_db():
    """Connect to fact_store database (read-only)."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_ts(ts_str):
    """Format timestamp string to readable."""
    if not ts_str:
        return "never"
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(ts_str)[:19]


def analyze_trust_distribution(facts):
    """Analyze trust score distribution."""
    total = len(facts)
    if total == 0:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "default_stuck": 0, "avg": 0.0}

    high = sum(1 for f in facts if f["trust_score"] >= 0.7)
    medium = sum(1 for f in facts if 0.3 <= f["trust_score"] < 0.7)
    low = sum(1 for f in facts if f["trust_score"] < 0.3)
    default = sum(1 for f in facts if f["trust_score"] == 0.5)
    avg = sum(f["trust_score"] for f in facts) / total if total else 0

    return {
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
        "default_stuck": default,
        "avg": round(avg, 2),
    }


def analyze_categories(facts):
    """Group facts by category."""
    cats = {}
    for f in facts:
        cat = f.get("category") or "uncategorized"
        if cat not in cats:
            cats[cat] = {"count": 0, "avg_trust": 0, "sum_trust": 0}
        cats[cat]["count"] += 1
        cats[cat]["sum_trust"] += f["trust_score"]
    for c in cats:
        cats[c]["avg_trust"] = round(cats[c]["sum_trust"] / cats[c]["count"], 2)
        del cats[c]["sum_trust"]
    return cats


def find_low_trust_facts(facts, threshold=0.3):
    """Find facts with trust below threshold."""
    return [f for f in facts if f["trust_score"] < threshold]


def find_contradictions(facts):
    """Heuristic: find facts about same entity with conflicting trust or content."""
    from collections import defaultdict

    by_entity = defaultdict(list)
    for f in facts:
        entity_list = f.get("entities") or ""
        for ent in entity_list.split("; "):
            ent = ent.strip()
            if ent:
                by_entity[ent].append(f)

    issues = []
    for entity, efacts in by_entity.items():
        if len(efacts) > 1:
            # Check for opposing trust (one high, one low about same thing)
            trusts = [f["trust_score"] for f in efacts]
            if max(trusts) - min(trusts) > 0.5:
                high = [f for f in efacts if f["trust_score"] >= 0.7]
                low = [f for f in efacts if f["trust_score"] < 0.3]
                if high and low:
                    issues.append({
                        "entity": entity,
                        "type": "trust_conflict",
                        "detail": f"{len(high)} high-trust vs {len(low)} low-trust facts",
                        "fact_ids": [f["fact_id"] for f in high + low],
                    })

            # Check for duplicate-ish content (same prefix)
            contents = [f.get("content", "")[:60] for f in efacts]
            seen = {}
            for i, c in enumerate(contents):
                if c in seen:
                    issues.append({
                        "entity": entity,
                        "type": "possible_duplicate",
                        "detail": f"Similar content: '{c}...'",
                        "fact_ids": [efacts[seen[c]]["fact_id"], efacts[i]["fact_id"]],
                    })
                seen[c] = i

    return issues


def find_stale_facts(facts, days=60):
    """Find facts not updated recently."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stale = []
    for f in facts:
        updated = f.get("updated_at") or f.get("created_at")
        if updated:
            try:
                dt = datetime.fromisoformat(updated)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    stale.append(f)
            except (ValueError, TypeError):
                pass
    return stale


def main():
    verbose = "--verbose" in sys.argv

    conn = get_db()
    cursor = conn.cursor()

    # Get all facts with entities
    cursor.execute("""
        SELECT f.fact_id, f.content, f.category, f.trust_score, f.tags,
               f.created_at, f.updated_at,
               GROUP_CONCAT(e.name, '; ') AS entities
        FROM facts f
        LEFT JOIN fact_entities fe ON f.fact_id = fe.fact_id
        LEFT JOIN entities e ON fe.entity_id = e.entity_id
        GROUP BY f.fact_id
        ORDER BY f.trust_score ASC
    """)
    facts = cursor.fetchall()
    facts = [dict(f) for f in facts]  # sqlite3.Row → dict for .get() support
    conn.close()

    # Analysis
    trust_dist = analyze_trust_distribution(facts)
    categories = analyze_categories(facts)
    low_trust = find_low_trust_facts(facts)
    contradictions = find_contradictions(facts)
    stale = find_stale_facts(facts)

    # === OUTPUT ===
    sep = "=" * 48
    print(f"{sep}")
    print(f"🧠  Directmind Self-Review")
    print(f"📅  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{sep}")
    print()

    # Trust summary
    print(f"📊 Trust Distribution ({trust_dist['total']} facts)")
    print(f"{'─' * 40}")
    print(f"  High (≥0.7):         {trust_dist['high']:>3}  → autoritatif")
    print(f"  Medium (0.3–0.7):    {trust_dist['medium']:>3}  → perlu verifikasi")
    print(f"  Low (<0.3):          {trust_dist['low']:>3}  → perlu perhatian ⚠️")
    print(f"  Stuck at 0.5:        {trust_dist['default_stuck']:>3}  → belum pernah di-feedback")
    print(f"  Average trust:       {trust_dist['avg']:.2f}")
    print()

    # Low-trust flags
    if low_trust:
        print(f"⚠️  Low-Trust Facts ({len(low_trust)})")
        print(f"{'─' * 40}")
        for f in low_trust:
            tags = f["tags"] or ""
            print(f"  [{f['fact_id']}] trust={f['trust_score']}  {f['content'][:100]}")
            if tags:
                print(f"       tags: {tags}")
        print()
    else:
        print(f"✅ No low-trust facts")
        print()

    # Category breakdown
    print(f"📁 Categories")
    print(f"{'─' * 40}")
    for cat, info in sorted(categories.items(), key=lambda x: -x[1]["count"]):
        bar = "█" * min(info["count"], 20)
        print(f"  {cat:<12} {info['count']:>3} facts  trust={info['avg_trust']:.2f}  {bar}")
    print()

    # Contradictions
    if contradictions:
        print(f"⚡ Contradictions / Duplicates ({len(contradictions)})")
        print(f"{'─' * 40}")
        for c in contradictions:
            print(f"  [{c['type']}] {c['entity']}: {c['detail']}")
            print(f"    fact IDs: {c['fact_ids']}")
        print()
    else:
        print(f"✅ No contradictions or duplicates detected")
        print()

    # Stale facts
    if stale:
        print(f"⏳ Stale Facts (>60 days untouched) ({len(stale)})")
        print(f"{'─' * 40}")
        for f in stale[:5]:
            updated = format_ts(f.get("updated_at") or f.get("created_at"))
            print(f"  [{f['fact_id']}] last={updated}  {f['content'][:80]}")
        if len(stale) > 5:
            print(f"  ... and {len(stale) - 5} more")
        print()
    else:
        print(f"✅ No stale facts")
        print()

    # Overall health score
    health_score = 100
    if trust_dist["low"] > 0:
        health_score -= trust_dist["low"] * 5
    if trust_dist["default_stuck"] > trust_dist["total"] * 0.5:
        health_score -= 15  # More than half never got feedback
    if len(contradictions) > 0:
        health_score -= len(contradictions) * 8
    if len(stale) > 0:
        health_score -= min(len(stale) * 2, 20)
    health_score = max(0, min(100, health_score))

    print(f"🏥  Brain Health Score: {health_score}/100")
    print(f"{sep}")

    # Recommendations
    print()
    print(f"💡 Recommendations")
    print(f"{'─' * 40}")
    recs = []
    if trust_dist["low"] > 0:
        recs.append(f"  • Review {trust_dist['low']} low-trust facts — verify or remove")
    if trust_dist["default_stuck"] > trust_dist["total"] * 0.5:
        recs.append(f"  • {trust_dist['default_stuck']} facts never got feedback — run think queries to trigger feedback loop")
    if contradictions:
        recs.append(f"  • Resolve {len(contradictions)} contradictions — consolidate conflicting facts")
    if stale:
        recs.append(f"  • {len(stale)} facts stale >60 days — verify and refresh")
    if trust_dist["avg"] < 0.5:
        recs.append(f"  • Average trust below 0.5 — brain needs more usage to mature")
    if trust_dist["avg"] >= 0.8:
        recs.append(f"  • Brain is mature (avg≥0.8) — consider pruning very old low-trust facts")

    if not recs:
        recs.append("  ✅ Brain is healthy — no recommendations")
    for r in recs:
        print(r)

    print()
    if verbose:
        print(f"📋 All Facts")
        print(f"{'─' * 40}")
        for f in facts:
            tags = f["tags"] or ""
            print(f"  [{f['fact_id']:>3}] t={f['trust_score']:.2f}  cat={str(f['category']):<10}  {f['content'][:120]}")
        print()

    # Machine-readable summary (last line for cron parsing)
    print(f"REVIEW_SUMMARY: {trust_dist['total']} facts | avg_trust={trust_dist['avg']} | low={trust_dist['low']} | contradictions={len(contradictions)} | stale={len(stale)} | health={health_score}")


if __name__ == "__main__":
    main()
