# Veri Arşivi

## Ham günlük arşiv (GitHub Release)

- **İndir:** https://github.com/LeChiffree/hoops-paper-lab/releases/download/data-v1/raw_day_bins.tar.gz
- **Sürüm:** `data-v1`
- **Boyut:** 101,5 MB (sıkıştırılmış) · 262 MB (açılmış) · 6.678 dosya
- **Kapsam:** 2009-10-01 → 2026-11-01, AiScore basketbol günlük feed'i
- **SHA256:** `68DE836D05351CA97C1814DA49D81C577FE8169D37F74260AAE858EE61B31945`

```bash
tar -xzf raw_day_bins.tar.gz
# raw/day_YYYYMMDD.bin dosyaları oluşur
```

`raw/` klasörü repo ağacında tutulmaz (6.241+ küçük dosya repo'yu şişirir); bu release asset'i ile dağıtılır.

## Repo içindeki veri

| Dosya | Kapsam | Not |
|---|---|---|
| `aiscore_all_matches_final.csv` | 608.833 maç, 2009–2026 | Git LFS |
| `data.sqlite3` | 132.978 maç, sonuç + oran | Git LFS |
| `paper_bets_250.csv` | 48.241 filtreli maç (2009–2025/26) | 250 TL paper bet |
| `paper_bets_2627.csv` | 605 maç (26/27) | Ayrı sezon |
| `paper_bets_league_summary.csv` | 66 lig özeti | Eski veri |
| `yillik_en_iyi_10_lig.md` | 2018–2026 yıllık top 10 | Markdown rapor |
| `crosscheck_*.csv` | AiScore ↔ Flashscore doğrulaması | 503 eşleşme |
| `tie_fix_status.csv` | 363 beraberlik / uzatma durumu | |

## LFS

```bash
git lfs pull
```

LFS dosyaları: `aiscore_all_matches_final.csv` (131 MB), `data.sqlite3` (66 MB).
