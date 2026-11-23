---
durum: yazildi
guncelleme: 2026-11-23
dal: docs/rapor-postasi-istisnasi
pr: -
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

## Kurulumda kalan (betik işi)

- Gönderen adres + SMTP bilgisi (`.env`) — Kağan.
- `bin/rapor_postasi.py`: alıcı dosyasından okur, gövdeyi sabit şablondan kurar (ad, tarih, bağlantı); gövdeye
  rakam ve ad girmediği testle kanıtlanır; tavan `bin/ayar.py`'de.
- Panel bağlantısı sunucu adresini ister — sunucuya taşımadan sonra.
- `NOVE-KURULUM.md` ve `CLAUDE.md` Yasaklar satırı istisnayı anar (metin işlendikten sonra).
