"""Filtreli maç CSV'leri (eski veri + 26/27) ve lig özeti."""
import os
import pandas as pd
from canonical import MAP
from scope_check import INC

BASE = r"D:\basketball_odds"
P = os.path.join(BASE, "aiscore_all_matches_final.csv")
STAKE = 250.0
CUT = "2026-08-01"

d = pd.read_csv(P, usecols=["date", "match_id", "league", "country", "home", "away",
                            "status_text", "home_score", "away_score", "ml_home"], low_memory=False)
d = d[(d.status_text == "finished") & d.ml_home.notna() &
      (d.ml_home >= 2.25) & (d.ml_home <= 4) & d.home_score.notna()].copy()
d["canon"] = d.league.map(lambda x: MAP.get(str(x).strip(), str(x).strip()))
d["key"] = list(zip(d.country.fillna(""), d.canon))
d["Lig"] = d.key.map(INC)
d = d[d.Lig.notna()].copy()
d["Tarih"] = pd.to_datetime(d.date.astype(str), format="%Y%m%d", errors="coerce")
d = d.dropna(subset=["Tarih"]).sort_values(["Tarih", "match_id"]).reset_index(drop=True)
d["s27"] = d.Tarih >= CUT

# eşik eski veriye göre
old_counts = d[~d.s27].Lig.value_counts()
keep = old_counts[old_counts >= 100].index
d = d[d.Lig.isin(keep)].copy()

d["Kazandi"] = d.home_score > d.away_score
d["Kar"] = (d.ml_home - 1) * STAKE * d.Kazandi - STAKE * (~d.Kazandi)
d["Kumulatif"] = d.Kar.cumsum()


def write(df, name):
    out = pd.DataFrame({
        "Tarih": df.Tarih.dt.strftime("%Y-%m-%d"),
        "Lig": df.Lig,
        "Ulke": df.country,
        "Ev Sahibi": df.home,
        "Deplasman": df.away,
        "Ev Skoru": df.home_score.astype(int),
        "Deplasman Skoru": df.away_score.astype(int),
        "Oran": df.ml_home.round(3),
        "Sonuc": df.Kazandi.map({True: "Kazandi", False: "Kaybetti"}),
        "Bahis (TL)": STAKE,
        "Kar (TL)": df.Kar.round(2),
        "Kumulatif (TL)": df.Kumulatif.round(2),
    })
    out.to_csv(os.path.join(BASE, name), index=False, encoding="utf-8-sig")
    return len(out)


n_old = write(d[~d.s27], "paper_bets_250.csv")
n_new = write(d[d.s27], "paper_bets_2627.csv")
print("old csv:", n_old, "| 26/27 csv:", n_new)

old = d[~d.s27]
rows = []
for lig, g in old.groupby("Lig"):
    n = len(g); w = int(g.Kazandi.sum()); profit = float(g.Kar.sum())
    eq = 0; peak = 0; dd = 0
    for p in g.Kar:
        eq += p; peak = max(peak, eq); dd = max(dd, peak - eq)
    rows.append({
        "Lig": lig, "Ulke": g.country.iloc[0], "Mac": n, "Kazanan": w, "Kaybeden": n - w,
        "Kazanma %": round(w / n * 100, 2), "Ort. Oran": round(float(g.ml_home.mean()), 3),
        "Yatirilan (TL)": n * STAKE, "Kar (TL)": round(profit, 2),
        "ROI %": round(profit / (n * STAKE) * 100, 2), "Maks DD (TL)": round(-dd, 2),
    })
s = pd.DataFrame(rows).sort_values("Mac", ascending=False)
s.to_csv(os.path.join(BASE, "paper_bets_league_summary.csv"), index=False, encoding="utf-8-sig")
print("league summary:", len(s))
print("old profit:", round(old.Kar.sum(), 2), "ROI:", round(old.Kar.sum() / (len(old) * STAKE) * 100, 2))
print("26/27 profit:", round(d[d.s27].Kar.sum(), 2), "ROI:", round(d[d.s27].Kar.sum() / (len(d[d.s27]) * STAKE) * 100, 2))
