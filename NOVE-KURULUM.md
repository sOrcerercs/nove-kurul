# NOVE KURUL OFİSİ — Kurulum Belgesi

> Nove Group yöneticileri için ajan ekosistemi. Kurul üyesi soru sorar; danışman ajanlar analiz eder,
> Denetçi (Bekçi) kuralları denetler, CEO Ajanı double check yapıp onaylar. **Yayın düğmesi yine insandadır.**
>
> Hazırlayan: Kağan Öztürk · Taslak: 09.10.2026 · Durum: **taslak — Kağan'ın son revizesini bekliyor**

---

## 0 · Bu belge neye dayanıyor

| Kaynak | Ne alındı |
|---|---|
| `~/kagan-sirketi` (VS Code projesi) | **Başlangıç noktası.** Sürücü katmanı, bekçinin NIM → OpenAI → Haiku sırası, karar defteri, Telegram komut kapısı, `sahne/` paneli, 430 test. **Denetçi** tanımı (`bin/bekci.py`, `docs/03-bekci.md`), **patron** tanımı (`sirket/AJAN-KIMLIGI.md`, CEO'nun temeli) ve ANAYASA'nın beş maddesi |
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

---

## 1 · Rol haritası — tasarımdaki her kişi neye karşılık geliyor

| Tasarımdaki rol | Ne yapar (tasarım) | Teknik karşılığı | Dosya |
|---|---|---|---|
| **Kurul üyesi** (insan) | Soruyu sorar, yanıtı okur | Panel kullanıcısı (e-posta + şifre girişi, N11) | — |
| **Q&A Danışmanı** | Soruyu alır, kayda geçirir; sonunda yanıtı kurula iletir | Giriş/çıkış kapısı. **LLM çağırmaz** — `telegram_dinle.py` ve `sahne.py` POST'unun birleşimi | `bin/soru_kapisi.py` |
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
  çıktı yeniden Bekçi'den ve CEO'dan geçer. İkinci `red` gelirse yanıt kurula gönderilmez. Soranın panelinde
  "onaylanamadı" etiketi ve CEO'nun gerekçesi görünür, böylece soru sessizce kaybolmaz.
- Tasarımdaki 8 adımla eşleşme: "CEO sorgular" → double check, "Danışman revize eder" → CEO red sonrası düzeltme,
  "CEO son kararı verir" → ikinci kontroldeki onay/red.
- Bir sorunun tamamı tek bir **soru kaydında** toplanır: `sirket-log/sorular/<soru-id>.md`. Kimin ne yaptığı,
  Bekçi kararları, CEO kararı ve bulguları ve maliyet bu dosyada yer alır. Sahnedeki "Soru akışı" paneli bu dosyayı okur.
- Birden fazla danışmanı ilgilendiren soru (ör. "Q3 bütçe sapması" hem Finans'ı hem OKR'ı ilgilendirir):
  İş Dağıtımcı **ana danışmanı** seçer, diğerini `öneri:` satırı olarak kayda yazar. Faz 1'de çoklu danışman yoktur.

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
├── formlar/
│   ├── DANISMAN-FORMU.md      yöneticilere giden boş şablon (§6)
│   ├── gelen/                 doldurulmuş formlar — git'e GİRMEZ
│   └── onayli/                Kağan'ın revize ettiği formlar
├── yanitlar/                  Yanıt defteri — yalnız sürücü yazar
├── skills/<ad>/SKILL.md
├── bin/                       kos · bekci · ceo · dagitici · soru_kapisi · yanit_defteri · crm_zil · panel · ayar · …
├── panel/                     arayüz: giriş gezegeni + Kurul Ofisi 3D v4 (index.html · stil.css · panel.js · ofis3d-v4.js)
├── sirket-log/                sorular/ · rapor/ · telemetri — git'e GİRMEZ
├── deploy/                    systemd birimleri, Caddy ayarı
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

> **Kağan'a:** kagan-sirketi'de `bekci.py:74`'teki yönerge metnini ve `docs/03-bekci.md`'deki üç ek sınırı
> (madde 3–4 denetçinin konusu değil; "kaynaksız sayı" yalnız dış dünya iddiaları için geçerli; %15 sapma red sebebi değil)
> aynen alıyorum. Değiştirmek istediğin bir yer varsa revizede belirt.

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
- `kos.py`'nin `_claude_kos` yolu kullanılır. Model **`opus`**, araçlar yalnız `[Read, Glob, Grep]`, bütçe **0,50 USD/kontrol**.
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

```markdown
# Danışman Formu — <Bölüm adı>

> Bu formu bölüm yöneticisi doldurur. Son hâlini Kağan verir. Bilmediğin alanı boş bırak,
> "?" yaz — uydurma. Hasta/müşteri adı, telefon, e-posta YAZMA.

## 1. Kimlik
- Danışman adı (odada görünecek):            ör. "Finans"
- Bölüm yöneticisi (sahibi):                  ad, unvan
- Tek cümleyle mesleği:                       "Finans danışmanı olarak kurulun bütçe, nakit ve
                                               maliyet sorularını muhasebe verisiyle yanıtlamak."
- Sahnedeki rengi (isteğe bağlı):             ör. yeşil

## 2. Hangi soruları alır
- Bu danışmana gelmesi gereken 5 örnek soru:
  1.
  2.
- Anahtar kelimeler (İş Dağıtımcı bunlarla yönlendirir):  bütçe, nakit, maliyet, sapma, …
- Bu danışmana GELMEMESİ gereken, karışabilecek sorular:

## 3. Veri
| Kaynak | Ne var içinde | Nerede (sistem/dosya) | Kim erişim verir | Ne sıklıkta güncellenir |
|---|---|---|---|---|
|  |  |  |  |  |

- Bu verideki hassas alanlar (KVKK):
- Formülü/tanımı herkesçe bilinmeyen göstergeler (ör. "upsell oranı nasıl hesaplanır"):

## 4. Kurallar (kurallar.md'ye gidecek)
- Bu danışman ASLA şunu yapmamalı:
- Her yanıtta mutlaka olması gereken:
- Hangi sayıyı kim teyit eder:

## 5. İyi yanıt nasıl görünür
- Kurula giden ideal yanıtın bir örneği (yarım sayfa yeter):

## 6. Tempo (isteğe bağlı)
- Soru beklemeden düzenli üretmesini istediğin bir rapor var mı? (ör. "her pazartesi bütçe sapması")
```

**Kağan'ın revize kontrol listesi** (`formlar/onayli/`'ye almadan önce):

- [ ] Mesleği tek cümle ve bir fiille bitiyor (`description` alanı bu cümle olur)
- [ ] Anahtar kelimeler diğer danışmanlarla çakışmıyor (`python3 bin/dagitici.py --cakisma` ile kontrol edilir)
- [ ] Her veri kaynağı **salt okunur** bir yolla bağlanabiliyor (SELECT rolü, dışa aktarım, paylaşılan klasör)
- [ ] Formülü teyitsiz gösterge `—` olarak işaretli ve teyit sahibi yazılı
- [ ] Formda kişisel veri yok
- [ ] Gereken en az bir yetenek seçilmiş (`skills:` boş kalırsa testler kırmızı verir)

---

## 7 · ANAYASA — Nove versiyonu (taslak, İNSANIN)

kagan-sirketi'nin beş maddesi temel alınır. Değişiklikler **kalın** yazılmıştır.

1. **Yayın düğmesi insanın.** Hiçbir ajan mail atmaz, mesaj göndermez, bir kişiye ya da departmana
   talimat vermez. **Panelde soranın masasına giden yanıt yayın sayılmaz**; o yanıtı kurul dışına
   taşımak insanın kararıdır. Veri kaynakları salt okunurdur, prod'a yazma yoktur.
2. **Kaynaksız sayı yok.** ✅/🟡/⛔ etiketi kullanılır, her sayının yanında `n` yazar, teyitsiz formül
   kullanılmaz. **Hasta ve müşteri adı, telefonu, e-postası ve TC kimlik numarası hiçbir yerde yazılmaz;**
   personel adı yalnız `kurallar.md` açıkça izin veriyorsa yazılır (kagan-sirketi'ndeki qa-hatti muafiyeti gibi).
3. **İki onay.** Üreten kendi işini onaylayamaz. **Kurula giden her yanıt önce Denetçi'den (ayrı aile), sonra CEO'dan (double check) geçer.**
4. **Her koşunun tavanı var.** Tavanlar §9'daki tablodadır. **Her soru bir bütçe taşır**; soru tavanı aşarsa
   sorunun sahibi panelde bunu görür.
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
  git'e girmez ve izni `600`'dür. Dağıtım ve sıfırlama S8'de.
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
| Mesai | 09:00–23:00 | 08:00–20:00 | Dışında gelen soru sabaha kalır; soran kişi bunu panelde görür |
| Danışman koşusu | 2 USD / 15 dk | 2 USD / 15 dk | Aynı kalır |
| CEO kontrolü | — | 0,50 USD / 5 dk | Opus kullanılır |
| **Soru başına toplam** | — | **5 USD** | Danışman + düzeltme + Bekçi + CEO toplamı |
| Kurul üyesi başına gün | — | 10 soru | Kötüye kullanım freni |
| Danışman başına gün | 2 koşu | 15 koşu | Soru akışı olaylıdır, takvimli değildir |
| Şirket günü | 5 USD | **40 USD** | İlk ay ölçülür (`sirket-log/rapor/`), sonra karar verilir |
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
- [ ] Anthropic Console'da Nove organizasyonu ve API anahtarı (aylık harcama limitiyle)
- [ ] NVIDIA NIM anahtarı (Denetçi için)
- [ ] Panel kullanıcı listesi ve ilk şifrelerin nasıl dağıtılacağı (S8)

### Faz 1 · Repo ve iskelet temizliği
> **Durum (09.10.2026):** başladı — yerelde, `~/Desktop/Nove AI` deposunun `faz-1` dalında. Sunucu gelince depo `/srv/nove-kurul`'a taşınır.

```bash
cd /srv/nove-kurul
git clone --depth 1 <kagan-sirketi özel repo> nove-kurul && cd nove-kurul
rm -rf .git && git init                   # geçmiş taşınmaz, upstream eklenmez (N5)
git remote add origin <nove-kurul özel repo>
# kişisel takımları çıkar, iskeleti bırak
git rm -r takimlar/{kasa-bakimi,haftalik-rapor,karar-takibi,qa-hatti,okr-takip} okr/ qa/
python3 -m unittest discover -s tests     # kırılan testleri bu fazda düzelt ya da kaldır
```
- [ ] `LICENSE` olduğu gibi duruyor (MIT; telif satırı silinmez, değiştirilmez — lisansın tek koşulu bu)
- [ ] `CLAUDE.md`, `README.md`, `ANAYASA.md` (§7), `sirket/AJAN-KIMLIGI.md` Nove'ye uyarlandı
- [ ] `bin/ayar.py` tavanları §9'a göre ayarlandı
- [ ] `.claude/settings.json` → `permissions.deny`: `.env`, `yanitlar/**`, `formlar/onayli/**`
- [ ] `python3 bin/ayar.py` ve testler yeşil

### Faz 2 · Denetçi ve CEO
> **Durum (09.10.2026):** belge kısmı hazır (`sirket/DENETCI.md`, `sirket/CEO-KIMLIGI.md`); kod Faz 1'den sonra.

- [x] `sirket/DENETCI.md` ve `sirket/CEO-KIMLIGI.md` taslakları yazıldı (09.10.2026) — Kağan'ın revizesini bekliyor
- [ ] `bekci.py` §4'teki değişiklikler: yönerge, üçlü kontrol, telefon/TC deseni
- [ ] `tests/fikstur/bekci/` altına `telefon-sizmis.md` ve `hesap-tutmuyor.md` eklendi
- [ ] `sirket/CEO-KIMLIGI.md` + `bin/ceo.py` + `tests/test_ceo.py` (yalnız Bekçi kabulünden sonra çalışır, karar şeması, bozuk JSON → red, en fazla 1 düzeltme turu)
- [ ] `python3 bin/bekci_karsilastir.py` ile NIM'in yeni fikstürlerde doğru karar verdiği görüldü

### Faz 3 · Soru akışı (panelsiz, komut satırından)
> **Durum (09.10.2026):** belge kısmı hazır (`sirket/QA-DANISMANI.md`, `sirket/IS-DAGITIMCI.md`); kod Faz 2'den sonra.

- [x] `sirket/QA-DANISMANI.md` ve `sirket/IS-DAGITIMCI.md` görev tanımları yazıldı (09.10.2026) — Kağan'ın revizesini bekliyor
- [ ] `bin/soru_kapisi.py`: `--yeni "<soru>" --soran <kişi>` → `gelen/` + soru kaydı · `--ilet <id>`
- [ ] `dagitici.py`: `s-<id>` ve `r-<id>` zincir kuralları, `takim.md`'deki `anahtar_kelimeler:` alanından yönlendirme, `--cakisma`
- [ ] Uçtan uca kuru koşu:
```bash
python3 bin/soru_kapisi.py --yeni "Q3 bütçe sapmasının ana nedenleri neler?" --soran test --kuru
python3 bin/dagitici.py --kuru
```

### Faz 4 · İlk danışman: **Kalite**
> **Durum (09.10.2026):** başlamadı — önce S7 (bütçe onayı). `takimlar/kalite/takim.md` boş duruyor.

Veri ve kurallar senin elinde olduğu için ilk danışman Kalite olur. `qa-hatti` örnek alınır: `QA_READONLY_URL`, `qa_ozet.py`
ve `qa-koclugu-kurgusu` taşınır.
- [ ] Kalite formunu kendin doldur; bu form diğer yöneticiler için örnek olur
- [ ] `bin/formdan_takim.py kalite` → dört dosya → `agents_uret.py`
- [ ] Beş gerçek soruyla uçtan uca gerçek koşu yapılır. Maliyet ve Denetçi/CEO kararları kayda bakılarak gözden geçirilir

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
| S3 | "Yanıt defteri" adı uygun mu? (Alternatifler: "Yanıtlar", "Kurul arşivi") | Yalnız etiket değişir; yapı aynı kalır |
| S4 | Sunucu Nove Finans ile aynı makine mi olacak? | Ortak `.env` ve ortak kullanıcı **olmamalı** |
| S5 | Yanıt dili hep Türkçe mi? (Satış ekibinde yabancı dil konuşan danışmanlar var) | `kurallar.md`'ye girer |
| S6 | Danışman yanıtları kurul dışına (ör. bölüm yöneticisine) otomatik kopyalansın mı? | Evet denirse bu bir "yayın" olur; ANAYASA §1 gereği şu an **hayır** |
| S7 | Tavanlar (§9) yönetimle konuşuldu mu? | Bütçe onayı Faz 4'ten önce gerekir |
| S8 | Panel şifreleri nasıl dağıtılır ve sıfırlanır? Öneri: yönetici kullanıcıyı ekler, ilk girişte geçici şifre değiştirilir, şifresini unutan yöneticiye başvurur (Nove PYS'deki yöntem). E-posta altyapısı gerekmez | N11 ile Google girişi bırakıldı; şifre yaşam döngüsü artık panelin işi |

---

## 12 · Kabul ölçütü — "kuruldu" ne demek

- [ ] `python3 -m unittest discover -s tests` sonucu yeşil
- [ ] Kurul üyesi panelden soru sorar, 15 dakika içinde yanıt kendi masasına düşer
- [ ] Her yanıtın soru kaydında şunlar görünür: dağıtım gerekçesi, Bekçi kararı (üçlü kontrol), CEO kararı ve maliyet
- [ ] Bekçi'nin reddettiği hiçbir çıktı CEO'ya ulaşmaz; CEO'nun onaylamadığı hiçbir çıktı kurula ulaşmaz (test fikstürleriyle kanıtlanır)
- [ ] Hiçbir ajan mail, mesaj ya da prod yazımı yapamaz. Bu, kuralla değil **yetkiyle** sağlanır (deny listesi + salt okunur roller)
- [ ] `kurul` rolündeki bir kullanıcı yalnız soru sorabilir ve kendi yanıtlarını görebilir (panel testiyle kanıtlanır)
- [ ] Panele yalnız e-posta + şifreyle girilir; şifreler düz metin saklanmaz, yanlış şifre `401` döner, oturum çıkışla kapanır (panel testiyle kanıtlanır)
- [ ] CRM'den gelen bir satış zili bir kez çaldırır
- [ ] İlk ayın sonunda `sirket-log/rapor/` altından gerçek maliyet raporu çıkarılır ve tavanlar yeniden ayarlanır
- [ ] KR 1.1 kanıtı: kurulu danışman sayısı, koşu kayıtları ve soru kayıtları
