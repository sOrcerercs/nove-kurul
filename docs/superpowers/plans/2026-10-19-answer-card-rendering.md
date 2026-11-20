---
durum: taslak
guncelleme: 2026-11-20
dal: -
pr: -
bekleyen: kullanici
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

## Henüz karar yok

- Kart, `md_html` çıktısını mı süsler (başlığa göre bölümleme sunucuda), yoksa panel dört başlığı ayrı alanlar
  olarak mı alır?
- Dört başlıktan biri eksik ya da beklenmedik biçimdeyse panel ne gösterir (bugünkü düz `.md` görünümüne geri
  dönüş mü, uyarı mı)?
- "Kurula not" kutusu (`panel/panel.js:681`) kartta nereye oturur?
- Denetçi ✓ · CEO ✓ satırı için iki imzanın bilgisi Yanıt defterinde var mı, yoksa soru kaydından mı okunur?
