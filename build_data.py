"""Dashboard veri seti: eski veri + 26/27 sezonu bayrağı, lig metrikleri."""
import json
import os
import numpy as np
import pandas as pd
from canonical import MAP
from scope_check import INC

BASE = r"D:\basketball_odds"
P = os.path.join(BASE, "aiscore_all_matches_final.csv")
OUT = os.path.join(BASE, "dashboard_data.json")
STAKE = 250.0
CUT = "2026-08-01"

d = pd.read_csv(P, usecols=["date", "match_id", "league", "country", "home", "away",
                            "status_text", "home_score", "away_score", "ml_home"], low_memory=False)
d = d[(d.status_text == "finished") & d.ml_home.notna() &
      (d.ml_home >= 2.25) & (d.ml_home <= 4) & d.home_score.notna()].copy()
d["canon"] = d.league.map(lambda x: MAP.get(str(x).strip(), str(x).strip()))
d["key"] = list(zip(d.country.fillna(""), d.canon))
d["display"] = d.key.map(INC)
d = d[d.display.notna()].copy()

d["date"] = pd.to_datetime(d.date.astype(str), format="%Y%m%d", errors="coerce")
d = d.dropna(subset=["date"])
d["s27"] = (d.date >= CUT).astype(int)
d["win"] = (d.home_score > d.away_score).astype(int)
d["profit"] = (d.ml_home - 1) * STAKE * d.win - STAKE * (1 - d.win)
d["season"] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)

old = d[d.s27 == 0]
cnt = old.display.value_counts()
keep = set(cnt[cnt >= 100].index)
d = d[d.display.isin(keep)].sort_values(["date", "match_id"]).reset_index(drop=True)

leagues = sorted(d.display.unique())
idx = {name: i for i, name in enumerate(leagues)}

meta = []
for name in leagues:
    sub = d[d.display == name]
    o = sub[sub.s27 == 0]
    n = len(o)
    profit = float(o.profit.sum())
    roi = profit / (n * STAKE) * 100 if n else 0
    ret = np.where(o.win == 1, o.ml_home - 1, -1.0)
    se = ret.std(ddof=1) / np.sqrt(n) * 100 if n > 1 else 0
    seasons = o.groupby("season").profit.sum()
    scount = o.groupby("season").size()
    season_df = pd.DataFrame({"p": seasons, "n": scount})
    season_df = season_df[season_df.n >= 20]
    pos = int((season_df.p > 0).sum())
    tot = len(season_df)
    worst_roi = float((season_df.p / (season_df.n * STAKE) * 100).min()) if tot else 0
    meta.append({
        "name": name, "country": sub.country.iloc[0],
        "n": n, "n27": int((sub.s27 == 1).sum()),
        "roi": round(roi, 2), "se": round(se, 2), "t": round(roi / se, 2) if se else 0,
        "posPct": round(pos / tot * 100, 1) if tot else 0,
        "seasons": tot, "worstRoi": round(worst_roi, 1),
    })

matches = []
for r in d.itertuples(index=False):
    matches.append([r.date.strftime("%Y-%m-%d"), idx[r.display], r.home, r.away,
                    int(r.home_score), int(r.away_score), round(float(r.ml_home), 3),
                    int(r.win), round(float(r.profit), 2), int(r.s27)])

reco = {
    "core": ["CBA"],
    "support": ["Macaristan NB I/A", "İzlanda Premier Lig"],
    "watch": ["Estonya/Letonya Ligi", "Polonya 1. Lig", "İtalya Serie A (LBA)", "Arjantin Liga Nacional"],
}

payload = {"stake": STAKE, "cut": CUT, "leagues": meta, "matches": matches, "reco": reco}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
print("leagues", len(leagues), "matches", len(matches), "s27", int(d.s27.sum()))
print("json MB", round(os.path.getsize(OUT) / 1048576, 2))
o = d[d.s27 == 0]
print("old matches", len(o), "profit", round(o.profit.sum(), 2), "roi", round(o.profit.sum() / (len(o) * STAKE) * 100, 2))
