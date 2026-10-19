---
durum: acik
guncelleme: 2026-10-19
dal: feature/patient-name-policy
pr: -
bekleyen: -
---

# ANAYASA §2 revizesi — hasta ve müşteri adının yanıtta yazılması

**Nereden geldi:** Kağan, form hattı tasarımı konuşması, 19.10.2026. Yönetim Kurulu bir şey sorduğunda yanıtın
ad ve unvana kadar bilgi vermesini istedi; hasta ve müşteri adı için de "yazabilsin" dedi ve C yolunu seçti
(önce ANAYASA revizesi, hukuk onayıyla; sonra kod).

## Belirti

- ANAYASA §2: "Hasta ve müşteri adı, telefonu, e-postası ve TC kimlik numarası hiçbir çıktıya, koşu kaydına,
  deftere ya da loga yazılmaz." `CLAUDE.md` Yasaklar ve `NOVE-KURULUM.md` §6 form şablonu (satır 259) aynı yasağı taşır.
- Denetçi istemi (`bin/bekci.py:126`) "kişi adı"nı ayrımsız ihlal sayar.
- Denetçi koşu kaydını şirket dışı sağlayıcılara gönderir: NIM → OpenAI → Haiku (`sirket/DENETCI.md:117`).
  Kayıtta hasta adı olursa ad bu sağlayıcılara gider.
- Personel adı ve unvanı bu taslağın konusu değil: ANAYASA §2 `kurallar.md` izniyle zaten mümkün; form hattında
  çözülüyor (`docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md`).

## Kanıt

- `ANAYASA.md` §2 · `bin/bekci.py:126` · `sirket/DENETCI.md:117`
- `kasa/decisions/n13-tc-deseni-saglama-hanesiyle-calisir.md` (hasta verisi riski, KVKK)
- `kasa/concepts/danisman-formu.md` · `kasa/entities/denetci-bekci.md`

## Verilen kararlar (Kağan, 19.10.2026 — ANAYASA §2 taslağı için)

1. **Kapsam: yalnız ad soyad** (önce B seçildi, aynı gün geri alındı — depo herkese açık çıktı). Hasta ve
   müşterinin adı soyadı yazılabilir; telefon, e-posta ve TC kimlik numarası yasak kalır. `bekci.ON_KONTROL`
   ve formdan_takim kişisel veri taraması değişmez.
2. **Yer: her yer (C)** — çıktı, Yanıt defteri, koşu kaydı, defter, log.
   Not: `nove-kurul` deposu PUBLIC; `takimlar/*/defter.md` git'e giriyordu (19.10.2026 ölçüldü).
3. **Danışman defterleri git'e girmez (A)** — `.gitignore`: `takimlar/*/defter.md`, iskelet hariç. PR #5'te uygulandı.

4. **`takim.md` Sahibi = yalnız unvan; `formlar/onayli/` git dışında** — PR #5'te uygulandı (`24beb97`, `0c6fdd7`).
5. **Yurt dışı aktarım (Anthropic, NVIDIA NIM, OpenAI): uygun** — Kağan'ın teyidi, 19.10.2026. Maskeleme yapılmaz
   (adın deseni yok; güvenilir maskeleme mümkün değil).
6. **ANAYASA §2 yeni metni onaylandı** — "Kişisel veri sınırlıdır. Hasta ve müşterinin adı soyadı yazılabilir;
   telefonu, e-postası ve TC kimlik numarası … yazılmaz. … Ad soyad taşıyabilen dosya herkese açık bir depoya
   girmez." Dosyayı Kağan kaydeder (ajan için kilitli). Ardından ayrı dalda: `bin/bekci.py` istemi,
   `formdan_takim.HER_ZAMAN_YASAK`, `CLAUDE.md` Yasaklar, `formlar/DANISMAN-FORMU.md` uyarısı, `NOVE-KURULUM.md`,
   `sirket/AJAN-KIMLIGI.md`, `sirket/DENETCI.md`, testler.

## Henüz karar yok (eski liste — 1–6 ile cevaplandı)

- Hukuk / KVKK sorumlusu hasta adının (özel nitelikli veri) kurul yanıtında, koşu kaydında ve logda tutulmasına
  hangi dayanakla izin veriyor? Kim onaylar?
- Yurt dışı aktarım: hasta adı içeren kayıt NIM ve OpenAI'ye gidebilir mi? Gidemezse Denetçi'ye gitmeden önce ad
  maskelenir mi, yoksa Denetçi yerel/aynı aileden mi koşar (ANAYASA §3 "ayrı kafa" ile çelişir mi)?
- İzin her danışmana mı, yalnız bazılarına mı (`kurallar.md` üzerinden)? Müşteri ile hasta aynı mı ele alınır?
- Telefon, e-posta, TC kimlik no yasak kalıyor mu (Kağan yalnız adı sordu)?
- Ad nerede durur: yalnız `cikti/` taslağında ve Yanıt defterinde mi, yoksa koşu kaydı, defter ve `sirket-log/`'da da mı?
  Saklama süresi?
