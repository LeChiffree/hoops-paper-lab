"""tie_*.bin detaylarını büyük CSV'ye uygula + tie_status üret."""
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb_decode import try_msg, read_varint

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
IN = os.path.join(BASE, "aiscore_all_matches.csv")
OUT = os.path.join(BASE, "aiscore_all_matches_fixed.csv")


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


def detail(path):
    b = open(path, "rb").read()
    wrapper = [v for f, t, v in try_msg(b) if f == 15]
    if not wrapper:
        return None
    w = try_msg(wrapper[0])
    match = [v for f, t, v in w if f == 1]
    if not match:
        return None
    d = fld(match[0])
    def per(key):
        arr = packed(d.get(key, b""))
        if arr and arr[-1] == 0:
            arr = arr[:-1]
        return [x / 2 for x in arr]
    hp, ap = per(12), per(13)
    if not hp or not ap:
        return None
    return sum(hp), sum(ap), hp, ap


def main():
    fixes = {}
    for p in glob.glob(os.path.join(RAW, "tie_*.bin")):
        mid = os.path.basename(p)[4:-4]
        got = detail(p)
        if got:
            fixes[mid] = got

    tie_ids = set(json.load(open(os.path.join(BASE, "tie_ids.json")))) if os.path.exists(os.path.join(BASE, "tie_ids.json")) else set()
    print("fixes:", len(fixes), "tie ids:", len(tie_ids))

    stats = {"fixed": 0, "unresolved_ot": 0, "missing_score": 0, "no_detail": 0}
    with open(IN, "r", encoding="utf-8-sig", newline="") as fin, \
         open(OUT, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.DictReader(fin)
        fields = list(reader.fieldnames) + ["tie_fixed", "tie_verified", "tie_status"]
        writer = csv.DictWriter(fout, fieldnames=fields)
        writer.writeheader()
        rows = 0
        for row in reader:
            rows += 1
            mid = row.get("match_id")
            status = ""
            fixed = 0
            verified = ""
            if mid in tie_ids:
                h0 = float(row["home_score"]) if row.get("home_score") not in ("", None) else None
                a0 = float(row["away_score"]) if row.get("away_score") not in ("", None) else None
                if h0 == 0 and a0 == 0:
                    status = "missing_score"
                elif mid in fixes:
                    h, a, hp, ap = fixes[mid]
                    if h != a:
                        row["home_score"] = h
                        row["away_score"] = a
                        row["periods"] = max(len(hp), len(ap))
                        for i in range(6):
                            row[f"h_q{i+1}"] = hp[i] if i < len(hp) else ""
                            row[f"a_q{i+1}"] = ap[i] if i < len(ap) else ""
                        fixed = 1
                        status = "fixed"
                    else:
                        verified = 1
                        status = "unresolved_ot"
                else:
                    status = "no_detail"
                stats[status] = stats.get(status, 0) + 1
            row["tie_fixed"] = fixed
            row["tie_verified"] = verified
            row["tie_status"] = status
            writer.writerow(row)
            if rows % 100000 == 0:
                print("  ", rows, flush=True)
    print("rows", rows)
    print(stats)
    print("->", OUT)


if __name__ == "__main__":
    main()
