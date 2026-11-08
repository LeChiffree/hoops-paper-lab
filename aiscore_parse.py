"""AiScore protobuf list feed -> CSV.

Schema reverse-engineered from the live API:
  wrapper field 15
    1 = league  {1:id, 5:name, 4:country}
    2 = match   {1:id, 4:league_ref, 6:home_ref, 7:away_ref, 8:status,
                 12:home periods*2, 13:away periods*2, 15:start_ts, 24:status, 30:odds}
    3 = team    {1:id, 6:name, 19:slug}
  odds field 30 -> field 7 repeated group of 3 markets:
     [0] spread [home_odds, line, away_odds, ?]
     [1] to win [home_odds, 0, away_odds, 0]
     [2] total  [over_odds, line, under_odds, ?]
"""
import glob
import os
import sys
import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb_decode import try_msg, read_varint

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")


def s(v):
    return v.decode("utf-8", "replace") if isinstance(v, bytes) else v


def fld(msg):
    return {f: v for f, t, v in (try_msg(msg) or [])}


def packed(bb):
    out = []
    i = 0
    try:
        while i < len(bb):
            x, i = read_varint(bb, i)
            out.append(x)
    except Exception:
        return []
    return out


def market_groups(blob):
    """field 30 -> list of [string,string,string,string] groups."""
    d = fld(blob)
    groups = []
    for f, t, v in (try_msg(d.get(7, b"")) or []):
        if f != 1:
            continue
        vals = [s(x) for ff, tt, x in (try_msg(v) or [])]
        if len(vals) >= 2:
            groups.append(vals)
    return groups


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_file(path):
    day = os.path.basename(path).replace("api_", "").replace(".bin", "")
    b = open(path, "rb").read()
    wrapper = [v for f, t, v in try_msg(b) if f == 15]
    if not wrapper:
        return []
    w = try_msg(wrapper[0])

    teams, leagues = {}, {}
    for f, t, v in w:
        if f == 3:
            d = fld(v); teams[s(d.get(1))] = s(d.get(6))
        elif f == 1:
            d = fld(v); leagues[s(d.get(1))] = s(d.get(5))

    rows = []
    for f, t, v in w:
        if f != 2:
            continue
        d = fld(v)
        home_id = s(fld(d[6]).get(1)) if 6 in d else None
        away_id = s(fld(d[7]).get(1)) if 7 in d else None
        league_id = s(fld(d[4]).get(1)) if 4 in d else None
        hp = [x / 2 for x in packed(d.get(12, b""))[:-1]] if 12 in d else []
        ap = [x / 2 for x in packed(d.get(13, b""))[:-1]] if 13 in d else []
        m = {"date": day, "match_id": s(d.get(1)), "league": leagues.get(league_id),
             "home": teams.get(home_id), "away": teams.get(away_id),
             "status": d.get(24), "start_ts": d.get(15)}
        if d.get(15):
            m["start_time"] = datetime.datetime.utcfromtimestamp(d[15]).strftime("%Y-%m-%d %H:%M")
        for i in range(5):
            m[f"h_q{i+1}"] = hp[i] if i < len(hp) else None
            m[f"a_q{i+1}"] = ap[i] if i < len(ap) else None
        m["home_score"] = sum(hp) if hp else None
        m["away_score"] = sum(ap) if ap else None
        if d.get(30):
            gs = market_groups(d[30])
            if len(gs) >= 3:
                sp, tw, tot = gs[0], gs[1], gs[2]
                m["ml_home"] = num(tw[0]); m["ml_away"] = num(tw[2])
                m["spread_line"] = num(sp[1]); m["spread_home"] = num(sp[0]); m["spread_away"] = num(sp[2])
                m["total_line"] = num(tot[1]); m["total_over"] = num(tot[0]); m["total_under"] = num(tot[2])
        rows.append(m)
    return rows


def main():
    files = sorted(glob.glob(os.path.join(RAW, "api_2026*.bin")))
    rows = []
    for p in files:
        r = parse_file(p)
        print(f"{os.path.basename(p):20s} {len(r):4d} matches")
        rows.extend(r)
    df = pd.DataFrame(rows)
    out = os.path.join(BASE, "aiscore_matches.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print("\nrows", len(df), "->", out)
    print("status values:", df.status.value_counts().to_dict())
    print("with to-win odds:", df.ml_home.notna().sum())
    print("\nsample:")
    cols = ["date", "league", "home", "away", "home_score", "away_score", "ml_home", "ml_away", "spread_line", "total_line"]
    print(df[cols].head(12).to_string(index=False))

    ties = df[(df.status == 3) & df.home_score.notna() & (df.home_score == df.away_score)]
    print(f"\nbitmiş ama berabere görünen: {len(ties)} (bunlar /match/data ile zenginleştirilmeli)")
    if len(ties):
        print("tie_ids =", ties.match_id.tolist())


if __name__ == "__main__":
    main()
