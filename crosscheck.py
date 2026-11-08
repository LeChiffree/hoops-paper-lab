"""AiScore vs Flashscore â€” aynÄ± 7 gÃ¼nÃ¼ eÅŸleÅŸtirip skor/orta hakem karÅŸÄ±laÅŸtÄ±rmasÄ±."""
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

BASE = r"D:\basketball_odds"
ai = pd.read_csv(f"{BASE}\\aiscore_matches.csv")
fs = pd.read_csv(f"{BASE}\\flashscore_days.csv")

ai["date"] = pd.to_datetime(ai["date"].astype(str), format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
fs["date"] = pd.to_datetime(fs["date"].astype(str), errors="coerce").dt.strftime("%Y-%m-%d")
fs = fs[fs.status == "finished"].copy()
ai_fin = ai[(ai.status == 3) & ai.home_score.notna() & ai.away_score.notna()].copy()


def norm(s):
    s = str(s) if pd.notna(s) else ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((w|women|woman)\)", " w ", s)
    s = re.sub(r"\b(women|woman)\b", " w ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


pairs = []
used_fs = set()
for day, group in ai_fin.groupby("date"):
    cand = fs[fs.date == day]
    for ar in group.itertuples(index=False):
        best = None
        for fr in cand.itertuples(index=False):
            if fr.fs_id in used_fs:
                continue
            same = 0.5 * sim(ar.home, fr.home) + 0.5 * sim(ar.away, fr.away)
            swap = 0.5 * sim(ar.home, fr.away) + 0.5 * sim(ar.away, fr.home)
            score = max(same, swap)
            if best is None or score > best[0]:
                best = (score, fr, swap > same)
        if best and best[0] >= 0.75:
            score, fr, swapped = best
            used_fs.add(fr.fs_id)
            pairs.append({
                "date": day, "ai_id": ar.match_id, "fs_id": fr.fs_id,
                "league_ai": ar.league, "league_fs": fr.league,
                "home_ai": ar.home, "away_ai": ar.away,
                "home_fs": fr.home, "away_fs": fr.away,
                "score_ai": f"{int(ar.home_score)}-{int(ar.away_score)}",
                "score_fs": f"{int(fr.home_score)}-{int(fr.away_score)}",
                "sim": round(score, 3), "swapped": swapped,
                "ml_home_ai": ar.ml_home, "ml_away_ai": ar.ml_away,
            })

p = pd.DataFrame(pairs)
p["score_equal"] = p.score_ai == p.score_fs
p["winner_ai"] = p.score_ai.apply(lambda x: "H" if int(x.split("-")[0]) > int(x.split("-")[1]) else "A")
p["winner_fs"] = p.score_fs.apply(lambda x: "H" if int(x.split("-")[0]) > int(x.split("-")[1]) else "A")
p["winner_equal"] = p.winner_ai == p.winner_fs

out = f"{BASE}\\crosscheck_matches.csv"
p.to_csv(out, index=False, encoding="utf-8-sig")

print("AiScore finished:", len(ai_fin))
print("Flashscore finished:", len(fs))
print("matched pairs:", len(p), f"({len(p)/len(ai_fin)*100:.1f}% of AiScore)")
print("exact score match:", p.score_equal.sum(), f"({p.score_equal.mean()*100:.1f}%)")
print("winner match:", p.winner_equal.sum(), f"({p.winner_equal.mean()*100:.1f}%)")
print("swapped home/away:", p.swapped.sum())
print("mean name similarity:", round(p.sim.mean(), 3))

bad = p[~p.score_equal]
print("\nmismatched scores:", len(bad))
for r in bad.head(15).itertuples(index=False):
    print(f"  {r.date} {r.league_ai[:28]:28s} | {r.home_ai} vs {r.away_ai} | AI {r.score_ai} FS {r.score_fs} | sim {r.sim}")

print("\nper day:")
for day, g in p.groupby("date"):
    print(f"  {day}: {len(g):3d} pairs, exact {g.score_equal.mean()*100:5.1f}%, winner {g.winner_equal.mean()*100:5.1f}%")
