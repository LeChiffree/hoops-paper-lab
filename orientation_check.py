"""Ã–rneklemde ev/deplasman yÃ¶nÃ¼ + skor + oran doÄŸrulamasÄ± (Flashscore)."""
import os
import re
import statistics
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher

import pandas as pd

sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore import discovery, teams
from flashscore.fetch import get_graphql_optional

BASE = r"D:\basketball_odds"
OUT = os.path.join(BASE, "orientation_check.csv")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def flatten(r):
    return [m for c in r.get("competitions") or [] for m in c.get("matches") or []]


def search_ids(name):
    try:
        res = discovery.search(name, type="team", sport="basketball")
        return [x.get("id") for x in (res.get("results") or [])][:4]
    except Exception:
        return []


def try_team(tid, date, home, away, max_pages=10):
    try:
        for page in range(1, max_pages + 1):
            ms = flatten(teams.get_results(tid, page=page))
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
                return m
    return None


def sf(v):
    try:
        x = float(v)
        return x if x > 1.0 else None
    except (TypeError, ValueError):
        return None


def med(v):
    v = [x for x in v if x]
    return round(statistics.median(v), 3) if v else None


def fs_odds(m):
    sides = {}
    if m.get("home_pid"):
        sides[m["home_pid"]] = "home"
    if m.get("away_pid"):
        sides[m["away_pid"]] = "away"
    for geo in ("DE", "GB"):
        try:
            payload = get_graphql_optional("oce", {"eventId": m["id"], "projectId": 2,
                                                   "geoIpCode": geo, "geoIpSubdivisionCode": ""}, odds=True) or {}
        except Exception:
            payload = {}
        h = payload.get("findOddsByEventId") or {}
        hh, aa = [], []
        for r in h.get("odds") or []:
            if r.get("bettingType") != "HOME_AWAY" or r.get("bettingScope") != "FULL_TIME_OVER_TIME":
                continue
            sel = r.get("odds") or []
            if len(sel) != 2:
                continue
            vals = {}
            for o in sel:
                side = sides.get(o.get("eventParticipantId"))
                v = sf(o.get("value"))
                if side and v:
                    vals[side] = v
            if "home" in vals and "away" in vals:
                hh.append(vals["home"]); aa.append(vals["away"])
        if hh:
            return med(hh), med(aa)
    return None, None


def check(row):
    m = resolve(row)
    if not m:
        return {"match_id": row.match_id, "date": row.date, "country": row.country,
                "league": row.league, "ai_home": row.home, "ai_away": row.away,
                "ai_score": f"{int(row.home_score)}-{int(row.away_score)}",
                "ai_ml_home": row.ml_home, "found": 0}
    fh = (m.get("home") or {}).get("name")
    fa = (m.get("away") or {}).get("name")
    same = sim(row.home, fh) + sim(row.away, fa)
    swap = sim(row.home, fa) + sim(row.away, fh)
    orient = "ok" if same >= swap else "swapped"
    fs_h, fs_a = m.get("home_score"), m.get("away_score")
    if orient == "swapped":
        fs_h, fs_a = fs_a, fs_h
    score_match = (fs_h == row.home_score and fs_a == row.away_score)
    fho, fao = fs_odds(m)
    fs_home_odds = fho if orient == "ok" else fao
    return {"match_id": row.match_id, "date": row.date, "country": row.country,
            "league": row.league, "ai_home": row.home, "ai_away": row.away,
            "ai_score": f"{int(row.home_score)}-{int(row.away_score)}",
            "ai_ml_home": row.ml_home, "fs_home": fh, "fs_away": fa,
            "fs_score": f"{fs_h}-{fs_a}", "fs_ml_home": fs_home_odds,
            "orientation": orient, "score_match": score_match,
            "odds_diff": round(row.ml_home - fs_home_odds, 3) if fs_home_odds else None,
            "found": 1}


def main():
    s = pd.read_csv(os.path.join(BASE, "orientation_sample.csv"), dtype={"date": str})
    print("samples:", len(s), flush=True)
    rows = list(s.itertuples(index=False))
    out = []
    done = 0
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(check, r) for r in rows]
        for f in as_completed(futs):
            done += 1
            try:
                out.append(f.result())
            except Exception:
                pass
            if done % 20 == 0:
                print(f"  {done}/{len(rows)}", flush=True)
    df = pd.DataFrame(out)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    f = df[df.found == 1]
    print("found:", len(f), "/", len(df))
    if len(f):
        print("orientation:", f.orientation.value_counts().to_dict())
        print("score match:", int(f.score_match.sum()), f"({f.score_match.mean()*100:.1f}%)")
        od = f.dropna(subset=["odds_diff"])
        print("odds n:", len(od), "MAE:", round(od.odds_diff.abs().mean(), 3),
              "median abs:", round(od.odds_diff.abs().median(), 3))
    print("->", OUT, flush=True)


if __name__ == "__main__":
    main()
