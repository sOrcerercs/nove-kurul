# Nove AI paneli

Kurul üyelerinin giriş yaptığı ve soru sorduğu arayüz. Ayrıntılar: `../NOVE-KURULUM.md` §8c.

Akış: dönen dünya ve e-posta + şifre formu → "Hoş geldin, <ad>" → Kurul Ofisi (3D ofis, soru akışı, ajan kartı, Yanıt defteri).

| Dosya | İçerik |
|---|---|
| `index.html` | Giriş sahnesi ve Kurul Ofisi işaretlemesi |
| `stil.css` | Renk/yazı belirteçleri, sahne ve panel stilleri |
| `panel.js` | Dünya ve geçişler, giriş (`POST /api/giris`), soru akışı, ajan kartı, Yanıt defteri |
| `ofis3d-v4.js` | 3D ofis; Claude Design "Nove Kurul Ofisi 3D v4"ten birebir. Three.js 0.160'ı unpkg'den yükler (internet gerekir) |

## Yerelde açmak

```bash
python3 bin/panel.py
# tarayıcıda: http://127.0.0.1:8770   (demo: http://127.0.0.1:8770/?demo)
```

- `bin/panel.py` `panel/` dosyalarını ve API'yi aynı adresten (`127.0.0.1:8770`) sunar.
- Bayraklar: `--port N` · `--ilerletme-yok` (arka plan ilerleticisini kapatır) · `--https-arkasinda` (çerez `Secure` olur) ·
  `--kullanici-ekle <eposta> --ad "<ad>"` (kullanıcı ekler; Claude Code ortamında reddedilir, kendi terminalinde koşturulur).
- `?demo` ile ya da dosyayı çift tıklayarak açınca **demo modu**: her e-posta ve şifre kabul edilir, `#ofis` girişi atlar.
- `?demo` olmadan açınca form `POST /api/giris`'e gider; gerçek modda soru, bekleme ekranı ve Yanıt defteri canlıdır.

## Sunucu sözleşmesi (`bin/panel.py`)

- `POST /api/giris` `{"eposta","sifre"}` → `200 {"ad","basHarf","rol"}` + oturum çerezi · `401` yanlış bilgi · `429` çok deneme
- `POST /api/cikis` → oturumu kapatır
- `GET /api/ben` → oturumdaki kullanıcı (`ad`, `basHarf`, `rol`) · `401` oturum yok
- `POST /api/soru` → soruyu Q&A kapısından geçirip kaydeder; soru kimliğini döner
- `GET /api/sorular/<id>` → sorunun durumu, `asama` (sabit sekiz ad, bu sırayla: `qa_al`, `dagit`, `analiz`, `denetim`, `ceo_sorgu`, `revize`, `ceo_onay`, `qa_ilet`; yalnız gerçekleşenler) ve `danisman`; başkasının sorusu `404`
- Gerçek modda sahne, yoklamadaki aşamalarla gerçek sırayla oynar (`sahne-sira.js`); sayfa yenilenince yalnız son aşama gösterilir, geçmiş aşamalar baştan oynamaz.
  Bilinen sınır: `onaylanamadı` biten sorudan sonra sahnenin boşta gezintileri bir sonraki tamamlanan akışa ya da yenilemeye kadar durur (`ofis3d-v4.js` değişmedi).
- `GET /api/yanitlar` → Yanıt defteri, role göre süzülür (kurul yalnız kendi sorularını görür)
- Durum yoklaması 10 sn'de bir yapılır. SSE (`GET /api/olaylar`) Faz 7'de.
- Arka plan ilerleticisi: açık soru varken her ~60 sn'de bir İş Dağıtımcı adımı koşturur; `.kos.lock` doluysa atlar, bir adımdan
  sonra en az 15 sn (`ASGARI_ARA_SN`) bekler.
- Şifre: scrypt, yoksa PBKDF2-SHA256 (600 000 tur; kayıtta `yontem`). `deploy/kullanicilar.json` git'e girmez, izni `600`.
  Oturumlar bellekte, 12 saat. Fren: aynı e-posta ya da IP için 15 dk'da 5 hatalı giriş (dev'de bütün istekler `127.0.0.1`).
- Kurulmamış bölüme giden soru koşusuz `onaylanamadı` ("Bu bölüm henüz kurulmadı") olarak deftere girer. Onaylanamayan
  yanıtlarda kurul kısa sebebi, yönetici ham gerekçeyi görür.
