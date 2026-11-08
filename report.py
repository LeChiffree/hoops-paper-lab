"""
Rapor üretici: Flashscore verisinden 1X2 ev sahibi 2.25-4.00 filtresi + 10.000 TL sabit bahis.

Çıktılar:
  basketball_1x2_rapor.xlsx   (özet + lig lig maç listeleri + ML özeti + yöntem)
  rapor.html                  (görsel rapor, lig lig açılır tablolar)
  tum_filtreli_maclar.csv
  lig_ozet.csv
"""
import json
import os
import re
import sqlite3
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data.sqlite3")
STAKE = 10000
LO, HI = 2.25, 4.00
MARGIN = 0.0
COVERAGE = 0.0
TOTAL_MATCHES = 0

NAVY = "1F2A44"
ACCENT = "0F766E"
LIGHT = "F1F5F9"
RED = "B91C1C"
GREEN = "15803D"


def tl(x):
    return f"{x:,.0f}".replace(",", ".")


def pct(x, digits=1):
    return f"{x:+.{digits}f}%".replace(".", ",")


def load():
    con = sqlite3.connect(DB)
    df = pd.read_sql_query(
        """SELECT id, league, season, season_start, date, home, away,
                  home_score, away_score, reg_home, reg_away, went_ot,
                  o1, ox, o2, ml1, ml2, n_books, odds_geo
           FROM matches
           WHERE status='finished' AND reg_home IS NOT NULL AND reg_away IS NOT NULL""",
        con,
    )
    con.close()
    df["tarih"] = pd.to_datetime(df["date"], errors="coerce")
    df["sonuc"] = df.apply(
        lambda r: "1" if r.reg_home > r.reg_away else ("X" if r.reg_home == r.reg_away else "2"), axis=1
    )
    df["ms"] = df.apply(
        lambda r: "1" if r.home_score > r.away_score else ("2" if r.home_score < r.away_score else "X"), axis=1
    )
    return df


def prepare(df):
    q = df[(df.o1 >= LO) & (df.o1 <= HI)].copy()
    q["bahis"] = STAKE
    q["kazandi"] = q.sonuc == "1"
    q["geri_donus"] = q.apply(lambda r: STAKE * r.o1 if r.kazandi else 0.0, axis=1)
    q["kar"] = q.geri_donus - q.bahis
    return q.sort_values(["league", "tarih"], ascending=[True, False])


def summarize(q, odds_col="o1"):
    rows = []
    for lg, g in q.groupby("league", sort=False):
        n = len(g)
        w = int(g.kazandi.sum())
        staked = n * STAKE
        profit = float(g.kar.sum())
        ret = (g[odds_col] - 1).where(g.kazandi, -1.0)
        se = float(ret.std(ddof=1) / (n ** 0.5) * 100) if n > 1 else 0.0
        rows.append({
            "Lig": lg,
            "Maç": n,
            "Kazanan": w,
            "Kaybeden": n - w,
            "Kazanma %": round(w / n * 100, 1) if n else 0.0,
            "Ort. Oran": round(float(g[odds_col].mean()), 2) if n else 0.0,
            "Başabaş %": round(float((1 / g[odds_col]).mean() * 100), 1) if n else 0.0,
            "Yatırılan": staked,
            "Geri Dönüş": staked + profit,
            "Kâr/Zarar": profit,
            "ROI %": round(profit / staked * 100, 2) if staked else 0.0,
            "ROI ±%": round(se, 2),
        })
    out = pd.DataFrame(rows).sort_values("Maç", ascending=False)
    return out


def totals(q, odds_col="o1"):
    n = len(q)
    w = int(q.kazandi.sum())
    staked = n * STAKE
    profit = float(q.kar.sum())
    ret = (q[odds_col] - 1).where(q.kazandi, -1.0)
    se = float(ret.std(ddof=1) / (n ** 0.5) * 100) if n > 1 else 0.0
    return {
        "n": n, "w": w, "l": n - w,
        "win_pct": (w / n * 100) if n else 0,
        "avg_odds": float(q[odds_col].mean()) if n else 0,
        "breakeven": float((1 / q[odds_col]).mean() * 100) if n else 0,
        "staked": staked, "profit": profit,
        "roi": (profit / staked * 100) if staked else 0,
        "se": se,
    }


def season_matrix(q):
    t = q.copy()
    t["sezon"] = t["season"]
    p = t.pivot_table(index="league", columns="sezon", values="kar", aggfunc="sum", fill_value=0)
    c = t.pivot_table(index="league", columns="sezon", values="id", aggfunc="count", fill_value=0)
    return p, c


def band_table(q):
    bins = [2.2499, 2.75, 3.25, 4.0001]
    labels = ["2.25 – 2.75", "2.75 – 3.25", "3.25 – 4.00"]
    t = q.copy()
    t["bant"] = pd.cut(t.o1, bins=bins, labels=labels)
    rows = []
    for b, g in t.groupby("bant", observed=True):
        n = len(g); w = int(g.kazandi.sum()); staked = n * STAKE; profit = float(g.kar.sum())
        rows.append({"Oran Bandı": str(b), "Maç": n, "Kazanan": w,
                     "Kazanma %": round(w / n * 100, 1), "Ort. Oran": round(float(g.o1.mean()), 2),
                     "Yatırılan": staked, "Kâr/Zarar": profit,
                     "ROI %": round(profit / staked * 100, 2)})
    return pd.DataFrame(rows)


def season_table(q):
    rows = []
    for s, g in q.groupby("season_start"):
        n = len(g); w = int(g.kazandi.sum()); staked = n * STAKE; profit = float(g.kar.sum())
        rows.append({"Sezon": g.season.iloc[0], "Maç": n, "Kazanan": w,
                     "Kazanma %": round(w / n * 100, 1), "Ort. Oran": round(float(g.o1.mean()), 2),
                     "Yatırılan": staked, "Kâr/Zarar": profit,
                     "ROI %": round(profit / staked * 100, 2)})
    return pd.DataFrame(rows).sort_values("Sezon")


# ------------------------------------------------------------------ Excel
THIN = Side(style="thin", color="D8DEE9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def style_header(ws, ncols, row=1):
    fill = PatternFill("solid", fgColor=NAVY)
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 30


def sheet_name(name):
    s = re.sub(r"[\\/*?:\[\]]", "", name)
    return s[:31] or "Lig"


def write_summary_sheet(wb, summary, tot, title, front=True):
    ws = wb.create_sheet(title, 0) if front else wb.create_sheet(title)
    headline = "Basketbol 1X2" if "ML" not in title else "Basketbol Moneyline (Uzatma Dahil)"
    ws["A1"] = f"{headline} — Ev Sahibi Oranı 2.25–4.00 | 10.000 TL Sabit Bahis"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws.merge_cells("A1:L1")
    ws["A2"] = (f"Son 10 sezon (2016/17–2025/26) · {tot['n']:,} filtreli maç · "
                f"Toplam yatırılan {tl(tot['staked'])} TL · Kâr/Zarar {tl(tot['profit'])} TL · "
                f"ROI {pct(tot['roi'])}").replace(",", ".")
    ws["A2"].font = Font(size=10, color="475569")
    ws.merge_cells("A2:L2")
    headers = list(summary.columns)
    for j, h in enumerate(headers, 1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, len(headers), row=4)
    for i, row in enumerate(summary.itertuples(index=False), start=5):
        for j, v in enumerate(row, 1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.border = BORDER
            if j in (8, 9, 10):
                cell.number_format = '#,##0 "TL"'
            elif j in (5, 11):
                cell.number_format = '0.0"%"'
            elif j == 6:
                cell.number_format = "0.00"
            elif j == 7:
                cell.number_format = '0.0"%"'
            elif j == 12:
                cell.number_format = '±0.0"%"'
            if j == 11:
                cell.font = Font(bold=True, color=GREEN if v >= 0 else RED)
            cell.alignment = Alignment(horizontal="center" if j != 1 else "left")
    r = len(summary) + 6
    ws.cell(row=r, column=1, value="TOPLAM").font = Font(bold=True)
    for j, v in [(2, tot["n"]), (3, tot["w"]), (4, tot["l"]), (5, round(tot["win_pct"], 1)),
                 (6, round(tot["avg_odds"], 2)), (7, round(tot["breakeven"], 1)),
                 (8, tot["staked"]), (9, tot["staked"] + tot["profit"]), (10, tot["profit"]),
                 (11, round(tot["roi"], 2)), (12, round(tot["se"], 2))]:
        c = ws.cell(row=r, column=j, value=v)
        c.font = Font(bold=True)
        c.border = BORDER
        c.fill = PatternFill("solid", fgColor=LIGHT)
        if j in (8, 9, 10):
            c.number_format = '#,##0 "TL"'
        if j in (5, 11):
            c.number_format = '0.00"%"'
        if j == 6:
            c.number_format = "0.00"
        if j == 12:
            c.number_format = '±0.00"%"'
    widths = [26, 9, 10, 10, 11, 10, 11, 15, 16, 14, 9, 8]
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A5"
    return ws


def write_league_sheet(wb, lg, g):
    ws = wb.create_sheet(sheet_name(lg))
    n = len(g); w = int(g.kazandi.sum()); staked = n * STAKE; profit = float(g.kar.sum())
    ws["A1"] = lg
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws.merge_cells("A1:M1")
    ws["A2"] = (f"{n} maç · {w} kazanan / {n-w} kaybeden · Kazanma %{w/n*100:.1f} · "
                f"Ort. oran {g.o1.mean():.2f} · Yatırılan {tl(staked)} TL · "
                f"Kâr/Zarar {tl(profit)} TL · ROI {pct(profit/staked*100)}").replace(",", ".")
    ws["A2"].font = Font(size=10, color="475569")
    ws.merge_cells("A2:M2")
    headers = ["Tarih", "Sezon", "Ev Sahibi", "Deplasman", "Normal Süre", "Uzatma",
               "Sonuç (1X2)", "Oran 1", "Oran X", "Oran 2", "Bahis (TL)", "Geri Dönüş (TL)", "Kâr (TL)"]
    for j, h in enumerate(headers, 1):
        ws.cell(row=4, column=j, value=h)
    style_header(ws, len(headers), row=4)
    for i, r in enumerate(g.itertuples(index=False), start=5):
        reg = f"{int(r.reg_home)}-{int(r.reg_away)}"
        vals = [r.date, r.season, r.home, r.away, reg, "Evet" if r.went_ot else "Hayır",
                r.sonuc, r.o1, r.ox, r.o2, STAKE, round(r.geri_donus), round(r.kar)]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = BORDER
            c.alignment = Alignment(horizontal="left" if j in (3, 4) else "center")
            if j in (11, 12, 13):
                c.number_format = "#,##0"
            if j in (8, 9, 10):
                c.number_format = "0.00"
        if r.kazandi:
            ws.cell(row=i, column=7).font = Font(bold=True, color=GREEN)
        else:
            ws.cell(row=i, column=7).font = Font(bold=True, color=RED)
    for j, wdt in enumerate([11, 10, 28, 28, 11, 8, 11, 8, 8, 8, 11, 14, 12], 1):
        ws.column_dimensions[get_column_letter(j)].width = wdt
    ws.freeze_panes = "A5"
    if n:
        ws.auto_filter.ref = f"A4:M{n+4}"


def write_all_matches(wb, q):
    ws = wb.create_sheet("Tüm Filtreli Maçlar")
    headers = ["Tarih", "Lig", "Sezon", "Ev Sahibi", "Deplasman", "Normal Süre", "Uzatma",
               "Sonuç (1X2)", "MS Sonuç", "Oran 1", "Oran X", "Oran 2",
               "Bahis (TL)", "Geri Dönüş (TL)", "Kâr (TL)", "Bookmaker"]
    for j, h in enumerate(headers, 1):
        ws.cell(row=1, column=j, value=h)
    style_header(ws, len(headers), row=1)
    for i, r in enumerate(q.itertuples(index=False), start=2):
        vals = [r.date, r.league, r.season, r.home, r.away, f"{int(r.reg_home)}-{int(r.reg_away)}",
                "Evet" if r.went_ot else "Hayır", r.sonuc, r.ms, r.o1, r.ox, r.o2,
                STAKE, round(r.geri_donus), round(r.kar), r.n_books]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = BORDER
            if j in (13, 14, 15):
                c.number_format = "#,##0"
            if j in (10, 11, 12):
                c.number_format = "0.00"
    for j, wdt in enumerate([11, 22, 10, 28, 28, 11, 8, 11, 9, 8, 8, 8, 11, 14, 12, 9], 1):
        ws.column_dimensions[get_column_letter(j)].width = wdt
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:P{len(q)+1}"


def write_method(wb, tot, ml_tot):
    ws = wb.create_sheet("Yöntem")
    lines = [
        ("Kaynak", "Flashscore açık veri servisi (sonuç + kapanış oranları), 2016/17–2025/26 sezonları."),
        ("Kapsam", f"{tl(TOTAL_MATCHES)} maçtan {tl(int(TOTAL_MATCHES*COVERAGE/100))} tanesinde 1X2 oranı var "
                   f"(%{COVERAGE:.1f}); bunlardan {tl(tot['n'])} tanesi 2.25–4.00 bandında. "
                   "G League'de Flashscore 1X2 oranı yayınlamıyor (yalnızca moneyline, kısmi)."),
        ("Marj", f"Analizdeki maçların ortalama 1X2 overround'u %{MARGIN:.1f}. Bu, uzun vadeli kaybın ana kaynağı."),
        ("Piyasa", "1X2 — FULL_TIME (normal süre). Uzatma 1X2 sonucuna dahil değildir."),
        ("Filtre", "Ev sahibi (1) kapanış oranı 2.25 ≤ x ≤ 4.00."),
        ("Bahis", f"Her filtreli maça {tl(STAKE)} TL sabit bahis, ev sahibi galibiyetine (MS 1)."),
        ("Kazanç", "Kazanan bahis: 10.000 × oran; kaybeden: 0. Kâr = geri dönüş − 10.000."),
        ("Oran", "7 bookmaker (bwin, Interwetten, Oddset vb.) kapanış oranlarının medyanı; yoksa 20 bookmaker'lık GB setine düşülür."),
        ("Uzatma", "Normal süre skoru ilk 4 periyoddan hesaplanır. 5+ periyot = uzatma; 1X2 bahsi normal süreye göre değerlendirilir."),
        ("Örneklem", f"{tl(tot['n'])} filtreli maç · {tl(tot['staked'])} TL yatırılan · {tl(tot['profit'])} TL kâr/zarar · ROI {pct(tot['roi'])}"),
        ("ML karşılaştırma", f"Uzatma dahil moneyline (2.25–4.00): {tl(ml_tot['n'])} bahis · ROI {pct(ml_tot['roi'])}"),
        ("Uyarı", "Kapanış oranları geriye dönük en iyi tahmindir; gerçek bahis anındaki oran ve limitler farklı olabilir."),
        ("Üretim", datetime.now().strftime("%d.%m.%Y %H:%M")),
    ]
    ws["A1"] = "Yöntem ve Tanımlar"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    for i, (k, v) in enumerate(lines, start=3):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True)
        ws.cell(row=i, column=2, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 110


def write_generic_table(wb, title, dframe, widths=None):
    ws = wb.create_sheet(title)
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=13, color=NAVY)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(dframe.columns))
    for j, h in enumerate(dframe.columns, 1):
        ws.cell(row=3, column=j, value=h)
    style_header(ws, len(dframe.columns), row=3)
    for i, r in enumerate(dframe.itertuples(index=False), start=4):
        for j, v in enumerate(r, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.border = BORDER
            c.alignment = Alignment(horizontal="left" if j == 1 else "center")
            h = str(dframe.columns[j - 1])
            if "TL" in h or h in ("Yatırılan", "Kâr/Zarar", "Geri Dönüş"):
                c.number_format = "#,##0"
            elif h.endswith("%"):
                c.number_format = '0.0"%"'
            elif h == "Ort. Oran":
                c.number_format = "0.00"
            if h == "ROI %":
                c.font = Font(bold=True, color=GREEN if v >= 0 else RED)
    for j, w in enumerate(widths or ([18] + [12] * (len(dframe.columns) - 1)), 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = "A4"


def coverage_table(df):
    g = df.groupby("league").agg(total=("id", "count"), with_odds=("o1", "count")).reset_index()
    g["Kapsam %"] = (g.with_odds / g.total * 100).round(1)
    g = g.rename(columns={"league": "Lig", "total": "Toplam Maç", "with_odds": "1X2 Oranı Olan"})
    return g.sort_values("Toplam Maç", ascending=False)


def build_excel(q, summary, tot, ml_summary, ml_tot, bands, seasons, cover):
    wb = Workbook()
    wb.remove(wb.active)
    ws = write_summary_sheet(wb, summary, tot, "Özet — 1X2")
    # NCAA hariç duyarlılık satırı
    no_ncaa = q[q.league != "NCAA Division I"]
    if len(no_ncaa) and len(no_ncaa) != len(q):
        t2 = totals(no_ncaa)
        r = len(summary) + 8
        ws.cell(row=r, column=1, value="NCAA hariç toplam").font = Font(bold=True, italic=True)
        for j, v in [(2, t2["n"]), (3, t2["w"]), (4, t2["l"]), (5, round(t2["win_pct"], 1)),
                     (6, round(t2["avg_odds"], 2)), (7, round(t2["breakeven"], 1)),
                     (8, t2["staked"]), (9, t2["staked"] + t2["profit"]), (10, t2["profit"]),
                     (11, round(t2["roi"], 2)), (12, round(t2["se"], 2))]:
            c = ws.cell(row=r, column=j, value=v)
            c.font = Font(bold=True, italic=True)
            c.border = BORDER
            if j in (8, 9, 10):
                c.number_format = '#,##0 "TL"'
            if j in (5, 11):
                c.number_format = '0.00"%"'
            if j == 6:
                c.number_format = "0.00"
            if j == 12:
                c.number_format = '±0.00"%"'
    write_generic_table(wb, "Oran Bandı Analizi — 1X2", bands,
                        [16, 10, 10, 12, 11, 14, 14, 10])
    write_generic_table(wb, "Sezon Analizi — 1X2", seasons,
                        [14, 10, 10, 12, 11, 14, 14, 10])
    write_generic_table(wb, "Veri Kapsamı", cover, [26, 14, 18, 11])
    write_all_matches(wb, q)
    for lg, g in q.groupby("league", sort=False):
        write_league_sheet(wb, lg, g)
    write_summary_sheet(wb, ml_summary, ml_tot, "Özet — ML (Uzatma Dahil)", front=False)
    write_method(wb, tot, ml_tot)
    path = os.path.join(BASE, "basketball_1x2_rapor.xlsx")
    wb.save(path)
    return path


# ------------------------------------------------------------------ HTML
def html_report(q, summary, tot, ml_summary, ml_tot, bands, seasons):
    def row_class(v):
        return "pos" if v > 0 else ("neg" if v < 0 else "")

    srows = []
    for r in summary.itertuples(index=False):
        srows.append(
            f"<tr><td class='lig'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td>"
            f"<td>{r[4]:.1f}%</td><td>{r[5]:.2f}</td><td>{r[6]:.1f}%</td>"
            f"<td>{tl(r[7])}</td><td>{tl(r[8])}</td>"
            f"<td class='{row_class(r[9])}'><b>{tl(r[9])}</b></td>"
            f"<td class='{row_class(r[10])}'><b>{pct(r[10])}</b></td>"
            f"<td class='muted'>±{r[11]:.1f}</td></tr>"
        )

    details = []
    for lg, g in q.groupby("league", sort=False):
        n = len(g); w = int(g.kazandi.sum()); profit = float(g.kar.sum())
        rows = []
        for r in g.itertuples(index=False):
            res_cls = "pos" if r.kazandi else "neg"
            rows.append(
                f"<tr><td>{r.date}</td><td>{r.season}</td><td class='team'>{r.home}</td>"
                f"<td class='team'>{r.away}</td><td>{int(r.reg_home)}-{int(r.reg_away)}</td>"
                f"<td>{'UZ' if r.went_ot else ''}</td><td class='{res_cls}'>{r.sonuc}</td>"
                f"<td>{r.o1:.2f}</td><td>{r.ox:.2f}</td><td>{r.o2:.2f}</td>"
                f"<td>{tl(r.geri_donus)}</td><td class='{res_cls}'>{tl(r.kar)}</td></tr>"
            )
        details.append(f"""
        <details>
          <summary><span class="lgname">{lg}</span>
            <span class="meta">{n} maç · Kazanma {w/n*100:.1f}% · Ort. oran {g.o1.mean():.2f} ·
            <b class="{row_class(profit)}">{tl(profit)} TL</b> · ROI {pct(profit/(n*STAKE)*100)}</span>
          </summary>
          <div class="tablewrap"><table class="matches">
            <thead><tr><th>Tarih</th><th>Sezon</th><th>Ev</th><th>Deplasman</th><th>Normal Süre</th>
            <th>UZ</th><th>1X2</th><th>1</th><th>X</th><th>2</th><th>Geri Dönüş</th><th>Kâr</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table></div>
        </details>""")

    ml_rows = []
    for r in ml_summary.itertuples(index=False):
        ml_rows.append(
            f"<tr><td class='lig'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td>"
            f"<td>{r[4]:.1f}%</td><td>{r[5]:.2f}</td><td>{tl(r[7])}</td>"
            f"<td class='{row_class(r[9])}'><b>{tl(r[9])}</b></td>"
            f"<td class='{row_class(r[10])}'><b>{pct(r[10])}</b></td></tr>"
        )

    band_rows = []
    for r in bands.itertuples(index=False):
        band_rows.append(
            f"<tr><td class='lig'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]:.1f}%</td>"
            f"<td>{r[4]:.2f}</td><td>{tl(r[5])}</td>"
            f"<td class='{row_class(r[6])}'><b>{tl(r[6])}</b></td>"
            f"<td class='{row_class(r[7])}'><b>{pct(r[7])}</b></td></tr>"
        )

    max_abs = max([abs(x) for x in seasons["ROI %"]] + [1])
    season_bars = []
    for r in seasons.itertuples(index=False):
        roi = r[7]
        width = abs(roi) / max_abs * 100
        side = "right" if roi >= 0 else "left"
        color = "var(--green)" if roi >= 0 else "var(--red)"
        season_bars.append(
            f"<div class='barrow'><div class='barlbl'>{r[0]}</div>"
            f"<div class='bartrack'><div class='barfill' style='width:{width:.1f}%;background:{color};"
            f"margin-left:{0 if roi>=0 else 100-width:.1f}%'></div></div>"
            f"<div class='barval {row_class(roi)}'>{pct(roi)} <span>({tl(r[6])} TL · {r[1]} maç)</span></div></div>"
        )

    no_ncaa = q[q.league != "NCAA Division I"]
    t2 = totals(no_ncaa) if len(no_ncaa) else {"n": 0, "staked": 0, "profit": 0, "roi": 0}

    html = f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Basketbol 1X2 — Ev Sahibi 2.25–4.00 | 10.000 TL Backtest</title>
<style>
:root{{--navy:#1f2a44;--teal:#0f766e;--bg:#f6f8fb;--card:#fff;--line:#e2e8f0;--muted:#64748b;--green:#15803d;--red:#b91c1c}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:#0f172a}}
header{{background:linear-gradient(135deg,#1f2a44,#0f766e);color:#fff;padding:42px 28px 34px}}
header h1{{margin:0 0 8px;font-size:26px;letter-spacing:-.3px}}
header p{{margin:0;color:#cbd5e1;font-size:14px;line-height:1.6}}
.wrap{{max-width:1280px;margin:0 auto;padding:0 28px}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:-24px 0 26px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 16px;box-shadow:0 6px 18px rgba(15,23,42,.06)}}
.kpi .l{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700}}
.kpi .v{{font-size:23px;font-weight:800;margin-top:6px;letter-spacing:-.5px}}
.pos{{color:var(--green)}} .neg{{color:var(--red)}}
h2{{font-size:17px;margin:30px 0 12px;color:var(--navy)}}
.tablewrap{{overflow:auto;border:1px solid var(--line);border-radius:12px;background:#fff}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{position:sticky;top:0;background:var(--navy);color:#fff;text-align:left;padding:9px 10px;font-weight:600;white-space:nowrap;z-index:2}}
td{{padding:8px 10px;border-top:1px solid #eef2f7;white-space:nowrap}}
tbody tr:nth-child(even){{background:#fafcff}}
td.lig{{font-weight:700;color:var(--navy)}}
details{{background:#fff;border:1px solid var(--line);border-radius:12px;margin:10px 0;overflow:hidden}}
summary{{cursor:pointer;padding:14px 16px;display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}}
summary:hover{{background:#f8fafc}}
.lgname{{font-weight:800;color:var(--navy)}}
.meta{{color:var(--muted);font-size:12.5px}}
table.matches th{{background:#334155}}
table.matches td.team{{font-weight:600}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 16px;font-size:13px;color:#78350f;line-height:1.6;margin:18px 0}}
footer{{color:var(--muted);font-size:12px;padding:30px 0 50px;line-height:1.7}}
.barrow{{display:grid;grid-template-columns:120px 1fr 230px;gap:12px;align-items:center;margin:7px 0;font-size:12.5px}}
.bartrack{{height:14px;background:#eef2f7;border-radius:7px;overflow:hidden}}
.barfill{{height:100%;border-radius:7px}}
.barlbl{{font-weight:700;color:var(--navy)}}
.barval{{text-align:right}}
.barval span{{color:var(--muted);font-size:11px}}
.muted{{color:var(--muted)}}
@media(max-width:900px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.barrow{{grid-template-columns:90px 1fr}}}}
</style></head><body>
<header><div class="wrap">
<h1>Basketbol 1X2 — Ev Sahibi Oranı 2.25–4.00</h1>
<p>35 lig · son 10 sezon (2016/17–2025/26) · her filtreli maça <b>10.000 TL</b> ev sahibi galibiyeti bahsi · kapanış oranları</p>
</div></header>
<div class="wrap">
<div class="kpis">
  <div class="kpi"><div class="l">Filtreli maç</div><div class="v">{tl(tot['n'])}</div></div>
  <div class="kpi"><div class="l">Kazanma oranı</div><div class="v">{tot['win_pct']:.1f}%</div></div>
  <div class="kpi"><div class="l">Ortalama oran</div><div class="v">{tot['avg_odds']:.2f}</div></div>
  <div class="kpi"><div class="l">Yatırılan</div><div class="v">{tl(tot['staked'])} TL</div></div>
  <div class="kpi"><div class="l">Kâr / Zarar</div><div class="v {row_class(tot['profit'])}">{tl(tot['profit'])} TL</div></div>
</div>
<div class="note"><b>Nasıl okunmalı:</b> Başabaş kazanma oranı <b>{tot['breakeven']:.1f}%</b>; gerçekleşen <b>{tot['win_pct']:.1f}%</b>.
Fark, {pct(tot['roi'])} ROI'yi üretiyor. Ortalama 1X2 bookmaker marjı (overround) <b>%{MARGIN:.1f}</b>; yani uzun vadede bu marjı yenmeden kâr mümkün değil.
Toplam örneklemde ROI standart hatası ±{tot['se']:.1f} puandır (yaklaşık %95 güven aralığı ±{tot['se']*1.96:.1f} puan).
<br/><b>NCAA hariç:</b> {tl(t2['n'])} bahis · {tl(t2['staked'])} TL yatırılan · {tl(t2['profit'])} TL · ROI {pct(t2['roi'])}.</div>

<h2>Lig bazında özet</h2>
<div class="tablewrap"><table>
<thead><tr><th>Lig</th><th>Maç</th><th>Kazanan</th><th>Kaybeden</th><th>Kazanma %</th>
<th>Ort. Oran</th><th>Başabaş %</th><th>Yatırılan (TL)</th><th>Geri Dönüş (TL)</th><th>Kâr/Zarar (TL)</th><th>ROI</th><th>ROI ±</th></tr></thead>
<tbody>{''.join(srows)}</tbody></table></div>

<h2>Oran bandı dağılımı</h2>
<div class="tablewrap"><table>
<thead><tr><th>Oran Bandı</th><th>Maç</th><th>Kazanan</th><th>Kazanma %</th><th>Ort. Oran</th>
<th>Yatırılan (TL)</th><th>Kâr/Zarar (TL)</th><th>ROI</th></tr></thead>
<tbody>{''.join(band_rows)}</tbody></table></div>

<h2>Sezon bazında ROI</h2>
<div class="seasonbars">{''.join(season_bars)}</div>

<h2>Lig lig maç listeleri ({tl(tot['n'])} maç)</h2>
<p class="meta">Her lig başlığına tıklayarak o ligin filtreye giren tüm maçlarını açabilirsin.</p>
{''.join(details)}

<h2>Karşılaştırma — Moneyline (uzatma dahil)</h2>
<div class="tablewrap"><table>
<thead><tr><th>Lig</th><th>Maç</th><th>Kazanan</th><th>Kazanma %</th><th>Ort. Oran</th>
<th>Yatırılan (TL)</th><th>Kâr/Zarar (TL)</th><th>ROI</th></tr></thead>
<tbody>{''.join(ml_rows)}</tbody></table></div>
<p class="meta">ML toplamı: {tl(ml_tot['n'])} bahis · {tl(ml_tot['staked'])} TL yatırılan · {tl(ml_tot['profit'])} TL · ROI {pct(ml_tot['roi'])}</p>

<footer>
Kaynak: Flashscore açık veri servisi (sonuçlar + kapanış oranları). 1X2 piyasası normal süre (40/48 dk) sonucudur;
uzatma ayrı periyot olarak ayıklanmıştır. Oranlar 7 bookmaker kapanışının medyanıdır (yoksa 20 bookmaker seti).
G League'de 1X2 oranı yayınlanmadığı için 1X2 tablosu 34 lig içerir; moneyline tablosunda 35 lig vardır.
10.000 TL sabit bahis, bileşik getiri yok. Bu rapor yatırım tavsiyesi değildir.
<br/>Üretim: {datetime.now().strftime('%d.%m.%Y %H:%M')}
</footer>
</div></body></html>"""
    path = os.path.join(BASE, "rapor.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def main():
    global MARGIN, COVERAGE, TOTAL_MATCHES
    df = load()
    TOTAL_MATCHES = len(df)
    m3 = df.dropna(subset=["o1", "ox", "o2"])
    MARGIN = float(((1 / m3.o1 + 1 / m3.ox + 1 / m3.o2 - 1) * 100).mean()) if len(m3) else 0.0
    COVERAGE = float(df.o1.notna().mean() * 100) if len(df) else 0.0
    q = prepare(df)
    summary = summarize(q)
    tot = totals(q)
    bands = band_table(q)
    seasons = season_table(q)

    ml = df[(df.ml1 >= LO) & (df.ml1 <= HI)].copy()
    ml["bahis"] = STAKE
    ml["kazandi"] = ml.home_score > ml.away_score
    ml["geri_donus"] = ml.apply(lambda r: STAKE * r.ml1 if r.kazandi else 0.0, axis=1)
    ml["kar"] = ml.geri_donus - ml.bahis
    ml_summary = summarize(ml, "ml1")
    ml_tot = totals(ml, "ml1")

    q.to_csv(os.path.join(BASE, "tum_filtreli_maclar.csv"), index=False, encoding="utf-8-sig")
    summary.to_csv(os.path.join(BASE, "lig_ozet.csv"), index=False, encoding="utf-8-sig")
    cover = coverage_table(df)
    xlsx = build_excel(q, summary, tot, ml_summary, ml_tot, bands, seasons, cover)
    html = html_report(q, summary, tot, ml_summary, ml_tot, bands, seasons)
    print("OK", xlsx, html, len(q), "matches")


if __name__ == "__main__":
    main()
