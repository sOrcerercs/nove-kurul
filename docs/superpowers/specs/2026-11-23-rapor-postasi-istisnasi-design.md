---
durum: yazildi
guncelleme: 2026-11-23
dal: feature/rapor-postasi
pr: 31 (metin) · betik: -
bekleyen: kullanici — metni ANAYASA.md §1 sonuna işlemek
onay: Kağan, 23.11.2026 (seçenek A — yalnız haber)
---

# Rapor postası — ANAYASA istisnası

> Yalnız anayasa metni. Postayı gönderen betik (`bin/rapor_postasi.py`) ayrı bir iş; gönderen adres ve SMTP
> bilgisi gelince planlanır. `ANAYASA.md` insanın dosyasıdır: metni Kağan işler.

## Neden

ANAYASA §1 "Hiçbir ajan mail atmaz" der. Kağan'ın planı (22.10.2026): Kurul Ofisi'nin bir mail adresi olsun,
yöneticilere günlük, haftalık, aylık ve gerekirse anlık raporlar ulaşsın. Bunu bekleyenler: Kalite günlük raporu
(11:00), satış ve hedef raporları, yorum takip ajanının olumsuz yorum uyarısı. Her özelliğe ayrı istisna yazmak
yerine tek genel istisna.

## Seçenekler

| | Mailde ne gider | Artısı | Eksisi |
|---|---|---|---|
| **A — yalnız haber (seçildi)** | Rapor/uyarı adı, tarih, panel bağlantısı | Rakam ve ad panelde kalır; ileri gönderilen mail veri taşımaz; metin kısa ve sıkı | Okumak için panele girmek gerekir |
| B — raporun tamamı | Onaylı rapor metni | Telefondan tek bakış | Hasta adı ve personel puanı posta kutularında; §2'ye ek kural gerekir |

Kağan, 23.11.2026: **A**. Gerekçe: "yayın düğmesi insanın" ilkesine en yakın olanı; panel tek okuma yeri, mail
yalnız haber verir.

## Metin (ANAYASA §1 sonuna)

```markdown
**İstisna — rapor postası (revize GG.AA.2026):** Panelde hazır olan bir raporun ya da uyarının **haberini**
  Kurul Ofisi'nin tek gönderen adresi mail ile iletir; bunu yalnız `bin/rapor_postasi.py` yapar, ajan mail atmaz.
  Mailde yalnız raporun ya da uyarının adı, tarihi ve panel bağlantısı bulunur: rakam, ad soyad, rapor metni ve
  ek bulunmaz; okuma panelde, girişle yapılır. Alıcılar rapor türüne göre `deploy/posta-alicilari.json`'da
  tutulur; listeyi yalnız insan değiştirir, ajan alıcı seçemez, ekleyemez. Listede olmayan kişiye, gruba ya da
  şirket dışına gönderim yoktur. Haber yalnız iki onaydan (§3) geçmiş bir rapor ya da kuralla (LLM'siz) üretilmiş
  bir uyarı için gider. Gönderim tavanı `bin/ayar.py`'dedir (§4). Maile gelen yanıtları ajan okumaz; mail bir
  talimata ya da yayına dönüşmez.
```

## Kararlar (Claude'un, Kağan onayladı 23.11.2026)

- **Yeri §1 sonu**, mail yasağının yanında. Tebrik istisnası (PR #10, `a043ce3`) §5 sonuna düşmüştü; o PR
  merge edilirken §1'e alınması önerilir.
- **Tebrik ayrı kalır.** Tebrik içeriğin kendisini (görsel, yazı) taşır; bu istisna yalnız haber taşır.
  Birleştirmek A kararını sulandırır.
- **Alıcı dosyası** `deploy/posta-alicilari.json`, git dışında (`roller.json` gibi). Ajanın yazamaması için
  `.claude/settings.json` `permissions.deny` listesine eklenir — ayar dosyası, Kağan onaylar.
- **Olumsuz yorum uyarısı:** yorum ajanı olumsuzluğu LLM ile değerlendirirse "kuralla üretilmiş uyarı"ya girmez;
  ya iki onaydan geçer ya da metne yeni madde eklenir. Yorum takibine dönünce karar verilir; metin şimdilik sıkı.

## Betik tasarımı (Kağan onayı 23.11.2026, dal `feature/rapor-postasi`)

### Yaklaşımlar

| | Nasıl | Artısı | Eksisi |
|---|---|---|---|
| A — iletimin içinden | `soru_kapisi.ilet()` defteri yazınca maili atar | En kısa yol | SMTP hatası iletim adımına girer; yarım "iletildi" kaydı, yeniden deneme zor |
| **B — giden kutusu (seçildi)** | `bin/rapor_postasi.py` Yanıt defterini tarar, haberi gitmemiş onaylı raporları gönderir, `sirket-log/posta/`'ya kaydeder | `ilet()`'e dokunulmaz; mail hatası raporu bozmaz; sonraki çağrı yeniden dener, aynı haber iki kez gitmez | Bir dosya ve bir kayıt klasörü fazla |

### Kararlar

- **Hangi raporlar:** Yanıt defterinde `- gorunurluk:` taşıyan (zamanlı rapor) ve `- etiket: onaylı` olan kayıtlar.
  "CEO kontrolü yapılmadı" ve "onaylanamadı" kayıtlarına haber gitmez (§3 iki onay).
- **Rapor türü:** kayıt id'sinden — `rapor-<danışman>-YYYYMMDD` → `<danışman>-gunluk` (ör. `kalite-gunluk`).
  Bu kalıba uymayan kayıt atlanır.
- **Tetik:** dağıtıcı başarılı her iletimden sonra betiği çağırır; hata dağıtıcıyı durdurmaz (yalnız loglanır).
  Elle de çalışır.
- **Mail:** sabit şablon. Konu: `<Rapor adı> hazır — GG.AA.YYYY`; gövde: tek cümle + panel bağlantısı. Rapor adı
  sabit bir eşlemeden gelir (`kalite-gunluk` → "Kalite günlük raporu"); tarih kayıt id'sinden. Gövdeye rapor
  metninden hiçbir şey girmez — rakam ve ad girmediği testle kanıtlanır.
- **Bağlantı:** `<PANEL_ADRES>/?soru=<id>`; `PANEL_ADRES` `.env`'den. Panel `?soru=` parametresini tanır: girişten
  sonra o kaydı açar (yetkisi yoksa açmaz, sunucu süzmesi değişmez).
- **Alıcılar:** `deploy/posta-alicilari.json` — `{"kalite-gunluk": ["a@nove.group", …]}`; git dışı, örneği
  `deploy/posta-alicilari.json.example` (sahte adreslerle). Ajana kapalı: `.claude/settings.json` deny listesine
  `Read/Write/Edit(./deploy/posta-alicilari.json)` — Kağan onaylar. Rapor türü dosyada yoksa haber gitmez,
  kayıt "alıcı yok" olarak düşer.
- **Kilitler** (biri tutmazsa gönderim yok, nedeni yazılır):
  1. `ANAYASA.md`'de `İstisna — rapor postası` metni var;
  2. `.env`'de SMTP bilgisi (`POSTA_SMTP_SUNUCU`, `POSTA_SMTP_PORT`, `POSTA_KULLANICI`, `POSTA_SIFRE`,
     `POSTA_GONDEREN`) ve `PANEL_ADRES` var;
  3. `CLAUDECODE` ortamında değil — ajan yalnız `--kuru` koşturur (formdan_takim K1 deseni).
- **Kayıt:** `sirket-log/posta/<id>.json` — gönderildi / alıcı yok / hata; zaman, alıcı **sayısı** (adres değil).
  Gönderildi kaydı varsa tekrar gönderilmez. Hata kaydı sonraki çağrıda yeniden denenir.
- **Tavan:** `ayar.POSTA_GUNLUK_TAVAN` (gün başına mail sayısı). Aşılırsa kalan haber ertesi çağrıya kalır,
  nedeni loglanır; sessiz durmaz.
- **Test:** gerçek SMTP yok — `smtplib` sahte sınıfla değiştirilir. Kilitler, idempotentlik, tavan, şablonun veri
  taşımaması, alıcı yokken davranış.

## Kurulumda kalan (Kağan)

- Metni `ANAYASA.md` §1 sonuna işlemek.
- Gönderen adres + SMTP bilgisi + `PANEL_ADRES` (`.env`).
- `deploy/posta-alicilari.json` ve deny listesi satırları.
- Panel bağlantısı sunucu adresini ister — sunucuya taşımadan sonra gerçek deneme.
- `NOVE-KURULUM.md` ve `CLAUDE.md` Yasaklar satırı istisnayı anar (metin işlendikten sonra).
