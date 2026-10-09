# Q&A DANIŞMANI — Nove Kurul Ofisi'nin giriş ve çıkış kapısı

> Q&A Danışmanı'nın (`bin/soru_kapisi.py`) insan-okur tanımı. Kurul üyesinin sorusu sisteme buradan girer,
> onaylı yanıt kurula buradan çıkar.
> **Bu dosya insanındır; ajan değiştirmez** (ANAYASA §5). Kural yanlışsa Kağan değiştirir.
>
> Durum: **taslak — Kağan'ın revizesini bekliyor** · Dayanak: `NOVE-KURULUM.md` §1, §2 (adım 1 ve 8), §8, §8b, §9,
> Faz 3; Claude Design *Nove Kurul Ofisi 3D v4* (ajan kartı ve sahne balonları). Belgede olmayan kurallar
> *(öneri)* diye işaretli.

---

## Sen kimsin

Sahnede bir danışman gibi görünürsün ama **ajan değilsin, sürücüsün**: LLM çağırmazsın, para harcamazsın.
Arkanda `bin/soru_kapisi.py` çalışır; `kagan-sirketi`'ndeki `telegram_dinle.py` ile `sahne.py`'nin soru
POST'unun birleşimidir (§1).

Neden LLM'siz: kagan-sirketi'nin kuralı "dağıtıcı LLM çağırmaz". Giriş kapısı ucuz ve deterministik olmalı;
her soru aynı kurallarla, aynı sırayla kayda girer.

**Yetkin:** Kayıt açarsın · **yanıt üretmezsin.** *(tasarımdaki ajan kartı)*

## Görevlerin — giriş (adım 1)

Kurul üyesi panelde "Soruyu gönder"e basınca `panel.py` soruyu `gelen/<soru-id>.json` olarak yazar
(`POST /api/soru`). Sen `--dinle` modunda bu klasörü izlersin ve her soruyu sırayla şu adımlardan geçirirsin:

### 1 · Soranı belirle
Soran, panel oturumundaki **e-posta**dır (N11); soru metninde yazan bir ad değil. Rolü `deploy/roller.json`'dan
okursun. `kurul` ya da `yonetici` olmayan kimseden soru almazsın.

### 2 · Ön kontroller — hepsi deterministik
Bir kontrol takılırsa soru bekletilir ya da geri döner ve soran sebebini panelde görür.
Hiçbir soru sessizce düşmez.

| Kontrol | Takılırsa | Dayanak |
|---|---|---|
| **Mesai** 08:00–20:00 | Soru kayda girer ama sabaha bekler; panelde "mesai dışı — sabah işlenecek" | §9 |
| **Kişi başı günde 10 soru** | 11. soru kayda girmez; panelde "bugünkü soru hakkın doldu" | §9 (tavan) · davranış *(öneri)* |
| **Şirket günü 40 USD** doldu | Soru kayda girer ama ertesi güne bekler; panelde sebebi görünür | §9 (tavan) · davranış *(öneri)* |
| **Boş ya da çok kısa soru** | Kayda girmez; panelde "soruyu biraz açar mısın" | *(öneri)* |
| **Aynı kişi, aynı soru, 10 dakika içinde** | İkinci kayıt açılmaz; ilk sorunun durumu gösterilir | *(öneri)* |

### 3 · Maskele
Soru metninde kişisel veri varsa kayda **maskelenmiş** hâliyle yazarsın (§2 adım 1, ANAYASA §2):
e-posta, telefon numarası, TC kimlik numarası → `[e-posta]`, `[telefon]`, `[tc-no]`. Desenler Denetçi'nin
ön kontrolüyle **aynıdır** (`sirket/DENETCI.md`); iki yer ayrı desen kullanmaz *(öneri)*. Maskeleme yapıldıysa
soru kaydına "maskelendi: telefon (1)" gibi bir satır düşersin; maskelenen değeri hiçbir yere yazmazsın.

### 4 · Kaydı aç
- `gelen/<soru-id>.json` — sorunun ham hâli (maskelenmiş metin, soran, zaman).
- `sirket-log/sorular/<soru-id>.md` — **soru kaydı.** Sorunun bütün hayatı bu dosyada toplanır: kimin ne yaptığı,
  dağıtım gerekçesi, Denetçi ve CEO kararları, maliyet (§2). Senin yazdığın ilk bölüm:

```markdown
# Soru <soru-id>
- soran: <e-posta> (rol: kurul)
- zaman: 2026-10-09 14:32
- soru: Q3 bütçe sapmasının ana nedenleri neler?
- bütçe: 5,00 USD
- durum: alındı
```

- `soru-id` biçimi *(öneri)*: `YYYYMMDD-HHMM-<4 harf>` — sıralanabilir ve panelde okunabilir.
- Her soru **5 USD** bütçe taşır (§9). Bütçeyi kayda sen yazarsın; harcamayı sürücü işler.

### 5 · İş Dağıtımcı'ya teslim et
Soruyu `bin/dagitici.py`'ye verirsin. Hangi danışmana gideceğine **sen karar vermezsin** (`sirket/IS-DAGITIMCI.md`).

### 6 · Paneli haberdar et
Her durum değişikliğini `panel.py`'nin olay akışına (SSE) yazarsın; soran sorusunun nerede olduğunu canlı görür.
Sahnede balonun: **"Kurul sorusu alındı"**, ardından **"Dağıtıma götürüyor"** *(tasarım)*.

## Görevlerin — çıkış (adım 8)

`soru_kapisi.py --ilet <soru-id>` bir yanıtı kurula iletir. İletmeden önce soru kaydına bakarsın:

### 7 · İki imzayı kontrol et
| Soru kaydında | Ne yaparsın |
|---|---|
| Denetçi `kabul` **ve** CEO `onay` | Yanıtı soranın masasına ve Yanıt defterine iletirsin (aşağıda) |
| CEO iki kez `red` | Yanıt gitmez. Soranın panelinde **"onaylanamadı"** etiketi ve **CEO'nun gerekçesi** görünür (§2) |
| Denetçi `red`/`atlandi` (sonuçlanmadı) | Yanıt gitmez. Soranın panelinde "onaylanamadı" ve Denetçi gerekçesi *(öneri; belgede tanımlı değil)* |
| CEO kapalı (yalnız geliştirme ortamı) | Yanıt **"CEO kontrolü yapılmadı"** etiketiyle gider (§5) |
| Soru bütçesi aşıldı | Panelde soranına gösterilir (ANAYASA §4); yanıt varsa ve iki imzası tamamsa yine iletilir *(öneri)* |

**Bir imza eksikse iletmezsin.** Bu senin değil sürücünün kuralı da olsa son kapı sensin; kayıtta iki imza
görmeden hiçbir şeyi kurula taşımazsın (ANAYASA §3).

### 8 · İlet
- **Soranın masasına:** panelde yalnız soranın görebileceği şekilde (N10). CEO'nun `kurula_not`'u varsa yanıtın başına eklenir.
- **Yanıt defterine:** `yanit_defteri.py` ile — soru, soran, tarih, cevaplayan danışman, Denetçi ✔, CEO ✔, yanıt metni,
  kaynaklar (§8b). Onaylanamayan sorular da "onaylanamadı" etiketiyle deftere girer. Deftere **yalnız sürücü yazar**;
  kayıt silinmez, değiştirilmez.
- Soru kaydında `durum: iletildi` ve iletim zamanı.
- Sahnede: **"Yanıt kurula gidiyor"** → kurul masasına yürüyüş → **"Kurula iletildi ✓"** *(tasarım)*.

## Asla

- **Yanıt üretmek ya da yanıtı değiştirmek.** Danışmanın onaylı metnini olduğu gibi iletirsin.
- **Sorunun anlamını değiştirmek.** Maskeleme dışında soru metnine dokunmazsın.
- **Kurul dışına iletmek.** Bölüm yöneticisine kopya, mail, mesaj yok — bu bir "yayın" olur (ANAYASA §1, S6).
- **Başka birinin sorusunu ya da yanıtını göstermek.** Kurul üyesi yalnız kendi sorularını görür (N10).
- **Yanıt defterinde kayıt silmek ya da düzeltmek.**
- **Maskelenen kişisel veriyi herhangi bir yere yazmak** — log, telemetri, hata mesajı dahil.

## Hata olursa

- Kayıt açılamadı, dağıtıcıya ulaşılamadı, panel olayı yazılamadı → soru **kaybolmaz**: `gelen/`'de kalır, soru kaydına
  `durum: hata` ve tek cümle sebep yazılır, panelde soranına "sorun işlenemedi, yeniden denenecek" görünür *(öneri)*.
- Sessiz düşme yoktur. Takılan her soru ya kayıtta ya panelde görünür.

## Sınırların

| | Değer | Kaynak |
|---|---|---|
| Model | **yok** — LLM çağrılmaz | §1 |
| Maliyet | 0; tavanlara sayılmaz | §1, §9 |
| Çalışma biçimi | systemd `nove-dinleyici.service` → `soru_kapisi.py --dinle` | §8 |
| Elle kullanım (Faz 3) | `--yeni "<soru>" --soran <kişi> [--kuru]` · `--ilet <soru-id>` | §10 |

## Açık nokta — "netleştirme"

Tasarımdaki ajan kartı "soruları karşılar, **netleştirir** ve onaylı yanıtı kurul masasına götürür" diyor; akış
panelinde 1. adım "Soru netleştirildi, kayıt açıldı" yazıyor. Belge ise Q&A Danışmanı'nın **LLM çağırmadığını**
söylüyor (§1). İki yorum var:

1. **Netleştirme = deterministik ön kontroller** (yukarıdaki 2. ve 3. adım). LLM yok, belgeyle uyumlu.
2. **Netleştirme = belirsiz soruda kurul üyesine geri soru sormak.** Bu bir LLM ya da insan gerektirir ve belgenin
   §1 kararını değiştirir.

Bu dosya şimdilik **1. yorumu** uyguluyor. Karar Kağan'ın.
