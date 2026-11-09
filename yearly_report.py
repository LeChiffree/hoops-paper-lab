"""2018-2026 yıllık en iyi 10 ROI ligi + yıllık özet -> markdown."""
import numpy as np
import pandas as pd

P = r"D:\basketball_odds\paper_bets_250.csv"
OUT = r"D:\basketball_odds\yillik_en_iyi_10_lig.md"
STAKE = 250.0
MIN_N = 30

d = pd.read_csv(P)
d["y"] = d["Tarih"].str[:4].astype(int)
d["win"] = d["Sonuc"] == "Kazandi"

lines = []
lines.append("# 2018–2026 Yıllık En İyi 10 ROI Lig")
lines.append("")
lines.append("> **Yöntem:** Her takvim yılı ayrı değerlendirildi. Ev sahibi 1-2 kapanış oranı 2.25–4.00, bahis 250 TL sabit.")
lines.append("> Lig sıralamasına yalnızca o yıl **en az 30 bahis** almış ligler girdi. 2026 verisi Ocak–Temmuz aralığını kapsar (25/26 sezon sonu); 26/27 sezonu dahil değildir.")
lines.append("> `t` = ROI / standart hata; 2+ güçlü, 1–2 destek, <1 zayıf kanıt.")
lines.append("")
lines.append("---")
lines.append("")

for y in range(2018, 2027):
    g = d[d.y == y]
    if not len(g):
        continue
    rows = []
    for lg, x in g.groupby("Lig"):
        n = len(x)
        if n < MIN_N:
            continue
        w = int(x.win.sum())
        profit = float(x["Kar (TL)"].sum())
        roi = profit / (n * STAKE) * 100
        ret = np.where(x.win, x.Oran - 1, -1.0)
        se = ret.std(ddof=1) / np.sqrt(n) * 100
        rows.append({"Lig": lg, "n": n, "w": w, "win": w / n * 100,
                     "odds": x.Oran.mean(), "profit": profit, "roi": roi,
                     "t": roi / se if se else 0})
    r = pd.DataFrame(rows).sort_values(["roi", "n"], ascending=[False, False])
    top = r.head(10)

    total_n = len(g)
    total_p = float(g["Kar (TL)"].sum())
    total_roi = total_p / (total_n * STAKE) * 100
    win_pct = g.win.mean() * 100
    be = (1 / g.Oran).mean() * 100
    pos_lg = int((r.roi > 0).sum())
    neg_lg = int((r.roi <= 0).sum())
    top_profit = float(top.profit.sum())
    share = top_profit / total_p * 100 if total_p else 0
    best = r.iloc[0]
    worst = r.iloc[-1]

    lines.append(f"## {y}" + (" *(kısmi yıl: Oca–Tem)*" if y == 2026 else ""))
    lines.append("")
    lines.append(f"### {y} — En İyi 10 Lig")
    lines.append("")
    lines.append("| # | Lig | Maç | Kazanan | Kazanma | Ort. Oran | Kâr | ROI | t |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, x in enumerate(top.itertuples(index=False), 1):
        lines.append(f"| {i} | {x.Lig} | {x.n} | {x.w} | %{x.win:.1f} | {x.odds:.2f} | "
                     f"{x.profit:+,.0f} TL | **%{x.roi:+.2f}** | {x.t:.2f} |".replace(",", "."))
    lines.append("")
    lines.append(f"### {y} — Yıllık Özet")
    lines.append("")
    lines.append("| Metrik | DeÄŸer |")
    lines.append("|---|---:|")
    lines.append(f"| Toplam bahis | {total_n:,} |".replace(",", "."))
    lines.append(f"| Toplam kâr / zarar | {total_p:+,.0f} TL |".replace(",", "."))
    lines.append(f"| Yıl geneli ROI | **%{total_roi:+.2f}** |")
    lines.append(f"| Kazanma oranı / başabaş | %{win_pct:.1f} / %{be:.1f} |")
    lines.append(f"| Pozitif / negatif lig (n≥{MIN_N}) | {pos_lg} / {neg_lg} |")
    lines.append(f"| En iyi lig | {best.Lig} (%{best.roi:+.1f}, {best.n} maç) |")
    lines.append(f"| Top 10 toplam kârı | {top_profit:+,.0f} TL |".replace(",", "."))
    lines.append("")
    lines.append("---")
    lines.append("")

# yıllar arası tekrar
lines.append("## Yıllar Arası Tekrar")
lines.append("")
lines.append("En iyi 10'a en çok giren ligler (2018–2026):")
lines.append("")
from collections import Counter
cnt = Counter()
for y in range(2018, 2027):
    g = d[d.y == y]
    rows = []
    for lg, x in g.groupby("Lig"):
        n = len(x)
        if n < MIN_N:
            continue
        profit = float(x["Kar (TL)"].sum())
        rows.append((lg, profit / (n * STAKE) * 100))
    top = sorted(rows, key=lambda z: z[1], reverse=True)[:10]
    for lg, _ in top:
        cnt[lg] += 1
lines.append("| Lig | Kaç yıl top 10 |")
lines.append("|---|---:|")
for lg, c in cnt.most_common(12):
    lines.append(f"| {lg} | {c} |")
lines.append("")
lines.append("---")
lines.append("")
lines.append("*Not: Yıllık sıralamalar geriye dönük seçimdir; yüksek ROI'li küçük örneklemler (30–100 bahis) yanıltıcı olabilir. "
             "Sürdürülebilirlik için t-değeri ve sezon tekrarına bakılmalıdır.*")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("written", OUT)
print("\n".join(lines[:60]))
