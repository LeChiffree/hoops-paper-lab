"""2 aylık periyotlardan 2'şer maçlık yön doğrulama örneklemi."""
import pandas as pd
import numpy as np

P = r"D:\basketball_odds\aiscore_all_matches_final.csv"
OUT = r"D:\basketball_odds\orientation_sample.csv"

d = pd.read_csv(P, usecols=["date", "match_id", "league", "country", "home", "away",
                            "status_text", "home_score", "away_score", "ml_home", "ml_away",
                            "tie_status"], low_memory=False)
d = d[(d.status_text == "finished") & d.ml_home.notna() & d.ml_away.notna() & d.home_score.notna()].copy()
d["date"] = d.date.astype(str)
d["year"] = d.date.str[:4].astype(int)
d["month"] = d.date.str[4:6].astype(int)
d["period"] = d.year.astype(str) + "-" + (((d.month - 1) // 2) + 1).astype(str).str.zfill(2)

# lig büyüklüğü (FS kapsamı için)
lg_n = d.groupby("league").size()
d["lg_n"] = d.league.map(lg_n)
d = d[d.lg_n >= 100]

rng = np.random.default_rng(42)
rows = []
for period, g in d.groupby("period"):
    # ülke çeşitliliği: her ülkeden en fazla 1
    picked = []
    countries = g.country.dropna().unique().tolist()
    rng.shuffle(countries)
    for c in countries:
        if len(picked) >= 2:
            break
        sub = g[g.country == c]
        if len(sub) == 0:
            continue
        picked.append(sub.sample(1, random_state=int(rng.integers(1e6))).iloc[0])
    rows.extend(picked)

s = pd.DataFrame(rows)
s.to_csv(OUT, index=False, encoding="utf-8-sig")
print("periods:", d.period.nunique(), "samples:", len(s))
print(s.groupby("period").size().describe())
print(s[["date", "country", "league", "home", "away", "ml_home", "ml_away"]].head(10).to_string(index=False))
