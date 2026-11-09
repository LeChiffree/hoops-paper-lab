"""Lig adı canonical haritası + filtre özeti."""
import re
import unicodedata
import pandas as pd

P = r"D:\basketball_odds\aiscore_all_matches_final.csv"

MAP = {
    # Italy
    "Italian Lega Basket Serie A": "İtalya Serie A (LBA)",
    "Lega Basket Serie A": "İtalya Serie A (LBA)",
    "Lega Nazionale Pallacanestro Serie A2": "İtalya Serie A2",
    "Serie B Basket": "İtalya Serie B",
    "Serie B Baske": "İtalya Serie B",
    "Italy Serie B": "İtalya Serie B",
    "Lega Basket Serie A Women": "İtalya Serie A Kadın",
    "Italy Women A2": "İtalya A2 Kadın",
    "Italy A2 Women": "İtalya A2 Kadın",
    # Turkey
    "Basketbol Super Ligi": "Türkiye Süper Ligi (BSL)",
    "Turkish Basketball First League": "Türkiye TBL",
    "Turkey Basketball 2 liga\t": "Türkiye TB2L",
    "Turkish Women's Basketball Super League": "Türkiye Kadın Süper Ligi",
    "Turkey Women's TKBL": "Türkiye Kadın TBL",
    # Spain
    "Liga Endesa": "İspanya Liga ACB",
    "ACB League": "İspanya Liga ACB",
    "Spain Primera FEB": "İspanya Primera FEB",
    "Spain Segunda FEB": "İspanya Segunda FEB",
    "Spain Tercera FEB": "İspanya Tercera FEB",
    "Liga EBA": "İspanya Liga EBA",
    "LEB Plata": "İspanya LEB Plata",
    "Liga Femenina de Baloncesto": "İspanya Liga Femenina",
    "Spain Women's Liga 2": "İspanya Kadın Liga 2",
    "Spain LF Challenge Women": "İspanya LF Challenge Kadın",
    # France
    "France Ligue Nationale de Basket": "Fransa Pro A",
    "French Ligue Nationale de Basket Pro B": "Fransa Pro B",
    "Nationale 1": "Fransa Nationale 1",
    "France Nationale 1": "Fransa Nationale 1",
    "Ligue Feminine de Basketball": "Fransa LFB Kadın",
    "France Women's LF2": "Fransa LF2 Kadın",
    # Germany
    "Basketball Bundesliga": "Almanya BBL",
    "German Basketball Pro A": "Almanya Pro A",
    "German Pro B": "Almanya Pro B",
    "Pro B South": "Almanya Pro B",
    "Pro B North": "Almanya Pro B",
    "German Women's Basketball Bundesliga": "Almanya Kadın BBL",
    # Greece
    "Greek Basket League": "Yunanistan Basket League",
    "Greece A2": "Yunanistan A2",
    "Greek A2 Basket League": "Yunanistan A2",
    "Greek Women's Basketball League": "Yunanistan Kadın Ligi",
    # Russia
    "Basketball Super League": "Rusya Süper Ligi",
    "Russia VTB United League": "VTB United League",
    "Basketball Cup": "Rusya Kupası",
    # Israel
    "Israel Basketball Super League": "İsrail Süper Ligi",
    "Israel Basketball  League": "İsrail Süper Ligi",
    # Lithuania
    "krepsinio lyga": "Litvanya LKL",
    "Nacionaline Krepsinio Lyga": "Litvanya NKL",
    "National krepšinis League": "Litvanya NKL",
    # Poland
    "Polska Liga Koszykówki": "Polonya PLK",
    "Poland 1st Division": "Polonya 1. Lig",
    "Poland 1 Liga": "Polonya 1. Lig",
    "Poland 2 Liga": "Polonya 2. Lig",
    "Women's Liga Koszykówki Kobiet": "Polonya Kadın Ligi",
    "Poland 1 Liga Women": "Polonya Kadın 1. Lig",
    # Brazil
    "Novo Basquete Brasil": "Brezilya NBB",
    "BRA  League": "Brezilya NBB",
    "Brazil Liga Ouro": "Brezilya Liga Ouro",
    "Brazil Liga Feminina de Basquete": "Brezilya Kadın Ligi",
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
    "National Basketball League": "Çin NBL",
    "Super Basketball League": "Çin Taipei SBL",
    "Taipei P League": "Çin Taipei P.League",
    "China Taipei Professional Basketball League": "Çin Taipei TPBL",
    "China Taiwan T1 League": "Çin Taipei T1",
    # USA
    "National Collegiate Athletic Association": "NCAA",
    "Women's National Collegiate Athletic Association": "NCAA Kadın",
    "WNCAA": "NCAA Kadın",
    "WNCAAB": "NCAA Kadın",
    "National Basketball Association": "NBA",
    "Women's National Basketball Association": "WNBA",
    # Europe
    "EuroCup Basketball": "EuroCup",
    "Adriatic Basketball Association League": "ABA League",
    "BNXT": "BNXT League",
    # International
    "Club Friendship": "Hazırlık Maçları",
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
