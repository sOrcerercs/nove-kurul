# Tebrik Danışmanı — tasarım

> Durum: taslak — Kağan'ın onayını bekliyor · 20.10.2026 · Sahibi: Kağan (Quality Supervisor)
> Bu depo herkese açıktır: bu belgede ve kodda çalışan adı, doğum günü, e-posta adresi yer almaz.

## Amaç

Çalışanların özel günlerinde tebrik görselini ve yazısını hazır hâlde tek bir iç alıcıya (Bahadır Bey) mail
olarak ulaştırmak. Alıcı tebriği şirket grubuna kendisi paylaşır. **Paylaşım kararı ve düğmesi alıcıda kalır**;
amaç onun işini kolaylaştırmak (Kağan, 20.10.2026).

## Hedefler

- Üç tür gün: **doğum günü**, **işe yeni başlayan** (hoş geldin), **bayramlar**.
- Her tür için sabit bir şablon; görselde değişen **yalnız ad** (hoş geldinde ad + ünvan). Bayram görseli herkese
  ortaktır, ad taşımaz (Claude'un çağrısı).
- Tebrik yazısı her tür için **sabit metin**, Türkçe + İngilizce (Kağan).
- Mail gününün sabahı **09:00'da** alıcının posta kutusunda olur (Kağan).
- Hiçbir tebrik sessizce kaybolmaz: tabloda eksik ya da hatalı satır varsa alıcıya bildirilir.

## Hedef olmayanlar

- Çalışana, gruba ya da dışarıya doğrudan gönderim — yok, hiçbir zaman.
- Yeni bebek, evlilik gibi başka kişisel günler (Kağan: yeni bebek yok).
- Yapay zekâyla kişiye özel metin ya da her seferinde yeni görsel.
- WhatsApp ya da başka bir kanal.

## Anti-hedefler (çalışsa bile başarısızlık sayılır)

- Adı yanlış yazılmış tebrik (Türkçe harfler: Ç, Ğ, İ, ı, Ö, Ş, Ü).
- Bozuk ya da uydurma Nove logosu.
- Aynı tebriğin iki kez gitmesi, ya da dünün tebriğinin bugün gitmesi.
- Alıcı dışında birine mail gitmesi.

## Kısıtlar

- **ANAYASA §1 istisnası** — Kağan ekleyecek (20.10.2026 onaylı metin): gönderimi `bin/tebrik_postasi.py` yapar;
  yalnız `.env`'deki tek alıcıya; alıcıyı ajan seçemez ve değiştiremez; içerik yalnız hazır tebrik. **İstisna
  ANAYASA'da yürürlüğe girmeden gönderim kodu birleştirilmez.** Betik, ANAYASA'da `İstisna — tebrik postası` başlıklı
  bir madde yoksa göndermeyi reddeder (Claude'un çağrısı — kural kodla da korunur; Kağan metnin geri kalanını
  değiştirebilir, eşleşme yalnız bu başlıkla). Onaylı taslak metin:
  > **İstisna — tebrik postası (revize __.__.2026):** Tebrik danışmanının hazırladığı görsel ve yazıyı
  > `bin/tebrik_postasi.py` yalnız `.env`'deki tek bir iç alıcıya mail olarak gönderir. Alıcıyı ajan seçemez,
  > değiştiremez. Çalışanlara, gruplara ya da dışarıya gönderim yoktur; paylaşım kararı alıcıdadır. Mail bir yanıta,
  > talimata ya da yayına dönüşmez: yalnız hazır tebrik iletilir.
- **Yapay zekâ yok.** Akış tamamen kurallı bir betiktir; Denetçi ve CEO kapısından geçmez (kurula yanıt değil).
  Panelde "Tebrik Danışmanı" olarak görünür (Kağan'ın adı).
- **Kişisel veri:** tabloda ad soyad, ünvan, doğum günü (yalnız gün ve ay, yıl yok), işe giriş tarihi. Bu veri ve
  üretilen görseller herkese açık depoya girmez (`.gitignore`). Doğum yılı istenmez.
- **Anahtarlar** yalnız `.env`'de: gönderen hesap, alıcı adresi, Drive erişimi. Ajan `.env`'i okuyamaz
  (`.claude/settings.json` deny); betik süreç ortamından alır.
- **Altyapı:** proje şirket sunucusuna Docker + PostgreSQL ile taşınacak (yazılımcının kararı, 20.10.2026). Bugün
  Kağan'ın Mac'inde launchd ile koşar; tasarım sunucuda cron/konteynerle aynı komutla koşacak şekilde yapılır.
- Python 3 stdlib öncelikli (repo düzeni). Dış bağımlılıklar yalnız: Pillow (görsel), openpyxl (xlsx okuma),
  google-auth + google-api-python-client (Drive). Hepsi `requirements-tebrik.txt`'te sabit sürümle (Claude'un çağrısı).
- Saat dilimi **Europe/Istanbul**; sunucuda konteynerde açıkça ayarlanır (Claude'un çağrısı).

## Parçalar ve akış

```
Google Drive'daki Excel  →  bin/tebrik_postasi.py (her gün 08:55)
   (Bahadır Bey günceller)      1. tabloyu oku, satırları doğrula
                                2. bugünün günlerini bul (doğum günü · işe giriş · bayram takvimi)
                                3. şablon + ad → PNG (Pillow, sabit yazı tipi ve konum)
                                4. tek mail: görseller ek, sabit metinler gövdede
                                5. gönderim kaydı (aynı gün ikinci kez göndermez)
                        →  alıcının posta kutusu (09:00)  →  alıcı gruba paylaşır
```

### 1 · Çalışan tablosu

- Başlangıçta Google Drive'da bir Excel dosyası; **Bahadır Bey günceller** (Kağan). Sonra sunucudaki PostgreSQL'de
  bir tabloya taşınır; okuma katmanı tek fonksiyonda tutulur ki kaynak değişince yalnız o değişsin.
- Sütunlar: `Ad Soyad` · `Ünvan` · `Doğum günü` (gün.ay) · `İşe giriş tarihi` (gün.ay.yıl).
- Drive erişimi: dosya bir Google servis hesabıyla **yalnız görüntüleme** paylaşılır; betik Drive API'siyle indirir
  (`drive.readonly` kapsamı), openpyxl ile okur. Servis hesabı anahtar dosyasının yolu ve dosya kimliği `.env`'de.
  Betik dosyaya yazmaz (Claude'un çağrısı). Drive'a ulaşılamazsa o gün tebrik yerine "tablo okunamadı" maili gider.
- Doğrulama: boş ad, tanınmayan tarih biçimi, olmayan gün (31.02) → o satır atlanmaz, **eksikler listesine** girer.
  Eksikler listesi her ayın ilk iş günü mailine ve o satırın tebriğinin olacağı günün mailine eklenir.

### 2 · Hangi gün

- **Doğum günü:** gün ve ay bugüne eşit. 29 Şubat doğumlular artık olmayan yıllarda 28 Şubat'ta (Claude'un çağrısı).
- **İşe yeni başlayan:** işe giriş tarihi bugün (yıl dahil). Hoş geldin yalnız ilk gün gider; yıl dönümü kutlanmaz.
- **Bayramlar:** hangi bayramlar olacağını Kağan bildirecek. Her bayramın kendi şablonu ve metni olur; çok günlü
  bayramda tebrik yalnız ilk gün gider (Claude'un çağrısı). Dini bayramların tarihi her yıl değişir; tarihler
  bir takvim dosyasında (`tebrik/bayramlar.json`, git'te) yıllık elle girilir — betik hesaplamaz. Takvimde gelecek
  yılın tarihleri yoksa aralık ayında alıcıya hatırlatma gider.
- Hafta sonu ve tatil günleri de gönderilir; gün kaydırılmaz (Claude'un çağrısı — kişinin günü o gün).

### 3 · Görsel

- Her tür için bir **adsız şablon** PNG (`tebrik/sablonlar/`). Şablonları Claude, Kağan'ın örnek görsellerinin
  tarzında (lacivert ağırlık, krem/altın doğum günü, mavi ışıklı ofis hoş geldin) Gemini'nin görsel modeliyle
  **bir kez** üretir; üzerinde hiç yazı olmaz. **Kağan her şablonu onaylar; onaysız şablon kullanılmaz.**
- Logo: Kağan'ın masaüstündeki `linkedinNewLogo.png`'deki beyaz "Nove" yazısı zeminden ayrılıp şeffaf PNG yapılır; altına "Group" benzer
  bir yazı tipiyle eklenir. Logo hiçbir zaman yapay zekâya çizdirilmez.
- Yazılar Pillow ile basılır: her şablon için sabit yazı tipi, boyut, renk ve kutu (`tebrik/sablonlar/<tur>.json`).
  Uzun ad kutuya sığmazsa yazı küçülür, sonra iki satıra bölünür; yine sığmazsa görsel üretilmez, eksikler listesine
  girer (Claude'un çağrısı). Yazı tipleri Türkçe harfleri tam desteklemeli; test her Türkçe harfin glif olarak
  basıldığını doğrular.
- Sabit metinler: doğum günü örnekten — "Yeni yaşınızda, tüm hayallerinizin gerçeğe dönüşmesini dileriz." /
  "In your new age, we wish all your dreams come true." Hoş geldin: "Welcome to the Team!" + ad + ünvan.
  Bayram metinleri bayram listesiyle birlikte Kağan'dan gelir.

### 4 · Mail

- Gönderen: bu iş için açılacak ayrı bir Nove adresi (Kağan onayladı). SMTP sunucusu, port, kullanıcı ve uygulama
  şifresi `.env`'de; TLS zorunlu. Sağlayıcı (Google Workspace ya da başka) BT'den öğrenilir; kod yalnız SMTP konuşur.
- Alıcı: `.env`'de tek adres. Betik alıcıda virgül, birden fazla adres ya da `@nove.group` dışı alan adı varsa
  reddeder; alan adı kodda sabittir (şirket adresleri `nove.group`) (Claude'un çağrısı).
- O gün tebrik yoksa ve eksik yoksa **mail gitmez**.
- Bir mailde o günün bütün tebrikleri: her biri ayrı ek PNG, gövdede kim için ve hangi metinle paylaşılacağı.
- Betik her gün 08:55'te koşar ve hemen gönderir; mail 09:00'dan önce ulaşır.
- Gönderim kaydı `sirket-log/tebrik/YYYY-MM-DD.json` (git'e girmez; ad içerir). **Her koşu kayıt yazar**, tebrik
  olmayan günde de (`durum: bos`). Sıra: önce gönder, sonra kaydı yaz; kayıt yazılamazsa betik hata koduyla çıkar ve
  günlüğe yazar (ikinci gönderimi önlemek için ertesi koşu SMTP "gönderildi" izini değil kaydı esas alır). Aynı gün
  kayıt `gonderildi` ise ikinci gönderim yok.
- Geç koşu (makine 09:00'da kapalıydı, launchd açılışta koşturdu): **aynı gün içindeyse gönderilir**, mailin başına
  "geç gönderildi" notu düşer. Ertesi güne kalan tebrik **gönderilmez**: önceki gün için kayıt yoksa, o günün
  tebrikleri yeniden hesaplanır ve bugünün mailinde "dün kaçan tebrikler: <adlar>" notu olarak yalnız alıcıya
  bildirilir; görselleri eklenmez (Claude'un çağrısı).
- `--kuru`: mail atmadan görselleri ve mail metnini klasöre yazar; Kağan ve alıcı önizler.

### 5 · Zamanlama ve panel

- Mac'te `bin/zamanla.py`'ye dördüncü takvimli iş: her gün 08:55 `bin/tebrik_postasi.py`. Sunucuda aynı komut cron'la.
- Panelde Tebrik Danışmanı kartı: son gönderim tarihi, bugün kaç tebrik, eksikler sayısı. Panel kayıtları değil,
  betiğin ayrıca yazdığı **adsız özet** `sirket-log/tebrik/ozet.json`'u okur (Claude'un çağrısı).

## Kurulum için gerekenler (insan işi)

| Ne | Kim | Durum |
|---|---|---|
| ANAYASA §1 istisnası | Kağan | metin onaylı, eklenmedi |
| Bayram listesi ve metinleri | Kağan | bekliyor |
| Ayrı gönderen Nove adresi + uygulama şifresi | BT / yazılımcı | bekliyor |
| Excel dosyası (dört sütun) ve Drive paylaşımı | Bahadır Bey | bekliyor |
| Gemini anahtarı (yalnız şablon üretimi için, bir kez) | Kağan | bekliyor |
| Şablon onayları | Kağan | şablonlar üretilince |

## Builder'a bırakılanlar

- Dosya ve fonksiyon düzeni, Pillow yerleşim kodu, Drive okuma kütüphanesi seçimi (stdlib ile yapılamıyorsa en az
  bağımlılık).
- Mail biçimi (düz metin + ekler yeterli).
- Testler: tarih eşleştirme (29 Şubat dahil), doğrulama ve eksikler listesi, tek gönderim, kaçan gün, alıcı
  doğrulaması, ANAYASA istisnası yoksa ret, Türkçe harf basımı, sığmayan ad. Testler sahte veriyle; gerçek ad yok.
