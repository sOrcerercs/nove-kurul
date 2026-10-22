# Kalite günlük raporu — tasarım

> Durum: **onaylı** — Kağan, 22.10.2026 (4 karar aşağıda)
> Dayanak: `takimlar/kalite/takim.md` "Tempo" (Kağan, 19.10.2026) · bağımlılık: PR #9 (Kalite veri okuyucusu) merge edilmeli.
> Herkese açık depo: bu belgede çalışan adı yok.

## Amaç

Pazartesi–cuma her gün, saat **11:00'de** kurula ulaşan günlük kalite raporu (Kağan):
- Salı–cuma: bir önceki günü kapsar.
- Pazartesi: cuma + cumartesi + pazar'ı kapsar.
- İçerik: ekip bazında kalite puanı ve değişimi, en sık kaçırılan kriterler, koçluk takibi.
- Kurul yanıtı düzeninde yazılır; Denetçi ve CEO onayından geçer.

## Bugünkü sistemde engel (ölçüldü)

- Zamanlı iş (`gunluk.ZAMANLI`) yalnız kuyruğa madde düşürür. Ama danışman koşusu, Denetçi'den sonra CEO ve Yanıt defterine
  iletim **yalnız soru kaydı** (`sirket-log/sorular/<id>.md`) üzerinden ilerliyor (`kos.SORU_MADDESI`, `ceo.kontrol_et`,
  `soru_kapisi.ilet`). Soru olmayan bir rapor maddesi kuyrukta `bekliyor` kalır, CEO'ya ve kurula hiç ulaşmaz.
- Dağıtıcı günde bir kez (sabah tetiği, 08:00) çalışıyor. Zincir (danışman → Denetçi → CEO → iletim) her dağıtıcı turunda
  bir adım ilerliyor; 11:00'e yetişmesi için gün içinde ek turlar gerekiyor.

## Tasarım (Claude'un önerisi)

### 1 · Rapor bir "sistem sorusu"dur

Zamanlayıcı her iş günü, raporu **soru kaydı olarak** açar. Böylece mevcut iki imzalı zincir (Denetçi + CEO) ve Yanıt defteri
olduğu gibi kullanılır; yeni bir onay yolu yazılmaz.

- Yeni fonksiyon `soru_kapisi.sistem_sorusu(kok, soru, danisman, simdi)`. Rol kontrolü ve soran başına günlük sınır **yok**,
  çünkü soran bir insan değil. `- soran: Zamanlayıcı (kalite günlük raporu)` yazılır. `## Dağıtım` doğrudan `kalite` olarak
  yazılır, Haiku yönlendirmesi atlanır. `s-<id>` kuyruğa düşer.
- Soru metni sabit şablondan üretilir, tarih aralığı içinde yazılı. Örnek: "21.10.2026 (Çarşamba) günlük kalite raporu: ekip bazında
  ortalama ve önceki dönemle farkı, en sık kaçırılan 5 kriter, koçluk takibi. … Aralık: 20.10.2026–20.10.2026 ·
  Karşılaştırma: 19.10.2026–19.10.2026." Aralığı ajan değil, zamanlayıcı hesaplar; Denetçi ve CEO aralığı metinde görür.
- Aynı gün ikinci kez açılmaz: id gün taşır (`rapor-kalite-YYYYMMDD`). Kayıt varsa atlanır.

### 2 · Zamanlama

| Tetik | Saat | Ne yapar |
|---|---|---|
| `rapor` (yeni) | Pzt–Cum **09:30** | Bugünün sistem sorusunu açar, dağıtıcıyı çalıştırır |
| `ilerlet` (yeni) | Mesai içinde her **10 dk** | Yalnız `dagitici.dagit()`: zinciri bir adım ilerletir (soruların da işine yarar) |

- 09:30 → danışman (≤ 15 dk) → Denetçi → CEO (≤ 5 dk) → iletim: olağan durumda 10:15 civarı biter. CEO reddi ve bir düzeltme
  turunda da 11:00'e yetişir.
- 11:00'de hâlâ iletilmemişse rapor iletilmez ama **kaybolmaz**: soru kaydı yerinde kalır, zincir bitince iletilir.
  Kayda `- gecikti: <saat>` düşülür.
- Hafta sonu tetik çalışmaz; launchd'de hafta günü alanıyla kurulur (`Weekday` 1–5).
- **Resmî tatilde rapor gitmez** (Kağan, 22.10.2026). Tatiller `takimlar/kalite/tatiller.json`'da yıllık elle tutulur
  (`[{"tarih": "YYYY-MM-DD", "ad": "..."}]`); Claude hazırlar, Kağan onaylar. Takvimde gelecek yıl yoksa aralığın ilk iş
  günü raporuna "tatil listesi eksik" notu düşer.
- **Rapor aralığı:** bir önceki iş gününden (dahil) dünkü güne kadar. Salı → pazartesi; pazartesi → cuma..pazar;
  29 Ekim perşembe tatilse 30 Ekim cuma → 28..29 Ekim.
- **Karşılaştırma aralığı** (Kağan: önceki eşit dönem): aralık tek günse bir önceki iş günü (salı raporu: pazartesi ↔ cuma);
  birden çok günse aynı takvim aralığı 7 gün geriye (pazartesi raporu: cuma..pazar ↔ bir önceki cuma..pazar).

### 3 · Rapor içeriği

Danışman yalnız `bin/kalite_veri.py`'yi kullanır (izinli komut):
- `ekip-ozet --baslangic <a> --bitis <b> --karsilastir-baslangic <c> --karsilastir-bitis <d>`
- `kriterler` (en sık kaçırılan)
- `kocluk` (yapılan, okunan, okunmayan)

Düzen `kurul-yaniti`: Kısa yanıt · Dayanak · Bilinmeyenler · Not. Örneklem 15'in altındaki ekip yorumlanmaz.

### 4 · Kurula ulaşma

Onaylanan rapor `soru_kapisi.ilet` ile **Yanıt defterine** (`yanitlar/<id>.md`) yazılır. Panelde görünmesi Faz 5'te
(`bin/panel.py`, `GET /api/yanitlar`) gelir. O zamana kadar rapor Yanıt defterinde ve sabah/akşam sistem raporunda görünür.

## Claude'un çağrıları (okuyucu kontrolünden, 22.10.2026)

- **Aralık yapısal alan olarak taşınır.** Soru kaydına `- aralik: YYYY-MM-DD..YYYY-MM-DD` ve
  `- karsilastir: YYYY-MM-DD..YYYY-MM-DD` satırları eklenir. Danışman komut argümanlarını bu satırlardan alır, düzyazıyı
  ayrıştırmaz. Mevcut okuyucular (`kos`, `ceo`, `soru_kapisi`) bilmedikleri satırları yok sayar.
- **Gün hesabı:** "dün" ve "cuma–pazar" İstanbul takvim gününe göre hesaplanır. Veri, betiğin UTC gün sınırıyla okunur;
  bu Raporlarım'ın kuralıyla aynıdır. Rapordaki rakam, panelde aynı tarihlerle bakılan rakamla tutar.
- **Komutlar mevcut:** `ekip-ozet` (`--karsilastir-baslangic/--karsilastir-bitis`), `kriterler` ve `kocluk` tarih aralığı
  alıyor (PR #9). `temsilci-ozet` az örneği `az_ornek=evet` ile işaretliyor. Yeni veri komutu gerekmez.
- **Tetikler `bin/zamanla.py`'de:**
  - `rapor`: `StartCalendarInterval` dizisi, Weekday 1–5, 09:30.
  - `ilerlet`: `StartInterval` 600 sn. Mesai dışında dağıtıcı bir şey başlatmaz (`tetik_karari` mesai kontrolü).
    Mesai (`ayar.mesaide_mi`) haftanın her günü 08–20'dir: hafta sonunda `ilerlet` kuyrukta bekleyen işi (ör. kurul
    sorusu) ilerletir; kuyruk boşsa maliyeti yoktur.
  - Mac 09:30'u uykuda geçirip ertesi gün uyanırsa o günün raporu geriye dönük açılmaz; aynı gün elle
    `python3 bin/gunluk.py --rapor` ile açılır.
- **Çakışma:** `kos.py` koşuları `.kos.lock` (`fcntl.flock`) ile sıraya giriyor. İki tur üst üste gelirse ikinci danışman
  koşusu bekler, aynı anda çift koşu olmaz. Kuyruk maddesi `yapiliyor` iken dağıtıcı onu yeniden başlatmaz.
- **Başarısızlık:** CEO iki kez reddederse mevcut kural geçerli. Rapor Yanıt defterine "onaylanamadı" etiketi ve CEO
  gerekçesiyle gider. Ayrı bir uyarı kanalı yok; durum akşam sistem raporunda görünür.
- **Tekrar:** O günün kaydı varsa rapor yeniden açılmaz. Takılan zincir, mevcut dağıtıcı turlarıyla ilerlemeye devam eder.
- **Bütçe:** rapor başına mevcut soru bütçesi (8 USD) geçerli. Günlük şirket tavanı (40 USD) içinde kalır.

## Kağan'ın kararları (22.10.2026)

1. **Değişim:** önceki eşit dönem (yukarıdaki karşılaştırma aralığı).
2. **Görünürlük:** kurulun hepsi. Sistem sorusu Yanıt defterinde `- gorunurluk: kurul` satırı taşır; panel (Faz 5) bu
   satırı okuyup herkese gösterir.
3. **Tatil:** rapor gitmez; tatilden sonraki ilk iş günü raporu tatil günlerini kapsar.
4. **Maliyet:** uygun (rapor başına tavan 8 USD, beklenen ayda 40–90 USD).

## Hedef olmayanlar

Mail ya da mesaj ile gönderim (ANAYASA §1), panelde canlı kart (Faz 5), haftanın çağrısı (`WeeklyBestCall` izni verilmedi).

## Builder'a bırakılanlar

Fonksiyon düzeni, test ayrıntıları, `ilerlet` tetiğinin launchd biçimi (`StartInterval`).
