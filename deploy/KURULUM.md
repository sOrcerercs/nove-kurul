# Nove Kurul Ofisi — sunucu kurulumu (Docker Compose)

Bu belge, sistemi şirket sunucusuna kuracak yazılımcı içindir. Baştan sona okursanız Kağan'a soru sormadan
kurabilirsiniz. Sizden istenen iki karar 3. bölümde, soru olarak yazılı.

Komutlar depo kökünden çalışır (`/srv/nove-kurul`). `docker compose` komutlarındaki
`-f deploy/docker/compose.yaml` bayrağı her seferinde yazılmıştır.

## 1. Ne kuruluyor

- **Tek imaj, iki servis, tek klasör.** İmajda Python, Node 22 ve Claude Code komut satırı aracı var; kod imajda
  **yok**. Sunucudaki depo klasörü (`/srv/nove-kurul`) konteynerlere aynı yolla bağlanır.
  - `panel`: web arayüzü. Port yalnız makinenin içine açılır (`127.0.0.1:8770`); dışarıyı ters vekil (HTTPS) açar.
    Soruları yürüten arka plan ilerleticisi de bunun içindedir.
  - `zamanlayici`: `supercronic` ile dört zamanlı iş (İstanbul saati): 08:00 sabah, pazartesi–cuma 09:30 Kalite
    günlük raporu, her 10 dakikada soru ilerletme, 19:00 akşam. Tatil ve mesai kararını kod verir, cron yalnız tetikler.
- **Veritabanı yok.** Sistemin kendi veritabanı bulunmaz; durum bağlı klasördeki dosyalardır (yanıtlar, kayıtlar,
  koşular, defterler, roller, kullanıcılar). Konteyner silinse de durum kalır. Kalite programı ve PYS veritabanları
  bu işin dışındadır; sistem onlara yalnız okuma yetkili bağlantıyla bakar.
- Claude Code'un oturum ve önbellek klasörü `claude-ev` adlı bir volume'dur; depoya karışmaz.
- Servisler `.env` dosyasını **kendileri** okur. Compose'ta `env_file` yoktur, sırlar ortam değişkeni olarak
  ikinci bir yerde durmaz. Bu yüzden `.env`'e dokunmayın, yalnız yazın.

## 2. Önkoşullar

- Docker ve Docker Compose v2 (`docker compose` komutu).
- Git.
- Konteynerden **dışarı çıkış** açık olmalı:
  - Anthropic API (zorunlu);
  - NVIDIA ya da OpenAI API (önerilen; Denetçi için);
  - SMTP sunucusu (isteğe bağlı; rapor postası için).
- Bir **ters vekil** (Caddy, nginx vb.): HTTPS sonlandırır, yalnız şirket ağından ya da VPN'den geleni
  `127.0.0.1:8770`'e iletir. Panel herkese açık internete **açılmaz**. Örnek: `deploy/Caddyfile.example`.

## 3. Sizden iki karar

**Karar 1 — Kalite ve PYS veritabanlarına konteynerden hangi adresle ulaşılır?**
Mac'teki `localhost` adresi sunucuda çalışmaz; konteynerin içinde `localhost` konteynerin kendisidir.
- Veritabanı aynı makinede, Docker'da ise: ortak bir dış Docker ağı kurun, URL'de servis adını kullanın.
  `deploy/docker/compose.yaml`'ın başındaki yorum, iki servise o ağı nasıl ekleyeceğinizi gösterir.
  **Dikkat:** panel bu ağa da bağlanır. Bu ağda **yalnız veritabanı konteynerleri** olmalı; sunucudaki başka
  uygulamaların da bağlı olduğu genel bir ağ kullanmayın. Nedeni 4. bölümde, "Vekil de konteynerdeyse" altında.
  Veritabanı genel bir ağdaysa, yalnız veritabanı ile bu sistemi içeren ayrı bir ağ açın ya da veritabanına
  makinenin adresi ve yayınlanan portu üzerinden ulaşın.
- Başka bir makinedeyse: makine adı ya da IP'yi kullanın ve konteynerden o porta erişimi açın.

Seçtiğiniz adres `.env`'deki `QA_READONLY_URL` ve `OKR_READONLY_URL` değerleri olur (5. bölüm).
`sunucu_kontrol.py --db` bağlantıyı dener ve yanlış adresi yakalar.

**Karar 2 — Depo, `.env` ve durum hangi makine kullanıcısına ait olacak?**
Hepsi **tek** bir makine kullanıcısına aittir. İmaj o kullanıcının uid/gid'iyle derlenir (aşağıdaki
`NOVE_UID` ve `NOVE_GID`), böylece konteyner içindeki root olmayan kullanıcı (`nove-ajan`) bağlı klasöre
yazabilir. `git pull` da yalnız o kullanıcıyla yapılır; başka kullanıcıyla yapılırsa dosya sahipliği bozulur.
`sunucu_kontrol.py` sahipliği de denetler.

Nove Finans ile aynı makineye kuruyorsanız ortak `.env` ve ortak kullanıcı olmaz; ayrı klasör, ayrı kullanıcı.

## 4. Adımlar

Aşağıdakileri 3. bölümde seçtiğiniz kullanıcıyla yapın.

```bash
# 1) Depoyu al (<depo-adresi>: şirketin git sunucusundaki depo; adresi Kağan verir)
git clone <depo-adresi> /srv/nove-kurul
cd /srv/nove-kurul

# 2) .env dosyasını yaz (anahtar adları 5. bölümde; değerleri Kağan verir)
#    Dosyayı kendi editörünüzle oluşturun, sonra izni daraltın:
chmod 600 .env

# 3) İmajı derle (uid/gid = 3. bölümdeki kullanıcı)
export NOVE_UID=$(id -u)
export NOVE_GID=$(id -g)
docker compose -f deploy/docker/compose.yaml build

# 4) Servisleri başlat
docker compose -f deploy/docker/compose.yaml up -d

# 5) Kurulumu doğrula
docker compose -f deploy/docker/compose.yaml exec panel python3 bin/sunucu_kontrol.py --db --tasima-oncesi
```

**`.env` dosyasının biçimi.** Düz metin dosyasıdır; her satıra bir anahtar yazılır: önce anahtarın adı, hemen
ardından eşittir işareti, hemen ardından değer. Eşittir işaretinin iki yanında boşluk bırakmayın. Değeri tırnak
içine almanız gerekmez. `#` ile başlayan satırlar yorum sayılır, boş satırlar atlanır. Anahtar adları 5. bölümdeki
tablolardadır.

`build` mutlaka `up -d`'den önce gelir: yalnız `panel` servisinde `build:` vardır, `zamanlayici` aynı imajı
(`nove-kurul:yerel`) kullanır.

Bağlı klasörün konumu varsayılan olarak `/srv/nove-kurul`'dur; başka bir yol kullanacaksanız `NOVE_KOK` değişkenini,
başka bir port için `NOVE_PORT`'u ayarlayın. Konteyner içindeki yol her durumda `/srv/nove-kurul` kalır.

**`sunucu_kontrol.py` ne yapar.** Yalnız okur; yalnız anahtar **adlarını** ve sonuçları basar, hiçbir değeri
basmaz; Anthropic'e istek atmaz (para harcamaz). Eksik varsa çıkış kodu 1'dir. `--tasima-oncesi`, Mac'ten
taşınacak `deploy/roller.json` ve `deploy/kullanicilar.json` henüz yokken bunların eksikliğini hata saymaz.
Geçiş gününden sonra bayraksız (`--db` ile) koşunca tamamen temiz çıkmalıdır.

### Ters vekil

`deploy/Caddyfile.example` örneğini kendi alan adınıza ve şirket ağı/VPN aralığınıza göre düzenleyin
(yer tutucu: `panel.example.com`, `10.0.0.0/8`). İlettiği hedef `127.0.0.1:8770`'tir.

Panel `--https-arkasinda` ile çalışır ve giriş denemesi frenini istemci IP'sine göre uygular (5 yanlış şifre,
15 dakika kilit). Bunun için vekilin **`X-Forwarded-For`** başlığını istemcinin gerçek adresinden yazması gerekir.
- **Caddy:** `reverse_proxy` bunu kendiliğinden yapar. `trusted_proxies` ayarlamayın; yalnız Caddy'nin kendisi
  başka bir vekilin arkasındaysa gerekir.
- **Başka vekil (nginx, HAProxy, ...):** başlığı gerçek istemci adresiyle **kendiniz yazmalısınız**; istemcinin
  gönderdiği başlığı olduğu gibi geçirmeyin. nginx için:
  `proxy_set_header X-Forwarded-For $remote_addr;` (`$proxy_add_x_forwarded_for` değil).
  Panel yalnız başlığın en sağdaki değerine güvenir ve yalnız bağlantı vekilden (loopback/özel ağ) geliyorsa.
  Vekil başlığı yazmazsa herkes tek IP görünür ve beş yanlış şifre herkesi kilitler (bkz. 9. bölüm).

#### Vekil de konteynerdeyse

Yukarıdaki anlatım, vekilin doğrudan makinede (konteyner dışında) çalıştığını varsayar. Vekil de bir Docker
konteyneriyse `127.0.0.1:8770`'e ulaşamaz: konteynerin içinde `127.0.0.1` vekil konteynerinin kendisidir.
Bu durumda:

1. **Yalnız vekil ile panelin bulunduğu ayrı bir Docker ağı** açın (örnek ad: `nove-vekil`):
   `docker network create nove-vekil`
2. Paneli bu ağa ekleyin. `deploy/docker/compose.yaml`'ın başındaki yorum nasıl yapılacağını gösterir.
   Vekil konteynerini de bu ağa bağlayın.
3. Vekilin hedefini `127.0.0.1:8770` yerine **`panel:8770`** yapın (Caddy'de `reverse_proxy panel:8770`).

**Paneli genel bir ağa bağlamayın.** Panel konteynerin içinde bütün adreslerden bağlantı kabul eder ve
şifresiz HTTP konuşur. Aynı Docker ağındaki her konteyner panele doğrudan ulaşabilir; böylece vekilin IP
süzgecini (yalnız şirket ağı/VPN) atlar. Üstelik Docker ağları özel adres aralığındadır; panel o ağdan gelen
bağlantıyı vekil sayar ve `X-Forwarded-For` başlığına güvenir. Yani oradaki bir konteyner giriş frenini de
aşabilir. Bu yüzden vekil ağında vekilden başka konteyner, veritabanı ağında da veritabanından başka konteyner
olmamalıdır.

## 5. `.env` anahtarları

`.env` depo kökünde durur, izni `600`'dür, sahibi 3. bölümdeki kullanıcıdır. **Git'e girmez, imaja girmez.**
Bu belge yalnız anahtar adlarını söyler.

**Değerleri Kağan size güvenli bir kanaldan verir:** şirketin parola yöneticisi ya da yüz yüze. Mail ya da
sohbet mesajı olmaz. **Mac'teki `.env` kopyalanmaz**; sunucuda ayrı ve yeni değerler kullanılır.

**Sunucuda kişisel Claude aboneliği kullanılmaz.** `claude login` yapmayın; sistem `ANTHROPIC_API_KEY` ile çalışır
ve maliyet şirket hesabına yazılır.

Zorunlu:

| Anahtar | Ne işe yarar | Nereden alınır |
|---|---|---|
| `ANTHROPIC_API_KEY` | Tüm ajan koşuları (`claude -p`) | Nove'nin Anthropic Console organizasyonu; sunucu için yeni bir anahtar üretilir |
| `QA_READONLY_URL` | Kalite Danışmanı'nın Kalite programı veritabanına salt okunur bağlantısı | Kağan verir; ağ adresi 3. bölümdeki karara göre sunucudan ulaşılan adres olur |
| `OKR_READONLY_URL` | OKR Danışmanı'nın PYS veritabanına salt okunur bağlantısı | Aynı |

Önerilen (ikisinden biri yeterli):

| Anahtar | Ne işe yarar | Nereden alınır |
|---|---|---|
| `NVIDIA_API_KEY` | Denetçi'nin ayrı model ailesinden ilk tercihi | NVIDIA NIM hesabı; Kağan verir |
| `OPENAI_API_KEY` | Denetçi'nin ikinci tercihi | OpenAI hesabı; Kağan verir |

İkisi de yoksa Denetçi geçici olarak Claude yedeğine düşer ve kayda "aynı aile" notu yazar. Kurulum durmaz,
`sunucu_kontrol.py` uyarı verir.

İsteğe bağlı (rapor postası; altısı birlikte dolu olmalı, yoksa posta gönderilmez, sistem çalışmaya devam eder):

| Anahtar | Ne işe yarar | Nereden alınır |
|---|---|---|
| `POSTA_SMTP_SUNUCU` | Giden posta sunucusu | Şirketin posta yöneticisi |
| `POSTA_SMTP_PORT` | SMTP portu (sayı) | Aynı |
| `POSTA_KULLANICI` | SMTP hesabının kullanıcı adı | Aynı |
| `POSTA_SIFRE` | SMTP hesabının parolası | Aynı; Kağan'dan güvenli kanalla |
| `POSTA_GONDEREN` | Gönderen adres | Aynı |
| `PANEL_ADRES` | Postadaki bağlantının adresi; `https://` ile başlar | Ters vekilin gerçek adresi (6. bölümün son adımı) |

**`.env` değişince** servisleri yeniden başlatın (`docker compose restart`; tam komut
`docker compose -f deploy/docker/compose.yaml restart`).
İmajı yeniden derlemek gerekmez. Yeniden başlatmadan önce **açık soru olmadığını** görün (8. bölümdeki ilk adım
gibi): yeniden başlatma, o anda yürüyen bir ajan koşusunu yarıda keser.

## 6. Geçiş günü (Mac'ten sunucuya)

Sistem bugün Kağan'ın Mac'inde çalışıyor. Mac ile sunucu **aynı anda** zamanlı iş koşturmamalı; yoksa aynı günün
raporu iki yerde açılır. Sıra budur; Kağan Mac tarafını yapar, siz sunucu tarafını.

1. **Sunucuda ön kontrol** (4. bölümün 5. adımı) temiz çıkar:
   `docker compose -f deploy/docker/compose.yaml exec panel python3 bin/sunucu_kontrol.py --tasima-oncesi`
2. **Mac'te zamanlayıcıları kaldır ve paneli durdur** (Kağan):
   `python3 bin/zamanla.py --kaldir`
   Bu komut zamanlı işlerle birlikte 8770'teki yerel paneli (sahne) de durdurur. Panel ya da sahne ayrıca bir
   terminalde elle açıldıysa o terminalde `Ctrl+C` ile kapatın. 8770'te hâlâ dinleyen var mı diye bakmak için:
   `lsof -nP -iTCP:8770 -sTCP:LISTEN` (çıktı boşsa port boştur). 8770 doluyken paketleme reddedilir.
3. **Mac'te durumu paketle** (Kağan; açık soru yokken):
   `python3 bin/tasima.py --paketle`
   Bu, bir `.tar.gz` arşivi ve yanına bir `.sha256` dosyası üretir; ikisi de sunucuya gider. İkisi de
   varsayılan olarak **ev klasörüne** yazılır; başka bir klasör için `--cikti DIZIN` ekleyin (deponun içi olamaz). Paket; `yanitlar/`,
   `sirket-log/`, `deploy/{roller,kullanicilar,posta-alicilari}.json`, `formlar/onayli/` ve
   `takimlar/*/{defter.md,durum.json,kosu,cikti}` içerir. **`.env` paketlenmez.** Açık soru ya da dolu koşu kilidi
   varsa paketleme reddedilir; yarım soru taşınmaz. Önce `--kuru` ile neyin gideceğini görebilirsiniz.
4. **Sunucuda aç.** Arşiv ve `.sha256` aynı klasörde olmalı (örnek: `/srv/tasima`). İki dosyanın izni yalnız
   sahibine açıktır; bu yüzden ya onları 3. bölümdeki kullanıcıyla kopyalayın ya da kopyaladıktan sonra
   sahipliği o kullanıcıya verin: `sudo chown <karar-2-kullanicisi> /srv/tasima/*`. Aksi hâlde `--ac`
   "okuma izni yok" der.
   ```bash
   docker compose -f deploy/docker/compose.yaml stop
   docker compose -f deploy/docker/compose.yaml run --rm -v /srv/tasima:/tasima:ro panel \
     python3 bin/tasima.py --ac /tasima/<arsiv-adi>.tar.gz
   docker compose -f deploy/docker/compose.yaml up -d
   docker compose -f deploy/docker/compose.yaml exec panel python3 bin/sunucu_kontrol.py --db
   ```
   Son komut **bayraksız** (`--tasima-oncesi` olmadan) tamamen temiz çıkmalıdır. Sağlama toplamı tutmazsa arşiv
   açılmaz. Hedefte aynı dosya varsa ve farklıysa `--ac` **çatışma diye reddeder**, sessizce ezmez. Mac'teki
   hâli bilerek yazmak isterseniz `--ustune-yaz` ekleyin; eski dosyalar önce `sirket-log/tasima-yedek/<zaman>/`
   klasörüne kopyalanır. Önce `--kuru` ile denenebilir.
5. **Kullanıcıları ekle.** Şifreler (özetlenmiş hâliyle) `kullanicilar.json` ile geldiği için mevcut kullanıcılar
   yeniden şifre belirlemez. Yeni kullanıcı için, şifreyi kişi kendisi girer:
   `docker compose -f deploy/docker/compose.yaml exec -it panel python3 bin/panel.py --kullanici-ekle uye@example.com`
6. **`PANEL_ADRES`'i gerçek adrese çevirin** (5. bölüm) ve `docker compose ... restart` yapın. Rapor postasının
   kalan kurulum adımları bundan sonra tamamlanır.

**Saat notu (09:30).** Taşıma günü saat 09:30'dan önce yapılırsa o günün Kalite raporu sunucuda açılır. Sonra
yapılırsa Mac'te açılmış rapor taşınır; sunucu aynı numarayı gördüğü için ikinci kez açmaz.

## 7. Yedek

Depo klasörü durumun kendisidir. Aşağıdakileri düzenli yedekleyin (hepsi `/srv/nove-kurul` altında):

- `yanitlar/` (Yanıt defteri)
- `sirket-log/` (soru kayıtları, raporlar, telemetri)
- `deploy/*.json` (roller, kullanıcılar, posta alıcıları)
- `formlar/onayli/`
- `takimlar/*/defter.md`, `takimlar/*/durum.json`, `takimlar/*/kosu/`, `takimlar/*/cikti/`
- `takimlar/bekci-telemetri.jsonl`
- `.env` (yalnız izni korunarak ve şifreli yedek ortamında; içinde sır var)

Bunların çoğu **kişisel veri** taşır (`yanitlar/`, `deploy/*.json`, `formlar/onayli/`); yedeği buna uygun
saklayın ve herkese açık bir yere koymayın. Geri kalan her şey `git clone` ile yeniden gelir.

## 8. Güncelleme

1. Açık soru olmadığını görün (panelde ya da `sirket-log/` altında bekleyen soru yok).
2. 3. bölümdeki kullanıcıyla: `cd /srv/nove-kurul && git pull`
3. `docker compose -f deploy/docker/compose.yaml restart`

Kod imajda olmadığı için bu yeterlidir. İmaj **yalnız `deploy/docker/Dockerfile` değişince** yeniden derlenir
(`build` + `up -d`). `NOVE_UID`/`NOVE_GID`'yi yeniden dışa aktarmayı unutmayın.

## 9. Sorun giderme

`sunucu_kontrol.py` her kontrol için bir satır basar: TAMAM, UYARI, HATA ya da BİLGİ. Son satır hata ve uyarı
sayısıdır.

| Satır | Anlamı ve çözüm |
|---|---|
| `env-dosyasi` | `.env` yok ya da izni `600` değil: `chmod 600 .env` |
| `zorunlu-anahtarlar` | Eksik anahtar adlarını söyler (değeri değil); `.env`'e ekleyin, `restart` |
| `posta-anahtarlari` | BİLGİ: isteğe bağlı; posta kullanılmayacaksa sorun değil |
| `claude` | `claude --version` çalışmıyor: imaj bozuk, yeniden derleyin |
| `denetci` | UYARI: NVIDIA ya da OpenAI anahtarı yok; Denetçi aynı model ailesine düşer |
| `saat-dilimi` | Konteyner saati İstanbul değil: imajı yeniden derleyin, `TZ` değiştirmeyin |
| `depo-yazilabilir` | Konteyner kullanıcısı klasöre yazamıyor: uid/gid ile sahipliği (3. bölüm, karar 2) eşleştirin |
| `sahiplik` | Dosyalar başka kullanıcıya ait ya da root olarak koşuyor: `chown -R` ile düzeltin; `git pull`'u başka kullanıcıyla yapmayın |
| `roller`, `kullanicilar` | `deploy/roller.json`, `deploy/kullanicilar.json` yok: geçiş gününden önce normal, sonra eksiktir |
| `db` | Kalite/PYS bağlantısı kurulamıyor: 3. bölümdeki karar 1'i gözden geçirin (`localhost` çalışmaz; ağ ve port erişimi) |

Diğer durumlar:
- **Günlükler:** `docker compose -f deploy/docker/compose.yaml logs panel` ve `... logs zamanlayici`.
- **Kaçan zamanlı iş** (servis kapalıyken saati geçtiyse) elle çalıştırılır, örneğin Kalite raporu:
  `docker compose -f deploy/docker/compose.yaml exec zamanlayici python3 bin/gunluk.py --rapor`
  (`--sabah`, `--ilerlet`, `--aksam` de aynı biçimde).
- **Herkes giriş yaparken `429` alıyor:** vekil `X-Forwarded-For` yazmıyor, panel herkesi tek IP görüyor ve fren
  herkesi kilitliyor. 4. bölümdeki "Ters vekil" kuralını uygulayın.
- **Servis sürekli yeniden başlıyor:** önce `logs`; sık neden `.env` izni ya da sahiplik.
- **İlk gerçek soru (`claude -p`) Kağan onayıyla yapılır.** Para harcar ve Denetçi'nin Stop kancasını da dener;
  ilk koşuda küçük bir düzeltme gerekebilir, bu beklenen bir risktir. Kurulumu `sunucu_kontrol.py` ile doğrulamak
  para harcamaz.
