# Hoops Paper Lab

> **Private repo:** https://github.com/LeChiffree/hoops-paper-lab
> **Dashboard:** [`dashboard.html`](dashboard.html) — tek dosya, çevrimdışı
> 2009–2026 AiScore arşivi · ev sahibi 1-2 oranı 2.25–4.00 · 250 TL paper bet · çoklu lig analizi

## Hızlı başlangıç

- `dashboard.html` — çift tıkla; Genel Özet / Analist Önerisi / Worst Case sekmeleri.
- `paper_bets_250.csv` — eski veri (48.241 maç), `paper_bets_2627.csv` — 26/27 (605 maç).
- `aiscore_all_matches_final.csv` — 608.833 maçlık tam arşiv (LFS).
- `data.sqlite3` — 132.978 maçlık ham veritabanı (LFS).
- `yillik_en_iyi_10_lig.md` — 2018–2026 yıllık en iyi 10 lig raporu.
- `DATA.md` — ham günlük arşiv (Release) ve veri sözlüğü.

> Ham günlük arşiv (6.241 gün, 101,5 MB sıkıştırılmış): [Release `data-v1`](https://github.com/LeChiffree/hoops-paper-lab/releases/tag/data-v1)
> LFS dosyaları için: `git lfs pull`

---

# Basketbol 1X2 — Ev Sahibi 2.25–4.00 Backtest

35 lig · 10 sezon (2016/17–2025/26) · kapanış oranları · 10.000 TL sabit bahis.

## Sonuç (özet)

| | |
|---|---:|
| Toplam maç | 132.978 |
| 1X2 oranı olan maç | 93.388 (%70,2) |
| Filtreye giren (ev sahibi 2.25–4.00) | **18.756** |
| Kazanan / kaybeden | 6.120 / 12.636 |
| Kazanma oranı | **%32,6** |
| Başabaş kazanma oranı | %35,6 |
| Ortalama oran | 2,88 |
| Yatırılan | **187.560.000 TL** |
| Geri dönüş | 171.516.850 TL |
| Kâr / Zarar | **−16.043.150 TL** |
| ROI | **−%8,55** (±0,98) |

Ortalama 1X2 bookmaker marjı (overround) **%9,5**. Filtre bu marjı aşamıyor.
Moneyline (uzatma dahil) aynı bant: 22.171 bahis, ROI **−%5,98**.
NCAA hariç: 16.861 bahis, ROI **−%8,18**.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `basketball_1x2_rapor.xlsx` | 41 sekme: özet, lig lig tüm filtreli maçlar, oran bandı, sezon, kapsam, ML özeti, yöntem |
| `rapor.html` | Görsel rapor; lig lig açılır maç tabloları |
| `tum_filtreli_maclar_TL.csv` | 18.756 filtreli maç (Türkçe kolonlar) |
| `lig_ozet.csv` | 34 lig özeti + ROI standart hatası |
| `data.sqlite3` | Ham veri: 132.978 maç, sonuçlar, normal süre skoru, 1X2/ML oranları |
| `scraper.py` | Veri çekici (phase1 sonuçlar, phase2 oranlar) |
| `report.py` | Rapor üretici |

## Yöntem

- **Kaynak:** Flashscore açık veri servisi (sonuçlar `tr_` feed; oranlar `global.ds.lsapp.eu/odds/pq_graphql`).
- **Piyasa:** `HOME_DRAW_AWAY` / `FULL_TIME` = 1X2, normal süre. Uzatma ayrı periyot (Quarter 5+) olarak ayıklanır.
- **Oran:** 7 bookmaker kapanış oranının medyanı (bwin, Interwetten, Oddset vb.); yoksa 20 bookmaker'lık GB seti.
- **Ev/deplasman:** Her maçın katılımcı ID'leri (`JA`/`JB`) ile eşlenir. Oran dizisi maçların ~%4'ünde deplasmanı önce listeliyor; bu eşleme olmadan sonuçlar bozulur.
- **Bahis:** Her filtreli maça 10.000 TL, ev sahibi galibiyetine (1). Kazanan: 10.000 × oran; kaybeden: 0.
- **Kâr:** Geri dönüş − 10.000. Bileşik getiri yok.

## Kapsam uyarıları

- **G League:** Flashscore'da 1X2 oranı yok (yalnızca kısmi moneyline). 1X2 tablosu bu yüzden 34 lig.
- **NCAA:** 35.816 maçın yalnızca %30'unda 1X2 oranı var (1.895 filtreli maç).
- **PBA:** %29,7; **VTB:** %38,6; **WNBA:** %76,1. Bu liglerde örneklem daha küçük.
- Pozitif görünen ligler (CBA +%14,0 ±5,0; İzlanda +%17,2 ±8,4) 34 lig içinde çoklu test sonrası anlamlı değil.

## Yeniden üretme

```bash
python scraper.py phase1          # sonuçlar (~11 dk)
python scraper.py phase2 --workers 32   # oranlar (~30 dk)
python report.py                  # Excel + HTML
```

Gereksinim: `C:\Users\GIGABAYT\AppData\Local\Temp\opencode\flashscore-scraper\.venv`


## AiScore API (Kasım 2026)

- Liste: `GET https://api.aiscore.com/v1/web/api/matches?lang=2&sport_id=2&date=YYYYMMDD&tz=03:00` (protobuf)
- Detay: `/v1/web/api/match/data?match_id=...`, oran: `/v1/web/api/match/odds_detail?match_id=...`, `/match/odds_list`
- Doğrudan istek Cloudflare nedeniyle 403; açık tarayıcı sekmesinden `fetch(..., {credentials:"include"})` ile çalışıyor.
  `collector.py` ham baytları kaydeder, `aiscore_parse.py` CSV'ye çevirir.
- 26.10.2026–01.11.2026: 1.388 maç, 1.128 bitmiş, 1.011'inde 1-2 (To win) oranı, 198 lig.
- **Not:** AiScore basketbol oranı 1-2'dir (beraberlik yok); 1X2 (X'li) değil, moneyline karşılığıdır.


## AiScore uzatma (OT) düzeltmesi

Liste endpoint'i (`/v1/web/api/matches`) periyotları 4'te kesiyor; uzatmalı maçlar **berabere** görünüyor.
Çözüm: berabere görünen her bitmiş maç için `GET /v1/web/api/match/data?match_id=...&lang=2` çağır.
Bu endpoint 5. periyodu (Q5) da veriyor (~500 byte).

- 26.10–01.11.2026: 1.128 bitmiş maçta 53 beraberlik; 53/53 detayla düzeltildi.
- 52'sinde Q5 vardı; 1'inde liste skoru bayattı (42-42 -> 42-51).
- Flashscore ile 23/23 birebir: Zenit 94-86, Utah 111-117, Cleveland 127-125...
- Skor tutarlılığı %94,4 -> **%99,0**.
- Maliyet: 53 detay isteği (~%4,7), yaklaşık 5 saniye.

Dosyalar: `aiscore_fixed.csv` (düzeltilmiş tüm maçlar), `aiscore_tie_fix.csv` (53 maçlık düzeltme tablosu),
`fix_ties.py` (detay baytlarını çözüp skorları değiştirir).



## Paper Bet Dashboard (250 TL)

- `dashboard.html` — tek dosya, çevrimdışı (Chart.js gömülü). Çift tıkla aç.
- Kapsam: **66 lig**. Varsayılan görünüm 2009–2025/26: **48.241 maç**. 26/27 sezonu ayrı modda: **605 maç**.
- Küçük bütçeli ligler (Venezuela, Etiyopya vb.), hazırlık ve gençlik ligleri hariç; lige en az 100 bahis eşiği.
- Filtre: bitmiş maç + ev sahibi 1-2 kapanış oranı **2.25 ≤ x ≤ 4.00** + 250 TL sabit bahis.

Varsayılan (eski veri):
- 16.763 kazanan / 31.478 kaybeden (%34,7), ortalama oran 2,87
- Yatırılan 12.060.250 TL, kâr **−350.035 TL**, ROI **−%2,90**, maks. drawdown −361.688 TL

26/27 sezonu:
- 605 maç, 218 kazanan (%36,0), kâr −3.640 TL, ROI −%2,41

Analist önerisi (3 lig: CBA + Macaristan + İzlanda):
- 1.951 bahis, 805 kazanan (%41,3), kâr **+90.325 TL**, ROI **+%18,52**

Dashboard özellikleri:
- Solda lig checkbox'ları (çoklu seçim, cross-lig analizi), arama, tümünü seç/temizle
- "Eski Veriler" / "26/27 Sezonu" anahtarı; 26/27'de sadece o sezonun maçları ve analizleri
- Yıl/sezon, ay, haftanın günü, ayın günü etkisi: her kovada brüt kâr (yeşil) ve brüt zarar (kırmızı)
- Gün gün net kâr/zarar grafiği ve günlük kâr/zarar dağılım histogramı
- Kasa durumu (0 TL başlangıçlı), aylık hacim, lig ROI, oran bandı, sıralanabilir lig tablosu, sayfalı bahis listesi
- "★ Analist Önerisi" sekmesi: çekirdek/destek/izleme kademeleri, t-değeri, pozitif sezon oranı, en kötü sezon ROI'si

Dosyalar:
- `paper_bets_250.csv` — 48.241 eski veri maçı
- `paper_bets_2627.csv` — 605 adet 26/27 maçı
- `paper_bets_league_summary.csv` — 66 lig özeti (eski veri)
- `dashboard_data.json` — gömülü dashboard verisi
- `canonical.py` / `scope_check.py` / `build_data.py` / `dashboard_template.html` / `build_dashboard.py` — üretim


### Dinamik filtre özellikleri (son güncelleme)

- **Sidebar ROI'leri seçili yıl aralığına göre** yeniden hesaplanır; yıl değişince tüm lig rozetleri güncellenir.
- **Sırala** menüsü: ROI ↓, **ROI ↑ (düşükten yükseğe)**, maç sayısı ↓, isim A-Z.
- 20 bahisten az ligler (düşük örneklem) sıralamada en alta alınır ve `•` ile işaretlenir.
- **Analist Önerisi** sekmesi seçili yıl aralığına göre kendini yeniler:
  - Eski veride ≥50, 26/27'de ≥20 bahis alan **pozitif ROI'li** ligler ROI'ye göre sıralanır.
  - En iyi 10 lig gösterilir ve otomatik seçilir; t-değeri ve pozitif sezon oranı sütunları vardır.
  - 26/27 gibi küçük dönemlerde pozitif lig sayısı 10'dan azsa yalnızca mevcut olanlar gösterilir.


### Worst Case sekmesi (−0,20)

- Üçüncü sekme: **⚠ Worst Case (−0,20)**.
- Maç seçimi yine orijinal 1-2 oranı 2.25–4.00 aralığına göre yapılır.
- Kazanan bahislerde oran **0,20 düşük** hesaplanır (2,50 → 2,30); kaybeden bahisler tamamı gider.
- Tüm KPI, kasa, histogram, lig tablosu, sidebar ROI ve bahis listesi bu senaryoya göre yenilenir.
- Bahis listesinde oran `2,30 → 2,10` şeklinde gösterilir.

Sonuç:

| | Normal | Worst Case |
|---|---:|---:|
| Bahis | 48.241 | 48.241 |
| Kazanan | 16.763 | 16.763 |
| Ort. oran | 2,87 | 2,67 |
| Başabaş | %35,8 | %38,6 |
| Yatırılan | 12.060.250 TL | 12.060.250 TL |
| Kâr | −350.035 TL | **−1.188.185 TL** |
| ROI | −%2,90 | **−%9,85** |
| Maks. DD | −361.688 TL | −1.189.460 TL |
