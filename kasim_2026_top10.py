"""2-8 Kasım 2026 — önceki backtestin en sağlam 10 ligiyle 250 TL backtest."""
import os
import pandas as pd
import numpy as np

BASE = r"D:\basketball_odds"
STAKE = 250.0

TOP10 = [
    "CBA",
    "Estonya/Letonya Ligi",
    "İzlanda Premier Lig",
    "Macaristan NB I/A",
    "Polonya 1. Lig",
    "İsviçre SBL",
    "Polonya Kadın Ligi",
    "Arjantin Liga Nacional",
    "İtalya Serie A (LBA)",
    "WCBA",
]

d = pd.read_csv(os.path.join(BASE, "kasim_2026_filtre.csv"))
d = d[d.Lig.isin(TOP10)].copy()
d["Tarih"] = pd.to_datetime(d.date.astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")
d["Kazandi"] = d.home_score > d.away_score
d["Kar"] = (d.ml_home - 1) * STAKE * d.Kazandi - STAKE * (~d.Kazandi)
d = d.sort_values(["Tarih", "match_id"]).reset_index(drop=True)
d["Kumulatif"] = d.Kar.cumsum()

out = pd.DataFrame({
    "Tarih": d.Tarih, "Lig": d.Lig,
    "Ev Sahibi": d.home, "Deplasman": d.away,
    "Skor": d.home_score.astype(int).astype(str) + "-" + d.away_score.astype(int).astype(str),
    "Oran": d.ml_home.round(3),
    "Sonuc": d.Kazandi.map({True: "Kazandi", False: "Kaybetti"}),
    "Bahis (TL)": STAKE, "Kar (TL)": d.Kar.round(2),
    "Kumulatif (TL)": d.Kumulatif.round(2),
})
out.to_csv(os.path.join(BASE, "kasim_2026_top10.csv"), index=False, encoding="utf-8-sig")

n = len(d); w = int(d.Kazandi.sum()); profit = float(d.Kar.sum())
turnover = n * STAKE
roi = profit / turnover * 100 if turnover else 0
be = float((1 / d.ml_home).mean() * 100) if n else 0
eq = d.Kar.cumsum(); dd = float((eq.cummax() - eq).max()) if n else 0

print(f"TOP10 bahis n={n} w={w} l={n-w} win%={w/n*100 if n else 0:.1f} avg={d.ml_home.mean() if n else 0:.2f} be={be:.1f}%")
print(f"turnover={turnover:.0f} profit={profit:.0f} roi={roi:.2f}% dd={dd:.0f}")
print("\nMac listesi:")
print(out.to_string(index=False))

md = []
md.append("# 2–8 Kasım 2026 — En Sağlam 10 Lig Backtesti (250 TL)")
md.append("")
md.append("Önceki tüm zamanlar analizindeki en sağlam 10 lig: " + ", ".join(TOP10) + ".")
md.append("")
md.append("| | |")
md.append("|---|---:|")
md.append(f"| Filtreye giren maç | **{n}** |")
md.append(f"| Kazanan / kaybeden | {w} / {n-w} |")
md.append(f"| Kazanma oranı | %{w/n*100 if n else 0:.1f} |")
md.append(f"| Başabaş oranı | %{be:.1f} |")
md.append(f"| Ortalama oran | {d.ml_home.mean() if n else 0:.2f} |")
md.append(f"| Yatırılan | {turnover:,.0f} TL |")
md.append(f"| Kâr / Zarar | **{profit:+,.0f} TL** |")
md.append(f"| ROI | **%{roi:+.2f}** |")
md.append(f"| Maks. drawdown | {dd:,.0f} TL |")
md.append("")
md.append("## Maçlar")
md.append("")
md.append("| Tarih | Lig | Ev | Deplasman | Skor | Oran | Sonuç | Kâr |")
md.append("|---|---|---|---|---|---:|---|---:|")
for r in out.to_dict("records"):
    md.append(f"| {r['Tarih']} | {r['Lig']} | {r['Ev Sahibi']} | {r['Deplasman']} | {r['Skor']} | {r['Oran']} | {r['Sonuc']} | {r['Kar (TL)']:+,.0f} TL |")
open(os.path.join(BASE, "kasim_2026_top10.md"), "w", encoding="utf-8").write("\n".join(md))
print("\n-> kasim_2026_top10.csv / .md")
