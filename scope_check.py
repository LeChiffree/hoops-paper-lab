import pandas as pd
from canonical import MAP

P = r"D:\basketball_odds\aiscore_all_matches_final.csv"

# (country, canonical) -> görünen ad
INC = {
 ("USA","NBA"): "NBA",
 ("USA","NCAA"): "NCAA",
 ("USA","NCAA Kadın"): "NCAA Kadın",
 ("USA","WNBA"): "WNBA",
 ("Europe","EuroLeague"): "EuroLeague",
 ("Europe","EuroCup"): "EuroCup",
 ("Europe","Basketball Champions League"): "Basketball Champions League",
 ("Europe","FIBA Europe Cup"): "FIBA Europe Cup",
 ("Europe","ABA League"): "ABA League",
 ("Europe","EuroLeague Women"): "EuroLeague Kadın",
 ("Europe","EuroCup Women"): "EuroCup Kadın",
 ("Europe","BNXT League"): "BNXT League",
 ("Spain","İspanya Liga ACB"): "İspanya Liga ACB",
 ("Spain","İspanya Primera FEB"): "İspanya Primera FEB",
 ("Spain","İspanya Liga Femenina"): "İspanya Liga Femenina",
 ("Italy","İtalya Serie A (LBA)"): "İtalya Serie A (LBA)",
 ("Italy","İtalya Serie A2"): "İtalya Serie A2",
 ("Italy","İtalya Serie A Kadın"): "İtalya Serie A Kadın",
 ("Turkey","Türkiye Süper Ligi (BSL)"): "Türkiye Süper Ligi (BSL)",
 ("Turkey","Türkiye TBL"): "Türkiye TBL",
 ("Turkey","Türkiye Kadın Süper Ligi"): "Türkiye Kadın Süper Ligi",
 ("France","Fransa Pro A"): "Fransa Pro A",
 ("France","Fransa Pro B"): "Fransa Pro B",
 ("France","Fransa LFB Kadın"): "Fransa LFB Kadın",
 ("Germany","Almanya BBL"): "Almanya BBL",
 ("Germany","Almanya Pro A"): "Almanya Pro A",
 ("Greece","Yunanistan Basket League"): "Yunanistan Basket League",
 ("Greece","Yunanistan A2"): "Yunanistan A2",
 ("Russia","Rusya Süper Ligi"): "Rusya Süper Ligi",
 ("Russia","VTB United League"): "VTB United League",
 ("Israel","İsrail Süper Ligi"): "İsrail Süper Ligi",
 ("Lithuania","Litvanya LKL"): "Litvanya LKL",
 ("Lithuania","Litvanya NKL"): "Litvanya NKL",
 ("Poland","Polonya PLK"): "Polonya PLK",
 ("Poland","Polonya 1. Lig"): "Polonya 1. Lig",
 ("Poland","Polonya Kadın Ligi"): "Polonya Kadın Ligi",
 ("Czech","Czech National Basketball League"): "Çekya NBL",
 ("Slovenia","Liga Nova KBM"): "Slovenya Liga Nova KBM",
 ("Croatia","Favbet Premijer liga"): "Hırvatistan Premijer Liga",
 ("Serbia","Basketball League"): "Sırbistan KLS",
 ("Hungary","Nemzeti Bajnokság I/A"): "Macaristan NB I/A",
 ("Romania","Liga Națională Baschet de Masculin"): "Romanya Liga Națională",
 ("Bulgaria","Bulgaria National Basketball League"): "Bulgaristan NBL",
 ("Ukraine","Ukrainian Basketball SuperLeague"): "Ukrayna Süper Lig",
 ("Belgium","Basketball League Division I"): "Belçika Division I",
 ("Portugal","Liga Portuguesa de Basquetebol"): "Portekiz LPB",
 ("Switzerland","Swiss Basketball League"): "İsviçre SBL",
 ("Austria","Austrian Basketball Superliga"): "Avusturya Süper Lig",
 ("Finland","Korisliiga"): "Finlandiya Korisliiga",
 ("Sweden","Basketball League"): "İsveç Basketligan",
 ("Denmark","Basketball League"): "Danimarka Basketligaen",
 ("Iceland","Iceland Basketball Premier League"): "İzlanda Premier Lig",
 ("England","British Super League Basketball"): "İngiltere Süper Lig",
 ("Estonia","Estonia and Latvia Basketball League"): "Estonya/Letonya Ligi",
 ("Japan","Japonya B.League Premier"): "Japonya B.League Premier",
 ("Japan","Japonya B.League One"): "Japonya B.League One",
 ("South Korea","KBL"): "KBL",
 ("South Korea","WKBL"): "WKBL",
 ("China","CBA"): "CBA",
 ("China","WCBA"): "WCBA",
 ("China","Çin Taipei P.League"): "Çin Taipei P.League",
 ("China","Çin Taipei TPBL"): "Çin Taipei TPBL",
 ("China","Çin Taipei T1"): "Çin Taipei T1",
 ("Australia","Australia National Basketball League"): "Avustralya NBL",
 ("Australia","Women's National Basketball League"): "Avustralya WNBL",
 ("New Zealand","New Zealand National Basketball League"): "Yeni Zelanda NBL",
 ("Brazil","Brezilya NBB"): "Brezilya NBB",
 ("Argentina","Arjantin Liga Nacional"): "Arjantin Liga Nacional",
 ("Mexico","Liga Nacional de Baloncesto Profesional"): "Meksika LNBP",
}

d = pd.read_csv(P, usecols=["date","league","country","status_text","ml_home","home_score","away_score"], low_memory=False)
d = d[(d.status_text=="finished") & d.ml_home.notna() & (d.ml_home>=2.25) & (d.ml_home<=4) & d.home_score.notna()].copy()
d["canon"] = d.league.map(lambda x: MAP.get(str(x).strip(), str(x).strip()))
d["key"] = list(zip(d.country.fillna(""), d.canon))
d["display"] = d.key.map(INC)
f = d[d.display.notna()].copy()
print("filtered total:", len(d), "included:", len(f), f"({len(f)/len(d)*100:.1f}%)", "leagues:", f.display.nunique())
g = f.groupby("display").agg(n=("ml_home","size"), country=("country","first"),
                             y0=("date","min"), y1=("date","max")).sort_values("n", ascending=False)
print(g.to_string())
g.to_csv(r"D:\basketball_odds\dashboard_leagues.csv", encoding="utf-8-sig")
