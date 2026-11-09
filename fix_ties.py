"""AiScore berabere görünen maçları /match/data ile düzelt."""
import glob
import os
import re
import pandas as pd

import sys
sys.path.insert(0, r"D:\basketball_odds")
from pb_decode import try_msg, read_varint

BASE = r"D:\basketball_odds"
RAW = os.path.join(BASE, "raw")


def fld(msg):
    return {f: v for f, t, v in (try_msg(msg) or [])}


def packed(bb):
    out, i = [], 0
    try:
        while i < len(bb):
            x, i = read_varint(bb, i)
            out.append(x)
    except Exception:
        return []
    return out


def detail_score(path):
    b = open(path, "rb").read()
    wrapper = [v for f, t, v in try_msg(b) if f == 15]
    if not wrapper:
        return None
    w = try_msg(wrapper[0])
    match = [v for f, t, v in w if f == 1]
    if not match:
        return None
    d = fld(match[0])
    def periods(key):
        arr = packed(d.get(key, b""))
        if arr and arr[-1] == 0:
            arr = arr[:-1]
        return [x / 2 for x in arr]
    hp, ap = periods(12), periods(13)
    if not hp or not ap:
        return None
    return sum(hp), sum(ap), hp, ap


rows = []
for p in glob.glob(os.path.join(RAW, "tie_*.bin")):
    mid = os.path.basename(p)[4:-4]
    got = detail_score(p)
    rows.append({"match_id": mid, "fix_home": got[0] if got else None,
                 "fix_away": got[1] if got else None,
                 "periods_home": len(got[2]) if got else None,
                 "periods_away": len(got[3]) if got else None})
fix = pd.DataFrame(rows)

ai = pd.read_csv(os.path.join(BASE, "aiscore_matches.csv"))
old_ties = ai[(ai.status == 3) & ai.home_score.notna() & (ai.home_score == ai.away_score)]
print("list-feed ties:", len(old_ties), "| details fetched:", len(fix))

merged = old_ties.merge(fix, on="match_id", how="left")
still_tie = merged[(merged.fix_home == merged.fix_away) | merged.fix_home.isna()]
print("still tie / no detail:", len(still_tie))
print("OT periods found (5+):", int((merged.periods_home >= 5).sum()))

# tüm maç tablosuna uygula
ai2 = ai.merge(fix, on="match_id", how="left")
mask = ai2.fix_home.notna()
ai2.loc[mask, "home_score"] = ai2.loc[mask, "fix_home"]
ai2.loc[mask, "away_score"] = ai2.loc[mask, "fix_away"]
ai2.loc[mask, "h_q5"] = ai2.loc[mask, "h_q5"].fillna(0)
ai2.to_csv(os.path.join(BASE, "aiscore_fixed.csv"), index=False, encoding="utf-8-sig")
merged.to_csv(os.path.join(BASE, "aiscore_tie_fix.csv"), index=False, encoding="utf-8-sig")

print("\nfixed rows:", int(mask.sum()))
print("\nexamples:")
for r in merged.head(12).itertuples(index=False):
    print(f"  {r.date} {r.home[:24]:24s} vs {r.away[:24]:24s} | list {int(r.home_score)}-{int(r.away_score)} "
          f"-> detail {r.fix_home}-{r.fix_away} | periods {r.periods_home}")

# Flashscore karşılaştırması
cc = pd.read_csv(os.path.join(BASE, "crosscheck_matches.csv"))
cc = cc[cc.issue == "ot_missing"] if "issue" in cc.columns else cc
m = merged.merge(cc[["ai_id", "score_fs"]], left_on="match_id", right_on="ai_id", how="inner")
m["fixed_score"] = m.fix_home.astype("Int64").astype(str) + "-" + m.fix_away.astype("Int64").astype(str)
print("\nFlashscore ile karşılaştırma (OT vakaları):", len(m))
print("birebir tutan:", int((m.fixed_score == m.score_fs).sum()), "/", len(m))
for r in m[m.fixed_score != m.score_fs].itertuples(index=False):
    print("  fark:", r.home, r.away, "fixed", r.fixed_score, "FS", r.score_fs)
