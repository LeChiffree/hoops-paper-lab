"""334 unresolved_ot maÃ§Ä±nÄ± Flashscore takÄ±m arÅŸivinden toplu Ã§Ã¶z."""
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

import pandas as pd

sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore import discovery, teams

BASE = r"D:\basketball_odds"
OUT = os.path.join(BASE, "flashscore_tie_fix.csv")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((w|women|woman)\)", " w ", s)
    s = re.sub(r"\b(women|woman)\b", " w ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def flatten(r):
    return [m for c in r.get("competitions") or [] for m in c.get("matches") or []]


def search_ids(name):
    try:
        res = discovery.search(name, type="team", sport="basketball")
        return [x.get("id") for x in (res.get("results") or [])][:5]
    except Exception:
        return []


def try_team(tid, date, home, away, max_pages=12):
    try:
        for page in range(1, max_pages + 1):
            r = teams.get_results(tid, page=page)
            ms = flatten(r)
            if not ms:
                break
            for m in ms:
                if m.get("date") != date:
                    continue
                hn = (m.get("home") or {}).get("name")
                an = (m.get("away") or {}).get("name")
                if (sim(hn, home) + sim(an, away)) / 2 >= 0.55:
                    return m
            dates = [m.get("date") for m in ms if m.get("date")]
            if dates and max(dates) < date:
                break
    except Exception:
        pass
    return None


def resolve(row):
    raw = str(int(row.date)) if str(row.date).isdigit() else str(row.date)
    date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    for name in (row.home, row.away):
        for tid in search_ids(name):
            m = try_team(tid, date, row.home, row.away)
            if m:
                return {
                    "match_id": row.match_id, "date": date, "league": row.league,
                    "home": row.home, "away": row.away, "list_score": row.list_score,
                    "fs_home": (m.get("home") or {}).get("name"),
                    "fs_away": (m.get("away") or {}).get("name"),
                    "fs_score": f"{m.get('home_score')}-{m.get('away_score')}",
                    "fs_id": m.get("id"),
                }
    return None


def main():
    d = pd.read_csv(os.path.join(BASE, "tie_fix_status.csv"), dtype=str)
    d = d[d.status.isin(["unresolved_ot", "still_tie"])].copy()
    print("to resolve:", len(d), flush=True)
    rows = list(d.itertuples(index=False))
    found = []
    done = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(resolve, r) for r in rows]
        for f in as_completed(futs):
            done += 1
            try:
                r = f.result()
            except Exception:
                r = None
            if r:
                found.append(r)
            if done % 20 == 0:
                print(f"  {done}/{len(rows)} done, found={len(found)}", flush=True)
    df = pd.DataFrame(found)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print("found:", len(found), "->", OUT, flush=True)


if __name__ == "__main__":
    main()
