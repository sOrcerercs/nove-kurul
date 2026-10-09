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
cd panel
python3 -m http.server 8000
# tarayıcıda: http://127.0.0.1:8000/?demo
```

- `?demo` ile ya da dosyayı çift tıklayarak açınca **demo modu**: her e-posta ve şifre kabul edilir, `#ofis` girişi atlar.
- `?demo` olmadan açınca form `POST /api/giris`'e gider. `bin/panel.py` yazılana kadar "Giriş şu an yapılamıyor" mesajı görünür; bu beklenen davranış.

## Sunucu sözleşmesi (`bin/panel.py`)

- `POST /api/giris` `{"eposta","sifre"}` → `200 {"ad","basHarf","rol"}` + oturum çerezi · `401` yanlış bilgi · `429` çok deneme
- `POST /api/cikis` → oturumu kapatır
- Soru akışı şu an `panel.js` içindeki demo verisiyle dönüyor; Faz 5'te `GET /api/olaylar` (SSE) olaylarına bağlanacak.
