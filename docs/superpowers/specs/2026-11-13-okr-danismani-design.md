---
durum: yazildi
guncelleme: 2026-11-13
dal: feature/okr-danismani
pr: -
bekleyen: -
onay: Kağan, 13.11.2026 (O3 tanıma kuralı, B1a ve B2a dahil)
---

# OKR Danışmanı — Tasarım

> Faz 6. Kararlar Kağan'la 13.11.2026'da verildi. Spec 13.11.2026'da Kağan'la birlikte gözden geçirildi ve onaylandı.
> Herkese açık depo: çalışan adı ve e-posta yok.

## Amaç ve neden

Kurul üyeleri Nove PYS'deki (Nove Performance, `noveperformance1.vercel.app`) OKR verisi hakkında **hızlıca bilgi
almak** istiyor: siteyi gezip tablolara bakmak yerine panelden tek cümleyle sorup kısa yanıt almak (Kağan). Örnek:
"Satış'ın bu çeyrekteki OKR durumu ne?", "Hangi KR'lar geride?", "Hangi KR'ların bu dönem hiç verisi yok?",
"Şirket genelinde hedeflerin yüzde kaçı yolunda?".

Kalite Danışmanı'nın yolu izlenir: danışman veriyi tek bir salt okunur okuma betiğinden (`bin/okr_veri.py`) ister,
hesabı betik yapar, danışman tabloyu okur ve kaynağıyla yazar. Yanıt bugünkü hattan geçer (Q&A → İş Dağıtımcı →
zorluğa göre model → Denetçi → CEO → panel).

**Başarı:** Danışmanın verdiği ilerleme yüzdesi, sitenin aynı dönem ve bölüm için gösterdiği yüzdeyle **aynıdır**
(Kağan sitedekiyle yan yana karşılaştırarak teyit eder) ve yanıtta dönem, son dolu ay ve her `—`'nin sebebi yazar.

## Kararlar (Kağan, 13.11.2026)

- O1. **Veri:** Nove PYS'nin Supabase Postgres'i, **`okr_okuyucu`** rolüyle salt okunur. Kurulum yapıldı ve
  doğrulandı (13.11): oturum `default_transaction_read_only = on`, `statement_timeout = 15s`; okuma izni
  `departments, periods, objectives, key_results, checkins, kr_monthly_values` ve `users`'ta yalnız
  `id, name, role, department_id, manager_id, title, state`; e-posta, parola özeti, `login_attempts`,
  `help_articles` kapalı; `app_settings`'te yalnız `default_range_start` satırı — **bu izin henüz verilmedi**, O8'deki SQL'i Kağan çalıştırır. Tablolarda RLS açık; yalnız bu role `okr_okuyucu_okur` SELECT politikası.
  Bağlantı `.env`'de **`OKR_READONLY_URL`** (Session pooler). Ölçüm 13.11: 11 bölüm, 3 dönem, 55 objective,
  118 KR, 439 aylık değer, 105 kişi, **0 check-in**.
- O2. **Görünürlük:** kurul üyeleri bütün departmanları sorabilir; departman kısıtı yok. Panelin mevcut kuralı
  (üye yalnız kendi sorusunu ve kurula açık yanıtları görür) aynen geçerli.
- O3. **Oran KR'ları** (07, 11, 38, 42, 43, 44, 45, 56): sitede `avg` = aylık oranların düz ortalaması, gerçek
  orandan sapabilir (pay/payda saklanmıyor; Nove Performance `2026-08-10-excel-okr-aktarimi-design.md`). Danışman
  **sitedeki sayıyı verir** ve yanına not düşer: *"aylık oranların ortalaması; ayların hacmi farklıysa gerçek
  orandan sapabilir"*. Gerçek oranı hesaplamaya çalışmaz (veri yok).
  **Tanıma kuralı (benim kararım, 13.11):** Excel satır numaraları veritabanında yok. Not, `rollup = 'avg'` ve
  `unit = '%'` olan **her** KR'a düşülür (13.11'de 2025-FY'de 17, 2026-FY'de 1 KR; canlı ölçümle teyit). Fazla eşleşme zararsızdır:
  aylık yüzdelerin düz ortalaması her bu tür KR'da aynı sapmayı taşır; eksik eşleşme ise anti-hedeftir.
- O4. **Tempo yok:** şimdilik yalnız sorulara yanıt; zamanlanmış rapor kurulmaz.
- O5. **Sahip ve teyit:** Kağan. Formda yönetici ve "sayıyı kim teyit eder" Kağan.
- O6. **Bütçe sapması Finans'ındır**, OKR'a yönlenmez (form §2'deki "gelmemesi gereken" listesi).
- O7. **Ana yüzde StD:** yanıtın başındaki yüzde sitenin rozetlerindeki `statusPct = std ?? annual`'dır
  (`lib/queries/std.ts:16-25,48`); yıllık yüzde yanında verilir. Kağan'ın karşılaştırması bu sayı üzerinden.
- O8. **Varsayılan aralık siteyle aynı:** soruda dönem yoksa aralık `default_range_start` → bugün (sitenin açılış
  görünümü; satır yoksa ya da bozuksa `2025-09-01`, `lib/queries/settings.ts`). Bunun için `okr_okuyucu`'ya
  `app_settings`'te yalnız bu satırı okuyan izin ve `okr_okuyucu_aralik` politikası verilir (Kağan çalıştırır).
  Aralık iki mali yılı kapsıyorsa site gibi birleştirir (`lib/queries/range.ts:40-47`) ve yanıtta bunu söyler.

## Benim kararlarım (Kağan okurken kontrol etsin)

- B1. **Hesap sitenin kodundan birebir taşınır.** İlerleme veritabanında hazır durmuyor; site her açılışta
  hesaplıyor. `okr_veri.py` şu kuralları Nove Performance'tan Python'a taşır, kendi kuralını icat etmez:
  `lib/domain/progress.ts` (krPct 0–140 kırpma ve yuvarlama, `sum` için başlangıç 0, ölçülemez KR ortalamaya
  girmez, objective/bölüm ağırlıklı ortalama yalnız ağırlık seti tamamsa), `monthly.ts` (dönemin ayları, dolu ay
  sayısına bölen `avg`, `last`, taşınan değer), `weights.ts`, `std.ts` (sezon başından bugüne), `fiscal.ts` ve
  `dates.ts` (mali yıl Eylül'de başlar). Sitenin `__tests__` altındaki test vektörleri Python testlerine kopyalanır;
  aynı girdi aynı sayıyı vermek zorunda. Yuvarlama JS `Math.round` ile aynı olmalı (Python `round` banker
  yuvarlaması yapar — farklı; `bin/kalite_veri.py`'deki `js_yuvarla` kullanılır).
  Taşınacaklara `lib/queries/tree.ts` ve `lib/queries/std.ts` de dahildir (inceleme, 13.11): kesim tarihi
  `min(aralık sonu, bugün İstanbul)` (`lib/domain/dates.ts:56-59`, `asOfCutoff`); KR'ın kendi döneminde aylık satırı yoksa saklı
  `key_results.current`'a düşüş (`tree.ts:209-256`); kesime kadar ölçülmemiş KR'ların dışlanması
  (`tree.ts:331-356`). Sayılar ve testleri bu dosyalardan da kopyalanır.
- B1a. **Site değişirse (onay 13.11):** taşınan her hesap bloğunun başında sitedeki karşılığı yazar — dosya yolu,
  satır aralığı ve Nove Performance deposunun taşındığı andaki commit kısaltması. Danışmanın `kurallar.md`'sine ve
  Nove Performance tarafına not düşülür: sitenin `lib/domain` ya da `lib/queries/{tree,std,range}.ts` hesabı
  değişirse `okr_veri.py` de güncellenir. Otomatik eşitleme kontrolü yok; bunun yerine Kağan'ın üç sayılık
  karşılaştırması (Doğrulama 3) her site hesap değişikliğinden sonra yinelenir. `kurallar.md` ve Nove Performance
  ajana kapalı: not forma (§4) yazılır, Nove Performance notunu Kağan düşer.
- B2. **Komutlar** (Kalite'deki `kalite_veri.py` deseni, her biri tablo basar, içerik değil hesap):
  `sema` (tablo/izin/satır sayısı ölçümü), `donemler`, `bolumler` (bölüm başına ilerleme), `objektifler`
  (bölüm/dönem filtresiyle objective ilerlemesi ve onu en çok aşağı çeken KR), `kr` (KR başına hedef / şu an /
  yüzde / son dolu ay / ölçülemiyor / oran notu), `eksik-veri` (dönemde hiç ya da son ayda verisi olmayan KR'lar),
  `sirket` (şirket geneli özet). Filtreler: dönem (kod ya da tarih aralığı), bölüm (ad). Kesin komut adları ve
  bayrakları plana bırakılır; bu liste sınırdır.
- B2a. **Dönemler yıllık:** veritabanında yalnız mali yıllar var (kodlar `2024-FY`, `2025-FY` kapalı; `2026-FY`
  aktif, 01.09.2026–31.08.2027); çeyrek dönemi yok. Sitede aralık bir *kesimdir*, pencere değil: değerler dönemin
  ilk ayından birikir (`tree.ts:121-123,242`). "Bu çeyrek" sorusunda danışman bunu söyler: sayı mali yıl başından
  çeyrek sonuna (ya da bugüne) kadardır. **Onay 13.11:** yanıt bu birikmiş sayıdır; yalnız çeyrek dilimi
  hesaplanmaz (siteyle karşılaştırılamaz).
- B2b. **"Geride / yolunda":** sitenin kendi durum bantları kullanılır (`lib/domain/status.ts:18-24`: 0 Başlamadı,
  1–59 Gelişime Açık, 60–79, 80–100, 101+), `statusPct` üzerinden. Betik her KR/objective için bandı basar; danışman
  kendi eşiğini koymaz. (Hedef dışındaki "başarı skalası" kişiye puan vermektir; KR durumu değil.)
- B3. **Check-in:** tablo boş (O1). Betik check-in sayısını basar; 0 ise danışman check-in'e dayanan soruya
  "Nove PYS'de check-in kaydı yok" der, tahmin yürütmez.
- B4. **Kişi adları:** KR/objective sorumlularının adları yanıtta yazılabilir (ANAYASA §2 revizesi; yanıtlar
  `sirket-log/` ve `yanitlar/`'da, git dışı). Depoya giren test ve örneklerde gerçek ad yok — uydurma adlar.
- B5. **Güvenlik:** betik yalnız `SELECT`; her bağlantı `read_only`, `statement_timeout` bağlantı seçeneğinde
  (rol ayarına ek, ikinci kat). Bağlantı hatasında URL ekrana basılmaz (parolalı). Kalite'deki
  `kalite_veri.py`'nin bağlantı ve hata maskeleme kodu ortak bir yere alınır ya da aynı desenle tekrarlanır —
  plan seçer.
- B6. **Danışmanın kurulması formdan:** `formlar/gelen/okr.md` güncellendi (13.11). Kağan formu `formlar/onayli/`'ya
  koyar ve `formdan_takim.py`'nin yazan koşusunu yapar (ajan yalnız `--kuru`). Takımın izinli komutu
  `Bash(python3 bin/okr_veri.py:*)`, gerekli anahtar `OKR_READONLY_URL`. Sahne anahtarı `okr` (panelde ve 3D
  sahnede zaten var). Zorluk sınıflaması ve model seçimi bugünkü hattan aynen gelir.
- B7. **Yanıt biçimi** (form §5): önce tek cümlelik cevap; sonra dönem kodu ve son dolu ay; KR başına hedef / şu an
  / kalan tablosu; sonda "Ölçülemeyenler" (`—` ve sebebi) — form hattının `kurul-yaniti` düzeninde **Bilinmeyenler** bölümüne yazılır. `—` ile `0` karışmaz.

## Hedef dışı

- Zamanlanmış rapor (O4). Check-in'e dayalı analiz (veri yok). Oran KR'larının gerçek oranı (O3).
- Nove PYS'ye yazma, siteye tarayıcıyla giriş, sitenin koduna dokunma.
- Bütçe soruları (O6). Kişiye puan ya da başarı skalası.

## Anti-hedefler

- Danışmanın yüzdesi sitedekinden farklı çıkarsa — başarısızlık (Kalite'deki 44/68 dersi).
- Danışman kendi aritmetiğini yaparsa ya da ölçülemez KR'ı 0 sayarsa — başarısızlık.
- Bağlantı dizesi ya da parola herhangi bir çıktıya, kayda ya da teste düşerse — başarısızlık.
- Oran KR'ı notsuz verilirse — başarısızlık.

## Doğrulama

1. Birim testleri: taşınan hesap, sitenin test vektörleriyle aynı sonucu verir; ağ ve `claude` çağrılmaz; test
   sayısı 795'in altına düşmez.
2. Canlı okuma (`okr_okuyucu`): `sema` 13.11 ölçümüyle tutarlı; e-posta sütunu kapalı.
3. Kağan karşılaştırması: aynı dönem için **bir bölüm yüzdesi, bir objective, bir KR** — betik çıktısı sitedeki
   sayıyla yan yana; üçü de aynı.
4. Dev panelde (8780) üç gerçek soru: biri kolay (Haiku), biri orta, biri oran KR'ı içeren — yanıt notu taşır.
