"""2-8 Kasım 2026 filtrelenmiş maçların 250 TL backtest'i."""
import os
import pandas as pd
import numpy as np

BASE = r"D:\basketball_odds"
P = os.path.join(BASE, "kasim_2026_filtre.csv")
STAKE = 250.0

d = pd.read_csv(P)
d["Tarih"] = pd.to_datetime(d.date.astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")
d["Kazandi"] = d.home_score > d.away_score
d["Kar"] = (d.ml_home - 1) * STAKE * d.Kazandi - STAKE * (~d.Kazandi)
d = d.sort_values(["Tarih", "match_id"]).reset_index(drop=True)
d["Kumulatif"] = d.Kar.cumsum()

out = pd.DataFrame({
    "Tarih": d.Tarih,
    "Lig": d.Lig,
    "Ev Sahibi": d.home,
    "Deplasman": d.away,
    "Skor": d.home_score.astype(int).astype(str) + "-" + d.away_score.astype(int).astype(str),
    "Oran": d.ml_home.round(3),
    "Sonuc": d.Kazandi.map({True: "Kazandi", False: "Kaybetti"}),
    "Bahis (TL)": STAKE,
    "Kar (TL)": d.Kar.round(2),
    "Kumulatif (TL)": d.Kumulatif.round(2),
})
out.to_csv(os.path.join(BASE, "kasim_2026_backtest.csv"), index=False, encoding="utf-8-sig")

n = len(d); w = int(d.Kazandi.sum()); profit = float(d.Kar.sum())
turnover = n * STAKE
roi = profit / turnover * 100
se = (np.where(d.Kazandi, d.ml_home - 1, -1.0).std(ddof=1) / np.sqrt(n)) * 100
be = float((1 / d.ml_home).mean() * 100)
eq = d.Kar.cumsum(); dd = float((eq.cummax() - eq).max())

print(f"n={n} w={w} l={n-w} win%={w/n*100:.1f} avg={d.ml_home.mean():.2f} be={be:.1f}%")
print(f"turnover={turnover:.0f} profit={profit:.0f} roi={roi:.2f}% se={se:.2f} dd={dd:.0f}")

rows = []
for lg, g in d.groupby("Lig"):
    nn = len(g); ww = int(g.Kazandi.sum()); pp = float(g.Kar.sum())
    rows.append({"Lig": lg, "Mac": nn, "Kazanan": ww, "Kazanma %": round(ww / nn * 100, 1),
                 "Ort. Oran": round(g.ml_home.mean(), 2), "Kar (TL)": round(pp, 2),
                 "ROI %": round(pp / (nn * STAKE) * 100, 2)})
lg = pd.DataFrame(rows).sort_values("Kar (TL)", ascending=False)
lg.to_csv(os.path.join(BASE, "kasim_2026_lig_ozet.csv"), index=False, encoding="utf-8-sig")
print("\nEn iyi ligler:")
print(lg.head(8).to_string(index=False))
print("\nEn kötü ligler:")
print(lg.tail(5).to_string(index=False))

md = []
md.append("# 2–8 Kasım 2026 — 250 TL Backtest")
md.append("")
md.append("| | |")
md.append("|---|---:|")
md.append(f"| Filtreye giren maç | **{n}** |")
md.append(f"| Kazanan / kaybeden | {w} / {n-w} |")
md.append(f"| Kazanma oranı | %{w/n*100:.1f} |")
md.append(f"| Başabaş oranı | %{be:.1f} |")
md.append(f"| Ortalama oran | {d.ml_home.mean():.2f} |")
md.append(f"| Yatırılan | {turnover:,.0f} TL |")
md.append(f"| Kâr / Zarar | **{profit:+,.0f} TL** |")
md.append(f"| ROI | **%{roi:+.2f}** |")
md.append(f"| Maks. drawdown | {dd:,.0f} TL |")
md.append("")
md.append("## Lig bazında")
md.append("")
md.append("| Lig | Maç | Kazanan | Kazanma | Ort. Oran | Kâr | ROI |")
md.append("|---|---:|---:|---:|---:|---:|---:|")
for r in lg.to_dict("records"):
    md.append(f"| {r['Lig']} | {r['Mac']} | {r['Kazanan']} | %{r['Kazanma %']} | {r['Ort. Oran']} | {r['Kar (TL)']:+,.0f} TL | %{r['ROI %']:+.2f} |")
md.append("")
md.append("## Günlük")
md.append("")
md.append("| Tarih | Maç | Kâr |")
md.append("|---|---:|---:|")
for day, g in d.groupby("Tarih"):
    md.append(f"| {day} | {len(g)} | {g.Kar.sum():+,.0f} TL |")
open(os.path.join(BASE, "kasim_2026_backtest.md"), "w", encoding="utf-8").write("\n".join(md))
print("\n-> kasim_2026_backtest.csv / .md")
