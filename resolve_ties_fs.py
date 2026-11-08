"""AiScore unresolved_ot maÃ§larÄ±nÄ± Flashscore takÄ±m arÅŸivinden Ã§Ã¶z."""
import sys, re, unicodedata, time
import pandas as pd
from difflib import SequenceMatcher

sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore import discovery, teams

BASE = r"D:\basketball_odds"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((w|women|woman)\)", " w ", s)
    s = re.sub(r"\b(women|woman)\b", " w ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def flatten(r):
    out = []
    for c in r.get("competitions") or []:
        for m in c.get("matches") or []:
            out.append(m)
    return out


def resolve(row, cache, max_pages=8):
    home, away = row.home, row.away
    raw = str(int(row.date)) if str(row.date).isdigit() else str(row.date)
    date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw
    key = norm(home)
    if key not in cache:
        try:
            res = discovery.search(home, type="team", sport="basketball")
            cache[key] = [x.get("id") for x in (res.get("results") or [])][:4]
        except Exception:
            cache[key] = []
    for tid in cache[key]:
        try:
            for page in range(1, max_pages + 1):
                r = teams.get_results(tid, page=page)
                ms = flatten(r)
                if not ms:
                    break
                dates = [m.get("date") for m in ms if m.get("date")]
                for m in ms:
                    if m.get("date") != date:
                        continue
                    hn = (m.get("home") or {}).get("name")
                    an = (m.get("away") or {}).get("name")
                    if (sim(hn, home) + sim(an, away)) / 2 >= 0.55:
                        return m.get("home_score"), m.get("away_score"), hn, an, tid
                # sayfa tarih aralÄ±ÄŸÄ±nÄ± geÃ§tiyse dur
                if dates and min(dates) < date and max(dates) < date:
                    break
        except Exception:
            continue
    return None


if __name__ == "__main__":
    d = pd.read_csv(f"{BASE}\\tie_fix_status.csv", dtype=str)
    d = d[d.status.isin(["unresolved_ot", "still_tie"])].copy()
    recent = d[d.date.astype(str) >= "20240101"].head(10)
    cache = {}
    for r in recent.itertuples(index=False):
        got = resolve(r, cache)
        print(f"{r.date} {r.league[:22]:22s} {r.home[:20]:20s}-{r.away[:20]:20s} liste {r.list_score} -> "
              f"{got[0]}-{got[1]} ({got[2]}-{got[3]})" if got else f"{r.date} {r.home} - {r.away} -> BULUNAMADI")
