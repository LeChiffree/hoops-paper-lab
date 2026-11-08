"""Matched Ã§iftler iÃ§in Flashscore moneyline oranÄ±nÄ± Ã§ek, AiScore ile karÅŸÄ±laÅŸtÄ±r."""
import sys, statistics
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore.fetch import get_graphql_optional

BASE = r"D:\basketball_odds"
pairs = pd.read_csv(f"{BASE}\\crosscheck_matches.csv")
days = pd.read_csv(f"{BASE}\\flashscore_days.csv").drop_duplicates("fs_id")
pid = days.set_index("fs_id")[["home_pid", "away_pid"]].to_dict("index")


def sf(v):
    try:
        x = float(v)
        return x if x > 1.0 else None
    except (TypeError, ValueError):
        return None


def med(v):
    v = [x for x in v if x]
    return round(statistics.median(v), 3) if v else None


def fetch(row):
    fs_id = row.fs_id
    info = pid.get(fs_id, {})
    sides = {}
    if info.get("home_pid"):
        sides[info["home_pid"]] = "home"
    if info.get("away_pid"):
        sides[info["away_pid"]] = "away"
    for geo in ("DE", "GB"):
        try:
            payload = get_graphql_optional(
                "oce", {"eventId": fs_id, "projectId": 2, "geoIpCode": geo, "geoIpSubdivisionCode": ""},
                odds=True) or {}
        except Exception:
            payload = {}
        h = payload.get("findOddsByEventId") or {}
        home, away = [], []
        home_o, away_o = [], []
        for row2 in h.get("odds") or []:
            if row2.get("bettingType") != "HOME_AWAY" or row2.get("bettingScope") != "FULL_TIME_OVER_TIME":
                continue
            sel = row2.get("odds") or []
            if len(sel) != 2:
                continue
            vals, opens = {}, {}
            for o in sel:
                side = sides.get(o.get("eventParticipantId"))
                v = sf(o.get("value"))
                ov = sf(o.get("opening"))
                if side and v:
                    vals[side] = v
                if side and ov:
                    opens[side] = ov
            if "home" in vals and "away" in vals:
                home.append(vals["home"]); away.append(vals["away"])
                if "home" in opens and "away" in opens:
                    home_o.append(opens["home"]); away_o.append(opens["away"])
            else:
                a, b = sf(sel[0].get("value")), sf(sel[1].get("value"))
                if a and b:
                    home.append(a); away.append(b)
        if home:
            return fs_id, med(home), med(away), geo, med(home_o), med(away_o)
    return fs_id, None, None, None, None, None


rows = list(pairs.itertuples(index=False))
with ThreadPoolExecutor(max_workers=24) as ex:
    res = list(ex.map(fetch, rows))
mp = {r[0]: r[1:] for r in res}

out = pairs.copy()
out["fs_ml_home"] = out.fs_id.map(lambda x: mp.get(x, (None, None, None, None, None))[0])
out["fs_ml_away"] = out.fs_id.map(lambda x: mp.get(x, (None, None, None, None, None))[1])
out["geo"] = out.fs_id.map(lambda x: mp.get(x, (None, None, None, None, None))[2])
out["fs_open_home"] = out.fs_id.map(lambda x: mp.get(x, (None, None, None, None, None))[3])
out["fs_open_away"] = out.fs_id.map(lambda x: mp.get(x, (None, None, None, None, None))[4])
out.to_csv(f"{BASE}\\crosscheck_odds.csv", index=False, encoding="utf-8-sig")

ok = out.dropna(subset=["ml_home_ai", "fs_ml_home", "ml_away_ai", "fs_ml_away"])
print("pairs", len(out), "both odds", len(ok))
if len(ok):
    dh = (ok.ml_home_ai - ok.fs_ml_home).abs()
    da = (ok.ml_away_ai - ok.fs_ml_away).abs()
    print("home MAE", round(dh.mean(), 4), "median", round(dh.median(), 4))
    print("away MAE", round(da.mean(), 4), "median", round(da.median(), 4))
    print("within 0.05:", round((dh <= 0.05).mean() * 100, 1), "%")
    print("within 0.10:", round((dh <= 0.10).mean() * 100, 1), "%")
    print("corr home:", round(ok.ml_home_ai.corr(ok.fs_ml_home), 4))
    print("avg AI/FS home:", round((ok.ml_home_ai / ok.fs_ml_home).mean(), 4))
    print("favorite side same:", round(((ok.ml_home_ai < ok.ml_away_ai) == (ok.fs_ml_home < ok.fs_ml_away)).mean() * 100, 1), "%")

    op = ok.dropna(subset=["fs_open_home"])
    if len(op):
        dho = (op.ml_home_ai - op.fs_open_home).abs()
        print("\nopening comparison n=", len(op))
        print("home MAE vs opening", round(dho.mean(), 4), "median", round(dho.median(), 4))
        print("corr vs opening:", round(op.ml_home_ai.corr(op.fs_open_home), 4))
        print("AI closer to opening than closing:", round((dho < (op.ml_home_ai - op.fs_ml_home).abs()).mean() * 100, 1), "%")

    clean = ok[(ok.score_ai == ok.score_fs) & (ok.ml_home_ai.notna())]
    if len(clean):
        d2 = (clean.ml_home_ai - clean.fs_ml_home).abs()
        print("\nscore-matched only n=", len(clean))
        print("home MAE", round(d2.mean(), 4), "median", round(d2.median(), 4),
              "within 0.10", round((d2 <= 0.10).mean() * 100, 1), "%",
              "corr", round(clean.ml_home_ai.corr(clean.fs_ml_home), 4))
