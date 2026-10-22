---
durum: yazildi
guncelleme: 2026-10-22
dal: feature/kalite-gunluk-rapor (feature/quality-db-reader üstünde)
pr: -
bekleyen: PR #9 merge; tatil listesi onayı (Kağan)
---

# Kalite günlük raporu — Implementation Plan (TASLAK)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ya da superpowers:executing-plans.
> Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.
> 4 soru yanıtlandı (Kağan, 22.10.2026): önceki eşit dönem · kurulun hepsi · tatilde rapor yok · bütçe uygun.

**Goal:** Pazartesi–cuma 09:30'da Kalite danışmanına günlük raporu "sistem sorusu" olarak açmak ve zinciri (danışman → Denetçi
→ CEO → Yanıt defteri) 11:00'e yetiştirmek için dağıtıcıyı gün içinde 10 dakikada bir ilerletmek.

**Architecture:** Yeni rapor yolu yazılmaz; mevcut soru zinciri kullanılır. `soru_kapisi.sistem_sorusu` kaydı açar,
`## Dağıtım`'ı doğrudan yazar, `s-<id>` kuyruğa düşer. `gunluk.py --rapor` bunu tetikler. `zamanla.py`'ye iki iş eklenir:
`rapor` (Weekday 1–5, 09:30) ve `ilerlet` (`StartInterval` 600).

**Tech Stack:** Python 3.9 stdlib, `unittest`, launchd plist (`plistlib`).

**Spec:** `docs/superpowers/specs/2026-10-22-kalite-gunluk-rapor-design.md`

## Global Constraints

- Taban: `python3 -m unittest discover -s tests` → dalın o anki sayısı, `OK (skipped=8)`.
- Soru kaydı id'si `rapor-kalite-YYYYMMDD` (İstanbul günü). Aynı gün ikinci kez açılmaz.
- Soru kaydına ek satırlar: `- aralik: YYYY-MM-DD..YYYY-MM-DD` · `- karsilastir: YYYY-MM-DD..YYYY-MM-DD` ·
  `- soran: Zamanlayıcı (kalite günlük raporu)`. `- durum: danışmanda`.
- İş günü: pazartesi–cuma ve `takimlar/kalite/tatiller.json`'da olmayan gün.
- Aralık: bir önceki iş gününden (dahil) dünkü güne. Karşılaştırma: aralık tek günse bir önceki iş günü; birden çok günse
  aynı aralık 7 gün geri.
- Sistem sorusu kaydında `- gorunurluk: kurul`.
- Rapor sorusu metni (sabit şablon): `<gg.aa.yyyy> (<gün>) günlük kalite raporu: ekip bazında ortalama ve önceki dönemle farkı,
  en sık kaçırılan 5 kriter, koçluk takibi. kalite_veri.py komutlarında yalnız kayıttaki "aralik" ve "karsilastir" tarihlerini kullan.
  Aralık: <gg.aa.yyyy>–<gg.aa.yyyy> · Karşılaştırma: <gg.aa.yyyy>–<gg.aa.yyyy>.` (son inceleme: aralıklar metinde de; tatil listesi eksikse sonuna not)
- Hafta sonu ve tatil günü `--rapor` hiçbir şey açmaz (rc 0, sebep yazılır).
- ANAYASA §1: dışarıya hiçbir şey gönderilmez; ulaşım Yanıt defteri.

## Review Focus

1. Pazartesi aralığı cuma..pazar, karşılaştırma bir önceki cuma..pazar; ayın ve yılın sınırında (1 Ocak pazartesi) doğru — Task 1 testi.
2. `--rapor` aynı gün iki kez (launchd + elle) → ikinci kez kayıt açmaz — Task 1 testi.
3. Makine UTC'de 23:30 (İstanbul'da ertesi gün 02:30) → id ve aralık İstanbul gününe göre — Task 1 testi.
4. `ilerlet` mesai dışında koşu başlatmaz (mevcut `tetik_karari`); mesai her gün 08–20, hafta sonunda kuyrukta bekleyen işi ilerletir (boş kuyrukta maliyet yok). Mac 09:30'u uykuda geçirip ertesi gün uyanırsa o günün raporu geriye dönük açılmaz (aynı gün elle `python3 bin/gunluk.py --rapor`) — Task 3 testi.
5. `yonlendir` sistem sorusunu yeniden yönlendirmez (`## Dağıtım` zaten var) ve Haiku çağrılmaz — Task 1 testi.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `bin/soru_kapisi.py` | `sistem_sorusu`, `rapor_araligi`, `is_gunu_mu`, `tatiller_oku` | Değişir (Task 1) |
| `takimlar/kalite/tatiller.json` | 2026–2027 resmî tatiller (Kağan onaylar) | Yeni (Task 1) |
| `bin/gunluk.py` | `--rapor` bayrağı | Değişir (Task 2) |
| `bin/zamanla.py` | `rapor` ve `ilerlet` işleri; `Weekday` dizisi ve `StartInterval` | Değişir (Task 3) |
| `tests/test_soru_kapisi_sistem.py`, `tests/test_gunluk_rapor.py`, `tests/test_zamanla_sahne.py` | Testler | Yeni / değişir |
| `NOVE-KURULUM.md`, `CLAUDE.md` | Faz 4 maddesi, Kalite satırı | Değişir (Task 3) |

### Task 1: Sistem sorusu

**Interfaces — Produces:**
- `is_gunu_mu(gun: date, tatiller: set[date]) -> bool`
- `rapor_araligi(gun: date, tatiller: set[date]) -> tuple[tuple[date, date], tuple[date, date]] | None` — iş günü değilse `None`.
- `tatiller_oku(kok) -> set[date]` — `takimlar/kalite/tatiller.json`; dosya yoksa boş küme.
- `sistem_sorusu(kok, danisman: str, soru: str, soru_id: str, aralik, karsilastir, simdi, kuru=False) -> dict`
  — `{"sonuc": "acildi" | "var", "soru_id"}`; kayıt + `## Dağıtım` (danışman, gerekçe "zamanlı rapor") + `kuyruga_yaz(s-<id>)`.

- [ ] **Step 1: Failing tests:** `test_aralik_sali` (2026-10-20 salı → 19..19, karşılaştırma 16..16 cuma) · `test_aralik_pazartesi`
  (2026-10-26 → 23..25, karşılaştırma 16..18) · `test_aralik_yil_basi` (2029-01-01 pazartesi → 2028-12-29..31) ·
  `test_hafta_sonu_none` · `test_tatil_none` · `test_tatil_sonrasi_aralik` (29.10.2026 tatil → 30.10 raporu 28..29, karşılaştırma 21..22) · `test_ayni_gun_ikinci_kez_var` · `test_dagitim_yazili_yonlendir_none` (sahte haiku çağrılmaz) ·
  `test_kuyrukta_s_maddesi` · `test_utc_gecesi_istanbul_gunu`
- [ ] **Step 2:** FAIL · **Step 3:** implement · **Step 4:** OK
- [ ] **Step 5:** `git commit -m "feat(rapor): sistem sorusu — zamanlı Kalite raporu soru kaydı olarak"`

### Task 2: `gunluk.py --rapor`

**Interfaces — Consumes:** Task 1. **Produces:** `rapor(kok, simdi=None, kuru=False) -> dict` — `ZAMANLI_RAPORLAR = [{"danisman": "kalite"}]`
listesi için bugünün sistem sorusunu açar, sonra `dagitici.dagit(kok)`; sabah raporu gibi `sirket-log/rapor/<gün>-rapor.md` yazar.

- [ ] **Step 1: Failing tests:** `test_rapor_acar_ve_dagitir` (sahte dagit çağrıldı) · `test_rapor_hafta_sonu_bos` · `test_rapor_kuru_yazmaz` · `test_cli_bayragi`
- [ ] **Step 2–4** · **Step 5:** `git commit -m "feat(rapor): gunluk.py --rapor"`

### Task 3: Zamanlama ve belgeler

- [ ] **Step 1: Failing tests:** `test_rapor_isi_hafta_ici` (`StartCalendarInterval` 5 sözlüklü dizi, Weekday 1..5, Hour 9, Minute 30) ·
  `test_ilerlet_isi_aralikli` (`StartInterval == 600`, `RunAtLoad` False, argv `--ilerlet`) · `gunluk.py --ilerlet` yalnız `dagitici.dagit` çağırır
- [ ] **Step 2–4:** `plist_icerigi` `gunler` (liste) ve `aralik_sn` alanlarını okur; mevcut işler değişmez (eski testler yeşil)
- [ ] **Step 5:** `NOVE-KURULUM.md` Faz 4 "Günlük rapor zamanlayıcısı" maddesi `[x]`; `CLAUDE.md` Kalite satırına "günlük rapor 11:00";
  `git commit -m "feat(rapor): 09:30 rapor ve 10 dk ilerletme tetikleri, belgeler"`

## Bitirme

- [ ] Tam takım yeşil
- [ ] `python3 bin/gunluk.py --rapor --kuru` (salı tarihinde) → açılacak kayıt ve aralık basılır, dosya yazılmaz
- [ ] `python3 bin/zamanla.py --kuru` → `rapor` hafta içi 09:30, `ilerlet` 10 dk
- [ ] Kağan onayıyla ilk gerçek rapor: bir salı 09:30, Yanıt defterinde 11:00'den önce
