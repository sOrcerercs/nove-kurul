---
durum: tamamlandi
guncelleme: 2026-11-23
dal: feature/yanit-karti
pr: 29
bekleyen: -
---

# Panelde kurul yanıtı kart olarak gösterilsin

**Nereden geldi:** Kağan, Kalite formu §5 konuşması, 19.10.2026: *"- ve hashtag yerine daha göze hitap edecek
şekilde cevap yazsın bizim için, program tasarımına uysun"* → seçenek A: danışman `kurul-yaniti` düzeninde yazar,
panel kart olarak çizer. Taslak `docs/answer-card-draft` dalında (e527b0d) bekliyordu; 20.11.2026'da güncellenip
main'e alındı.

## Belirti

- **19.10'daki hâli:** panel yanıtı düz metin basıyordu; `##` ve `-` olduğu gibi görünüyordu.
- **20.11'deki hâli (panel canlı, PR #20):** yanıt sunucuda HTML'e çevriliyor (`bin/panel_defter.py:220`,
  `yanit_html=md_html(...)`) ve `<div class="md">` içinde basılıyor (`panel/panel.js:680-682`). `##` ve `-` artık
  görünmüyor; başlıklar `.md h3…` stiliyle (`panel/stil.css:211-212`) düz başlık olarak çıkıyor.
- Kart görünümü hâlâ yok. Örnek: `yanitlar/20261120-1547-uuvm.md` (OKR, Satış Kalite 2026-FY) panelde dört başlık
  (`## Kısa yanıt`, `## Dayanak`, `## Bilinmeyenler`, `## Not` — `skills/kurul-yaniti/SKILL.md`) alt alta aynı
  yeşil kutuda (`.answer`, `panel/stil.css:144-147`) görünüyor.

## Konuşmada gösterilen hedef

Kısa yanıt büyük ve koyu; Dayanak rozetli satırlar (✅ Birincil, 🟡 İkincil, ⛔ Doğrulanamadı); Bilinmeyenler sarı
kutu; Not küçük ve gri; altta danışman · tarih · Denetçi ✓ · CEO ✓.

## Kararlar (Kağan, 20.11.2026)

- Kart **panelde** kurulur: sunucu yanıtı bugünkü gibi `md_html` ile HTML'e çevirir; `panel/yanit-karti.js`
  (DOM'suz modül, `sahne-sira.js` deseni) `<h4>` başlıklarına göre böler ve kartı çizer.
- Zorunlu başlıklardan (Kısa yanıt, Dayanak, Bilinmeyenler) biri eksikse ya da tanınmayan bir başlık varsa kartın
  üstünde **"Kontrol edilmesi gerekebilir"** yazar; içerik kaybolmaz. `Not` isteğe bağlıdır (SKILL.md).
- **Kurula not** kutusu kartın en altında; **iki imza** (Denetçi ✓ · CEO ✓) onun altında, danışman ve tarihle aynı satırda.
- İmza bilgisi Yanıt defterinin `- Denetçi: ✔ · CEO: ✔` satırından okunur (`bin/panel_defter.py`, `imzalar`).

## Yapılan

- `panel/yanit-karti.js` + `tests/test_yanit_karti.py` (node), `bin/panel_defter.py` `imzalar` + testleri,
  `panel/panel.js` kartı çağırır, `panel/index.html` betik, `panel/stil.css` kart stilleri.
- Önizleme: `yanitlar/20261120-1547-uuvm.md` headless Chrome ile çizildi (panele giriş yapılmadan).

## Kapanış (23.11.2026)

PR #29 merge edildi (main 15f5f62). Kağan panelde göz kontrolü yaptı; Dayanak tabloları dar yan sütunda harf harf
bölünüyordu — `panel/stil.css`'te tabloda kelime bölme kapatıldı, hücreye en az genişlik verildi, sığmayan tablo yatay
kayar ve ilk sütun sabit kalır (b2c98a0). main'de 931 test OK (skipped=9); taban 919'du (+12 yeni test).
