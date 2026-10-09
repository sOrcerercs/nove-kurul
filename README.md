# Nove Kurul Ofisi

Nove Group yöneticileri için ajan ekosistemi. Kurul üyesi panelden soru sorar; danışman ajanlar şirket verisini
okuyup yanıtlar, **Denetçi** kuralları denetler, **CEO Ajanı** ikinci kez kontrol edip onaylar. Onaylı yanıt
soranın masasına ve Yanıt defterine gider. **Yayın düğmesi insanda.**

Tasarım, kararlar ve fazlar: [`NOVE-KURULUM.md`](NOVE-KURULUM.md) · Projenin kimliği ve okuma sırası:
[`CLAUDE.md`](CLAUDE.md) · Kurallar: [`ANAYASA.md`](ANAYASA.md)

## Durum

Faz 1 (repo ve iskelet) yerelde sürüyor. Sürücü, Denetçi ve İş Dağıtımcı'nın altyapısı ile testler hazır; soru
akışı (Faz 3), CEO Ajanı (Faz 2) ve panelin sunucu tarafı (Faz 5) henüz yazılmadı. Danışmanların hepsi
"kurulumda". Panel `panel/` altında demo verisiyle çalışıyor.

## Yerelde çalıştırma

1. Python 3.9 ya da üstü ve Claude Code kurulu olsun (`claude --version`).
2. Depoyu aç: `cd "~/Desktop/Nove AI"`.
3. Anahtarları hazırla: `cp .env.example .env`, sonra değerleri doldur (aşağıdaki tablo). `.env` git'e girmez.
4. Testleri koştur: `python3 -m unittest discover -s tests` — hepsi yeşil olmalı.
5. Ayarları ve tavanları gör: `python3 bin/ayar.py`; bir danışmanı kuru koştur: `python3 bin/kos.py <danisman> --kuru` (Claude çağrılmaz, dosya yazılmaz).
6. Dağıtıcının kararlarını gör: `python3 bin/dagitici.py --kuru`; zamanlayıcı durumu: `python3 bin/zamanla.py --durum`.
7. Paneli aç: `cd panel && python3 -m http.server 8000` → `http://127.0.0.1:8000/?demo`

## Anahtarlar (`.env`)

| Anahtar | Ne için | Ne zaman |
|---|---|---|
| `ANTHROPIC_API_KEY` | Danışman ve CEO koşuları (Claude Code). Nove'nin Anthropic Console organizasyonundan, aylık harcama limitiyle; kişisel abonelik kullanılmaz | Faz 0 |
| `NVIDIA_API_KEY` | Denetçi'nin birinci yolu (NIM) | Faz 0 |
| `NIM_BEKCI_MODEL` | Denetçi'nin NIM modeli; boşsa `openai/gpt-oss-20b` | isteğe bağlı |
| `OPENAI_API_KEY` | Denetçi'nin ikinci yolu | isteğe bağlı |
| `NIM_MODEL` | Bir danışmanı NIM modeliyle koşturmak için (tool-use desteklemeli) | isteğe bağlı |
| `QA_READONLY_URL` | Kalite danışmanının veritabanı bağlantısı — yalnız `SELECT` yetkili rol | Faz 4 |
| `CRM_API_URL` · `CRM_READONLY_TOKEN` · `CRM_WEBHOOK_SECRET` | Satış zili; biri yeter (API sorgusu ya da webhook) | Faz 7 |

Denetçi'nin sırası NIM → OpenAI → Haiku: bir yolun anahtarı **yoksa ya da geçersizse** bir sonrakine geçilir ve
gerekçe hangi yoldan geçildiğini söyler. Üçü de kullanılamazsa Haiku denetler ve karar "denetçi aynı aileden —
uyarı" notuyla kaydedilir.

## Platform notu

Sürücü Linux ve macOS'ta çalışır: koşu kilidi `fcntl`'e bağlıdır, Windows'ta yalnız **WSL** içinde çalışır.
Sunucuda (NOVE-KURULUM.md §8) zamanlayıcı systemd timer'dır; macOS'ta `bin/zamanla.py` launchd kullanır;
ikisi de yoksa **cron** ile `python3 bin/gunluk.py --sabah` ve `--aksam` çağrılır.

## Lisans

[`LICENSE`](LICENSE) — MIT. Dosya olduğu gibi kalır; telif satırı silinmez ve değiştirilmez.
