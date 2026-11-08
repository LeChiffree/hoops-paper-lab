"""Lig adÄ± canonical haritasÄ± + filtre Ã¶zeti."""
import re
import unicodedata
import pandas as pd

P = r"D:\basketball_odds\aiscore_all_matches_final.csv"

MAP = {
    # Italy
    "Italian Lega Basket Serie A": "Ä°talya Serie A (LBA)",
    "Lega Basket Serie A": "Ä°talya Serie A (LBA)",
    "Lega Nazionale Pallacanestro Serie A2": "Ä°talya Serie A2",
    "Serie B Basket": "Ä°talya Serie B",
    "Serie B Baske": "Ä°talya Serie B",
    "Italy Serie B": "Ä°talya Serie B",
    "Lega Basket Serie A Women": "Ä°talya Serie A KadÄ±n",
    "Italy Women A2": "Ä°talya A2 KadÄ±n",
    "Italy A2 Women": "Ä°talya A2 KadÄ±n",
    # Turkey
    "Basketbol Super Ligi": "TÃ¼rkiye SÃ¼per Ligi (BSL)",
    "Turkish Basketball First League": "TÃ¼rkiye TBL",
    "Turkey Basketball 2 liga\t": "TÃ¼rkiye TB2L",
    "Turkish Women's Basketball Super League": "TÃ¼rkiye KadÄ±n SÃ¼per Ligi",
    "Turkey Women's TKBL": "TÃ¼rkiye KadÄ±n TBL",
    # Spain
    "Liga Endesa": "Ä°spanya Liga ACB",
    "ACB League": "Ä°spanya Liga ACB",
    "Spain Primera FEB": "Ä°spanya Primera FEB",
    "Spain Segunda FEB": "Ä°spanya Segunda FEB",
    "Spain Tercera FEB": "Ä°spanya Tercera FEB",
    "Liga EBA": "Ä°spanya Liga EBA",
    "LEB Plata": "Ä°spanya LEB Plata",
    "Liga Femenina de Baloncesto": "Ä°spanya Liga Femenina",
    "Spain Women's Liga 2": "Ä°spanya KadÄ±n Liga 2",
    "Spain LF Challenge Women": "Ä°spanya LF Challenge KadÄ±n",
    # France
    "France Ligue Nationale de Basket": "Fransa Pro A",
    "French Ligue Nationale de Basket Pro B": "Fransa Pro B",
    "Nationale 1": "Fransa Nationale 1",
    "France Nationale 1": "Fransa Nationale 1",
    "Ligue Feminine de Basketball": "Fransa LFB KadÄ±n",
    "France Women's LF2": "Fransa LF2 KadÄ±n",
    # Germany
    "Basketball Bundesliga": "Almanya BBL",
    "German Basketball Pro A": "Almanya Pro A",
    "German Pro B": "Almanya Pro B",
    "Pro B South": "Almanya Pro B",
    "Pro B North": "Almanya Pro B",
    "German Womenâ€™s Basketball Bundesliga": "Almanya KadÄ±n BBL",
    # Greece
    "Greek Basket League": "Yunanistan Basket League",
    "Greece A2": "Yunanistan A2",
    "Greek A2 Basket League": "Yunanistan A2",
    "Greek Women's Basketball League": "Yunanistan KadÄ±n Ligi",
    # Russia
    "Basketball Super League": "Rusya SÃ¼per Ligi",
    "Russia VTB United League": "VTB United League",
    "Basketball Cup": "Rusya KupasÄ±",
    # Israel
    "Israel Basketball Super League": "Ä°srail SÃ¼per Ligi",
    "Israel Basketball  League": "Ä°srail SÃ¼per Ligi",
    # Lithuania
    "krepsinio lyga": "Litvanya LKL",
    "Nacionaline Krepsinio Lyga": "Litvanya NKL",
    "National krepÅ¡inis League": "Litvanya NKL",
    # Poland
    "Polska Liga KoszykÃ³wki": "Polonya PLK",
    "Poland 1st Division": "Polonya 1. Lig",
    "Poland 1 Liga": "Polonya 1. Lig",
    "Poland 2 Liga": "Polonya 2. Lig",
    "Women's Liga KoszykÃ³wki Kobiet": "Polonya KadÄ±n Ligi",
    "Poland 1 Liga Women": "Polonya KadÄ±n 1. Lig",
    # Brazil
    "Novo Basquete Brasil": "Brezilya NBB",
    "BRA  League": "Brezilya NBB",
    "Brazil Liga Ouro": "Brezilya Liga Ouro",
    "Brazil Liga Feminina de Basquete": "Brezilya KadÄ±n Ligi",
    # Argentina
    "Argentinian Liga Nacional de Bosquetbol": "Arjantin Liga Nacional",
    "Argentina Liga Nacional": "Arjantin Liga Nacional",
    "Argentina La Liga": "Arjantin Liga Nacional",
    "Argentina Liga B": "Arjantin Liga B",
    "LDD": "Arjantin LDD",
    # Japan
    "B.League Premier": "Japonya B.League Premier",
    "B.League One": "Japonya B.League One",
    "B.League Next": "Japonya B.League Next",
    "Women's Basketball League": "Japonya W League",
    # Korea
    "Korean Basketball League": "KBL",
    "Women's Korean Basketball League": "WKBL",
    # China / Taiwan
    "China Basketball Association": "CBA",
    "Women's Basketball Association": "WCBA",
    "National Basketball League": "Ã‡in NBL",
    "Super Basketball League": "Ã‡in Taipei SBL",
    "Taipei P League": "Ã‡in Taipei P.League",
    "China Taipei Professional Basketball League": "Ã‡in Taipei TPBL",
    "China Taiwan T1 League": "Ã‡in Taipei T1",
    # USA
    "National Collegiate Athletic Association": "NCAA",
    "Women's National Collegiate Athletic Association": "NCAA KadÄ±n",
    "WNCAA": "NCAA KadÄ±n",
    "WNCAAB": "NCAA KadÄ±n",
    "National Basketball Association": "NBA",
    "Womenâ€™s National Basketball Association": "WNBA",
    # Europe
    "EuroCup Basketball": "EuroCup",
    "Adriatic Basketball Association League": "ABA League",
    "BNXT": "BNXT League",
    # International
    "Club Friendship": "HazÄ±rlÄ±k MaÃ§larÄ±",
}


def canon(name):
    n = str(name).strip()
    return MAP.get(n, n)


def main():
    d = pd.read_csv(P, usecols=["date", "league", "country", "status_text", "ml_home", "home_score"], low_memory=False)
    d = d[(d.status_text == "finished") & d.ml_home.notna() & (d.ml_home >= 2.25) & (d.ml_home <= 4) & d.home_score.notna()].copy()
    d["canon"] = d.league.map(canon)
    g = d.groupby(["canon", "country"]).size().reset_index(name="n").sort_values("n", ascending=False)
    g.to_csv(r"D:\basketball_odds\canonical_leagues.csv", index=False, encoding="utf-8-sig")
    print("rows", len(d), "canon", d.canon.nunique())
    print(g.head(80).to_string(index=False))


if __name__ == "__main__":
    main()
