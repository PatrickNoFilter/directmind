#!/usr/bin/env python3
"""
gap_learner.py — Directmind Layer 3: Proactive Gap Detection.

Scans recent conversation sessions for entities and topics the user asked about
but that have NO corresponding facts in the brain. Reports knowledge gaps
so they can be proactively filled.

Usage:
  python3 scripts/gap_learner.py                    # Last 7 days
  python3 scripts/gap_learner.py --days 30          # Custom range
  python3 scripts/gap_learner.py --verbose          # Full detail
"""

import sqlite3, os, re, sys
from datetime import datetime, timezone, timedelta
from collections import Counter

MEMORY_DB = os.path.expanduser("~/.hermes/memory_store.db")
STATE_DB = os.path.expanduser("~/.hermes/state.db")

STOP_WORDS = {
    "the","this","that","what","how","why","when","where",
    "which","then","than","also","just","like","here","there",
    "now","but","and","not","are","was","can","get","see",
    "use","say","one","you","your","will","has","had","did",
    "does","been","some","any","all","each","few","more",
    "most","other","such","only","own","same","too","very",
    "please","let","may","could","would","should","might",
    "shall","need","take","make","want","know","think",
    "help","show","tell","give","find","keep","put","set",
    "new","old","big","small","long","short","high","low",
    "good","bad","able","back","well","still","even","much",
    "always","never","ever","away","off","done",
    "already","around","away","back","because","before",
    "between","both","each","enough","every","finally",
    "first","following","further","however","indeed",
    "instead","last","least","less","maybe","next",
    "non","nor","nothing","often","once","otherwise",
    "overall","perhaps","quite","rather","really","regarding",
    "several","since","so","still","such",
    "through","throughout","together","toward","under",
    "unless","until","upon","usually","versus",
    "within","without",
    "dan","di","ke","dari","pada","dengan","untuk","dalam",
    "oleh","sebagai","secara","telah","sudah","akan","sedang",
    "saya","kami","kita","anda","dia","mereka","ini","itu",
    "disini","disana","sini","sana","adalah","bisa","dapat",
    "perlu","harus","mau","ingin","belum","tidak",
    "ya","lagi","masih",
    "kalau","jika","ketika","setelah","sebelum","karena",
    "tapi","namun","tetapi","sedangkan","sementara","atau",
    "seperti","antara","tentang","tanpa","sampai","hingga",
    "mulai","buat","simpan","lihat","buka","tutup","jalan",
    "coba","test","cek","periksa","verifikasi","tambah",
    "kurang","ubah","hapus","ganti","pilih","cari","tulis",
    "baca","kirim","terima","proses","selesai","lanjut",
    "henti","stop","break","continue",
    "lengkap","kosong","penuh","besar","kecil","cepat",
    "lambat","baru","lama","baik","buruk","benar","salah",
    "sama","beda","semua","setiap","beberapa","banyak",
    "sedikit","satu","dua","lain","lainnya","kembali",
    "ulang","langsung","manual","otomatis","tolong",
    "minta","kasih","info","hasil","progres","status",
    "done","ok","oke","yes","no","y","n",
}


class GapLearner:
    def __init__(self, days=7, verbose=False):
        self.days = days
        self.verbose = verbose
        self.cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        self.sessions = []
        self.user_queries = []
        self.extracted_entities = Counter()
        self.fact_entities = set()
        self.gaps = []
        self.gap_candidates = []
        self.orphan_facts = []

    def load_sessions(self):
        """Load recent sessions from state.db."""
        if not os.path.exists(STATE_DB):
            return False
        conn = sqlite3.connect(STATE_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        cutoff_ts = self.cutoff.timestamp()
        c.execute("""
            SELECT s.id, s.title, s.started_at, s.message_count,
                   COUNT(m.id) as msg_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id AND m.role = 'user'
            WHERE s.started_at >= ?
            GROUP BY s.id
            ORDER BY s.started_at DESC
        """, (cutoff_ts,))
        for row in c.fetchall():
            self.sessions.append(dict(row))
        conn.close()
        return len(self.sessions) > 0

    def load_user_queries(self):
        """Extract user messages from recent sessions."""
        if not self.sessions:
            return
        conn = sqlite3.connect(STATE_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        session_ids = [s["id"] for s in self.sessions]
        placeholders = ",".join("?" * len(session_ids))
        c.execute(f"""
            SELECT m.session_id, m.content, m.timestamp
            FROM messages m
            WHERE m.session_id IN ({placeholders})
              AND m.role = 'user'
              AND m.content IS NOT NULL
            ORDER BY m.timestamp DESC
            LIMIT 500
        """, session_ids)
        for row in c.fetchall():
            self.user_queries.append(dict(row))
        conn.close()

    def extract_entities_from_text(self, text):
        """Extract potential entities from user text."""
        entities = set()

        # Pattern 1: Multi-word Capitalized phrases (most reliable)
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        for c in caps:
            words = c.lower().split()
            if any(w not in STOP_WORDS for w in words):
                entities.add(c)

        # Pattern 2: UPPERCASE acronyms (3+ letters)
        acro = re.findall(r'\b[A-Z]{3,}\b', text)
        entities.update(acro)

        # Pattern 3: Quoted phrases
        quoted = re.findall(r'"([^"]{3,})"', text)
        entities.update(q.strip() for q in quoted if q.strip())

        # Pattern 4: Single capitalized words (filtered)
        single = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        for s in single:
            if s.lower() not in STOP_WORDS:
                entities.add(s)

        return entities

    def extract_entities_from_query(self):
        """Extract entities from user queries."""
        for q in self.user_queries:
            content = q.get("content") or ""
            entities = self.extract_entities_from_text(content)
            self.extracted_entities.update(entities)

    def load_fact_entities(self):
        """Load all entity names from fact_store."""
        if not os.path.exists(MEMORY_DB):
            return False
        conn = sqlite3.connect(MEMORY_DB)
        c = conn.cursor()
        c.execute("SELECT name FROM entities")
        for row in c.fetchall():
            self.fact_entities.add(row[0].lower())
        c.execute("""
            SELECT f.fact_id, f.content
            FROM facts f
            WHERE f.fact_id NOT IN (SELECT fact_id FROM fact_entities)
            LIMIT 50
        """)
        self.orphan_facts = c.fetchall()
        conn.close()
        return len(self.fact_entities) > 0

    def find_gaps(self):
        """Compare extracted entities vs fact_store entities — find gaps."""
        self.gap_candidates = []
        seen_upper = {e.lower(): e for e in self.extracted_entities}

        for norm, orig in sorted(seen_upper.items(), key=lambda x: -self.extracted_entities[x[1]]):
            if norm not in self.fact_entities:
                freq = self.extracted_entities[orig]
                if freq >= 2 or self.verbose:
                    self.gap_candidates.append({
                        "entity": orig,
                        "frequency": freq,
                    })

        self.gap_candidates.sort(key=lambda x: -x["frequency"])
        self.gaps = self.gap_candidates[:20]

    def _get_recent_queries_about(self, entity):
        """Find recent user queries mentioning this entity."""
        matching = []
        for q in self.user_queries[:30]:
            content = q.get("content") or ""
            if entity.lower() in content.lower():
                matching.append(content[:120])
        return matching[:3]

    def report(self):
        """Print the gap analysis report."""
        sep = "=" * 48
        print(f"{sep}")
        print(f"🔍  Directmind Gap Learner")
        print(f"📅  {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"📊  Scanning last {self.days} days")
        print(f"{sep}\n")

        # Summary
        print(f"📈 Summary")
        print(f"{'─' * 40}")
        print(f"  Sessions scanned:    {len(self.sessions)}")
        print(f"  User messages:       {len(self.user_queries)}")
        print(f"  Entities extracted:  {len(self.extracted_entities)}")
        print(f"  Fact-store entities: {len(self.fact_entities)}")
        print(f"  Knowledge gaps:      {len(self.gaps)}\n")

        # Knowledge gaps
        if self.gaps:
            print(f"🔴 Knowledge Gaps (top {len(self.gaps)})")
            print(f"{'─' * 40}")
            for g in self.gaps:
                bar = "█" * min(g["frequency"], 15)
                recent = self._get_recent_queries_about(g["entity"])
                print(f"  {g['entity']:<20}  freq={g['frequency']:>2}  {bar}")
                if recent and self.verbose:
                    for q in recent:
                        print(f"    └─ \"{q}...\"")
            print()
        else:
            print(f"✅ No knowledge gaps found!\n")

        # Well-known entities
        known = [(e, self.extracted_entities[e])
                 for e in self.extracted_entities
                 if e.lower() in self.fact_entities]
        known.sort(key=lambda x: -x[1])
        if known:
            print(f"✅ Well-Known Entities (already in brain)")
            print(f"{'─' * 40}")
            for e, count in known[:10]:
                print(f"  {e:<20}  freq={count}")
            print()

        # Orphan facts
        if self.orphan_facts:
            print(f"👻 Orphan Facts (no entity links)")
            print(f"{'─' * 40}")
            for fid, content in self.orphan_facts[:5]:
                print(f"  [{fid}] {content[:80]}")
            print()

        # Machine-readable summary
        total = len(self.extracted_entities)
        known_count = len([e for e in self.extracted_entities if e.lower() in self.fact_entities])
        coverage = round(known_count / total * 100, 1) if total > 0 else 100
        print(f"GAP_SUMMARY: {len(self.sessions)} sessions | {total} entities | "
              f"{known_count} known | {len(self.gaps)} gaps | coverage={coverage}%")


def main():
    days = 7
    verbose = False
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
        elif arg == "--verbose":
            verbose = True

    learner = GapLearner(days=days, verbose=verbose)

    print(f"🔍 Loading sessions...", file=sys.stderr)
    if not learner.load_sessions():
        print("❌ No sessions found.", file=sys.stderr)
        sys.exit(1)
    print(f"📖 {len(learner.sessions)} sessions", file=sys.stderr)
    learner.load_user_queries()
    print(f"💬 {len(learner.user_queries)} user messages", file=sys.stderr)
    learner.extract_entities_from_query()
    print(f"🏷  {len(learner.extracted_entities)} entities extracted", file=sys.stderr)
    learner.load_fact_entities()
    print(f"🧠 {len(learner.fact_entities)} brain entities", file=sys.stderr)
    learner.find_gaps()
    print(file=sys.stderr)
    learner.report()


if __name__ == "__main__":
    main()
