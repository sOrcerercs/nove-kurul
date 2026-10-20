---
durum: yazildi
guncelleme: 2026-10-20
dal: feature/tebrik-danismani
pr: -
bekleyen: Task 0 (Kağan), Task 7–8 (Kağan onayı)
---

# Tebrik Danışmanı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ya da
> superpowers:executing-plans (Kağan'ın seçimine göre). Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra
> kod, yeşil, commit.

**Goal:** Her sabah 08:55'te çalışan tablosundan o günün doğum günü, hoş geldin ve bayram tebriklerini çıkaran,
adı sabit şablona basıp tek bir iç alıcıya tek mail olarak gönderen, yapay zekâsız bir betik.

**Architecture:** Üç saf modül + bir sürücü. `tebrik_takvim` (tablo → doğrulanmış kişiler → bugünün tebrikleri),
`tebrik_gorsel` (şablon + yazı → PNG), `tebrik_posta` (alıcı/ANAYASA kapısı, mail kurma, SMTP). Sürücü
`tebrik_postasi.py` bunları bağlar, gönderim kaydını ve adsız özeti yazar. Dış dünya (Drive, SMTP, saat) her yerde
parametreyle verilir; testler sahte nesneyle koşar.

**Tech Stack:** Python 3.9 stdlib (`zoneinfo`, `smtplib`, `email`), Pillow 11 ve openpyxl 3.1 (kurulu),
google-auth + google-api-python-client (yalnız Drive okuyucuda, tembel import), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-20-tebrik-danismani-design.md` (Kağan onayı 20.10.2026)

## Global Constraints

- Dal `feature/tebrik-danismani` (spec `6ea73c5`). Taban: `python3 -m unittest discover -s tests` → `Ran 468 tests` · `OK (skipped=8)`.
- **Depo herkese açık.** Kodda, testte, fikstürde gerçek çalışan adı, doğum günü, e-posta adresi yok. Test adları
  uydurma ve Türkçe harfli (`Çağla Işıkoğlu`, `Ömer Şükrü Güneş` gibi).
- `.env` anahtarları (yalnız süreç ortamından, `ayar.ortam_yukle()`): `TEBRIK_SMTP_SUNUCU`, `TEBRIK_SMTP_PORT`,
  `TEBRIK_SMTP_KULLANICI`, `TEBRIK_SMTP_SIFRE`, `TEBRIK_ALICI`, `TEBRIK_DRIVE_DOSYA`, `TEBRIK_DRIVE_ANAHTAR`
  (servis hesabı JSON yolu), `GEMINI_API_KEY` (yalnız Task 7). Değerler hiçbir çıktıya, loga, hata mesajına yazılmaz.
- Saat dilimi `ZoneInfo("Europe/Istanbul")`; "bugün" her zaman bu dilimde hesaplanır, makinenin dilimi kullanılmaz.
- Alıcı kuralı: tek adres, `@nove.group` ile biter (`ALAN_ADI = "nove.group"`, kodda sabit), virgül/noktalı virgül/boşluk yok.
- ANAYASA kapısı: `ANAYASA.md` içinde `İstisna — tebrik postası` başlığı yoksa gönderim yok (rc 3, sebep yazılır).
  `--kuru` bu kapıdan bağımsız çalışır.
- Ad **yazıldığı gibi** basılır (baştaki/sondaki boşluk kırpılır, iç boşluklar teke iner); büyük/küçük harf dönüşümü
  yok (`str.title()`/`upper()` Türkçe `i/İ`'yi bozar).
- Kişisel veri taşıyan her dosya git dışı: `sirket-log/tebrik/` (zaten `sirket-log/` altında), indirilen tablo
  `sirket-log/tebrik/tablo.xlsx`, üretilen görseller `sirket-log/tebrik/<gun>/`.
- Sabit metinler (spec): doğum günü TR `Yeni yaşınızda, tüm hayallerinizin gerçeğe dönüşmesini dileriz.` · EN
  `In your new age, we wish all your dreams come true.` · hoş geldin başlığı `Welcome to the Team!`.
- Çıkış kodları: 0 tamam (gönderildi ya da gönderilecek bir şey yok), 1 hata (Drive, SMTP, kayıt), 2 kullanım,
  3 ANAYASA kapısı kapalı ya da alıcı geçersiz.

## Review Focus

1. Excel'de tarih hücresi tarih tipinde gelir (`datetime`, doğum gününde uydurma yıl), metin olarak da gelebilir
   (`15.10`, `15/10`, `15.10.1990`) → hepsi aynı gün/aya çözülür — Task 1 testi.
2. Ad küçük harfle ya da fazla boşlukla yazılmış (`  ebru  yıldız `) → `ebru yıldız` olarak basılır, `Ebru Yildiz`
   olmaz — Task 1 ve Task 3 testi.
3. Aynı kişi tabloda iki kez → tek tebrik, eksikler listesine "tekrarlı satır" notu — Task 1 testi.
4. Betik aynı gün iki kez koşar (launchd açılışta + elle) → ikinci koşu göndermez; SMTP hatasında kayıt
   `gonderildi` olmaz ve aynı gün sonraki koşu yeniden dener — Task 5 testi.
5. Makine UTC'de ve saat 21:30 UTC (İstanbul'da ertesi gün 00:30) → "bugün" İstanbul günüdür — Task 5 testi.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `bin/tebrik_takvim.py` | xlsx okuma, satır doğrulama, bugünün tebrikleri, bayram takvimi | Yeni (Task 1) |
| `bin/tebrik_drive.py` | Drive'dan tabloyu indirme (servis hesabı, `drive.readonly`) | Yeni (Task 2) |
| `requirements-tebrik.txt` | Pillow, openpyxl, google-auth, google-api-python-client — sabit sürüm | Yeni (Task 2) |
| `bin/tebrik_gorsel.py` | Şablon + yerleşim JSON + yazı → PNG; logo türetme | Yeni (Task 3) |
| `tebrik/yazi-tipleri/` | OFL yazı tipleri + lisans dosyaları | Yeni (Task 3) |
| `tebrik/logo.png` | Şeffaf "Nove Group" logosu (Kağan'ın `linkedinNewLogo.png`'sinden türetilir) | Yeni (Task 3) |
| `bin/tebrik_posta.py` | Alıcı doğrulama, ANAYASA kapısı, mail kurma, SMTP | Yeni (Task 4) |
| `bin/tebrik_postasi.py` | Sürücü: gün, kayıt, geç/kaçan, özet, `--kuru` | Yeni (Task 5) |
| `tebrik/bayramlar.json` | Yıllık bayram tarihleri ve metinleri (Kağan'ın listesi gelene kadar boş liste) | Yeni (Task 5) |
| `bin/zamanla.py` | 08:55 takvimli iş | Değişir (Task 6) |
| `CLAUDE.md`, `docs/superpowers/PLANS.md`, `.env.example` | Tebrik Danışmanı satırı, plan satırı, anahtar adları | Değişir (Task 6) |
| `bin/tebrik_sablon_uret.py`, `tebrik/sablonlar/` | Gemini'yle adsız şablon üretimi + yerleşim JSON'ları | Yeni (Task 7, Kağan onayı) |
| `tests/test_tebrik_*.py` | Her modülün testleri | Yeni |

### Task 0: Kağan'ın işleri (kod beklemez, Task 7–8'i bekletir)

- [ ] ANAYASA §1'e `İstisna — tebrik postası` maddesi (spec "Kısıtlar"daki metin)
- [ ] Bayram listesi ve her bayramın TR/EN metni
- [ ] `GEMINI_API_KEY` `.env`'e
- [ ] BT: ayrı gönderen Nove adresi, SMTP sunucusu/portu, uygulama şifresi → `.env`
- [ ] Bahadır Bey: Drive'da dört sütunlu Excel; servis hesabının e-postasıyla **görüntüleyen** olarak paylaşım

### Task 1: Takvim — tablo, doğrulama, bugünün tebrikleri

**Files:** Create `bin/tebrik_takvim.py`, `tests/test_tebrik_takvim.py`

**Interfaces — Produces:**
- `SUTUNLAR = ("Ad Soyad", "Ünvan", "Doğum günü", "İşe giriş tarihi")`
- `xlsx_oku(yol: Path) -> list[dict]` — ilk sayfa, ilk satır başlık; başlık eşleşmesi kırpılmış ve büyük/küçük harf
  duyarsız (`dagitici._tr_kucuk` ile); eksik sütun → `ValueError("eksik sütun: <ad>")`.
- `ad_temizle(ad: str) -> str`
- `gun_ay(deger) -> tuple[int, int] | None` ve `tam_tarih(deger) -> date | None` — `datetime`/`date`, `gg.aa`,
  `gg/aa`, `gg.aa.yyyy`, `gg/aa/yyyy`; olmayan gün (31.02) → `None`.
- `dogrula(satirlar: list[dict]) -> tuple[list[dict], list[str]]` — kişi: `{"ad", "unvan", "dogum": (g, a) | None,
  "giris": date | None}`; eksik metni ad + sorun (`"Çağla Işıkoğlu — doğum günü okunamadı: '31.02'"`). Boş satır
  sessizce atlanır; adı boş ama başka hücresi dolu satır eksiktir (`"<satır no>. satır — ad yok"`).
- `bugunun_tebrikleri(kisiler, bayramlar: list[dict], gun: date) -> list[dict]` — öğe
  `{"tur": "dogum_gunu"|"hos_geldin"|"bayram", "ad", "unvan", "bayram": dict|None}`; sıra: bayram, hoş geldin,
  doğum günü, sonra ada göre.
- `bayram_bugun(bayramlar, gun) -> dict | None` — öğe şeması `{"ad", "baslangic": "YYYY-MM-DD", "tr", "en",
  "sablon"}`; yalnız `baslangic` günü eşleşir (çok günlü bayramda ilk gün).

- [ ] **Step 1: Failing tests** (`tests/test_tebrik_takvim.py`):
  - `test_gun_ay_bicimleri`: `gun_ay(datetime(1900,10,15))`, `"15.10"`, `"15/10"`, `"15.10.1990"` → `(15, 10)`; `"31.02"`, `"abc"`, `""` → `None`
  - `test_ad_yazildigi_gibi`: `ad_temizle("  ebru  yıldız ")` → `"ebru yıldız"`; `ad_temizle("İSMAİL")` → `"İSMAİL"`
  - `test_dogrula_eksikleri_adla_yazar`: geçersiz doğum günü satırı kişiye girer (`dogum=None`) ve eksikte adıyla görünür
  - `test_tekrarli_satir_tek_kisi`: aynı ad iki satır → bir kişi, eksikte `"tekrarlı satır"`
  - `test_29_subat`: `dogum=(29,2)`, `gun=date(2027,2,28)` → doğum günü var; `date(2028,2,28)` → yok, `date(2028,2,29)` → var
  - `test_hos_geldin_yalniz_ilk_gun`: `giris=date(2026,10,20)` → 20.10.2026'da var, 20.10.2027'de yok
  - `test_bayram_ilk_gun`: `baslangic="2027-03-20"` → 20 Mart'ta bayram öğesi, 21 Mart'ta yok
  - `test_xlsx_oku_eksik_sutun`: openpyxl ile geçici dosya, `Ünvan` sütunu yok → `ValueError`
  - `test_xlsx_oku_baslik_esnek`: başlıklar `" ad soyad "`, `"ÜNVAN"` → okunur
- [ ] **Step 2:** `python3 -m unittest tests.test_tebrik_takvim` → FAIL (`ModuleNotFoundError`)
- [ ] **Step 3:** Implement the interfaces above in `bin/tebrik_takvim.py`.
- [ ] **Step 4:** aynı komut → OK
- [ ] **Step 5:** `git commit -m "feat(tebrik): takvim — tablo okuma, doğrulama, bugünün tebrikleri"`

### Task 2: Drive okuyucu

**Files:** Create `bin/tebrik_drive.py`, `requirements-tebrik.txt`, `tests/test_tebrik_drive.py`

**Interfaces — Produces:** `tablo_indir(ortam: dict, hedef: Path, servis_kur=None) -> Path` — `ortam`dan
`TEBRIK_DRIVE_DOSYA` ve `TEBRIK_DRIVE_ANAHTAR`; kapsam `["https://www.googleapis.com/auth/drive.readonly"]`;
dosya Google Sheets ise `files().export_media(mimeType=xlsx)`, değilse `files().get_media`; `servis_kur(anahtar_yolu,
kapsamlar)` verilmezse google kütüphaneleri fonksiyon içinde import edilir. Hata → `RuntimeError("Drive okunamadı:
<tür>")`; mesajda dosya kimliği ve yol yok.

- [ ] **Step 1: Failing tests:** `test_eksik_anahtar` (`TEBRIK_DRIVE_DOSYA` yok → `RuntimeError`, mesajda `TEBRIK_DRIVE_DOSYA` adı var, değer yok) · `test_sahte_servisle_indirir` (sahte servis bayt döner → `hedef` dosyası o baytları taşır) · `test_hata_mesaji_kimlik_sizdirmaz` (sahte servis kimliği içeren istisna atar → mesajda kimlik yok) · `test_kapsam_yalniz_okuma` (`servis_kur`'a giden kapsam listesi tam olarak `drive.readonly`)
- [ ] **Step 2:** `python3 -m unittest tests.test_tebrik_drive` → FAIL
- [ ] **Step 3:** Implement; `requirements-tebrik.txt`: `Pillow==11.3.0`, `openpyxl==3.1.5`, `google-auth`, `google-api-python-client` (sürümler kurulumdaki `pip index versions` çıktısından en yeni kararlı sürüme sabitlenir).
- [ ] **Step 4:** → OK · **Step 5:** `git commit -m "feat(tebrik): Drive'dan salt okunur tablo indirme"`

### Task 3: Görsel — yazı basma, sığdırma, logo

**Files:** Create `bin/tebrik_gorsel.py`, `tebrik/yazi-tipleri/` (Google Fonts'tan OFL: `GreatVibes-Regular.ttf`,
`Poppins-Bold.ttf`, `Poppins-Regular.ttf` + `OFL.txt` her aile için), `tebrik/logo.png`, `tests/test_tebrik_gorsel.py`

**Interfaces — Produces:**
- Yerleşim JSON (`tebrik/sablonlar/<sablon>.json`): `{"gorsel": "<sablon>.png", "alanlar": [{"anahtar": "ad"|"unvan"|"tr"|"en"|"baslik", "yazi_tipi": "<dosya>", "boyut": int, "en_kucuk": int, "renk": "#RRGGBB", "kutu": [x, y, genislik, yukseklik], "hiza": "orta", "satir_max": 1|2}], "logo": [x, y, genislik]}`
- `gorsel_uret(tebrik: dict, sablon_klasoru: Path, cikis: Path, yazi_klasoru: Path) -> Path | None` — `tebrik["tur"]` → şablon adı `dogum_gunu`/`hos_geldin`/bayramda `tebrik["bayram"]["sablon"]`; sığmazsa `None`.
- `yazi_sigdir(metin, yazi_tipi_yolu, boyut, en_kucuk, genislik, yukseklik, satir_max) -> tuple[list[str], int] | None` — önce tek satırda boyutu 2'şer küçültür; `en_kucuk`'a inince iki satıra böler (en dengeli boşluktan); yine sığmazsa `None`.
- `logo_hazirla(kaynak: Path, hedef: Path) -> None` — beyaz harfleri ayırır: alfa = parlaklık eşiği (≥ 200 → opak beyaz, altı şeffaf, arası doğrusal), kırpılır; altına `Poppins-Regular` ile `Group` (logo yüksekliğinin %40'ı, ortalı). Kaynak git'e girmez, yalnız `tebrik/logo.png` girer.

- [ ] **Step 1: Failing tests** (sahte şablon testte `Image.new("RGB", (1080, 1350), "#0b1b3f")` + JSON geçici klasöre):
  - `test_turkce_harfler_basilir`: her biri `ÇĞİIÖŞÜçğıiöşü` için `ImageFont.truetype(...).getmask(h).getbbox()` boş değil ve `getmask("\U0010FFFD")` baytlarından farklı (tofu değil) — üç yazı tipinde
  - `test_ad_yazildigi_gibi_basilir`: `gorsel_uret` `"ebru yıldız"` ile koşar; bastığı metin (fonksiyonun döndürdüğü satırlar ya da çağrılan çizim kaydı) `"ebru yıldız"`
  - `test_uzun_ad_iki_satir`: `"Ayşegül Nur Karaoğlu Büyükşahin Demirtaş"` dar kutuda → iki satır
  - `test_sigmayan_ad_none`: 60 harfli tek kelime → `gorsel_uret` `None`, dosya yazılmaz
  - `test_hos_geldin_unvan_basilir` ve `test_bayram_ad_tasimaz` (bayram şablonunda `ad` alanı yok; tebrikte ad olsa bile basılmaz)
  - `test_logo_seffaf`: siyah zemin üstünde beyaz kare olan sahte kaynak → hedefte köşe pikseli alfa 0, kare alfa 255
- [ ] **Step 2:** `python3 -m unittest tests.test_tebrik_gorsel` → FAIL
- [ ] **Step 3:** Yazı tiplerini indir (`curl -L` Google Fonts GitHub `ofl/greatvibes`, `ofl/poppins`), lisansları yanına koy; implement; `python3 -c "import sys;sys.path.insert(0,'bin');import tebrik_gorsel as g;from pathlib import Path;g.logo_hazirla(Path.home()/'Desktop/linkedinNewLogo.png',Path('tebrik/logo.png'))"`
- [ ] **Step 4:** → OK; `tebrik/logo.png`'yi aç ve bak (Read), Kağan'a göster
- [ ] **Step 5:** `git commit -m "feat(tebrik): görsel — yazı sığdırma, Türkçe harf, şeffaf logo"`

### Task 4: Posta — kapı, mail, SMTP

**Files:** Create `bin/tebrik_posta.py`, `tests/test_tebrik_posta.py`

**Interfaces — Produces:**
- `ALAN_ADI = "nove.group"`, `ISTISNA_BASLIGI = "İstisna — tebrik postası"`
- `alici_dogrula(adres: str) -> str` — geçerliyse kırpılmış adres; değilse `ValueError` (adres mesajda yok).
- `istisna_var(anayasa_metni: str) -> bool`
- `mail_kur(tebrikler: list[dict], gorseller: list[Path], notlar: list[str], gonderen: str, alici: str, gun: date) -> EmailMessage` — konu `Tebrikler — <gg.aa.yyyy>` (tebrik yoksa `Tebrik tablosu — <tarih>`); gövde düz metin: her tebrik için tür, ad, paylaşılacak TR/EN metin; sonra `notlar` (geç gönderim, kaçan, eksikler); ek adları ASCII (`2026-10-20-dogum-gunu-cagla-isikoglu.png`, Türkçe harf → ASCII karşılığı).
- `gonder(mesaj: EmailMessage, ortam: dict, smtp_kur=smtplib.SMTP) -> None` — port 465 → `SMTP_SSL`, değilse `starttls()` zorunlu; giriş `TEBRIK_SMTP_KULLANICI/SIFRE`; `send_message(mesaj, to_addrs=[alici])` — alıcı listesi tek elemanlı; hata → `RuntimeError("SMTP: <tür>")`, şifre/adres mesajda yok.

- [ ] **Step 1: Failing tests:** `test_alici_tek_adres` (`"a@nove.group"` geçer; `"a@nove.group,b@nove.group"`, `"a@nove.group b@x.com"`, `"a@gmail.com"`, `"a@nove.group.evil.com"`, `""` → `ValueError`) · `test_istisna_basligi` (başlık varken True, yokken ve `İstisna — tebrik` kesikken False) · `test_mail_ekleri_ve_govde` (iki tebrik + bayram → üç ek, gövdede iki ad ve sabit TR metin) · `test_ek_adi_ascii` · `test_gonder_tek_alici_ve_tls` (sahte SMTP: `starttls` çağrıldı, `to_addrs == [alici]`) · `test_smtp_hatasi_sifre_sizdirmaz`
- [ ] **Step 2:** `python3 -m unittest tests.test_tebrik_posta` → FAIL
- [ ] **Step 3:** Implement · **Step 4:** → OK
- [ ] **Step 5:** `git commit -m "feat(tebrik): posta — tek alıcı, ANAYASA kapısı, SMTP"`

### Task 5: Sürücü — gün, kayıt, geç/kaçan, özet, `--kuru`

**Files:** Create `bin/tebrik_postasi.py`, `tebrik/bayramlar.json` (`[]`), `tests/test_tebrik_postasi.py`

**Interfaces — Consumes:** Task 1–4'ün hepsi. **Produces:**
- `KAYIT_KLASORU = KOK / "sirket-log" / "tebrik"`; kayıt `<gun>.json`: `{"gun", "durum": "gonderildi"|"bos"|"hata"|"kuru", "zaman", "tebrik_sayisi", "eksik_sayisi", "gec": bool, "adlar": [...]}`; özet `ozet.json`: kayıttan `adlar` hariç alanlar + `son_gonderim`.
- `istanbul_gunu(simdi: datetime) -> date` (aware `simdi` → İstanbul tarihi)
- `kos(simdi: datetime, ortam: dict, kok: Path, kuru=False, indir=tebrik_drive.tablo_indir, gonder=tebrik_posta.gonder) -> int` — sıra: (1) bugünün kaydı `gonderildi` ise 0 dön; (2) ANAYASA + alıcı kapısı (kuru değilse) → 3; (3) tabloyu indir (hata → "tablo okunamadı" maili denenir, kayıt `hata`, rc 1); (4) doğrula, bugünün tebrikleri, görseller (`None` dönen görsel eksiğe yazılır); (5) notlar: dün için kayıt yoksa dünün tebrikleri yeniden hesaplanır → `"Dün kaçan tebrikler: <adlar>"`; saat ≥ 09:15 İstanbul ise `"Geç gönderildi (<ss:dd>)"`; ayın ilk iş günüyse (Pzt–Cum, ayın ilk böyle günü) bütün eksikler, değilse yalnız bugünün tebriğini etkileyen eksikler; aralıkta gelecek yılın `baslangic`'ı takvimde yoksa `"Gelecek yılın bayram tarihleri takvimde yok"`; (6) tebrik ve not yoksa kayıt `bos`, mail yok, rc 0; (7) gönder, **sonra** kayıt `gonderildi`; gönderim hatası → kayıt `hata`, rc 1 (aynı gün sonraki koşu yeniden dener); (8) özet yazılır. `kuru=True`: mail gitmez, `.eml` + PNG `KAYIT_KLASORU/<gun>/` altına, kayıt `kuru` (kuru kayıt gönderimi engellemez).
- `main(argv=None) -> int` — `--kuru`, `--gun YYYY-MM-DD` (yalnız `--kuru` ile; aksi rc 2).

- [ ] **Step 1: Failing tests** (geçici kök, sahte `indir` ve `gonder`, gerçek modüller):
  - `test_istanbul_gunu_utc_gecesi`: `datetime(2026,10,19,21,30,tzinfo=UTC)` → `date(2026,10,20)`
  - `test_ayni_gun_ikinci_kosu_gondermez`: iki `kos` → `gonder` bir kez
  - `test_smtp_hatasi_sonra_yeniden_dener`: ilk `gonder` istisna → rc 1, kayıt `hata`; ikinci koşu gönderir
  - `test_istisna_yoksa_rc3_gonderim_yok` ve `test_kuru_istisnasiz_calisir`
  - `test_bos_gun_mail_yok_kayit_bos`
  - `test_dun_kacan_not`: dün kaydı yok, dün doğum günü olan kişi → bugünün notunda adı, eki yok
  - `test_gec_gonderim_notu`: 14:00 İstanbul → `Geç gönderildi`
  - `test_ayin_ilk_is_gunu_tum_eksikler`: 2 Kasım 2026 Pazartesi (1 Kasım Pazar) → bütün eksikler; 3 Kasım → yalnız bugünü etkileyenler
  - `test_ozet_ad_tasimaz`: `ozet.json`'da hiçbir test adı geçmez
  - `test_drive_hatasi_rc1_ve_bildirim`
- [ ] **Step 2:** `python3 -m unittest tests.test_tebrik_postasi` → FAIL
- [ ] **Step 3:** Implement · **Step 4:** → OK; tam takım → 468 + yeni, OK
- [ ] **Step 5:** `git commit -m "feat(tebrik): sürücü — tek gönderim, geç/kaçan, adsız özet, kuru koşu"`

### Task 6: Zamanlama ve belgeler

**Files:** Modify `bin/zamanla.py` (`TETIKLER`), `tests/` (zamanla testi bulunduğu dosyada), `CLAUDE.md`,
`docs/superpowers/PLANS.md`, `.env.example`

- [ ] **Step 1: Failing test:** `test_tebrik_tetigi`: `TETIKLER`'de `{"ad": "tebrik", "saat": 8, "dakika": 55, "betik": "tebrik_postasi.py"}`; `plist_icerigi` → `ProgramArguments[-1]` `.../bin/tebrik_postasi.py`, `StartCalendarInterval == {"Hour": 8, "Minute": 55}`, `RunAtLoad` False
- [ ] **Step 2:** FAIL · **Step 3:** `TETIKLER`'e ekle (`argv: []`); `.env.example`'a anahtar adları (değersiz); `CLAUDE.md` Sistem rolleri tablosuna `Tebrik Danışmanı — özel gün tebrikleri, LLM'siz · spec · bin/tebrik_postasi.py`; `PLANS.md` satırı
- [ ] **Step 4:** tam takım OK · **Step 5:** `git commit -m "feat(tebrik): 08:55 takvimli iş, belgeler"`

### Task 7: Şablonlar (Kağan'ın Gemini anahtarı ve onayı gerekir)

**Files:** Create `bin/tebrik_sablon_uret.py`, `tebrik/sablonlar/{dogum_gunu,hos_geldin}.{png,json}` (+ bayram
listesi gelince her bayram için bir çift)

- [ ] **Step 1:** Gemini görsel modelinin güncel adını ve REST uç noktasını resmî belgeden doğrula (WebFetch `ai.google.dev`); `bin/tebrik_sablon_uret.py <sablon> --istem-dosyasi` → `urllib` ile `GEMINI_API_KEY` başlıkta, çıktı PNG `tebrik/sablonlar/aday/`. Anahtar URL'ye ya da loga yazılmaz.
- [ ] **Step 2:** İstemler: Kağan'ın iki örneğinin tarzı — doğum günü krem zemin, lacivert-altın pasta/balon/hediye, üstte ad için boş bant, altta lacivert metin bandı; hoş geldin mavi ışıklı modern ofis, üst yarı koyu boş alan. **Her istemde: "no text, no letters, no logo, no watermark"**. 1080×1350.
- [ ] **Step 3:** Adayları Kağan'a göster; onaylananı `tebrik/sablonlar/<sablon>.png` yap; yerleşim JSON'unu görsele göre yaz; `python3 bin/tebrik_postasi.py --kuru --gun <örnek gün>` ile uydurma bir adla önizleme üret, Kağan'a göster.
- [ ] **Step 4:** Kağan onayı → `git commit -m "feat(tebrik): onaylı şablonlar"`

### Task 8: Canlı (Kağan onayıyla, Task 0 bitince)

- [ ] `python3 bin/tebrik_postasi.py --kuru` gerçek tabloyla → eksikler listesi Bahadır Bey'e iletilmek üzere Kağan'a
- [ ] ANAYASA istisnası yürürlükte → `python3 bin/zamanla.py --kur`; ilk gerçek gönderimi Kağan ve alıcı birlikte kontrol eder

## Self-Review

| Spec maddesi | Görev |
|---|---|
| Üç tür gün, bayram ilk gün, 29 Şubat, hafta sonu kaydırma yok | 1 |
| Excel → Drive salt okunur servis hesabı, okunamazsa bildirim | 2, 5 |
| Sabit şablon, yalnız ad (hoş geldinde ünvan), bayramda ad yok, sığdırma, Türkçe harf, gerçek logo | 3, 7 |
| Sabit TR/EN metin | Global, 3, 4 |
| Tek `@nove.group` alıcı, ANAYASA başlık kapısı, TLS | 4 |
| 08:55 koşu, aynı gün tek gönderim, geç notu, kaçan gün gönderilmez, her koşu kayıt | 5, 6 |
| Eksikler: ayın ilk iş günü + ilgili gün; aralık bayram hatırlatması | 5 |
| Panel kartı adsız özet | 5 (`ozet.json`) — **panele bağlantı yok**: Kurul Ofisi paneli (`panel/`) bugün demo verisiyle çalışıyor, canlı veri Faz 5'te `bin/panel.py` ile; özet dosyası o zaman okunur (Ruling) |
| Kişisel veri git dışı | Global, 5 |

Bilerek dışarıda (spec "Hedef olmayanlar"): kişiye özel metin, çalışana doğrudan gönderim, WhatsApp, yeni bebek.
Tür tutarlılığı: tebrik sözlüğü (`tur`, `ad`, `unvan`, `bayram`) Task 1'de tanımlı; 3, 4, 5 aynı anahtarları kullanır.
`tablo_indir`, `gonder` imzaları Task 5'te parametre olarak enjekte edilir.

## Bitirme

- [ ] `python3 -m unittest discover -s tests` → 468 + yeni testler, `OK (skipped=8)`
- [ ] `git grep -n -E "@nove\.group" -- . ':!docs' ':!tests'` → yalnız `ALAN_ADI` sabiti
- [ ] `python3 bin/tebrik_postasi.py --kuru --gun 2026-10-20` (tablo yokken) → rc 1, `Drive okunamadı` sebebi, adres/kimlik basılmaz
- [ ] `python3 bin/zamanla.py --kuru` → `tebrik` işi 08:55
