"""raw/day_*.bin (AiScore günlük liste feed'i) -> büyük CSV.

Çıktı:
  aiscore_all_matches.csv   tüm maçlar (bitmiş + canlı + planlanmış)
  aiscore_ties.csv          bitmiş ama berabere görünenler (uzatma düzeltmesi için)
"""
import glob
import os
import sys
import datetime
import json

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb_decode import try_msg, read_varint

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
OUT = os.path.join(BASE, "aiscore_all_matches.csv")
TIES = os.path.join(BASE, "aiscore_ties.csv")

STATUS = {1: "scheduled", 2: "live", 3: "finished", 4: "postponed", 7: "cancelled", 8: "unknown"}

COLUMNS = ["date", "match_id", "league", "country", "home", "away", "status", "status_text",
           "start_ts", "start_time_utc",
           "h_q1", "h_q2", "h_q3", "h_q4", "h_q5", "h_q6",
           "a_q1", "a_q2", "a_q3", "a_q4", "a_q5", "a_q6",
           "periods", "home_score", "away_score",
           "ml_home", "ml_away", "spread_line", "spread_home", "spread_away",
           "total_line", "total_over", "total_under"]


def s(v):
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else v


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


def parse_day(path):
    day = os.path.basename(path).replace("day_", "").replace(".bin", "")
    b = open(path, "rb").read()
    wrapper = [v for f, t, v in try_msg(b) if f == 15]
    if not wrapper:
        return []
    w = try_msg(wrapper[0])

    teams, leagues, countries = {}, {}, {}
    for f, t, v in w:
        if f == 3:
            d = fld(v); teams[s(d.get(1))] = s(d.get(6))
        elif f == 1:
            d = fld(v)
            lid = s(d.get(1))
            leagues[lid] = s(d.get(5))
            c = fld(d.get(4, b""))
            countries[lid] = s(c.get(2))
    rows = []
    for f, t, v in w:
        if f != 2:
            continue
        d = fld(v)
        league_id = s(fld(d[4]).get(1)) if 4 in d else None
        home_id = s(fld(d[6]).get(1)) if 6 in d else None
        away_id = s(fld(d[7]).get(1)) if 7 in d else None
        def periods(key):
            arr = packed(d.get(key, b""))
            if arr and arr[-1] == 0:
                arr = arr[:-1]
            return [x / 2 for x in arr]
        hp, ap = periods(12), periods(13)
        status = d.get(24)
        row = {
            "date": day,
            "match_id": s(d.get(1)),
            "league": leagues.get(league_id),
            "country": countries.get(league_id),
            "home": teams.get(home_id),
            "away": teams.get(away_id),
            "status": status,
            "status_text": STATUS.get(status, "unknown"),
            "start_ts": d.get(15),
            "start_time_utc": None,
            "periods": None, "home_score": None, "away_score": None,
            "ml_home": None, "ml_away": None,
            "spread_line": None, "spread_home": None, "spread_away": None,
            "total_line": None, "total_over": None, "total_under": None,
        }
        if d.get(15):
            row["start_time_utc"] = datetime.datetime.utcfromtimestamp(d[15]).strftime("%Y-%m-%d %H:%M")
        for i in range(6):
            row[f"h_q{i+1}"] = hp[i] if i < len(hp) else None
            row[f"a_q{i+1}"] = ap[i] if i < len(ap) else None
        row["periods"] = len(hp)
        row["home_score"] = sum(hp) if hp else None
        row["away_score"] = sum(ap) if ap else None
        if d.get(30):
            groups = []
            for ff, tt, vv in (try_msg(fld(d[30]).get(7, b"")) or []):
                if ff != 1:
                    continue
                vals = [s(x) for x2, t2, x in (try_msg(vv) or [])]
                if len(vals) >= 2:
                    groups.append(vals)
            if len(groups) >= 3:
                def num(x):
                    try:
                        return float(x)
                    except (TypeError, ValueError):
                        return None
                sp, tw, tot = groups[0], groups[1], groups[2]
                row["ml_home"] = num(tw[0]); row["ml_away"] = num(tw[2])
                row["spread_line"] = num(sp[1]); row["spread_home"] = num(sp[0]); row["spread_away"] = num(sp[2])
                row["total_line"] = num(tot[1]); row["total_over"] = num(tot[0]); row["total_under"] = num(tot[2])
        rows.append(row)
    return rows


def main():
    files = sorted(glob.glob(os.path.join(RAW, "day_*.bin")))
    print("files:", len(files), flush=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    wrote = 0
    ties = []
    buf = []
    for i, p in enumerate(files, 1):
        try:
            rows = parse_day(p)
        except Exception as e:
            print("ERR", os.path.basename(p), type(e).__name__, e, flush=True)
            continue
        buf.extend(rows)
        for r in rows:
            if r["status"] == 3 and r["home_score"] is not None and r["home_score"] == r["away_score"]:
                ties.append(r)
        if len(buf) >= 20000:
            pd.DataFrame(buf).reindex(columns=COLUMNS).to_csv(OUT, mode="a", header=(wrote == 0), index=False, encoding="utf-8-sig")
            wrote += len(buf); buf = []
            print(f"  {i}/{len(files)} files, rows={wrote}", flush=True)
    if buf:
        pd.DataFrame(buf).reindex(columns=COLUMNS).to_csv(OUT, mode="a", header=(wrote == 0), index=False, encoding="utf-8-sig")
        wrote += len(buf)
    print("total rows:", wrote, "ties:", len(ties))
    pd.DataFrame(ties).to_csv(TIES, index=False, encoding="utf-8-sig")
    ids = [t["match_id"] for t in ties]
    with open(os.path.join(BASE, "tie_ids.json"), "w", encoding="utf-8") as f:
        json.dump(ids, f)
    print("tie ids ->", os.path.join(BASE, "tie_ids.json"))


if __name__ == "__main__":
    main()
