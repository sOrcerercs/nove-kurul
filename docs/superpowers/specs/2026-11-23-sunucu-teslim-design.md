---
durum: onaylandi
guncelleme: 2026-11-23
dal: feature/sunucu-docker
pr: 34
onay: Kağan, 23.11.2026 (yaklaşım A — Docker Compose; tasarım onayı aynı gün)
---

# Sunucu teslimi — Docker Compose paketi

## Neden

Kurul Ofisi bugün Kağan'ın Mac'inde çalışıyor (launchd, `zamanla.py`). Bu yüzden:
- panelin herkesin açabileceği bir adresi yok;
- Kalite günlük raporu Mac açıksa açılıyor;
- rapor postasının gönderdiği bağlantı (`PANEL_ADRES`) bir yere gitmiyor.

NOVE-KURULUM N1 der ki: sistem şirket sunucusunda çalışır. Sunucuyu kuracak olan şirketin yazılımcısı. Yazılımcının
kuralı (20.10.2026): şirket projeleri Docker ile çalışır. §8'deki tasarım ise Docker'sız yazıldı (systemd + Caddy).

Bu belge, yazılımcıya verilecek **teslim paketini** tarif eder. Paket kurulum dosyalarından ve tek bir kurulum
belgesinden oluşur. Ölçüt: yazılımcı Kağan'a neredeyse hiç soru sormadan sistemi ayağa kaldırabilmeli.

## Hedefler

- Yazılımcı `deploy/KURULUM.md`'yi okuyup `docker compose up -d` ile sistemi ayağa kaldırır.
- Panel yalnız şirket ağından ya da VPN'den HTTPS ile açılır.
- Zamanlı işler İstanbul saatiyle koşar:
  - sabah 08:00;
  - Kalite raporu pzt–cuma 09:30;
  - ilerletme her 10 dk;
  - akşam 19:00.
- Durum diskte kalır; konteyner silinse de hiçbir şey kaybolmaz. Durum şunlardır: yanıtlar, kayıtlar, koşular,
  defterler, roller, kullanıcılar.
- Bugünkü güvenlik kilitlerinin hepsi sunucuda da geçerlidir:
  - `.claude/settings.json` deny listesi;
  - Denetçi Stop hook'u;
  - `CLAUDECODE` kilitleri;
  - `.env` izni 600.
- Kurulumun doğru olduğunu tek bir komut söyler: `bin/sunucu_kontrol.py`.

## Hedef olmayanlar

- **Veritabanı taşıma.** Kurul Ofisi'nin kendi veritabanı yok; durumu dosyada tutar. Kalite programının ve PYS'nin
  veritabanları bu işin dışındadır. Bağlantı adresleri (`QA_READONLY_URL`, `OKR_READONLY_URL`) `.env`'den gelir.
- CI/CD, otomatik dağıtım, birden çok kopya, yük dengeleme.
- Faz 5'te yazılmamış özellikler: SSE (`/api/olaylar`), CRM zili.

## Olmaması gerekenler (anti-goal)

- Panelin herkese açık internete açılması.
- `.env`'in ya da kişisel verinin imaja gömülmesi. Kişisel veri: `yanitlar/`, `deploy/*.json`, `formlar/onayli/`.
- Sunucuda kişisel Claude aboneliği kullanılması. Kullanılacak olan Nove'nin Console API anahtarıdır (§8).
- Mac ile sunucunun aynı anda zamanlı iş koşturması, yani aynı günün raporunun iki yerde açılması.

## Kısıtlar

- Kod: Python stdlib, bir de `psycopg` (Kalite ve OKR okuyucuları). Testler Python 3.9 uyumlu kalır.
- Her soru `claude -p` ile koşar, bu yüzden imajda Node ve Claude Code komut satırı aracı bulunur.
- `kos.py` ve `rapor_postasi.py` `fcntl` dosya kilidi kullanır. Kilidin işe yaraması için tüm servisler aynı makinede,
  aynı bağlı klasörü (bind mount) görmelidir.
- `.env`'i servisler kendileri okur (`ayar.env_yukle` ve `ortam_yukle`). Bu yüzden compose'ta `env_file`
  kullanılmaz; sırlar ortam değişkeni olarak iki yerde durmaz.
- Panel bugün `127.0.0.1`'e sabit bağlanıyor (`bin/panel.py:304`).
- S4: Nove Finans ile aynı makineye kurulursa ortak `.env` ve ortak kullanıcı olmaz.

## Yaklaşımlar

| | Nasıl | Artısı | Eksisi |
|---|---|---|---|
| **A — Docker Compose (seçildi)** | Tek imaj (Python + Node + Claude Code). İki servis: `panel` ve `zamanlayici`. Depo sunucudaki klasörden bağlanır | Yazılımcının standardı; kurulum ve güncelleme tek komut | §8 yeniden yazılır; Claude Code konteynerde denenmeli |
| B — Doğrudan makine (§8) | `nove-ajan` kullanıcısı, systemd zamanlayıcıları, Caddy | En az hareketli parça; tasarım yazılı | Yazılımcının Docker kararına ters |
| C — Karışık | Panel Docker'da, zamanlayıcılar makinede | — | İki düzen birden; elendi |

Kağan, 23.11.2026: **A**.

## Tasarım

### Paketin dosyaları

| Dosya | Ne |
|---|---|
| `deploy/docker/Dockerfile` | `python:3.12-slim` tabanı. İçinde şunlar bulunur, hepsi sürümü sabitlenmiş: `tzdata`, `git`, Node 22, `@anthropic-ai/claude-code`, `psycopg[binary]`, `supercronic`. Root olmayan bir kullanıcı (`nove-ajan`, uid/gid build argümanı). `TZ=Europe/Istanbul`. Kodu kopyalamaz |
| `deploy/docker/compose.yaml` | İki servis, aynı imaj, aynı bind mount: `/srv/nove-kurul` (sunucu) → `/srv/nove-kurul` (konteyner), çalışma dizini orası. `restart: unless-stopped` |
| `deploy/docker/crontab` | `zamanlayici` servisinin işleri (aşağıda) |
| `.dockerignore` | Depo kökünde. `.env`, `yanitlar/`, `sirket-log/`, `deploy/*.json`, `formlar/`, `kasa/`, `takimlar/*/{kosu,cikti,gelen,veri}` ve defter dosyaları build bağlamına girmez |
| `deploy/Caddyfile.example` | Örnek ters vekil: TLS, yalnız şirket ağı ya da VPN IP aralığı, `127.0.0.1:8770`'e yönlendirme. Yazılımcının kendi vekili varsa yalnız örnektir |
| `deploy/KURULUM.md` | Yazılımcının belgesi: önkoşullar, adımlar, `.env` anahtar adları (değer yok), yedeklenecek klasörler, güncelleme, sorun giderme |
| `bin/tasima.py` | Mac'ten sunucuya durum taşıma: `--paketle` / `--ac` (bkz. S-1) |
| `bin/sunucu_kontrol.py` | Kurulum doğrulaması. Yalnız okur; yalnız anahtar adlarını ve sonuçları basar, hiçbir değeri basmaz |

### Servisler

- **`panel`**: `python3 bin/panel.py --adres 0.0.0.0 --https-arkasinda`.
  - Panelin arka plan ilerleticisi açıktır; soruları bu yürütür. §8'deki `soru_kapisi --dinle` yerini bu tutar.
  - Port yalnız makinenin içine yayınlanır: `127.0.0.1:8770:8770`. Dışarıya ters vekil açar.
- **`zamanlayici`**: `supercronic deploy/docker/crontab`. İşler:
  - `0 8 * * *` → `gunluk.py --sabah`
  - `30 9 * * 1-5` → `gunluk.py --rapor`
  - `*/10 * * * *` → `gunluk.py --ilerlet`
  - `0 19 * * *` → `gunluk.py --aksam`

  Panelin ilerleticisi ile `--ilerlet` aynı anda koşabilir. İkisi de `kos.py` kilidini gözetir (§8'de de ikisi vardı).
  Tatil ve mesai kararını kod verir; cron yalnız tetikler.

### Kod değişiklikleri (küçük)

- `bin/panel.py`: yeni `--adres` argümanı.
  - Varsayılan `127.0.0.1`, böylece bugünkü davranış aynı kalır.
  - Başlangıç iletisi gerçek adresi basar.
  - `0.0.0.0` verildiğinde stderr'e uyarı yazar: "yalnız konteyner içinde; makinede ters vekil arkasında kullan".
- `bin/sunucu_kontrol.py` (yeni). Kontroller ve davranış:
  - `.env` var mı, izni 600 mü;
  - zorunlu anahtarlar dolu mu (`ANTHROPIC_API_KEY`, danışmanların `gerekli_anahtarlar`'ı); posta anahtarları ayrı
    satırda "isteğe bağlı" olarak gösterilir;
  - `claude --version` çalışıyor mu;
  - Denetçi sağlayıcısı: `NVIDIA_API_KEY` ya da `OPENAI_API_KEY` yoksa **uyarı** (hata değil) — bekçi geçici Opus
    yedeğine düşer ve kayda "aynı aile" notu yazar (`bekci.py`). *(Claude'un kararı: kurulumu durdurmaz.)*
  - saat dilimi İstanbul mu;
  - depo yazılabilir mi;
  - `deploy/roller.json` ve `deploy/kullanicilar.json` var mı;
  - `--db` verilirse Kalite ve OKR okuyucularına salt okunur bağlantı denemesi yapar;
  - `claude`'a gerçek istek atmaz (para harcamaz);
  - çıkış kodu: eksik varsa 1.
- **`.env` yüklemesi (inceleme bulgusu):** `panel.py` ve `gunluk.py` açılışta `ayar.ortam_yukle()` çağırır
  (`ceo.py`/`bekci.py` gibi). Bugün İş Dağıtımcı'nın `claude -p --model haiku` çağrısı (`dagitici.py:239`) yalnız
  `os.environ`'u taşır; Mac'te kişisel `claude login` bunu gizliyor, sunucuda anahtarsız kalır ve hiçbir soru
  yönlendirmeyi geçemez. Test: `.env`'deki `ANTHROPIC_API_KEY` dağıtıcının alt sürecine ulaşır. *(Claude'un kararı:
  `env_file` yerine kod — sırlar tek yerde kalır.)*
- **Giriş freni vekil arkasında (inceleme bulgusu):** `DenemeFreni` IP başına 5 hatada 15 dk kilitler
  (`panel_kimlik.py:21`); vekil arkasında herkes aynı IP'den gelir, beş yanlış şifre herkesi kilitler. Çözüm:
  yalnız `--https-arkasinda` açıkken ve istek `127.0.0.1`/özel ağdan (vekil) geliyorsa `X-Forwarded-For`'un **en
  sağdaki** değeri istemci IP'si sayılır; aksi hâlde bağlantı IP'si. Başlık sahteyse en kötü durum bugünkü durumdur.
  Testlerle. *(Claude'un kararı — güvenlikle ilgili, Kağan okurken baksın.)*
- `bin/zamanla.py`: Linux'ta (`sys.platform != "darwin"`) çalışmayı reddeder ve compose'u işaret eder.
- `NOVE-KURULUM.md` §8 ve Faz 0 güncellenir; systemd anlatımı yerine Docker gelir. `CLAUDE.md` klasör yapısında
  `deploy/` satırı güncellenir.

### Sırlar ve kimlik

- `.env` sunucuda `/srv/nove-kurul/.env` konumundadır. Sahibi konteyner kullanıcısının uid'idir, izni 600.
  Değerleri Kağan yazılımcıya güvenli bir kanaldan verir. KURULUM.md yalnız anahtar adlarını listeler.
- `claude -p` alt süreçleri `ANTHROPIC_API_KEY`'i `.env`'den alır. Üç yerde zaten öyle:
  - `kos.py` (`ayar.env_yukle`);
  - `ceo.py:185` (`ortam_yukle`);
  - `bekci.py:420` (`ortam_yukle`).

  Sunucuda kişisel giriş (`claude login`) yapılmaz.
- Claude Code'un ev klasörü (`/home/nove-ajan/.claude`) adlandırılmış bir volume'dur. Oturum ve önbellek burada
  durur, depoya karışmaz.

### Durum ve yedek

Depo klasörü durumun kendisidir. Yazılımcı şunları yedekler (KURULUM.md'de liste):
- `yanitlar/`
- `sirket-log/`
- `deploy/*.json`
- `formlar/onayli/`
- `takimlar/*/{defter.md,durum.json,kosu,cikti}`
- `.env`

Güncelleme sırası: `git pull`, ardından `docker compose restart`. İmaj yalnız Dockerfile değişince yeniden
derlenir.

### Mac'ten geçiş günü

1. Sunucuda `sunucu_kontrol.py` temiz çıkar.
2. Mac'te `python3 bin/zamanla.py --kaldir`. Bunun amacı aynı günün raporunun iki yerde açılmasını önlemek.
3. Mac'teki durum `tasima.py` ile sunucuya taşınır (bkz. S-1).
4. Kullanıcılar eklenir: `docker compose exec -it panel python3 bin/panel.py --kullanici-ekle <eposta>`. Şifreyi
   kişi kendisi girer.
5. `PANEL_ADRES` artık gerçek adres olur. Rapor postası kurulum adımları buradan sonra tamamlanır.

### Test

- Birim testleri:
  - `--adres` argümanı;
  - `sunucu_kontrol.py` kontrolleri (geçici klasörle; değer basmadığı da test edilir);
  - `zamanla.py`'nin Linux'ta reddi.
- Statik testler (`tests/test_deploy_statik.py`):
  - compose portu `127.0.0.1:` ile başlıyor;
  - `env_file` yok;
  - crontab saatleri yukarıdaki dört satırla aynı;
  - Dockerfile'da `TZ=Europe/Istanbul` var ve `USER` root değil;
  - `.dockerignore` `.env`, `yanitlar/` ve `deploy/*.json`'u içeriyor.
- Elle duman testi, Kağan'ın Mac'inde Docker ile (Docker 29 kurulu):
  - imaj derlenir;
  - `docker compose run --rm panel claude --version` çalışır;
  - `sunucu_kontrol.py` kurgusal bir `.env`'le koşar;
  - panel `127.0.0.1:8770`'de açılır.

  Gerçek `claude -p` koşusu ilk sunucu kurulumunda yapılır, Kağan onayıyla.

### Yazılımcıya bırakılan (KURULUM.md'de açıkça sorulur)

- **Ağ:** Kalite ve PYS veritabanlarına konteynerden nasıl ulaşılır? Aynı makinede Docker'daysa ortak bir dış
  ağ ve servis adıyla URL; değilse makine adı/IP. Mac'teki `localhost` URL'si sunucuda çalışmaz —
  `sunucu_kontrol.py --db` bunu yakalar. Konteynerin dışarı (Anthropic, isteğe bağlı NVIDIA/OpenAI, SMTP) çıkışı açık olmalı.
- **Sahiplik:** depo, `.env` ve tüm durum tek bir makine kullanıcısına aittir; imaj o kullanıcının uid/gid'iyle
  derlenir (`--build-arg`). `git pull` da yalnız o kullanıcıyla yapılır. `sunucu_kontrol.py` sahipliği de denetler.

### Duman testi

Mac'teki Docker duman testi planın bir görevidir (insan adımı değil): imaj derlenir, konteyner içinde root olmayan
kullanıcıyla `claude --version`, `sunucu_kontrol.py` ve panel açılışı denenir. Gerçek `claude -p` (para harcar,
Stop hook'u da dener) ilk sunucu kurulumunda Kağan onayıyla yapılır; ilk koşunun orada düzeltme gerektirmesi kabul
edilen risktir. *(Claude'un kararı.)*

## Kağan'ın kararları

- **S-1 — karar (Kağan, 23.11.2026): Mac'teki durum sunucuya taşınır.** Taşınanlar: `yanitlar/`, `sirket-log/`,
  `deploy/{roller,kullanicilar,posta-alicilari}.json`, `formlar/onayli/`, `takimlar/*/{defter.md,durum.json,kosu,cikti}`.
  Kurallar (Claude'un kararı):
  - Taşıma Mac'te zamanlayıcılar kaldırıldıktan (`zamanla.py --kaldir`) ve panel durdurulduktan **sonra**, açık soru
    yokken yapılır; `kos.py` kilidi boş olmalı. Açık soru varsa önce biter ya da bekler — yarım soru taşınmaz.
  - Kopya tek arşivle (`tar`) ve sağlama toplamıyla; sunucuda sahiplik konteyner kullanıcısına verilir.
  - Taşıma günü saat 09:30'dan önce yapılırsa o günün raporu sunucuda açılır; sonra yapılırsa Mac'te açılmış rapor
    taşınır, sunucu aynı id'yi gördüğü için ikinci kez açmaz.
  - Şifreler (`kullanicilar.json`, özetlenmiş) taşındığı için kimse yeniden şifre belirlemez.
  - `bin/tasima.py --paketle` (Mac) / `--ac` (sunucu): neyi paketlediğini listeler, açık soru ya da dolu kilit varsa
    reddeder; değer basmaz.
- **S-2 — karar (Kağan, 23.11.2026): `.env`'i yazılımcı yazar.** KURULUM.md anahtar adlarını, ne işe yaradıklarını
  ve nereden alınacaklarını listeler (değer yok). Değerler Kağan'dan yazılımcıya güvenli bir kanalla gider — mail ya da
  sohbet mesajı değil (Claude'un önerisi: şirketin parola yöneticisi ya da yüz yüze). Mac'teki `.env` sunucuya
  **kopyalanmaz**: sunucuda ayrı ve yeni değerler olur — en az Console API anahtarı yeni, `QA_READONLY_URL` /
  `OKR_READONLY_URL` sunucudan ulaşılan adreslerle. `tasima.py` `.env`'i paketlemez.

## Builder'a kalan

- Sürüm sabitlemeleri: Node, Claude Code, supercronic, psycopg.
- Dockerfile katman düzeni.
- KURULUM.md'nin dili ve sırası.
- `sunucu_kontrol.py` çıktı biçimi.
