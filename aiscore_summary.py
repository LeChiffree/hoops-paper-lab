"""Büyük CSV özeti: yıl, lig, kapsam."""
import os
import pandas as pd
from collections import Counter

BASE = r"D:\basketball_odds"
PATH = os.path.join(BASE, "aiscore_all_matches_fixed.csv")
if not os.path.exists(PATH):
    PATH = os.path.join(BASE, "aiscore_all_matches.csv")

years = Counter(); leagues = Counter(); status = Counter()
total = 0; finished = 0; with_score = 0; with_odds = 0; ties = 0
ids = set()
for ch in pd.read_csv(PATH, chunksize=200000, low_memory=False):
    total += len(ch)
    ids.update(ch.match_id.dropna().astype(str))
    years.update(ch.date.astype(str).str[:4])
    leagues.update(ch.league.fillna("?"))
    status.update(ch.status_text.fillna("?"))
    fin = ch[ch.status_text == "finished"]
    finished += len(fin)
    with_score += int(fin.home_score.notna().sum())
    with_odds += int(fin.ml_home.notna().sum())
    ties += int(((fin.home_score == fin.away_score) & fin.home_score.notna()).sum())

print("file:", PATH)
print("rows:", total, "unique ids:", len(ids))
print("status:", dict(status))
print("finished:", finished, "with score:", with_score, "with odds:", with_odds, "ties:", ties)
print("\nby year:")
for y in sorted(years):
    print(f"  {y}: {years[y]}")
print("\ntop leagues:")
for lg, n in leagues.most_common(25):
    print(f"  {n:7d}  {lg}")
