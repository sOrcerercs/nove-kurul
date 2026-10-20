---
durum: yazildi
guncelleme: 2026-10-19
dal: feature/quality-db-reader
pr: -
bekleyen: -
---

# Kalite ajanının veri okuyucusu — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (Kağan'ın seçimine göre) ya da
> superpowers:subagent-driven-development. Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.

**Goal:** Kalite ajanı, SDR Analyzer veritabanını `qa_okuyucu` rolüyle salt okunur okuyan `bin/kalite_veri.py`'yi
soruya göre çağırıp Raporlar → Raporlarım ile aynı ekip/temsilci/kriter/koçluk rakamlarını alsın.

**Architecture:** Tek betik, alt komutlar. Sorgu kurucular (SQL + parametre döner) ve toplayıcılar (satır → tablo)
saf fonksiyon; bağlantı yalnız `main`'de. Ajanın tek yeni izni `Bash(python3 bin/kalite_veri.py:*)`; form hattı
bunu §7'deki yeni alandan `tools`'a yazar.

**Tech Stack:** Python 3 stdlib + `psycopg` (v3, kurulu), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-19-quality-db-reader-design.md` (Kağan onayı 19.10.2026)

## Global Constraints

- Dal `feature/quality-db-reader` (spec commit'leri `1944eeb`, `ac67656`). Taban: `python3 -m unittest discover -s tests` → `Ran 468 tests` · `OK (skipped=8)`.
- Bağlantı yalnız `QA_READONLY_URL` (`.env`, `ayar.ortam_yukle()`); başka rol/URL yok. Adres hiçbir çıktıya, loga, hata mesajına yazılmaz.
- Yalnız `SELECT`. Her bağlantıda `read_only = True`, `SET statement_timeout = '15s'`, `connect_timeout=20`.
- **Raporlarım kuralı** (spec "Referans ekran"; `sdr-analyzer/app/api/reports/auto/route.ts:19-50`, `app/lib/reportAggregation.ts`):
  - `callDate >= <baslangic> 00:00:00` ve `<= <bitis> 23:59:59` — sunucu saatinde. Canlı sunucunun saat dilimi Task 1'de ölçülür; varsayılan UTC.
  - kayıt sahibinin rolü `AGENT` ya da `TEAM_LEADER`; ekip üyeliği: `User.isActive = true` ve `User.teamId = <ekip>`
  - sayım: `Evaluation."callClassification" IS NULL OR = 'CONNECTED_QUALIFIED'` (`callVisibility.ts:90`)
  - ortalama kayıt başına; **ekip/özet ortalaması tam sayıya** (`Math.round`), **temsilci ortalaması bir haneye** (`Math.round(x*10)/10`). JS yuvarlaması: `floor(x + 0.5)` — Python `round()` kullanılmaz (70.5 → 71).
- `qa_degerlendirme` / `qa_kriter` görünümleri **değiştirilmez** (qa-hatti kullanıyor). Ek izin gerekirse yeni `GRANT`/görünüm SQL'i yazılır, **Kağan çalıştırır**.
- Okunmaz ve çıktıya girmez: `transcript`, `report`, `customerName`, kanıt alıntıları, hasta bilgisi (rol zaten kapalı).
- Her durma görünür sebep döndürür: stdout'a `**Hazırlanamadı:** <sebep>`, çıkış kodu 1. Kullanım hatası 2.
- Ajan bu betiği koşturabilir (salt okunur). Form hattında yazan koşu Kağan'ın (K1); `formlar/onayli/` ajana kapalı.

## Review Focus

1. Bağlantı hatası mesajı adresi/parolayı sızdırmaz (psycopg mesajı DSN içerebilir) — Task 2 testi.
2. Ay sınırı: `--bitis 2026-10-31` 31 Ekim 23:59:59'u dahil eder, 1 Kasım 00:00'ı etmez — Task 2 testi.
3. Boş sonuç: ekip adı yanlış ya da dönemde kayıt yok → sessiz "0" değil, sebepli uyarı — Task 3 testi.
4. Pasif temsilci ve `AGENT/TEAM_LEADER` dışı rol (ör. MANAGER'ın kaydı) sayılmaz — Task 3 testi (SQL'de koşul var mı).
5. Kriter verisi olmayan ekip "0 kaçırma" diye görünmez; kapsam dışı olarak adıyla yazılır — Task 4 testi.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `bin/kalite_veri.py` | Alt komutlar, sorgu kurucular, toplayıcılar, biçim, bağlantı | Yeni (Task 1–5) |
| `tests/test_kalite_veri.py` | Sahte imleçle birim testleri | Yeni (Task 1–5) |
| `bin/formdan_takim.py` | §7 "İzinli komut" → `tools` ve koşu adımı | Değişir (Task 6) |
| `formlar/DANISMAN-FORMU.md` | §7'ye yeni satır | Değişir (Task 6) |
| `tests/test_formdan_takim.py`, `tests/fikstur/form/kalite.md` | Yeni alanın testleri | Değişir (Task 6) |
| `docs/kalite-veri-izin.sql` | Gerekirse `qa_okuyucu`'ya ek izin (Kağan çalıştırır) | Yeni, koşullu (Task 1) |
| `formlar/gelen/kalite.md` | Formun revize taslağı (§3 DB, §4, §7) — git dışı | Değişir (Task 7) |
| `NOVE-KURULUM.md`, `CLAUDE.md` | Faz 4 maddesi, Kalite durumu | Değişir (Task 7) |

---

### Task 0: Bağlantı adresi (Kağan)

- [ ] **Step 1:** Kağan şu satırı **kendi** çalıştırır (ajan `.env` okuyamaz, değeri görmez):

  `! grep '^QA_READONLY_URL=' ~/kagan-sirketi/.env >> ~/Desktop/"Nove AI"/.env`

- [ ] **Step 2:** Run: `python3 -c "import sys; sys.path.insert(0,'bin'); import ayar; ayar.ortam_yukle(); print(ayar.eksik_anahtarlar(['QA_READONLY_URL']))"` → Expected: `[]`

### Task 1: İskelet, `sema` alt komutu ve izin ölçümü

**Files:** Create `bin/kalite_veri.py`, `tests/test_kalite_veri.py`; koşullu `docs/kalite-veri-izin.sql`
**Interfaces — Produces:**
- `main(argv, ortam=None, baglan=None) -> int` — `baglan(url) -> bağlantı` enjekte edilebilir (test için)
- `sema_sorgulari() -> list[tuple[str, str]]` — (ad, SQL); yalnız yapı ve sayım, içerik yok
- `hazirlanamadi(sebep: str) -> str`

- [ ] **Step 1: Testler** — `class SemaTesti`:
  - `test_url_yoksa_hazirlanamadi_rc1`: `main(["sema"], ortam={})` → rc 1, stdout `**Hazırlanamadı:** QA_READONLY_URL yok`
  - `test_sema_sorgulari_icerik_okumaz`: hiçbir SQL `transcript|report"|customerName|evidence|medicalFlags` içermez; hepsi `SELECT` ile başlar
  - `test_sema_sorgulari_sayim_ve_izin_kapsar`: adlar arasında `izinler` (`information_schema.column_privileges`, `grantee = current_user`, tablolar `Evaluation`, `User`, `Team` ve adında `weekly`/`nomination` geçenler), `sinif_farki` (sütun ile `reportData->>'callClassification'` farklı olan kayıt **sayısı**), `saat_dilimi` (`SHOW timezone`) var
- [ ] **Step 2:** `python3 -m unittest tests.test_kalite_veri -v` → FAIL `ModuleNotFoundError: kalite_veri`
- [ ] **Step 3:** Uygula. `main`: `ayar.ortam_yukle()` (ortam verilmemişse), argparse alt komutları; bağlantı `psycopg.connect(url, connect_timeout=20)`, `read_only=True`, `statement_timeout`. `sema` her sorguyu ayrı dener; izin hatası satırı `- <ad>: okunamadı (<HataTürü>)` olarak basılır, betik durmaz.
- [ ] **Step 4:** Test → PASS. **Step 5:** Commit `feat(kalite): kalite_veri iskeleti ve sema ölçümü`
- [ ] **Step 6: Canlı ölçüm (salt okunur):** `python3 bin/kalite_veri.py sema` — çıktı ledger'a ve plan sonuna "Ölçüm" olarak yazılır: okunabilen sütunlar (özellikle `Evaluation.callClassification`, `isActive`, `role`, `coachingDone`, `agentRead`), `sinif_farki` sayısı, haftanın çağrısı tabloları, `timezone`.
- [ ] **Step 7 (koşullu):** `Evaluation.callClassification` ya da `User.isActive`/`role` okunamıyorsa `docs/kalite-veri-izin.sql` yaz: yalnız `GRANT SELECT ("<sütun>", …) ON public."<Tablo>" TO qa_okuyucu;` satırları, `kagan-sirketi/docs/qa-gorunumler.sql` gibi adım adım ve "Kağan çalıştırır" başlığıyla. **Dur, Kağan'a ver**; çalıştırınca Step 6'yı tekrarla. Görünüm değiştirilmez.

### Task 2: Ortak çekirdek — tarih, kural, yuvarlama, biçim, hata maskesi

**Interfaces — Produces:**
- `gun_siniri(baslangic: str, bitis: str) -> tuple[datetime, datetime]` — `YYYY-MM-DD`; bitiş `23:59:59`; ters aralık → `ValueError`
- `SAYIM_KOSULU: str` — SQL parçası (`e."callClassification" IS NULL OR e."callClassification" = 'CONNECTED_QUALIFIED'`) + rol/aktiflik koşulu `UYE_KOSULU`
- `js_yuvarla(x: float, hane: int = 0) -> float` — `floor(x*10**hane + 0.5) / 10**hane`
- `kapsam_bolumu(komut, baslangic, bitis, filtre: dict, kayit: int) -> str` — `## kapsam` + `anahtar=değer` satırları (kaynak, aralık, saat dilimi, kural, kayıt)
- `guvenli_hata(hata: Exception, url: str) -> str` — tür adı + mesaj; `url`, `://` sonrası kimlik ve `password=` parçaları `***` ile değiştirilmiş

- [ ] **Step 1: Testler** — `class CekirdekTesti`:
  - `test_ay_siniri_dahil`: `gun_siniri("2026-10-01","2026-10-31")` → (`2026-10-01 00:00:00`, `2026-10-31 23:59:59`)
  - `test_ters_aralik_hata`: `gun_siniri("2026-10-10","2026-10-01")` → `ValueError`
  - `test_js_yuvarla`: `js_yuvarla(70.5) == 71`, `js_yuvarla(70.45, 1) == 70.5`, `js_yuvarla(-0.5) == 0` (JS `Math.round(-0.5)` = -0 → 0)
  - `test_hata_mesaji_adres_sizdirmaz`: `guvenli_hata(Exception('connection to "postgresql://qa:gizli@h:5432/db" failed'), "postgresql://qa:gizli@h:5432/db")` içinde `gizli` ve `qa:` yok
  - `test_sayim_kosulu_panelle_ayni`: `SAYIM_KOSULU` içinde `"callClassification" IS NULL` ve `'CONNECTED_QUALIFIED'`; `UYE_KOSULU` içinde `'AGENT'`, `'TEAM_LEADER'`, `"isActive"`
- [ ] **Step 2:** FAIL → **Step 3:** uygula → **Step 4:** PASS → **Step 5:** Commit `feat(kalite): ortak çekirdek — Raporlarım kuralı, JS yuvarlama, hata maskesi`

### Task 3: `ekipler` ve `ekip-ozet`

**Interfaces — Consumes:** Task 2. **Produces:**
- `ekip_ozet_sorgusu(bas, bit, tip: str | None) -> tuple[str, dict]` — satır: `(ekip, temsilci_id, puan)` ya da ekip başına `(ekip, toplam, adet, temsilci_sayisi)`; seçim uygulayıcının
- `ekip_tablosu(satirlar) -> list[dict]` — `{"ekip", "ortalama", "kayit", "temsilci"}`, ortalama `js_yuvarla(toplam/adet)`
- `karsilastir(simdi: list[dict], onceki: list[dict]) -> list[dict]` — ekle `onceki_ortalama`, `onceki_kayit`, `fark`; düşüşe göre sıralı
- CLI: `ekipler`, `ekip-ozet --baslangic --bitis [--karsilastir-baslangic --karsilastir-bitis] [--tip first|second] [--ekip <ad>]`

- [ ] **Step 1: Testler** — `class EkipOzetTesti` (sahte satırlarla):
  - `test_kayit_basina_agirlikli`: ekip A: temsilci1 puanları [80,80,80], temsilci2 [50] → ortalama `js_yuvarla(290/4)=73` (temsilci ortalamalarının ortalaması 65 **değil**), kayit 4, temsilci 2
  - `test_karsilastir_dususe_gore_sirali`: A 78→71, B 70→72 → ilk satır A, `fark == -7`
  - `test_sorgu_kurallari_tasir`: `ekip_ozet_sorgusu(...)[0]` içinde `SAYIM_KOSULU`, `UYE_KOSULU`, `"callDate" >=` ve `<=` var; parametreler gün sınırları
  - `test_bos_sonuc_uyari`: satır yoksa çıktı `**Hazırlanamadı:** <aralık> için sayılabilir kayıt yok` ve rc 1
  - `test_ekip_adi_bulunamaz`: `--ekip Olmayan` → sebepte mevcut ekip adları listelenir, rc 1
  - `test_cikti_kapsam_ve_payda`: çıktıda `## kapsam`, her ekip satırında `kayit=` ve `temsilci=`; Second Call içeriyorsa `not=canlı Second Call formülü deploy bekliyor`
- [ ] **Steps 2–5:** FAIL → uygula → PASS → Commit `feat(kalite): ekipler ve ekip-ozet`

### Task 4: `temsilci-ozet` ve `kriterler`

**Produces:**
- `temsilci_tablosu(satirlar) -> list[dict]` — `{"temsilci", "ekip", "ortalama"(1 hane), "kayit"}`
- `kriter_tablosu(satirlar, ekipler_tum: list[str]) -> tuple[list[dict], list[str]]` — (kriter satırları `{"kriter_id","kriter","kaldi","kismi","gecti","oran_kaldi"}` kaldıya göre sıralı, kriter verisi olmayan ekipler)
- CLI: `temsilci-ozet --baslangic --bitis [--ekip]`, `kriterler --baslangic --bitis [--ekip] [--tip]`

Kriter satırları `qa_kriter`'den, `eval_id` ile `Evaluation`'a bağlanarak `SAYIM_KOSULU` + `UYE_KOSULU` uygulanır.

- [ ] **Step 1: Testler** — `class TemsilciKriterTesti`:
  - `test_temsilci_bir_hane`: [70, 71] → `70.5`
  - `test_az_kayitli_temsilci_isaretli`: 2 kayıtlı temsilci satırında `az_ornek=evet` (kurallar.md: 3'ten az "en iyi" seçilmez)
  - `test_kriter_kaldiya_gore_sirali_ve_oranli`: `oran_kaldi = kaldi/(kaldi+kismi+gecti)` iki hane
  - `test_kriter_verisi_olmayan_ekip_adiyla`: ekip B'nin satırı yoksa ikinci dönüş `["B"]`; çıktıda `kapsam_disi=B` (Review Focus 5)
- [ ] **Steps 2–5:** FAIL → uygula → PASS → Commit `feat(kalite): temsilci-ozet ve kriterler`

### Task 5: `kocluk` (ve koşullu `haftanin-cagrisi`)

**Produces:** `kocluk_tablosu(satirlar) -> list[dict]` — temsilci başına `{"temsilci","ekip","kayit","kocluk_yapilan","okunan","okunmayan"}`; CLI `kocluk --baslangic --bitis [--ekip]`.
Alanlar `Evaluation."coachingDone"` ve `"agentRead"` (qa_ozet.py'nin okuduğu); Task 1 ölçümü başka adlar gösterirse onları kullan ve plan sonuna yaz.

- [ ] **Step 1: Testler** — `test_kocluk_okunmayan_sayisi`: kocluk_yapilan 4, okunan 1 → okunmayan 3; `test_gelisme_yok`: çıktıda `kocluk_sonrasi_gelisme=— (ölçütü tanımlı değil; teyit: Quality Supervisor)`
- [ ] **Steps 2–5:** FAIL → uygula → PASS → Commit `feat(kalite): kocluk`
- [ ] **Step 6 (koşullu):** Task 1 ölçümünde haftanın çağrısı tabloları okunabiliyorsa `haftanin-cagrisi --hafta YYYY-Www` aynı desenle (test + uygulama) eklenir. Okunamıyorsa eklenmez; ajan bu soruya `—` ve "veri rolde kapalı" yazar (Task 6'daki koşu adımı metni bunu söyler).

### Task 6: Form hattı — §7 "İzinli komut"

**Files:** `bin/formdan_takim.py` (`BILINEN[7]`, `oku()`, `takim_md()`), `formlar/DANISMAN-FORMU.md`, `tests/test_formdan_takim.py`, `tests/fikstur/form/kalite.md`
**Produces:** form alanı `- İzinli komut (yalnız Kağan; boşsa yok): python3 bin/kalite_veri.py` → `form["izinli_komut"]: str`;
`takim.md` `tools: [Read, Write, Glob, Grep, Bash(<komut>:*)]` ve koşu adımı 3'e ek cümle:
*"Veriyi yalnız `<komut> <alt-komut> …` ile al; çıktının `## kapsam` bölümünü yanıtta kaynak olarak yaz; `Hazırlanamadı` gelirse sayı uydurma, sebebi Bilinmeyenler'e yaz."*

- [ ] **Step 1: Testler:**
  - `test_izinli_komut_tools_a_eklenir` (fikstüre satır eklenmiş): `ayar.frontmatter(...)["tools"][-1] == "Bash(python3 bin/kalite_veri.py:*)"`
  - `test_izinli_komut_yoksa_tools_degismez`: alan boş → `tools == ["Read","Write","Glob","Grep"]`
  - `test_izinli_komut_yalniz_bin_altinda`: `rm -rf /`, `python3 ../x.py`, `curl …` → `deger_sorunlari` sebebi `§7 İzinli komut yalnız 'python3 bin/<ad>.py' olabilir`
  - `test_koşu_adimi_komutu_soyler`: `takim.md` gövdesinde `python3 bin/kalite_veri.py` ve `Hazırlanamadı`
  - şablon testi: boş şablon hâlâ `eksikler` = 5 (yeni alan zorunlu değil); `BILINEN[7]` yeni öneki içerir
- [ ] **Steps 2–5:** FAIL → uygula → `python3 -m unittest discover -s tests` PASS → Commit `feat(form): §7 izinli komut → tools`

### Task 7: Kalite formunun revizesi ve belgeler

- [ ] **Step 1:** `formlar/gelen/kalite.md`'yi güncelle (git dışı): §3 veri tablosu `qa_okuyucu` kaynaklarıyla (Evaluation, User, Team, qa_kriter; `kalite_veri.py` alt komutları), §4 ilk "Asla" maddesi → *"Veritabanına `qa_okuyucu` dışında bağlanmak ya da `kalite_veri.py` dışında komut çalıştırmak"*, §7 `Gerekli anahtarlar: QA_READONLY_URL` ve `İzinli komut: python3 bin/kalite_veri.py`. `formdan_takim.oku/eksikler/bilinmeyen_alanlar/deger_sorunlari/kisisel_veri` → hepsi boş (Run: aynı tek satırlık kontrol, Expected `[]`).
- [ ] **Step 2:** Kağan kendi Terminal'inde: `cp formlar/gelen/kalite.md formlar/onayli/kalite.md && python3 bin/formdan_takim.py kalite --yeniden` → fark gösterilir, `yazıldı:`. Ardından ajan: `python3 bin/agents_uret.py`, testler.
- [ ] **Step 3:** `NOVE-KURULUM.md` Faz 4 "SDR Analyzer okuma betiği" maddesi `[x]` (veritabanı yolu, `qa_okuyucu`); `CLAUDE.md` Kalite satırı "kurulu — veri `kalite_veri.py`". Commit `docs(kalite): veri okuyucu kuruldu`.

### Task 8: Tutarlılık ölçümü (canlı, salt okunur)

- [ ] **Step 1:** Run: `python3 bin/kalite_veri.py ekip-ozet --baslangic 2026-10-01 --bitis 2026-10-19` → ekip tablosu.
- [ ] **Step 2:** Kağan Raporlarım'da aynı aralığı ve **bir ekibin temsilcilerini** seçip özet ortalamasını ve kayıt sayısını söyler.
- [ ] **Step 3:** Fark 0 → plan sonuna "Ölçüm"e yaz. Fark ≠ 0 → superpowers:systematic-debugging: önce saat dilimi (Task 1 ölçümü), sonra pasif/rol kuralı, sonra sınıf sütunu. Kural düzeltmesi Task 2 testine eklenir.

---

## Self-Review

| Spec | Task |
|---|---|
| `qa_okuyucu`, `QA_READONLY_URL`, `.env` | 0, 1, Global |
| Hesabı betik yapar (ağırlıklı, yuvarlama) | 2, 3 |
| Ajan veriyi kendisi ister, özel dilim | 3–5 (parametreli alt komutlar), 6 (izin) |
| Referans ekran Raporlarım, fark 0 | Global kuralı, 8 |
| Koçluk ilk sürümde, haftanın çağrısı koşullu | 5 |
| Önce mevcut izin; görünüm değişmez; yeni izin Kağan'ın | 1 Step 7, Global |
| Kriter kapsamı ölçülür, kapsam dışı ekip adıyla | 1 Step 6, 4 |
| Form §3/§4/§7 revizesi, `--yeniden` Kağan | 6, 7 |
| `Bash(...)` izninin yalnız bu komuta izin verdiğinin doğrulanması | Bitirme (Kağan onayıyla küçük canlı deneme) |

Bilerek dışarıda (spec "Hedef değil"): zamanlayıcı, API yolu, panel kartı.
Tür tutarlılığı: `js_yuvarla`, `gun_siniri`, `SAYIM_KOSULU`, `UYE_KOSULU`, `kapsam_bolumu`, `guvenli_hata` Task 2'de tanımlı; 3–5 bunları kullanır. Bağlantı: her yeni fonksiyon `main`'in alt komut dalından çağrılır; `test_*_cli` testleri `main([...], ortam=…, baglan=sahte)` ile alt komutları gerçekten koşturur (her Task'ta biri).

## Bitirme

- [ ] `python3 -m unittest discover -s tests` → 468 + yeni testler, `OK (skipped=8)`
- [ ] `python3 bin/agents_uret.py --check` → `OK: agents güncel`
- [ ] `python3 bin/dagitici.py --cakisma` → `0`
- [ ] `python3 bin/kos.py kalite --kuru` → `gerekli anahtarlar: QA_READONLY_URL`, eksik anahtar uyarısı yok
- [ ] `grep -c "QA_READONLY_URL=" -r takimlar sirket-log .claude/agents 2>/dev/null` → hiçbir dosyada adres yok
- [ ] **Kağan onayıyla (küçük ücret):** `claude -p "python3 bin/kalite_veri.py ekipler çalıştır, sonra 'ls' çalıştır" --model haiku --allowedTools "Read,Bash(python3 bin/kalite_veri.py:*)" --max-budget-usd 0.05 --output-format json` → ilk komut çalışır, `ls` reddedilir (`permission_denials` dolu)
- [ ] Task 8 ölçümü: fark 0

## Ölçüm

(Task 1 Step 6 ve Task 8 sonuçları buraya yazılır.)

### Task 1 — canlı `sema` ölçümü (qa_okuyucu, saat dilimi UTC)
- Okunabilir `Evaluation`: agentId, agentRead, agentReadAt, callDate, callType, coachingDone, coachingDoneAt, id, score, sectionScores, unassigned, weakCriteria
- Okunabilir `Team`: id, leaderId, name
- Okunabilir `User`: id, isActive, name, role, teamId
- `qa_kriter` görünümü okunabilir (28460 satır)
- OKUNAMAYAN: `Evaluation."callClassification"` (SAYIM_KOSULU için gerekli), `Evaluation."coachingSeenAt"` (kocluk için gerekli); `sinif_farki` InsufficientPrivilege ile düştü; WeeklyBestCall tablolarına erişim yok
- Sonuç: Step 7 tetiklendi -> `docs/kalite-veri-izin.sql` (Kağan çalıştırır; ADIM 1 zorunlu, ADIM 2 isteğe bağlı, ADIM 3 doğrulama). İzin verilince `sema` tekrarlanır.
