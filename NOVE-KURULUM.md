# NOVE KURUL OFİSİ — Kurulum Belgesi

> Nove Group yöneticileri için ajan ekosistemi. Kurul üyesi soru sorar; danışman ajanlar analiz eder,
> Denetçi (Bekçi) kuralları denetler, CEO Ajanı double check yapıp onaylar. **Yayın düğmesi yine insandadır.**
>
> Hazırlayan: Kağan Öztürk · Taslak: 09.10.2026 · Durum: **taslak — revize sürüyor** (13.10.2026: §0–§12)

---

## 0 · Bu belge neye dayanıyor

| Kaynak | Ne alındı |
|---|---|
| `~/kagan-sirketi` (VS Code projesi) | **Başlangıç noktası.** Sürücü katmanı, bekçinin NIM → OpenAI → Haiku sırası, karar defteri, `sahne.py`, testler (Faz 1'de 266'sı taşındı). **Denetçi** tanımı (`bin/bekci.py`, `docs/03-bekci.md`), **patron** tanımı (`sirket/AJAN-KIMLIGI.md`, CEO'nun temeli) ve ANAYASA'nın beş maddesi |
| Claude Design — *Nove Kurul Ofisi 3D v4* | Rol listesi, 8 adımlı soru akışı, ofis yerleşimi, satış ekibi ve zil, "+ Boş oda", Yanıt defteri sekmesi (eski adı: Karar defteri) |
| Nove AI giriş tasarımı (09.10.2026) | Dönen dünya üstünde "Welcome to Nove AI" girişi, e-posta + şifre formu, "Hoş geldin" geçişi ve ofise dalış. Dosyalar `panel/` altında (§8c) |

**Alınan kararlar (09.10.2026):**

| # | Karar |
|---|---|
| N1 | Sistem **şirket sunucusunda** çalışır. Yöneticiler tasarımdaki web panelini kullanır (on-prem; Nove Finans'taki kararla aynı yön) |
| N2 | **CEO Ajanı = ikinci onay kapısı.** Bekçi'nin (Denetçi) onayladığı her çıktı CEO'ya da gider. CEO double check yapar ve onaylar. Onaylamazsa çıktı kurula gitmez. Temeli kagan-sirketi'deki "patron" rolüdür (çıktıyı okur, evet/hayır der) ama dışarıya hiçbir şey yayınlamaz |
| N3 | **Denetçi = bekçi.** kagan-sirketi'deki tanım büyük ölçüde aynen kalır (§4) |
| N4 | Danışmanları yöneticiler **Markdown şablonuyla** doldurur (§6). Son revizeyi Kağan yapar, sonra `takim.md` ve `kurallar.md` dosyalarına çevirir |
| N5 | Repo **`kagan-sirketi`'nden** türetilir. Yeni depo **temiz geçmişle** başlar: kagan-sirketi'nin git geçmişi taşınmaz, upstream remote eklenmez. `LICENSE` dosyası olduğu gibi korunur (Faz 1) |
| N6 | **Zil CRM'e bağlanır:** CRM'den "satış yapıldı" bilgisi gelince zil çalar. Bağlantı salt okunurdur ve LLM kullanılmaz |
| N7 | **Kurul üyesi yetkisi = soru sor, yanıt al.** Başka yetkileri yoktur. Ayrıntıları Kağan sonra paylaşacak |
| N8 | **"Karar defteri" sekmesinin adı "Yanıt defteri" olur.** Sekmede kurul üyesinin sorduğu soruların onaylı yanıtları listelenir |
| N9 | **Zilde temsilci adı görünmez.** Sahnede yalnız masa numarası kullanılır. Ayrıntıya sonra inilecek |
| N10 | **Kurul üyesi Yanıt defterinde yalnız kendi sorularını görür.** Bu artık varsayım değil, karardır |
| N11 | **Panele giriş e-posta ve şifreyle yapılır.** Google Workspace / oauth2-proxy girişi kullanılmaz. Giriş ekranı Nove AI giriş tasarımıdır (`panel/`); doğrulamayı `panel.py` yapar (§8c) |
| N12 | **Denetçi'nin üçlü kontrolünde biri `kaldi` ise karar `red`'dir**, model `kabul` dese bile (12.10.2026) |
| N13 | **TC kimlik deseni sağlama hanesiyle çalışır:** yalnız geçerli TC numarası yakalanır (12.10.2026) |
| N14 | **Şemasız yollarda (NIM, Haiku) `kontrol` alanı eksikse karar korunur**, kontrol "yapılmadı" yazılır; panelde ışıklar gri (12.10.2026) |
| N15 | **Q&A ön kontrolleri:** günlük 10 soruyu dolduranın 11. sorusu reddedilir · şirket günü 40 USD doluysa soru ertesi güne bekler · 3 kelimeden kısa soru geri döner · aynı kişi aynı soruyu 10 dk içinde sorarsa ikinci kayıt açılmaz (12.10.2026) |
| N16 | **Anahtar kelime eşleşmezse ya da berabere kalırsa Haiku sınıflandırır** (yalnız aktif danışmanlar); listede olmayan ad → "yönlendirilemedi", varsayılan danışman yok (12.10.2026) |
| N17 | **Soruyu adımdan adıma İş Dağıtımcı otomatik taşır:** Denetçi kararını soru kaydına sürücü kopyalar, CEO'yu dağıtıcı başlatır, CEO reddinde `r-` açar, onayda iletir (12.10.2026) |
| N18 | **Denetçi'nin son kararı `red` ya da `atlandi` ise soru "onaylanamadı" olur:** CEO'ya gitmez, Yanıt defterine Denetçi'nin gerekçesiyle girer (12.10.2026) |
| N19 | **Denetçi yönergesi ve üç ek sınır kagan-sirketi'nden aynen alınır:** madde 3–4 Denetçi'nin konusu değildir · "kaynaksız sayı" yalnız dış dünya iddiaları içindir · hedef aralıktan %15'e kadar sapma red sebebi değildir (13.10.2026) |
| N20 | **Sekmenin adı "Yanıt defteri" olarak kesinleşir** (S3 kapandı, 13.10.2026) |
| N21 | **Yanıt dili her danışmanda Türkçedir;** teknik terimler orijinal hâliyle kalır (S5 kapandı, 13.10.2026) |
| N22 | **Yanıtlar kurul dışına otomatik kopyalanmaz.** Kurul dışına taşımak insanın kararıdır, ANAYASA §1 (S6 kapandı, 13.10.2026) |
| N23 | **Panel şifreleri:** yönetici kullanıcıyı ekler, ilk girişte geçici şifre değiştirilir, şifresini unutan yöneticiye başvurur (Nove PYS'deki yöntem); e-posta altyapısı gerekmez (S8 kapandı, 13.10.2026) |
| N24 | **ANAYASA §2: etiket iddiaya konur, cümleye değil;** kaynak dış dünya sayısında, `n` örneklemden türeyen sayıda zorunludur (N19 ile aynı sınır, 13.10.2026) |
| N25 | **ANAYASA §4 rakam taşımaz:** tavanların ilkesi anayasada, rakamları yalnız `bin/ayar.py`'de ve §9'da (13.10.2026) |
| N26 | **ANAYASA §1: danışman yalnız kendi klasörüne yazar** — `cikti/`, `kosu/`, `defter.md` (13.10.2026) |
| N27 | **Soru bütçesi 6 USD:** en kötü yol (iki danışman koşusu + iki CEO kontrolü) 5 USD tuttuğu için Denetçi'ye ve paya 1 USD kalır (13.10.2026) |
| N28 | **Yanıt süresi ölçütü:** düzeltme turu geçirmeyen soruda 30 dk; düzeltmedeki soruya süre sözü verilmez (13.10.2026) |
| N29 | **Sistem haftanın her günü 08:00–20:00 çalışır;** aylık en kötü durum 1.200 USD (13.10.2026) |
| N30 | **ANAYASA §2: hasta ve müşterinin ad soyadı yazılabilir;** telefon, e-posta, TC kimlik no yasak kalır; ad soyad taşıyabilen dosya (defter, onaylı form) herkese açık depoya girmez. Yapay zekâ sağlayıcılarına aktarım Kağan'ın teyidiyle uygun (19.10.2026) |
| N31 | **CEO tavanı geçici olarak 1,50 USD/kontrol, soru bütçesi 8 USD:** Opus 5.5 fiyatıyla (4 $ / 20 $ MTok, düşünme kapatılamıyor ve çıktı sayılıyor) tahmin tipik ~0,53, ağır ~1,28 USD; 0,50 USD'de CEO karar yazamadan kesilir. Kalıcı rakam Faz 4 beş gerçek soruda ölçülüp konur. En kötü yol 2 + 1,5 + 2 + 1,5 = 7 USD + 1 USD pay. Aylık 1.200 USD değişmez (günlük 40 USD belirliyor) (19.10.2026) |

---

## 1 · Rol haritası — tasarımdaki her kişi neye karşılık geliyor

| Tasarımdaki rol | Ne yapar (tasarım) | Teknik karşılığı | Dosya |
|---|---|---|---|
| **Kurul üyesi** (insan) | Soruyu sorar, yanıtı okur | Panel kullanıcısı (e-posta + şifre girişi, N11) | — |
| **Q&A Danışmanı** | Soruyu alır, kayda geçirir; sonunda yanıtı kurula iletir | Giriş/çıkış kapısı. **LLM çağırmaz.** Rol, ön kontroller (N15) ve maskeleme burada; panelden gelen soruyu Faz 5'te `panel.py` buraya verir | `bin/soru_kapisi.py` |
| **İş Dağıtımcı** | Bölümü seçer, soruyu doğru danışmana götürür | `dagitici.py` + `takim_sec()`. Önce anahtar kelime tablosu kullanılır; o tutmazsa Haiku ile sınıflandırılır | `bin/dagitici.py` |
| **Danışman** (Finans, Kalite, OKR, Raporlama, Satış Müdürü, …) | Analiz eder; CEO reddederse düzeltir | **Takım.** Dört dosyalı iskelet: `takim.md` · `kurallar.md` · `defter.md` · `durum.json` | `takimlar/<danisman>/` |
| **Denetçi Ajan** | Masaya gelir; kaynak, hesap ve tutarlılık kontrol eder | **Bekçi.** Stop hook'ta, ayrı süreçte ve ayrı model ailesinde çalışır | `bin/bekci.py` |
| **CEO Ajanı** | Bekçi'nin onayladığı çıktıyı ikinci kez kontrol eder, onaylar | **Yeni.** Bekçi kabulünden sonra çalışan ayrı bir `claude -p` koşusu: double check + onay şeması | `bin/ceo.py`, `sirket/CEO-KIMLIGI.md` |
| **Yanıt defteri** (sekme, eski adı Karar defteri) | Sorulan soruların onaylı yanıtlarının listesi | `yanit_defteri.py` (`karar_defter.py`'den türer). Ona yalnız sürücü yazar | `yanitlar/` |
| **Satış ekibi (20) + Zil** | Her satışta temsilci zile gider | **Ajan değildir.** CRM'den gelen "satış yapıldı" olayının görselleştirmesidir (§8a) | `bin/crm_zil.py` |
| **+ Boş oda** | Yeni danışman yeri | Doldurulmamış danışman formu → `bin/takim-olustur.sh` | `formlar/` |

> **Neden Q&A ve İş Dağıtımcı LLM'siz?** kagan-sirketi'nin kuralı "dağıtıcı LLM çağırmaz". Giriş kapısı ile
> yönlendirme ucuz ve deterministik olmalı. Sahnede ajan gibi görünürler, ama arkalarında sürücü vardır.
> İş Dağıtımcı yalnız belirsiz durumda Haiku'ya sorar ve gerekçeyi kayda yazar.

---

## 2 · Soru akışı — tasarımdaki 8 adım, teknik karşılığıyla

```
 Kurul üyesi ── panel: "Soruyu gönder"
      │
 [1] Q&A Danışmanı      soru_kapisi.py → gelen/<soru-id>.json, maskele, sahibini yaz
      │
 [2] İş Dağıtımcı       dagitici.py → anahtar kelime tablosu → (belirsizse Haiku)
      │                 → takimlar/<danisman>/durum.json kuyruğuna  s-<soru-id>
 [3] Danışman           kos.py <danisman>   (claude -p, sonnet)
      │                 → cikti/<soru-id>-taslak.md
 [4] Denetçi (Bekçi)    Stop hook → bekci.py  (NIM → OpenAI → Haiku)
      │   red ─► aynı oturumda düzelt (en fazla 2) — CEO'ya HİÇ gitmez
      │ kabul
 [5] CEO double check   ceo.py <soru-id>  → {karar: onay | red, bulgular[]}
      │   red ─► [6] Danışman düzeltir  kuyruk: r-<soru-id>  → Bekçi tekrar ([4]) → CEO tekrar ([5])
      │ onay
 [7] Onaylı yanıt       iki imza: Bekçi ✔ + CEO ✔
      │
 [8] Q&A Danışmanı      soru_kapisi.py --ilet → panelde soranın masasına + Yanıt defterine
```

**Akışın kuralları:**

- **Kurula yalnız iki onaylı çıktı gider:** önce Bekçi `kabul`, sonra CEO `onay`. Sıra değişmez;
  Bekçi'nin reddettiği çıktı CEO'ya ulaşmaz.
- **CEO reddederse bir düzeltme turu vardır** (`ayar.CEO_MAKS_RED = 1`). Danışman CEO'nun bulgularıyla düzeltir,
  çıktı yeniden Bekçi'den ve CEO'dan geçer.
- **Hiçbir soru sessizce kaybolmaz.** Şu üç durumda yanıt kurula gönderilmez; soru "onaylanamadı" etiketiyle ve
  gerekçesiyle Yanıt defterine girer, soran bunu panelinde görür:
  - Bekçi'nin son kararı `red` ya da `atlandi` (N18) — gerekçe Bekçi'nin
  - CEO'nun ikinci `red`'i — gerekçe CEO'nun
  - Soru bütçesi (`ayar.SORU_BUTCESI_USD`) sonraki adıma yetmiyor
- CEO süreci karar yazmadan düşerse dağıtıcı onu süre tavanı + 2 dk sonra bir kez yeniden başlatır; yine karar
  yoksa soru onaylanamadı olur.
- Tasarımdaki 8 adımla eşleşme: "CEO sorgular" → double check, "Danışman revize eder" → CEO red sonrası düzeltme,
  "CEO son kararı verir" → ikinci kontroldeki onay/red.
- Bir sorunun tamamı tek bir **soru kaydında** toplanır: `sirket-log/sorular/<soru-id>.md`. Kimin ne yaptığı,
  Bekçi kararları, CEO kararı ve bulguları ve maliyet bu dosyada yer alır. Sahnedeki "Soru akışı" paneli bu dosyayı okur.
- Birden fazla danışmanı ilgilendiren soru (ör. "Q3 bütçe sapması" hem Finans'ı hem OKR'ı ilgilendirir):
  İş Dağıtımcı **ana danışmanı** seçer, diğerini `öneri:` satırı olarak kayda yazar. İlk sürümde çoklu danışman yoktur.

---

## 3 · Klasör yapısı (`nove-kurul` reposu)

```
nove-kurul/
├── ANAYASA.md                 Nove versiyonu (§7) — İNSANIN
├── CLAUDE.md                  projenin kimliği, okuma sırası, yasaklar
├── sirket/
│   ├── AJAN-KIMLIGI.md        danışman kimliği (kagan-sirketi'nden uyarlanır)
│   ├── CEO-KIMLIGI.md         YENİ — §5
│   ├── DENETCI.md             YENİ — bekçinin insan-okur tanımı, §4
│   └── YETENEKLER.md
├── takimlar/
│   ├── _iskelet/              takim-olustur.sh'in kopyaladığı dört dosya
│   ├── finans/  kalite/  okr/  raporlama/  satis-muduru/
│   └── <danisman>/  takim.md · kurallar.md · defter.md · durum.json · gelen/ · kosu/ · cikti/ · veri/
├── formlar/                   şablon: `DANISMAN-FORMU.md`
│   ├── DANISMAN-FORMU.md      yöneticilere giden boş şablon (§6)
│   ├── gelen/                 doldurulmuş formlar — git'e GİRMEZ
│   └── onayli/                Kağan'ın revize ettiği formlar — git'e GİRMEZ (19.10.2026)
├── yanitlar/                  Yanıt defteri — yalnız sürücü yazar
├── skills/<ad>/SKILL.md
├── bin/                       kos · bekci · ceo · dagitici · soru_kapisi · yanit_defteri · crm_zil · panel · ayar · …
├── panel/                     arayüz: giriş gezegeni + Kurul Ofisi 3D v4 (index.html · stil.css · panel.js · ofis3d-v4.js)
├── sirket-log/                sorular/ · rapor/ · telemetri — git'e GİRMEZ
├── deploy/                    systemd birimleri, Caddy ayarı · roller.json (e-posta → rol, git'e GİRMEZ; örneği roller.json.example)
└── tests/
```

`kagan-sirketi`'ndeki takımlar (`kasa-bakimi`, `haftalik-rapor`, `karar-takibi`, `qa-hatti`, `okr-takip`)
**taşınmaz**, çünkü onlar senin kişisel şirketin. Yalnız sürücü, testler ve `skills/` altındaki genel yetenekler gelir.
`qa-hatti` ve `okr-takip`, Kalite ve OKR danışmanları için **örnek takım** olarak okunur.

---

## 4 · Denetçi — kagan-sirketi'deki bekçi, Nove'ye uyarlanmış hâli

kagan-sirketi'deki tanım **aynen** kalır:

- Stop hook'ta, ayrı süreçte çalışır (`.claude/settings.json` → `bin/bekci.py`). Çıkış kodu **her zaman 0**'dır.
- **Katman 1 — LLM'siz ön kontrol:** e-posta, anahtar ve token desenleri bulunursa karar doğrudan `red` olur.
  Boş kayıtta da karar `red` olur.
- **Katman 2 — LLM denetimi:** `<anayasa>` + `<kurallar>` + `<kosu>` blokları verilir. Model şüphede `red` verir ve yalnız JSON döner.
- **Ayrı aile:** sıra NIM (`openai/gpt-oss-20b`) → OpenAI → Haiku. Haiku'ya düşülürse karar
  "denetçi aynı aileden — uyarı" notuyla kaydedilir.
- **En fazla 2 red.** Sayaç `kosu/.bekci-deneme` dosyasında tutulur. `stop_hook_active` gelirse Denetçi son kararı yine verir.
- Karar `atlandi` olabilir ama asla sessizce `kabul` sayılmaz.

> **Tam metin:** `sirket/DENETCI.md` (görevler, üçlü kontrol, karar şeması, yanlış red sınırları, örnekler).
> Bu bölüm ile dosya ayrışırsa dosya esastır.

**Nove'de değişenler:**

| Değişiklik | Neden |
|---|---|
| Yönerge: "bir içerik şirketinin bağımsız denetçisi" → **"Nove Group Yönetim Kurulu'nun bağımsız denetçisi"** | Bağlam değişti |
| Kontrol üçe ayrılır: **kaynak** (her sayının kaynağı ve `n` değeri var mı) · **hesap** (sürücünün verdiği sayıyla metindeki sayı aynı mı) · **tutarlılık** (soru ile yanıt eşleşiyor mu, önceki kararla çelişiyor mu) | Tasarımda Denetçi bu üçünü kontrol ediyor |
| Ön kontrole **telefon** ve **TC kimlik no** deseni eklenir | Hasta verisi riski (KVKK) |
| Karar JSON'una `kontrol: {kaynak, hesap, tutarlilik}` alanı eklenir, her biri `gecti`, `kaldi` ya da `uygulanmaz` olur | Sahne panelinde üç ışık olarak gösterilir |
| Denetçi `kabul` verince sürücü soruyu CEO'ya geçirir (§5) | İkinci onay kapısı |
| `bin/bekci_karsilastir.py` korunur | NIM kalitesi varsayılmaz, ölçülür (kagan-sirketi K13b) |

> **Karar (N19):** kagan-sirketi'deki yönerge metni (`bekci.py:74`) ve `docs/03-bekci.md`'deki üç ek sınır
> (madde 3–4 denetçinin konusu değil; "kaynaksız sayı" yalnız dış dünya iddiaları için geçerli; %15 sapma red sebebi değil)
> aynen alındı. Tam hâli `sirket/DENETCI.md`'de.

---

## 5 · CEO Ajanı — Bekçi'den sonraki ikinci onay

CEO Ajanı **ikinci onay kapısıdır**: Bekçi'nin `kabul` verdiği her danışman çıktısı CEO'ya da gider.
CEO çıktıyı baştan kontrol eder (double check) ve onaylar. CEO onaylamazsa çıktı kurula gitmez.

Bekçi ile CEO'nun işi aynı değildir. Biri kuralları, diğeri kararı kontrol eder:

| | Bekçi (Denetçi) | CEO Ajanı |
|---|---|---|
| Ne zaman | Danışman koşusunun sonunda (Stop hook) | Yalnız Bekçi `kabul` verdikten sonra |
| Neye bakar | **Kural:** ANAYASA + `kurallar.md`. Kaynak, hesap, tutarlılık, gizli veri | **Karar kalitesi:** soru gerçekten yanıtlandı mı, kurul bu yanıtla karar verebilir mi, sayılar taslağın kendi kaynaklarıyla tutuyor mu, Yanıt defterindeki önceki yanıtlarla çelişki var mı |
| Model | Ayrı aile (NIM → OpenAI → Haiku) | Claude **Opus**. Danışman Sonnet'te çalıştığı için CEO ondan daha güçlü bir modeldir |
| Sonuç | `kabul` / `red` | `onay` / `red` + bulgular |
| Red sonrası | Danışman aynı oturumda düzeltir (en fazla 2) | Danışman yeni bir koşuda düzeltir (en fazla 1), sonra yine Bekçi → CEO |

Temeli kagan-sirketi'deki **"patron"** tanımıdır. Patron "çıktını okur, evet/hayır der"; CEO Ajanı bu işi yapar.
Patronun diğer işleri, yani yayın düğmesi, para, hesaplar ve prod kararı, insanda kalır.

### `sirket/CEO-KIMLIGI.md` (taslak)

> **Tam metin:** `sirket/CEO-KIMLIGI.md` (görevler, girdiler, karar şeması, ölçüm kuralları, sınırlar, örnekler).
> Aşağıdaki özet ile dosya ayrışırsa dosya esastır.

```markdown
# CEO KİMLİĞİ — Nove Kurul Ofisi

Sen Nove Kurul Ofisi'nin CEO Ajanısın. Bir yapay zekâ ajanısın; Nove Group'un gerçek CEO'su değilsin
ve onun adına konuşmazsın. Önüne gelen her çıktı Denetçi'nin (Bekçi) kural kontrolünden geçmiştir.
Senin işin ikinci kontroldür: bu yanıt kurula gidecek kadar iyi mi?

## Double check — her çıktıda sırayla
1. Soru kaydını, danışmanın çıktısını ve Bekçi kararını oku.
2. Kontrol et:
   - **Yanıt:** Sorulan soru mu yanıtlandı, yoksa kolay olan yan soru mu?
   - **Sayılar:** Her önemli sayıyı danışmanın verdiği kaynak dosyada (`veri/`) bul. Bulamıyorsan bulgu yaz.
   - **Karar verilebilirlik:** Kurul bu yanıtla karar verebilir mi? (seçenek, risk, sahip, tarih)
   - **Tutarlılık:** Yanıt defterindeki önceki onaylı bir yanıtla çelişiyor mu? Çelişiyorsa fark açıklanmış mı?
3. Kararını yalnız JSON olarak ver:
   {"karar": "onay" | "red",
    "bulgular": ["red ise: danışmanın düzeltmesi gereken en fazla 3 somut madde"],
    "gerekce": "tek paragraf",
    "kurula_not": "onay ise: yanıtın başına eklenecek en fazla 2 cümle (isteğe bağlı)"}
4. Şüphedeysen `red` ver, ama bulgun somut olsun: "zayıf" değil, "2. tablodaki %18 veri/q3.txt'te yok" gibi.

## Ne yapmazsın
- Analizi kendin yeniden yazmazsın. Bulgu yazarsın, düzeltmeyi danışman yapar.
- Yeni sayı üretmezsin. Taslakta olmayan bir sayıyı kurula notuna koymazsın.
- Bekçi'nin kural kararını yeniden tartışmazsın. O kontrol yapıldı; sen karar kalitesine bakarsın.
- Mail atmazsın, mesaj göndermezsin, kişiye ya da departmana talimat vermezsin.
- Danışmanın `kurallar.md`'sini ya da ANAYASA'yı değiştirmezsin.
```

**Teknik ayrıntılar:**

- `bin/ceo.py <soru-id>` yalnız soru kaydında Bekçi kararı `kabul` ise çalışır; değilse hata verir. Bu bir testle sabitlenir.
- `kos.py`'nin `_claude_kos` yolu kullanılır. Model **`opus`**, araçlar yalnız `[Read, Glob, Grep]`, bütçe **`ayar.CEO_BUTCESI_USD`/kontrol** (geçici 1,50 USD, N31).
  CEO dosya yazamaz: JSON'u sürücü yakalar ve soru kaydına `## CEO — karar: onay/red` başlığıyla yazar.
- CEO içerik üretmediği için Stop hook'ta Bekçi'ye tabi değildir. `SIRKET_TAKIM` ayarlanmaz; bekçi bu durumda karışmaz.
  JSON şemaya uymazsa karar `red` sayılır ve "CEO yanıtı okunamadı" gerekçesi yazılır. Hiçbir zaman sessizce `onay` sayılmaz.
- Panelde iki ışık yanar: **Bekçi ✔** ve **CEO ✔**. "Danışman CEO odasına gider" animasyonu `ceo.py` başladığı an tetiklenir.
- Tasarımdaki **`ceoSorgular`** anahtarı `ayar.CEO_ACIK` değerine bağlanır. Üretimde **açık ve kilitlidir**; yalnız
  geliştirme ortamında kapatılabilir. Kapalı olduğunda yanıt "CEO kontrolü yapılmadı" etiketiyle gider.

---

## 6 · Danışman formu — yöneticilerin dolduracağı şablon

Her yöneticiye `formlar/DANISMAN-FORMU.md` gönderilir. Doldurulmuş form `formlar/gelen/<bolum>.md` olarak gelir.
Kağan revize eder ve `formlar/onayli/` altına koyar. Ardından `bin/formdan_takim.py <bolum>` dört dosyayı üretir.

Şablon ve revize kontrol listesi: `formlar/DANISMAN-FORMU.md` (§1–§6 yönetici, §7 Revize Kağan). Betik bölümleri
numarasından bulur; zorunlu alan, kişisel veri ve yetenek eksikse durur, anahtar kelime çakışmasında uyarır
(`docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md`).

---

## 7 · ANAYASA — Nove versiyonu (İNSANIN)

kagan-sirketi'nin beş maddesi temel alındı. Revize 13.10.2026'da yapıldı (N24–N26).

> **Tam metin:** `ANAYASA.md`. Aşağıdaki özet ile dosya ayrışırsa dosya esastır. Dosyayı yalnız insan değiştirir.

1. **Yayın düğmesi insanın.** Hiçbir ajan mail atmaz, mesaj göndermez, bir kişiye ya da departmana talimat
   vermez. Panelde soranın masasına giden yanıt yayın sayılmaz; kurul dışına taşımak insanın kararıdır (N22).
   Veri kaynakları salt okunurdur. Danışman yalnız kendi klasörüne yazar: `cikti/`, `kosu/`, `defter.md` (N26).
2. **Kaynaksız sayı yok.** Etiket (✅/🟡/⛔) cümleye değil iddiaya konur. Dış dünya sayısının kaynağı,
   örneklemden türeyen sayının `n`'i yazılır (N24, N19 ile aynı sınır). Teyitsiz formül kullanılmaz.
   Hasta ve müşterinin telefonu, e-postası ve TC kimlik numarası hiçbir yerde yazılmaz; ad soyad yazılabilir,
   ad soyad taşıyabilen dosya herkese açık depoya girmez (N30).
3. **İki onay.** Üreten kendi işini onaylayamaz. Kurula giden her yanıt önce Denetçi'den (ayrı aile), sonra CEO'dan geçer.
4. **Her koşunun tavanı var.** Her koşunun, her sorunun ve her günün tavanı vardır; tavana çarpan sessiz kalmaz.
   Rakamlar anayasada değil, yalnız `bin/ayar.py`'de ve §9'da durur (N25).
5. **Defter ajanın, kural insanın.** `ANAYASA.md`, `kurallar.md`, `formlar/onayli/` ve `CEO-KIMLIGI.md`
   yalnız insan tarafından değişir. Danışmanlar birbirine yazmaz. Zinciri İş Dağıtımcı kurar.

---

## 8 · Sunucu mimarisi

```
  Tarayıcı (yönetici) ──HTTPS──► Caddy (TLS, yalnız şirket ağı / VPN)
                                              │
                                              ▼
                                   bin/panel.py  (127.0.0.1:8770)
                                   sahne.py'den türer: POST giriş/çıkış (e-posta + şifre, N11),
                                   GET durum, POST soru, SSE olay akışı
                                              │ yazar: gelen/<soru-id>.json
                                              ▼
            systemd: nove-dinleyici.service   bin/soru_kapisi.py --dinle → dagitici.py → kos.py
            systemd: nove-sabah.timer 09:00   bin/gunluk.py --sabah
            systemd: nove-aksam.timer 22:00   bin/gunluk.py --aksam
                                              │
                                   claude -p (Sonnet: danışman · Opus: CEO)
                                   Stop hook → bekci.py (NIM → OpenAI → Haiku)
```

- **Henüz yazılmayanlar:** `panel.py` ve `soru_kapisi.py --dinle` Faz 5'te gelir; bugün soru komut satırından
  `soru_kapisi.py --yeni` ile girer. `gunluk.py`'deki `ZAMANLI` boştur: sabah ve akşam zamanlayıcıları yalnız
  `sirket-log/rapor/`'a rapor yazar; bir danışman formunda "Tempo" istenmedikçe zamanlı koşu başlatmaz.
- **İşletim sistemi:** Linux (Ubuntu 24.04 LTS önerilir). `kos.py`'nin `fcntl` kilidi Linux'ta olduğu gibi çalışır.
  `zamanla.py`'nin launchd kısmı yerine **systemd timer** kullanılır (`deploy/` altında).
- **Claude Code kimliği:** Sunucuda kişisel abonelik oturumu **kullanılmaz.** Nove'nin Anthropic Console
  organizasyonundan bir `ANTHROPIC_API_KEY` alınır. Böylece maliyet şirket hesabına yazılır ve kişiye bağlı kalmaz.
- **Kullanıcı:** Sistem ayrı bir `nove-ajan` Linux kullanıcısıyla çalışır. Repo bu kullanıcıya aittir ve `.env` dosyasının izni `600` olur.
- **Panel:** `panel/` altında (§8c). `ofis3d-v4.js` Claude Design'dan birebir alındı; v4 bileşeninin mantığı (soru akışı, ajan kartı,
  Yanıt defteri) `panel.js`'te düz JavaScript'e çevrildi. Şu an demo verisiyle dönen akış, `panel.py`'nin SSE olaylarına bağlanır.
  Orijinal `Nove Kurul Ofisi 3D v4.dc.html` ve `support.js` henüz dışa aktarılmadı; Claude Design 14 Aralık'ta Artifacts'a
  taşınacağı için **bu tarihten önce dışa aktarılmaları gerekir.**
- **Erişim:** Panel yalnız şirket ağından ya da VPN'den açılır. Herkese açık internete açılmaz.

---

### 8a · CRM → Zil

```
CRM ── "satış yapıldı" olayı ──► bin/crm_zil.py  (LLM yok, salt okunur)
                                   │ olay id'siyle tekilleştir, temsilci kimliğini maskele
                                   ▼
                          sirket-log/zil.jsonl ──► panel.py SSE ──► sahnede bir temsilci zile gider
```

- **Hangi programa bağlanacağı henüz belli değil (S1).** Bağlantı katmanı bu yüzden programdan bağımsız kurulur:
  `crm_zil.py` tek tip bir olay bekler (`{olay_id, zaman, masa}`) ve her program için küçük bir çevirici yazılır.
- **İki bağlantı yolu vardır.** CRM webhook gönderebiliyorsa `panel.py` üzerinde `POST /api/crm/satis` açılır
  ve paylaşılan bir sırla doğrulanır. Gönderemiyorsa `crm_zil.py --yokla` her 2 dakikada bir CRM API'sini
  **yalnız okuma** yetkili bir anahtarla sorgular (systemd timer).
- Zil olayı **ajan tetiklemez** ve para harcamaz. Tavanlara (§9) sayılmaz.
- Olaya yalnız şunlar yazılır: olay id'si, zaman ve temsilcinin sahnedeki masa numarası. Satış tutarı yazılmaz.
  **Müşteri ve hasta bilgisi hiç alınmaz. Temsilci adı gösterilmez (N9).**
- `.env` anahtarları: `CRM_API_URL`, `CRM_READONLY_TOKEN` ya da `CRM_WEBHOOK_SECRET`.
- Panelde sayaç gösterilir: "ZİL · bugün N satış". Satış Müdürü danışmanı isterse aynı veriyi kendi `veri/` klasörüne
  özet olarak alabilir; bunun için CRM'e ayrı bir bağlantı açılmaz.

### 8b · Kurul üyesi yetkisi ve Yanıt defteri

- Kurul üyesi **yalnız iki şey yapabilir:** soru sormak ve kendi yanıtını okumak. Danışman formlarını,
  koşu kayıtlarını, Bekçi/CEO gerekçelerinin ayrıntısını, ayarları ve diğer üyelerin sorularını **göremez**.
  Bunlar yalnız yönetici (Kağan) rolüne açıktır.
- Panelde iki rol vardır: `kurul` ve `yonetici`. Roller `deploy/roller.json` dosyasında e-posta → rol eşlemesiyle tutulur
  ve girişte doğrulanan e-posta bu dosyayla eşlenir. Yetki ayrıntıları gelince (S2) bu dosya genişletilir.
- **Yanıt defteri** her onaylı yanıt için bir kayıt tutar: soru, soran, tarih, cevaplayan danışman,
  Bekçi ✔ ve CEO ✔ işaretleri, yanıt metni, kaynaklar. Onaylanamayan sorular da "onaylanamadı" etiketiyle listelenir.
- Kurul üyesi Yanıt defterinde **yalnız kendi sorularını** görür (N10). Yönetici rolündeki kişi hepsini görür.
- Yanıt defterini yalnız sürücü yazar (`yanit_defteri.py`). Ajanlar ve panel kullanıcıları kayıt silemez ve değiştiremez.

---

### 8c · Panel girişi (N11)

Panel tek sayfadır (`panel/index.html`). Akış: **dönen dünya + giriş formu → "Hoş geldin, <ad>" → Kurul Ofisi.**

```
panel/
├── index.html      işaretleme: giriş sahnesi + Kurul Ofisi
├── stil.css        renk ve yazı belirteçleri, sahne ve panel stilleri
├── panel.js        dünya ve geçişler, giriş, soru akışı / ajan kartı / Yanıt defteri
└── ofis3d-v4.js    3D ofis (Claude Design'dan birebir; Three.js 0.160'ı unpkg'den yükler)
```

- **Giriş ucu:** `POST /api/giris` gövdesi `{"eposta", "sifre"}`. Başarıda `200 {"ad", "basHarf", "rol"}` ve
  `HttpOnly; Secure; SameSite=Strict` oturum çerezi döner. Yanlış bilgide `401`, çok denemede `429`. Panel bu üç durumu
  kullanıcıya ayrı mesajla gösterir; sunucuya ulaşılamazsa da ayrı mesaj verir.
- **Çıkış ucu:** `POST /api/cikis` oturumu kapatır; panel giriş ekranına döner.
- **Şifre saklama:** Düz metin tutulmaz; `panel.py` Python stdlib'deki `hashlib.scrypt` ile özet saklar. Kullanıcı ve özet dosyası
  git'e girmez ve izni `600`'dür. Dağıtım ve sıfırlama N23'e göre: yönetici ekler, ilk girişte geçici şifre değişir.
- **Rol:** `/api/giris` yanıtındaki `rol` (`kurul` | `yonetici`) `deploy/roller.json`'dan gelir (§8b). `panel.js` rolü henüz
  kullanmıyor; süzme (ör. Yanıt defteri, N10) sunucuda yapılır.
- **Demo modu:** Sayfa dosyadan açılırsa (`file://`) ya da adres `?demo` ile açılırsa her e-posta ve şifre kabul edilir ve
  `#ofis` bağlantısı girişi atlar. Bu yalnız tarayıcıdaki görünümü açar; güvenlik sınırı `panel.py`'dir: oturum çerezi olmadan
  hiçbir uç veri döndürmez. Üretimde `panel.js`'teki `DEMO` bayrağı `false` sabitlenir.
- **Yerelde açmak:** `cd panel && python3 -m http.server 8000` → `http://127.0.0.1:8000/?demo`

---

## 9 · Tavanlar (`bin/ayar.py`) — ilk ay bilerek muhafazakâr

| Ayar | kagan-sirketi | Nove başlangıç | Not |
|---|---|---|---|
| Mesai | 09:00–23:00 | 08:00–20:00, haftanın her günü | Dışında gelen soru sabaha kalır; soran kişi bunu panelde görür |
| Danışman koşusu | 2 USD / 15 dk | 2 USD / 15 dk | Aynı kalır |
| CEO kontrolü | — | **1,50 USD** / 5 dk | Opus kullanılır. **Geçici** — Faz 4 beş gerçek soruda ölçülecek (N31) |
| **Soru başına toplam** | — | **8 USD** | Danışman + düzeltme + Bekçi + CEO. En kötü yol 2 + 1,5 + 2 + 1,5 = 7 USD; 1 USD Denetçi ve pay (N27, N31) |
| Kurul üyesi başına gün | — | 10 soru | Kötüye kullanım freni |
| Danışman başına gün | 2 koşu | 15 koşu | Soru akışı olaylıdır, takvimli değildir |
| Şirket günü | 5 USD | **40 USD** | İlk ay ölçülür (`sirket-log/rapor/`), sonra karar verilir |
| **Şirket ayı (en kötü)** | — | **1.200 USD** | 30 gün × 40 USD; sistem hafta sonu da çalışır (N29). Anthropic Console'daki aylık harcama limiti bu rakama ayarlanır |
| Eşzamanlı koşu | 2 | 3 | Sunucu kapasitesine göre ayarlanır |

---

## 10 · Kurulum adımları — fazlar halinde

Her faz, bir öncekinin çalıştığı görüldükten sonra açılır (kagan-sirketi K11).

### Faz 0 · Sunucu hazırlığı
> **Durum (09.10.2026):** başlamadı — şirketten kaynak bekliyor (API anahtarı, NIM, sunucu, S4). Faz 1–3 beklemeden yerelde ilerler.

```bash
sudo adduser --system --group --home /srv/nove-kurul nove-ajan
sudo apt install -y python3 git caddy
# Node + Claude Code
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash - && sudo apt install -y nodejs
sudo npm install -g @anthropic-ai/claude-code
sudo -u nove-ajan claude --version
```
- [ ] Anthropic Console'da Nove organizasyonu ve API anahtarı (aylık harcama limiti 1.200 USD, §9)
- [ ] NVIDIA NIM anahtarı (Denetçi için)
- [ ] Panel kullanıcı listesi ve ilk şifrelerin nasıl dağıtılacağı (yöntem N23; kullanıcı listesi S2'ye bağlı)

### Faz 1 · Repo ve iskelet temizliği
> **Durum (09.10.2026):** yerelde tamamlandı — `faz-1` dalında, 266 test yeşil (8'i taşınmayan kit belgelerini aradığı için atlanıyor).
> Sunucu gelince depo `/srv/nove-kurul`'a taşınır.
>
> **Bu fazda verilen kararlar:**
> - kagan-sirketi'nin commit'lenmiş hâli kopyalandı (geçmiş ve upstream yok, N5); `LICENSE` birebir aynı.
> - Kişisel takımlar ve onlara ait betik, yetenek ve testler taşınmadı (`okr_*`, `qa_ozet`, `repo_ozet`, `claude_gecmis`,
>   5 yetenek). `qa_ozet.py` ve `qa-koclugu-kurgusu` Faz 4'te Kalite için uyarlanarak gelir.
> - **Telegram taşınmadı.** Nove'nin arayüzü panel; Q&A Danışmanı Faz 3'te yazılırken kagan-sirketi'deki
>   `telegram_dinle.py` yalnız örnek olarak okunur.
> - `dagitici.ZINCIR` ve `gunluk.ZAMANLI` boş: Nove soru odaklı; `s-`/`r-` zinciri Faz 3'te, zamanlı iş yalnız
>   bir danışman formunda "Tempo" istenirse gelir.
> - **"Kurulumda" koda girdi:** `takim.md`'si tanımsız (frontmatter'sız) danışman koşturulmaz, ajan dosyası
>   üretilmez, dağıtıma girmez (`ayar.kurulumda_mi`, `ayar.kurulu_takimlar`; `tests/test_kurulumda.py`).
> - Soru akışı sabitleri `bin/ayar.py`'ye eklendi: `SORU_BUTCESI_USD`, `KURUL_UYESI_GUNLUK_SORU`, `BEKCI_MAKS_RED`,
>   `CEO_ACIK`, `CEO_MAKS_RED`, `CEO_BUTCESI_USD`, `CEO_SURESI_SN`.

```bash
cd /srv/nove-kurul
git clone --depth 1 <kagan-sirketi özel repo> nove-kurul && cd nove-kurul
rm -rf .git && git init                   # geçmiş taşınmaz, upstream eklenmez (N5)
git remote add origin <nove-kurul özel repo>
# kişisel takımları çıkar, iskeleti bırak
git rm -r takimlar/{kasa-bakimi,haftalik-rapor,karar-takibi,qa-hatti,okr-takip} okr/ qa/
python3 -m unittest discover -s tests     # kırılan testleri bu fazda düzelt ya da kaldır
```
- [x] `LICENSE` olduğu gibi duruyor (MIT; telif satırı silinmez, değiştirilmez — lisansın tek koşulu bu)
- [x] `CLAUDE.md`, `README.md`, `ANAYASA.md` (§7), `sirket/AJAN-KIMLIGI.md` Nove'ye uyarlandı
- [x] `bin/ayar.py` tavanları §9'a göre ayarlandı
- [x] `.claude/settings.json` → `permissions.deny`: `.env`, `yanitlar/**`, `formlar/onayli/**`
- [x] `python3 bin/ayar.py` ve testler yeşil

### Faz 2 · Denetçi ve CEO
> **Durum (12.10.2026):** kod `faz-2` dalında, 314 test yeşil (8 atlanan). Kalan: NIM ölçümü (anahtar bekliyor, Faz 0)
> ve iki belgenin revizesi. `ceo.py` soru kaydını okur; kaydı ve içindeki `## Denetçi` bölümünü Faz 3'te sürücü yazar.

- [x] `sirket/DENETCI.md` ve `sirket/CEO-KIMLIGI.md` taslakları yazıldı (09.10.2026) — Kağan'ın revizesini bekliyor
- [x] `bekci.py` §4'teki değişiklikler: yönerge, üçlü kontrol, telefon/TC deseni (12.10.2026)
- [x] `tests/fikstur/bekci/` altına `telefon-sizmis.md` ve `hesap-tutmuyor.md` eklendi (12.10.2026)
- [x] `sirket/CEO-KIMLIGI.md` + `bin/ceo.py` + `tests/test_ceo.py` (yalnız Bekçi kabulünden sonra çalışır, karar şeması, bozuk JSON → red, en fazla 1 düzeltme turu)
- [ ] `python3 bin/bekci_karsilastir.py` ile NIM'in yeni fikstürlerde doğru karar verdiği görüldü

### Faz 3 · Soru akışı (panelsiz, komut satırından)
> **Durum (13.10.2026):** kod `faz-3` dalında, 414 test yeşil (8 atlanan). Sekiz adım uçtan uca testle
> kanıtlı (`tests/test_uctan_uca_soru.py`, LLM'ler sahte). Gerçek soru için gereken: `deploy/roller.json` ve en az bir
> kurulu danışman (Faz 4) — bugün bütün danışmanlar kurulumda.

- [x] `sirket/QA-DANISMANI.md` ve `sirket/IS-DAGITIMCI.md` görev tanımları yazıldı (09.10.2026) — Kağan'ın revizesini bekliyor
- [x] `bin/soru_kapisi.py`: `--yeni "<soru>" --soran <e-posta>` → `gelen/` + soru kaydı · `--ilet <id>` → Yanıt defteri (12.10.2026)
- [x] `dagitici.py`: `s-<id>` ve `r-<id>` zincir kuralları, `takim.md`'deki `anahtar_kelimeler:` alanından yönlendirme, `--cakisma` (12.10.2026)
- [x] `kos.py` soruyu danışmana verir, Denetçi taslağı denetler (`SIRKET_TASLAK`), karar soru kaydına kopyalanır (12.10.2026)
- [x] Uçtan uca: `tests/test_uctan_uca_soru.py`. Kuru koşu (`--soran` `deploy/roller.json`'daki bir e-posta olmalı):
```bash
python3 bin/soru_kapisi.py --yeni "Q3 bütçe sapmasının ana nedenleri neler?" --soran <e-posta> --kuru
python3 bin/dagitici.py --kuru
```

### Faz 4 · İlk danışman: **Kalite**
> **Durum (09.10.2026):** başlamadı — önce S7 (bütçe onayı). `takimlar/kalite/takim.md` boş duruyor.

Veri ve kurallar senin elinde olduğu için ilk danışman Kalite olur. `qa-hatti` örnek alınır: `QA_READONLY_URL`, `qa_ozet.py`
ve `qa-koclugu-kurgusu` taşınır.
- [x] **Form hattı kurulur** (Faz 1–3'te atlanmıştı, 13.10.2026'da fark edildi): `formlar/DANISMAN-FORMU.md` (§6 şablonu),
  `formlar/gelen/` (git'e girmez), `formlar/onayli/` ve `bin/formdan_takim.py` + testi. Faz 6 da aynı hattı kullanır — 19.10.2026
- [x] Kalite formunu kendin doldur; bu form diğer yöneticiler için örnek olur — 19.10.2026 (veri: SDR Analyzer API, ayrı MANAGER kullanıcı, yalnız GET; tempo pzt–cuma 11:00)
- [x] `bin/formdan_takim.py kalite` → dört dosya → `agents_uret.py` — 19.10.2026
- [x] Kalite veri okuyucusu: `bin/kalite_veri.py` — SDR Analyzer veritabanından `qa_okuyucu` rolüyle salt okunur (`QA_READONLY_URL`); alt komutlar ekipler, ekip-ozet, temsilci-ozet, kriterler, kocluk; ek sütun izni `docs/kalite-veri-izin.sql` (Kağan çalıştırdı, 20.10.2026). Haftanın çağrısı izni verilmedi.
- [x] Tutarlılık ölçümü: Raporlarım (127 / 77) ile betik (122 / 81) farkı veritabanında kayıt kayıt uzlaştırıldı — 5 `TRANSCRIPT_UNUSABLE` (0 puan) kayıt; betik SDR Analyzer PR #71 kuralını uyguluyor (22.10.2026). Kağan merge'ü buna dayandırdı; SDR Analyzer güncellemesinden (Cuma) sonra panelde 122 / 81 bir kez görülecek
- [ ] Günlük rapor zamanlayıcısı: pzt–cuma, 11:00'de kurula ulaşacak şekilde (`gunluk.ZAMANLI`); pazartesi = cuma–pazar
- [ ] Beş gerçek soruyla uçtan uca gerçek koşu yapılır. Maliyet ve Denetçi/CEO kararları kayda bakılarak gözden geçirilir
  - Aynı adımda `python3 bin/bekci_karsilastir.py` (8 fikstür): Denetçi istemi 19.10.2026'da iki kez değişti
    (K7 personel adı, N30 ad soyadı); `hasta-ad-soyadi` `kabul` almalı. Kağan, 19.10.2026: ölçüm buraya ertelendi
  - Aynı adımda CEO kontrolünün gerçek maliyeti kayıtlardan okunur; `ayar.CEO_BUTCESI_USD`'nin kalıcı değeri
    buna göre konur (N31, şimdi geçici 1,50 USD)

### Faz 5 · Panel
> **Durum (09.10.2026):** kısmen — panel demo verisiyle çalışıyor; `panel.py` yok.

- [x] Giriş ekranı ve Kurul Ofisi `panel/` altında, demo verisiyle çalışıyor (09.10.2026)
- [ ] Orijinal `.dc.html` + `support.js` Claude Design'dan dışa aktarıldı (14 Aralık'tan önce)
- [ ] `bin/panel.py`: `sahne.py` temel alınır. `POST /api/giris`, `POST /api/cikis` (§8c), `POST /api/soru`, `GET /api/durum`, `GET /api/olaylar` (SSE), `GET /api/yanitlar` (role göre süzülür), `POST /api/crm/satis`
- [ ] "Soru akışı" kartı soru kaydından, "Ajan kartı" `takim.md` + `durum.json` + `defter.md`'den beslenir
- [ ] `otomatikDemo` yalnız demo ortamında açılır, üretimde kapalı kalır
- [ ] Caddy + systemd birimleri (`deploy/`)

### Faz 6 · Yönetici danışmanları
> **Durum (09.10.2026):** başlamadı — `takim.md` dosyaları boş açıldı.

- [ ] Formlar gönderildi: Finans, OKR, Raporlama, Satış Müdürü (+ boş odalar)
- [ ] Her form gelince: revize → `onayli/` → `formdan_takim.py` → kuru koşu → 3 gerçek soru → devreye alma
- [ ] Bir danışman ancak **verisi bağlıysa** devreye girer. Verisi olmayan danışman sahnede "kurulumda" olarak görünür

### Faz 7 · Satış ekibi ve zil — S1 netleşince açılır
> **Durum (09.10.2026):** kapalı — S1 bekliyor.

- [ ] CRM bağlantısı kurulur (§8a): salt okunur API anahtarı ya da webhook → `bin/crm_zil.py` → `sirket-log/zil.jsonl` → panelde zil olayı
- [ ] Test: sahte bir "satış yapıldı" olayı zili bir kez çaldırır. Aynı olay iki kez gelirse zil ikinci kez çalmaz

---

## 11 · Açık sorular — revizede karar bekleyenler

| # | Soru | Neden önemli |
|---|---|---|
| S1 | Zil hangi programa bağlanacak (CRM ya da başka bir program)? Webhook mu, periyodik sorgu mu? | **Beklemede.** Kağan karar verince çevirici yazılır; Faz 7 o zamana kadar açılmaz |
| S2 | Kurul üyesi yetkisinin diğer ayrıntıları (kimler üye, herkes her danışmana soru sorabilir mi) | Kağan paylaşacak. Görünürlük kararı verildi (N10) |
| S4 | Sunucu Nove Finans ile aynı makine mi olacak? | Ortak `.env` ve ortak kullanıcı **olmamalı** |
| S7 | Tavanlar (§9) yönetimle konuşuldu mu? | Bütçe onayı Faz 4'ten önce gerekir. Götürülecek öneri hazır: §9, ayda en fazla 1.200 USD (13.10.2026) |

S3, S5, S6 ve S8 13.10.2026'daki revizede kapandı: N20–N23.

---

## 12 · Kabul ölçütü — "kuruldu" ne demek

- [ ] `python3 -m unittest discover -s tests` sonucu yeşil
- [ ] Kurul üyesi panelden soru sorar; düzeltme turu geçirmeyen soruda yanıt 30 dakika içinde kendi masasına düşer (N28).
  Düzeltmedeki soru için süre sözü verilmez, soran durumu panelde görür
- [ ] Her yanıtın soru kaydında şunlar görünür: dağıtım gerekçesi, Bekçi kararı (üçlü kontrol), CEO kararı ve maliyet
- [ ] Bekçi'nin reddettiği hiçbir çıktı CEO'ya ulaşmaz; CEO'nun onaylamadığı hiçbir çıktı kurula ulaşmaz (test fikstürleriyle kanıtlanır)
- [ ] Hiçbir ajan mail, mesaj ya da prod yazımı yapamaz. Bu, kuralla değil **yetkiyle** sağlanır (deny listesi + salt okunur roller)
- [ ] `kurul` rolündeki bir kullanıcı yalnız soru sorabilir ve kendi yanıtlarını görebilir (panel testiyle kanıtlanır)
- [ ] Panele yalnız e-posta + şifreyle girilir; şifreler düz metin saklanmaz, yanlış şifre `401` döner, oturum çıkışla kapanır (panel testiyle kanıtlanır)
- [ ] CRM'den gelen bir satış zili bir kez çaldırır
- [ ] İlk ayın sonunda `sirket-log/rapor/` altından gerçek maliyet raporu çıkarılır ve tavanlar yeniden ayarlanır
- [ ] KR 1.1 kanıtı: kurulu danışman sayısı, koşu kayıtları ve soru kayıtları
