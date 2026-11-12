---
durum: tamamlandi
guncelleme: 2026-11-12
dal: feature/panel-canli
pr: 20
bekleyen: -
---

# Panel canlı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (önerilen) ya da
> superpowers:executing-plans. Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.

**Goal:** Kurul üyesi panelden (dev: `http://127.0.0.1:8770`) e-posta + şifreyle girip bir kalite sorusu sorsun,
beklerken "Sizin için araştırılıyor" görsün, yanıtı aynı ekranda ve Yanıt defterinde okusun.

**Architecture:** Üç yeni stdlib modülü: `panel_kimlik` (kullanıcı, oturum, deneme freni), `panel_defter` (Yanıt defteri
okuma, görünürlük, durum eşlemesi, kısa sebep, Markdown→HTML), `panel` (soketsiz test edilen `Uygulama` + ince
`http.server` adaptörü + tek iş parçacıklı `Ilerletici`). Hattın kuralları yalnız `soru_kapisi.yeni`'de kalır; panel onu
çağırır, sonucunu çevirir. `dagitici.yonlendir` kurulmamış bölüme giden soruyu koşusuz deftere kapatır (K5).
`panel.js` gerçek modda bu uçları kullanır; demo yolu dokunulmadan kalır.

**Tech Stack:** Python 3.9 stdlib (`http.server`, `hashlib`, `secrets`, `hmac`, `threading`), `unittest`; düz JavaScript.

**Spec:** `docs/superpowers/specs/2026-11-12-panel-canli-design.md` (Kağan onayı 12.11.2026, K1–K6). Uygulayan ikisini de okur.

## Açık nokta (Kağan okusun — sessizce tahmin edilmedi)

1. **`hashlib.scrypt` dev makinesinde yok.** Spec B4 ve §8c "scrypt özeti" diyor; kısıt "yalnız stdlib". Bu makinenin
   tek Python'u 3.9.6 / LibreSSL 2.8.3 ve `hashlib.scrypt` tanımlı değil (ölçüldü, 12.11). **Karar:** kayıt bir `yontem`
   alanı taşır; `hashlib.scrypt` varsa `scrypt` (n=2^14, r=8, p=1), yoksa `pbkdf2-sha256` (600 000 tur, stdlib).
   Doğrulama kayıttaki yöntemle yapılır. Dev'de açılan hesap PBKDF2 olur; sunucuda (OpenSSL) açılan scrypt olur.
   Spec B4 düzeltildi (12.11); NOVE-KURULUM §8c'deki "scrypt" cümlesi Task 7'de düzeltilir.
2. ~~"bütçe → Günlük bütçe doldu" cümlesi kodla örtüşmüyor.~~ **Kapandı (Kağan, 12.11.2026):** cümle
   "Bu sorunun bütçesi doldu" (`panel_defter.KISA_SEBEPLER["butce"]`). Soruyu bütçeden kapatan tek yol *soru* bütçesidir.
3. **Başarı ölçütündeki "ikinci hesap Kalite günlük raporunu görür" bugün gözlenemez:** `yanitlar/`'daki 10 kaydın
   hiçbiri `gorunurluk: kurul` taşımıyor (zamanlayıcı kurulu değil). Ölçütün bu kısmı için önce bir iş günü
   `python3 bin/gunluk.py --rapor` koşmuş olmalı (gerçek para). Kod yolu Task 3 testiyle kanıtlanır.

## Global Constraints

- Dal `feature/panel-canli`; `main`'e doğrudan commit yok. Commit: `type(scope): Türkçe konu`. Çalışma ağacında bu işe ait
  olmayan değişiklikler var (`ANAYASA.md`, `takimlar/kalite/durum.json`): **`git add -A` kullanılmaz**, dosyalar adıyla eklenir.
  İlk commit spec + plan + `PLANS.md` (`docs(plan): panel canlı — spec ve plan`).
- Taban: `python3 -m unittest discover -s tests` → `Ran 594 tests` · `OK (skipped=8)`. Sayı düşmez. (Task 2'nin scrypt
  testi bu makinede atlanır: `skipped=9` beklenir.)
- Yalnız Python stdlib. Sunucu yalnız `127.0.0.1`'e bağlanır (`--host` bayrağı yok). Port `8770`.
- Testler ağa çıkmaz, `claude` çağırmaz, gerçek `yanitlar/` ve `sirket-log/`'a dokunmaz (geçici kök). Fikstürlerde gerçek
  kişi adı ya da e-postası yok: `uye@example.com`, `diger@example.com`, `yonetici@example.com`, ad "Deneme Üye".
- `.env` okunmaz, basılmaz. Değişmez: `ANAYASA.md`, `takimlar/*/kurallar.md`, `formlar/onayli/`, `sirket/CEO-KIMLIGI.md`.
  `yanitlar/`'a yalnız sürücü yazar (`yanit_defteri.yaz`); panel modülleri oraya **yazmaz**.
- Ajan `panel.py --kullanici-ekle` koşturmaz, `deploy/roller.json`'u düzenlemez, tarayıcıyla panele girmez (CLAUDE.md).
  Bunlar Task 7'de Kağan'ın elle adımlarıdır.
- Hat kuralları (günlük soru hakkı, tekrar, maskeleme, mesai, bütçe, rol) **yalnız `soru_kapisi.yeni`'de**. `panel.py`
  soru metnini kırpmaz, saymaz, maskelemez, saate bakmaz; yalnız `yeni`'yi çağırır.
- Ham Denetçi/CEO gerekçesi `kurul` rolüne giden hiçbir yanıtta yer almaz; sınıflama sunucuda (B8).
- Şifre ve oturum belirteci hiçbir dosyaya ya da loga düz metin yazılmaz. Oturum bellekte, 12 saat.
- Koşu yığılmaz: ilerletme tek iş parçacığı, `ayar.kosu_suruyor` doluysa turu atlar; `tetik_karari` koruması değişmez.
- `?demo` ve `file://` davranışı değişmez: `DEMO` doğruyken hiçbir `/api/` çağrısı yapılmaz.
- Her ret, atlama, hata görünür sebep döndürür.
- Sabit metinler: bekleme `Sizin için araştırılıyor`; kısa sebepler Task 3'te; hepsinin sonu `Yöneticiniz bilgilendirildi.`

## Review Focus

1. Denetçi gerekçesinin içinde "timeout" ya da "bütçe" geçen red (gerçek kayıtlarda var: "nim ulaşılamadı: timeout",
   "model bütçeyi reasoning'e harcadı") → kısa sebep "Süre doldu"/"bütçe" değil, kalite denetimi — Task 3 testi.
2. Yanıt gövdesinin kendi `## ` başlıkları, hatta `## Gerekçe` adlı bir başlığı → defter ayrıştırıcı yanıtı bölmez,
   gerekçe sanmaz — Task 3 testi.
3. Soru açıkken sunucu yeniden başlar ya da sayfa yenilenir → oturum düşer (bellekte), girişten sonra bekleme ekranı
   `acik` listesinden geri gelir ve ilerletici açık soruyu görüp kaldığı yerden sürer — Task 3 ve Task 5 testleri.
4. İstek gövdesinde `soran` alanı göndermek ya da başkasının soru id'sini / `../` içeren id'yi denemek → soran yalnız
   oturumdan alınır; `404` — Task 4 testi.
5. Gerçek modda örnek çipine tıklamak para harcayan soru göndermez (yalnız kutuyu doldurur); aynı soruyu iki kez
   göndermek (çift tık, iki sekme) tek kayıt açar ve aynı beklemeyi gösterir — Task 4 ve Task 6 testleri.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `bin/dagitici.py` | Haiku'ya "hiçbiri"; yönlendirilemeyen soru deftere kapanır | Değişir (Task 1) |
| `sirket/IS-DAGITIMCI.md` | "yönlendirilemedi" paragrafı yeni davranışla | Değişir (Task 1) |
| `tests/test_dagitici_yonlendirme.py` | K5'in üç durumu | Değişir (Task 1) |
| `bin/panel_kimlik.py` | Kullanıcı dosyası, özet, oturumlar, deneme freni | Yeni (Task 2) |
| `.gitignore` | `deploy/kullanicilar.json` | Değişir (Task 2) |
| `bin/panel_defter.py` | Defter okuma, görünürlük, durum, kısa sebep, `md_html` | Yeni (Task 3) |
| `bin/panel.py` | `Uygulama` (uçlar), `Ilerletici`, `Sunucu`, komut satırı | Yeni (Task 4–5) |
| `tests/test_panel_kimlik.py`, `test_panel_defter.py`, `test_panel_api.py`, `test_panel_sunucu.py`, `test_panel_statik.py` | Testler | Yeni (Task 2–6) |
| `panel/panel.js`, `panel/stil.css` | Gerçek mod: oturum, soru, bekleme, yanıt, defter | Değişir (Task 6) |
| `panel/README.md`, `NOVE-KURULUM.md`, `CLAUDE.md` | Çalıştırma, §8c, N16, Faz 5 | Değişir (Task 7) |

### Task 1: Kurulmamış bölüm koşusuz kapanır (K5, B10)

**Files:** Modify `bin/dagitici.py` (`_haiku_istemi` ~201, `_karar` ~233, `yonlendir` ~278, `sorulari_isle` ~305,
`dagit` ~465, modül belge dizgisi satır 7) · `sirket/IS-DAGITIMCI.md:48-49` · Test `tests/test_dagitici_yonlendirme.py`

**Interfaces — Produces:**
- `dagitici.KURULMADI = "bu bölüm henüz kurulmadı"` — Task 3 sınıflamada bunu içe aktarır.
- `yonlendir(kok, soru_id, haiku=haiku_sinifla, kuru=False, ilet=None, simdi=None) -> dict | None` (`ilet=None` →
  `soru_kapisi.ilet`). `sorulari_isle(..., ilet=None)` ve `dagit` aynı parametreyi geçirir.
- Danışman seçilemeyince (kuru değilse): `## Dağıtım` yazılır, durum `yönlendirilemedi`, sonra
  `ilet(kok, soru_id, simdi=simdi, onaylanamadi=<gerekçe>)` → kayıt durumu `onaylanamadı`, `yanitlar/<id>.md` oluşur.
  Gerekçe: karar sebebi `KURULMADI` ile başlıyorsa aynen; değilse `"yönlendirilemedi — <sebep>"`.
  `IletHatasi` yakalanır: durum `yönlendirilemedi` kalır, karar `sebep`'ine ` · deftere yazılamadı: <hata>` eklenir.
- `_karar` sebepleri: aktif danışman yok → `f"{KURULMADI} — aktif danışman yok, hepsi kurulumda"`; Haiku "hiçbiri" →
  `f"{KURULMADI} — {gerekce or 'soru kurulu danışmanların alanına girmiyor'}"`. "hiçbiri" eşleşmesi:
  `_tr_kucuk(str(ad)).strip() in ("hiçbiri", "hicbiri")`. Haiku hatası ve listede olmayan ad: sebepleri değişmez.
- `_haiku_istemi` eklenen cümle (aynen): `Soru bu danışmanlardan hiçbirinin alanına girmiyorsa "danisman" alanına
  "hiçbiri" yaz; soruyu zorla birine yönlendirme.` JSON şablonu: `"danisman":"<listeden bir ad>"|"hiçbiri"`.
- `BITMIS` değişmez. Anahtar kelime eşleşen sorunun yolu değişmez.

- [ ] **Step 1: Kırmızı testler** (`HaikuTesti` ve yeni `KurulmamisBolumTesti(Kurulum)`; gerçek `soru_kapisi.ilet`, geçici kök):
  - `test_haiku_hicbiri_derse_kosusuz_kapanir` — haiku `{"danisman": "hiçbiri", "gerekce": "insan kaynakları sorusu", "oneri": None, "maliyet": 0.01}` →
    `sonuc["danisman"] is None`; üç kuyruk `[]`; `sk.alan(kayit, "durum") == "onaylanamadı"`; `yanitlar/<sid>.md` var,
    içinde `- etiket: onaylanamadı`, `- danışman: —`, `## Gerekçe\nbu bölüm henüz kurulmadı — insan kaynakları sorusu`.
  - `test_hicbiri_yazim_varyantlari` — `"Hiçbiri"`, `" HİÇBİRİ "`, `"hicbiri"` için subTest: aynı sonuç.
  - `test_tek_aktif_danismanda_haikuya_hicbiri_sunulur` — yalnız `kalite` kurulu, eşleşmeyen soru: `haiku` bir kez çağrılır;
    `"hiçbiri" in dagitici._haiku_istemi("x", dagitici.aktif_danismanlar(self.kok))`; "hiçbiri" yanıtında `kuyruk("kalite") == []`.
  - `test_haiku_listede_olmayan_ad_donerse_yonlendirilemedi` (mevcut, güncellenir) — durum artık `"onaylanamadı"`; defter
    gerekçesi `"yönlendirilemedi — "` ile başlar, `KURULMADI` ile başlamaz; kuyruklar boş.
  - `test_aktif_danisman_yoksa_haiku_cagrilmaz` (mevcut, eklenir) — defter kaydı var, gerekçe `KURULMADI` ile başlar.
  - `test_anahtar_kelime_yolu_degismez` — "Q3 bütçe sapması…" → `finans`, haiku çağrılmaz, `yanitlar/` yok.
  - `test_kuru_deftere_yazmaz` — `kuru=True`: `(kok / "yanitlar").exists()` yanlış, durum `alındı`.
  - `test_defterde_zaten_varsa_durum_yonlendirilemedi_kalir` — `yanitlar/<sid>.md` önceden var: istisna yok, durum
    `"yönlendirilemedi"`, `"zaten var" in sonuc["sebep"]`.
- [ ] **Step 2:** `python3 -m unittest tests.test_dagitici_yonlendirme -v` → yeni testler FAIL.
- [ ] **Step 3:** Yukarıdaki arayüzü uygula; `IS-DAGITIMCI.md:48-49` ve belge dizgisi: "seçilemeyen soru koşu yapılmadan
  `onaylanamadı` etiketiyle Yanıt defterine girer; Haiku 'hiçbiri' diyebilir".
- [ ] **Step 4:** `python3 -m unittest discover -s tests` → OK, sayı ≥ 594 (`test_dagitici_soru_akisi` yeşil kalır).
- [ ] **Step 5:** `git commit -m "feat(dagitici): kurulmamış bölüme giden soru koşusuz deftere kapanır"`

### Task 2: Kullanıcı, oturum, deneme freni

**Files:** Create `bin/panel_kimlik.py` · Modify `.gitignore` (`deploy/roller.json` satırının altına `deploy/kullanicilar.json`)
· Test `tests/test_panel_kimlik.py`

**Interfaces — Consumes:** `soru_kapisi.roller(kok)`, `soru_kapisi.SORABILEN_ROLLER`. **Produces:**
- Sabitler: `CEREZ_ADI = "nove_oturum"` · `OTURUM_SURESI_SN = 12 * 3600` · `DENEME_SINIRI = 5` ·
  `DENEME_PENCERESI_SN = 15 * 60` · `PBKDF2_TUR = 600_000` · `SIFRE_EN_AZ = 8`.
- `kullanicilar(kok) -> dict` — `deploy/kullanicilar.json`; yoksa/bozuksa `{}`.
  Kayıt: `{"<eposta>": {"ad": str, "yontem": "scrypt" | "pbkdf2-sha256", "tuz": hex, "ozet": hex}}`.
- `kullanici_ekle(kok, eposta, ad, sifre) -> None` — e-posta `strip().lower()`; 16 bayt `secrets` tuzu; geçici dosya +
  `os.replace`, izin `0o600`; aynı e-posta varsa üzerine yazar (şifre yenileme); `len(sifre) < SIFRE_EN_AZ` → `ValueError`.
- `dogrula(kok, eposta, sifre) -> dict | None` — `{"eposta", "ad", "rol"}`. `None`: kullanıcı yok, şifre yanlış
  (`hmac.compare_digest`), rolü `SORABILEN_ROLLER` dışında, kayıttaki `yontem` bu makinede yok. Kullanıcı yoksa da bir
  özet hesaplanır (süre farkı kullanıcı adını sızdırmasın).
- `bas_harf(ad) -> str` — ilk iki kelimenin baş harfi, `"Deneme Üye"` → `"DÜ"`.
- `class Oturumlar(saat=time.time)`: `ac(eposta, ad) -> str` (`secrets.token_urlsafe(32)`) · `bul(belirtec) -> dict | None`
  (`{"eposta", "ad"}`; süresi dolan silinir) · `kapat(belirtec) -> None`. `threading.Lock`'lu.
- `class DenemeFreni(saat=time.time)`: `engelli_mi(eposta, ip) -> bool` (pencerede e-posta **ya da** IP için ≥ 5 başarısız)
  · `basarisiz(eposta, ip)` · `basarili(eposta)` (yalnız o e-postanın sayacını siler). Kilitli.

- [ ] **Step 1: Kırmızı testler** (`PBKDF2_TUR` testte `mock.patch.object(panel_kimlik, "PBKDF2_TUR", 1000)`):
  `test_ekle_izin_600_ve_duz_sifre_yok` (`stat.S_IMODE == 0o600`; dosya metninde şifre geçmez; `tuz`, `ozet`, `yontem` var) ·
  `test_dogru_sifre` (`== {"eposta": "uye@example.com", "ad": "Deneme Üye", "rol": "kurul"}`) · `test_yanlis_sifre_none` ·
  `test_bilinmeyen_eposta_none` · `test_rolde_olmayan_giremez` · `test_pasif_rol_giremez` (rol `"pasif"`) ·
  `test_eposta_buyuk_harf_ve_bosluk` (`" UYE@Example.com "` girer) · `test_ayni_sifre_farkli_ozet` ·
  `test_bozuk_dosya_none` · `test_bilinmeyen_yontem_none` · `test_kisa_sifre_valueerror` ·
  `test_ikinci_ekleme_sifreyi_yeniler` (eski şifre `None`, yeni girer) ·
  `test_scrypt_varsa_kullanilir` (`skipUnless(hasattr(hashlib, "scrypt"))`; `yontem == "scrypt"`) ·
  `test_oturum_ac_bul_kapat` · `test_oturum_12_saat_sonra_duser` (sahte saat `+ 12*3600 + 1` → `None`) ·
  `test_belirtecler_farkli_ve_uzun` (`len >= 32`) ·
  `test_fren_ayni_eposta_5` (5 farklı IP'den 5 başarısız → engelli; 4 → değil) · `test_fren_ayni_ip_5` (5 farklı e-posta) ·
  `test_fren_15_dk_sonra_acilir` · `test_basarili_giris_eposta_sayacini_siler`.
- [ ] **Step 2:** `python3 -m unittest tests.test_panel_kimlik -v` → FAIL (`No module named 'panel_kimlik'`).
- [ ] **Step 3:** Uygula. Yöntem seçimi: `"scrypt" if hasattr(hashlib, "scrypt") else "pbkdf2-sha256"` (Açık nokta 1).
- [ ] **Step 4:** PASS; `git check-ignore deploy/kullanicilar.json` → yolu basar.
- [ ] **Step 5:** `git commit -m "feat(panel): kullanıcı dosyası, oturum ve deneme freni"`

### Task 3: Defter okuma, görünürlük, durum, kısa sebep, Markdown

**Files:** Create `bin/panel_defter.py` · Test `tests/test_panel_defter.py`

**Interfaces — Consumes:** `dagitici.KURULMADI` (Task 1), `soru_kaydi.alan/yol`, `yanit_defteri.yol`,
`soru_kapisi._soran_eposta`. Defter biçimi `bin/soru_kapisi.py:240-268`. **Produces:**
- `ID_DESENI = re.compile(r"^[a-z0-9-]{1,64}$")`
- `defter_oku(metin) -> dict` — `{soru, soran, tarih, danisman, etiket, gorunurluk, kurula_not, yanit, gerekce}` (olmayan `None`).
  Başlık = ilk boş satıra kadar. Gövde `## Gerekçe\n` ile başlıyorsa kalanın tamamı `gerekce`. Değilse ilk `## Yanıt\n`
  satırından dosya sonuna kadar `yanit`; öncesindeki `## Kurula not\n` gövdesi `kurula_not`. Gövde `## ` üzerinden **bölünmez**.
- `gorebilir_mi(soran, gorunurluk, eposta, rol) -> bool` — `rol == "yonetici"` ya da `soran == eposta` ya da `gorunurluk == "kurul"` (B8b).
- `KISA_SEBEPLER` + `SON_EK = "Yöneticiniz bilgilendirildi."`; `kisa_sebep(gerekce) -> str`, **sırayla, başa bakarak**:
  1. `KURULMADI` ile başlar → `Bu bölüm henüz kurulmadı.`
  2. `Denetçi:` ile başlar ya da `^CEO \d+\. kez reddetti` → `Yanıt kalite denetiminden geçemedi.`
  3. `^CEO \d+ kez başlatıldı` → `Süre doldu.`
  4. `soru bütçesi doldu` ile başlar → `Bu sorunun bütçesi doldu.` (Açık nokta 2 — Kağan, 12.11)
  5. diğer (boş dahil) → `Bu soruya şu an güvenilir bir yanıt verilemedi.` — hepsinin sonuna ` ` + `SON_EK`.
- `md_html(metin) -> str` — önce `html.escape`, sonra: `#`→`<h3>`, `##`→`<h4>`, `###`+→`<h5>`; `- `/`* `→`<ul>`; `1. `→`<ol>`;
  ayırıcı satırı (`|---|`) olan boru tablosu→`<table>` (`<th>`/`<td>`); `**x**`→`<strong>`; `` `x` ``→`<code>`; kalan
  satırlar `<p>`. Bağlantı `<a>` üretilmez (metin kalır). Boş girdi → `""`.
- `durum(kok, soru_id, eposta, rol) -> dict | None` — `None` → uç `404` verir (id desene uymuyor, kayıt yok, göremez — ayırt edilmez).
  Ortak alanlar `soru_id, soru, zaman, durum`. Defterde yoksa `durum: "arastiriliyor"` + kayıtta `- not:` varsa `not`.
  Defterde ve etiket `onaylanamadı` değilse `durum: "yanitlandi"` + `etiket, danisman, yanit_html`, varsa `kurula_not_html`.
  `onaylanamadı` ise `durum: "onaylanamadi"` + `sebep` (`kisa_sebep`); **yalnız `rol == "yonetici"`** için ayrıca `gerekce` (ham).
  (Spec B7'deki `metin` alanı HTML ve düz metin karışmasın diye `yanit_html` / `sebep` / `gerekce` olarak ayrıldı.)
- `liste(kok, eposta, rol) -> dict` — `{"kayitlar": [...], "acik": [...]}`. `kayitlar`: görebildiği defter kayıtları, `tarih`'e
  göre yeniden eskiye; satır `{soru_id, tarih, soru, danisman, etiket, gorunurluk}`, yönetici için ek `soran`; gövde yok.
  Okunamayan dosya atlanır. `acik`: **soranı ben olan** ve defterde olmayan soru kayıtları `{soru_id, soru, zaman, not?}`, yeniden eskiye.
- `acik_sorular(kok) -> list[str]` — defterde olmayan ve `durum` alanı `iletildi | onaylanamadı | yönlendirilemedi`
  olmayan bütün soru kayıtlarının id'leri (Task 5 ilerletici bunu yoklar).

- [ ] **Step 1: Kırmızı testler** (fikstürleri test dosyası kurar; `soru_kapisi.ilet` ile gerçek biçimde yazdırılabilir):
  - Ayrıştırma: `test_onayli_kayit` (kurula not + yanıt) · `test_kurula_not_yok` · `test_onaylanamadi_kayit` ·
    `test_yanit_icindeki_basliklar_bolmez` (yanıt gövdesinde `## Özet` ve `## Gerekçe` → `yanit` ikisini de içerir, `gerekce is None`).
  - Görünürlük: `test_kurul_yalniz_kendini_gorur` · `test_kurul_gunluk_raporu_gorur` (`gorunurluk: kurul`, soran `zamanlayıcı`) ·
    `test_yonetici_hepsini_gorur_ve_soran_alir` · `test_kurul_satirinda_soran_yok` (`"soran" not in satir`).
  - Kısa sebep, girdiler aynen: `"Denetçi: red — nim ulaşılamadı: timeout → openai yolu · model bütçeyi reasoning'e harcadı"` →
    `"Yanıt kalite denetiminden geçemedi. Yöneticiniz bilgilendirildi."` · `"CEO 2. kez reddetti — kaynak eksik"` → aynı ·
    `"CEO 2 kez başlatıldı, karar yazmadı (bkz. sirket-log/ceo.log)"` → `"Süre doldu. …"` ·
    `"soru bütçesi doldu: 7.20 USD harcandı, CEO kontrolüne yetmiyor"` → `"Bu sorunun bütçesi doldu. …"` ·
    `dagitici.KURULMADI + " — x"` → `"Bu bölüm henüz kurulmadı. …"` · `"yönlendirilemedi — Haiku JSON döndürmedi"` ve `""` →
    `"Bu soruya şu an güvenilir bir yanıt verilemedi. …"`.
  - Durum: `test_defterde_yoksa_arastiriliyor_ve_not` (`not` "mesai dışı" içerir) · `test_onayli_yanitlandi` (`yanit_html` `<h3>` içerir) ·
    `test_ceo_yapilmadi_de_yanitlandi` (`etiket == "CEO kontrolü yapılmadı"`) ·
    `test_kurul_ham_gerekceyi_almaz` (`"gerekce" not in d` ve ham metindeki işaret dizgi `json.dumps(d)` içinde yok) ·
    `test_yonetici_ham_gerekceyi_alir` · `test_baskasinin_sorusu_none` · `test_gecersiz_id_none` (`"../x"`, `"A B"`, `""`) ·
    `test_liste_siralama_ve_acik` (açık soru yalnız sahibinin `acik`'inde; yöneticinin `acik`'inde başkasınınki yok) ·
    `test_acik_sorular_bitmisleri_saymaz`.
  - Markdown: `test_script_kacar` (`"<script" not in` çıktı, `"&lt;script&gt;" in`) · `test_kalin_baslik_liste` ·
    `test_tablo` (`<th>A</th>`, `<td>1</td>`) · `test_ayiricisiz_boru_tablo_degil` · `test_baglanti_a_uretmez`
    (`"[x](javascript:alert(1))"` → `"<a" not in`) · `test_bos`.
- [ ] **Step 2:** `python3 -m unittest tests.test_panel_defter -v` → FAIL (modül yok).
- [ ] **Step 3:** Uygula. Modül `yanitlar/` ve `sirket-log/` altında yalnız okur (`read_text`); hiçbir dosya yazmaz.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat(panel): Yanıt defteri okuma, görünürlük süzgeci ve kısa sebep"`

### Task 4: `Uygulama` — uçlar (B1, B5–B7)

**Files:** Create `bin/panel.py` (bu görevde yalnız `Uygulama`) · Test `tests/test_panel_api.py`

**Interfaces — Consumes:** Task 2 ve Task 3'ün tamamı; `soru_kapisi.yeni(kok, soru, soran) -> {"sonuc", "soru_id", "sebep"}`.
**Produces:**
- `GOVDE_SINIRI = 16 * 1024`
- `class Uygulama(kok, oturumlar=None, fren=None, ilerletici=None, yeni=soru_kapisi.yeni, https=False)`
- `Uygulama.istek(yontem: str, yol: str, govde: bytes = b"", cerez: str | None = None, ip: str = "127.0.0.1")
  -> tuple[int, dict, list[tuple[str, str]]]` — (HTTP kodu, JSON gövdesi, ek başlıklar). Soket bilmez. `cerez` = belirteç değeri.

| Uç | Davranış |
|---|---|
| `POST /api/giris` `{eposta, sifre}` | fren engelliyse `429` (şifre denenmez) · `dogrula` `None` → `fren.basarisiz`, `401` · başarı → `fren.basarili`, `200 {ad, basHarf, rol}` + `Set-Cookie: nove_oturum=<b>; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200` (`https` ise sonuna `; Secure`) |
| diğer bütün `/api/` uçları | oturum yok/süresi dolmuş **ya da** e-postanın rolü artık `SORABILEN_ROLLER`'da değil → `401 {"hata": "oturum yok"}`. Rol her istekte `soru_kapisi.roller(kok)`'tan okunur |
| `GET /api/ben` | `200 {ad, basHarf, rol}` |
| `POST /api/cikis` | oturumu kapatır, `200 {}` + `Set-Cookie: nove_oturum=; Max-Age=0; …` |
| `POST /api/soru` `{soru}` | `soru` dizgi değil/boş → `400`. `yeni(kok, soru, <oturum e-postası>)` bir `threading.Lock` altında. `reddedildi` → `200 {"durum": "reddedildi", "sebep"}`. `acildi`/`var` → `200 panel_defter.durum(...)`; `var` ise ek `bilgi: <sebep>`. Yalnız `acildi`'da `ilerletici.tetikle()` (ilerletici varsa) |
| `GET /api/sorular/<id>` | `panel_defter.durum` → `200` ya da `404 {"hata": "bulunamadı"}` |
| `GET /api/yanitlar` | `200 panel_defter.liste(...)` |
| bilinmeyen `/api/…` → `404`; uç var yöntem yanlış → `405`; gövde JSON nesnesi değil → `400`; `len(govde) > GOVDE_SINIRI` → `413`; beklenmeyen istisna → `500 {"hata": "sunucu hatası"}` (ayrıntı gövdeye girmez; stderr'e yalnız istisna türü) |

- [ ] **Step 1: Kırmızı testler** (geçici kök: `deploy/roller.json` = `uye@example.com: kurul`, `diger@example.com: kurul`,
  `yonetici@example.com: yonetici`; `kullanici_ekle` ile üç hesap; `yeni=mock.MagicMock(wraps=soru_kapisi.yeni)`; sahte ilerletici `MagicMock`):
  `test_cerezsiz_bes_uc_401` (`ben`, `cikis`, `soru`, `sorular/x`, `yanitlar`) · `test_giris_govdesi_ve_cerez`
  (`{"ad": "Deneme Üye", "basHarf": "DÜ", "rol": "kurul"}`; çerezde `HttpOnly`, `SameSite=Strict`, `Path=/`, `Max-Age=43200`, `Secure` yok) ·
  `test_https_arkasinda_secure` · `test_yanlis_sifre_401_altincida_429` (5×`401`, 6. `429`; **doğru şifreyle de** `429`) ·
  `test_soran_oturumdan_alinir` (gövde `{"soru": …, "soran": "yonetici@example.com"}` → `yeni.call_args[0][2] == "uye@example.com"`) ·
  `test_soru_acildi_arastiriliyor_ve_tetikler` (`durum == "arastiriliyor"`, `soru_id` var, `tetikle` bir kez) ·
  `test_kisa_soru_reddedildi_tetiklemez` (`{"soru": "ne oldu"}` → `durum == "reddedildi"`, sebep `yeni`'ninki: "soru çok kısa" içerir) ·
  `test_gunluk_hak_yeniden_gelir` (`mock.patch.object(ayar, "KURUL_UYESI_GUNLUK_SORU", 1)`; ikinci farklı soru → `reddedildi`, "soru hakkın doldu") ·
  `test_ayni_soru_iki_kez_tek_kayit` (ikinci yanıt aynı `soru_id`, `bilgi` var; `sirket-log/sorular/` altında tek dosya; `tetikle` bir kez) ·
  `test_mesai_disi_notu` (`mock.patch.object(ayar, "mesaide_mi", return_value=False)` → `"mesai dışı" in yanit["not"]`) ·
  `test_baskasinin_sorusu_404` · `test_gecersiz_id_404` (`/api/sorular/..%2F..%2Fdeploy`) ·
  `test_kurul_ham_gerekceyi_almaz_yonetici_alir` · `test_cikis_sonrasi_401` · `test_rol_silinince_401` (roller.json'dan çıkar) ·
  `test_bozuk_json_400` · `test_buyuk_govde_413` · `test_yanlis_yontem_405` (`GET /api/soru`) ·
  `test_belirtec_ve_sifre_dosyaya_yazilmaz` (giriş + soru sonrası geçici kökteki her dosyanın metninde belirteç ve şifre yok) ·
  `test_panel_yanitlara_yazmaz` (soru sonrası `(kok / "yanitlar").exists()` yanlış).
- [ ] **Step 2:** `python3 -m unittest tests.test_panel_api -v` → FAIL.
- [ ] **Step 3:** `Uygulama`'yı uygula. Soru metni `yeni`'ye **olduğu gibi** geçer (kırpma, sayma, maskeleme yok).
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** `git commit -m "feat(panel): giriş, soru, durum ve Yanıt defteri uçları"`

### Task 5: İlerletici, HTTP adaptörü, komut satırı (B3, B4, B11)

**Files:** Modify `bin/panel.py` · Test `tests/test_panel_sunucu.py`

**Interfaces — Consumes:** `Uygulama.istek` (Task 4), `panel_defter.acik_sorular` (Task 3), `panel_kimlik.kullanici_ekle`
(Task 2), `dagitici.dagit(kok)`, `ayar.kosu_suruyor(kok)`. **Produces:**
- `class Ilerletici(kok, adim=None, aralik_sn=60, kilit_dolu=ayar.kosu_suruyor, acik=panel_defter.acik_sorular)`
  (`adim=None` → `dagitici.dagit`):
  `tur() -> str` — `"bos"` (açık soru yok, `adim` çağrılmaz) · `"kilit"` (`kilit_dolu(kok)` doğru, çağrılmaz) ·
  `"adim"` (`adim(kok)` bir kez) · `"hata"` (`adim` istisna attı; yakalanır, stderr'e tür adı).
  `baslat()` tek daemon iş parçacığı: `tur()` → sonuç `"bos"` ise `tetikle()`'ye kadar, değilse `aralik_sn` ya da
  `tetikle()`'ye kadar bekler → yine `tur()`. `tetikle()` beklemeyi keser. `durdur()` iş parçacığını bitirir.
  Adımlar yalnız bu iş parçacığında koşar: aynı anda iki `adim` olamaz.
- `class Sunucu(SimpleHTTPRequestHandler)` — `directory=panel/`. `/api/` ile başlayan `GET`/`POST` → gövdeyi
  (`Content-Length`, en çok `GOVDE_SINIRI + 1` bayt okur), `nove_oturum` çerezini (`http.cookies.SimpleCookie`) ve
  `client_address[0]`'ı `Uygulama.istek`'e verir; yanıt `application/json; charset=utf-8`, `Cache-Control: no-store`.
  `/` → `index.html`. `PUT/DELETE/PATCH` → `405`. `log_message` varsayılanı kalır (istek satırı; gövde ve çerez loglanmaz).
- `main(argv) -> int` — bayraklar: `--port N` (varsayılan `8770`) · `--ilerletme-yok` · `--https-arkasinda` ·
  `--kullanici-ekle <eposta> --ad "<ad>"`.
  `--kullanici-ekle`: ortamda `CLAUDECODE` varsa **yazmaz**, `2` döner ("bu komutu Kağan kendi terminalinde çalıştırır").
  Yoksa `getpass.getpass` iki kez; uyuşmazsa ya da `ValueError` (kısa şifre) → `1` ve sebep; başarıda `0`. E-posta
  `roller.json`'da yoksa hesabı yine yazar ve uyarır: "rolü yok — `deploy/roller.json`'a eklenene kadar giremez".
  Sunucu: `ThreadingHTTPServer(("127.0.0.1", port), …)`; port doluysa `1` ve "port <N> dolu (`bin/sahne.py` de 8770 kullanır)".
  Açılışta adres, ilerletmenin açık/kapalı olduğu ve `kullanicilar.json` yoksa ekleme komutu basılır.

- [ ] **Step 1: Kırmızı testler:**
  `test_tur_bos_adim_cagirmaz` · `test_tur_kilit_doluyken_atlar` · `test_tur_adim_kokle_cagrilir` · `test_tur_hata_yutulur` (`"hata"`, istisna çıkmaz) ·
  `test_baslat_acik_soru_varsa_hemen_adim_atar` (yeniden başlama: `acik` → `["x"]`; sahte `adim` bir `threading.Event` kurar, `wait(2)` doğru) ·
  `test_tetikle_bekleyeni_uyandirir` (`aralik_sn=3600`; başta `acik` boş, sonra dolu + `tetikle()` → `adim` 2 sn içinde) ·
  `test_ayni_anda_tek_adim` (sahte `adim` 0,2 sn uyur ve eşzamanlı sayacı tutar; art arda 5 `tetikle()` → en yüksek eşzamanlılık `1`) ·
  `test_ilerletme_yok_tetiklemez` (`Uygulama(ilerletici=None)` ile soru → hata yok) ·
  `test_kullanici_ekle_claudecode_altinda_yazmaz` (`mock.patch.dict(os.environ, {"CLAUDECODE": "1"})` → `2`, dosya yok) ·
  `test_kullanici_ekle_yazar` (`CLAUDECODE` ortamdan çıkarılır, `getpass.getpass` yamalanır → `0`, `dogrula` girer) ·
  `test_kullanici_ekle_sifreler_uyusmazsa_1` ·
  `test_adaptor_duman` (port `0`'da gerçek `Sunucu`, `urllib` ile: `GET /` → `200` ve gövdede `Nove AI`; `GET /api/ben` → `401` JSON,
  `Cache-Control: no-store`; `GET /deploy/kullanicilar.json` → `404`. Bağlanamıyorsa `skipTest("yerel soket açılamadı")`).
- [ ] **Step 2:** `python3 -m unittest tests.test_panel_sunucu -v` → FAIL.
- [ ] **Step 3:** Uygula. `sahne.py`'den kod kopyalanmaz; yalnız `_govde`/`_yanit` kalıbı örnek alınır.
- [ ] **Step 4:** PASS. Elle duman (şifre gerekmez):
  `python3 bin/panel.py --ilerletme-yok --port 8771 &` → `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8771/` → `200`;
  `curl -s -w ' %{http_code}' http://127.0.0.1:8771/api/ben` → `{"hata": "oturum yok"} 401`; süreci kapat.
- [ ] **Step 5:** `git commit -m "feat(panel): ilerletici, yerel sunucu ve --kullanici-ekle"`

### Task 6: `panel.js` gerçek modu (B9)

**Files:** Modify `panel/panel.js` (`dogrula` ~347, giriş ~351, çıkış ~387, `gonder` ~486, `renderApp` ~521, çipler ~562,
`boot` ~607), `panel/stil.css` · Test `tests/test_panel_statik.py`

**Interfaces — Consumes:** Task 4 tablosundaki uçlar ve Task 3'teki `durum` / `liste` biçimleri. `DEMO` satırı değişmez;
aşağıdakilerin hepsi `if (!DEMO)` dalındadır, demo fonksiyonları (`yonlendir`, `adimUret`, `adimGonder`, `ilerle`, `SEED_DEFTER`) yerinde kalır.

Kararlar:
- `api(yol, secenek)` yardımcısı: `fetch(..., {credentials: 'same-origin'})`; `401` → zamanlayıcıları durdurur, çıkış akışını
  çalıştırır, giriş hatası olarak "Oturumun kapandı. Yeniden giriş yap." gösterir.
- Açılış: `GET /api/ben` `200` ise giriş atlanır, ad/baş harf/rol yazılır, doğrudan ofise geçilir (mevcut `#ofis` kısa yolunun
  kodu), `defterYukle()` çağrılır. Girişten sonra da `toOffice` içinde `defterYukle()`.
- `defterYukle()`: `GET /api/yanitlar` → `st.defter` satırları: TARİH `gg.aa.yyyy SS:DD` · SORU (yöneticide altında küçük
  `soran`) · BÖLÜM (`danisman` baş harfi büyük, `—` kalır) · DENETÇİ (`onaylanamadı` → `—`, değilse `Doğrulandı`) · rozet
  (`onaylı` → `Onaylandı` · `CEO kontrolü yapılmadı` → aynı metin · `onaylanamadı` → `Onaylanamadı`). Boş liste:
  "Henüz kayıt yok" (gerçek modda `SEED_DEFTER` hiç gösterilmez). `acik` doluysa ve bekleyen soru yoksa `bekle(acik[0])`.
- `gonder` gerçek dalı: `POST /api/soru`. `reddedildi` → akış alanında "SORU KAYDA ALINMADI" + `sebep`. Diğer → `bekle(yanit)`.
- `bekle(k)`: akış alanında soru, başlık **`Sizin için araştırılıyor`**, geçen süre (`3 dk 12 sn`; `k.zaman`'dan, saniyede bir
  yalnız o öğe güncellenir), varsa `not`, altında "Yanıt birkaç dakika sürebilir. Bu sayfayı kapatabilirsiniz; yanıt Yanıt
  defterine düşer." Gönder düğmesi "Araştırılıyor…" ve devre dışı. `YOKLAMA_MS = 10000` ile `GET /api/sorular/<id>`; ağ hatasında
  bekleme sürer, küçük "Bağlantı kesildi, yeniden deneniyor" satırı çıkar. Adım listesi ve 3D olayları (`nove-akis`) gerçek modda
  tetiklenmez; sahne boşta animasyonunda kalır.
- Sonuç: `yanitlandi` → etiket `CEO ONAYLI YANIT` (`etiket` "CEO kontrolü yapılmadı" ise `YANIT · CEO KONTROLÜ YAPILMADI`),
  varsa "KURULA NOT" kutusu (`kurula_not_html`), `<div class="md">` içinde `yanit_html` (sunucuda kaçışlı; `innerHTML`).
  `onaylanamadi` → `ONAYLANAMADI` + `sebep` (`esc`), `gerekce` geldiyse (yönetici) `<pre>` içinde `esc(gerekce)`.
  Ardından `defterYukle()`, soru kutusu boşalır.
- Defter satırı gerçek modda tıklanır (`role="button"`, `tabindex="0"`, Enter): `GET /api/sorular/<id>` → sonuç akış alanında.
  Bir soru beklenirken satır tıklaması yok sayılır.
- Örnek çipleri gerçek modda soruyu **göndermez**, yalnız kutuya yazar ve odaklar (her soru gerçek para).
- Başlıktaki küçük etiket: `rol === "yonetici"` ise "Yönetici". Çıkışta `st.run`, `st.defter`, zamanlayıcılar sıfırlanır.
- `stil.css`: `.md` (tablo kenarlığı, `h3–h5`, liste, `code`), bekleme başlığı ve süre için mevcut belirteçlerle stiller.

- [ ] **Step 1: Kırmızı test** `tests/test_panel_statik.py` (dosya metni üstünde): `"Sizin için araştırılıyor"`, `"/api/ben"`,
  `"/api/soru"`, `"/api/sorular/"`, `"/api/yanitlar"`, `"YOKLAMA_MS = 10000"` `panel.js`'te geçer; `"has('demo')"` ve `"SEED_DEFTER"`
  hâlâ geçer; `"/api/olaylar"` geçmez; `stil.css`'te `.md` kuralı var.
- [ ] **Step 2:** `python3 -m unittest tests.test_panel_statik -v` → FAIL.
- [ ] **Step 3:** Yukarıdaki kararları uygula.
- [ ] **Step 4:** Test PASS · `node --check panel/panel.js` → çıktı yok, kod 0 · `grep -c "if *(DEMO)\|if *(!DEMO)\|DEMO &&\|!DEMO &&" panel/panel.js` ≥ 4.
- [ ] **Step 5:** `git commit -m "feat(panel): gerçek modda soru, bekleme ekranı ve Yanıt defteri"`

### Task 7: Belgeler ve Kağan'ın dev doğrulaması

**Files:** Modify `panel/README.md`, `NOVE-KURULUM.md` (N16 satır 37; §8c satır 366–378; Faz 5 satır 494–502), `CLAUDE.md` (satır 50 ve `bin/` satırı)

- [ ] **Step 1:** `panel/README.md`: "Yerelde açmak" → `python3 bin/panel.py` → `http://127.0.0.1:8770` (`?demo` aynı adreste);
  uç tablosu Task 4'teki gibi; `--ilerletme-yok`, `--https-arkasinda`, `--kullanici-ekle`; "SSE Faz 7'de". 8000'deki `http.server` satırı silinir.
- [ ] **Step 2:** `NOVE-KURULUM.md`: N16'ya "(12.11.2026: Haiku 'hiçbiri' diyebilir; seçilemeyen soru koşusuz `onaylanamadı`
  olarak deftere girer)"; §8c: özet yöntemi "scrypt, yoksa PBKDF2-SHA256 (kayıtta `yontem`)", `Secure` yalnız `--https-arkasinda`,
  yerelde açma komutu; Faz 5 durum satırı "(12.11.2026): panel canlı — giriş, soru, durum yoklaması, Yanıt defteri; SSE, CRM zili,
  ajan kartı, Caddy/systemd açık" ve `bin/panel.py` maddesi bu kapsamla bölünüp yapılan kısmı `[x]`.
- [ ] **Step 3:** `CLAUDE.md`: `panel/` satırı "(canlı: `bin/panel.py`; `?demo` demo verisiyle)"; `bin/` satırına `panel.py`.
- [ ] **Step 4:** `git commit -m "docs(panel): panel.py çalıştırma, §8c ve Faz 5 durumu"`; `PLANS.md` satırı ve bu dosyanın
  frontmatter'ı PR açılınca `acik`/PR numarasıyla güncellenir.
- [ ] **Step 5: Kağan'ın elle adımları (ajan yapmaz; mesai 08:00–20:00 içinde, her soru gerçek para ≈ 1,20 USD):**
  1. 8000'deki `python3 -m http.server` ve varsa 8770'teki `bin/sahne.py` kapatılır.
  2. `deploy/roller.json`'a ikinci test e-postası `kurul` rolüyle eklenir.
  3. Kendi terminalinde (Claude Code dışında) iki hesap: `python3 bin/panel.py --kullanici-ekle <eposta> --ad "<ad>"`.
  4. `python3 bin/panel.py` → `http://127.0.0.1:8770`. (Dev'de bütün istekler `127.0.0.1`'den gelir: 15 dk'da 5 yanlış giriş
     herkesi kilitler; sunucuyu yeniden başlatmak freni ve oturumları sıfırlar.)
  5. Ölçütler (spec "Başarı ölçütü"):
     - [ ] Birinci hesapla giriş; bir kalite sorusu → "Sizin için araştırılıyor" ve geçen süre görünür.
     - [ ] Sayfa yenilenince giriş istenmez, bekleme ekranı geri gelir.
     - [ ] Dakikalar sonra yanıt aynı ekranda belirir; Yanıt defterinde satır olarak görünür.
     - [ ] İkinci hesap (kurul) bu soruyu defterde görmez; adres çubuğundan `/api/sorular/<o id>` → `404`.
     - [ ] İkinci hesap `gorunurluk: kurul` taşıyan Kalite günlük raporunu görür (Açık nokta 3: önce bir rapor koşmuş olmalı).
     - [ ] Kalite dışı bir soru (Kalite'nin anahtar kelimelerinden hiçbirini içermeyen, ör. izin/bordro) koşu yapılmadan
       "Bu bölüm henüz kurulmadı. Yöneticiniz bilgilendirildi." ile kapanır; `takimlar/kalite/kosu/`'da yeni dosya yok.
     - [ ] Onaylanamayan bir soruda kurul hesabı kısa sebebi, yönetici hesabı tam gerekçeyi görür.
     - [ ] `http://127.0.0.1:8770/?demo` eskisi gibi: her giriş kabul, canlandırmalı akış, örnek defter.

## Self-Review

- **Spec kapsaması:** Hedef 1 → Task 5 · 2 → Task 2, 4 · 3 → Task 4, 5 · 4 → Task 6 · 5 → Task 3, 4 · 6 → Task 6 (statik test + Kağan).
  B1 → Task 4 · B2 → Task 6 (`YOKLAMA_MS`) · B3 → Task 5 · B4 → Task 2, 5 · B5/B6 → Task 2, 4 · B7/B8/B8b → Task 3 · B9 → Task 6 ·
  B10/K5 → Task 1 · B11 → Task 5, 7 · K6 → Task 3. Anti-hedefler: kural kopyası yok (Task 4 testleri `yeni`'nin sebebini bekler),
  başkasının sorusu `404`, tek adım (Task 5), düz metin sır yok (Task 2, 4), `yanitlar/`'a yazma yok (Task 4 testi).
- **Hedef dışı kalanlar plana girmedi:** SSE, CRM zili, ajan kartı, Caddy/systemd, şifre sıfırlama/N23.
- **Tip tutarlılığı:** `KURULMADI` (Task 1 → 3) · `durum()`/`liste()`/`acik_sorular()` (Task 3 → 4, 5, 6) ·
  `Uygulama.istek` üçlüsü (Task 4 → 5) · `tetikle()` (Task 4 ↔ 5) · alan adları `yanit_html`, `kurula_not_html`, `sebep`, `gerekce`,
  `not`, `bilgi` (Task 3, 4 → 6).
- **Review Focus:** beş maddenin her birinin testi sahibi olan görevde adıyla var.
- **Bilinen sınır:** `panel.js` için otomatik tarayıcı testi yok (repo bağımlılıksız; ajan panele tarayıcıyla girmez) —
  davranış Task 7 Step 5'te Kağan'ın listesiyle doğrulanır.

## Bitirme

- [ ] `python3 -m unittest discover -s tests` → `OK`, test sayısı > 594 (taban 594, `skipped=8`; bu makinede `skipped=9`)
- [ ] `python3 bin/agents_uret.py --check` → temiz
- [ ] `python3 bin/ayar.py` → üç satır, hata yok
- [ ] `python3 -m py_compile bin/panel.py bin/panel_kimlik.py bin/panel_defter.py bin/dagitici.py` → çıktı yok
- [ ] `node --check panel/panel.js` → çıktı yok
- [ ] `python3 bin/dagitici.py --kuru` → hata yok, hiçbir şey yazılmaz
- [ ] `git status --short` → `deploy/kullanicilar.json`, `yanitlar/`, `sirket-log/` görünmez; `ANAYASA.md` ve `kurallar.md` bu dalda değişmedi
- [ ] Task 7 Step 5'teki Kağan listesi tamam
