---
durum: yazildi
guncelleme: 2026-11-13
dal: feature/okr-danismani
pr: -
bekleyen: -
---

# OKR Danışmanı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (önerilen) ya da
> superpowers:executing-plans. Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.
> **(Kağan)** yazan görev ve adımlar insanındır; ajan onları yapmaz, yerine geçecek bir yol da aramaz.

**Goal:** OKR Danışmanı, Nove PYS veritabanını `okr_okuyucu` rolüyle salt okunur okuyan `bin/okr_veri.py`'yi
çağırıp sitenin aynı dönem ve bölüm için gösterdiği yüzdeyle **aynı** sayıyı, dönemi, son dolu ayı ve her `—`'nin
sebebini alsın.

**Architecture:** İki dosya. `bin/okr_hesap.py` sitenin hesabının birebir Python taşımasıdır: saf fonksiyon, G/Ç yok,
her bloğun başında sitedeki karşılığı (B1a). `bin/okr_veri.py` komut satırıdır: bağlantı, düz tablo okumaları
(site gibi — birleştirme ve toplama SQL'de değil bellekte), aralık çözümü, tablo basımı. Bağlantı ve hata maskesi
`bin/kalite_veri.py`'den **içe aktarılır** (B5'in "ortak yer" seçeneği; Kalite dosyası değişmez).

**Tech Stack:** Python 3.9 stdlib (`zoneinfo`, `calendar`, `argparse`) + `psycopg` 3.2 (kurulu), `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-13-okr-danismani-design.md` (Kağan onayı 13.11.2026). Kararlar orada;
bu plan onları yeniden açmaz.

## Global Constraints

- Dal `feature/okr-danismani` (spec commit `d1383d9`). Taban: `python3 -m unittest discover -s tests` →
  `Ran 795 tests` · `OK (skipped=9)`. Sayı düşmez; her görevin sonunda tam takım koşar.
- **Hesap siteden taşınır, icat edilmez (B1).** Kaynak: `/Users/sorcerer/Desktop/Nove Performance`, HEAD `d5d0e5d`
  — ajan için **salt okunur**. Klasör iCloud Masaüstünde; okuma asılırsa tahmin yürütme, dur ve "dosya dataless"
  diye bildir.
- **B1a başlığı:** `okr_hesap.py`'de taşınan her bloğun hemen üstünde tek satır:
  `# KAYNAK: Nove Performance <yol>:<satır aralığı> @ d5d0e5d`. Satır aralıkları bu planda yazılı; değiştirme.
- **Taşınan fonksiyonların adı sitedekinin snake_case'idir** (`krPct` → `kr_pct`); sözlük anahtarları da öyle
  (`measuredByCutoff` → `measured_by_cutoff`). Depo Türkçe ad kullanır; burada bilerek ayrılınır — site değişince
  karşılık tek bakışta bulunsun (B1a). `okr_veri.py`'deki komut katmanı Türkçe adlıdır.
- **Yuvarlama ve kayan nokta:** `Math.round` yerine `kalite_veri.js_yuvarla` (Python `round()` yasak — banker
  yuvarlaması). Toplamlar sitedeki `reduce` gibi **soldan sağa, 0'dan başlayan düz döngüyle** alınır;
  `math.fsum` ve `statistics` kullanılmaz. İşlem sırası sitedekiyle aynı kalır (`((current - start) / span) * 100`).
- **Ana yüzde `status_pct = std ?? annual`'dır (O7)**; yıllık yanında basılır. Aralık bir *kesimdir*: değerler her
  KR'ın kendi döneminin ilk ayından kesime kadar birikir; ara dilim hesaplanmaz (B2a).
- **`—` ile `0` karışmaz (B7).** Üç ayrı durum, üç ayrı sebep metni: `ölçülemiyor (hedef = başlangıç)` ·
  `kesime kadar aylık veri yok` · `ölçülebilir KR yok`. Aylık satırı hiç olmayan KR `—` değildir: saklı özet
  değeriyle (`key_results.current`) basılır ve yanına notu düşülür.
- **Oran notu (O3):** `rollup == 'avg'` ve `unit.strip() == '%'` olan **her** KR satırı `oran_notu=evet` taşır ve
  kapsamda not metni birebir yazar: `aylık oranların ortalaması; ayların hacmi farklıysa gerçek orandan sapabilir`.
- **Güvenlik (B5):** yalnız `SELECT`; her bağlantı `read_only = True`, `statement_timeout` bağlantı seçeneğinde
  (`kalite_veri.baglanti_ac`). Bağlantı yalnız `OKR_READONLY_URL` (`ayar.ortam_yukle()`); adres hiçbir çıktıya,
  hata iletisine, teste, kayda girmez. **Ajan `.env`'i ve `.env.example`'ı okumaz** (`permissions.deny`).
- **Okunmayan sütunlar:** `users`'ta yalnız `id, name`. E-posta, parola özeti, `login_attempts`, `help_articles`,
  `checkins.note`, `kr_monthly_values.note` hiçbir sorguda yok. Sorgularda `SELECT *` yok.
- **Depo herkese açık (B4):** test, fikstür, örnek ve bu plandaki adlar uydurmadır. Gerçek çalışan adı,
  e-posta, gerçek KR başlığı depoya girmez.
- Birim testleri ağa çıkmaz, `claude` çağırmaz; bağlantı `baglan` ile enjekte edilir (`tests/test_kalite_veri.py`
  deseni: `_SahteImlec`, `_SahteBaglanti`).
- Her durma görünür: stdout'a `**Hazırlanamadı:** <sebep>`, çıkış 1; kullanım hatası 2. Geçersiz tarih, bilinmeyen
  dönem kodu ya da bölüm adı **sessizce varsayılana düşmez** (site eski yer imleri için düşer,
  `range.ts:149-165`; danışmanda bu `AJAN-KIMLIGI` "sessiz düşme yok" kuralına aykırıdır — bilerek ayrılınır).
- Çıktı `## kapsam` ile başlar (form hattının ürettiği `takim.md` 3. adımı bunu kaynak olarak yazdırır).
- Ajan yazamaz: `ANAYASA.md`, `takimlar/*/kurallar.md`, `formlar/onayli/`, `sirket/CEO-KIMLIGI.md`.
  `bin/formdan_takim.py` ajanda yalnız `--kuru`. Prod'da DDL/GRANT/POLICY'yi **Kağan** çalıştırır.
  Nove PYS'ye yazma, siteye tarayıcıyla giriş, sitenin koduna dokunma yok.
- Commit: `type(scope): Türkçe konu`. `formlar/gelen/` git dışıdır; commit'e girmez.

## Review Focus

1. **Yarım yuvarlama:** yüzde tam `.5`'e denk gelince site yukarı yuvarlar (`krPct` 12,5 → 13; ortalama 62,5 → 63);
   Python `round()` 12 ve 62 verir — Task 1 testi.
2. **İki mali yılı kapsayan aralık:** varsayılan aralık (2025-09-01 → bugün) iki dönemi birleştirir; her KR kendi
   döneminin aylarını sayar, kapalı dönemin KR'ı açık dönemin ayına bakmaz — Task 4 testi, Task 6 kapsam satırı.
3. **Dört durum ayrı görünür:** ölçülemiyor · kesime kadar veri yok · aylık satır yok (saklı özet) · gerçek `0` —
   Task 8 testi (`0` basan KR ile `—` basan KR aynı çıktıda).
4. **`app_settings` okunamıyor:** betik durmaz, `2025-09-01`'e düşer, düşüşü kapsamda yazar ve hatalı işlem sonraki
   sorguyu bozmaz (`rollback`) — Task 6 testi.
5. **Bölüm adı:** `--bolum satış`, `--bolum SATIŞ`, `--bolum satis` (slug) aynı bölümü bulur; bulunamayan ad sebepli
   durur ve geçerli adları listeler; aralığa hiçbir dönem düşmüyorsa boş tablo değil sebepli durma — Task 6–7 testi.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `bin/okr_hesap.py` | Sitenin hesabı: ilerleme, ağırlık, durum bandı, ay/kural, StD, mali takvim, tarih, ağaç, yüzde çiftleri | Yeni (Task 1–4) |
| `tests/test_okr_hesap.py` | Sitenin test vektörleri (kopya) + B1a başlık denetimi | Yeni (Task 1–4) |
| `bin/okr_veri.py` | Komutlar, sorgular, aralık çözümü, kapsam, tablo basımı | Yeni (Task 5–8) |
| `tests/test_okr_veri.py` | Sahte imleçle komut testleri; izin dosyası testi | Yeni (Task 5–8) |
| `docs/okr-veri-izin.sql` | `app_settings` için tek satırlık okuma izni ve politikası (Kağan çalıştırır) | Yeni (Task 5) |
| `formlar/gelen/okr.md` | Form taslağı: §3 komutlar, §4 kural satırları, §5 örnek — git dışı | Değişir (Task 9) |
| `takimlar/okr/{takim,kurallar,defter}.md`, `durum.json` | Formdan üretilir | **Kağan** üretir (Task 10) |
| `.claude/agents/okr.md` | `agents_uret.py` çıktısı | Yeni (Task 10) |
| `CLAUDE.md`, `NOVE-KURULUM.md` | OKR satırı "kurulu"; Faz 6 maddesi | Değişir (Task 10) |

`bin/kalite_veri.py` **değişmez**; yalnız içe aktarılır.

---

### Task 1: İlerleme, ağırlık, durum bandı

**Files:** Create `bin/okr_hesap.py`, `tests/test_okr_hesap.py`

**Interfaces — Produces** (KR bir sözlüktür: `start, current, target` zorunlu; `weight`, `rollup` yoksa `None`):
- `effective_start(kr) -> float` — `progress.ts:8-10`
- `kr_pct(kr) -> int` — `progress.ts:25-31` (0–140 kırpma; aralık 0 ise 0)
- `is_measurable(kr) -> bool` — `progress.ts:42-44`
- `obj_pct(krs: list) -> int` — `progress.ts:46-62` (`mean` dahil)
- `objective_weights_complete(objectives: list) -> bool` — `progress.ts:73,83-93`
- `dept_pct(objectives: list) -> int` — `progress.ts:106-113`; objective sözlüğü: `krs`, `weight`, `period_id`
- `company_pct(depts: list) -> int` — `progress.ts:121-125`; bölüm sözlüğü: `objectives`
- `WEIGHT_TOLERANCE = 0.005`, `check_weights(ws, required: bool) -> str | None` (`'missing' | 'partial' | 'range' | 'total'`),
  `weight_set_state(ws) -> str` (`'none' | 'complete' | 'incomplete'`) — `weights.ts:11,15,21-31,49-52`
- `status_of(pct) -> str` (`'above' | 'expected' | 'below' | 'open' | 'none'`), `is_open_to_development(pct) -> bool`
  — `status.ts:18-24,27`
- `DURUM_ADLARI = {"above": "Beklenenin Üzerinde", "expected": "Beklenen", "below": "Beklenenin Altında",
  "open": "Gelişime Açık", "none": "Başlamadı"}` — `status.ts:3-14`

Taşınmaz (kullanılmıyor): `weightTotal`, `equalWeights`, `STATUS_VARS`.

- [ ] **Step 1: Failing tests** — sitenin vektörleri aynen (`lib/domain/__tests__/progress.test.ts`,
  `objective-weights.test.ts`, `weights.test.ts`, `status.test.ts`):
  - `test_kr_pct`: `(42000, 61000, 80000) → 50` · `(950, 720, 650) → 77` · `(100, 120, 50) → 0` · `(0, 500, 100) → 140` ·
    `(50, 70, 50) → 0` · `sum` kuralı `start 51500, current 19167, target 57500 → 33` · `avg` ve `last` `(950, 720, 650) → 77`
  - `test_is_measurable`: `(77.5, 77.5, 77.5)` ve `(0, 0, 0)` → `False`; `(0, 0, 100)` ve `(110, 110, 100)` → `True`;
    `sum (100, 0, 100)` → `True`; `sum (0, 0, 0)` → `False`; `avg (100, 0, 100)` → `False`
  - `test_obj_pct`: `[50, 80] → 65` · `[] → 0` · ölçülebilir 50 + `(5, 5, 5)` → `50` · yalnız `(5, 5, 5)` → `0` ·
    ağırlıklı `80@75, 40@25 → 70` · `80@40, 40@40, (5,5,5)@20 → 60` · ağırlıksız ve `None` → `60` · `80@90, 40@None → 60`
  - `test_dept_pct`: `[100]` ile `[0, 0]` → `50` · `80` ile ölçülemez → `80` · yalnız ölçülemez → `0` · `[] → 0` ·
    `o(80, 70), o(40, 30) → 68` · ağırlıksız → `60` · `o(80, 70), o(40, None) → 60` · `o(80, 60), o(40, 30) → 60` ·
    `o(80, 70)` + ölçülemez@30 → `80` (ve `objective_weights_complete` `True`) · `o(80, 60)` + `{krs: [], weight: 40}` → `80` ·
    iki dönem `o(80,100,'p1'), o(40,50,'p2'), o(0,50,'p2') → 50` · biri eksik dönem → `40` ·
    `objective_weights_complete([]) → False`
  - `test_company_pct`: `[40]` + objective'siz bölüm → `40` · `[] → 0` · `60` + ölçülemez bölüm → `60` ·
    yalnız ölçülemez → `0` · `[o(80,70), o(40,30)]` ile `[o(40, None)]` → `54`
  - `test_weight_set_state`: `[] → none` · `[None, None] → none` · `[60, 40] → complete` ·
    `[33.34, 33.33, 33.33] → complete` · `[60, None] → incomplete` · `[60, 30] → incomplete`
  - `test_check_weights`: `[50, 30, 20] → None` · `[33.33, 33.33, 33.33] → 'total'` · `[50, 50.01] → 'total'` ·
    `[None, None]` `required=True → 'missing'`, `False → None` · `[100, None] → 'partial'` · `[0, 100] → 'range'` ·
    `[-10, 110] → 'range'` · `[33.333, 66.667] → 'range'`
  - `test_status_of`: `140, 130, 101 → above` · `100, 80 → expected` · `79, 60 → below` · `59, 1 → open` · `0 → none`;
    `is_open_to_development(59)` `True`, `(60)` `False`
  - `test_yarim_yukari_yuvarlanir` (Review Focus 1): `kr_pct({start: 0, current: 12.5, target: 100}) == 13`;
    `obj_pct([(0, 62, 100), (0, 63, 100)]) == 63` (ortalama 62,5)
  - `test_kaynak_basliklari`: `okr_hesap.py`'deki her `# KAYNAK:` satırı
    `^# KAYNAK: Nove Performance lib/(domain|queries)/[a-z-]+\.ts:\d+(-\d+)?(,\d+(-\d+)?)* @ d5d0e5d$` desenine uyar ve
    modüldeki her üst düzey `def`'in üstündeki ilk yorum bloğunda bir `# KAYNAK:` satırı vardır
- [ ] **Step 2:** Run `python3 -m unittest tests.test_okr_hesap -v` → FAIL (`No module named 'okr_hesap'`)
- [ ] **Step 3:** Yukarıdaki fonksiyonları yaz. Modül belgesi B1a notunu taşır: "sitenin `lib/domain` ya da
  `lib/queries/{tree,std,range}.ts` hesabı değişirse bu dosya güncellenir; Kağan'ın üç sayılık karşılaştırması
  yinelenir". `from kalite_veri import js_yuvarla`.
- [ ] **Step 4:** Run `python3 -m unittest tests.test_okr_hesap -v` → OK; `python3 -m unittest discover -s tests` → OK, `skipped=9`, sayı ≥ 795
- [ ] **Step 5:** `git commit -m "feat(okr): ilerleme, ağırlık ve durum bandı hesabı siteden taşındı"`

### Task 2: Aylar, toplama kuralı, mali takvim, tarih

**Files:** Modify `bin/okr_hesap.py`, `tests/test_okr_hesap.py`

**Interfaces — Produces** (tarihler `YYYY-MM-DD`, aylar `YYYY-MM` dizgisidir; karşılaştırma dizgi karşılaştırmasıdır):
- `months_in_range(from_: str, to: str) -> list[str]` — `monthly.ts:27-45`
- `months_of_period(starts_on: str, ends_on: str) -> list[str]` — `monthly.ts:52-54`
- `rollup(rule: str, values: list) -> float | None` — `monthly.ts:66-76`
- `value_for_range(rule, months, by_month: dict, period_months) -> dict` — anahtarlar `value, carried_from, latest_month`
  — `monthly.ts:97-134`
- `FISCAL_START_MONTH = 9`, `fiscal_year_of(date) -> int`, `fiscal_quarter_range(fiscal_year, quarter) -> dict`
  (`starts_on, ends_on`), `fiscal_year_range(fiscal_year) -> dict` — `fiscal.ts:14,19-24,33-42,45-50`
- `today_in_istanbul(now: datetime | None = None) -> str` — `dates.ts:23-32` (`zoneinfo.ZoneInfo("Europe/Istanbul")`)
- `as_of_cutoff(to: str, today: str) -> str` — `dates.ts:56-59` (`today` dışarıdan gelir; saat burada okunmaz)
- `is_valid_iso_date(value: str) -> bool` — `dates.ts:34,62-67`

Taşınmaz: `defaultEntryMonth`, `currentAfterEntry`, `ENTRY_GRACE_DAYS` (veri giriş ekranına ait).

- [ ] **Step 1: Failing tests** (`monthly.test.ts`, `fiscal.test.ts`, `dates.test.ts`):
  - `test_months_in_range`: `2026-03-12..2026-05-20 → [03, 04, 05]` · `2026-03-28..2026-04-02 → [03, 04]` ·
    `2026-03-15..2026-03-15 → [03]` · `2025-11-20..2026-02-03 → [2025-11, 2025-12, 2026-01, 2026-02]` ·
    ters aralık `2026-05-01..2026-03-01 → []`
  - `test_months_of_period`: `2025-09-01..2026-08-31` 12 ay, ilki `2025-09`, sonu `2026-08`; `2028-02-01..2028-02-29 → [2028-02]`
  - `test_rollup`: `sum [10, 20, 30] → 60` · `avg [90, 100, 80] → 90` · `last [10, 20, 30] → 30` · üç kuralda `[] → None`
  - `test_value_for_range_tasima`: dönem `2025-09..2025-12`, `{2025-09: 42}`, aylar `[2025-11, 2025-12]` →
    `last`: `{value: 42, carried_from: '2025-09', latest_month: '2025-09'}`; `sum` ve `avg`: üçü de `None`
  - `test_tasima_donem_disina_cikmaz`: dönem `[2025-09, 2025-10]`, `{2025-08: 99}`, `last`, `[2025-10]` → üçü de `None`
  - `test_dolu_ay_tasinani_yener`: `{2025-09: 42, 2025-11: 7}`, `last`, `[2025-10, 2025-11]` →
    `{value: 7, carried_from: None, latest_month: '2025-11'}`
  - `test_sirasiz_aylar`: `{2025-10: 10, 2025-11: 20, 2025-12: 30}`; `last`, `[2025-11, 2025-12, 2025-10]` →
    `value 30`, `latest_month '2025-12'`; üç kuralda sırasız girdi sıralıyla aynı sonuç
  - `test_donem_sonunu_asan_aralik`: dönem `[2026-06, 2026-07, 2026-08]`, `{2026-07: 15}`, aylar `[2026-08, 2026-09]` →
    `last`: `{15, '2026-07', '2026-07'}`; `sum`: üçü de `None`
  - `test_latest_month`: `{2025-09: 10, 2025-11: 30}` üç ay istenir → üç kuralda `2025-11`; `{2025-09: 10}` → `2025-09`;
    `{2025-09: 10, 2025-10: 0}` → `2025-10` (sıfır ölçümdür)
  - `test_fiscal`: `fiscal_year_of('2025-09-01') == 2025`, `('2025-12-31') == 2025`, `('2026-08-31') == 2025`,
    `('2026-01-01') == 2025`; çeyrekler 2025: `09-01..11-30`, `12-01..2026-02-28`, `2026-03-01..05-31`, `06-01..08-31`;
    `fiscal_quarter_range(2027, 2)['ends_on'] == '2028-02-29'`; `fiscal_year_range(2025) == {2025-09-01, 2026-08-31}`
  - `test_today_in_istanbul`: `2026-08-09T22:30:00Z → '2026-08-10'`; `2026-08-09T20:00:00Z → '2026-08-09'`
  - `test_as_of_cutoff`: `('2026-08-31', today='2026-03-15') → '2026-03-15'` · `('2025-11-30', '2026-03-15') → '2025-11-30'` ·
    `('2026-08-10', '2026-08-10') → '2026-08-10'`
  - `test_is_valid_iso_date`: `2026-08-10`, `2028-02-29` → `True`; `2026-02-30`, `2026-13-01`, `2026-8-10`, `yarın`, `''` → `False`
- [ ] **Step 2:** Run `python3 -m unittest tests.test_okr_hesap -v` → yeni testler FAIL (`AttributeError`)
- [ ] **Step 3:** Yaz. Ay taşması `Date.UTC` yerine tam sayı yıl/ay aritmetiğiyle; ayın son günü `calendar.monthrange`.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): ay, toplama kuralı, mali takvim ve tarih yardımcıları"`

### Task 3: StD — sezon başından bugüne

**Files:** Modify `bin/okr_hesap.py`, `tests/test_okr_hesap.py`

**Interfaces — Consumes:** `value_for_range` (Task 2). **Produces:**
- `last_completed_month(as_of: str) -> str` — `std.ts:15-21`
- `monthly_target(rule, target, month_count) -> float` — `monthly-table.ts:14-16`
- `std_figure(rollup, target, period_months, by_month, as_of) -> dict | None` — anahtarlar
  `current, target, months_counted, months_filled` — `std.ts:44-47,55-68`

Taşınmaz: `requiredPerMonth` ("ayda gereken" spec B2'de yok).

- [ ] **Step 1: Failing tests** (`lib/domain/__tests__/std.test.ts`; `FY = months_of_period('2026-09-01', '2027-08-31')`):
  - `test_last_completed_month`: `2026-11-04 → 2026-10` · `2026-11-30 → 2026-11` · `2026-12-31 → 2026-12` ·
    `2026-09-15 → 2026-08` · `2027-08-31 → 2027-08` · `2028-02-28 → 2028-01` · `2028-02-29 → 2028-02` · `2027-02-28 → 2027-02`
  - `test_std_sum`: `{09: 200, 10: 250, 11: 200, 12: 250}`, hedef 3000, `2026-12-31` →
    `{current: 900, target: 1000, months_counted: 4, months_filled: 4}`
  - `test_std_avg`: `{09: 95, 10: 80}`, hedef 90, `2026-11-04` → `{87.5, 90, 2, 2}`
  - `test_icinde_bulunulan_ay_sayilmaz`: `{09: 200, 11: 999}`, `sum`, 3000, `2026-11-04` → `{200, 500, 2, 1}`
  - `test_std_none`: `{09: 1}` `2026-09-15` → `None` (k = 0); `{11: 1}` `2026-11-04` → `None` (sayılan ay boş)
  - `test_kapali_donem`: her ay 250, `2027-08-31` → `{3000, 3000, 12, 12}`
- [ ] **Step 2:** FAIL · **Step 3:** yaz · **Step 4:** `python3 -m unittest tests.test_okr_hesap -v` → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): StD hesabı siteden taşındı"`

### Task 4: Ağaç, kesim ve yüzde çiftleri

**Files:** Modify `bin/okr_hesap.py`, `tests/test_okr_hesap.py`

**Interfaces — Consumes:** Task 1–3. **Produces:**
- `periods_in_range(periods: list, from_: str, to: str) -> list` — `range.ts:40-47` (çakışma, `starts_on`'a göre sıralı)
- `load_tree(rows: dict, period_ids: list, as_of: str) -> tuple[list, list]` → `(periods, depts)` — `tree.ts:139-314`.
  `as_of` zorunludur; sitenin kesimsiz dalı (`tree.ts:201-203`) taşınmaz, danışman hep kesimle okur.
  - `rows` anahtarları (hepsi sözlük listesi): `periods` (`id, code, kind, state, starts_on, ends_on`),
    `departments` (`id, slug, name_tr`), `users` (`id, name`), `objectives`
    (`id, code, department_id, period_id, title_tr, owner_user_id, weight`), `key_results`
    (`id, objective_id, title_tr, start, current, target, unit, rollup, weight, owner_user_id`),
    `monthly` (`key_result_id, month, value`)
  - KR düğümü: `id, title_tr, start, current, target, unit, rollup, weight, owner_name, latest_month,
    measured_by_cutoff, std, bridge`. `bridge` sitede adı konmamış durumun bayrağıdır (`tree.ts:240-241` koşulunun
    değili): KR'ın kendi döneminin aylarında hiç satırı yok → `current` saklı özet, `latest_month None`, `std None`,
    `measured_by_cutoff True`.
  - Objective düğümü: `id, code, title_tr, owner_name, department_id, period_id, weight, krs`.
    Bölüm düğümü: `id, slug, name_tr, objectives`.
  - Kesim kuralı (`tree.ts:187,209-256`): `as_of_month = as_of[:7]`; aylar KR'ın **kendi** döneminden
    (`tree.ts:211-216`); `months = period_months` içinden `<= as_of_month` olanlar; `value_for_range` `None` dönerse
    `current = effective_start(k)` ve `measured_by_cutoff = False` (`tree.ts:248-250`); `std_figure` tam `as_of`
    tarihini alır (`tree.ts:251-254`). Eşleşen dönem yoksa `([], [])` (`tree.ts:162`).
- `measured_krs_of(krs) -> list` — `tree.ts:331-333`; `measured_only(depts) -> list` — `tree.ts:351-356`
- `std_krs_of(krs) -> list` — `queries/std.ts:33-39`
- `kr_pair(kr)`, `obj_pair(obj)`, `dept_pair(dept)`, `company_pair(depts)` → sözlük
  `{"annual": int, "std": int | None, "status_pct": int, "with_std": int, "measurable": int}` —
  `queries/std.ts:16-25,41-48,53-56,58-66,68-76,78-89`

- [ ] **Step 1: Failing tests.** Yardımcı `_satirlar(**ek)`: dönem `p26` (`p-2026-fy`, `2026-09-01..2027-08-31`, `active`)
  ve `p25` (`p-2025-fy`, `2025-09-01..2026-08-31`, `closed`); bölüm `d-sat` (`satis`, "Satış"); objective `o1` (`p26`);
  kullanıcı `u1` "Deniz Örnek". `m1..m4 = 2026-09..2026-12`. Sitenin `lib/queries/__tests__/tree.test.ts`
  senaryoları, bellek içi satırlarla (site tohum veritabanı kullanır; sayılar aynıdır):
  - `test_aylik_satiri_olmayan_ozetini_korur` (`:179`): saklı `current 42`, satır yok, kesim `m1-15` →
    `current 42`, `measured_by_cutoff True`, `latest_month None`, `std None`, `bridge True`
  - `test_kesim_dahil_toplar` (`:200`): `sum`, `m1 20, m2 40, m4 500`, kesim `m2-15` → `current 60`, `latest_month m2`
  - `test_ay_ortasi_kesim_tum_ayi_alir` (`:220`): `m1 40`; kesim `m1-01` ve `m1-28` → ikisi de `40`
  - `test_kesime_kadar_veri_yoksa_olculmemis` (`:237`): `avg`, `start 73`, yalnız `m3 60`, kesim `m1-15` →
    `current 73`, `measured_by_cutoff False`, `latest_month None`, `bridge False`
  - `test_sum_kesimden_sonra_sifir_okur` (`:257`): `sum`, `start 51500`, yalnız `m3`, kesim `m1-15` → `current 0`, ölçülmemiş
  - `test_measured_only` (`:295`): ölçülmemiş KR düşer, diğeri kalır
  - `test_her_kr_kendi_doneminin_aylari` (`:315`, Review Focus 2): `p25`'te `sum` KR, `2025-10 → 10`; `p26` KR'ı saklı
    `current 42`, satırı `2025-09 → 70` (kendi dönemi dışında); iki dönem, kesim `2025-10-15` →
    kapalı dönemin KR'ı `10`; diğeri `42`, `measured_by_cutoff True`
  - `test_donem_disi_satir_kopruye_duser` (`:375`): saklı `42`, tek satır `2027-09 → 70`, kesim `m1-15` → `42`, ölçülmüş,
    `latest_month None`, `measured_only` içinde
  - `test_avg_dolu_aylar` (`:436`): `avg`, `4.4, 4.5, 5.0`, kesim `m3-15` → `assertAlmostEqual((4.4 + 4.5 + 5.0) / 3)`
  - `test_last_bayat_ay` (`:456`): `last`, `m1 4.1, m2 4.2`, kesim `m4-15` → `current 4.2`, `latest_month m2`
  - `test_kesit_uc_kural` (`kesit-regression.test.ts:70`): `sum 20, 20, 500 → 40`; `avg 99, 99.4, 10 →` ≈ `99.2`;
    `last 30, 45, 99 → 45`; kesim `m2-15`; üçünde `latest_month m2`
  - `test_std_tamamlanan_aylar` (`:502`): `sum`, hedef 200, `m1 20, m2 30, m3 40`, kesim `m3-15` →
    `std.months_counted 2`, `months_filled 2`, `current 50`, `target ≈ 200 / 12 * 2`
  - `test_std_yalniz_kesim_ayi_doluysa_none` (`:529`): yalnız `m3 40`, kesim `m3-15` → `std None`
  - `test_iki_donem_std` (`:544`): `p25`'te `sum`, hedef 120, on iki ay × 10; kesim `2026-11-15` →
    `months_counted 12`, `target ≈ 120`, `current 120`
  - `test_bos_ya_da_bilinmeyen_donem` (`:143,:149`): `period_ids = []` ve `['yok']` → `([], [])`
  - Çiftler (`lib/queries/__tests__/std.test.ts`; `kr()` = `sum`, `start 0, current 900, target 3000`;
    `with_std()` = aynı + `std {current 900, target 1000, months_counted 4, months_filled 4}`):
    `test_kr_pair`: `with_std → annual 30, std 90, status_pct 90`; düz → `std None`, `status_pct == annual`,
    `with_std 0, measurable 1` · `test_obj_pair`: `kr@60` + `with_std@40` → `std 90`, `with_std 1, measurable 2` ·
    `test_dept_pair`: tek düz KR → `std None`, `status_pct == annual`, `0/1` ·
    `test_company_pair`: düz bölüm + StD'li bölüm → `std 90`, `1/2`
  - `test_periods_in_range` (`range.test.ts:33,:45`): beş dönem (`before 2025-01-01..2025-08-31`,
    `ends-on-from 2025-06-01..2025-09-01`, `inside 2025-10-01..2025-12-31`, `starts-on-to 2026-08-10..2026-10-31`,
    `after 2026-08-11..2026-12-31`), aralık `2025-09-01..2026-08-10` → `[ends-on-from, inside, starts-on-to]`; sıra eskiden yeniye
- [ ] **Step 2:** FAIL · **Step 3:** yaz · **Step 4:** `python3 -m unittest tests.test_okr_hesap -v` → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): ağaç, kesim ve StD/yıllık yüzde çiftleri"`

### Task 5: `okr_veri.py` iskeleti — bağlantı, `sema`, tablo okuma, izin dosyası

**Files:** Create `bin/okr_veri.py`, `tests/test_okr_veri.py`, `docs/okr-veri-izin.sql`

**Interfaces — Consumes:** `kalite_veri.baglanti_ac, guvenli_hata, hazirlanamadi, _tek_satir, js_yuvarla`.
**Produces:**
- `main(argv, ortam=None, baglan=None, bugun=None) -> int` — `bugun` (`YYYY-MM-DD`) yalnız test içindir, komut
  satırı bayrağı **yoktur**; verilmezse `okr_hesap.today_in_istanbul()`. Anahtar `OKR_READONLY_URL`; yoksa
  `**Hazırlanamadı:** OKR_READONLY_URL yok`, çıkış 1.
- `KAYNAK = "Nove PYS Postgres (okr_okuyucu, salt okunur)"`
- `TABLO_SORGULARI: dict[str, str]` — anahtarlar `periods, departments, users, objectives, key_results, monthly`;
  sütunlar Task 4'teki `rows` anahtarlarıyla birebir, sütun adı listeli (`kind::text`, `state::text`, `rollup::text`;
  `"start"` ve `"current"` tırnaklı); sıralama sitedeki gibi: `periods` `starts_on`, `departments` `sort_order`,
  `objectives` `code`, `key_results` `id` (`lib/queries/tables.ts:94-132`)
- `tablolari_oku(baglanti) -> dict` — `rows` sözlüğü (Task 4 biçimi)
- `checkin_sayisi(baglanti) -> int` — `SELECT count(*) FROM public.checkins`
- `sema_sorgulari() -> list[tuple[str, str]]` ve `sema_bas(baglanti)` — yalnız yapı ve sayım: `satir_sayilari`
  (yedi tablo için `count(*)`), `users_sutun_izinleri` (`information_schema.column_privileges`, `grantee = current_user`),
  `eposta_izni` (`SELECT has_column_privilege(current_user, 'public.users', 'email', 'SELECT')`; beklenen `False`),
  `app_settings_okunur` (`SELECT count(*) FROM public.app_settings`), `oturum`
  (`current_setting('default_transaction_read_only')`, `current_setting('statement_timeout')`). Her sorgu ayrı denenir;
  hata satırı `- <ad>: okunamadı (<HataTürü>)` basılır, `rollback` yapılır, betik durmaz (`kalite_veri.sema_bas` deseni).

`docs/okr-veri-izin.sql` (Kağan çalıştırır; `docs/kalite-veri-izin.sql` düzeninde, adım adım, ANAYASA §1 ve CLAUDE.md
Yasaklar alıntıları birebir):
```sql
-- ADIM 1 — ön kontrol (salt okunur). Beklenen: true. false ise DUR, bu dosyayı çalıştırma, Claude'a bildir.
SELECT relrowsecurity FROM pg_class WHERE oid = 'public.app_settings'::regclass;
-- ADIM 2
GRANT SELECT ON public.app_settings TO okr_okuyucu;
-- ADIM 3
CREATE POLICY okr_okuyucu_aralik ON public.app_settings FOR SELECT TO okr_okuyucu USING (key = 'default_range_start');
-- ADIM 4 — doğrulama (salt okunur). Beklenen: tek satır, okr_okuyucu_aralik, SELECT.
SELECT policyname, cmd, roles, qual FROM pg_policies WHERE schemaname = 'public' AND tablename = 'app_settings';
```

- [ ] **Step 1: Failing tests** (`tests/test_okr_veri.py`; `_SahteImlec` / `_SahteBaglanti` `test_kalite_veri.py:22-59`'daki gibi):
  - `test_url_yoksa_hazirlanamadi_rc1`: `main(["sema"], ortam={})` → 1, çıktı `**Hazırlanamadı:** OKR_READONLY_URL yok`
  - `test_kullanim_hatasi_rc2`: `main(["yok-boyle-komut"], ortam={})` → `SystemExit(2)`
  - `test_baglanti_salt_okunur_ve_kapanir`: `read_only is True`, `kapandi`, hiçbir SQL'de `statement_timeout` yok
  - `test_baglanti_hatasi_urli_sizdirmaz`: `baglan` `RuntimeError("could not connect to " + url)` atar; URL
    `postgresql://okr_okuyucu.proje:gizli-parola@ornek.pooler.test:5432/postgres` → çıkış 1, çıktıda
    `gizli-parola`, `ornek.pooler.test`, `okr_okuyucu.proje` **yok**
  - `test_sorgu_hatasi_hazirlanamadi_rc1`: imleç `execute`'ta URL içeren hata atar → 1, `**Hazırlanamadı:** sorgu başarısız (`…, URL parçası yok
  - `test_sema_hatada_durmaz`: `column_privileges` sorgusu `PermissionError` → çıkış 0,
    `- users_sutun_izinleri: okunamadı (PermissionError)`, `rollback_sayisi >= 1`
  - `test_sorgular_yalniz_select_ve_yasak_sutun_yok`: `TABLO_SORGULARI` ve `sema_sorgulari()`'nın her SQL'i `SELECT` ile başlar;
    hiçbirinde `\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|GRANT)\b`, `SELECT *`, `password`, `login_attempts`,
    `help_articles`, `\bnote\b` yok; `email` yalnız `has_column_privilege(` çağrısının içinde geçer
  - `test_tablolari_oku_sozluk_bicimi`: sahte satırlardan `rows["key_results"][0]` anahtarları Task 4 listesiyle aynı
  - `IzinDosyasiTesti`: dosya var; yorum dışı ifadelerin her biri
    `^(SELECT\b|GRANT SELECT ON public\.app_settings TO okr_okuyucu$|CREATE POLICY okr_okuyucu_aralik ON public\.app_settings FOR SELECT TO okr_okuyucu USING \(key = 'default_range_start'\)$)`;
    hiçbirinde `\b(INSERT|UPDATE|DELETE|DROP|ALTER|REVOKE|TRUNCATE)\b` yok; ANAYASA alıntısı
    `Prod veritabanına yazma yoktur: \`INSERT\`/\`UPDATE\`/\`DELETE\`, DDL ve migration yasak.` ve CLAUDE.md alıntısı
    `Veri kaynaklarına, prod veritabanına yazma; DDL ya da migration` hem dosyada hem kaynağında birebir
    (`test_kalite_veri.py:765-781` deseni)
- [ ] **Step 2:** Run `python3 -m unittest tests.test_okr_veri -v` → FAIL (`No module named 'okr_veri'`)
- [ ] **Step 3:** Yaz. `argparse` alt komutu şimdilik yalnız `sema`. `main`'in bağlantı / `try` / `finally` iskeleti
  `kalite_veri.main` ile aynı (`bin/kalite_veri.py:651-683`).
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): okr_veri.py iskeleti, sema, salt okunur tablo okuma, app_settings izin dosyası"`

### Task 6: Aralık çözümü, kapsam ve `donemler`

**Files:** Modify `bin/okr_veri.py`, `tests/test_okr_veri.py`

**Interfaces — Consumes:** Task 4–5. **Produces:**
- Ortak bayraklar (`donemler` ve `sema` dışındaki her komutta): `--donem <kod>` **ya da**
  `--baslangic YYYY-MM-DD --bitis YYYY-MM-DD` (ikisi birlikte); `--bolum <ad>`. `--donem` ile tarih birlikte
  verilirse ya da tarihin tek ucu verilirse `ap.error` (çıkış 2).
- `VARSAYILAN_BASLANGIC = "2025-09-01"` — `settings.ts:14`
- `varsayilan_baslangic(baglanti) -> tuple[str, str]` → `(tarih, kaynak)`; SQL
  `SELECT value FROM public.app_settings WHERE key = 'default_range_start'` (`settings.ts:6,24-28`). `kaynak`:
  `app_settings.default_range_start` · `yerleşik varsayılan — app_settings okunamadı (<HataTürü>)` (hatada `rollback`) ·
  `yerleşik varsayılan — app_settings satırı yok` · `yerleşik varsayılan — app_settings değeri geçersiz`
- `aralik_coz(args, rows, baglanti, bugun) -> dict | None` — `None` ise sebep basılmıştır. Sözlük:
  `from_, to, kaynak, as_of, donemler` (dönem sözlükleri, eskiden yeniye). Kurallar:
  tarih verildiyse o aralık (`range.ts:156-158`; geçersiz tarih ya da `from_ > to` → sebepli durma) · `--donem`
  verildiyse dönemin `starts_on..ends_on`'u (`range.ts:160-162`; bilinmeyen kod → sebepli durma, geçerli kodlar listelenir) ·
  hiçbiri yoksa `varsayilan_baslangic → bugun` (`range.ts:97-110`, `range-presets.ts:30`).
  `as_of = okr_hesap.as_of_cutoff(to, bugun)`; `donemler = periods_in_range(...)`; boşsa
  `**Hazırlanamadı:** <from>..<to> aralığına düşen dönem yok`.
- `kapsam_bolumu(komut, aralik, ek: dict, kayit: int) -> str` — satır sırası sabit:
  ```
  ## kapsam
  kaynak=Nove PYS Postgres (okr_okuyucu, salt okunur)
  komut=<komut>
  aralik=<from>..<to>
  aralik_kaynagi=<varsayılan (…kaynak…) | dönem <kod> | verilen tarih>
  kesim=<as_of> (aralık sonu ile bugünün küçüğü; Europe/Istanbul)
  donemler=<kod,kod>
  birlesik=evet — aralık <n> dönemi kapsıyor; site gibi birleştirildi      ← yalnız n > 1
  son_tamamlanan_ay=<YYYY-MM>
  birikim=değerler her KR'ın kendi döneminin ilk ayından kesime kadar birikir; ara dilim hesaplanmaz
  ana_yuzde=StD varsa StD, yoksa yıllık (sitenin rozet yüzdesi)
  hesap=Nove Performance d5d0e5d
  <ek anahtar=değer satırları>
  kayit=<n>
  ```
  Değerler `_tek_satir`'dan geçer (satır sahteciliği olmaz).
- `agac_hazirla(baglanti, args, bugun) -> tuple | None` → `(aralik, periods, depts, checkin)`; komutların ortak girişi.
- `donemler` komutu: dönem başına `- <kod>: tur=<kind> durum=<state> aralik=<starts_on>..<ends_on> objective=<n>`;
  ardından `## mali ceyrekler` — `state == 'active'` dönemin mali yılı için dört satır
  `- Ç<n>: <starts_on>..<ends_on>` ve bugünü içeren çeyrekte ` (bugün)` (`fiscal_quarter_range`); kapanış satırı:
  `not=dönemler yıllıktır; çeyrek sorusunda --baslangic <mali yıl başı> --bitis <çeyrek sonu> kullanılır, sayı birikmiştir`.

- [ ] **Step 1: Failing tests** (`bugun="2026-11-13"`; dönemler `p-2025-fy` kapalı, `p-2026-fy` açık):
  - `test_varsayilan_aralik_iki_donemi_birlestirir` (Review Focus 2): bayraksız → kapsamda `aralik=2025-09-01..2026-11-13`,
    `donemler=p-2025-fy,p-2026-fy`, `birlesik=evet — aralık 2 dönemi kapsıyor; site gibi birleştirildi`,
    `kesim=2026-11-13`, `son_tamamlanan_ay=2026-10`
  - `test_app_settings_degeri_kullanilir`: satır `2026-09-01` → `aralik=2026-09-01..2026-11-13`, `birlesik=` satırı yok
  - `test_app_settings_okunamazsa_dusus_gorunur` (Review Focus 4): sorgu `PermissionError` → çıkış 0,
    `aralik_kaynagi=varsayılan (yerleşik varsayılan — app_settings okunamadı (PermissionError))`, `rollback_sayisi >= 1`,
    tablo yine basılır; satır yok ve `2026-02-30` değerinde de karşılık gelen metin
  - `test_donem_bayragi`: `--donem p-2026-fy` → `aralik=2026-09-01..2027-08-31`, `kesim=2026-11-13` (gelecek kesilir)
  - `test_gecmis_aralik_kesilmez`: `--baslangic 2025-09-01 --bitis 2026-02-28` → `kesim=2026-02-28`, `son_tamamlanan_ay=2026-02`
  - `test_bilinmeyen_donem_sebepli_durur`: `--donem p-2030-fy` → 1,
    `**Hazırlanamadı:** dönem bulunamadı: p-2030-fy (geçerli: p-2025-fy, p-2026-fy)`
  - `test_gecersiz_tarih_sebepli_durur`: `--bitis 2026-02-30` → 1, `tarih geçersiz`; ters aralık → 1
  - `test_tek_uc_ve_cifte_bayrak_kullanim_hatasi`: yalnız `--baslangic` → `SystemExit(2)`; `--donem` + tarihler → `SystemExit(2)`
  - `test_araliga_donem_dusmuyor`: `--baslangic 2020-01-01 --bitis 2020-12-31` → 1, `aralığına düşen dönem yok`
  - `test_donemler_cli`: iki dönem satırı; `## mali ceyrekler` altında `- Ç1: 2026-09-01..2026-11-30 (bugün)`,
    `- Ç2: 2026-12-01..2027-02-28`
  - `test_kapsam_satir_sahteciligi_olmaz`: `--bolum "x\nkayit=999"` çıktısında `kayit=999` satırı yok
- [ ] **Step 2:** FAIL · **Step 3:** yaz · **Step 4:** `python3 -m unittest tests.test_okr_veri -v` → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): aralık çözümü, kapsam bölümü ve donemler komutu"`

### Task 7: `bolumler`, `objektifler`, `sirket`

**Files:** Modify `bin/okr_veri.py`, `tests/test_okr_veri.py`

**Interfaces — Consumes:** `agac_hazirla`, `kapsam_bolumu` (Task 6), çiftler (Task 4). **Produces:**
- `bolum_bul(depts, ad) -> dict | None` — `name_tr` ya da `slug` ile, Türkçe küçük harfe çevirerek
  (`İ → i`, `I → ı`, sonra `lower()`); bulunamazsa `**Hazırlanamadı:** bölüm bulunamadı: <ad> (geçerli: <adlar>)`.
- `sayi_yaz(x) -> str` — `"%.2f" % x`, sondaki `0` ve `.` atılır (`57500`, `99.2`, `4.47`)
- `cift_yaz(cift, olculebilir: bool) -> str` —
  `yuzde=<status_pct> std=<std|yok> yillik=<annual> durum=<DURUM_ADLARI> std_kapsam=<with_std>/<measurable>`;
  `olculebilir` değilse `yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok`
- `bolumler`: `- <ad>: <cift_yaz(dept_pair)> objective=<n> kr=<n>`. `olculebilir` = ölçülmüş ağaçta bölümün en az bir
  ölçülebilir KR'ı var (`progress.ts:73,121-125`). `--bolum` verilirse tek satır.
- `objektifler`: `- <bölüm> / <kod> <başlık>: donem=<kod> agirlik=<w|yok> <cift_yaz(obj_pair)> kr=<n> olculmeyen=<n>
  olculemeyen=<n> sorumlu=<ad|yok> en_dusuk_kr=<başlık> (%<status_pct>, agirlik=<w|yok>)`; aday yoksa `en_dusuk_kr=yok`.
  **En düşük KR kuralı (bu planın kararı — sitede karşılığı yok):** objective'in ölçülmüş ve ölçülebilir KR'ları
  içinde `kr_pair(kr)["status_pct"]` en küçük olan; eşitlikte ağırlığı büyük olan, sonra `id` sırası.
- `sirket`:
  ```
  - sirket: <cift_yaz(company_pair)>
  - sayim: bolum=<n> objective=<n> kr=<n> olculebilir=<n> olculmeyen=<n> olculemeyen=<n> ozetten=<n>
  - kr_dagilimi (n=<N>): Beklenenin Üzerinde=<n> (%<p>) · Beklenen=<n> (%<p>) · Beklenenin Altında=<n> (%<p>) · Gelişime Açık=<n> (%<p>) · Başlamadı=<n> (%<p>)
  - objective_dagilimi (n=<N>): …aynı beş bant…
  - gelisime_acik_kr=<n> (%59 ve altı; Başlamadı dahil)
  - checkin=<n>
  ```
  `kr_dagilimi` sitenin halkasıyla aynı kümedir: ölçülmüş **ve** ölçülebilir KR'lar, `status_of(kr_pair.status_pct)`
  (`overview.ts:202-215,253-257`); `gelisime_acik_kr` aynı kümede `is_open_to_development` (`overview.ts:231-234`).
  `objective_dagilimi` en az bir ölçülmüş ölçülebilir KR'ı olan objective'ler, `obj_pair.status_pct`. Paylar
  `js_yuvarla(100 * n / N)`'dir; `N == 0` ise pay yerine `—`. Kapsama `ek`:
  `paylar=betik hesabı; sitede sayım var, pay yok`. `checkin == 0` ise kapsama `checkin_notu=Nove PYS'de check-in kaydı yok` (B3).

- [ ] **Step 1: Failing tests** (fikstür: "Satış" — `O1` ağırlıksız iki KR: `sum` hedef 1200 `m1 100, m2 100` ve
  `avg` birim `%` hedef 90 başlangıç 50 `m1 70, m2 80`; "Finans" — `O1` tek KR `last` `(5, 5, 5)`, `m1 5, m2 5`
  (aylık satırı var, yine de ölçülemez); "Pazarlama" — objective yok;
  sorumlular "Deniz Örnek", "Ada Deneme"; `bugun="2026-11-13"`, `--donem p-2026-fy`):
  - `test_bolumler_cli`: Satış satırı `yuzde=82 std=82 yillik=40 durum=Beklenen std_kapsam=2/2 objective=1 kr=2`.
    Elle hesap (test bu sayılara dayanır, `okr_hesap` çıktısına değil): kesim `2026-11-13`, son tamamlanan ay `2026-10`.
    KR1 yıllık `200 / 1200 → 17`, StD `200 / (1200 / 12 × 2) → 100`. KR2 şu an `75`, yıllık ve StD
    `(75 − 50) / (90 − 50) = 62,5 → 63`. StD ortalaması `(100 + 63) / 2 = 81,5 → 82`; yıllık `(17 + 63) / 2 = 40`.
  - `test_bolumler_olculemez_bolum_tire`: Finans satırı `yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok`;
    Pazarlama satırı aynı sebep, `objective=0 kr=0`
  - `test_bolum_adi_buyuk_kucuk_ve_slug` (Review Focus 5): `--bolum satış`, `SATIŞ`, `satis` → aynı tek satır
  - `test_bolum_bulunamaz`: `--bolum Lojistik` → 1, `bölüm bulunamadı: Lojistik (geçerli: Finans, Pazarlama, Satış)`
  - `test_objektifler_en_dusuk_kr`: Satış `O1` satırında `en_dusuk_kr=<KR2 başlığı> (%63, agirlik=yok)`, `sorumlu=Deniz Örnek`
  - `test_objektifler_agirlikli`: `O1`'e `75 / 25` ağırlık → `yuzde=91` (`(100·75 + 63·25) / 100 = 90,75`)
  - `test_sirket_cli`: `- sirket: yuzde=82 …` (Finans ve Pazarlama ortalamaya girmez); `kr_dagilimi (n=2)` içinde
    `Beklenen=1 (%50)` ve `Beklenenin Altında=1 (%50)`; `olculemeyen=1`; `checkin=0` ve kapsamda
    `checkin_notu=Nove PYS'de check-in kaydı yok`
  - `test_sirket_bos_dagilim_pay_tire`: yalnız Finans → `kr_dagilimi (n=0)` ve paylar `—`
- [ ] **Step 2:** FAIL · **Step 3:** yaz · **Step 4:** `python3 -m unittest tests.test_okr_veri -v` → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): bolumler, objektifler ve sirket komutları"`

### Task 8: `kr` ve `eksik-veri`

**Files:** Modify `bin/okr_veri.py`, `tests/test_okr_veri.py`

**Interfaces — Consumes:** Task 6–7. **Produces:**
- `ORAN_NOTU = "aylık oranların ortalaması; ayların hacmi farklıysa gerçek orandan sapabilir"`;
  `oran_kr_mi(kr) -> bool` — `kr["rollup"] == "avg" and (kr["unit"] or "").strip() == "%"` (O3)
- `kr` komutu, KR başına tek satır:
  `- <bölüm> / <objective kodu> / <KR başlığı>: hedef=<t> su_an=<c> kalan=<t − c> birim=<unit|yok> kural=<sum|avg|last>
  yuzde=<status_pct> std=<n|yok> yillik=<annual> durum=<bant> son_dolu_ay=<YYYY-MM|yok> agirlik=<w|yok> sorumlu=<ad|yok>`
  ve duruma göre ekler:
  - ölçülemiyor (`not is_measurable`): `yuzde=— std=yok yillik=— durum=— sebep=ölçülemiyor (hedef = başlangıç)`; `su_an` basılır
  - ölçülmemiş (`not measured_by_cutoff`): `su_an=— kalan=— yuzde=— std=yok yillik=— durum=— sebep=kesime kadar aylık veri yok`
  - köprü (`bridge`): satır sonuna `not=aylık satır yok; saklı özet değer`
  - oran KR'ı: satır sonuna `oran_notu=evet`
  Çıktının sonunda `## olculemeyenler` — `—` taşıyan her KR `- <bölüm> / <kod> / <başlık>: <sebep>` (yoksa `- yok`).
  Kapsama `ek`: `son_dolu_ay=<çıktıdaki en büyük latest_month|yok>`, `kalan=hedef − şu an (betik hesabı)`, ve çıktıda
  en az bir oran KR'ı varsa `oran_notu=<ORAN_NOTU>`.
- `eksik-veri` komutu, üç başlık (boşsa altında `- yok`):
  `## hic aylik verisi yok` (köprü) · `## kesime kadar verisi yok` (ölçülmemiş) ·
  `## son tamamlanan ayda verisi yok` (`last_completed_month(as_of)` KR'ın kendi döneminin aylarındaysa ve o ayda değer
  yoksa; ilk iki gruptakiler burada yinelenmez). Satır: `- <bölüm> / <kod> / <başlık>: kural=<…> son_dolu_ay=<…|yok> sorumlu=<…|yok>`.
  Bunun için `load_tree` KR düğümüne `period_months` ve `filled_months` (sıralı liste) alanlarını ekle — sitede karşılığı
  olmayan iki taşıyıcı alandır, hesap değiştirmez; `# KAYNAK` başlığının altına "ek alan: okr_veri eksik-veri için" yaz.
  Kapsama `ek`: `hic=<n>`, `kesime_kadar=<n>`, `son_ay=<n>`.

- [ ] **Step 1: Failing tests** (Task 7 fikstürü + "Satış"a üç KR: `K3` `last` satırsız saklı `current 0`, hedef 10;
  `K4` `sum` yalnız `2026-12 → 5`; `K5` `sum` hedef 100 `m1 0, m2 0`):
  - `test_kr_dort_durum_ayri` (Review Focus 3): Finans KR'ı `sebep=ölçülemiyor (hedef = başlangıç)` ve `su_an=5`;
    `K4` `su_an=— kalan=— yuzde=—` ve `sebep=kesime kadar aylık veri yok`; `K3` `su_an=0 … yuzde=0` ve
    `not=aylık satır yok; saklı özet değer`; `K5` `su_an=0 … yuzde=0 std=0`, satırında `—` **yok**
  - `test_kr_oran_notu`: `avg` + `%` KR satırı `oran_notu=evet` ile biter; kapsamda `oran_notu=aylık oranların ortalaması; ayların hacmi farklıysa gerçek orandan sapabilir`;
    `avg` + birim `puan` KR'ında yok; `unit " % "` olanda var
  - `test_kr_oran_kr_yoksa_kapsamda_not_yok`: `--bolum Finans` → kapsamda `oran_notu=` satırı yok
  - `test_kr_son_dolu_ay_ve_kalan`: KR1 `hedef=1200 su_an=200 kalan=1000 … son_dolu_ay=2026-10`; kapsam `son_dolu_ay=2026-10`
  - `test_kr_olculemeyenler_bolumu`: `## olculemeyenler` altında tam iki satır (Finans KR'ı, `K4`); hepsi ölçülüyse `- yok`
  - `test_kr_bolum_filtresi`: `--bolum Satış` çıktısında Finans satırı yok, `kayit=5`
  - `test_eksik_veri_uc_grup`: `K3` yalnız ilk başlıkta; `K4` yalnız ikincide; bu testte eklenen `K6`
    (`sum`, yalnız `m1` dolu, `2026-10` boş) yalnız üçüncüde; kapsamda `hic=1`, `kesime_kadar=1`, `son_ay=1` satırları
  - `test_eksik_veri_bos`: her şey doluysa üç başlığın altında `- yok`, çıkış 0
  - `test_fikstur_adlari_uydurma` (B4): fikstürdeki `users` adlarının kümesi tam olarak `{"Deniz Örnek", "Ada Deneme"}`
- [ ] **Step 2:** FAIL · **Step 3:** yaz; `okr_veri.py` modül belgesine kullanım satırlarını ekle (`kalite_veri.py:1-17` düzeni)
- [ ] **Step 4:** `python3 -m unittest tests.test_okr_veri tests.test_okr_hesap -v` → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(okr): kr ve eksik-veri komutları; oran notu ve ölçülemeyenler"`

### Task 9: Canlı ölçüm ve form taslağı

**Files:** Modify `formlar/gelen/okr.md` (git dışı); bu plana `## Ölçüm` bölümü

- [ ] **Step 1 (canlı, salt okunur):** Run `python3 bin/okr_veri.py sema` → Expected (spec O1, 13.11 ölçümü):
  `departments 11`, `periods 3`, `objectives 55`, `key_results 118`, `kr_monthly_values 439`, `users 105`,
  `checkins 0`; `eposta_izni` `False`; `oturum` `on` ve `15s`. `app_settings_okunur` Kağan SQL'i çalıştırana kadar
  `okunamadı` olabilir — hata değildir. Çıktıyı bu planın `## Ölçüm` bölümüne yaz (bağlantı adresi yok).
  `**Hazırlanamadı:** OKR_READONLY_URL yok` gelirse dur ve Kağan'a bildir; `.env`'e bakma.
- [ ] **Step 2 (canlı):** Run `python3 bin/okr_veri.py sirket` ve `python3 bin/okr_veri.py bolumler --donem 2026-FY`
  → çıkış 0, `## kapsam` başta. Oran notu sayımı: `python3 bin/okr_veri.py kr --donem 2025-FY` çıktısında
  `oran_notu=evet` taşıyan satır **17**, `--donem 2026-FY`'de **1** (spec O3). Tutmazsa dur, farkı `## Ölçüm`'e yaz.
- [ ] **Step 3:** `formlar/gelen/okr.md`'yi düzelt (yalnız bu satırlar; §7 "İzinli komut"a **dokunma** — yalnız Kağan):
  - §3 tablo, "Nerede" hücresi: `` `okr_veri.py sirket, bolumler, objektifler, kr, eksik-veri, donemler` (Nove PYS veritabanı, `okr_okuyucu`, salt okunur) ``
  - §4 "ASLA" listesinde `Nove PYS'nin toplama sonucunu yeniden hesaplamak (olduğu gibi aktarır)` satırı yerine:
    `okr_veri.py'nin vermediği bir sayıyı türetmek ya da yüzdeyi kendisi hesaplamak (betiğin sayısı sitenin sayısıdır)`;
    ekle: `Veritabanına okr_okuyucu dışında bağlanmak ya da okr_veri.py dışında komut çalıştırmak` ·
    `Oran KR'ını (oran_notu=evet) notsuz vermek` · `Yalnız bir çeyreğin dilimini hesaplamak (sayı mali yıl başından birikir)` ·
    `Check-in kaydı yokken check-in'e dayanan soruya tahminle yanıt vermek`
  - §4 "Her yanıtta mutlaka": sonuna ` · ana yüzde StD'dir, yıllık yanında · aralık birden çok dönemi kapsıyorsa bunun söylenmesi`
  - §4 "Hangi sayıyı kim teyit eder" (girintili iki satır): `Tüm yüzdeler: Kağan` ·
    `Site hesabı (Nove Performance lib/domain ve lib/queries/{tree,std,range}.ts) değişirse bin/okr_hesap.py güncellenir ve üç sayılık karşılaştırma yinelenir: Kağan` (B1a)
  - §5: örneğe dayanak yolu ekle: `Dayanak satırları okr_veri.py çıktısındandır (✅, komut adıyla); "Ölçülemeyenler" kurul-yaniti düzeninde Bilinmeyenler bölümüne yazılır`
  - Dosyanın sonundaki revize notlarına tarihli satır: `13.11.2026: veri bağlantısı okr_veri.py (spec 2026-11-13-okr-danismani-design.md); §3, §4, §5 güncellendi; §7 İzinli komut Kağan'da.`
- [ ] **Step 4:** Formda telefon, e-posta, TC yok: Run `python3 -c "import sys; sys.path.insert(0,'bin'); import bekci; print(bekci.on_kontrol(open('formlar/gelen/okr.md', encoding='utf-8').read()))"` → Expected `[]`
- [ ] **Step 5:** `git commit -m "docs(plan): OKR canlı sema ölçümü"` (yalnız plan dosyası; form git dışı)

### Task 10: Kurulum (Kağan) ve ajan dosyası

**Files:** `takimlar/okr/*` (Kağan üretir), Create `.claude/agents/okr.md`, Modify `CLAUDE.md`, `NOVE-KURULUM.md`

- [ ] **Step 1 (Kağan):** `docs/okr-veri-izin.sql`'i Supabase SQL editöründe **adım adım** çalıştırır (Nove PYS projesi).
  ADIM 1 `false` dönerse durur. Kod bu adıma bağlı değildir (O8: betik `2025-09-01`'e düşer); sıra serbesttir.
- [ ] **Step 2 (Kağan):** `formlar/gelen/okr.md` §7'de `- İzinli komut (yalnız Kağan; boşsa yok): python3 bin/okr_veri.py`
  yazar; Task 9'daki düzeltmeleri okur; dosyayı `formlar/onayli/okr.md`'ye koyar.
- [ ] **Step 3 (ajan):** Run `python3 bin/formdan_takim.py okr --kuru` → Expected: `(kuru koşu: hiçbir dosya yazılmadı)`;
  basılan `takim.md`'de `tools: [Read, Write, Glob, Grep, Bash(python3 bin/okr_veri.py:*)]`,
  `gerekli_anahtarlar: [OKR_READONLY_URL]`, `renk: mavi`; `kurallar.md`'de B1a satırı ve oran notu yasağı.
  `durdu` gelirse sebepleri Kağan'a aynen ilet; formu ajan düzeltmez (`formlar/onayli/` kapalı).
- [ ] **Step 4 (Kağan):** kendi terminalinde `python3 bin/formdan_takim.py okr` → `yazildi`.
- [ ] **Step 5 (ajan):** Run `python3 bin/agents_uret.py` → `.claude/agents/okr.md` yazılır; `python3 bin/agents_uret.py --check` → çıkış 0;
  `python3 bin/ayar.py` → OKR kurulu, eksik anahtar yok.
- [ ] **Step 6 (ajan):** `CLAUDE.md` Danışmanlar tablosunda OKR satırı:
  `| OKR Danışmanı | \`takimlar/okr/\` | **kurulu** (<gün.ay.2026>) — veri \`bin/okr_veri.py\` (\`okr_okuyucu\`, salt okunur); yalnız soru, zamanlı rapor yok; hesap Nove Performance \`d5d0e5d\`'den taşındı (\`bin/okr_hesap.py\`) |`.
  `NOVE-KURULUM.md` Faz 6'ya `[x]` maddesi: `OKR veri okuyucusu: bin/okr_veri.py — Nove PYS veritabanından okr_okuyucu rolüyle salt okunur (OKR_READONLY_URL); komutlar sema, donemler, bolumler, objektifler, kr, eksik-veri, sirket; app_settings izni docs/okr-veri-izin.sql`.
- [ ] **Step 7:** Run `python3 -m unittest discover -s tests` → OK, `skipped=9`, sayı ≥ 795 (kurulu danışman sayısına bağlı test kırılırsa
  testi gevşetme: sebebini bul, Kağan'a bildir).
- [ ] **Step 8:** `git add takimlar/okr/takim.md takimlar/okr/kurallar.md takimlar/okr/durum.json .claude/agents/okr.md CLAUDE.md NOVE-KURULUM.md`
  → `git commit -m "feat(okr): OKR Danışmanı kuruldu — formdan takım, ajan dosyası, belgeler"`
  (`defter.md`, `kosu/`, `cikti/` git dışıdır.)

### Task 11: Doğrulama (Kağan)

- [ ] **Step 1 (ajan, canlı):** aynı dönem için üç komutu koştur; çıktılar KR başlığı ve sorumlu adı taşır, depo herkese
  açık (B4) — tam çıktı yalnız git dışı `takimlar/okr/cikti/`'ya; `## Ölçüm`'e yalnız üç yüzde (bölüm, objective kodu, KR sırası) yazılır:
  `python3 bin/okr_veri.py bolumler --donem 2026-FY` · `objektifler --donem 2026-FY --bolum <Kağan'ın seçtiği bölüm>` ·
  `kr --donem 2026-FY --bolum <aynı bölüm>`.
- [ ] **Step 2 (Kağan) — spec Doğrulama 3:** sitede `?period=2026-FY` ile **bir bölüm yüzdesi, bir objective, bir KR**
  rozetini betik çıktısındaki `yuzde=` ile yan yana koyar. Üçü de aynı olmalı. Fark varsa görev kapanmaz:
  fark `## Ölçüm`'e yazılır, `superpowers:systematic-debugging` ile kaynağı bulunur (yuvarlama, kesim günü, köprü).
- [ ] **Step 3 (Kağan) — spec Doğrulama 4:** `python3 -u bin/panel.py --port 8780`; dev panelde üç soru: kolay
  ("Şirket geneli OKR durumu ne?"), orta ("Hangi bölümün objective ilerlemesi en düşük, onu en çok hangi KR aşağı çekiyor?"),
  oran KR'ı içeren (17 KR'dan birinin bölümü). Üçüncü yanıt oran notunu taşır; üçü de dönem kodu, son dolu ay ve
  `—` sebeplerini yazar. Ajan tarayıcıyla panele girmez.
- [ ] **Step 4 (Kağan):** Nove Performance tarafına not (B1a): o deponun `CLAUDE.md`'sine tek satır —
  "`lib/domain` ya da `lib/queries/{tree,std,range}.ts` hesabı değişirse Nove AI `bin/okr_hesap.py` de güncellenir".
  Ajan o depoya yazmaz.

## Ölçüm (Task 9, 13.11.2026 — canlı, salt okunur)

- `sema`: periods 3 · departments 11 · users 105 · objectives 55 · key_results 118 · kr_monthly_values 439 ·
  checkins 0; `users` izinleri yalnız 7 sütun; `eposta_izni` False; `oturum` on | 15s;
  `app_settings_okunur` okunamadı (InsufficientPrivilege) — Kağan `docs/okr-veri-izin.sql`'i çalıştırana kadar
  beklenen. Spec O1 ölçümüyle birebir.
- **Dönem kodları `2024-FY`, `2025-FY`, `2026-FY`** (plan `p-2026-fy` id'sini kod sanmıştı; site de `code` ile
  eşler, `range.ts:160`). Task 9+ adımları ve spec düzeltildi; birim test fikstürleri uydurma kodla kaldı.
- Oran notu: `kr --donem 2025-FY` → 17, `kr --donem 2026-FY` → 1 (spec O3 ile aynı).
- `sirket` (varsayılan aralık 2025-09-01..2026-11-13, iki dönem birleşik): yuzde=60 std=60 yillik=28,
  Beklenenin Altında; std_kapsam 62/116; kr=118, ölçülemeyen 2, özetten 55.
- `bolumler --donem 2026-FY`: 11 bölüm; 3'ünde objective yok (`—`, ölçülebilir KR yok); 3'ü 0 / Başlamadı.

## Spec kusurları — devredildi

Spec onaylıdır. 1, 2, 3, 5 ve 7 spec'te düzeltildi (13.11, plan incelemesi). 6 Task 9 Step 3'te. 4 Kağan onayladı (13.11: en düşük `status_pct`'li ölçülmüş KR, eşitlikte büyük ağırlık).

1. **B1, satır atfı yanlış:** `dates.ts:823-826` yok (dosya 67 satır). Doğrusu `lib/domain/dates.ts:56-59` (`asOfCutoff`). Plan doğrusunu kullandı.
2. **B1a, yazılamayan iki yer:** not "danışmanın `kurallar.md`'sine" ve "Nove Performance tarafına" düşülecek deniyor.
   İkisi de ajana kapalı (`kurallar.md` insanın; Hedef dışı "sitenin koduna dokunma"). Plan: ilki form §4 üzerinden
   (Task 9 Step 3 → Kağan üretir), ikincisi Kağan'ın adımı (Task 11 Step 4).
3. **B2b, eksik bant:** spec dört bant sayıyor; `status.ts:18-24` beş bant döner (`pct < 1` → "Başlamadı"). Plan beşini taşıdı.
4. **B2, tanımsız ölçüt:** "objective'i en çok aşağı çeken KR"ın sitede karşılığı yok. Plan "en düşük `status_pct`'li
   ölçülmüş KR; eşitlikte ağırlığı büyük olan" kuralını koydu ve alanı `en_dusuk_kr` diye adlandırdı (Task 7). Kağan teyit etsin.
5. **O1 ile O8 çelişiyor:** O1 `app_settings` iznini "kurulum yapıldı" listesinde sayıyor, O8 "verilir (Kağan çalıştırır)"
   diyor. Plan verilmemiş sayar; `sema` ölçer (Task 9 Step 1).
6. **Form §4 ile B1 çelişiyor:** formdaki "toplama sonucunu yeniden hesaplamak (olduğu gibi aktarır)" satırı, yüzdenin
   veritabanında hazır durmadığı gerçeğiyle (B1) çelişir. Task 9 Step 3 satırı yeniden yazar; son söz Kağan'da.
7. **B7 ile `kurul-yaniti` düzeni:** B7 "Ölçülemeyenler" bölümü ister; form hattının ürettiği çıktı sözleşmesi
   Kısa yanıt · Dayanak · Bilinmeyenler · Not'tur. Plan "Ölçülemeyenler → Bilinmeyenler" eşlemesini forma yazdı (Task 9).

## Self-Review

- **Spec kapsamı:** O1 → Task 5, 9 · O2 → kısıt yok, komutlarda bölüm sınırı yok · O3 → Task 8 · O4 → tempo kurulmaz
  (form §6) · O5 → form · O6 → form §2 (değişmedi) · O7 → Task 4, 7 (`cift_yaz`) · O8 → Task 5 (SQL), 6 (düşüş) ·
  B1 → Task 1–4 · B1a → Task 1 (başlık testi), 9, 11 · B2 → Task 5–8 (yedi komut; fazlası yok) · B2a → Task 6
  (`birikim`, mali çeyrekler) · B2b → Task 1, 7 · B3 → Task 7 · B4 → Task 8 (`test_fikstur_adlari_uydurma`) · B5 → Task 5 ·
  B6 → Task 10 · B7 → Task 8, 9 · Doğrulama 1 → her görev · 2 → Task 9 · 3–4 → Task 11.
- **Anti-hedefler:** yüzde farkı → Task 11 Step 2 · danışmanın aritmetiği → `kalan` ve paylar betikte, form §4 yasağı ·
  ölçülemez KR'ın 0 sayılması → Task 1, 8 · bağlantı dizesi sızması → Task 5 · notsuz oran KR'ı → Task 8, form §4.
- **Ad tutarlılığı:** `status_pct`, `with_std`, `measurable`, `measured_by_cutoff`, `bridge`, `latest_month`,
  `period_months`, `filled_months` Task 4, 7, 8'de aynı yazılır. `agac_hazirla` Task 6'da tanımlanır, 7–8 kullanır.
- **Bilerek dışarıda:** `requiredPerMonth`, trend, veri giriş yardımcıları, objective/KR kodu filtresi, zamanlı rapor,
  `.env.example` satırı (ajana kapalı; isterse Kağan ekler).
- **Açık risk:** Task 7–8'deki beklenen sayılar elle hesaplandı (plan yazılırken koşturulmadı). `app_settings`'te RLS
  kapalıysa SQL ADIM 1 durur ve karar Kağan'a döner.

## Bitirme

- [ ] `python3 -m unittest discover -s tests` → `OK (skipped=9)`, test sayısı ≥ 795 (taban `Ran 795 tests`); gerçek sayı PR'a yazılır
- [ ] `python3 bin/agents_uret.py --check` → çıkış 0
- [ ] `python3 bin/ayar.py` → OKR kurulu, eksik anahtar yok
- [ ] `python3 bin/okr_veri.py sema` → 13.11 ölçümüyle tutarlı; e-posta kapalı
- [ ] `git grep -n "OKR_READONLY_URL=" -- . ':!docs'` → eşleşme yok (değer hiçbir dosyada)
- [ ] Kağan: üç sayılık site karşılaştırması aynı (Task 11 Step 2); dev panelde üç soru (Step 3)
- [ ] `docs/superpowers/PLANS.md` satırı güncel
