"""2-8 Kasım 2026 maçlarını parse et, filtrele."""
import os
import sys
import pandas as pd

BASE = r"D:\basketball_odds"
sys.path.insert(0, BASE)
from aiscore_bulk_parse import parse_day, COLUMNS
from canonical import MAP
from scope_check import INC

DAYS = ["20261102", "20261103", "20261104", "20261105", "20261106", "20261107", "20261108"]

rows = []
for d in DAYS:
    p = os.path.join(BASE, "raw", f"day_{d}.bin")
    r = parse_day(p)
    print(d, len(r), "matches")
    rows += r

df = pd.DataFrame(rows).reindex(columns=COLUMNS)
df["canon"] = df.league.map(lambda x: MAP.get(str(x).strip(), str(x).strip()))
df["key"] = list(zip(df.country.fillna(""), df.canon))
df["Lig"] = df.key.map(INC)
fin = df[df.status_text == "finished"].copy()
print("\ntoplam:", len(df), "bitmiş:", len(fin), "lig eşleşen:", fin.Lig.notna().sum())

inc = fin[fin.Lig.notna()].copy()
print("kapsam içi bitmiş:", len(inc))
print("oranı olan:", inc.ml_home.notna().sum())

filt = inc[(inc.ml_home >= 2.25) & (inc.ml_home <= 4)].copy()
filt["Kazandi"] = filt.home_score > filt.away_score
filt["Kar"] = (filt.ml_home - 1) * 250 * filt.Kazandi - 250 * (~filt.Kazandi)
print("\nfiltreye giren:", len(filt))
print("berabere (uzatma kontrolü gerekli):", int((filt.home_score == filt.away_score).sum()))
print(filt.groupby("Lig").size().sort_values(ascending=False).to_string())

filt.to_csv(os.path.join(BASE, "kasim_2026_filtre.csv"), index=False, encoding="utf-8-sig")
print("\n-> kasim_2026_filtre.csv")
