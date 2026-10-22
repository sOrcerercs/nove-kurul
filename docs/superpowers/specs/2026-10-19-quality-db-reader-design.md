---
durum: yazildi
guncelleme: 2026-10-19
dal: feature/quality-db-reader
pr: -
bekleyen: -
---

# Kalite ajanının veri okuyucusu — Tasarım

> Faz 4. Kararlar Kağan'la 19.10.2026'da adım adım verildi. Bu belge onaylanmadan kod yazılmaz.

## Amaç ve neden

Kalite ajanı (`takimlar/kalite/`, 19.10'da formdan kuruldu) kurulun kalite sorularını SDR Analyzer'ın gerçek
verisiyle yanıtlayacak. İlk gerçek soru (Kağan): *"Bu ay hangi ekibin kalite puanı düştü?"* Sorular hem standart
dönemlerle ("bu ay", "geçen ay") hem özel dilimlerle ("<ekip lideri>'nin ekibi, 3–17 Ekim") gelebilir (Kağan).

Ajan bugün veri okuyamıyor: aracı yalnız `Read, Write, Glob, Grep`. Bu iş, ajanın soruya göre çağıracağı tek bir
okuma betiği ve ona verilecek tek izinle bu boşluğu kapatır.

**Başarı:** Ajanın verdiği sayı, panelin aynı dönem ve filtre için gösterdiği sayıyla aynıdır ve yanıtta hangi
kaynaktan, hangi tarih aralığıyla, kaç kayda dayanarak geldiği yazar.

**Görülecek kişi:** Yalnız kurul üyesi (Nove paneli, kendi sorularının yanıtı). Satış temsilcileri ve ekip
liderleri Nove'yi görmez (Kağan).

## Verilen kararlar (Kağan, 19.10.2026)

1. **Veritabanından salt okunur okuma.** Önce API (A) seçilmişti; Kağan veritabanına geçti. SDR Analyzer'ın
   Supabase'ine mevcut **`qa_okuyucu`** rolüyle bağlanılır (16.09.2026'da `kagan-sirketi/docs/qa-gorunumler.sql`
   ile kuruldu: yazma yetkisi yok; `transcript`, `report`, `customerName`, kanıt alıntıları ve hasta bilgisi
   sütun düzeyinde kapalı; okuma `qa_degerlendirme` ve `qa_kriter` görünümlerinden).
2. **Bağlantı adresi `.env`'de**: `QA_READONLY_URL`. Sunucuya taşınınca da aynı yol çalışsın diye (Kağan).
   Ajan `.env`'yi okuyamaz (`.claude/settings.json` deny); adresi yalnız betik okur, hiçbir yere yazmaz.
3. **Hesabı betik yapar, ajan yapmaz.** API/veritabanı hazır vermiyorsa (ör. ekip bazında aylık ortalama) betik
   hesaplar; ajan betiğin tablosunu okuyup yorumlar ve kaynağıyla yazar. (`qa-hatti` deseni: "sen aritmetik yapmazsın".)
4. **Ajan veriyi kendisi ister**: soruya göre betiğe tarih aralığı ve ekip verir. Hazır paket yetmez, çünkü özel
   dilimler soruluyor.

## Hedefler

- Tek betik: `bin/kalite_veri.py` (ad uygulayıcının; burada bu adla geçer). Alt komutlar, ilk sürüm:
  - `ekipler` — ekipler ve üyeleri
  - `ekip-ozet --baslangic YYYY-MM-DD --bitis YYYY-MM-DD [--karsilastir-baslangic … --karsilastir-bitis …] [--tip first|second]`
    — ekip bazında ortalama puan ve kayıt sayısı, istenirse iki dönem yan yana ve fark
  - `kriterler --baslangic … --bitis … [--ekip …] [--tip …]` — kriter bazında kaldı/kısmi/geçti sayıları, en sık kaçırılanlar
  - `temsilci-ozet --baslangic … --bitis … [--ekip …]` — temsilci bazında ortalama ve kayıt sayısı
  - `kocluk --baslangic … --bitis … [--ekip …]` — **[Claude'un kararı]** koçluk yapılan / temsilcinin okuduğu
    kayıt sayıları. `qa_ozet.py` aynı rolle `coachingDone` ve `agentRead`'i okuyor (inceleme bulgusu); formun 4.
    sorusu için. "Koçluktan sonra gelişme" yine `—` (ölçütü yok, Kağan).
  - Haftanın çağrısı **[Claude'un kararı]**: rol bu tabloları okuyabiliyorsa komut eklenir; okuyamıyorsa ajan `—` ve
    sebebini yazar. Uygulayıcı izni ölçer.
- Her çıktı başında: kaynak (görünüm adları), tarih aralığı (TR saati), filtre, toplam kayıt sayısı.
- Ajana tek yeni izin: bu betiği çalıştırmak. Başka komut yok.
- Formdan üretilen dosyalar bunu taşır (aşağıda "Form ve kurulum").

## Referans ekran (Kağan, 19.10.2026)

Kağan ekip puanına **Raporlar → Raporlarım**'dan bakıyor. Bu sekme `ReportsView` →
`GET /api/reports/auto?start=…&end=…&agentIds=…` (`sdr-analyzer/app/api/reports/auto/route.ts`). "Fark 0" ölçümünün
referansı bu ekrandır; betik onun kuralını birebir uygular:

- kayıtlar: `callDate` `gte start` ve `lte end` (uç dahil), `agent.role ∈ {AGENT, TEAM_LEADER}` (`REPORTABLE_ROLES`,
  `app/lib/reportScope.ts:3`), `scoringWhere()` (sınıf sütunu boş ya da `CONNECTED_QUALIFIED`)
- ortalama: **kayıt başına** (çağrı sayısıyla ağırlıklı), virgülden sonra bir haneye yuvarlanmış
  (`app/lib/reportAggregation.ts`, `healthScore`/`avgScore`)
- ekip: ekranda ekip, temsilci seçilerek oluşur; betik ekibi `User.teamId` ile kurar. Pasif kullanıcıların
  kayıtlarının sayılıp sayılmadığı (`isActive` yalnız listeyi mi süzüyor, kayıtları da mı) uygulayıcı tarafından
  `route.ts`'den doğrulanır ve aynısı yapılır.
- `start`/`end`'in saat dilimi ve ekranın gönderdiği değerler uygulayıcı tarafından ön yüz kodundan doğrulanır.

`/api/scores/compare` referans **değildir** (tarih aralığı yok, temsilci ortalamalarının ağırlıksız ortalaması).

## Hedef değil (bilerek dışarıda)

- Günlük rapor zamanlayıcısı (pzt–cuma 11:00) — ayrı iş.
- API yolu, SDR Analyzer'da kod değişikliği, deploy.
- Transkript, müşteri adı, rapor metni okumak — rol bunlara kapalı ve kapalı kalmalı.
- Panelde yanıtın kart olarak çizilmesi — ayrı taslak (`docs/superpowers/plans/2026-10-19-answer-card-rendering.md`).

## Anti-hedef (çalışsa bile başarısızlık sayılır)

- Ajanın sayısının panelden farklı çıkması (yanlış sayı, eksik sayıdan zararlıdır — ANAYASA §2).
- Betiğin ya da ajanın veritabanına yazabilmesi; rol dışında bir bağlantı kullanması.
- Bağlantı adresinin bir dosyaya, loga ya da koşu kaydına düşmesi.
- Örneklemi gizlemek: kayıt sayısı yazmayan bir sayı.

## Kısıtlar

- **[Claude'un kararı] Önce mevcut izinler.** `qa_okuyucu` bazı tablo sütunlarını doğrudan okuyabiliyor
  (`qa_ozet.py`: `Evaluation.score`, `callType`, `coachingDone`, `agentRead`, `sectionScores`; `User`, `Team`).
  Betik bunları kullanır. Ek izin ya da görünüm gerekirse **yeni** bir görünüm/izin eklenir; `qa-hatti`'nin
  kullandığı `qa_degerlendirme` ve `qa_kriter` **değiştirilmez**. Not (inceleme): `qa_degerlendirme`
  `reportData`'sı nesne olmayan kayıtları düşürüyor; panel onları sayıyor — ekip ortalaması bu görünümden alınmaz.
- **Panelle aynı sayım kuralı.** Panel ortalamaya yalnız `callClassification` sütunu boş ya da
  `CONNECTED_QUALIFIED` olan kayıtları katar (`sdr-analyzer/app/lib/callVisibility.ts:90`, `scoringWhere`).
  Kağan'ın elle koyduğu `TRANSCRIPT_UNUSABLE` işaretleri bu **sütunda**. `qa_degerlendirme` ise sınıfı
  `reportData->>'callClassification'`'dan okuyor — elle işaretlenen kayıtları kaçırabilir. Uygulayıcı farkı ölçer;
  sütun görünümde yoksa görünüme ekleyen SQL'i yazar, **Kağan Supabase'de çalıştırır** (DDL insanın;
  `kagan-sirketi/docs/qa-gorunumler.sql` deseni, adım adım).
- **Puan:** `Evaluation.score` esas (kart puanı — `sdr-wiki` `kart-puani-esas-alinsin`). Canlıda Second Call puanı
  deploy'a kadar eski formülle yazılıyor ve gece hizalanıyor; çıktı Second Call içeriyorsa bunu not eder.
- **Tarih:** `callDate`, TR saatine göre gün sınırı (panelle aynı olmalı; uygulayıcı paneldeki kuralı doğrular).
- **Ekip eşleşmesi:** `User.teamId` → `Team` (qa_ozet.py bunu `qa_okuyucu` ile yapıyor, `kagan-sirketi/bin/qa_ozet.py:137-138`).
  Bugünkü üyelik kullanılır; geçmiş üyelik tutulmuyor (çıktı bunu söyler).
- **Kurallar (`takimlar/kalite/kurallar.md`):** 15'ten az puanlanabilir çağrıda yorum yok; 3'ten az değerlendirmeli
  temsilci "en iyi" seçilmez; 1 Eylül 2026 öncesiyle karşılaştırma yok; anlamlılık ölçülmeden "iyileşti" yok.
  Betik bunları kendisi uygulamaz ama gereken veriyi verir (kayıt sayıları, tarih sınırı uyarısı).
- **Kriter verisinin kapsamı ölçülmeli.** `qa-hatti` (16.09) kriter bazlı zengin bloğun yalnız bir ekipte ve tek prompt
  sürümünde (v11.4) olduğunu yazıyordu (`kagan-sirketi/takimlar/qa-hatti/takim.md`). Bugün hangi ekip ve sürümlerde
  `qa_kriter` dolu, uygulayıcı sayar; `kriterler` çıktısı kapsam dışı kalan ekipleri adıyla söyler.
- **Bağlantı sürücüsü:** `psycopg` (v3) bu makinede kurulu; `qa_ozet.py` onu kullanıyor. Başka bağımlılık eklenmez.
- **Kişisel veri:** Çıktıda temsilci adı olur (kurallar.md: personel adı yazılabilir); müşteri adı rol gereği yok.
- Sorgular salt `SELECT`; zaman aşımı kısa (`statement_timeout`), bağlantı hatası görünür sebeple döner (sessiz düşme yok).

## Form ve kurulum

Kalite formu (`formlar/onayli/kalite.md`) bugün API'ye göre yazılı. Kurulumla birlikte değişmesi gerekenler:

- §3 veri tablosu: kaynak `qa_okuyucu` görünümleri; API uç listesi çıkar.
- §4 "Asla": "izin listesi dışındaki API ucu" maddesi → "veritabanına `qa_okuyucu` dışında bağlanmak; betik dışında
  komut çalıştırmak".
- §7: `Gerekli anahtarlar: QA_READONLY_URL` (SDR_API_* çıkar).
- Ajanın aracı: form hattı bugün `tools`'u sabit üretiyor (`bin/formdan_takim.py` `ARACLAR`). §7'ye bir alan eklenir
  (ör. "İzinli komut") ve betik `tools`'a `Bash(python3 bin/kalite_veri.py:*)` biçiminde ekler. Sürücü `tools`'u
  `--allowedTools`'a veriyor (`bin/kos.py:409`).
- Formu Kağan revize eder, `formlar/onayli/`'ye koyar ve `python3 bin/formdan_takim.py kalite --yeniden`'i kendi
  terminalinde koşturur (ajan ortamında yazma kapalı, K1).

## Uygulayıcıya kalanlar

- Alt komutların tam parametreleri ve çıktı biçimi (ajan için okunur, testte karşılaştırılabilir).
- Görünüm/sütun farkının ölçümü ve gerekirse görünüm SQL'i.
- `Bash(...)` izin deseninin `claude -p --allowedTools` ile gerçekten yalnız bu komuta izin verdiğinin doğrulanması.
- Ajanın `takim.md` koşu adımlarına "veriyi `python3 bin/kalite_veri.py …` ile al" talimatı (form hattının ürettiği
  metne eklenecek yer).

## Bitirme ölçütü

- Birim testleri: sorgu oluşturma, ağırlıklı ekip ortalaması, tarih sınırları, sayım kuralı; veritabanı olmadan (sahte bağlantı).
- **Tutarlılık ölçümü (canlı, salt okunur):** Bir ay ve bir ekip için betiğin `ekip-ozet` sonucu, panelin aynı dönem ve
  filtredeki rakamıyla karşılaştırılır; fark 0 olmalı. Sonuç belgeye yazılır.
- `QA_READONLY_URL` yokken betik ve ajan görünür sebeple durur; sürücü ajanı "eksik anahtar" ile atlar.
- `python3 -m unittest discover -s tests` yeşil; taban 468.
