import pandas as pd
from canonical import MAP

P = r"D:\basketball_odds\aiscore_all_matches_final.csv"

# (country, canonical) -> gÃ¶rÃ¼nen ad
INC = {
 ("USA","NBA"): "NBA",
 ("USA","NCAA"): "NCAA",
 ("USA","NCAA KadÄ±n"): "NCAA KadÄ±n",
 ("USA","WNBA"): "WNBA",
 ("Europe","EuroLeague"): "EuroLeague",
 ("Europe","EuroCup"): "EuroCup",
 ("Europe","Basketball Champions League"): "Basketball Champions League",
 ("Europe","FIBA Europe Cup"): "FIBA Europe Cup",
 ("Europe","ABA League"): "ABA League",
 ("Europe","EuroLeague Women"): "EuroLeague KadÄ±n",
 ("Europe","EuroCup Women"): "EuroCup KadÄ±n",
 ("Europe","BNXT League"): "BNXT League",
 ("Spain","Ä°spanya Liga ACB"): "Ä°spanya Liga ACB",
 ("Spain","Ä°spanya Primera FEB"): "Ä°spanya Primera FEB",
 ("Spain","Ä°spanya Liga Femenina"): "Ä°spanya Liga Femenina",
 ("Italy","Ä°talya Serie A (LBA)"): "Ä°talya Serie A (LBA)",
 ("Italy","Ä°talya Serie A2"): "Ä°talya Serie A2",
 ("Italy","Ä°talya Serie A KadÄ±n"): "Ä°talya Serie A KadÄ±n",
 ("Turkey","TÃ¼rkiye SÃ¼per Ligi (BSL)"): "TÃ¼rkiye SÃ¼per Ligi (BSL)",
 ("Turkey","TÃ¼rkiye TBL"): "TÃ¼rkiye TBL",
 ("Turkey","TÃ¼rkiye KadÄ±n SÃ¼per Ligi"): "TÃ¼rkiye KadÄ±n SÃ¼per Ligi",
 ("France","Fransa Pro A"): "Fransa Pro A",
 ("France","Fransa Pro B"): "Fransa Pro B",
 ("France","Fransa LFB KadÄ±n"): "Fransa LFB KadÄ±n",
 ("Germany","Almanya BBL"): "Almanya BBL",
 ("Germany","Almanya Pro A"): "Almanya Pro A",
 ("Greece","Yunanistan Basket League"): "Yunanistan Basket League",
 ("Greece","Yunanistan A2"): "Yunanistan A2",
 ("Russia","Rusya SÃ¼per Ligi"): "Rusya SÃ¼per Ligi",
 ("Russia","VTB United League"): "VTB United League",
 ("Israel","Ä°srail SÃ¼per Ligi"): "Ä°srail SÃ¼per Ligi",
 ("Lithuania","Litvanya LKL"): "Litvanya LKL",
 ("Lithuania","Litvanya NKL"): "Litvanya NKL",
 ("Poland","Polonya PLK"): "Polonya PLK",
 ("Poland","Polonya 1. Lig"): "Polonya 1. Lig",
 ("Poland","Polonya KadÄ±n Ligi"): "Polonya KadÄ±n Ligi",
 ("Czech","Czech National Basketball League"): "Ã‡ekya NBL",
 ("Slovenia","Liga Nova KBM"): "Slovenya Liga Nova KBM",
 ("Croatia","Favbet Premijer liga"): "HÄ±rvatistan Premijer Liga",
 ("Serbia","Basketball League"): "SÄ±rbistan KLS",
 ("Hungary","Nemzeti BajnoksÃ¡g I/A"): "Macaristan NB I/A",
 ("Romania","Liga NaÈ›ionalÄƒ Baschet de Masculin"): "Romanya Liga NaÈ›ionalÄƒ",
 ("Bulgaria","Bulgaria National Basketball League"): "Bulgaristan NBL",
 ("Ukraine","Ukrainian Basketball SuperLeague"): "Ukrayna SÃ¼per Lig",
 ("Belgium","Basketball League Division I"): "BelÃ§ika Division I",
 ("Portugal","Liga Portuguesa de Basquetebol"): "Portekiz LPB",
 ("Switzerland","Swiss Basketball League"): "Ä°sviÃ§re SBL",
 ("Austria","Austrian Basketball Superliga"): "Avusturya SÃ¼per Lig",
 ("Finland","Korisliiga"): "Finlandiya Korisliiga",
 ("Sweden","Basketball League"): "Ä°sveÃ§ Basketligan",
 ("Denmark","Basketball League"): "Danimarka Basketligaen",
 ("Iceland","Iceland Basketball Premier League"): "Ä°zlanda Premier Lig",
 ("England","British Super League Basketball"): "Ä°ngiltere SÃ¼per Lig",
 ("Estonia","Estonia and Latvia Basketball League"): "Estonya/Letonya Ligi",
 ("Japan","Japonya B.League Premier"): "Japonya B.League Premier",
 ("Japan","Japonya B.League One"): "Japonya B.League One",
 ("South Korea","KBL"): "KBL",
 ("South Korea","WKBL"): "WKBL",
 ("China","CBA"): "CBA",
 ("China","WCBA"): "WCBA",
 ("China","Ã‡in Taipei P.League"): "Ã‡in Taipei P.League",
 ("China","Ã‡in Taipei TPBL"): "Ã‡in Taipei TPBL",
 ("China","Ã‡in Taipei T1"): "Ã‡in Taipei T1",
 ("Australia","Australia National Basketball League"): "Avustralya NBL",
 ("Australia","Womenâ€™s National Basketball League"): "Avustralya WNBL",
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
