---
durum: acik
guncelleme: 2026-11-23
dal: feature/sunucu-docker
pr: -
spec: docs/superpowers/specs/2026-11-23-sunucu-teslim-design.md
---

# Sunucu Teslimi (Docker Compose paketi) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (önerilen) ya da
> superpowers:executing-plans. Adımlar `- [ ]`. Her görev: önce test, kırmızıyı gör, sonra kod, yeşil, commit.
> **(Kağan)** yazan adımlar insanındır; ajan onları yapmaz, yerine geçecek bir yol da aramaz.

**Goal:** Şirket yazılımcısının `deploy/KURULUM.md`'yi okuyup `docker compose up -d` ile Kurul Ofisi'ni ayağa
kaldırabildiği teslim paketi: Docker dosyaları, kurulum doğrulaması (`bin/sunucu_kontrol.py`), Mac'ten durum taşıma
(`bin/tasima.py`) ve sunucuda çalışması için gereken üç küçük kod değişikliği.

**Architecture:** Tek imaj (Python + Node + Claude Code + supercronic), kodu kopyalamaz; depo sunucudaki klasörden
bağlanır. İki servis aynı bind mount'u görür: `panel` (ilerletici açık) ve `zamanlayici` (supercronic → `gunluk.py`).
`.env`'i servisler kendileri okur (`ayar.ortam_yukle`); compose sır taşımaz. Kod tarafında panel `--adres` alır,
vekil arkasında istemci IP'sini `X-Forwarded-For`'dan okur, `panel.py`/`gunluk.py` açılışta `.env`'i ortama yükler.

**Tech Stack:** Python 3.9 uyumlu stdlib (`argparse`, `ipaddress`, `tarfile`, `hashlib`, `fcntl`, `zoneinfo`) +
var olan `psycopg`; `unittest` + `unittest.mock`; Docker Compose, supercronic, Caddy (yalnız örnek).

**Spec:** `docs/superpowers/specs/2026-11-23-sunucu-teslim-design.md` (Kağan onayı 23.11.2026; S-1, S-2 ve iki
"inceleme bulgusu" dahil). Kararlar orada; bu plan onları yeniden açmaz. Spec dosyası değişmez. Spec'in sustuğu
yerde verilen kararlar **(plan kararı)** diye işaretlidir.

## Global Constraints

- Dal `feature/sunucu-docker` (açık; dal değiştirme). Taban: `python3 -m unittest discover -s tests` →
  `Ran 989 tests` · `OK (skipped=9)`. Sayı düşmez; her görevin sonunda tam takım koşar.
- Kod Python 3.9.6 ile çalışır (`from __future__ import annotations` gerekiyorsa eklenir); yeni bağımlılık yok.
  Tanımlayıcılar ve kullanıcıya görünen metin Türkçe.
- **Ajan `.env` ve `.env.*` dosyalarını okumaz, açmaz, grep'lemez** (`.env.example` dahil). Testler ve duman testi
  geçici klasörde **kurgusal** `.env` kullanır. Ajan `bin/sunucu_kontrol.py`'yi ve `bin/tasima.py`'yi gerçek depo
  kökünde koşturmaz (birincisi yalnız geçici kökle/konteynerde, ikincisi yalnız `--kuru`).
- **Hiçbir çıktı değer basmaz:** `sunucu_kontrol.py` ve `tasima.py` yalnız anahtar **adlarını**, sayıları ve
  sonuçları yazar. Hata iletilerine `str(e)` girmez, yalnız `type(e).__name__` (URL ve parola taşıyabilir).
- **Sır ve kişisel veri imaja/arşive/depoya girmez:** compose'ta `env_file` ve sır taşıyan `environment` yok;
  Dockerfile kodu kopyalamaz; `tasima.py` `.env`'i hiçbir koşulda paketlemez ve açmaz. Commit'lenen dosyalarda
  gerçek e-posta, alan adı, IP yok (`uye@example.com`, `panel.example.com`, `203.0.113.x`, `ornek.bir@nove.group`).
- Ajan yazamaz: `ANAYASA.md`, `takimlar/*/kurallar.md`, `formlar/onayli/`, `sirket/CEO-KIMLIGI.md`, `yanitlar/`, `.env`.
- Zamanlı işler (İstanbul): `0 8 * * *` `--sabah` · `30 9 * * 1-5` `--rapor` · `*/10 * * * *` `--ilerlet` ·
  `0 19 * * *` `--aksam`. Port yayını `127.0.0.1:8770:8770`. Bind mount hedefi `/srv/nove-kurul`.
  Taban imaj `python:3.12-slim`, Node 22, kullanıcı `nove-ajan` (root değil), `TZ=Europe/Istanbul`.
- `X-Forwarded-For` kuralı (spec, birebir): yalnız `--https-arkasinda` açıkken **ve** bağlantı loopback/özel ağdan
  geliyorsa başlığın **en sağdaki** değeri istemci IP'sidir; aksi hâlde bağlantı IP'si.
- Ajan `docker`'ı yalnız Task 8'de koşturur; `claude -p` hiçbir görevde koşmaz (`claude --version` yalnız Task 6
  sürüm sabitlemesi ve Task 8'de). Mac'te Kağan'ın çalışan servislerine (launchd işleri, 8770) dokunulmaz.
- Commit: `type(scope): Türkçe konu`; sonunda `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **`--ac` ikinci kez ya da "kirlenmiş" sunucuda:** yazılımcı compose'u taşımadan önce kaldırdı, cron
   `dagitici.log` ve `durum.json` yazdı; ya da `--ac` yarıda kesilip yeniden koşuldu. Beklenen: aynı içerik sessizce
   atlanır, farklı içerik **reddedilir**, hiçbir şey yazılmaz; `--ustune-yaz` eskiyi yedekleyip yazar — Task 5 testi.
2. **Bozuk ya da sahte `X-Forwarded-For`:** boş, `abc`, `1.2.3.4:5678`, birden çok başlık, IPv6, internetten
   doğrudan gelen istekte sahte başlık. Beklenen: çökme yok, bağlantı IP'sine düşülür, bir kişinin beş yanlış
   şifresi başkasını kilitlemez — Task 2 testi.
3. **Düşmanca/bozuk arşiv:** `../` yolu, mutlak yol, sembolik bağ üyesi, `.env` üyesi, yanlış sağlama toplamı,
   `.sha256` dosyası eksik. Beklenen: arşivin tamamı reddedilir, tek dosya yazılmaz — Task 5 testi.
4. **`sunucu_kontrol.py` hata yolunda sızıntı:** veritabanı istisnasının iletisi URL'yi (parolayla) taşır; `.env`
   okunamaz; `claude` yok. Beklenen: traceback yok, çıktıda hiçbir değer yok, çıkış 1 — Task 3 testi.
5. **Mac'te servisler açıkken paketleme:** zamanlayıcı kaldırılmamış ya da panel/sahne 8770'te çalışıyor; arşiv
   alınırken yeni soru/koşu düşer, yarım durum taşınır. Beklenen: `--paketle` reddeder ve nedeni söyler; paketleme
   boyunca koşu kilidini kendisi tutar — Task 4 testi.

---

### Task 1: Panel `--adres` ve servis açılışında `.env` yüklemesi

**Files:** Modify `bin/panel.py` (`main` 288-326), `bin/gunluk.py` (`main` 315), `panel/README.md` (bayraklar satırı) ·
Test: `tests/test_panel_sunucu.py`, `tests/test_gunluk_rapor.py`

**Interfaces — Produces:**
- `panel.py --adres ADRES` (varsayılan `"127.0.0.1"`): `ThreadingHTTPServer((arg.adres, arg.port), …)`.
  Başlangıç iletisi `panel: http://<adres>:<port> — ilerletme …` gerçek adresi basar.
- `ipaddress.ip_address(adres).is_loopback` değilse (ayrıştırılamayan ad da "değil" sayılır) stderr'e:
  `panel: uyarı: <adres> — yalnız konteyner içinde; makinede ters vekil arkasında kullan`
  *(plan kararı: spec `0.0.0.0` der; loopback dışı her adres aynı riski taşır, hepsi uyarılır)*.
- Bağlanamazsa (`OSError`): `panel: <adres>:<port> açılamadı — port dolu (`bin/sahne.py` de 8770 kullanır) ya da
  adres geçersiz` + çıkış `1` *(plan kararı: var olan "port dolu" iletisi adresi de anar)*.
- `panel.main`: `--kullanici-ekle` dalından **sonra**, `Ilerletici` kurulmadan önce `ayar.ortam_yukle(KOK / ".env")`.
  `gunluk.main`: ilk satırda `ayar.ortam_yukle(KOK / ".env")`. İkisi de modülün `KOK`'undan okur (testte
  `mock.patch.object(<modül>, "KOK", …)` tutsun); `.env` yoksa sessizce geçer (`env_yukle` `{}` döner).
- argparse açıklaması `"Nove Kurul Ofisi paneli (varsayılan 127.0.0.1)"`.

- [ ] **Step 1: Failing tests.**
  `tests/test_panel_sunucu.py`, `class AdresVeOrtamTesti` — yardımcı `kos(argv, env_metni=None)`: geçici `kok`
  (`deploy/` dizini), istenirse `kok/.env`; `mock.patch.object(panel, "KOK", kok)`,
  `mock.patch.object(panel, "ThreadingHTTPServer")` (örneğin `serve_forever`'ı hemen döner),
  `mock.patch.dict(os.environ)`, stdout/stderr yakalanır → `(rc, out, err, sunucu_mock)`:
  - `test_varsayilan_adres_127`: `kos(["--ilerletme-yok"])` → `sunucu_mock.call_args[0][0] == ("127.0.0.1", 8770)`;
    `"http://127.0.0.1:8770"` in out; `"uyarı"` not in err; `rc == 0`
  - `test_adres_0000_baglanir_ve_uyarir`: `["--adres", "0.0.0.0", "--ilerletme-yok"]` → bağ `("0.0.0.0", 8770)`;
    `"http://0.0.0.0:8770"` in out; `"yalnız konteyner içinde; makinede ters vekil arkasında kullan"` in err
  - `test_loopback_disi_adres_uyarir`: `--adres 192.0.2.10` → aynı uyarı; `--adres ::1` → uyarı yok
  - `test_baglanamazsa_1`: `ThreadingHTTPServer` `side_effect=OSError` → `rc == 1`, err `"0.0.0.0:8770 açılamadı"` içerir
  - `test_env_anahtari_dagitici_alt_surecine_ulasir` (spec testi): `env_metni="ANTHROPIC_API_KEY=sk-ant-sahte-0001\n"`,
    `os.environ`'dan anahtar önce silinir; `kos(["--ilerletme-yok"])`'tan sonra **aynı** `patch.dict` içinde
    `mock.patch.object(dagitici.subprocess, "run", return_value=mock.Mock(stdout=<geçerli haiku JSON'u>))` ile
    `dagitici.haiku_zorluk("soru")` → `run.call_args.kwargs["env"]["ANTHROPIC_API_KEY"] == "sk-ant-sahte-0001"`
    (JSON kalıbı: `tests/test_dagitici_yonlendirme.py::test_haiku_zorluk_komutu`)
  - `test_env_yokken_acilir`: `.env` yok → `rc == 0`
  - `test_kullanici_ekle_env_yuklemez`: `mock.patch.object(panel.ayar, "ortam_yukle")` +
    `["--kullanici-ekle", UYE]` (`CLAUDECODE=1`) → `ortam_yukle.assert_not_called()`

  `tests/test_gunluk_rapor.py`:
  - `IlerletTesti.test_env_anahtari_ortama_yuklenir`: geçici `kok/.env` (`ANTHROPIC_API_KEY=sk-ant-sahte-0002`),
    `mock.patch.object(gunluk, "KOK", kok)`, `mock.patch.object(gunluk.dagitici, "dagit")`, `patch.dict(os.environ)`
    → `gunluk.main(["--ilerlet"])` sonrası `os.environ["ANTHROPIC_API_KEY"] == "sk-ant-sahte-0002"`
  - Var olan `IlerletTesti.test_yalniz_dagitici_calisir`'a `mock.patch.object(gunluk.ayar, "ortam_yukle")` eklenir —
    gerçek `.env` test sürecine yüklenmesin.
- [ ] **Step 2:** Run `python3 -m unittest tests.test_panel_sunucu tests.test_gunluk_rapor -v` → yeni testler FAIL
  (`unrecognized arguments: --adres`, `KeyError: 'ANTHROPIC_API_KEY'`)
- [ ] **Step 3:** Yaz. `panel/README.md` bayraklar satırına `--adres A` (varsayılan `127.0.0.1`; `0.0.0.0` yalnız
  konteynerde) eklenir.
- [ ] **Step 4:** Run aynı komut → OK; `python3 -m unittest discover -s tests` → OK, `skipped=9`, sayı > 989
- [ ] **Step 5:** `git commit -m "feat(panel): --adres argümanı; panel ve günlük tetik açılışta .env'i yükler"`

### Task 2: Giriş freni vekil arkasında — `X-Forwarded-For`

**Files:** Modify `bin/panel.py` (`Sunucu._api` 216-237; yeni modül fonksiyonu), `panel/README.md` (fren satırı) ·
Test: `tests/test_panel_sunucu.py`

**Interfaces — Produces:**
- `panel.istemci_ip(baglanti_ip: str, xff_basliklari: list, vekil_arkasinda: bool) -> str`
- `Sunucu._api` `self.uygulama.istek(...)`'e `self.client_address[0]` yerine
  `istemci_ip(self.client_address[0], self.headers.get_all("X-Forwarded-For") or [], self.uygulama.https)` verir.
  `Uygulama` ve `DenemeFreni` **değişmez**.

Algoritma (güvenlik çekirdeği; imza ve testler tek başına belirlemez):

```python
def istemci_ip(baglanti_ip, xff_basliklari, vekil_arkasinda):
    if not vekil_arkasinda or not xff_basliklari:
        return baglanti_ip
    try:
        es = ipaddress.ip_address(baglanti_ip)
        es = getattr(es, "ipv4_mapped", None) or es
    except ValueError:
        return baglanti_ip
    if not (es.is_loopback or es.is_private):      # vekil değil: başlığa güvenilmez
        return baglanti_ip
    aday = xff_basliklari[-1].split(",")[-1].strip()   # en sağdaki: vekilin kendi eklediği
    try:
        return str(ipaddress.ip_address(aday))
    except ValueError:
        return baglanti_ip
```

Birden çok başlık satırında **son** satırın en sağdaki değeri alınır *(plan kararı)*. Geçersiz değer frene anahtar
olarak girmez (tablo çöp anahtarla şişmez).

- [ ] **Step 1: Failing tests** (`class IstemciIpTesti`):
  - `test_vekil_kapali_baslik_yok_sayilir`: `istemci_ip("127.0.0.1", ["203.0.113.7"], False) == "127.0.0.1"`
  - `test_loopback_vekilden_en_sagdaki`: `("127.0.0.1", ["198.51.100.1, 203.0.113.7"], True) == "203.0.113.7"`
  - `test_ozel_agdan_vekil` (Docker köprüsü): `("172.18.0.1", ["203.0.113.7"], True) == "203.0.113.7"`;
    `("::ffff:172.18.0.1", ["203.0.113.7"], True) == "203.0.113.7"`
  - `test_genel_ipden_baslik_yok_sayilir`: `("198.51.100.20", ["203.0.113.7"], True) == "198.51.100.20"`
  - `test_bozuk_baslik_baglanti_ipsi` (Review Focus 2): `[""]`, `["abc"]`, `["1.2.3.4:5678"]`, `["203.0.113.7, "]`,
    `[]` → hepsi `"127.0.0.1"`; `["2001:DB8::1"]` → `"2001:db8::1"`
  - `test_birden_cok_baslik_son_satir`: `("127.0.0.1", ["203.0.113.7", "203.0.113.9"], True) == "203.0.113.9"`
  - `test_adaptor_ipyi_uygulamaya_tasir` (`AdaptorTesti` deseni, gerçek soket): `uyg = panel.Uygulama(kok, https=True)`,
    `uyg.istek = mock.Mock(return_value=(200, {}, []))`; `POST /api/giris` + `X-Forwarded-For: 203.0.113.7` →
    `uyg.istek.call_args[0][4] == "203.0.113.7"`; `https=False` ile aynı istek → `"127.0.0.1"`
  - `test_bir_kisinin_kilidi_digerini_kilitlemez` (gerçek `Uygulama`, `https=True`, `roller.json` + iki kullanıcı,
    `PBKDF2_TUR` 1000): `X-Forwarded-For: 203.0.113.7` ile `baska@example.com` için beş yanlış şifre → hepsi `401`;
    sonra `X-Forwarded-For: 203.0.113.8` ile `uye@example.com` doğru şifre → `200`. Aynı senaryo `https=False` →
    son istek `429` (bugünkü davranış sabitlenir).
- [ ] **Step 2:** Run `python3 -m unittest tests.test_panel_sunucu -v` → FAIL (`AttributeError: istemci_ip`)
- [ ] **Step 3:** Yaz. `panel/README.md` fren satırı: "`--https-arkasinda` ile vekil (loopback/özel ağ) arkasında
  istemci IP'si `X-Forwarded-For`'un en sağdaki değeridir".
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "fix(panel): vekil arkasında giriş freni istemci IP'sini X-Forwarded-For'dan okur"`

### Task 3: `bin/sunucu_kontrol.py`

**Files:** Create `bin/sunucu_kontrol.py`, `tests/test_sunucu_kontrol.py`

**Interfaces — Consumes:** `ayar.env_yukle`, `ayar.kurulu_takimlar`, `ayar.takim_bilgisi`,
`rapor_postasi.GEREKLI_ANAHTARLAR`, `kalite_veri.baglanti_ac(url, baglan=None)`. **Produces:**
- `ZORUNLU = ("ANTHROPIC_API_KEY",)` · `DENETCI_ANAHTARLARI = ("NVIDIA_API_KEY", "OPENAI_API_KEY")` ·
  `DB_OKUYUCULAR = {"kalite": "QA_READONLY_URL", "okr": "OKR_READONLY_URL"}` ·
  `DURUM_YOLLARI = ("yanitlar", "sirket-log", "deploy", "formlar/onayli", "takimlar")`
- `kontroller(kok, db=False, tasima_oncesi=False, calistir=subprocess.run, baglan=None, euid=None,
  yerel_fark=None) -> list[dict]` — her öğe `{"ad", "durum": "tamam" | "uyari" | "hata" | "bilgi", "ileti"}`.
  Hiçbir kontrol istisna sızdırmaz; hiçbir şey yazmaz (yalnız okur).
- `bas(kok, sonuclar) -> None` · `main(argv, kok=None, **enjekte) -> int` — bayraklar `--db`, `--tasima-oncesi`;
  çıkış `1` en az bir `hata` varsa, yoksa `0`; bilinmeyen bayrak `2`.

Anahtarlar **yalnız** `ayar.env_yukle(kok / ".env")`'den okunur, `os.environ`'dan değil *(plan kararı: servisler
`.env`'i okur; kabukta tanımlı anahtar sahte "tamam" vermesin)*. `os.environ` değiştirilmez.

Kontroller (bu sırayla; `ad` sabit):

| `ad` | Tamam | Değilse |
|---|---|---|
| `env-dosyasi` | `.env` var, `stat.S_IMODE == 0o600` | `hata` (yok / izin `<sekizlik>`) |
| `zorunlu-anahtarlar` | `ZORUNLU` + kurulu danışmanların `gerekli_anahtarlar`'ı dolu | `hata` — `eksik: <adlar>` |
| `posta-anahtarlari` | altısı dolu | `bilgi` — `isteğe bağlı; eksik: <adlar>` |
| `claude` | `calistir(["claude", "--version"], capture_output=True, text=True, timeout=30)` dönüş `0` | `hata` (sınıf adı ya da dönüş kodu) |
| `denetci` | `DENETCI_ANAHTARLARI`'ndan biri dolu | `uyari` — `Denetçi geçici Opus yedeğine düşer (aynı aile)` |
| `saat-dilimi` | yerel UTC farkı `ZoneInfo("Europe/Istanbul")` farkına eşit *(plan kararı: fark karşılaştırması; `ayar.simdi_iso` yerel saati kullanır)* | `hata` (`ZoneInfoNotFoundError` da) |
| `depo-yazilabilir` | `os.access(W_OK)` — kök ve var olan `DURUM_YOLLARI` *(plan kararı: dosya yazıp silmez)* | `hata` — yazılamayan üst klasör adları |
| `sahiplik` | `euid != 0` ve kök, `.env`, var olan `DURUM_YOLLARI` ile birinci düzey çocuklarının `st_uid == euid` | `hata` — `root olarak koşuyor` ya da `<n> yol başka kullanıcıya ait` (yalnız sayı + üst klasör adı) |
| `roller`, `kullanicilar` | `deploy/<ad>.json` var ve JSON sözlük | `hata`; `--tasima-oncesi` ile dosya **yoksa** `uyari` — `taşımadan sonra gelir` *(plan kararı: geçiş günü 1. adım taşımadan önce temiz çıkabilsin)*; bozuk JSON her durumda `hata` |
| `db-<danışman>` (yalnız `--db`; kurulu ve `DB_OKUYUCULAR`'da olan) | `kalite_veri.baglanti_ac(url, baglan)` + `SELECT 1` | `hata` — yalnız `type(e).__name__`; URL'nin makinesi `localhost`/`127.0.0.1`/`::1` ise iletiye `adres localhost — konteynerden ulaşılmaz` eklenir. Anahtar yoksa `bilgi` — `atlandı` |

`claude` kontrolü yalnız `--version` çağırır; API'ye istek atan hiçbir çağrı yok.

Çıktı *(plan kararı: biçim)*:

```
sunucu kontrolü — /srv/nove-kurul
  [TAMAM] env-dosyasi — var, izin 600
  [HATA ] zorunlu-anahtarlar — eksik: OKR_READONLY_URL
  [BİLGİ] posta-anahtarlari — isteğe bağlı; eksik: POSTA_SIFRE, PANEL_ADRES
  [UYARI] denetci — Denetçi geçici Opus yedeğine düşer (aynı aile)
sonuç: 1 hata, 1 uyarı
```

- [ ] **Step 1: Failing tests.** Yardımcı `kur(kok, env=TAM_ENV, izin=0o600)`: `takimlar/kalite/takim.md` ve
  `takimlar/okr/takim.md` (frontmatter `gerekli_anahtarlar: [QA_READONLY_URL]` / `[OKR_READONLY_URL]`),
  `deploy/roller.json` (`{"uye@example.com": "kurul"}`), `deploy/kullanicilar.json` (`{}`), `yanitlar/`,
  `sirket-log/`, `.env`. `TAM_ENV`: `ANTHROPIC_API_KEY=sk-ant-GIZLI-4711`,
  `QA_READONLY_URL=postgresql://okuyucu:PAROLA-9911@db.ornek:5432/qa`,
  `OKR_READONLY_URL=postgresql://okuyucu:PAROLA-9922@localhost:5432/pys`, `NVIDIA_API_KEY=nvapi-GIZLI-1`.
  `TAMAM_CALISTIR = mock.Mock(return_value=mock.Mock(returncode=0, stdout="9.9.9 (Claude Code)\n"))`;
  `ISTANBUL_FARK = timedelta(hours=3)`; `durumlar(s) = {x["ad"]: x["durum"] for x in s}`.
  - `test_temiz_kurulum_cikis_0`: hepsi `tamam`, `posta-anahtarlari == "bilgi"`; `main([], kok, …) == 0`
  - `test_env_yok_ve_izin`: `.env` yok → `env-dosyasi == "hata"`, çıkış `1`; izin `0o644` → `hata`, iletide `644`
  - `test_zorunlu_anahtar_eksik`: `.env`'de `OKR_READONLY_URL` yok → `hata`, iletide ad geçer; kabukta
    `mock.patch.dict(os.environ, {"OKR_READONLY_URL": "x"})` olsa da `hata` kalır
  - `test_kurulumdaki_danismanin_anahtari_istenmez`: `takimlar/finans/takim.md` frontmatter'sız → eksik listesinde
    yalnız kurulu danışmanların anahtarları
  - `test_denetci_anahtari_yoksa_uyari_cikis_0`: `NVIDIA_API_KEY` satırı yok → `denetci == "uyari"`, çıkış `0`
  - `test_claude_yok`: `calistir` `FileNotFoundError` → `claude == "hata"`; dönüş kodu `1` → `hata`;
    `calistir.call_args[0][0] == ["claude", "--version"]` (başka çağrı yok: `call_count == 1`)
  - `test_saat_dilimi`: `yerel_fark=timedelta(0)` → `hata`; `timedelta(hours=3)` → `tamam`
  - `test_sahiplik`: `euid=0` → `hata`, iletide `root`; `euid=os.geteuid() + 1` → `hata`, iletide sayı
  - `test_depo_yazilamaz`: `sirket-log` `chmod 0o500` (temizlikte geri alınır; `os.geteuid() == 0` ise `skipTest`)
    → `depo-yazilabilir == "hata"`, iletide `sirket-log`
  - `test_roller_kullanicilar`: `kullanicilar.json` yok → `hata`, çıkış `1`; `--tasima-oncesi` → `uyari`, çıkış `0`;
    bozuk JSON + `--tasima-oncesi` → `hata`
  - `test_db_bayragi_yokken_baglanmaz`: `baglan` mock'u çağrılmaz; `db-` adlı sonuç yok
  - `test_db_basarili`: `baglan=mock` (imleç `SELECT 1`) → `db-kalite`, `db-okr` `tamam`; bağlantı kapatıldı
  - `test_db_hatasi_url_sizdirmaz` (Review Focus 4): `baglan` `side_effect=RuntimeError("connection to
    postgresql://okuyucu:PAROLA-9911@db.ornek:5432/qa failed")` → `db-kalite == "hata"`, iletide `RuntimeError`;
    `db-okr` iletisi `adres localhost` içerir
  - `test_cikti_deger_tasimaz` (Review Focus 4): yukarıdaki hata senaryosu + `calistir` `side_effect=OSError("sk-ant-GIZLI-4711")`
    ile `main(["--db"], kok, …)` stdout+stderr'inde `GIZLI`, `PAROLA`, `db.ornek`, `okuyucu`, `postgresql://`,
    `example.com`, `Traceback` **yok**; `ANTHROPIC_API_KEY` adı da (dolu olduğu için) geçmez
  - `test_hicbir_sey_yazmaz`: koşudan önce/sonra `kok` altındaki dosya listesi ve `st_mtime`'lar aynı
  - `test_kullanim_hatasi`: `main(["--x"], kok) == 2`
- [ ] **Step 2:** Run `python3 -m unittest tests.test_sunucu_kontrol -v` → FAIL (`ModuleNotFoundError`)
- [ ] **Step 3:** Yaz. Modül başlığı: ne denetler, "yalnız okur, değer basmaz, `claude`'a istek atmaz", kullanım
  satırları (`docker compose … exec panel python3 bin/sunucu_kontrol.py [--db] [--tasima-oncesi]`).
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(deploy): sunucu_kontrol.py — kurulum doğrulaması, değer basmaz"`

### Task 4: `bin/tasima.py --paketle` (Mac)

**Files:** Create `bin/tasima.py`, `tests/test_tasima.py`

**Interfaces — Consumes:** `panel_defter.acik_sorular(kok)`, `ayar.KOSU_KILIDI`, `zamanla.durum()`. **Produces:**
- `TASINANLAR = ("yanitlar", "sirket-log", "deploy/roller.json", "deploy/kullanicilar.json",
  "deploy/posta-alicilari.json", "formlar/onayli", "takimlar/*/defter.md", "takimlar/*/durum.json",
  "takimlar/*/kosu", "takimlar/*/cikti", "takimlar/bekci-telemetri.jsonl")` — S-1 listesi; son öğe
  *(plan kararı: spec saymıyor ama akşam raporu ve Denetçi telemetrisi bu dosyadan okur)*.
- `ATLANAN_ADLAR = (".DS_Store", ".kilit", "__pycache__")`
- `class TasimaHatasi(Exception)` — iletisi dosya içeriği taşımaz
- `izinli_mi(goreli: str) -> bool` — posix göreli yol; `..` ya da boş parça yok, mutlak değil; **hiçbir parçası
  `.env` ile başlamaz**; `TASINANLAR`'dan birinin kendisi ya da altı; `takimlar/<ad>/…`'da `<ad>` `_` ile başlamaz
  (`_iskelet` git'te) *(plan kararı)*; son parça `ATLANAN_ADLAR`'da değil. Paketleme ve açma **aynı** fonksiyonu kullanır.
- `dosyalar(kok) -> list[str]` — `izinli_mi` geçen düzenli dosyalar, sıralı; sembolik bağ ve özel dosya atlanır.
- `kos_kilidi(kok)` — bağlam yöneticisi: `kok / ayar.KOSU_KILIDI` üzerinde `flock(LOCK_EX | LOCK_NB)`; alınamazsa
  `TasimaHatasi("koşu kilidi dolu — süren koşu bitsin")`. Paketleme/açma **boyunca** tutulur *(plan kararı: yalnız
  bakıp bırakmak yerine tutar; arada koşu başlayamaz)*.
- `engeller(kok, mac_denetimi=None) -> list[str]` — açık soru varsa `açık soru var: <n> (<id'ler>)`;
  `mac_denetimi` verilmezse `sys.platform == "darwin"` iken: `zamanla.durum()`'da `yuklu` iş varsa
  `zamanlayıcı kurulu — önce: python3 bin/zamanla.py --kaldir`; `127.0.0.1:8770`'e 1 sn'lik soket bağlantısı
  tutarsa `8770'te panel/sahne çalışıyor — önce durdur` *(plan kararı: S-1 "zamanlayıcı kaldırıldıktan ve panel
  durdurulduktan sonra" kuralının denetimi)*. Linux'ta Mac denetimi boş döner. Zorlama bayrağı **yok**.
- `paketle(kok, cikti_dizini, simdi=None, kuru=False, mac_denetimi=None) -> dict` —
  `{"engeller": [str], "ozet": {"<üst klasör>": adet}, "toplam": int, "arsiv": Path | None, "sha256": str | None}`.
  Engel varsa ya da kilit alınamazsa arşiv yazılmaz. Arşiv `nove-tasima-YYYYMMDD-HHMM.tar.gz` (`tarfile`, `w:gz`,
  göreli adlarla); yanına `<arşiv>.sha256` — içerik `"<hex>  <arşiv adı>\n"` (`sha256sum -c` biçimi). İkisi de
  `0o600`. `cikti_dizini` `kok`'un içindeyse ya da aynı adlı arşiv varsa `TasimaHatasi`.
- `main(argv, kok=None, ortam=None) -> int` — `--paketle [--cikti DIZIN] [--kuru]` (varsayılan çıktı
  `Path.home()` *(plan kararı)*); `--ac` Task 5'te. `0` tamam · `1` reddedildi · `2` kullanım hatası (iki kip
  birden, hiçbiri, bilinmeyen bayrak). `--kuru` yokken `ortam.get("CLAUDECODE")` doluysa
  `durdu — ajan ortamında taşıma kapalı; yalnız --kuru.` + `1` *(plan kararı: `rapor_postasi.py` deseni)*.
  `--kuru`: engelleri ve özeti basar, arşiv yazmaz, kilit almaz, çıkış `0`.

Çıktı (dosya adı ve içerik yok; yalnız üst klasör başına adet) *(plan kararı)*:

```
taşıma paketi — 2026-11-24 08:40
  ENGEL açık soru var: 1 (20261124-0835-abcd)
  yanitlar/        212 dosya
  sirket-log/      640 dosya
  → 975 dosya · arşiv: <yol> · sha256: <hex>
  .env paketlenmedi (S-2): sunucuda yazılımcı yazar.
```

- [ ] **Step 1: Failing tests.** Yardımcı `kur(kok)` şunları yazar: `yanitlar/s1.md`; `sirket-log/sorular/s1.md`
  (başlıkta `- durum: iletildi`; biçim `tests/test_panel_defter.py` kurulumundan), `sirket-log/dagitici.log`,
  `sirket-log/posta/.kilit`, `sirket-log/.env.yedek`; `deploy/{roller,kullanicilar,posta-alicilari}.json`,
  `deploy/roller.json.example`; `formlar/onayli/kalite.md`, `formlar/gelen/x.md`;
  `takimlar/kalite/{defter.md,durum.json,kurallar.md,takim.md,kosu/k.md,cikti/c.md,veri/v.csv}`,
  `takimlar/_iskelet/defter.md`, `takimlar/bekci-telemetri.jsonl`; `.env` (`ANTHROPIC_API_KEY=sk-ant-GIZLI-4711`);
  `.DS_Store`. `BOS = lambda kok: []` (Mac denetimi kapalı). `uyeler(arsiv)` = tar üye adları kümesi.
  - `test_izinli_mi`: doğru — `yanitlar/a.md`, `sirket-log/sorular/a.md`, `deploy/roller.json`,
    `takimlar/kalite/kosu/k.md`, `takimlar/bekci-telemetri.jsonl`; yanlış — `.env`, `sirket-log/.env.yedek`,
    `yanitlar/../.env`, `/etc/passwd`, `deploy/roller.json.example`, `deploy/x.json`, `takimlar/kalite/kurallar.md`,
    `takimlar/kalite/veri/v.csv`, `takimlar/_iskelet/defter.md`, `formlar/gelen/x.md`, `bin/ayar.py`,
    `sirket-log/posta/.kilit`, `yanitlar/.DS_Store`, `""`
  - `test_paketler_s1_listesini`: `uyeler` tam olarak `kur`'daki izinli on iki dosya (liste testte açık yazılır)
  - `test_env_asla_paketlenmez` (S-2): üye adlarının hiçbir parçası `.env` ile başlamaz; arşivin ham baytlarını
    açıp bütün üye içeriklerinde `GIZLI-4711` yok
  - `test_saglama_toplami`: `.sha256` içeriği `hashlib.sha256(arşiv baytları).hexdigest() + "  " + arşiv.name + "\n"`;
    dönüşteki `sha256` aynı; iki dosyanın izni `0o600`
  - `test_acik_soru_varsa_reddeder`: `sirket-log/sorular/s2.md` (`- durum: alindi`, defterde yok) →
    `engeller` bir öğe, `"açık soru var: 1"` ve `s2` içerir; `arsiv is None`; çıktı dizininde dosya yok; `main` `1`
  - `test_kilit_doluysa_reddeder`: test `.kos.lock`'u açıp `flock(LOCK_EX)` ile tutar → `main` `1`, çıktı
    `koşu kilidi dolu` içerir, arşiv yok; bırakınca paketler
  - `test_paketlerken_kilidi_tutar` (Review Focus 5): `mock.patch.object(tasima.tarfile, "open", side_effect=…)`
    içinde `ayar.kosu_suruyor(kok)` çağrılır → `True`; paketleme bitince `False`
  - `test_mac_servisleri_acikken_reddeder` (Review Focus 5): `mac_denetimi=lambda k: ["zamanlayıcı kurulu — önce:
    python3 bin/zamanla.py --kaldir"]` → arşiv yok, neden çıktıda; varsayılan denetim için
    `mock.patch.object(tasima.zamanla, "durum", return_value=[{"ad": "rapor", "yuklu": True}])` +
    `mock.patch.object(tasima.sys, "platform", "darwin")` + soket bağlantısı `OSError` → tek engel, `--kaldir` içerir;
    `platform == "linux"` → `zamanla.durum` çağrılmaz
  - `test_sembolik_bag_atlanir`: `yanitlar/bag.md` → `kok/.env`'e sembolik bağ → üyelerde yok
  - `test_cikti_depo_icinde_olamaz`: `cikti_dizini=kok / "sirket-log"` → `TasimaHatasi`; `main` `1`
  - `test_ayni_adli_arsiv_ezilmez`: aynı `simdi` ile iki kez → ikincisi `1`, ilk arşivin baytları aynı
  - `test_kuru_yazmaz`: `--kuru` (`CLAUDECODE=1`) → `0`; çıktı dizini boş; çıktıda `→ 12 dosya` ve
    `yanitlar/` satırı; engel varken de `0` ve `ENGEL` satırı
  - `test_ajan_ortaminda_yazan_kosu_durur`: `main(["--paketle", "--cikti", d], kok, ortam={"CLAUDECODE": "1"})` →
    `1`, `yalnız --kuru`, arşiv yok
  - `test_cikti_deger_ve_dosya_adi_tasimaz`: stdout'ta `GIZLI`, `example.com`, `kalite.md`, `s1.md` yok
  - `test_kullanim_hatasi`: `main([])`, `main(["--paketle", "--ac", "x"])`, `main(["--x"])` → `2`
- [ ] **Step 2:** Run `python3 -m unittest tests.test_tasima -v` → FAIL (`ModuleNotFoundError`)
- [ ] **Step 3:** Yaz. Modül başlığı: S-1 kuralları (sıra: zamanlayıcı kaldır → panel durdur → açık soru yok →
  paketle), "`.env` paketlenmez (S-2)", kullanım satırları.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK; `python3 bin/tasima.py --paketle --kuru` (ajan ortamı, gerçek
  kök) → çıkış `0`, çıktıda dosya adı ve değer yok
- [ ] **Step 5:** `git commit -m "feat(deploy): tasima.py --paketle — S-1 durumu tek arşiv ve sağlama toplamıyla"`

### Task 5: `bin/tasima.py --ac` (sunucu)

**Files:** Modify `bin/tasima.py`, `tests/test_tasima.py`

**Interfaces — Consumes:** `izinli_mi`, `kos_kilidi`, `engeller`, `TasimaHatasi`, `paketle` (Task 4). **Produces:**
- `ac(kok, arsiv, ustune_yaz=False, kuru=False, simdi=None, euid=None) -> dict` —
  `{"engeller": [str], "yazilan": int, "ayni": int, "catisan": [goreli], "yedek": Path | None}`
- `main`: `--ac ARSIV [--ustune-yaz] [--kuru]`; çıkış kodları Task 4 ile aynı; çatışma reddi `1`.

Akış (sıra bağlayıcı; **doğrulama bitmeden tek bayt yazılmaz**):

1. `<arşiv>.sha256` okunur; dosya yoksa ya da özet uyuşmuyorsa `TasimaHatasi("sağlama toplamı …")`.
2. `euid == 0` → `TasimaHatasi("root olarak açılmaz — konteyner kullanıcısıyla koştur")` *(plan kararı: betik
   `chown` yapmaz; sahiplik, açan kullanıcı konteyner kullanıcısı olduğu için doğru çıkar)*.
3. `engeller(kok)` (hedefte açık soru) boş değilse dur; `kos_kilidi(kok)` alınır (kuru koşuda alınmaz).
4. Bütün üyeler: yalnız düzenli dosya ya da dizin (`isreg()`/`isdir()`); dosya adları `izinli_mi` geçer. Tek bir
   ihlal → `TasimaHatasi("arşivde beklenmeyen yol: <n>")`. `tarfile.extractall` **kullanılmaz**; içerik
   `extractfile` ile okunur.
5. Sınıflama: hedefte yok → yazılacak · var ve sha256 aynı → `ayni` (dokunulmaz) · var ve farklı → `catisan`.
6. `catisan` doluysa ve `ustune_yaz` değilse: **hiçbir dosya yazılmaz**, çıkış `1`, çıktıda üst klasör başına
   çatışma sayısı ve `--ustune-yaz` ipucu *(plan kararı: sessiz ezme yok; tekrar koşu aynı içerikte zararsız)*.
7. `ustune_yaz`: çatışan her hedef önce `sirket-log/tasima-yedek/<YYYYMMDD-HHMMSS>/<goreli>`'ye kopyalanır,
   sonra yazılır *(plan kararı: Mac geçiş gününde doğrunun kaynağıdır; eski hâl kaybolmaz)*.
8. Yazım: geçici dosya + `os.replace`; dosya `0o600`, yeni dizin `0o700` *(plan kararı: tar'daki izin/sahip
   yok sayılır; tek kullanıcı okur)*.

`kuru`: 1, 2, 4, 5 koşar; sayıları basar, yazmaz.

- [ ] **Step 1: Failing tests.** Yardımcı `arsivle(kaynak_kok)` = Task 4 `paketle` ile arşiv; `elle_arsiv(uyeler)` =
  `tarfile` ile serbest üyeli arşiv + geçerli `.sha256` (düşmanca durumlar için). Hedef `kok` boş klasör
  (`sirket-log/` yok). `euid` testlerde `1000` verilir.
  - `test_gidis_donus`: `kur(a)` → `arsivle(a)` → `ac(b, arsiv)` → `tasima.dosyalar(b) == tasima.dosyalar(a)`,
    her dosyanın baytı aynı; `yazilan == 12`; `deploy/kullanicilar.json` izni `0o600`; `b/.env` **yok**
  - `test_saglama_toplami_tutmazsa_reddeder` (Review Focus 3): arşive bir bayt eklenir → `TasimaHatasi`, `b` boş;
    `.sha256` silinir → `TasimaHatasi`, `b` boş
  - `test_dusmanca_arsiv_tamamen_reddedilir` (Review Focus 3): ayrı ayrı — `../disari.md` · `/tmp/x.md` ·
    `.env` · `yanitlar/.env` · `bin/ayar.py` · `takimlar/kalite/kurallar.md` · sembolik bağ üyesi
    (`yanitlar/bag.md` → `/etc/passwd`) · sabit bağ üyesi. Her birinde arşivde ayrıca geçerli `yanitlar/iyi.md`
    vardır → `TasimaHatasi`; `b/yanitlar/iyi.md` **yok** (hiçbir şey yazılmadı); hedef kökün dışında dosya oluşmadı
  - `test_ikinci_kosu_zararsiz` (Review Focus 1): `ac` iki kez → ikincide `yazilan == 0`, `ayni == 12`,
    `catisan == []`, çıkış `0`; dosyaların `st_mtime`'ı değişmedi
  - `test_catisma_varsa_hicbir_sey_yazmaz` (Review Focus 1): hedefte önceden `sirket-log/dagitici.log` (farklı
    içerik) → `catisan == ["sirket-log/dagitici.log"]`, `main` `1`; `b/yanitlar/` **yok**; log içeriği eskisi
  - `test_ustune_yaz_yedekler`: aynı kurulum + `ustune_yaz=True`, `simdi` sabit → log yeni içerik;
    `sirket-log/tasima-yedek/20261124-084000/sirket-log/dagitici.log` eski içerik; `yedek` o klasör; `yazilan == 12`
  - `test_hedefte_acik_soru_varsa_reddeder`: `b/sirket-log/sorular/s9.md` (`- durum: alindi`) → `main` `1`, yazım yok
  - `test_hedef_kilit_doluysa_reddeder`: `b/.kos.lock` tutulur → `1`, yazım yok
  - `test_root_reddedilir`: `euid=0` → `TasimaHatasi`, iletide `root`
  - `test_kuru_yazmaz`: `--ac <arşiv> --kuru` (`CLAUDECODE=1`) → `0`, çıktıda `12`; `b` boş
  - `test_ajan_ortaminda_yazan_ac_durur`: `CLAUDECODE=1`, `--kuru` yok → `1`, `yalnız --kuru`
  - `test_cikti_dosya_adi_tasimaz`: çatışma reddinde stdout üst klasör adı ve sayı içerir; `example.com` yok
- [ ] **Step 2:** Run `python3 -m unittest tests.test_tasima -v` → yeni testler FAIL (`AttributeError: ac`)
- [ ] **Step 3:** Yaz (yukarıdaki sıra).
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(deploy): tasima.py --ac — doğrulamadan yazmaz, sessizce ezmez"`

### Task 6: Docker paketi, statik testler ve `zamanla.py`'nin Linux reddi

**Files:** Create `deploy/docker/Dockerfile`, `deploy/docker/compose.yaml`, `deploy/docker/crontab`,
`.dockerignore`, `deploy/Caddyfile.example`, `tests/test_deploy_statik.py` · Modify `bin/zamanla.py` (`main` 238,
modül başlığı), `tests/test_zamanla_sahne.py`, `tests/test_temiz_kurulum.py:130`

**Interfaces — Produces:** compose değişkenleri (Task 7 belgeler, Task 8 kullanır): `NOVE_KOK` (varsayılan
`/srv/nove-kurul`), `NOVE_UID`/`NOVE_GID` (varsayılan `1000`), `NOVE_PORT` (varsayılan `8770`); servis adları
`panel`, `zamanlayici`; imaj `nove-kurul:yerel`; volume `claude-ev`.

**`zamanla.main`:** ilk satırda `sys.platform != "darwin"` ise stderr'e
`zamanla: yalnız macOS (launchd). Sunucuda zamanlayıcı Docker'dadır: deploy/docker/compose.yaml (deploy/KURULUM.md)`
ve çıkış `2`; `--kuru` dahil hiçbir kip koşmaz *(plan kararı: çıkış kodu)*.

**`deploy/docker/Dockerfile`** — kurallar (katman düzeni Builder'ın; şunlar bağlayıcı):
- `ARG PYTHON_SURUM=3.12.8` → `FROM python:${PYTHON_SURUM}-slim-bookworm`; Node ikinci aşamadan kopyalanır:
  `ARG NODE_SURUM=22.12.0` → `FROM node:${NODE_SURUM}-bookworm-slim AS node`, `COPY --from=node` ile
  `/usr/local/bin/node` ve `/usr/local/lib/node_modules` (+ `npm` bağı).
- `ARG CLAUDE_CODE_SURUM=<Step 3'te>` → `npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_SURUM}`;
  `ARG PSYCOPG_SURUM=3.2.13` (Mac'te kurulu sürüm) → `pip install --no-cache-dir "psycopg[binary]==${PSYCOPG_SURUM}"`;
  `ARG SUPERCRONIC_SURUM=0.2.33` + `ARG SUPERCRONIC_SHA1_AMD64` / `…_ARM64` → `supercronic-linux-${TARGETARCH}`
  indirilir, `sha1sum -c` ile doğrulanır (sunucu büyük olasılıkla amd64, Mac arm64 — ikisi de derlenir).
- Her sürüm tam sürümdür: `latest`, `^`, `~`, aralık yok. `apt` paketleri (`tzdata`, `git`, `ca-certificates`,
  `curl`) sürümünü sabit taban imaj etiketinden alır *(plan kararı: `paket=sürüm` Debian deposu döndükçe kırılır)*.
  Verilen sürüm etiketi kayıt defterinde yoksa Builder en yakın var olan **tam** sürüme sabitler; kural değişmez.
- `ENV TZ=Europe/Istanbul DISABLE_AUTOUPDATER=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1`
- `ARG UID=1000`, `ARG GID=1000`; grup yalnız yoksa açılır
  (`getent group ${GID} || groupadd -g ${GID} nove-ajan` — Mac'te gid 20 Debian'da doludur);
  `useradd -u ${UID} -g ${GID} -m -d /home/nove-ajan nove-ajan`; `/home/nove-ajan/.claude` ve `/srv/nove-kurul`
  oluşturulup kullanıcıya verilir (adlandırılmış volume sahipliği imajdaki dizinden gelir).
- Son satırlar `USER nove-ajan`, `WORKDIR /srv/nove-kurul`. **Depodan `COPY`/`ADD` yok** (yalnız `COPY --from=node`).

**`deploy/docker/compose.yaml`** *(plan kararları: `NOVE_*` değişkenleri — duman testi başka klasör/port/uid ister;
`init: true` — panel PID 1'ken `start_new_session` alt süreçleri zombi kalmasın; log döndürme)*:

```yaml
name: nove-kurul
x-ortak: &ortak
  image: nove-kurul:yerel
  working_dir: /srv/nove-kurul
  volumes:
    - "${NOVE_KOK:-/srv/nove-kurul}:/srv/nove-kurul"
    - claude-ev:/home/nove-ajan/.claude
  restart: unless-stopped
  init: true
  logging: {driver: json-file, options: {max-size: "10m", max-file: "5"}}
services:
  panel:
    <<: *ortak
    build:
      context: ../..
      dockerfile: deploy/docker/Dockerfile
      args: {UID: "${NOVE_UID:-1000}", GID: "${NOVE_GID:-1000}"}
    command: ["python3", "bin/panel.py", "--adres", "0.0.0.0", "--https-arkasinda"]
    ports: ["127.0.0.1:${NOVE_PORT:-8770}:8770"]
  zamanlayici:
    <<: *ortak
    command: ["supercronic", "deploy/docker/crontab"]
volumes:
  claude-ev:
```

Dosyanın başında yorum: sırlar `.env`'den, servisler kendisi okur; veritabanı ağı için yorum satırı hâlinde
`networks:` (dış ağ) örneği — yazılımcı açar (spec "Yazılımcıya bırakılan"). Dosyada `env_file` sözcüğü yorumda
bile geçmez (statik test).

**`deploy/docker/crontab`:** yorum satırı + tam olarak Global Constraints'teki dört satır, komutlar
`python3 bin/gunluk.py --<bayrak>`.

**`.dockerignore`** (depo kökü): `.git`, `.env`, `.env.*`, `yanitlar/`, `sirket-log/`, `deploy/*.json`, `formlar/`,
`kasa/`, `gelen/`, `takimlar/*/kosu/`, `takimlar/*/cikti/`, `takimlar/*/gelen/`, `takimlar/*/veri/`,
`takimlar/*/defter.md`, `takimlar/*/durum.json`, `**/*.jsonl`.

**`deploy/Caddyfile.example`:** `panel.example.com { @disaridan not remote_ip <şirket ağı/VPN aralığı>;
respond @disaridan 403; reverse_proxy 127.0.0.1:8770 }` — aralık örneği `10.0.0.0/8`, TLS için yorum (`tls internal`
ya da şirket sertifikası), "Caddy `X-Forwarded-For`'u kendisi yazar" notu.

- [ ] **Step 1: Failing tests.** `tests/test_deploy_statik.py` (dosyalar metin olarak okunur; YAML ayrıştırıcı yok):
  - `ComposeTesti.test_port_yalniz_loopback`: `ports` satırındaki her değer `127.0.0.1:` ile başlar;
    `"127.0.0.1:${NOVE_PORT:-8770}:8770"` var; `0.0.0.0:` yalnız `--adres` komutunda geçer (port satırında yok)
  - `test_env_file_yok_ve_sir_yok`: `"env_file"` not in metin; `ANTHROPIC`, `_API_KEY`, `READONLY_URL`, `POSTA_` yok
  - `test_iki_servis_ayni_baglama`: `panel:` ve `zamanlayici:` var; `<<: *ortak` iki kez;
    `${NOVE_KOK:-/srv/nove-kurul}:/srv/nove-kurul`, `working_dir: /srv/nove-kurul`, `restart: unless-stopped`,
    `claude-ev:/home/nove-ajan/.claude`
  - `test_komutlar`: `"bin/panel.py", "--adres", "0.0.0.0", "--https-arkasinda"`; `"supercronic", "deploy/docker/crontab"`
  - `CrontabTesti.test_dort_satir`: yorum ve boş satırlar atılınca liste tam olarak
    `["0 8 * * * python3 bin/gunluk.py --sabah", "30 9 * * 1-5 python3 bin/gunluk.py --rapor",
    "*/10 * * * * python3 bin/gunluk.py --ilerlet", "0 19 * * * python3 bin/gunluk.py --aksam"]`
  - `test_saatler_ayarla_ayni` (ANAYASA §4): `8 == ayar.MESAI_BASLANGIC`, `19 == ayar.MESAI_BITIS - 1`; rapor satırı
    `zamanla.RAPOR_ISLERI`'ndeki `saat`/`dakika`/`gunler` (`9`, `30`, `[1..5]`) ve `aralik_sn == 600` ile tutarlı
  - `DockerfileTesti.test_saat_dilimi_ve_kullanici`: `TZ=Europe/Istanbul` var; son `USER` satırı `nove-ajan`
    (`root` ya da `0` değil)
  - `test_kodu_kopyalamaz`: `ADD ` ile başlayan satır yok; `COPY ` ile başlayan her satır `COPY --from=`
  - `test_surumler_sabit`: `PYTHON_SURUM`, `NODE_SURUM`, `CLAUDE_CODE_SURUM`, `PSYCOPG_SURUM`, `SUPERCRONIC_SURUM`
    `ARG`'larının her biri `^\d+\.\d+\.\d+$`; `PYTHON_SURUM` `3.12.` ile, `NODE_SURUM` `22.` ile başlar;
    iki `SUPERCRONIC_SHA1_*` kırk onaltılık hane; metinde `latest` yok; `psycopg[binary]==`, `claude-code@$` var
  - `test_uid_gid_ve_ev`: `ARG UID`, `ARG GID`, `getent group`, `/home/nove-ajan/.claude`, `DISABLE_AUTOUPDATER=1`
  - `DockerignoreTesti.test_sir_ve_kisisel_veri`: satır kümesi `.env`, `.env.*`, `yanitlar/`, `sirket-log/`,
    `deploy/*.json`, `formlar/`, `kasa/`, `takimlar/*/kosu/`, `takimlar/*/cikti/`, `takimlar/*/gelen/`,
    `takimlar/*/veri/`, `takimlar/*/defter.md`, `takimlar/*/durum.json` öğelerini içerir
  - `CaddyTesti.test_ornek`: `reverse_proxy 127.0.0.1:8770`, `remote_ip`, `panel.example.com` var; `nove.group` yok
  - `tests/test_zamanla_sahne.py` `LinuxReddiTesti.test_linuxta_reddeder`: `mock.patch.object(zamanla.sys,
    "platform", "linux")` ile `main(["--kur"])`, `main(["--kuru"])`, `main(["--durum"])` → hepsi `2`; stderr
    `deploy/docker/compose.yaml` içerir; `mock.patch.object(zamanla, "kur")` çağrılmadı.
    `test_macte_calisir`: `platform="darwin"` → `main(["--kuru"]) == 0`
  - Var olan `zamanla.main` çağıran testler (`test_zamanla_sahne.py::test_kuru_metni_yeni_isleri_basar`,
    `test_temiz_kurulum.py:130`) `mock.patch.object(zamanla.sys, "platform", "darwin")` alır (takım Linux
    konteynerinde de geçsin).
- [ ] **Step 2:** Run `python3 -m unittest tests.test_deploy_statik tests.test_zamanla_sahne -v` → FAIL
  (`FileNotFoundError`, reddi testi `0 != 2`)
- [ ] **Step 3:** Sürümleri sabitle, dosyaları yaz. `CLAUDE_CODE_SURUM`: Mac'te `claude --version` çıktısındaki
  sürüm *(plan kararı: sunucu, Mac'te denenmiş sürümle aynı davransın)*; komut yoksa
  `npm view @anthropic-ai/claude-code version`. Supercronic SHA1'leri sürümün GitHub yayın sayfasındaki
  `supercronic-linux-amd64` / `-arm64` değerleri. `zamanla.py` modül başlığına "sunucuda Docker" notu.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK
- [ ] **Step 5:** `git commit -m "feat(deploy): Docker Compose paketi, statik testler; zamanla.py Linux'ta reddeder"`

### Task 7: `deploy/KURULUM.md` ve belge güncellemeleri

**Files:** Create `deploy/KURULUM.md` · Modify `NOVE-KURULUM.md` (§8 285-320, Faz 0 405-418, Faz 5 "Caddy +
systemd" satırı), `CLAUDE.md` (klasör yapısı), `README.md:45`, `tests/test_deploy_statik.py`

**Interfaces — Consumes:** Task 1–6'nın bayrakları, dosya adları, compose değişkenleri.

`deploy/KURULUM.md` bölümleri (dil ve sıra Builder'ın; içerik bağlayıcı):
1. **Ne kuruluyor** — iki servis, tek klasör, veritabanı yok (durum dosyada).
2. **Önkoşullar** — Docker + Compose; dışarı çıkış (Anthropic; isteğe bağlı NVIDIA/OpenAI, SMTP); ters vekil.
3. **Sizden iki karar** (spec "Yazılımcıya bırakılan", soru olarak): Kalite/PYS veritabanına konteynerden hangi
   adresle ulaşılır (ortak dış ağ + servis adı ya da makine adı/IP; `localhost` çalışmaz) · depo, `.env` ve durum
   hangi makine kullanıcısına ait (imaj o uid/gid ile derlenir; `git pull` yalnız o kullanıcıyla).
4. **Adımlar** — `git clone` → `/srv/nove-kurul`; `.env` yaz (`chmod 600`); derle:
   `NOVE_UID=$(id -u) NOVE_GID=$(id -g) docker compose -f deploy/docker/compose.yaml build`; `up -d`; doğrula:
   `docker compose -f deploy/docker/compose.yaml exec panel python3 bin/sunucu_kontrol.py --db --tasima-oncesi`;
   ters vekil (`deploy/Caddyfile.example`; başka vekilde `X-Forwarded-For`'a gerçek istemci IP'si **eklenmeli**,
   port `127.0.0.1:8770`).
5. **`.env` anahtarları** — tablo: ad · ne işe yarar · nereden alınır. **Değer yok, `AD=değer` satırı yok.**
   Zorunlu: `ANTHROPIC_API_KEY` (Nove Console; kişisel abonelik/`claude login` kullanılmaz), `QA_READONLY_URL`,
   `OKR_READONLY_URL`. Önerilen: `NVIDIA_API_KEY` ya da `OPENAI_API_KEY` (yoksa Denetçi aynı aileye düşer).
   İsteğe bağlı: `POSTA_SMTP_SUNUCU`, `POSTA_SMTP_PORT`, `POSTA_KULLANICI`, `POSTA_SIFRE`, `POSTA_GONDEREN`,
   `PANEL_ADRES`. Değerler Kağan'dan güvenli kanalla gelir (parola yöneticisi ya da yüz yüze; mail/sohbet değil);
   Mac'teki `.env` kopyalanmaz (S-2). `.env` değişince `docker compose restart` gerekir.
6. **Geçiş günü** — spec'in beş adımı, komutlarıyla: `sunucu_kontrol.py --tasima-oncesi` temiz · Mac'te
   `zamanla.py --kaldir` + panel durdur · Mac'te `tasima.py --paketle`, arşiv + `.sha256` sunucuya ·
   `docker compose stop` → `docker compose run --rm -v <arşiv klasörü>:/tasima:ro panel python3 bin/tasima.py
   --ac /tasima/<arşiv>` → `up -d` → `sunucu_kontrol.py --db` (bayraksız temiz) · kullanıcı ekleme
   (`exec -it panel python3 bin/panel.py --kullanici-ekle <eposta>`) · `PANEL_ADRES`. 09:30 notu (S-1).
   Çatışma reddi ve `--ustune-yaz` (yedek `sirket-log/tasima-yedek/`).
7. **Yedek** — spec listesi birebir: `yanitlar/`, `sirket-log/`, `deploy/*.json`, `formlar/onayli/`,
   `takimlar/*/{defter.md,durum.json,kosu,cikti}`, `.env` (+ `takimlar/bekci-telemetri.jsonl`).
8. **Güncelleme** — `git pull` → `docker compose restart`; imaj yalnız Dockerfile değişince; açık soru yokken.
9. **Sorun giderme** — `sunucu_kontrol.py` satır satır ne der; `docker compose logs`; kaçan zamanlı iş elle
   (`exec zamanlayici python3 bin/gunluk.py --rapor`); herkes `429` alıyorsa vekil `X-Forwarded-For` yazmıyor;
   ilk gerçek `claude -p` koşusu Kağan onayıyla yapılır.

`NOVE-KURULUM.md`: §8 şeması Docker'a çevrilir (Tarayıcı → ters vekil → `panel` servisi `127.0.0.1:8770`;
`zamanlayici` servisi dört iş; `soru_kapisi --dinle` yerine panelin ilerleticisi); "systemd timer", "`nove-ajan`
Linux kullanıcısı" maddeleri compose/imaj karşılığıyla değişir; ayrıntı için `deploy/KURULUM.md`'ye bağ. Faz 0 kod
bloğu `adduser/apt/npm` yerine `deploy/KURULUM.md` adımlarını gösterir (onay kutuları kalır). Faz 5'te
"Caddy + systemd birimleri" → "Docker Compose paketi + Caddyfile örneği (`deploy/`)", işaretli, tarihli.
`CLAUDE.md` klasör yapısına satır: `deploy/               KURULUM.md · docker/ (Dockerfile, compose.yaml, crontab) ·
Caddyfile.example · roller/kullanicilar/posta-alicilari.json (git'e girmez)`; `bin/` satırına `sunucu_kontrol.py ·
tasima.py`. `README.md:45` "systemd timer" → "Docker (`deploy/docker/`, supercronic)".

- [ ] **Step 1: Failing tests** (`tests/test_deploy_statik.py`, `class BelgeTesti`):
  - `test_kurulum_anahtar_adlari`: `deploy/KURULUM.md` on bir adı içerir (`ANTHROPIC_API_KEY`, `QA_READONLY_URL`,
    `OKR_READONLY_URL`, `NVIDIA_API_KEY`, `OPENAI_API_KEY` + `rapor_postasi.GEREKLI_ANAHTARLAR`'ın altısı)
  - `test_kurulum_deger_tasimaz`: `re.search(r"^\s*[A-Z][A-Z0-9_]{2,}=\S", metin, re.M) is None`; `sk-ant`,
    `postgresql://`, `@nove.group` yok
  - `test_kurulum_yedek_listesi`: `yanitlar/`, `sirket-log/`, `deploy/*.json`, `formlar/onayli/`, `defter.md`,
    `durum.json`, `kosu`, `cikti`, `.env` geçer
  - `test_kurulum_komutlari`: `sunucu_kontrol.py`, `--tasima-oncesi`, `tasima.py --paketle`, `tasima.py --ac`
    (aralarındaki boşluk/satır kırığına dayanıklı desenle), `zamanla.py --kaldir`, `--kullanici-ekle`,
    `NOVE_UID`, `docker compose restart`, `X-Forwarded-For`, `claude login` geçer
  - `test_ana_belgeler_dockeri_anlatir`: `NOVE-KURULUM.md`'de `deploy/KURULUM.md` ve `zamanlayici` var,
    `nove-dinleyici.service` ve `nove-sabah.timer` yok; `CLAUDE.md`'de `deploy/` satırı `KURULUM.md` içerir;
    `README.md`'de `systemd timer` yok
- [ ] **Step 2:** Run `python3 -m unittest tests.test_deploy_statik -v` → `BelgeTesti` FAIL
- [ ] **Step 3:** Yaz. `LICENSE` ve `ANAYASA.md`'ye dokunulmaz.
- [ ] **Step 4:** Run aynı komut → OK; tam takım OK, `skipped=9`
- [ ] **Step 5:** `git commit -m "docs(deploy): KURULUM.md; NOVE-KURULUM §8 ve Faz 0 Docker'a çevrildi"`

### Task 8: Duman testi — Mac'te Docker (ajan koşturur)

**Files:** Modify bu plan dosyası ("Uygulama" bölümüne sonuç); bulgu çıkarsa ilgili Task 6 dosyası + statik testi

**Interfaces — Consumes:** `NOVE_KOK`, `NOVE_UID`, `NOVE_GID`, `NOVE_PORT`; `sunucu_kontrol.py`.

Kurallar: gerçek depo klasörü ve gerçek `.env` konteynere **bağlanmaz**; `claude -p` koşmaz; Kağan'ın 8770'teki
servisine ve launchd işlerine dokunulmaz; `zamanlayici` servisi `up` edilmez (yalnız crontab doğrulanır).
`C="docker compose -p nove-duman -f $D/deploy/docker/compose.yaml"`; ortam her komutta
`NOVE_KOK=$D NOVE_UID=$(id -u) NOVE_GID=$(id -g) NOVE_PORT=18770`.

- [ ] **Step 1: Kurgusal kök.** `D=$(mktemp -d /tmp/nove-duman.XXXXXX)`; `git archive HEAD | tar -x -C "$D"`
  (yalnız git'teki dosyalar: `.env` ve kişisel veri gelmez). `$D/.env` kurgusal değerlerle yazılır
  (`ANTHROPIC_API_KEY=sk-ant-sahte-duman`, `QA_READONLY_URL=postgresql://okuyucu:sahte@db.invalid:5432/qa`,
  `OKR_READONLY_URL=postgresql://okuyucu:sahte@db.invalid:5432/pys`), `chmod 600`;
  `$D/deploy/roller.json` = `{"uye@example.com": "kurul"}`, `$D/deploy/kullanicilar.json` = `{}`.
  Beklenen: `ls -la "$D/.env"` → `-rw-------`.
- [ ] **Step 2: Derle.** `$C build` → çıkış `0`. Etiket bulunamadı / sağlama toplamı tutmadı hatasında Dockerfile'da
  sürüm düzeltilir (kural: tam sürüm), `tests.test_deploy_statik` yeşil kalır, `fix(deploy): …` commit'i,
  Step 1 yeniden.
- [ ] **Step 3: Kullanıcı ve saat.** `$C run --rm panel id -u` → `$(id -u)` ile aynı, `0` değil;
  `$C run --rm panel date +%z` → `+0300`; `$C run --rm panel sh -c 'test -w /home/nove-ajan/.claude && echo tamam'`
  → `tamam`.
- [ ] **Step 4: Claude Code.** `$C run --rm panel claude --version` → çıkış `0`, sürüm `CLAUDE_CODE_SURUM` ile aynı.
- [ ] **Step 5: Kurulum doğrulaması.** `$C run --rm panel python3 bin/sunucu_kontrol.py` → çıkış `0`;
  `env-dosyasi`, `zorunlu-anahtarlar`, `claude`, `saat-dilimi`, `depo-yazilabilir`, `sahiplik`, `roller`,
  `kullanicilar` `TAMAM`; `denetci` `UYARI`; çıktıda `sahte` ve `db.invalid` yok. `--db` ile → çıkış `1`,
  `db-kalite` `HATA`, çıktıda yine değer yok.
- [ ] **Step 6: Panel.** `$C up -d panel`; `curl -fsS http://127.0.0.1:18770/ | grep -c "Nove AI"` → `≥ 1`;
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18770/api/ben` → `401`;
  `$C port panel 8770` → `127.0.0.1:18770`; `$C logs panel` → `http://0.0.0.0:8770` ve
  `yalnız konteyner içinde` uyarısı.
- [ ] **Step 7: Crontab.** `$C run --rm zamanlayici supercronic -test deploy/docker/crontab` → çıkış `0`.
- [ ] **Step 8: Takım konteynerde (bilgi).** `$C run --rm panel python3 -m unittest discover -s tests` — sonuç
  (sayı, hata adları) plana yazılır. Bu planın dokunduğu modüllerdeki hata düzeltilir; diğer Linux/3.12 hataları
  "Sonraya kalan" listesine girer, bu planda düzeltilmez.
- [ ] **Step 9: Temizlik.** `$C down -v --rmi local`; `rm -rf "$D"`. Beklenen: `docker ps -a --filter
  name=nove-duman` boş; Mac'te 8770'teki servis yerinde.
- [ ] **Step 10:** Sonuçlar bu plandaki "Uygulama" bölümüne yazılır;
  `git commit -m "docs(plan): sunucu docker — duman testi sonucu"`

---

## Uygulama

### Task 8 — duman testi (Mac, Docker 29.9.3, 23.11.2026)

Kurgusal kök: `git archive HEAD` → `mktemp -d /tmp/nove-duman.*`; kurgusal `.env` (izin `-rw-------`), `roller.json`
(`uye@example.com`: kurul), `kullanicilar.json` (`{}`). Proje `nove-duman`, port 18770. Dockerfile'da düzeltme gerekmedi.

| Adım | Sonuç |
|---|---|
| 2 `build` | çıkış 0; imaj `nove-kurul:yerel` |
| 3 kullanıcı/saat | `id -u` = 501 (host ile aynı, root değil); `date +%z` = `+0300`; `.claude` yazılabilir (`tamam`) |
| 4 `claude --version` | çıkış 0; `2.1.330 (Claude Code)` = `CLAUDE_CODE_SURUM` |
| 5 `sunucu_kontrol.py` | çıkış 0; sekiz madde TAMAM, `denetci` UYARI, `posta-anahtarlari` BİLGİ; çıktıda `sahte`/`db.invalid` yok (0). `--db`: çıkış 1, `db-kalite` ve `db-okr` HATA (`OperationalError`), çıktıda değer yok |
| 6 panel | `up -d panel`; `/` içinde "Nove AI" 2 eşleşme; `/api/ben` 401; `port panel 8770` = `127.0.0.1:18770`; günlükte `http://0.0.0.0:8770` ve "yalnız konteyner içinde" uyarısı |
| 7 crontab | `supercronic -test deploy/docker/crontab` çıkış 0, "crontab is valid" |
| 8 takım konteynerde | `Ran 1078 tests`, `FAILED (failures=4, skipped=8)` (ana makinede skipped=9: fark `test_scrypt_varsa_kullanilir`; Mac'teki Python'da scrypt yok, konteynerde var ve koşuyor; ana makine atlama nedenleri çıktıdan doğrulandı) |
| 9 temizlik | `down -v --rmi local` çıkış 0; kapsayıcı, imaj, birim, ağ kalmadı; geçici klasör silindi; 8770'teki servis yerinde |

**X-Forwarded-For denetimi (Task 2, gerçek Docker ağı üzerinden).** Panel `--https-arkasinda` ile; bağlantı IP'si
Docker geçidi (172.19.0.1). Yanlış parolayla POST `/api/giris`, sırasıyla olan:
1. İlk koşu (kısa brief sırası): `203.0.113.7` + `uye@example.com` x5 → 401 x5; `203.0.113.8` + aynı e-posta → 429;
   `203.0.113.7` + aynı e-posta → 429. Sonuç karışık: 429'un nedeni IP mi e-posta mı ayırt edilemedi.
2. `docker compose restart panel` ile bellekteki sayaçlar sıfırlandı (fren yalnız bellekte).
3. Yeniden başlatmadan sonra dizi baştan koşuldu: `203.0.113.7` + `uye@example.com` x5 → 401 x5;
   `203.0.113.8` + `diger1@example.com` → **401**; `203.0.113.7` + `diger2@example.com` → **429**;
   `203.0.113.8` + `uye@example.com` → 429.
   Anlamı: .8, .7'nin beş hatasından etkilenmedi (fren geçit IP'sine bağlı olsaydı .8 de 429 alırdı); .7 farklı
   e-postayla bile 429 aldı, yani engel IP sayacından geliyor.
- Kod: `bin/panel_kimlik.py` `DenemeFreni.engelli_mi` (satır 161-165) e-posta sayacına **veya** IP sayacına
  bakar (`DENEME_SINIRI = 5`, pencere 15 dk; satır 21-22); `basarisiz` (167-173) ikisine de yazar. Bu yüzden aynı
  e-postayla 5 hatadan sonra IP'den bağımsız 429 gelmesi koddan beklenen davranıştır.

**Sonraya kalan (bu planda düzeltilmedi).** Konteynerdeki 4 hata hep `tests/test_formdan_takim.py` `DefterGitTesti`
(`test_danisman_defteri_git_disinda` kalite/finans/satis-muduru, `test_onayli_formlar_git_disinda_sablon_izleniyor`):
`git archive` kökünde `.git` yok, `git check-ignore` çalışmıyor; test ortamı artefaktı, planın dokunduğu modül değil.
Çözüm önerisi: bu testler `.git` yoksa atlansın.

## Kağan'ın elle adımları (ajan yapmaz)

1. Planı ve PR'ı gözden geçir; özellikle `X-Forwarded-For` kuralı (Task 2) ve `tasima.py` reddetme kuralları.
2. `deploy/KURULUM.md`'yi yazılımcıya gönder; iki soruyu (veritabanı ağı, makine kullanıcısı) yanıtlasın.
3. `.env` değerlerini güvenli kanalla ver (S-2): yeni Console API anahtarı, sunucudan ulaşılan veritabanı adresleri.
4. Geçiş günü (KURULUM.md §6): sunucuda kontrol → Mac'te `zamanla.py --kaldir`, panel durdur →
   `python3 bin/tasima.py --paketle` (kendi terminalinde) → sunucuda `--ac` → kullanıcılar → `PANEL_ADRES`.
5. İlk gerçek `claude -p` koşusu sunucuda, onayınla (para harcar, Stop hook'u ilk kez orada dener).
6. Rapor postası kurulumunun kalan adımları (`2026-11-23-rapor-postasi.md`) panel adresi belli olunca.

## Spec'te belirsiz kalan ve planın çözdüğü noktalar

- Geçiş günü 1. adım "kontrol temiz çıkar" der, ama `roller.json`/`kullanicilar.json` 3. adımda (taşıma) gelir →
  `--tasima-oncesi` bayrağı (Task 3).
- S-1 listesinde `takimlar/bekci-telemetri.jsonl` yok; akşam raporu onu okur → listeye eklendi (Task 4).
- "CLAUDE.md'de `deploy/` satırı güncellenir": bugün öyle bir satır yok → eklenir (Task 7).
- "Hepsi sürümü sabitlenmiş": `apt` paketleri taban imaj etiketiyle sabitlenir (Task 6).
- `--ac` çakışma davranışı spec'te yok → aynı içerik atlanır, farklı içerik reddedilir, `--ustune-yaz` yedekler (Task 5).
