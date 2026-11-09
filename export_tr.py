import sqlite3, pandas as pd, numpy as np
c = sqlite3.connect(r"D:\basketball_odds\data.sqlite3")
df = pd.read_sql_query("""SELECT league, season, date, home, away, home_score, away_score,
                                 reg_home, reg_away, went_ot, o1, ox, o2, ml1, ml2, n_books
                          FROM matches WHERE status='finished' AND reg_home IS NOT NULL""", c)
df["sonuc"] = np.where(df.reg_home > df.reg_away, "1", np.where(df.reg_home == df.reg_away, "X", "2"))
df["ms"] = np.where(df.home_score > df.away_score, "1", np.where(df.home_score == df.away_score, "X", "2"))
q = df[(df.o1 >= 2.25) & (df.o1 <= 4)].copy()
q["kazandi"] = q.sonuc == "1"
q["bahis"] = 10000
q["geri_donus"] = np.where(q.kazandi, q.bahis*q.o1, 0)
q["kar"] = q.geri_donus - q.bahis
ret = np.where(q.kazandi, q.o1-1, -1.0)
se = ret.std(ddof=1)/np.sqrt(len(ret))*100
print("n", len(q), "profit", q.kar.sum(), "roi", q.kar.sum()/(len(q)*10000)*100, "se", se)
print("return", q.geri_donus.sum())

out = pd.DataFrame({
    "Tarih": q.date, "Lig": q.league, "Sezon": q.season,
    "Ev Sahibi": q.home, "Deplasman": q.away,
    "Normal Süre": q.reg_home.astype(int).astype(str) + "-" + q.reg_away.astype(int).astype(str),
    "Uzatma": np.where(q.went_ot == 1, "Evet", "Hayır"),
    "1X2 Sonuç": q.sonuc, "MS Sonuç": q.ms,
    "Oran 1": q.o1, "Oran X": q.ox, "Oran 2": q.o2,
    "Bahis (TL)": q.bahis, "Geri Dönüş (TL)": q.geri_donus.round(0), "Kâr (TL)": q.kar.round(0),
    "Bookmaker": q.n_books,
})
out.to_csv(r"D:\basketball_odds\tum_filtreli_maclar_TL.csv", index=False, encoding="utf-8-sig")
print("csv written", len(out))
