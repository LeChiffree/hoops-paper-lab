"""Flashscore'dan bulunan uzatma skorlarını ana CSV'ye uygula."""
import csv
import os
from difflib import SequenceMatcher
import re
import unicodedata

import pandas as pd

BASE = r"D:\basketball_odds"
IN = os.path.join(BASE, "aiscore_all_matches_fixed.csv")
OUT = os.path.join(BASE, "aiscore_all_matches_final.csv")
FIX = os.path.join(BASE, "flashscore_tie_fix.csv")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def sim(a, b):
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def main():
    fixes = {}
    if os.path.exists(FIX):
        d = pd.read_csv(FIX, dtype=str)
        for r in d.itertuples(index=False):
            try:
                h, a = [int(x) for x in str(r.fs_score).split("-")]
            except Exception:
                continue
            if h == a:
                continue
            # yön kontrolü
            if sim(r.fs_home, r.home) >= sim(r.fs_home, r.away):
                pass
            else:
                h, a = a, h
            fixes[str(r.match_id)] = (h, a)

    print("fixes:", len(fixes))
    stats = {"fixed_fs": 0, "unresolved_ot": 0, "missing_score": 0}
    with open(IN, "r", encoding="utf-8-sig", newline="") as fin, \
         open(OUT, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.DictReader(fin)
        fields = list(reader.fieldnames)
        writer = csv.DictWriter(fout, fieldnames=fields)
        writer.writeheader()
        n = 0
        for row in reader:
            n += 1
            mid = row.get("match_id")
            if mid in fixes:
                h, a = fixes[mid]
                row["home_score"] = h
                row["away_score"] = a
                row["tie_fixed"] = 1
                row["tie_verified"] = 1
                row["tie_status"] = "fixed_fs"
                stats["fixed_fs"] += 1
            elif row.get("tie_status"):
                stats[row["tie_status"]] = stats.get(row["tie_status"], 0) + 1
            writer.writerow(row)
            if n % 100000 == 0:
                print("  ", n, flush=True)
    print("rows", n, stats)
    print("->", OUT)


if __name__ == "__main__":
    main()
