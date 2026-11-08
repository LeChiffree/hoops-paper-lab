"""
Basketball 1X2 odds backtest scraper (Flashscore public data).

Phase 1: league/season results -> SQLite
Phase 2: per-match closing odds (1X2 full time + moneyline incl. OT) -> SQLite

Usage:
    python scraper.py phase1
    python scraper.py phase2 --workers 16 [--league "EuroLeague"]
    python scraper.py status
"""
import argparse
import json
import os
import sqlite3
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

LIB = r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper"
sys.path.insert(0, LIB)

from flashscore import tournaments, refs, matches as M     # noqa: E402
from flashscore.fetch import get_graphql_optional             # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data.sqlite3")

CATALOG = [
    ("NBA", ["/basketball/usa/nba/"]),
    ("EuroLeague", ["/basketball/europe/euroleague/"]),
    ("NCAA Division I", ["/basketball/usa/ncaa/"]),
    ("Liga ACB", ["/basketball/spain/acb/"]),
    ("Lega A", ["/basketball/italy/lega-a/"]),
    ("Turkiye Super Lig", ["/basketball/turkey/super-lig/"]),
    ("LNB Pro A", ["/basketball/france/lnb/"]),
    ("BBL", ["/basketball/germany/bbl/"]),
    ("VTB United League", ["/basketball/russia/vtb-united-league/"]),
    ("Basket League", ["/basketball/greece/basket-league/"]),
    ("ABA League", ["/basketball/europe/admiralbet-aba-league/"]),
    ("Super League", ["/basketball/israel/super-league/"]),
    ("NBL Australia", ["/basketball/australia/nbl/"]),
    ("CBA", ["/basketball/china/cba/"]),
    ("B.League Premier", ["/basketball/japan/b-league-premier/"]),
    ("KBL", ["/basketball/south-korea/kbl/"]),
    ("PBA", ["/basketball/philippines/pba-commissioner-s-cup/",
             "/basketball/philippines/pba-governors-cup/",
             "/basketball/philippines/pba-philippine-cup/"]),
    ("LNBP", ["/basketball/mexico/lnbp/"]),
    ("NBB", ["/basketball/brazil/nbb/"]),
    ("Liga A Argentina", ["/basketball/argentina/liga-a/"]),
    ("G League", ["/basketball/usa/nba-g-league/"]),
    ("WNBA", ["/basketball/usa/wnba/"]),
    ("EuroCup", ["/basketball/europe/eurocup/"]),
    ("Champions League", ["/basketball/europe/champions-league/"]),
    ("LKL", ["/basketball/lithuania/lkl/"]),
    ("Basket Liga", ["/basketball/poland/basket-liga/"]),
    ("NBL Czech", ["/basketball/czech-republic/nbl/"]),
    ("BNXT League", ["/basketball/europe/bnxt-league/"]),
    ("Basketligan", ["/basketball/sweden/basketligan/"]),
    ("Korisliiga", ["/basketball/finland/korisliiga/"]),
    ("Basketligaen", ["/basketball/denmark/basketligaen/"]),
    ("Premier League Iceland", ["/basketball/iceland/premier-league/"]),
    ("LPB", ["/basketball/portugal/lpb/"]),
    ("SB League", ["/basketball/switzerland/sb-league/"]),
    ("FIBA Europe Cup", ["/basketball/europe/fiba-europe-cup/"]),
]

SEASON_START_MIN, SEASON_START_MAX = 2016, 2025
ODDS_YEAR_MIN = 2015  # coverage starts 2016/17 but keep margin


# ---------------------------------------------------------------- database
def connect():
    con = sqlite3.connect(DB, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS matches(
            id TEXT PRIMARY KEY,
            league TEXT NOT NULL,
            season TEXT,
            season_start INTEGER,
            date TEXT,
            start_time TEXT,
            status TEXT,
            round TEXT,
            home_id TEXT, home TEXT,
            away_id TEXT, away TEXT,
            home_pid TEXT, away_pid TEXT,
            home_score INTEGER, away_score INTEGER,
            o1 REAL, ox REAL, o2 REAL,
            o1_open REAL, o2_open REAL,
            ml1 REAL, ml2 REAL,
            n_books INTEGER,
            odds_geo TEXT,
            odds_status TEXT,
            periods_json TEXT,
            reg_home INTEGER,
            reg_away INTEGER,
            went_ot INTEGER DEFAULT 0,
            odds_done INTEGER DEFAULT 0
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_m_league ON matches(league, season_start)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_m_done ON matches(odds_done)")
    # lightweight migration for existing databases
    have = {r[1] for r in con.execute("PRAGMA table_info(matches)")}
    for col, ddl in [("periods_json", "TEXT"), ("reg_home", "INTEGER"), ("reg_away", "INTEGER"),
                     ("went_ot", "INTEGER DEFAULT 0"), ("home_pid", "TEXT"), ("away_pid", "TEXT")]:
        if col not in have:
            con.execute(f"ALTER TABLE matches ADD COLUMN {col} {ddl}")
    con.commit()
    return con


# ---------------------------------------------------------------- phase 1
def season_links(league, paths):
    """[(season_name, start_year, link)] for the target window."""
    out = []
    for path in paths:
        try:
            seasons = tournaments.get_seasons({"path": path})["seasons"]
        except Exception as e:
            print(f"  ! seasons {league} {path}: {type(e).__name__}: {e}", flush=True)
            continue
        for s in seasons:
            name = (s.get("name") or "").strip()
            if len(name) < 4 or not name[:4].isdigit():
                continue
            year = int(name[:4])
            if not (SEASON_START_MIN <= year <= SEASON_START_MAX):
                continue
            link = f"https://www.flashscore.com{path}-{name.replace('/', '-')}/"
            out.append((name, year, link))
    # dedupe (PBA conferences share season names)
    seen = set()
    uniq = []
    for name, year, link in out:
        key = (name, link)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((name, year, link))
    return uniq


def regulation_score(m):
    """(reg_home, reg_away, went_ot). Basketball 1X2 settles on regulation time.
    Flashscore lists overtime as extra periods (Quarter 5, Quarter 6...)."""
    periods = [p for p in (m.get("periods") or []) if p.get("home") is not None and p.get("away") is not None]
    if len(periods) < 4:
        return m.get("home_score"), m.get("away_score"), 0
    reg = periods[:4]
    ot = 1 if len(periods) > 4 else 0
    return sum(p["home"] for p in reg), sum(p["away"] for p in reg), ot


def upsert_matches(con, league, season, year, matches):
    rows = []
    for m in matches:
        if not m.get("id"):
            continue
        home = (m.get("home") or {}).get("name")
        away = (m.get("away") or {}).get("name")
        reg_h, reg_a, ot = regulation_score(m)
        rows.append((
            m["id"], league, season, year, m.get("date"), m.get("start_time"),
            m.get("status"), m.get("round"),
            (m.get("home") or {}).get("id"), home,
            (m.get("away") or {}).get("id"), away,
            m.get("home_pid"), m.get("away_pid"),
            m.get("home_score"), m.get("away_score"),
            json.dumps(m.get("periods") or [], ensure_ascii=False), reg_h, reg_a, ot,
        ))
    if not rows:
        return 0
    con.executemany("""
        INSERT INTO matches(id, league, season, season_start, date, start_time, status, round,
                            home_id, home, away_id, away, home_pid, away_pid,
                            home_score, away_score, periods_json, reg_home, reg_away, went_ot)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            league=excluded.league, season=excluded.season, season_start=excluded.season_start,
            date=excluded.date, start_time=excluded.start_time, status=excluded.status,
            round=excluded.round, home=excluded.home, away=excluded.away,
            home_pid=excluded.home_pid, away_pid=excluded.away_pid,
            home_score=excluded.home_score, away_score=excluded.away_score,
            periods_json=excluded.periods_json, reg_home=excluded.reg_home,
            reg_away=excluded.reg_away, went_ot=excluded.went_ot
    """, rows)
    return len(rows)


def phase1(only_league=None):
    con = connect()
    t0 = time.time()
    for league, paths in CATALOG:
        if only_league and league != only_league:
            continue
        links = season_links(league, paths)
        n_inserted = 0
        for season, year, link in links:
            try:
                ctx = refs.resolve_tournament(link)
                first = tournaments.get_results(ctx)
                pages = (first.get("pagination") or {}).get("total_pages") or 1
                n_inserted += upsert_matches(con, league, season, year, first.get("matches") or [])
                for page in range(2, pages + 1):
                    try:
                        r = tournaments.get_results(ctx, page=page)
                        n_inserted += upsert_matches(con, league, season, year, r.get("matches") or [])
                    except Exception as e:
                        print(f"    ! page {page} {league} {season}: {type(e).__name__}: {e}", flush=True)
                        time.sleep(1)
                con.commit()
            except Exception as e:
                print(f"  ! {league} {season}: {type(e).__name__}: {e}", flush=True)
                time.sleep(1)
        total = con.execute("SELECT COUNT(*) FROM matches WHERE league=?", (league,)).fetchone()[0]
        print(f"{league:28s} seasons={len(links):2d} inserted={n_inserted:6d} total_in_db={total:6d} "
              f"[{time.time()-t0:.0f}s]", flush=True)
    con.close()


# ---------------------------------------------------------------- phase 2
def sf(v):
    try:
        x = float(v)
        return x if x > 1.0 else None
    except (TypeError, ValueError):
        return None


def median(vals):
    vals = [v for v in vals if v]
    return round(statistics.median(vals), 3) if vals else None


def parse_odds(payload, sides=None):
    """Return home/draw/away closing odds. `sides` maps event-participant id ->
    'home'/'away'; without it the array order (home, away, draw) is assumed."""
    h = (payload or {}).get("findOddsByEventId") or {}
    rows = h.get("odds") or []
    books = (h.get("settings") or {}).get("bookmakers") or []
    o1, ox, o2, o1o, o2o, ml1, ml2 = [], [], [], [], [], [], []
    for row in rows:
        bt = row.get("bettingType")
        sc = row.get("bettingScope")
        sel = row.get("odds") or []
        if bt == "HOME_DRAW_AWAY" and sc == "FULL_TIME" and len(sel) == 3:
            v = [sf(x.get("value")) for x in sel]
            if not all(v) or v[2] < 2.5:
                continue
            margin = (1 / v[0]) + (1 / v[1]) + (1 / v[2])
            if not (1.0 <= margin <= 1.40):
                continue
            home_v = away_v = draw_v = None
            if sides:
                for x, val in zip(sel, v):
                    pid = x.get("eventParticipantId")
                    side = "draw" if not pid else sides.get(pid)
                    if side == "home":
                        home_v = val
                    elif side == "away":
                        away_v = val
                    elif side == "draw":
                        draw_v = val
            if home_v is None or away_v is None:
                home_v, away_v, draw_v = v[0], v[1], v[2]
            o1.append(home_v); o2.append(away_v); ox.append(draw_v)
            # opening values follow the same participant mapping
            if sides:
                for x in sel:
                    pid = x.get("eventParticipantId")
                    side = "draw" if not pid else sides.get(pid)
                    if side == "home":
                        o1o.append(sf(x.get("opening")))
                    elif side == "away":
                        o2o.append(sf(x.get("opening")))
            else:
                o1o.append(sf(sel[0].get("opening"))); o2o.append(sf(sel[1].get("opening")))
        elif bt == "HOME_AWAY" and sc == "FULL_TIME_OVER_TIME" and len(sel) == 2:
            v = [sf(x.get("value")) for x in sel]
            if not all(v):
                continue
            if sides:
                pair = {}
                for x, val in zip(sel, v):
                    pair[sides.get(x.get("eventParticipantId"))] = val
                if pair.get("home") and pair.get("away"):
                    ml1.append(pair["home"]); ml2.append(pair["away"])
                else:
                    ml1.append(v[0]); ml2.append(v[1])
            else:
                ml1.append(v[0]); ml2.append(v[1])
    if not o1 and not ml1:
        return None
    return {
        "o1": median(o1), "ox": median(ox), "o2": median(o2),
        "o1_open": median(o1o), "o2_open": median(o2o),
        "ml1": median(ml1), "ml2": median(ml2),
        "n_books": len(books),
    }


def fetch_odds(mid, home_pid=None, away_pid=None):
    """Closing odds for one match. Participant sides come from the results feed
    (JA/JB); the detail endpoint is only a fallback."""
    if home_pid and away_pid:
        sides = {home_pid: "home", away_pid: "away"}
    else:
        try:
            sides = M._participant_sides(mid)
        except Exception:
            sides = {}
    for geo in ("DE", "GB"):
        try:
            payload = get_graphql_optional(
                "oce",
                {"eventId": mid, "projectId": 2, "geoIpCode": geo, "geoIpSubdivisionCode": ""},
                odds=True,
            )
        except Exception:
            payload = None
        if payload:
            got = parse_odds(payload, sides)
            if got and (got.get("o1") or got.get("ml1")):
                got["odds_geo"] = geo
                got["odds_status"] = "ok"
                return got
    return {"odds_geo": None, "odds_status": "none", "o1": None, "ox": None, "o2": None,
            "o1_open": None, "o2_open": None, "ml1": None, "ml2": None, "n_books": 0}


def phase2(workers=16, only_league=None, limit=None):
    con = connect()
    q = "SELECT id, home_pid, away_pid, league, season FROM matches WHERE odds_done=0 AND status='finished'"
    args = []
    if only_league:
        q += " AND league=?"
        args.append(only_league)
    q += " ORDER BY season_start DESC, date DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    todo = con.execute(q, args).fetchall()
    print(f"phase2: {len(todo)} matches to process, workers={workers}", flush=True)
    if not todo:
        con.close()
        return

    lock = threading.Lock()
    done = 0
    t0 = time.time()
    wrote = 0

    def work(row):
        return row[0], fetch_odds(row[0], row[1], row[2])

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        batch = []
        for fut in as_completed(futs):
            try:
                mid, od = fut.result()
            except Exception:
                done += 1
                continue
            batch.append((od.get("o1"), od.get("ox"), od.get("o2"),
                          od.get("o1_open"), od.get("o2_open"),
                          od.get("ml1"), od.get("ml2"),
                          od.get("n_books"), od.get("odds_geo"), od.get("odds_status"), mid))
            done += 1
            if len(batch) >= 200:
                con.executemany("""UPDATE matches SET o1=?, ox=?, o2=?, o1_open=?, o2_open=?,
                                   ml1=?, ml2=?, n_books=?, odds_geo=?, odds_status=?, odds_done=1
                                   WHERE id=?""", batch)
                con.commit(); wrote += len(batch); batch = []
                rate = done / max(time.time() - t0, 1)
                eta = (len(todo) - done) / max(rate, 0.01)
                print(f"  {done}/{len(todo)}  {rate:.1f}/s  eta {eta/60:.1f} min", flush=True)
        if batch:
            con.executemany("""UPDATE matches SET o1=?, ox=?, o2=?, o1_open=?, o2_open=?,
                               ml1=?, ml2=?, n_books=?, odds_geo=?, odds_status=?, odds_done=1
                               WHERE id=?""", batch)
            con.commit(); wrote += len(batch)
    print(f"phase2 done: {wrote} updated in {(time.time()-t0)/60:.1f} min", flush=True)
    con.close()


def reset_odds():
    con = connect()
    con.execute("""UPDATE matches SET o1=NULL, ox=NULL, o2=NULL, o1_open=NULL, o2_open=NULL,
                   ml1=NULL, ml2=NULL, n_books=NULL, odds_geo=NULL, odds_status=NULL,
                   odds_done=0""")
    con.commit()
    print("odds reset")
    con.close()


def status():
    con = connect()
    total = con.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    fin = con.execute("SELECT COUNT(*) FROM matches WHERE status='finished'").fetchone()[0]
    done = con.execute("SELECT COUNT(*) FROM matches WHERE odds_done=1").fetchone()[0]
    ok = con.execute("SELECT COUNT(*) FROM matches WHERE o1 IS NOT NULL").fetchone()[0]
    print(f"rows={total} finished={fin} odds_done={done} 1x2_ok={ok}")
    for r in con.execute("""SELECT league, COUNT(*) t, SUM(status='finished') f,
                                   SUM(odds_done=1) d, SUM(o1 IS NOT NULL) o
                            FROM matches GROUP BY league ORDER BY t DESC"""):
        print(f"  {r[0]:28s} total={r[1]:6d} finished={r[2]:6d} done={r[3]:6d} 1x2={r[4]:6d}")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["phase1", "phase2", "status", "reset"])
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--league", default=None)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.phase == "phase1":
        phase1(a.league)
    elif a.phase == "phase2":
        phase2(a.workers, a.league, a.limit)
    elif a.phase == "reset":
        reset_odds()
    else:
        status()
