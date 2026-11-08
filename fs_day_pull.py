"""Pull the same 7 days from Flashscore's daily schedule feed."""
import sys, os
import pandas as pd
sys.path.insert(0, r"C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper")
from flashscore import matches as M

BASE = r"D:\basketball_odds"
DAYS = ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29",
        "2026-10-30", "2026-10-31", "2026-11-01"]

rows = []
for d in DAYS:
    r = M.get_matches("basketball", date=d, timezone=3)
    n = 0
    for comp in r["competitions"]:
        c = comp.get("competition") or {}
        for m in comp.get("matches") or []:
            rows.append({
                "date": m.get("date") or d,
                "fs_id": m.get("id"),
                "league": c.get("display_name") or c.get("name"),
                "country": (c.get("country") or {}).get("name"),
                "home": (m.get("home") or {}).get("name"),
                "away": (m.get("away") or {}).get("name"),
                "home_score": m.get("home_score"),
                "away_score": m.get("away_score"),
                "status": m.get("status"),
                "periods": len(m.get("periods") or []),
                "home_pid": m.get("home_pid"),
                "away_pid": m.get("away_pid"),
                "start_time": m.get("start_time"),
            })
            n += 1
    print(f"{d}: {n} matches, {r['competition_count']} competitions")

df = pd.DataFrame(rows)
out = os.path.join(BASE, "flashscore_days.csv")
df.to_csv(out, index=False, encoding="utf-8-sig")
print("\ntotal", len(df), "->", out)
print("finished:", (df.status == "finished").sum())
