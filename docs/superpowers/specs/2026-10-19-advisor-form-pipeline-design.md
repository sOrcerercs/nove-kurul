---
durum: acik
guncelleme: 2026-10-19
dal: feature/advisor-form-pipeline
pr: 5
bekleyen: -
---

# Danışman formu hattı — Tasarım

> Faz 4'ün ilk adımı (`NOVE-KURULUM.md` §6, Faz 4). Kararlar Kağan'la 14.10 ve 19.10.2026'da adım adım verildi.
> Bu belge onaylanmadan kod yazılmaz.

## Amaç

Bir bölüm yöneticisinin doldurduğu formdan, elle düzenleme yapmadan **kurulu bir danışman** çıkarmak.
Form `formlar/onayli/<bolum>.md`'ye girince `bin/formdan_takim.py <bolum>` danışmanın dosyalarını yazar.
`takim.md` frontmatter'lı olduğu anda danışman kurulu sayılır (`ayar.kurulumda_mi`).

## Kapsam

| Dosya | Ne |
|---|---|
| `formlar/DANISMAN-FORMU.md` | Boş şablon: §6'daki bölümler 1–6, artı yeni **7. Revize (Kağan doldurur)** |
| `formlar/gelen/` | Doldurulmuş formlar. Git'e girmez (`.gitignore`'da zaten var) |
| `formlar/onayli/` | Kağan'ın revize ettiği formlar. Ajanlara yazma kapalı (deny listesinde zaten var) |
| `bin/formdan_takim.py` | Formu okur, denetler, dosyaları yazar |
| `skills/kurul-yaniti/SKILL.md` | İlk ortak yetenek: kurula giden taslağın düzeni |
| `.claude/settings.json` | Üç yeni kilit (aşağıda, Karar 6) |
| `tests/test_formdan_takim.py` | Aşağıdaki testler (1–10); 11 `tests/` altındaki Denetçi testlerine |
| `bin/bekci.py` | Denetçi isteminde personel adı kuralı (K7) |

## Kararlar

### K1 · Betiği yalnız Kağan koşturur
- Ajan yalnız `--kuru` ile çalıştırabilir: sonuç ekrana basılır, **hiçbir dosya yazılmaz**.
- Bu kural yetkiyle de korunur (Kağan, 19.10.2026): `CLAUDECODE` ortam değişkeni varsa (Claude Code ajanın her
  Bash komutuna koyar) betik `--kuru` dışında durur. Kağan'ın kendi terminalinde değişken yoktur.
- Hedefte `kurallar.md` varsa ya da `takim.md` frontmatter'lıysa (danışman kuruluysa) betik **durur**.
- `--yeniden` ile koşturulursa önce eski ve yeni hâlin farkını gösterir, sonra yazar.

### K2 · Form biçimi: Markdown, sabit numaralı başlıklar
- Betik başlıkları numarasıyla bulur (`## 1. Kimlik` … `## 7. Revize`). Başlık metni değişse de numara yeter.
- Eksik zorunlu alanların **hepsi birden** listelenir ve betik durur. İlk eksikte durmaz.
- Yalnız "?" yazılmış alan boş sayılır.

### K3 · Alan → hedef eşlemesi

**`takim.md` frontmatter**

| Alan | Kaynak |
|---|---|
| `name` | `<bolum>` argümanı (klasör adı, ASCII kebab-case) |
| `description` | §1 "Tek cümleyle mesleği" |
| `anahtar_kelimeler` | §2 anahtar kelimeler |
| `renk` | §1 renk (isteğe bağlı) |
| `skills` | `[kurul-yaniti]` + §7'de Kağan'ın eklediği yetenekler |
| `model` | §7 (yoksa iskeletin değeri: `sonnet`) |
| `gerekli_anahtarlar` | §7 (yoksa `[]`) |
| `butce_usd` | `ayar.KOSU_BUTCESI_USD` — formdan gelmez |
| `saglayici`, `tools` | İskeletten |

**`takim.md` gövdesi** — iskeletin koşu adımları korunur (kuyruk kapatma adımı dahil), üstüne:
- "Hangi soruları alır": §2 örnek sorular. "Hangi soruları almaz": §2 karışabilecek sorular.
- "Girdi kaynakları": §3 veri tablosu olduğu gibi.
- "Çıktı sözleşmesi": `cikti/<soru-id>-taslak.md`, `kurul-yaniti` düzeninde. §5 "iyi yanıt örneği" buraya örnek olarak girer.
- "Tempo": §6 yalnız not olarak yazılır. Zamanlı koşu `gunluk.ZAMANLI`'ya elle eklenir.

**`kurallar.md`** — iskeletten, üstüne:
- "Asla yapmaz": §4.
- "Çıktı kalite ölçütleri": iskeletin iki maddesi + §4 "her yanıtta mutlaka olması gereken".
- Yeni bölüm "Teyit ve hassas veri": §4 "hangi sayıyı kim teyit eder", §3 hassas alanlar, §3 formülü teyitsiz
  göstergeler (her biri `—` ve teyit sahibiyle).

**`defter.md`, `durum.json`** — iskeletten, `TAKIM` yerine danışman adı.

**Zorunlu alanlar:** danışman adı, meslek cümlesi, `<bolum>` (klasör adı), ≥1 anahtar kelime, ≥1 örnek soru,
≥1 veri kaynağı satırı.

### K4 · Yazmadan önceki kontroller

| # | Kontrol | Sonuç |
|---|---|---|
| 1 | Kişisel veri ve anahtar taraması — `bekci.ON_KONTROL` desenleri (e-posta, telefon, TC kimlik, anahtar/token) | **Durur**, bulunan türü ve bölümü söyler (değeri basmaz) |
| 2 | Anahtar kelime çakışması — `dagitici.cakisma` | **Uyarır, devam eder** |
| 3 | Her yetenek `skills/<ad>/SKILL.md` olarak diskte var mı | Yoksa **durur**. Varsa o `SKILL.md`'nin `takimlar:` listesine danışmanı ekler |
| 4 | `kosu/`, `cikti/` klasörleri | Yoksa açar |
| 5 | Sonraki adımlar | Ekrana yazar: `python3 bin/agents_uret.py`, `python3 -m unittest discover -s tests`. Kendisi koşturmaz |

Her durma, sebebini görünür yazar ve sıfırdan farklı çıkış koduyla biter. Durma hâlinde **hiçbir dosya yazılmaz**
(kontroller yazımdan önce biter).

### K5 · `kurul-yaniti` yeteneği
Her danışmana kendiliğinden eklenir. Kural koymaz (kurallar ANAYASA §2 ve `AJAN-KIMLIGI.md`'de), **düzen** verir.
Taslak dört bölümdür:

1. **Kısa yanıt** — 2–3 cümle; ilk cümle sorunun cevabıdır. Soru belirsizse hangi yorumla yanıtlandığı burada yazar.
2. **Dayanak** — cevabı taşıyan iddialar; her biri ✅/🟡/⛔ etiketli, kaynaklı, gerekiyorsa `n`'li.
3. **Bilinmeyenler** — doğrulanamayanlar, `—` göstergeler ve teyit sahibi. Yoksa "yok".
4. **Not** — isteğe bağlı; ör. "öneri: `finans`".

Her bölüm için kısa bir örnek içerir. `tests/test_skills.py` sözleşmesine uyar: zorunlu frontmatter
(`name`, `description`, `kaynak`, `lisans`, `uyarlayan`, `takimlar`), `## Öğrenilenler` bölümü, ≤250 satır.

### K6 · Kilitler — kuralla değil, yetkiyle
`.claude/settings.json` `permissions.deny` listesine eklenir:

```
"Write(./takimlar/*/kurallar.md)",  "Edit(./takimlar/*/kurallar.md)",
"Write(./ANAYASA.md)",              "Edit(./ANAYASA.md)",
"Write(./sirket/CEO-KIMLIGI.md)",   "Edit(./sirket/CEO-KIMLIGI.md)"
```

Betik etkilenmez: Kağan onu terminalden koşturur; kilit yalnız ajanın dosya araçlarını kapatır.
`CLAUDE.md`'deki "Yasaklar" maddesi bu üç dosyanın da yetkiyle kapalı olduğunu söyleyecek şekilde güncellenir.

### K7 · Personel adı ve unvanı yazılabilir
Kurul, yanıtta kimin sorumlu olduğunu ad ve unvanıyla görmeli (Kağan, 19.10.2026). ANAYASA §2 bunu
`kurallar.md` izniyle zaten mümkün kılar; ANAYASA değişmez.
- Betik her danışmanın `kurallar.md`'sindeki "Teyit ve hassas veri" bölümüne şu satırı yazar:
  "Personel adı ve unvanı yazılabilir. Hasta ve müşteri adı, telefon, e-posta, TC kimlik no yazılmaz."
- Varsayılan **açık**. §7 Revize'de "Personel adı: hayır" yazılırsa satır "Personel adı yazılmaz." olur.
- Bölüm yöneticisinin adı ve unvanı `takim.md` gövdesine "Sahibi" satırı olarak girer.
- **Denetçi düzeltmesi** (`bin/bekci.py` istemi): bugün "kişi adı"nı ayrımsız ihlal sayıyor, `kurallar.md`'deki izni
  görmüyor. Yeni metin: hasta/müşteri adı her zaman ihlal; personel adı yalnız `kurallar.md` izin vermiyorsa ihlal.
  `bekci.gecersiz_gerekceyi_ayikla`'nın "kişi adı" gerekçesine dokunmaması korunur.

## Testler

| # | Girdi | Beklenen |
|---|---|---|
| 1 | Eksiksiz form | `takim.md` ve `kurallar.md` doğru; `skills` içinde `kurul-yaniti` |
| 2 | İki zorunlu alanı boş form | İkisi birden listelenir; hiçbir dosya yazılmaz |
| 3 | Bir alanda yalnız "?" | Boş sayılır |
| 4 | Formda telefon ya da TC kimlik no | Durur |
| 5 | Diskte olmayan yetenek | Durur |
| 6 | Başka danışmanla çakışan anahtar kelime | Uyarır, dosyalar yazılır |
| 7 | `kurallar.md` zaten var | Durur; `--yeniden` önce farkı gösterir |
| 8 | `--kuru` | Ekrana basar, hiçbir dosya yazılmaz |
| 9 | `.claude/settings.json` | Altı kilit satırı yerinde |
| 10 | Form §7'de personel adı belirtilmemiş / "hayır" | `kurallar.md`'de izin satırı var / yasak satırı var |
| 11 | Denetçi istemi | Personel adını `kurallar.md` iznine bağlıyor; hasta/müşteri adını her zaman ihlal sayıyor |

Testler geçici bir kök klasörde koşar; gerçek `takimlar/`'a dokunmaz.
Taban: `python3 -m unittest discover -s tests` → 414 test, OK (8 atlanan) — 19.10.2026.

## Kapsam dışı
- Kalite formunun doldurulması ve `formdan_takim.py kalite` koşusu (Faz 4'ün sonraki adımı).
- Kalite'ye özel yetenekler (`qa-koclugu-kurgusu` uyarlaması).
- CEO tavanı ölçümü (ayrı konu, Kağan'ın kararını bekliyor).
- `bin/takim-olustur.sh` değişmez; boş oda açmak için kalır.

- Hasta ve müşteri adı: ayrı taslak, ANAYASA §2 revizesi ve hukuk onayı bekliyor
  (`docs/superpowers/plans/2026-10-19-patient-name-policy.md`). Bu hat bugünkü kuralla ilerler.
