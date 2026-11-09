"""2-8 Kasım filtrelenmiş maçları Flashscore günlük feed'iyle doğrula."""
import sys, re, statistics, unicodedata
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore import matches as M
from flashscore.fetch import get_graphql_optional

BASE = r"D:\basketball_odds"
DAYS = ["2026-11-02","2026-11-03","2026-11-04","2026-11-05","2026-11-06","2026-11-07","2026-11-08"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

def sim(a,b): return SequenceMatcher(None, norm(a), norm(b)).ratio()

rows=[]
for d in DAYS:
    r = M.get_matches("basketball", date=d, timezone=3)
    n=0
    for c in r["competitions"]:
        for m in c.get("matches") or []:
            rows.append({"date": m.get("date") or d, "fs_id": m.get("id"),
                         "home": (m.get("home") or {}).get("name"),
                         "away": (m.get("away") or {}).get("name"),
                         "hscore": m.get("home_score"), "ascore": m.get("away_score"),
                         "home_pid": m.get("home_pid"), "away_pid": m.get("away_pid")})
            n+=1
    print(d, n)
fs = pd.DataFrame(rows)
print("flashscore matches:", len(fs))

ai = pd.read_csv(f"{BASE}\\kasim_2026_filtre.csv")
ai["date"] = pd.to_datetime(ai.date.astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")

pairs=[]; used=set()
for ar in ai.itertuples(index=False):
    cand = fs[fs.date == ar.date]
    best=None
    for fr in cand.itertuples(index=False):
        if fr.fs_id in used: continue
        same = 0.5*sim(ar.home, fr.home)+0.5*sim(ar.away, fr.away)
        swap = 0.5*sim(ar.home, fr.away)+0.5*sim(ar.away, fr.home)
        sc=max(same,swap)
        if best is None or sc>best[0]: best=(sc,fr,swap>same)
    if best and best[0]>=0.75:
        sc,fr,sw = best; used.add(fr.fs_id)
        pairs.append({"date":ar.date,"ai_id":ar.match_id,"ai_home":ar.home,"ai_away":ar.away,
                      "ai_score":f"{int(ar.home_score)}-{int(ar.away_score)}","ai_odds":ar.ml_home,
                      "fs_id":fr.fs_id,"fs_home":fr.home,"fs_away":fr.away,
                      "fs_score":f"{fr.hscore}-{fr.ascore}","swapped":sw,"sim":round(sc,3),
                      "home_pid":fr.home_pid,"away_pid":fr.away_pid})
p=pd.DataFrame(pairs)
print("matched:", len(p), "of", len(ai), f"({len(p)/len(ai)*100:.1f}%)")
print("swapped:", int(p.swapped.sum()))

def sf(v):
    try:
        x=float(v); return x if x>1 else None
    except: return None
def med(v):
    v=[x for x in v if x]; return round(statistics.median(v),3) if v else None

def odds(row):
    sides={}
    if row.home_pid: sides[row.home_pid]="home"
    if row.away_pid: sides[row.away_pid]="away"
    for geo in ("DE","GB"):
        try:
            pl=get_graphql_optional("oce",{"eventId":row.fs_id,"projectId":2,"geoIpCode":geo,"geoIpSubdivisionCode":""},odds=True) or {}
        except: pl={}
        h=(pl.get("findOddsByEventId") or {})
        hh=[];aa=[]
        for r in h.get("odds") or []:
            if r.get("bettingType")!="HOME_AWAY" or r.get("bettingScope")!="FULL_TIME_OVER_TIME": continue
            sel=r.get("odds") or []
            if len(sel)!=2: continue
            vals={}
            for o in sel:
                side=sides.get(o.get("eventParticipantId")); v=sf(o.get("value"))
                if side and v: vals[side]=v
            if "home" in vals and "away" in vals:
                hh.append(vals["home"]);aa.append(vals["away"])
        if hh: return med(hh),med(aa)
    return None,None

with ThreadPoolExecutor(max_workers=12) as ex:
    res=list(ex.map(odds,p.itertuples(index=False)))
p["fs_home_odds"]=[x[0] for x in res]
p["fs_away_odds"]=[x[1] for x in res]
p["fs_home_odds_aligned"]=p.apply(lambda r: r.fs_away_odds if r.swapped else r.fs_home_odds, axis=1)
p["odds_diff"]=p.ai_odds-p.fs_home_odds_aligned

def hs(x): return int(float(str(x).split("-")[0]))
def as_(x): return int(float(str(x).split("-")[1]))
p["score_equal"]=p.apply(lambda r: (hs(r.ai_score),as_(r.ai_score))==((as_(r.fs_score),hs(r.fs_score)) if r.swapped else (hs(r.fs_score),as_(r.fs_score))), axis=1)
p.to_csv(f"{BASE}\\kasim_2026_crosscheck.csv", index=False, encoding="utf-8-sig")
print("score equal:", int(p.score_equal.sum()), f"({p.score_equal.mean()*100:.1f}%)")
od=p.dropna(subset=["odds_diff"])
print("odds n:",len(od),"MAE:",round(od.odds_diff.abs().mean(),3),"median:",round(od.odds_diff.abs().median(),3))
print("AI home odds vs FS aligned: corr", round(od.ai_odds.corr(od.fs_home_odds_aligned),3))
