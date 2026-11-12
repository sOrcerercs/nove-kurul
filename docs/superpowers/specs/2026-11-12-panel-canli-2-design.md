# Panel canlı 2 — Denetçi yedeği, zorluğa göre model, gerçek modda sahne

> Durum: **onaylı** — Kağan, 12.11.2026 (K7–K11)
> Dayanak: `2026-11-12-panel-canli-design.md` (onaylı) üstüne. Dal: `feature/panel-canli` (henüz merge edilmedi).
> Herkese açık depo: çalışan adı ve e-posta yok.

## Neden

Kağan canlı paneli dev sunucusunda denedi (12.11, iki kalite sorusu). Üç şey çıktı:

1. **Denetçi hep Haiku'ya düşüyor.** `.env`'de `OPENAI_API_KEY` yok; NIM geçici kapalı (PR #18). `llm_karari`
   anahtar yokken sessizce geçiyor (`bin/bekci.py:252-255`) — 23.10'dan beri 18 denetim Haiku'yla yapıldı.
   Anahtar şimdilik eklenemiyor; Kağan sistemin "başta düzgün çalıştığını" görmek istiyor.
2. **Her soru aynı modelle yanıtlanıyor** (Kalite `model: sonnet`). Kağan zorluğa göre model istiyor.
3. **Gerçek modda sahne kıpırdamıyor.** Soru sorulunca Q&A ve İş Dağıtımcı yerlerinden kalkmıyor; çünkü ilk
   tasarım (B9) gerçek modda `nove-akis` olaylarını bilerek kapattı. Kağan canlandırmayı istiyor.

## Kararlar

**Kağan'ın (12.11.2026):**
- K7. OpenAI anahtarı gelene kadar Denetçi'nin yedeği **Haiku değil Opus 5.5**. Geçici.
- K8. **İş Dağıtımcı soruyu zorluğuna göre sınıflar**; danışman koşusu kolay → Haiku, orta → Sonnet, zor → Opus 5.5.
  Denetçi ve CEO (Opus) her yanıtı kontrol eder.
- K9. **Zor (Opus) koşunun tavanı 4 USD**; kolay ve orta 2 USD kalır; soru tavanı 8 USD değişmez.
- K11. **Zor sorunun düzeltme turu kalan bütçeyle koşar** (12.11.2026): model yine Opus; tavanı
  `SORU_BUTCESI_USD − harcanan − CEO_BUTCESI_USD` (4 USD'yi geçmez). Bu tutar anlamlı bir koşuya yetmiyorsa
  (`< 0.50 USD`) düzeltme başlamaz, soru "soru bütçesi doldu" ile kapanır. Kolay/orta sorular için bugünkü kural
  (`harcanan + 2 USD > 8 USD` → kapat) aynı kalıp aynı formüle bağlanır.
- K10. Gerçek modda sahne canlansın: soru gelince Q&A kalkar, dağıtıma götürür; İş Dağıtımcı danışmana götürür;
  sonraki aşamalar da gerçek ilerlemeyle oynar.

**Benim kararım (Kağan okurken kontrol etsin):**
- B12. **Denetçi yedeği:** `haiku_sor` → model ayardan okunur (`ayar.BEKCI_YEDEK_MODEL = "opus"`). Gerekçe öneki
  "opus yedeği · " olur; "[bekçi aynı aileden — uyarı]" notu **kalır** (Opus da danışmanla aynı aile). Yedek
  çağrının para tavanı vardır (`ayar.BEKCI_YEDEK_BUTCESI_USD = 0.75`). **Bugün Denetçi maliyeti hiç sayılmıyor**
  (`haiku_sor` maliyeti atıyor, `bin/bekci.py:233-235`); Opus'la bu soru başına 1,5–3 USD görünmez para demek.
  Bu yüzden Denetçi maliyeti kaydedilir (`## Denetçi` altında `- denetçi maliyeti:`) ve **soru bütçesine ve
  şirket günlük tavanına** sayılır (`soru_kaydi.harcanan`, `ayar.gunluk_maliyet`). Danışman koşusunun 2/4 USD
  tavanına sayılmaz (o tavan `claude -p`'nin kendi bütçesidir). Yedek alt sürecin zaman aşımı Stop hook süresinin
  (420 sn) içinde kalacak şekilde yükseltilir. Sıra değişmez: NIM (kapalı) → OpenAI (anahtar varsa) → yedek.
- B13. **Sessiz düşüş biter:** anahtarı olmayan yol gerekçeye yazılır: "openai anahtarı yok → " (NIM için de aynı
  kalıp). `NIM_ACIK` kontrolü anahtar kontrolünden önce yapılır (bugün anahtar yoksa "nim kapalı" bile yazılmıyor,
  `bin/bekci.py:252-257`). Gerekçe öneklerini bekleyen testler güncellenir. ANAYASA §3 "hiçbir düşüş sessiz değildir" der; bugünkü kod buna uymuyor.
- B14. **ANAYASA §3 çelişkisi açıkça not edilir:** §3 yedeği "Haiku" diye adlandırıyor. K7 bunu geçici olarak
  değiştiriyor. ANAYASA'yı ajan değiştirmez; `sirket/DENETCI.md` ve `NOVE-KURULUM.md`'ye "geçici: yedek Opus 5.5
  (Kağan, 12.11.2026)" notu düşülür. ANAYASA metnini güncellemek Kağan'ın kararı.
- B15. **Zorluk sınıflaması:** her soru için İş Dağıtımcı Haiku'ya tek bir kısa çağrı yapar (yönlendirme için Haiku
  zaten çağrılıyorsa aynı çağrıda): `zorluk: kolay | orta | zor` + tek cümle gerekçe. Anahtar kelimeyle
  yönlenen sorular da sınıflanır. Haiku hatası ya da tanınmayan yanıt → `orta` (bugünkü davranış), sebep yazılır.
  Tanımlar istemde: kolay = tek kaynak, tek sayı/liste, hesap yok; orta = birkaç kaynak ya da basit karşılaştırma;
  zor = çok adımlı analiz, dönemler arası karşılaştırma, neden-sonuç, koçluk önerisi. Sınıflama maliyeti mevcut
  `DAGITIM_HAIKU_BUTCESI_USD` içinde kalır.
- B16. **Model ve tavanın taşınması:** zorluk soru kaydının `## Dağıtım` bölümüne (`- zorluk: zor · gerekçe`) ve
  kuyruk maddesine yazılır. `kos.py` soru maddesini koşarken modeli ve bütçeyi `ayar.ZORLUK_MODELI` /
  `ayar.ZORLUK_BUTCESI_USD` tablosundan alır: kolay `haiku`/2.0 · orta `sonnet`/2.0 · zor `opus`/4.0.
  `takim.md`'deki `model:` yalnız zorluk yokken (zamanlı rapor, eski kuyruk maddesi) geçerli kalır. Düzeltme
  turu (Denetçi reddi sonrası) aynı modelle koşar. Koşu kaydının altbilgisine model ve zorluk yazılır.
- B17. **Gerçek modda sahne:** `GET /api/sorular/<id>` yanıtına `asama` alanı eklenir — soru kaydının bölümlerinden
  türetilen sıralı liste: `qa_al` (kayıt var) · `dagit` (`## Dağıtım` var) · `analiz` (durum `danışmanda` ya da
  sonrası) · `denetim` (yalnız Denetçi kararı `kabul` olan bir `## Denetçi` bölümü varsa; `red`/`atlandi` sahnede
  "Doğrulandı ✓" oynatmaz — `ofis3d-v4.js` değişmez) · `ceo_sorgu`/`revize` (CEO reddi + düzeltme varsa) · `ceo_onay` (`## CEO —
  karar: onay`) · `qa_ilet` (defterde). `panel.js` yoklamada yeni bir aşama gördükçe o aşamanın `nove-akis` olayını
  **bir kez** gönderir (aynı `runId`, `dept` = danışman anahtarı). Sayfa yenilenince geçmiş aşamalar yeniden
  oynatılmaz, yalnız son aşamadan devam edilir. Onaylanamayan soruda `qa_ilet` yerine sahne boşa döner.
  `asama` yalnız kurulun görmesine izin verilen bilgiden türetilir; gerekçe metni taşımaz. Yanıta `danisman`
  (sahne anahtarı, Kalite için `kalite`) de eklenir. Sahnede olay kuyruğu yok (`akis()` tek olay oynatır, bitince
  `nove-adim-bitti` yollar, `ofis3d-v4.js:693`); aynı yoklamada gelen aşamaları `panel.js` sırayla, her biri
  bitince bir sonrakini göndererek oynatır (`dagit` ve `analiz` hep birlikte gelir). Demo yolu değişmez.
- B18. **Ajan kartı ve akış listesi:** bu adımda yalnız 3D sahne canlanır; demo'daki adım listesi gerçek modda
  gösterilmez (bekleme ekranı aynen kalır).

## Hedef dışı

- OpenAI anahtarının eklenmesi (Kağan'da). NIM'in yeniden açılması.
- Kalite dışı danışmanlar; zorluğa göre CEO modeli (CEO hep Opus).
- ANAYASA §3 metninin değiştirilmesi.

## Anti-hedefler

- Opus yedeği "farklı aile" gibi gösterilirse (uyarı notu düşerse) — başarısızlık.
- Zor sorular 4 USD'yi, herhangi bir soru 8 USD'yi aşarsa — başarısızlık.
- Sahne olayı gerçek ilerlemeden önce oynarsa (ör. Denetçi kontrol etmeden "Doğrulandı ✓") — başarısızlık.
- Kurul rolü `asama` üzerinden ham gerekçe ya da başka üyenin sorusu hakkında bilgi alırsa — başarısızlık.

## Başarı ölçütü

Dev sunucusunda: kolay bir soru Haiku'yla, zor bir soru Opus'la koşar (koşu kaydı altbilgisinde görünür);
Denetçi gerekçesi "nim kapalı (geçici) → openai anahtarı yok → opus yedeği · [bekçi aynı aileden — uyarı]" ile başlar;
soru sorulunca Q&A kalkıp dağıtıma gider, İş Dağıtımcı Kalite'ye götürür, Denetçi ve CEO aşamaları gerçek sırayla
oynar. Testler ağ ve `claude` çağırmaz; test sayısı 697'nin altına düşmez.
