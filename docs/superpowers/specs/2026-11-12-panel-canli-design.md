# Panel canlı — tasarım

> Durum: **onaylı** — Kağan, 12.11.2026 (K1–K6)
> Dayanak: NOVE-KURULUM.md §8, §8b, §8c, Faz 5 · `bin/soru_kapisi.py` · `bin/dagitici.py` · `panel/`
> Herkese açık depo: bu belgede çalışan adı ve e-posta yok.

## Amaç ve neden

Bugün panel yalnız demo: soru tarayıcıda canlandırılır, gerçek hatta gitmez. Arka hat ise hazır
(`soru_kapisi --yeni` → dağıtıcı → Kalite → Denetçi → CEO → `soru_kapisi --ilet` → `yanitlar/`); bu yolla
10 yanıt kurula gitti, hepsi komut satırından.

**Hedef an (Kağan):** Kurul üyesi panelden bir kalite sorusu sorar, yanıtı panelde görür. Beklerken ekranda
**"Sizin için araştırılıyor"** yazar.

Kağan bunu dev sunucusunda (kendi makinesi) deneyerek geliştirmek istiyor; sunucu kurulumu (Caddy, systemd)
bu işin dışında.

## Hedefler

1. `bin/panel.py`: `panel/` dosyalarını ve API'yi aynı adresten veren yerel sunucu (`127.0.0.1:8770`).
2. Gerçek giriş: e-posta + şifre (N11, §8c). Rol `deploy/roller.json`'dan.
3. Panelden soru → `soru_kapisi.yeni` → hat ilerler → yanıt panelde.
4. Bekleme durumu: "Sizin için araştırılıyor".
5. Yanıt defteri gerçek `yanitlar/` kayıtlarından; kurul üyesi yalnız kendi sorularını görür, yönetici hepsini (N10).
6. `?demo` modu olduğu gibi çalışmaya devam eder.

## Hedef dışı (bu iş değil)

- CRM zili (`POST /api/crm/satis`, Faz 7), Caddy/systemd/`deploy/` birimleri, sunucuya kurulum.
- Ajan kartının `takim.md`/`durum.json`/`defter.md`'den canlı beslenmesi.
- Kurulumdaki danışmanların (Finans, OKR, …) devreye alınması.
- Şifre sıfırlama akışı ve "ilk girişte geçici şifre değişir" (N23) — sonra.
- SSE olay akışı (`/api/olaylar`) — bu adımda durum yoklamayla alınır (aşağıda).

## Anti-hedefler (çalışsa bile başarısızlık sayılır)

- Panelin hattın kurallarını atlaması: günlük soru hakkı, tekrar kontrolü, maskeleme, mesai, bütçe,
  rol kontrolü **yalnız `soru_kapisi.yeni`'de** yapılır; panel kendi kopyasını yazmaz.
- Bir kurul üyesinin başka üyenin sorusunu, yanıtını ya da Denetçi/CEO gerekçe ayrıntısını görebilmesi (§8b).
- Aynı anda birden çok `kos.py`'nin yığılması (11.11'deki 5 boş koşu, 1,16 USD). PR #17'nin kilidi korunur;
  panel bunu aşacak bir yol açmaz.
- Şifrenin ya da oturum belirtecinin düz metin olarak dosyaya veya loga yazılması.
- `yanitlar/`'a panelin yazması (yalnız sürücü yazar).

## Kısıtlar

- Yalnız Python stdlib (repo bağımlılıksız; `sahne.py` `http.server` kullanıyor).
- Sunucu yalnız `127.0.0.1`'e bağlanır.
- Her soru gerçek para harcar (koçluk sorusu 1,20 USD; soru tavanı 8 USD). Testler ağ ve `claude` çağırmaz.
- Mesai 08:00–20:00 (İstanbul); dışında gelen soru kayda girer ama sabaha kalır — panel bunu `not:` ile gösterir.
- Kurulu tek danışman Kalite. Başka bölüme yönlenen soru "bu bölüm henüz kurulmadı" olarak sonuçlanmalı,
  sessizce beklememeli.
- Denetçi şu an OpenAI yolunda (NIM kapalı, PR #18).
- `.env` okunmaz/basılmaz; `ANAYASA.md`, `kurallar.md`, `sirket/CEO-KIMLIGI.md` değişmez.
- Mevcut testler: 594 OK, 8 skipped — düşmez.

## Kararlar

**Kağan'ın:**
- K1. Kullanım anı: kurul üyesi soru sorar, yanıtı panelde görür.
- K2. Bekleme ekranı: "Sizin için araştırılıyor".
- K3. Dev sunucusunda test ederek ilerlenir.
- K4. Aşağıdaki varsayımlar (yalnız Kalite yanıt verir; dev'de test hesabı; hattın kuralları atlanmaz;
  gerçek para harcanır) doğru.
- K5. **Kurulmamış bölüme giden soru koşu yapılmadan kapanır** (12.11.2026). Uygun aktif danışman yoksa soru
  "bu bölüm henüz kurulmadı" gerekçesiyle `onaylanamadı` olarak Yanıt defterine girer; para harcanmaz.
  Bu `dagitici.py`'de küçük bir değişiklik ister (B10).
- K6. **Onaylanamayan soruda kurul üyesi kısa sebep görür** (12.11.2026): ham Denetçi/CEO metni değil, bir
  kategori cümlesi + "yöneticiniz bilgilendirildi". Yönetici tam gerekçeyi görür (B8).

**Benim kararım (Kağan okurken kontrol etsin):**
- B1. **Uçlar:** `POST /api/giris`, `POST /api/cikis`, `POST /api/soru`, `GET /api/sorular/<id>`,
  `GET /api/yanitlar`, `GET /api/ben` (oturum açık mı). Hepsi oturum çerezi ister (giriş hariç); çerezsiz `401`.
- B2. **Durum yoklaması, SSE değil:** panel açık sorunun durumunu ~10 sn'de bir `GET /api/sorular/<id>` ile sorar.
  Hat dakikalar sürdüğü için SSE'nin kazancı yok; SSE zil ile (Faz 7) gelir.
- B3. **Hattı ilerletmek:** sunucuda bu iş 10 dk'lık `--ilerlet` zamanlayıcısının; dev'de bu çok yavaş. `panel.py`
  açık (henüz `yanitlar/`'a düşmemiş) bir panel sorusu varken arka planda ~60 sn'de bir **tek** dağıtıcı adımı
  çalıştırır (`gunluk.py --ilerlet` ya da `dagitici.dagit` — builder seçer), soru kalmayınca durur. Aynı anda
  birden çok adım başlatmaz; koşu kilidi doluysa (`ayar.kosu_suruyor`) o turu atlar. Soru girer girmez de bir adım atılır.
  Bu davranış bir bayrakla kapatılabilir (`--ilerletme-yok`), sunucuda zamanlayıcı varken kapalı çalışır.
  Not: `gunluk.py --ilerlet` yalnız `dagitici.dagit(KOK)` çağırır (`bin/gunluk.py:317-320`), ikisi aynı şey. `dagit`
  süreçler arası kilit taşımaz; makinede `zamanla.py`'nin `ilerlet` işi kuruluysa panel `--ilerletme-yok` ile çalışmalı
  (bugün bu repo için kurulu değil). Koşu yığılma koruması `tetik_karari` içinde zaten var (`bin/dagitici.py:158-159`).
- B4. **Kullanıcı dosyası:** `deploy/kullanicilar.json` (git'e girmez, izni 600): e-posta → {ad, yöntem, özet, tuz}; yöntem `scrypt` (varsa) ya da `pbkdf2-sha256` (600 000 tur) — dev makinesindeki Python 3.9/LibreSSL'de `hashlib.scrypt` yok (12.11).
  Ekleme: `python3 bin/panel.py --kullanici-ekle <eposta> --ad "<ad>"` şifreyi `getpass` ile ister (Kağan çalıştırır,
  ajan çalıştırmaz). Rol `roller.json`'dan; kullanıcıda olup rolde olmayan giremez.
- B5. **Oturum:** rastgele belirteç (`secrets`), bellekte tutulur (sunucu yeniden başlarsa yeniden giriş). Çerez
  `HttpOnly; SameSite=Strict; Path=/`; `Secure` yalnız `--https-arkasinda` bayrağıyla (dev http olduğu için).
  Süre 12 saat.
- B6. **Deneme freni:** aynı e-posta ya da IP için 15 dk'da 5 başarısız giriş → `429`.
- B7. **Durum eşlemesi** (`GET /api/sorular/<id>` yanıtı `{durum, metin?, not?}`):
  `arastiriliyor` (kayıt var, `yanitlar/<id>.md` yok) · `yanitlandi` (defterde, onaylı) ·
  `onaylanamadi` (defterde, gerekçesiyle) · `reddedildi` (`yeni` reddetti — `POST /api/soru` anında döner).
  Mesai/bütçe `not:` satırı varsa `arastiriliyor` yanında `not` olarak gösterilir. Kurul üyesi yalnız kendi sorusunu sorgulayabilir; başkasınınkine `404`.
- B8. **Yanıtın gösterimi:** onaylı kayıtta (`bin/soru_kapisi.py:258-268`) panel `## Kurula not` (varsa; CEO'nun
  kurula yazdığı uyarı — yanıtın anlamını değiştirebildiği için gösterilir) ve `## Yanıt` bölümlerini okunur
  biçimde gösterir (basit Markdown: başlık, liste, tablo, kalın). Onaylanamayan kayıtta `## Gerekçe` ham metni
  (`:249-250`) **yalnız yöneticiye** gider; kurul üyesine K6'daki kısa sebep gider. Kısa sebep gerekçe metninden
  sınıflanır: Denetçi/CEO reddi → "Yanıt kalite denetiminden geçemedi" · süre/zaman aşımı → "Süre doldu" ·
  soru bütçesi → "Bu sorunun bütçesi doldu" (Kağan, 12.11) · K5 → "Bu bölüm henüz kurulmadı" · tanınmayan → "Bu soruya şu an güvenilir bir yanıt
  verilemedi"; her birinin sonuna "Yöneticiniz bilgilendirildi." Sınıflama sunucuda yapılır, ham metin kurul
  rolüne hiç gönderilmez. Bu adımda yönetici de yalnız defter dosyasını görür; `sirket-log/sorular/<id>.md`
  denetim izi panele açılmaz (sonra).
- B8b. **Görünürlük süzgeci (N10):** kayıt şu durumda görünür: soran bensem, ya da kayıt `gorunurluk: kurul`
  taşıyorsa (Kalite günlük raporu — `bin/soru_kapisi.py:197-200`, `2026-10-22-kalite-gunluk-rapor-design.md:98-99`),
  ya da rolüm `yonetici` ise. Katı "yalnız kendi e-postam" süzgeci günlük raporları gizlerdi.
- B9. **Panel tarafı:** `panel.js`'te `DEMO` yanlışken gerçek uçlar kullanılır; demo akışı (`yonlendir`, `adimUret`
  canlandırması) gerçek modda çalışmaz. Gerçek modda soru gönderilince akış alanında "Sizin için araştırılıyor"
  ve geçen süre görünür; 3D sahne bekleme boyunca mevcut boşta animasyonunda kalır. Yanıt gelince akış alanı yanıtı gösterir,
  Yanıt defteri yenilenir. Sayfa yenilenirse açık soru `GET /api/yanitlar`'dan bulunur ve bekleme ekranı geri gelir.
- B10. **Kurulmamış bölüm (K5'in uygulanışı).** Bugün iki açık var: tek aktif danışman Kalite olduğunda Haiku'ya
  yalnız `kalite` seçeneği sunuluyor (`bin/dagitici.py:201-208`, `:245`), yani kalite dışı soru Kalite'ye gidip
  koşu harcayabiliyor; `yönlendirilemedi` durumu ise `BITMIS` içinde (`:320`) ve `ilet` hiç çağrılmıyor, soru
  deftere girmiyor. Değişiklik:
  - Haiku istemine "hiçbiri" seçeneği eklenir; Haiku "hiçbiri" derse soru danışmana gitmez.
  - `yönlendirilemedi` olan soru `soru_kapisi.ilet(..., onaylanamadi="bu bölüm henüz kurulmadı …")` ile
    deftere kapanır (Haiku hatası ya da listede olmayan ad da aynı yoldan, kendi sebebiyle).
  - Anahtar kelime eşleşmesi olan sorunun yolu değişmez. Testler bu üç durumu kapsar.
- B11. **Port:** `8770` (§8 ile aynı). Şu an 8000'de çalışan `http.server` kapatılır.

## Builder'a bırakılanlar

- `panel.py`'nin `sahne.py`'den ne kadar kod aldığı ya da ayrı yazıldığı.
- Markdown → HTML dönüşümünün ayrıntısı (stdlib; XSS'e karşı önce kaçış).
- Test düzeni (sahte `soru_kapisi`/dağıtıcı; gerçek `claude` çağrısı yok), dosya bölünmesi.
- Arayüzdeki küçük metinler ("Sizin için araştırılıyor" dışında).

## Kağan'ın elle yapacakları (ajan yapmaz)

- `deploy/roller.json`'a ikinci bir test e-postası `kurul` rolüyle eklenir (dosya Kağan'ın).
- İki test hesabı `panel.py --kullanici-ekle` ile açılır (şifre `getpass` ile, ajan görmez).

## Başarı ölçütü

Dev sunucusunda: Kağan test hesabıyla girer, bir kalite sorusu sorar, "Sizin için araştırılıyor" görür,
dakikalar sonra yanıt aynı ekranda belirir ve Yanıt defterinde satır olarak görünür. İkinci bir test hesabı
(kurul rolü) bu soruyu göremez ama Kalite günlük raporunu görür. Kalite dışı bir soru koşu yapılmadan
"Bu bölüm henüz kurulmadı" ile kapanır. `?demo` eskisi gibi çalışır. Test sayısı 594'ün altına düşmez.
