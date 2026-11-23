---
durum: beklemede
guncelleme: 2026-11-23
dal: feature/rapor-postasi
pr: -
bekleyen: kullanici — PR merge; Kağan'ın elle adımları 1–6
---

# Rapor Postası — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (önerilen) ya da
> superpowers:executing-plans. Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.
> **(Kağan)** yazan adımlar insanındır; ajan onları yapmaz, yerine geçecek bir yol da aramaz.

**Goal:** Yanıt defterine düşen onaylı zamanlı raporun **haberini** (ad, tarih, panel bağlantısı) alıcı listesine
mail ile ileten `bin/rapor_postasi.py`; dağıtıcı onu her başarılı iletimden sonra çağırır, panel `?soru=<id>`
bağlantısını girişten sonra açar.

**Architecture:** Giden kutusu (spec, yaklaşım B). `rapor_postasi.py` Yanıt defterini tarar, haberi gitmemiş
kayıtları bulur, üç kilit tutuyorsa sabit şablonla gönderir ve sonucu `sirket-log/posta/<id>.json`'a yazar;
`soru_kapisi.ilet()` değişmez. Dağıtıcı betiği süreç içinde, hatayı yutan bir sarmalayıcıyla çağırır. Panel
tarafında yalnız istemci değişir: küçük saf bir JS modülü parametreyi okur, `panel.js` girişten sonra var olan
`satirAc`'ı çağırır.

**Tech Stack:** Python 3.9 stdlib (`smtplib`, `email.message`, `fcntl`, `json`, `zoneinfo`), `unittest` +
`unittest.mock`; JS testi `node` ile (`tests/test_sahne_sira.py` deseni).

**Spec:** `docs/superpowers/specs/2026-11-23-rapor-postasi-istisnasi-design.md` — "Betik tasarımı" bölümü
(Kağan onayı 23.11.2026). Kararlar orada; bu plan onları yeniden açmaz. Spec dosyası değişmez.

## Global Constraints

- Dal `feature/rapor-postasi` (açık; dal değiştirme). Taban: `python3 -m unittest discover -s tests` →
  `Ran 931 tests` · `OK (skipped=9)`. Sayı düşmez; her görevin sonunda tam takım koşar.
- **Gerçek SMTP yok.** Testlerde `rapor_postasi.smtplib.SMTP` ve `SMTP_SSL` sahte sınıfla değiştirilir
  (`mock.patch.object`); hiçbir test ağa çıkmaz. Testler geçici `kok` ile çalışır, `ortam` sözlüğü enjekte edilir.
- **Mail yalnız haber taşır.** Konu `<Rapor adı> hazır — GG.AA.YYYY`; gövde tek cümle + bağlantı. Gövdeye ve
  konuya Yanıt defteri kaydının `soru`, `Kurula not`, `Yanıt` kısımlarından hiçbir şey girmez; ek ve HTML yok.
  Şablon fonksiyonu defter metnini parametre olarak **almaz**.
- **Adres hiçbir yere yazılmaz:** stdout, stderr, `sirket-log/posta/*.json`, `dagitici.log`, hata iletisi —
  yalnız alıcı **sayısı**. SMTP hatasında kayda yalnız istisnanın sınıf adı girer (`type(e).__name__`);
  `str(e)` adres ve sunucu yanıtı taşıyabilir, yazılmaz. `POSTA_SIFRE` ve `POSTA_KULLANICI` da hiçbir çıktıda yok.
- **Üç kilit** (spec): (1) `ANAYASA.md`'de `İstisna — rapor postası` metni; (2) `.env`'de `POSTA_SMTP_SUNUCU`,
  `POSTA_SMTP_PORT`, `POSTA_KULLANICI`, `POSTA_SIFRE`, `POSTA_GONDEREN`, `PANEL_ADRES`; (3) `CLAUDECODE`
  ortamında değil. Biri tutmazsa gönderim yok, kayıt yazılmaz, nedeni çıktıda. Bugün (1) ve (2) tutmuyor —
  betik bu hâlde teslim edilir; kilidi açmak Kağan'ın.
- **Ajan yazamaz, okumaz:** `.env` ve `.env.example` (okuma kapalı), `ANAYASA.md`, `yanitlar/`,
  `.claude/settings.json`, `deploy/posta-alicilari.json`. Bunlar sondaki "Kağan'ın elle adımları"nda. Ajan betiği
  yalnız `--kuru` ile koşturur.
- Rakamlar yalnız `bin/ayar.py`'de (ANAYASA §4). Kayıt zamanı ve "bugün" İstanbul saatidir.
- Depo herkese açık: test ve örnek dosyadaki adresler uydurmadır (`ornek.bir@nove.group`); gerçek adres girmez.
- `bin/panel.py`, `bin/panel_defter.py`, `bin/soru_kapisi.py`, `bin/yanit_defteri.py` **değişmez** — sunucu
  tarafı görünürlük süzmesi olduğu gibi kalır.
- Commit: `type(scope): Türkçe konu`; sonunda `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`.

## Review Focus

1. **İlk açılışta geçmiş raporlar:** kilitler açıldığı gün defterde haftalarca eski onaylı rapor var, hiçbirinin
   kaydı yok — yöneticiye onlarca eski haber gitmemeli. Yalnız son `POSTA_EN_FAZLA_GUN` günün raporu — Task 2 testi.
2. **Aynı anda iki çağrı:** panelin ilerleticisi ile zamanlayıcı aynı dakikada dağıtıcıyı koşturur; aynı haber iki
   kez gitmemeli (süreç kilidi) — Task 2 testi.
3. **Alıcı dosyası bozuk:** geçersiz JSON, liste yerine dizgi, satır sonu taşıyan "adres" (başlık enjeksiyonu) —
   hiçbir mail gitmez, neden adres yazmadan görünür — Task 2 testi.
4. **SMTP hata iletisinde adres:** `SMTPRecipientsRefused` iletisi alıcı adreslerini taşır; kayda ve çıktıya
   yalnız sınıf adı girer — Task 2 testi.
5. **Bağlantıdaki kayıt açılamıyor:** yetki yok, kayıt yok ya da `?soru=` bozuk — panel "bağlantını kontrol et"
   demez, kaydın bulunamadığını söyler; bozuk değer sunucuya hiç gitmez — Task 5 testi.

---

### Task 1: Rakamlar, aday tarama ve şablon (saf kısım)

**Files:** Modify `bin/ayar.py` (tavanlar bloğunun sonu) · Create `bin/rapor_postasi.py`,
`tests/test_rapor_postasi.py`

**Interfaces — Produces:**
- `ayar.POSTA_GUNLUK_TAVAN = 10` — gün başına **mail** (rapor başına bir mail) *(planlayıcının kararı: rakam)*
- `ayar.POSTA_EN_FAZLA_GUN = 2` — id tarihi bugünden bu kadar günden eski raporun haberi gitmez
  *(planlayıcının kararı; Review Focus 1)*
- `ayar.POSTA_SMTP_ZAMAN_ASIMI_SN = 20` *(planlayıcının kararı)*
- `ayar.POSTA_IZINLI_ALAN = "nove.group"` — alıcı adresi yalnız `@nove.group` ile biter *(Kağan, 23.11.2026)*
- `rapor_postasi.RAPOR_ADLARI = {"kalite-gunluk": "Kalite günlük raporu"}`
- `rapor_postasi.tur_ve_tarih(soru_id: str) -> tuple[str, datetime.date] | None` — kalıp
  `^rapor-([a-z0-9-]+)-(\d{8})$` → `("<danışman>-gunluk", tarih)`; kalıba uymayan ya da geçersiz tarih → `None`
- `rapor_postasi.adaylar(kok) -> list[dict]` — `yanitlar/*.md` içinden `- gorunurluk:` taşıyan **ve**
  `- etiket: onaylı` olan **ve** id'si kalıba uyan kayıtlar; `{"id", "tur", "tarih"}`, id sırasıyla. Alanlar
  `soru_kaydi.alan(metin, ...)` ile okunur (yalnız başlık; yanıt gövdesindeki sahte `- etiket:` satırı sayılmaz).
- `rapor_postasi.sablon(tur: str, tarih: datetime.date, soru_id: str, panel_adres: str) -> tuple[str, str]`
  (konu, gövde). `tur` `RAPOR_ADLARI`'nda yoksa `KeyError`.

Sabit metin *(planlayıcının kararı: cümlenin tam hâli; spec "tek cümle + bağlantı" der)*:

```
Konu : Kalite günlük raporu hazır — 23.11.2026
Gövde: Kalite günlük raporu (23.11.2026) panelde hazır; okumak için giriş yapın:\n
       https://panel.ornek/?soru=rapor-kalite-20261123\n
```

Bağlantı `panel_adres.rstrip("/") + "/?soru=" + soru_id`.

- [ ] **Step 1: Failing tests** (`tests/test_rapor_postasi.py`; yardımcı `defterle(kok, soru_id, etiket="onaylı",
  gorunurluk="kurul", govde="## Yanıt\n...")` — `soru_kapisi.ilet`'in yazdığı başlık biçimiyle `yanitlar/<id>.md`):
  - `test_tur_ve_tarih`: `rapor-kalite-20261123 → ("kalite-gunluk", date(2026, 11, 23))` ·
    `rapor-satis-muduru-20261123 → ("satis-muduru-gunluk", …)` · `20261123-1105-abcd → None` ·
    `rapor-kalite-20261340 → None` · `rapor-kalite-2026112 → None`
  - `test_adaylar_yalniz_onayli_zamanli_rapor`: dört kayıt — onaylı+gorunurluk · `CEO kontrolü yapılmadı` ·
    `onaylanamadı` · gorunurluk'suz onaylı insan sorusu (`20261123-1105-abcd`) → `[a["id"] for a in adaylar(kok)]
    == ["rapor-kalite-20261123"]`
  - `test_govdedeki_sahte_etiket_sayilmaz`: etiket `onaylanamadı`, gövdede `- etiket: onaylı` satırı → `adaylar == []`
  - `test_defter_yoksa_bos`: `yanitlar/` yok → `[]`
  - `test_sablon_konu_ve_baglanti`: konu `== "Kalite günlük raporu hazır — 23.11.2026"`; gövde
    `https://panel.ornek/?soru=rapor-kalite-20261123` içerir; `panel_adres="https://panel.ornek/"` ile çift `/` yok
  - `test_sablon_veri_tasimaz`: `sablon` imzasında defter metni yok (`inspect.signature` parametreleri
    `== ["tur", "tarih", "soru_id", "panel_adres"]`); gövdedeki rakamlar yalnız tarih ve id'den gelir —
    `re.sub(r"23\.11\.2026|rapor-kalite-20261123", "", govde)` içinde `\d` eşleşmesi yok
  - `test_ayar_rakamlari`: `POSTA_GUNLUK_TAVAN == 10`, `POSTA_EN_FAZLA_GUN == 2`, `POSTA_SMTP_ZAMAN_ASIMI_SN == 20`
- [ ] **Step 2:** Run `python3 -m unittest tests.test_rapor_postasi -v` → FAIL (`ModuleNotFoundError`)
- [ ] **Step 3:** Yaz. Modül başlığı (docstring): ne yapar, üç kilit, kullanım satırları, "mailde yalnız haber"
  (ANAYASA §1 istisnası, spec yolu). `sys.path` ve `KOK` kalıbı `bin/soru_kapisi.py`'deki gibi.
- [ ] **Step 4:** Run aynı komut → OK; `python3 -m unittest discover -s tests` → OK, `skipped=9`, sayı > 931
- [ ] **Step 5:** `git commit -m "feat(posta): aday tarama, rapor türü ve haber şablonu"`

### Task 2: Kilitler, alıcılar, gönderim ve kayıt

**Files:** Modify `bin/rapor_postasi.py`, `tests/test_rapor_postasi.py`, `.gitignore` (satır
`deploy/posta-alicilari.json`, `deploy/roller.json` satırının yanına) · Create
`deploy/posta-alicilari.json.example` (`{"kalite-gunluk": ["ornek.bir@nove.group", "ornek.iki@nove.group"]}`)

**Interfaces — Consumes:** `adaylar`, `sablon`, `RAPOR_ADLARI` (Task 1). **Produces:**
- `ISTISNA_ISARETI = "İstisna — rapor postası"` · `AJAN_ISARETI = "CLAUDECODE"` ·
  `GEREKLI_ANAHTARLAR = ("POSTA_SMTP_SUNUCU", "POSTA_SMTP_PORT", "POSTA_KULLANICI", "POSTA_SIFRE",
  "POSTA_GONDEREN", "PANEL_ADRES")`
- `class PostaHatasi(Exception)` — iletisi adres taşımaz
- `kilitler(kok, ortam: dict) -> list[str]` — tutmayan kilitlerin nedenleri (boş liste = üçü de tutuyor).
  Kilit 2 ayrıca: `POSTA_SMTP_PORT` tam sayı değilse ve `PANEL_ADRES` `http://`/`https://` ile başlamıyorsa tutmaz
  *(planlayıcının kararı)*. Neden metni yalnız anahtar **adlarını** yazar, değer yazmaz.
- `alicilari_oku(kok) -> dict[str, list[str]]` — `deploy/posta-alicilari.json`; dosya yoksa `{}`; geçersiz JSON,
  sözlük olmayan kök, liste olmayan değer ya da `^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]{2,}$` desenine uymayan
  öğe ya da `@` + `ayar.POSTA_IZINLI_ALAN` ile bitmeyen adres (alt alan adı da değil; büyük/küçük harf duyarsız)
  → `PostaHatasi("alıcı dosyası bozuk: <tür adı ya da 'kök'>")` — tek bir alan dışı adres bütün gönderimi durdurur. Adresler `strip().lower()`, yinelenen atılır.
- `kayit_yolu(kok, soru_id) -> Path` (`sirket-log/posta/<id>.json`) · `kayit_oku(kok, soru_id) -> dict | None`
  (bozuk dosya → `None`)
- `calistir(kok, simdi=None, kuru=False, ortam=None) -> dict` —
  `{"kilitler": [str], "sonuclar": [{"id", "tur", "sonuc", "alici_sayisi", "konu"}], "bugun": int, "tavan": int}`.
  `sonuc` ∈ `gonderildi · alici-yok · hata · tavan · eski · ad-yok · gonderilecek` (yalnız kuru) `· kilitli`.
  `ortam` verilmezse `{**os.environ, **ayar.env_yukle(Path(kok) / ".env")}` — `os.environ` **değiştirilmez**
  (geçici `kok`'lu testler gerçek `.env`'i görmez) *(planlayıcının kararı)*.

Kayıt: `{"id", "tur", "durum": "gonderildi" | "alici-yok" | "hata", "zaman" (İstanbul, ISO, saniye),
"alici_sayisi": int, "deneme": int, "hata": "<istisna sınıf adı>"}` (`hata` yalnız `durum == "hata"`).

`calistir` sırası (aday başına, id sırasıyla) — imza ve testlerin belirlemediği tek akış:

1. Kaydı `gonderildi` olan aday atlanır (sonuçlara girmez).
2. `tarih < bugün − POSTA_EN_FAZLA_GUN` → `eski`, kayıt yazılmaz.
3. `tur` `RAPOR_ADLARI`'nda yok → `ad-yok`, kayıt yazılmaz *(planlayıcının kararı)*.
4. `kuru` değilse ve `kilitler(...)` boş değilse → kalan adaylar `kilitli`, kayıt yazılmaz, SMTP açılmaz.
5. Alıcı listesi yok ya da boş → kayıt `alici-yok` (`alici_sayisi: 0`); tavandan düşmez. Sonraki çağrıda yeniden
   bakılır — yalnız `gonderildi` kesindir *(planlayıcının kararı)*.
6. Bugün `gonderildi` sayısı (`kayıt.zaman` İstanbul günü) `>= POSTA_GUNLUK_TAVAN` → `tavan`, kayıt değişmez.
7. Gönder: rapor başına **bir** `EmailMessage` — `From: POSTA_GONDEREN`, `To: POSTA_GONDEREN`, alıcılar
   yalnız zarfta: `send_message(msg, to_addrs=alicilar)`; mesajda `Bcc`/`Cc` başlığı yok, alıcılar birbirini görmez
   *(Kağan, 23.11.2026: gizli alıcı)*; düz metin; tavan mail sayar. Port `465` → `smtplib.SMTP_SSL`,
   değilse `smtplib.SMTP` + `starttls()`; ikisi de `timeout=ayar.POSTA_SMTP_ZAMAN_ASIMI_SN`; `login`;
   `send_message` *(planlayıcının kararı)*. Bağlantı çağrı başına bir kez, ilk gönderimde açılır.
8. Bağlantı/giriş hatası → o aday `hata`, döngü biter (kalanlar sonraki çağrıya). `send_message` hatası → o aday
   `hata`, döngü sürer. Her `hata` kaydında `deneme` bir artar.

`kuru`: 1–3 ve 5–6 aynı, hiçbir kayıt yazılmaz, SMTP açılmaz; gönderilecek aday `gonderilecek`; `kilitler`
üçü de raporlanır ama listelemeyi durdurmaz. Süreç kilidi: `sirket-log/posta/.kilit` üzerinde
`fcntl.flock(LOCK_EX | LOCK_NB)`; alınamazsa `{"kilitler": ["başka bir gönderim sürüyor"], "sonuclar": []}`
(kuru koşu kilit almaz).

- [ ] **Step 1: Failing tests.** Ortak: `class SahteSMTP` — sınıf düzeyinde `ornekler` listesi; `__init__(host,
  port, timeout=None)`, `starttls()`, `login(k, s)`, `send_message(msg)` (mesajı `gonderilen`'e ekler),
  `quit()`; `hata_ver` sınıf alanı verilirse ilgili adımda o istisnayı fırlatır. `kur()` yardımcıları: geçici
  `kok`'a `ANAYASA.md` (içinde `ISTISNA_ISARETI`), `deploy/posta-alicilari.json`, `defterle(...)`;
  `ORTAM = {anahtarların altısı; port "587", PANEL_ADRES "https://panel.ornek"}` (`CLAUDECODE` yok);
  `SIMDI = datetime(2026, 11, 23, 11, 5, tzinfo=ISTANBUL)`.
  - `test_gonderir_ve_kaydeder`: bir aday, iki alıcı → `SahteSMTP` bir mesaj; `msg["Subject"] ==
    "Kalite günlük raporu hazır — 23.11.2026"`; `msg["From"] == msg["To"] == ORTAM["POSTA_GONDEREN"]`; `"Bcc" not in msg`; `to_addrs` iki alıcı;
    `msg.as_string()` alıcı adreslerinden hiçbirini içermez (SahteSMTP `send_message(msg, to_addrs=None)` ikisini de
    kaydeder); kayıt
    `durum == "gonderildi"`, `alici_sayisi == 2`; `starttls` çağrıldı, `SMTP_SSL` kullanılmadı
  - `test_port_465_ssl`: port `"465"` → `SMTP_SSL` örneği, `starttls` çağrılmadı
  - `test_govdeye_rapor_metni_girmez`: defter gövdesi `## Kurula not\nGizli not 4711\n\n## Yanıt\nAyşe Örnek 87,5
    puan\n`, soru `"Günlük kalite raporu 31 görüşme"` → mesajın `as_string()`'inde `4711`, `87,5`, `Ayşe`,
    `Örnek`, `31 görüşme`, `Gizli` **yok**; `msg.is_multipart()` yanlış (ek yok)
  - `test_idempotent`: `calistir` iki kez → toplam bir mesaj; ikinci dönüşte `sonuclar == []`
  - `test_kilit_anayasa`: `ANAYASA.md`'de işaret yok → mesaj yok, kayıt dosyası yok, `kilitler` bir öğe ve
    `"ANAYASA"` içerir, aday `sonuc == "kilitli"`
  - `test_kilit_env_eksik`: `POSTA_SIFRE` ve `PANEL_ADRES` yok → mesaj yok; neden iki adı da sayar; nedenlerde
    `ORTAM` değerlerinden hiçbiri geçmez
  - `test_kilit_env_bicim`: port `"abc"` → kilit; `PANEL_ADRES="panel.ornek"` → kilit
  - `test_kilit_ajan_ortami`: `ORTAM + {"CLAUDECODE": "1"}` → mesaj yok, kayıt yok; `kuru=True` ile aynı ortamda
    `sonuc == "gonderilecek"`, `SahteSMTP.ornekler == []`
  - `test_alici_yok`: dosyada tür yok → mesaj yok, kayıt `alici-yok`/`0`; dosya hiç yok → aynı; sonra tür eklenip
    yeniden `calistir` → gönderilir, kayıt `gonderildi`
  - `test_alici_dosyasi_bozuk` (Review Focus 3): (a) `{"kalite-gunluk": "a@nove.group"}` · (b) geçersiz JSON ·
    (c) `["ornek.bir@nove.group\nBcc: x@disari.ornek"]` · (d) alan dışı `["ornek.bir@nove.group",
    "biri@disari.ornek"]` · (e) benzer alan `["biri@nove.group.disari.ornek"]` → beşinde mesaj yok, `kilitler` `"alıcı dosyası bozuk"`
    içerir ve `@` içermez
  - `test_tavan`: `mock.patch.object(ayar, "POSTA_GUNLUK_TAVAN", 1)`; iki tür/iki aday (ikinci tür için
    `mock.patch.dict(rapor_postasi.RAPOR_ADLARI, {"okr-gunluk": "OKR günlük raporu"})`) → bir mesaj, ikinci
    `sonuc == "tavan"` ve kaydı yok; `simdi + 1 gün` ile yeniden → ikinci gider
  - `test_eski_rapor_gitmez` (Review Focus 1): adaylar `rapor-kalite-20261023`, `…20261120`, `…20261121`,
    `…20261123`; `SIMDI` 23.11 → mesaj yalnız `…1121` ve `…1123` için; diğerleri `eski`, kayıtları yok
  - `test_hata_yeniden_denenir`: `send_message` `smtplib.SMTPRecipientsRefused({"ornek.bir@nove.group": (550,
    b"x")})` fırlatır → kayıt `hata`, `hata == "SMTPRecipientsRefused"`, `deneme == 1`; kayıt dosyasının ham
    metninde ve dönüş değerinin `json.dumps`'ında `@` yok (Review Focus 4); sahte düzeltilip yeniden → `gonderildi`
  - `test_baglanti_hatasi_donguyu_bitirir`: `SahteSMTP.__init__` `OSError` fırlatır, iki aday → ilki `hata`
    (`"OSError"`), ikincisinin kaydı yok; `SahteSMTP` bir kez denendi
  - `test_ayni_anda_iki_cagri` (Review Focus 2): test `sirket-log/posta/.kilit`'i kendi açıp `flock` ile tutar →
    `calistir` mesaj göndermez, `kilitler == ["başka bir gönderim sürüyor"]`; kilit bırakılınca gönderir
  - `test_kayitta_adres_yok`: başarılı gönderimden sonra `sirket-log/posta/` altındaki bütün dosyalarda `@` yok
  - `test_ortam_varsayilani_kok_env`: `ortam` verilmeden, geçici `kok`'ta `.env` yok ve
    `mock.patch.dict(os.environ, {}, clear=True)` → kilit 2 altı adı sayar; çağrıdan sonra `os.environ` değişmemiş
  - `test_ornek_dosya_gecerli`: `deploy/posta-alicilari.json.example` geçerli JSON, `alicilari_oku` deseninden
    geçer; `.gitignore` `deploy/posta-alicilari.json` satırını taşır
- [ ] **Step 2:** Run `python3 -m unittest tests.test_rapor_postasi -v` → yeni testler FAIL (`AttributeError`)
- [ ] **Step 3:** Yaz (yukarıdaki sıra). Bozuk alıcı dosyası `calistir` içinde yakalanır: iletisi `kilitler`'e
  eklenir, gönderim yapılmaz; adaylar (kuru koşuda da) `kilitli` döner.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(posta): kilitler, alıcı listesi, gönderim kaydı ve günlük tavan"`

### Task 3: Komut satırı ve `--kuru`

**Files:** Modify `bin/rapor_postasi.py`, `tests/test_rapor_postasi.py`

**Interfaces — Consumes:** `calistir`, `AJAN_ISARETI` (Task 2). **Produces:**
- `bas(sonuc: dict, simdi, kuru: bool) -> None` — stdout'a özet
- `main(argv, kok=None, ortam=None) -> int` — `0` tamam (gönderilecek bir şey olmaması da) · `1` kilit tutmadı
  ya da en az bir `hata` · `2` kullanım hatası (bilinmeyen `--` bayrağı ya da konumsal argüman). `--kuru` her
  zaman `0`. `--kuru` yokken `ortam.get(AJAN_ISARETI)` doluysa `calistir` çağrılmadan
  `durdu — ajan ortamında gönderim kapalı; yalnız --kuru.` basıp `1` (`bin/formdan_takim.py:469-483` deseni).

Çıktı biçimi (adres yok; satır başlıkları sabit):

```
rapor postası — 2026-11-23 11:05 (kuru)
  KİLİT ANAYASA.md'de "İstisna — rapor postası" metni yok
  KİLİT .env eksik: POSTA_SMTP_SUNUCU, POSTA_SIFRE
  GÖNDER    rapor-kalite-20261123 · kalite-gunluk · "Kalite günlük raporu hazır — 23.11.2026" · 2 alıcı
  ALICI YOK rapor-okr-20261123 · okr-gunluk
  → 1 haber · bugün gönderilen 0/10
  (kuru koşu: mail gönderilmedi, kayıt yazılmadı)
```

Diğer satır başlıkları: `GİTTİ`, `HATA` (+ sınıf adı), `TAVAN`, `ESKİ`, `AD YOK`, `KİLİTLİ`.

- [ ] **Step 1: Failing tests** (`contextlib.redirect_stdout`; Task 2'nin `kur()` ve `SahteSMTP`'si):
  - `test_kuru_ajan_ortaminda_listeler`: `main(["--kuru"], kok, ortam=ORTAM + {"CLAUDECODE": "1"})` → `0`; çıktıda
    `rapor-kalite-20261123`, `2 alıcı`, `kuru koşu`; çıktıda `@` yok; `SahteSMTP.ornekler == []`;
    `sirket-log/posta/` altında `.json` yok
  - `test_ajan_ortaminda_yazan_kosu_durur`: `main([], …CLAUDECODE…)` → `1`, çıktıda `yalnız --kuru`, mesaj yok
  - `test_kilitler_kuruda_gorunur`: `ANAYASA.md` işaretsiz, `ortam={}` → `--kuru` `0`; çıktıda iki `KİLİT` satırı
    ve yine `GÖNDER` satırı
  - `test_gercek_kosu_cikis_kodlari`: kilitler tamam → `0` ve `GİTTİ`; kilit tutmuyor → `1`; `send_message`
    hatası → `1` ve `HATA SMTPRecipientsRefused`, çıktıda `@` yok
  - `test_kullanim_hatasi`: `main(["--gonder"])` ve `main(["x"])` → `2`
  - `test_alt_surec_kuru` (bitiş ölçütü): `subprocess.run([sys.executable, "bin/rapor_postasi.py", "--kuru"],
    cwd=KOK, env={**os.environ, "CLAUDECODE": "1"}, capture_output=True, text=True)` → `returncode == 0`,
    stdout `rapor postası —` ile başlar, stdout+stderr'de `@` yok
- [ ] **Step 2:** Run `python3 -m unittest tests.test_rapor_postasi -v` → yeni testler FAIL
- [ ] **Step 3:** Yaz. `if __name__ == "__main__": sys.exit(main(sys.argv[1:]))`.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK; `python3 bin/rapor_postasi.py --kuru` (ajan ortamında)
  çıkış `0`, adres yazmadan liste ve tutmayan kilitler
- [ ] **Step 5:** `git commit -m "feat(posta): komut satırı ve kuru koşu"`

### Task 4: Dağıtıcı tetiği

**Files:** Modify `bin/dagitici.py` (`sorulari_ilerlet` 470-503, `dagit` 543-574, modül başlığı),
`sirket/IS-DAGITIMCI.md` (iletim adımına bir cümle: "başarılı iletimden sonra `bin/rapor_postasi.py` çağrılır;
hatası dağıtımı durdurmaz") · Test: `tests/test_dagitici_soru_akisi.py`

**Interfaces — Consumes:** `rapor_postasi.calistir(kok, simdi=...)` (Task 2). **Produces:**
- `dagitici._posta_tetikle(kok, simdi) -> None` — `rapor_postasi`'yı fonksiyon içinde içe aktarır, `calistir`'ı
  çağırır; **her** `Exception` yakalanır. `dagitici.log`'a `_log_yaz` ile yazar (`takim` alanı `posta`): tutmayan
  her kilit için `kilit | <neden>`, `gonderildi` dışındaki her sonuç için `<sonuc> | <id>`, gönderilenler için tek
  satır `gonderildi | <n> haber`, istisnada `hata | <sınıf adı>`.
- `sorulari_ilerlet(kok, simdi=None, kuru=False, ceo_baslat=None, ilet=None, posta=None)` — döngü bittikten
  sonra, `kuru` değilse ve bu turda en az bir adım `iletildi` olarak kaldıysa (`IletHatasi` ile `hata`'ya
  dönmediyse) `(posta or _posta_tetikle)(kok, simdi)` **bir kez** çağrılır *(planlayıcının kararı: iletim başına
  değil tur başına bir çağrı — betik defterin tamamını taradığı için eşdeğer)*. `onaylanamadı` iletimi tetiklemez.
  Dönüş değeri değişmez.

Not: var olan testler geçici `kok` ile çalışır; varsayılan tetik orada kilit 1'de durur (`ANAYASA.md` yok),
mail yolu açılmaz. Yeni testler `posta`'yı sahteler.

- [ ] **Step 1: Failing tests** (`class PostaTetigiTesti(Kurulum)`):
  - `test_iletimden_sonra_posta_cagrilir`: `DENETCI_KABUL, CEO_ONAY`; `posta = mock.MagicMock()` →
    `posta.assert_called_once_with(self.kok, OGLEN)`
  - `test_onaylanamadida_posta_yok`: `DENETCI_RED` → `posta.assert_not_called()`
  - `test_kuruda_posta_yok`: `kuru=True` → çağrılmaz
  - `test_ilet_hatasinda_posta_yok`: `self.ilet.side_effect = soru_kapisi.IletHatasi("x")` → çağrılmaz, adım `hata`
  - `test_posta_hatasi_dagiticiyi_durdurmaz`: `mock.patch.object(rapor_postasi, "calistir",
    side_effect=RuntimeError("smtp a@b.c"))`, `posta` verilmez → `sorulari_ilerlet` istisnasız döner, adım
    `iletildi`; `sirket-log/dagitici.log` `posta | hata | RuntimeError` içerir ve `a@b.c` içermez
  - `test_posta_sonucu_loga_duser`: `calistir` `{"kilitler": ["ANAYASA.md'de … yok"], "sonuclar": [{"id":
    "rapor-kalite-20261012", "sonuc": "kilitli", …}], …}` döner → logda `posta | kilit |` ve `posta | kilitli |
    rapor-kalite-20261012`
  - `test_dagit_tetigi_baglar`: `DagitTesti` deseniyle `mock.patch.object(dagitici, "_posta_tetikle")` +
    onaylı kayıt → `dagit` sonunda bir kez çağrıldı
- [ ] **Step 2:** Run `python3 -m unittest tests.test_dagitici_soru_akisi -v` → yeni testler FAIL (`TypeError: posta`)
- [ ] **Step 3:** Yaz. `dagit` `sorulari_ilerlet`'e `posta=_posta_tetikle` geçirir (modül adından okunur ki
  `mock.patch.object` tutsun).
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(dagitici): başarılı iletimden sonra rapor postası tetiği"`

### Task 5: Panel `?soru=<id>` bağlantısı

**Files:** Create `panel/soru-baglantisi.js`, `tests/test_soru_baglantisi.py` · Modify `panel/index.html`
(120-122: `<script src="soru-baglantisi.js">`, `panel.js`'ten önce), `panel/panel.js` (`toOffice` 388-392,
`satirAc` 654-664, `boot` 795-803), `panel/README.md` (bir satır), `tests/test_panel_statik.py`,
`tests/test_panel_sunucu.py`

**Interfaces — Produces** (`panel/yanit-karti.js` sarmalayıcı deseni: tarayıcıda `window.NoveSoruBaglantisi`,
node'da `module.exports`):
- `NoveSoruBaglantisi.oku(search: string) -> string | null` — ilk `soru` parametresi `/^[a-z0-9-]{1,64}$/`'e
  uyuyorsa o, değilse `null` (`bin/panel_defter.ID_DESENI` ile aynı desen)
- `NoveSoruBaglantisi.temiz(search: string) -> string` — `soru` parametreleri atılmış sorgu (`"?a=1"` ya da `""`)

`panel.js` değişiklikleri:
- `let istenenSoru = DEMO ? null : NoveSoruBaglantisi.oku(location.search);`
- `async function istenenAc()` — `istenenSoru` yoksa döner; değeri alır, `istenenSoru = null` yapar,
  `history.replaceState(null, '', location.pathname + NoveSoruBaglantisi.temiz(location.search))` ile parametreyi
  adresten siler, `satirAc(id, true)` çağırır. Parametre **tüketilene kadar** durur: oturumu olmayan kullanıcı
  giriş yapınca kayıt açılır.
- Çağrı yerleri: `toOffice` ve `boot`'taki açık oturum yolu — ikisinde de `defterYukle().then(istenenAc)`.
- `satirAc(id, baglantidan)` — `baglantidan` doğruyken `s.durum === 404` → `gs.hata = 'Bu kayıt bulunamadı ya da
  görme yetkin yok.'`, `st.panel = 'akis'`, `renderApp()` *(planlayıcının kararı: sessiz kalmak yerine tek satır
  bilgi; sunucu 404'te "yok" ile "göremez"i ayırt etmez, panel de etmez)*. Var olan `gs.bekleyen` koruması kalır:
  kullanıcının bekleyen sorusu varsa bağlantı açılmaz, rapor defter listesinde durur *(planlayıcının kararı)*.

- [ ] **Step 1: Failing tests.**
  `tests/test_soru_baglantisi.py` (`@unittest.skipUnless(shutil.which("node"), "node yok")`, `test_sahne_sira.py`
  çağrı deseni):
  - `test_gecerli_id`: `oku("?soru=rapor-kalite-20261123") == "rapor-kalite-20261123"`; `oku("?a=1&soru=x1") == "x1"`
  - `test_bozuk_deger_null` (Review Focus 5): `"?soru="`, `"?soru=../../etc"`, `"?soru=Rapor-Kalite"`,
    `"?soru=a%20b"`, `"?soru=" + "a"*65`, `""`, `"?demo"` → hepsi `null`
  - `test_ilk_parametre`: `oku("?soru=a&soru=b") == "a"`
  - `test_temiz`: `temiz("?soru=x") == ""` · `temiz("?soru=x&a=1") == "?a=1"` · `temiz("?a=1") == "?a=1"`

  `tests/test_panel_statik.py`:
  - `test_soru_baglantisi_kullanilir`: `panel.js`'te `NoveSoruBaglantisi.oku(location.search)`,
    `async function istenenAc(`, `history.replaceState(`, `defterYukle().then(istenenAc)` (iki kez),
    `Bu kayıt bulunamadı ya da görme yetkin yok.`; `DEMO ? null :` ile başlayan atama
  - `test_betik_sirasi`'na ek: `index.html`'de `soru-baglantisi.js` `panel.js`'ten önce

  `tests/test_panel_sunucu.py` (`AdaptorTesti`):
  - `test_soru_parametreli_kok_index_doner`: `GET /?soru=rapor-kalite-20261123` → `200`, gövdede `Nove AI`
    (oturumsuz; sayfa veri taşımaz, veri `/api/sorular/<id>`'den oturumla gelir)
- [ ] **Step 2:** Run `python3 -m unittest tests.test_soru_baglantisi tests.test_panel_statik
  tests.test_panel_sunucu -v` → yeni testler FAIL (sunucu testi şimdiden geçer: davranışı sabitler)
- [ ] **Step 3:** Yaz. `oku`/`temiz` `URLSearchParams` ile.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK, `skipped=9`, sayı > 931.
  `git diff --stat main -- bin/panel.py bin/panel_defter.py bin/soru_kapisi.py bin/yanit_defteri.py` → boş.
  `python3 bin/rapor_postasi.py --kuru` → çıkış `0`, çıktıda `@` yok.
- [ ] **Step 5:** `git commit -m "feat(panel): ?soru=<id> bağlantısı girişten sonra kaydı açar"`

---

## Kağan'ın elle adımları (ajan yapmaz)

Sıra önemli: 1–4 bitmeden betik göndermez (kilitler); 5 gerçek deneme.

1. **`ANAYASA.md` §1 sonuna** spec'teki "İstisna — rapor postası" metnini işle (tarihiyle). Kilit 1 tam olarak
   `İstisna — rapor postası` dizgisini arar.
2. **`.env`**: `POSTA_SMTP_SUNUCU`, `POSTA_SMTP_PORT` (`465` → SSL, başka port → STARTTLS), `POSTA_KULLANICI`,
   `POSTA_SIFRE`, `POSTA_GONDEREN`, `PANEL_ADRES` (`https://…`, sonda `/` olsa da olur). Aynı altı adı değersiz
   olarak `.env.example`'a ekle (ajan `.env.*` okuyamaz).
3. **`deploy/posta-alicilari.json`**: `deploy/posta-alicilari.json.example`'ı kopyala, gerçek adresleri yaz
   (`{"kalite-gunluk": [...]}`). Dosya git dışı (`.gitignore`, Task 2).
4. **`.claude/settings.json` → `permissions.deny`**'e üç satır: `Read(./deploy/posta-alicilari.json)`,
   `Write(./deploy/posta-alicilari.json)`, `Edit(./deploy/posta-alicilari.json)`.
5. **Deneme (kendi terminalinde, `CLAUDECODE` yok):** `python3 bin/rapor_postasi.py --kuru` → kilit satırı yok,
   beklenen haber listede; sonra `python3 bin/rapor_postasi.py` → `GİTTİ`; maildeki bağlantı girişten sonra raporu
   açıyor mu; `sirket-log/posta/<id>.json` `gonderildi`. Panel bağlantısı sunucu adresini ister — sunucuya
   taşımadan sonra.
6. Metin işlendikten sonra `NOVE-KURULUM.md` ve `CLAUDE.md` Yasaklar satırı istisnayı anar (spec "Kurulumda kalan").

## Kararlar (Kağan, 23.11.2026 — önceki açık sorular)

1. `POSTA_GUNLUK_TAVAN = 10` ve `POSTA_EN_FAZLA_GUN = 2` uygun.
2. Alıcılar gizli: `To` gönderen adres, alıcılar yalnız zarfta (Task 2 adım 7).
3. Alan adı kilidi var: yalnız `@nove.group` (`ayar.POSTA_IZINLI_ALAN`, Task 2 `alicilari_oku`).
4. Zamanlayıcıya ayrı yeniden deneme tetiği şimdilik yok; zamanlayıcı sunucuya taşınınca eklenir.

## Uygulama (23.11.2026)

5 görev, görev başına inceleme, son dal incelemesi Fable 5.2. 989 test OK (skipped=9; taban 931).
`python3 bin/rapor_postasi.py --kuru` (ajan ortamı) → çıkış 0, üç KİLİT satırı, adres yok.

Son incelemede kapatılan üç açık (4d6e867): `.env`'deki `CLAUDECODE=` satırı ajan kilidini açamaz; alıcı dosyası
hata iletisi ham anahtarı yazmaz; SMTP TLS sertifikası doğrulanır (başarısız bağlantı kapatılır).

Kurulum kararları (controller): sahte SMTP `send_message(msg, to_addrs=None)` (gizli alıcı) · commit atfı Opus 5.5 ·
`POSTA_IZINLI_ALAN` testli · `from __future__ import annotations` (Python 3.9).

### Sonraya kalan küçükler (son inceleme: bekleyebilir)

- Kısmi alıcı reddi (`send_message` dönüşü) yok sayılıyor; `alici_sayisi` reddedilenleri de sayıyor — ilk takip işi.
- `SMTPServerDisconnected` sonrası döngü ölü bağlantıyla sürüyor (kalanlar `hata`, sonra yeniden denenir).
- Süreç kilidi doluyken dönüşte `bugun: 0`; gelecek tarihli id üst sınırı yok; `_kayit_yaz` gönderim sonrası
  hata verirse tek tekrar gönderim; zaman aşımı DATA sonrası olursa tekrar (en az bir kez teslim).
- Dağıtıcı logu her turda `eski`/`ad-yok` satırı yazar — sunucuda raporlar birikince gürültü; logda atlanmalı.
- `Date`/`Message-ID` başlığı yok; `PANEL_ADRES` `http://` kabul ediyor.
- Alıcı dosyasında biçimsiz ama geçerli listeli anahtar sessizce kabul ediliyor (kullanılmaz).
- Kilit yarışında geç kalan haber bir sonraki iletime kalır.
- Panel: `replaceState` hash'i düşürür; statik testler kaynak dizgisi; tarayıcıyla uçtan uca denenmedi.
- Testler: `test_kilit_env_bicim` anahtar adını, giriş hatası testi kayıttaki sınıf adını doğrulamıyor; karma tur
  (iletildi + onaylanamadı) testi yok. `IS-DAGITIMCI.md` cümlesi s-/r- listesinde.
