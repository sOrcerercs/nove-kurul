---
durum: yazildi
guncelleme: 2026-10-19
dal: feature/advisor-form-pipeline
pr: -
bekleyen: -
---

# Danışman formu hattı — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (ya da satır içi
> `superpowers:executing-plans`). Her görev: önce test, kırmızıyı gör, sonra kod, yeşili gör, commit.

**Goal:** `formlar/onayli/<bolum>.md` formundan, elle düzenleme olmadan kurulu bir danışman üretmek; ortak `kurul-yaniti`
yeteneğini, insan dosyalarının yetki kilidini ve personel adı kuralının Denetçi'deki karşılığını eklemek.

**Architecture:** Tek betik `bin/formdan_takim.py`: form okuma (numaralı başlıklar) → kontroller (zorunlu alan,
kişisel veri, yetenek, çakışma) → dosya metinlerini bellekte üretme → `--kuru` değilse yazma. Durma hâlinde hiçbir
dosya yazılmaz. Mevcut parçalar yeniden kullanılır: `ayar.frontmatter`, `ayar.takim_bilgisi`, `bekci.on_kontrol`,
`dagitici.aktif_danismanlar`, `dagitici._tr_kucuk`.

**Tech Stack:** Python 3 standart kütüphane (`difflib`, `re`, `pathlib`), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md` (Kağan onayı 19.10.2026)

## Global Constraints

- Dal: `feature/advisor-form-pipeline` (açık; spec commit'leri `7bf73d8`, `409bb8a`). `main`'e commit yok.
- Taban (19.10.2026, ölçüldü):
  - `python3 -m unittest discover -s tests` → `Ran 414 tests` · `OK (skipped=8)`
  - `python3 bin/agents_uret.py --check` → `OK: agents güncel`
  - `python3 bin/dagitici.py --cakisma` → `çakışan anahtar kelime: 0 — revize için hazır`
  - `ayar.kurulu_takimlar()` → `[]` · `skills/` yalnız `.gitkeep`
- Var olan testler var olan davranışın kanıtıdır; hiçbiri kırılmaz, hiçbiri gevşetilmez.
- **Betiği gerçek kökte yalnız `--kuru` ile koştur** (spec K1). Yazan koşu Kağan'ındır. Testler geçici kökte koşar.
- Task 1'den sonra ajan `takimlar/*/kurallar.md`, `ANAYASA.md`, `sirket/CEO-KIMLIGI.md`'ye Write/Edit yapamaz. Hiçbir
  görev bunu gerektirmez; gerektiriyor gibi görünürse dur ve sor.
- `formlar/onayli/` ajanlara yazmaya kapalı (`.claude/settings.json:8-9`). Bu plan o klasöre dosya koymaz; ilk formu
  Kağan koyar. Betik form yoksa görünür sebeple durur.
- Her durma görünür sebep döndürür ve sıfırdan farklı çıkış koduyla biter. Sessiz düşme yok.
- Kişisel veri yok: fikstürlerde gerçek kişi adı, telefon, e-posta, TC yok. Telefon/TC test girdisi test kodunun içinde
  üretilir; TC olarak sağlama hanesi geçerli sentetik `10000000146` kullanılır.
- Commit biçimi: `type(scope): Türkçe konu` + `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Dosya haritası

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `.claude/settings.json` | Altı yeni deny satırı (K6) | Değişir (Task 1) |
| `CLAUDE.md` | Yasaklar: kilitler yetkiyle; betik ajan için yalnız `--kuru`; klasör yapısına `formlar/`, `docs/` | Değişir (Task 1, 8) |
| `bin/bekci.py` | Denetçi istemi: personel adı `kurallar.md` iznine bağlı (K7) | Değişir (Task 2) |
| `tests/test_bekci_nove.py` | Test 11 | Değişir (Task 2) |
| `skills/kurul-yaniti/SKILL.md` | Taslağın dört bölümlük düzeni (K5) | Yeni (Task 3) |
| `tests/test_skills.py` | Dört bölüm sırayla var | Değişir (Task 3) |
| `formlar/DANISMAN-FORMU.md` | Boş şablon, §1–§7 + revize kontrol listesi | Yeni (Task 4) |
| `tests/fikstur/form/kalite.md` | Doldurulmuş örnek form (sentetik) | Yeni (Task 4) |
| `bin/formdan_takim.py` | Okuma, kontrol, üretim, komut | Yeni (Task 5–8) |
| `tests/test_formdan_takim.py` | Testler 1–10 + komut satırı bağlantısı | Yeni (Task 1, 5–8) |
| `NOVE-KURULUM.md` | §6 şablon bloğu dosyaya bağlanır; Faz 4 ilk madde işaretlenir | Değişir (Task 9) |
| `docs/superpowers/PLANS.md`, spec frontmatter | Durum | Değişir (Task 9) |

---

### Task 1: Kilitler (K6, test 9)

**Files:** `.claude/settings.json`, `CLAUDE.md`, `tests/test_formdan_takim.py` (yeni, yalnız `KilitTesti`)
**Interfaces:** yok

- [ ] **Step 1: Testi yaz** — `tests/test_formdan_takim.py`:

```python
"""Danışman formu hattı (docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md).

Ağ yok, para harcamaz; betik geçici bir kökte koşar, gerçek `takimlar/`'a dokunmaz.
python3 -m unittest discover -s tests
"""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))


class KilitTesti(unittest.TestCase):
    """K6: insanın dosyaları kuralla değil yetkiyle kapalı; eski altı kilit de yerinde (12'nin 12'si)."""

    def test_insan_dosyalari_yetkiyle_kilitli(self):
        deny = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]["deny"]
        beklenen = ["Read(./.env)", "Read(./.env.*)"]
        for yol in ("./yanitlar/**", "./formlar/onayli/**", "./takimlar/*/kurallar.md",
                    "./ANAYASA.md", "./sirket/CEO-KIMLIGI.md"):
            beklenen += [f"Write({yol})", f"Edit({yol})"]
        self.assertEqual(len(beklenen), 12)
        for satir in beklenen:
            with self.subTest(satir=satir):
                self.assertIn(satir, deny)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -8`
Expected: FAIL — 6 subTest: `'Write(./takimlar/*/kurallar.md)' not found in [...]` ve diğer beşi.

- [ ] **Step 3: `.claude/settings.json` deny listesine ekle** (mevcut altı satırın altına, sıra korunur):

```json
      "Write(./formlar/onayli/**)",
      "Edit(./formlar/onayli/**)",
      "Write(./takimlar/*/kurallar.md)",
      "Edit(./takimlar/*/kurallar.md)",
      "Write(./ANAYASA.md)",
      "Edit(./ANAYASA.md)",
      "Write(./sirket/CEO-KIMLIGI.md)",
      "Edit(./sirket/CEO-KIMLIGI.md)"
```

- [ ] **Step 4: `CLAUDE.md` Yasaklar** — ilk maddenin ikinci satırını şöyle değiştir:

```
  Yanıt defteri (`yanitlar/`), onaylı formlar (`formlar/onayli/`), `ANAYASA.md`, `sirket/CEO-KIMLIGI.md` ve her
  danışmanın `kurallar.md`'si de aynı şekilde yazmaya kapalı; Yanıt defterine yalnız sürücü yazar.
```

- [ ] **Step 5: Yeşili gör**

Run: `python3 -m unittest tests.test_formdan_takim tests.test_kit -v 2>&1 | tail -3`
Expected: `OK` (test_kit'in `test_stop_hook_bekciyi_cagiriyor` testi de geçer; `hooks` değişmedi)

- [ ] **Step 6: Commit** — `chore(yetki): kurallar.md, ANAYASA ve CEO-KIMLIGI yetkiyle kilitli (K6)`

---

### Task 2: Denetçi — personel adı `kurallar.md` iznine bağlı (K7, test 11)

**Files:** `bin/bekci.py:126`, `tests/test_bekci_nove.py` (`YonergeTesti`)
**Interfaces:** `bekci._istem(anayasa, kurallar, kosu_metni)` imzası değişmez.

Bugün (`bin/bekci.py:125-126`): `"…Sen kaydın İÇERİĞİNİ denetle: kaynaksız sayı, kişi adı/e-posta/telefon/TC kimlik no/anahtar, kural dosyasındaki 'asla yapmaz' maddeleri, kaydın boş olması.\n"` — "kişi adı" ayrımsızdır, `kurallar.md`'deki izni görmez.

- [ ] **Step 1: Testi yaz** — `tests/test_bekci_nove.py`, `YonergeTesti` sınıfına:

```python
    def test_personel_adi_kurallara_bagli_hasta_adi_her_zaman_ihlal(self):
        """K7: personel adı yalnız kurallar.md izin vermiyorsa ihlal; hasta/müşteri adı her zaman."""
        istem = bekci._istem("anayasa", "kurallar", "kayıt")
        self.assertIn("hasta/müşteri adı", istem)
        self.assertIn("personel adı yalnız kurallar dosyası izin vermiyorsa", istem)
        self.assertNotIn("kişi adı/", istem)
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_bekci_nove -v 2>&1 | tail -6`
Expected: FAIL — `'hasta/müşteri adı' not found in 'Sen Nove Group…'`

- [ ] **Step 3: `bin/bekci.py:126` satırını değiştir:**

```python
        "sayı, hasta/müşteri adı, e-posta/telefon/TC kimlik no/anahtar, personel adı yalnız kurallar dosyası "
        "izin vermiyorsa, kural dosyasındaki 'asla yapmaz' maddeleri, kaydın boş olması.\n"
```

`gecersiz_gerekceyi_ayikla` (`bin/bekci.py:256-258`) değişmez: içerik ihlali gerekçelerine dokunmaz.

- [ ] **Step 4: Yeşili gör**

Run: `python3 -m unittest tests.test_bekci_nove tests.test_bekci_nim tests.test_bekci_karsilastir 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 5: Commit** — `fix(bekci): personel adı kurallar.md iznine bağlı, hasta/müşteri adı her zaman ihlal (K7)`

---

### Task 3: `kurul-yaniti` yeteneği (K5)

**Files:** `skills/kurul-yaniti/SKILL.md` (yeni), `tests/test_skills.py`
**Interfaces:** frontmatter `takimlar: []` — Task 7 bu satıra danışman ekler (`yetenege_ekle`).

Sözleşme (`tests/test_skills.py:15`, `:42-49`, `:63-66`): `name, description, kaynak, lisans, uyarlayan, takimlar`;
`## Öğrenilenler` + "kendini geliştir" + "defter.md"; ≤250 satır. `kaynak` `http` ile başlamadığı için
"Kaynak ve değişiklikler" bölümü gerekmez (`:51-61`). `takimlar` yalnız kurulu takımları sayabilir (`:108-120`) —
bugün kurulu takım yok, liste boş başlar.

- [ ] **Step 1: Testi yaz** — `tests/test_skills.py`, `SkillSozlesmesiTesti` sınıfının sonuna:

```python
    def test_kurul_yaniti_dort_bolumu_sirayla_tasir(self):
        """K5: kurula giden her taslak aynı dört başlığı aynı sırayla taşır."""
        metin = (KOK / "skills/kurul-yaniti/SKILL.md").read_text(encoding="utf-8")
        yerler = [metin.find(f"## {b}\n") for b in ("Kısa yanıt", "Dayanak", "Bilinmeyenler", "Not")]
        self.assertNotIn(-1, yerler)
        self.assertEqual(yerler, sorted(yerler))
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_skills -v 2>&1 | tail -6`
Expected: ERROR — `FileNotFoundError: … skills/kurul-yaniti/SKILL.md`

- [ ] **Step 3: `skills/kurul-yaniti/SKILL.md` yaz:**

````markdown
---
name: kurul-yaniti
description: Kurula giden taslağın düzeni — Kısa yanıt, Dayanak, Bilinmeyenler, Not. Her danışmanın her taslağında.
kaynak: Nove Kurul Ofisi (yerli yetenek, 19.10.2026)
lisans: MIT (LICENSE)
uyarlayan: Nove Kurul Ofisi
takimlar: []
---

# kurul-yaniti — taslağın düzeni

Bu yetenek kural koymaz. Kurallar `ANAYASA.md` §2'de ve `sirket/AJAN-KIMLIGI.md`'de (etiket, kaynak, `n`, `—`,
kişisel veri). Burada yalnız **düzen** var: kurul üyesi her danışmanın yanıtını aynı yerden okur.

## Ne zaman

Her koşuda, `takimlar/<danisman>/cikti/<soru-id>-taslak.md` yazarken. `r-` (CEO reddinden sonra düzeltme)
maddesinde de aynı düzen korunur; yalnız CEO'nun bulduğu yer düzeltilir.

## Düzen

Taslak bu dört başlığı bu sırayla taşır. İlk üçü her zaman vardır; `Not` yalnız söylenecek bir şey varsa.

```
# <soru-id> — <sorunun kısa adı>

## Kısa yanıt
## Dayanak
## Bilinmeyenler
## Not
```

## Kısa yanıt

- 2–3 cümle. **İlk cümle sorunun cevabıdır** — soru "hangisi" diyorsa ilk cümle hangisi olduğunu söyler.
- Soru belirsizse hangi yorumla yanıtladığın burada, ilk cümleden hemen sonra yazar.
- Cevap verilemiyorsa ilk cümle bunu söyler ve sebebini verir ("veri bağlı değil", "formül teyit bekliyor").

Örnek (yer tutucular `<…>`; sayı uydurulmaz):

> <Ekip adı>, <dönem> içinde kalite puanı en çok düşen ekip. Düşüş <puan> puan ✅; ölçülen çağrı sayısı küçük
> (n=<n>), bu yüzden eğilim değil işaret olarak okunmalı.

## Dayanak

- Cevabı taşıyan iddialar, madde madde. Her iddianın yanında etiketi (✅ birincil · 🟡 ikincil · ⛔ doğrulanamadı),
  kaynağı ve örneklemden geliyorsa `n`'i.
- Sayılar tabloya girebilir; tablonun her satırı da kaynaklıdır.
- Bağlam ve yöntem cümleleri etiketsiz kalabilir (ANAYASA §2).

Örnek:

> - <dönem> kalite puanı <puan> ✅ — `veri/<dosya>`, n=<n>
> - Önceki dönem <puan> ✅ — aynı kaynak, n=<n>
> - Düşüşün en çok görüldüğü bölüm: <bölüm> 🟡 — bölüm skorları, ağırlıklar teyit bekliyor

## Bilinmeyenler

- Doğrulanamayanlar (⛔), formülü teyitsiz için `—` gösterilen göstergeler ve **teyidi kimin vereceği**.
- Bilinmeyen yoksa tek satır: `yok`.

Örnek:

> - Bölüm ağırlıklı skor: `—` — ağırlıkları <unvan> teyit edecek.

## Not

- İsteğe bağlı. Başka bir danışmanı ilgilendiren nokta (`öneri: <danışman>`), verideki bir hata, kurulun
  bilmesi gereken bir sınır.
- Koşu kaydındaki `öneri:` satırı ayrıca yazılır; bu bölüm onun yerine geçmez.

## Öğrenilenler

Ajan koşuda aldığı veriyle kendini geliştirir: düzenle ilgili tekrarlayan ders önce `defter.md`'ye yazılır;
aynı ders üç koşuda tekrar ederse buraya öneri olarak bırakılır. Kararı Kağan verir.

- (henüz yok)
````

- [ ] **Step 4: Yeşili gör**

Run: `python3 -m unittest tests.test_skills -v 2>&1 | tail -3`
Expected: `OK` (sözleşme testleri yeni dosyayı da tarar)

- [ ] **Step 5: Commit** — `feat(skills): kurul-yaniti — taslağın dört bölümlük düzeni (K5)`

---

### Task 4: Form şablonu ve fikstür

**Files:** `formlar/DANISMAN-FORMU.md` (yeni), `tests/fikstur/form/kalite.md` (yeni)
**Interfaces:** Etiket önekleri Task 5'teki `oku()` ile birebir aynı: `Danışman adı`, `Bölüm yöneticisi`,
`Tek cümleyle mesleği`, `Sahnedeki rengi`, `Bu danışmana gelmesi gereken`, `Anahtar kelimeler`,
`Bu danışmana GELMEMESİ`, `Bu verideki hassas alanlar`, `Formülü/tanımı`, `Bu danışman ASLA`,
`Her yanıtta mutlaka`, `Hangi sayıyı kim teyit eder`, `Kurula giden ideal yanıtın`, `Soru beklemeden`, `Model`,
`Ek yetenekler`, `Gerekli anahtarlar`, `Personel adı`.

Kaynak: `NOVE-KURULUM.md:255-302` (§6 şablonu ve kontrol listesi). Fark: §6'daki satır içi "ör." değerleri `>`
not satırlarına taşınır (betik `>` satırını okumaz, örnek değer sanılmaz); §7 eklenir.

- [ ] **Step 1: `formlar/DANISMAN-FORMU.md` yaz:**

```markdown
# Danışman Formu — <Bölüm adı>

> Bu formu bölüm yöneticisi doldurur. Son hâlini Kağan verir. Bilmediğin alanı boş bırak ya da "?" yaz — uydurma.
> Hasta/müşteri adı, telefon, e-posta, TC kimlik no YAZMA: betik formda bunları bulursa durur.
> Biçim: her alan `- Etiket: değer` satırıdır. Birden çok madde varsa alt satırlara iki boşluk girintiyle yaz.
> Başlık numaralarını (`## 1.` … `## 7.`) değiştirme; betik bölümleri numarasından bulur.

## 1. Kimlik
- Danışman adı (odada görünecek):
- Bölüm yöneticisi (sahibi):
- Tek cümleyle mesleği:
- Sahnedeki rengi (isteğe bağlı):

> ör. Danışman adı: Finans · Bölüm yöneticisi: ad, unvan · Renk: yeşil
> ör. Mesleği: "Finans danışmanı olarak kurulun bütçe, nakit ve maliyet sorularını muhasebe verisiyle yanıtlamak."

## 2. Hangi soruları alır
- Bu danışmana gelmesi gereken 5 örnek soru:
  1.
  2.
  3.
  4.
  5.
- Anahtar kelimeler (virgülle; İş Dağıtımcı bunlarla yönlendirir):
- Bu danışmana GELMEMESİ gereken, karışabilecek sorular:

> ör. anahtar kelimeler: bütçe, nakit, maliyet, sapma

## 3. Veri
| Kaynak | Ne var içinde | Nerede (sistem/dosya) | Kim erişim verir | Ne sıklıkta güncellenir |
|---|---|---|---|---|
|  |  |  |  |  |

- Bu verideki hassas alanlar (KVKK):
- Formülü/tanımı herkesçe bilinmeyen göstergeler:

> ör. gösterge: "upsell oranı nasıl hesaplanır" — formülü teyit edilene kadar `—` gösterilir.

## 4. Kurallar (kurallar.md'ye gidecek)
- Bu danışman ASLA şunu yapmamalı:
- Her yanıtta mutlaka olması gereken:
- Hangi sayıyı kim teyit eder:

## 5. İyi yanıt nasıl görünür
- Kurula giden ideal yanıtın bir örneği (yarım sayfa yeter):

## 6. Tempo (isteğe bağlı)
- Soru beklemeden düzenli üretmesini istediğin bir rapor:

> ör. "her pazartesi bütçe sapması"

## 7. Revize (Kağan doldurur)
- Model (boşsa sonnet):
- Ek yetenekler (virgülle; kurul-yaniti kendiliğinden eklenir):
- Gerekli anahtarlar (virgülle, ör. QA_READONLY_URL):
- Personel adı (boşsa evet; kapatmak için hayır):

## Kağan'ın revize kontrol listesi

`formlar/onayli/`'ye almadan önce. İşaretli olanları betik ayrıca denetler.

- [ ] Mesleği tek cümle ve bir fiille bitiyor (`description` alanı bu cümle olur)
- [ ] Anahtar kelimeler diğer danışmanlarla çakışmıyor — betik uyarır
- [ ] Her veri kaynağı **salt okunur** bir yolla bağlanabiliyor (SELECT rolü, dışa aktarım, paylaşılan klasör)
- [ ] Formülü teyitsiz gösterge `—` olarak işaretli ve teyit sahibi yazılı
- [ ] Formda kişisel veri yok — betik durur
- [ ] Ek yetenekler `skills/` altında var — betik durur
```

- [ ] **Step 2: `tests/fikstur/form/kalite.md` yaz** (sentetik; kişi adı yok, yalnız unvan):

```markdown
# Danışman Formu — Kalite

## 1. Kimlik
- Danışman adı (odada görünecek): Kalite
- Bölüm yöneticisi (sahibi): Kalite Müdürü
- Tek cümleyle mesleği: Kalite danışmanı olarak kurulun çağrı kalitesi ve şikâyet sorularını değerlendirme verisiyle yanıtlamak.
- Sahnedeki rengi (isteğe bağlı): mor

> ör. Danışman adı: Finans

## 2. Hangi soruları alır
- Bu danışmana gelmesi gereken 5 örnek soru:
  1. Bu ay kalite puanı en çok düşen ekip hangisi?
  2. Şikâyetlerin en sık konusu ne?
  3. ?
  4.
  5.
- Anahtar kelimeler (virgülle; İş Dağıtımcı bunlarla yönlendirir): kalite, şikâyet, memnuniyet, denetim
- Bu danışmana GELMEMESİ gereken, karışabilecek sorular:
  - Satış hedefleri (Satış Müdürü)

## 3. Veri
| Kaynak | Ne var içinde | Nerede (sistem/dosya) | Kim erişim verir | Ne sıklıkta güncellenir |
|---|---|---|---|---|
| Kalite değerlendirmeleri | çağrı puanları, bölüm skorları | QA veritabanı (salt okunur rol) | BT | günlük |
|  |  |  |  |  |

- Bu verideki hassas alanlar (KVKK): değerlendirilen temsilcinin adı
- Formülü/tanımı herkesçe bilinmeyen göstergeler:
  - Bölüm ağırlıklı kalite skoru

## 4. Kurallar (kurallar.md'ye gidecek)
- Bu danışman ASLA şunu yapmamalı:
  - Tek bir çağrıdan ekip geneli hakkında hüküm kurmak
- Her yanıtta mutlaka olması gereken:
  - Değerlendirilen çağrı sayısı (n)
- Hangi sayıyı kim teyit eder:
  - Bölüm ağırlıkları: Kalite Müdürü

## 5. İyi yanıt nasıl görünür
- Kurula giden ideal yanıtın bir örneği (yarım sayfa yeter):
  Önce tek cümlelik cevap.
  Sonra kaynaklı dayanak tablosu.

## 6. Tempo (isteğe bağlı)
- Soru beklemeden düzenli üretmesini istediğin bir rapor: ?

## 7. Revize (Kağan doldurur)
- Model (boşsa sonnet):
- Ek yetenekler (virgülle; kurul-yaniti kendiliğinden eklenir):
- Gerekli anahtarlar (virgülle, ör. QA_READONLY_URL): QA_READONLY_URL
- Personel adı (boşsa evet; kapatmak için hayır):
```

Not: "Hangi sayıyı kim teyit eder" satırındaki `Bölüm ağırlıkları: Kalite Müdürü` iki nokta taşır ama girintilidir;
`ALAN` deseni satır başında `- ` ister, girintili satır devam satırıdır (Task 5 testi bunu sınar).

- [ ] **Step 3: Sızıntı taraması yeni dosyaları da tarar, temiz kalmalı**

Run: `python3 -m unittest tests.test_kit 2>&1 | tail -3`
Expected: `OK`

- [ ] **Step 4: Commit** — `feat(form): DANISMAN-FORMU şablonu (§1–§7) ve Kalite fikstürü`

---

### Task 5: Form okuma ve zorunlu alanlar (K2, K3; testler 2, 3)

**Files:** `bin/formdan_takim.py` (yeni), `tests/test_formdan_takim.py`
**Interfaces:**
- `bolumler(metin) -> dict[int, str]`
- `alanlar(govde) -> dict[str, str]`
- `tablo(govde) -> tuple[list[str], list[str]]` — (başlık+ayraç, dolu satırlar)
- `oku(metin) -> dict` — anahtarlar: `ad, sahibi, meslek, renk` (str) · `ornek_sorular, anahtar_kelimeler, almaz,
  veri_baslik, veri, hassas, teyitsiz, asla, mutlaka, teyit, yetenekler, anahtarlar` (list[str]) ·
  `iyi_yanit, tempo, model, personel_adi` (str)
- `eksikler(form) -> list[str]` — her öğe `"eksik: <etiket>"`

Var olan koda dair: `dagitici._tr_kucuk` (`bin/dagitici.py:174-175`) Türkçe büyük/küçük harfi doğru çevirir;
etiket önekleri onunla karşılaştırılır. `dagitici` modülü `kos`, `soru_kapisi`, `soru_kaydi`'yı içe aktarır
(`bin/dagitici.py:33-36`); `tests/test_kit.py:42` de aynı içe aktarmayı yaptığı için ağ/yan etki yok.

- [ ] **Step 1: Testleri yaz** — `tests/test_formdan_takim.py`'ye, `KilitTesti`'nin üstüne:

```python
import ayar  # noqa: E402
import formdan_takim as ft  # noqa: E402

FORM = (KOK / "tests/fikstur/form/kalite.md").read_text(encoding="utf-8")


class OkumaTesti(unittest.TestCase):
    def test_tam_form_okunur(self):
        form = ft.oku(FORM)
        self.assertEqual(form["ad"], "Kalite")                       # `>` örnek satırı ezmez
        self.assertEqual(form["sahibi"], "Kalite Müdürü")
        self.assertTrue(form["meslek"].startswith("Kalite danışmanı olarak"))
        self.assertEqual(form["anahtar_kelimeler"], ["kalite", "şikâyet", "memnuniyet", "denetim"])
        self.assertEqual(len(form["ornek_sorular"]), 2)              # "3. ?" ve boş 4., 5. düşer
        self.assertEqual(len(form["veri"]), 1)                       # boş tablo satırı sayılmaz
        self.assertEqual(form["teyit"], ["Bölüm ağırlıkları: Kalite Müdürü"])  # girintili iki noktalı satır
        self.assertEqual(form["iyi_yanit"], "Önce tek cümlelik cevap.\nSonra kaynaklı dayanak tablosu.")
        self.assertEqual(form["tempo"], "")                          # yalnız "?" boş
        self.assertEqual(form["anahtarlar"], ["QA_READONLY_URL"])
        self.assertEqual(ft.eksikler(form), [])

    def test_bos_sablon_butun_zorunlulari_listeler(self):
        sablon = (KOK / "formlar/DANISMAN-FORMU.md").read_text(encoding="utf-8")
        self.assertEqual(len(ft.eksikler(ft.oku(sablon))), len(ft.ZORUNLU))

    def test_iki_eksik_birden_listelenir(self):
        """Test 2: ilk eksikte durulmaz."""
        metin = FORM.replace("- Tek cümleyle mesleği: Kalite danışmanı olarak kurulun çağrı kalitesi ve şikâyet "
                             "sorularını değerlendirme verisiyle yanıtlamak.", "- Tek cümleyle mesleği:")
        metin = metin.replace("| Kalite değerlendirmeleri | çağrı puanları, bölüm skorları | QA veritabanı (salt okunur rol) "
                              "| BT | günlük |\n", "")
        self.assertEqual(ft.eksikler(ft.oku(metin)),
                         ["eksik: §1 Tek cümleyle mesleği", "eksik: §3 Veri tablosu (en az bir dolu satır)"])

    def test_soru_isareti_bos_sayilir(self):
        """Test 3."""
        metin = FORM.replace("yönlendirir): kalite, şikâyet, memnuniyet, denetim", "yönlendirir): ?")
        self.assertEqual(ft.eksikler(ft.oku(metin)), ["eksik: §2 Anahtar kelimeler (en az bir)"])
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -5`
Expected: ERROR — `ModuleNotFoundError: No module named 'formdan_takim'`

- [ ] **Step 3: `bin/formdan_takim.py` yaz (okuma kısmı):**

```python
#!/usr/bin/env python3
"""Danışman formu → `takimlar/<bolum>/` (takim.md, kurallar.md, defter.md, durum.json).

Form `formlar/onayli/<bolum>.md`'dedir (şablon: `formlar/DANISMAN-FORMU.md`, NOVE-KURULUM.md §6).
Betiği yalnız Kağan koşturur; ajan yalnız `--kuru` ile çıktıyı gösterir
(docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md, K1).

Kullanım:
  python3 bin/formdan_takim.py <bolum>             # denetler ve yazar
  python3 bin/formdan_takim.py <bolum> --kuru      # denetler, ekrana basar, hiçbir dosya yazmaz
  python3 bin/formdan_takim.py <bolum> --yeniden   # kurulu danışmanı yeniden üretir; önce farkı gösterir
Çıkış: 0 yazıldı ya da kuru · 1 durdu (sebeplerin hepsi listelenir) · 2 kullanım hatası
"""
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import bekci  # noqa: E402
import dagitici  # noqa: E402

BASLIK = re.compile(r"^## (.*)$", re.M)
NUMARA = re.compile(r"^(\d+)\.")
ALAN = re.compile(r"^- ([^:]+):[ \t]*(.*)$")
MADDE = re.compile(r"^(\d+\.|-)\s*")
ZORUNLU = (
    ("ad", "§1 Danışman adı"),
    ("meslek", "§1 Tek cümleyle mesleği"),
    ("anahtar_kelimeler", "§2 Anahtar kelimeler (en az bir)"),
    ("ornek_sorular", "§2 Örnek sorular (en az bir)"),
    ("veri", "§3 Veri tablosu (en az bir dolu satır)"),
)


# --- form okuma (K2) --------------------------------------------------------

def bolumler(metin):
    """{numara: gövde} — `## N. …` başlıkları; gövde bir sonraki `## ` başlığında biter.

    Başlık metni değil numara bağlar. Numarasız başlık (revize kontrol listesi) hiçbir bölüme girmez."""
    baslar = list(BASLIK.finditer(metin))
    sonuc = {}
    for i, bas in enumerate(baslar):
        numara = NUMARA.match(bas.group(1).strip())
        if numara:
            son = baslar[i + 1].start() if i + 1 < len(baslar) else len(metin)
            sonuc[int(numara.group(1))] = metin[bas.end():son]
    return sonuc


def alanlar(govde):
    """{etiket: ham değer} — `- Etiket: değer` satırı ve altındaki devam satırları.

    `>` not satırları ve `|` tablo satırları hiçbir alana girmez; girintili satır her zaman devam satırıdır."""
    sonuc, etiket = {}, None
    for satir in govde.splitlines():
        alan = ALAN.match(satir)
        if alan:
            etiket = alan.group(1).strip()
            sonuc[etiket] = [alan.group(2)]
        elif satir.lstrip().startswith("|"):
            etiket = None
        elif etiket and not satir.lstrip().startswith(">"):
            sonuc[etiket].append(satir)
    return {k: "\n".join(v) for k, v in sonuc.items()}


def _bul(k, onek):
    onek = dagitici._tr_kucuk(onek)
    return next((v for e, v in k.items() if dagitici._tr_kucuk(e).startswith(onek)), "")


def _satirlar(ham):
    """Dolu satırlar: madde işareti (`1.`, `-`) atılır; boş ve yalnız '?' satır düşer."""
    temiz = (MADDE.sub("", s.strip()).strip() for s in (ham or "").splitlines())
    return [s for s in temiz if s and s != "?"]


def _tek(k, onek):
    return " ".join(_satirlar(_bul(k, onek)))


def _liste(k, onek):
    return _satirlar(_bul(k, onek))


def _virgullu(k, onek):
    parcalar = (p.strip() for s in _satirlar(_bul(k, onek)) for p in s.split(","))
    return [p for p in parcalar if p and p not in ("?", "…", "...")]


def _metin(k, onek):
    """Çok satırlı serbest metin: satırlar sırasıyla, girinti atılır; yalnız '?' ise boş."""
    satirlar = [s.strip() for s in _bul(k, onek).splitlines() if s.strip()]
    return "" if satirlar in ([], ["?"]) else "\n".join(satirlar)


def tablo(govde):
    """(başlık+ayraç satırları, dolu satırlar) — hücrelerinin hepsi boş ya da '?' olan satır sayılmaz."""
    satirlar = [s.strip() for s in (govde or "").splitlines() if s.strip().startswith("|")]
    dolu = [s for s in satirlar[2:] if any(h.strip() not in ("", "?") for h in s.strip("|").split("|"))]
    return satirlar[:2], dolu


def oku(metin):
    """Formu sözlüğe çevirir. Olmayan bölüm boş sayılır; eksikleri `eksikler` söyler."""
    b = bolumler(metin)
    k = {n: alanlar(b.get(n, "")) for n in range(1, 8)}
    veri_baslik, veri = tablo(b.get(3, ""))
    return {
        "ad": _tek(k[1], "Danışman adı"),
        "sahibi": _tek(k[1], "Bölüm yöneticisi"),
        "meslek": _tek(k[1], "Tek cümleyle mesleği"),
        "renk": _tek(k[1], "Sahnedeki rengi"),
        "ornek_sorular": _liste(k[2], "Bu danışmana gelmesi gereken"),
        "anahtar_kelimeler": _virgullu(k[2], "Anahtar kelimeler"),
        "almaz": _liste(k[2], "Bu danışmana GELMEMESİ"),
        "veri_baslik": veri_baslik,
        "veri": veri,
        "hassas": _liste(k[3], "Bu verideki hassas alanlar"),
        "teyitsiz": _liste(k[3], "Formülü/tanımı"),
        "asla": _liste(k[4], "Bu danışman ASLA"),
        "mutlaka": _liste(k[4], "Her yanıtta mutlaka"),
        "teyit": _liste(k[4], "Hangi sayıyı kim teyit eder"),
        "iyi_yanit": _metin(k[5], "Kurula giden ideal yanıtın"),
        "tempo": _tek(k[6], "Soru beklemeden"),
        "model": _tek(k[7], "Model"),
        "yetenekler": _virgullu(k[7], "Ek yetenekler"),
        "anahtarlar": _virgullu(k[7], "Gerekli anahtarlar"),
        "personel_adi": _tek(k[7], "Personel adı"),
    }


def eksikler(form):
    """Boş zorunlu alanların hepsi — ilk eksikte durulmaz."""
    return [f"eksik: {etiket}" for alan, etiket in ZORUNLU if not form[alan]]
```

- [ ] **Step 4: Yeşili gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -3`
Expected: `Ran 5 tests` · `OK`

- [ ] **Step 5: Commit** — `feat(form): formdan_takim — form okuma ve zorunlu alan listesi (K2)`

---

### Task 6: Kontroller (K4/1–3; testler 4, 5, 6 — birim düzeyi)

**Files:** `bin/formdan_takim.py`, `tests/test_formdan_takim.py`
**Interfaces:**
- `kisisel_veri(metin) -> list[str]` — `"kişisel veri: <tür> (<başlık>)"`; değer basılmaz
- `yetenek_sorunlari(kok, adlar) -> list[str]`
- `cakismalar(kok, bolum, kelimeler) -> list[str]` — uyarı metinleri

Var olan koda dair: `bekci.on_kontrol(metin)` ihlal **türlerinin** listesini döner (`bin/bekci.py:101-103`), değeri
değil; TC deseni sağlama hanesine bakar (`:74-82`). `dagitici.aktif_danismanlar(kok)` yalnız kurulu danışmanları,
kelimeleri `_tr_kucuk` ile küçültülmüş verir (`bin/dagitici.py:178-186`). `dagitici.cakisma` yalnız kurulu danışmanlar
arasında bakar (`:416-422`) — yeni danışman henüz kurulu olmadığı için ayrı karşılaştırma gerekir.

- [ ] **Step 1: Testleri yaz:**

```python
class KontrolTesti(unittest.TestCase):
    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.kok = Path(self._g.name)
        shutil.copytree(KOK / "skills/kurul-yaniti", self.kok / "skills/kurul-yaniti")

    def tearDown(self):
        self._g.cleanup()

    def test_telefon_durdurur_degeri_basmaz(self):
        """Test 4a."""
        metin = FORM.replace("  - Tek bir çağrıdan", "  - Arayan 0532 123 45 67 ise\n  - Tek bir çağrıdan")
        sorunlar = ft.kisisel_veri(metin)
        self.assertEqual(sorunlar, ["kişisel veri: telefon numarası (4. Kurallar (kurallar.md'ye gidecek))"])
        self.assertNotIn("0532", " ".join(sorunlar))

    def test_tc_kimlik_durdurur(self):
        """Test 4b — sağlama hanesi geçerli sentetik numara."""
        metin = FORM.replace("değerlendirilen temsilcinin adı", "değerlendirilen temsilcinin adı, 10000000146")
        self.assertIn("kişisel veri: TC kimlik numarası (3. Veri)", ft.kisisel_veri(metin))

    def test_temiz_form_ve_bos_sablon_temiz(self):
        self.assertEqual(ft.kisisel_veri(FORM), [])
        self.assertEqual(ft.kisisel_veri((KOK / "formlar/DANISMAN-FORMU.md").read_text(encoding="utf-8")), [])

    def test_olmayan_yetenek_durdurur(self):
        """Test 5."""
        self.assertEqual(ft.yetenek_sorunlari(self.kok, ["kurul-yaniti", "olmayan-yetenek"]),
                         ["yetenek yok: skills/olmayan-yetenek/SKILL.md"])

    def test_takimlar_alani_olmayan_yetenek_durdurur(self):
        yol = self.kok / "skills/bozuk/SKILL.md"
        yol.parent.mkdir(parents=True)
        yol.write_text("---\nname: bozuk\n---\n\n# bozuk\n", encoding="utf-8")
        self.assertEqual(ft.yetenek_sorunlari(self.kok, ["bozuk"]),
                         ["yetenek bozuk: skills/bozuk/SKILL.md 'takimlar: [...]' alanı taşımıyor"])

    def test_cakisma_uyari_metni(self):
        """Test 6 (birim): kurulu finans 'Şikâyet' taşıyor; büyük/küçük harf farkı çakışmayı gizlemez."""
        (self.kok / "takimlar/finans").mkdir(parents=True)
        (self.kok / "takimlar/finans/takim.md").write_text(
            "---\nname: finans\ndescription: x\nanahtar_kelimeler: [bütçe, Şikâyet]\n---\n\n# Finans\n",
            encoding="utf-8")
        uyarilar = ft.cakismalar(self.kok, "kalite", ["kalite", "şikâyet"])
        self.assertEqual(len(uyarilar), 1)
        self.assertIn("'şikâyet' → finans", uyarilar[0])

    def test_kendi_kelimesi_cakisma_sayilmaz(self):
        """`--yeniden`de danışman zaten kurulu: kendi kelimeleri uyarı vermez."""
        (self.kok / "takimlar/kalite").mkdir(parents=True)
        (self.kok / "takimlar/kalite/takim.md").write_text(
            "---\nname: kalite\ndescription: x\nanahtar_kelimeler: [kalite]\n---\n", encoding="utf-8")
        self.assertEqual(ft.cakismalar(self.kok, "kalite", ["kalite"]), [])
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -5`
Expected: ERROR — `AttributeError: module 'formdan_takim' has no attribute 'kisisel_veri'`

- [ ] **Step 3: `bin/formdan_takim.py`'ye ekle** (`eksikler`'in altına):

```python
# --- kontroller (K4) --------------------------------------------------------

def kisisel_veri(metin):
    """Formda kişisel veri ya da anahtar (`bekci.ON_KONTROL`) → durdurur. Değer basılmaz: yalnız tür ve yer.

    Her `## ` başlığının altı ayrı taranır; ilk başlıktan önceki metin de ("başlık") taranır."""
    baslar = list(BASLIK.finditer(metin))
    parcalar = [("başlık", metin[:baslar[0].start()] if baslar else metin)]
    for i, bas in enumerate(baslar):
        son = baslar[i + 1].start() if i + 1 < len(baslar) else len(metin)
        parcalar.append((bas.group(1).strip(), metin[bas.end():son]))
    return [f"kişisel veri: {tur} ({yer})" for yer, govde in parcalar for tur in bekci.on_kontrol(govde)]


def yetenek_sorunlari(kok, adlar):
    """Diskte olmayan ya da `takimlar: [...]` alanı taşımayan yetenek → durdurur."""
    sorunlar = []
    for ad in adlar:
        yol = Path(kok) / "skills" / ad / "SKILL.md"
        if not yol.is_file():
            sorunlar.append(f"yetenek yok: skills/{ad}/SKILL.md")
        elif not isinstance(ayar.frontmatter(yol.read_text(encoding="utf-8"))[0].get("takimlar"), list):
            sorunlar.append(f"yetenek bozuk: skills/{ad}/SKILL.md 'takimlar: [...]' alanı taşımıyor")
    return sorunlar


def cakismalar(kok, bolum, kelimeler):
    """Kurulu başka bir danışmanda da geçen kelimeler → uyarı, durdurmaz."""
    sahipler = {}
    for d in dagitici.aktif_danismanlar(kok):
        if d["takim"] != bolum:
            for kelime in d["kelimeler"]:
                sahipler.setdefault(kelime, []).append(d["takim"])
    uyarilar = []
    for kelime in kelimeler:
        diger = sahipler.get(dagitici._tr_kucuk(kelime).strip())
        if diger:
            uyarilar.append(f"anahtar kelime çakışması: '{kelime}' → {', '.join(sorted(diger))} "
                            "(İş Dağıtımcı karışabilir; python3 bin/dagitici.py --cakisma)")
    return uyarilar
```

- [ ] **Step 4: Yeşili gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -3`
Expected: `Ran 12 tests` · `OK`

- [ ] **Step 5: Commit** — `feat(form): formdan_takim — kişisel veri, yetenek ve çakışma kontrolleri (K4)`

---

### Task 7: Üretim ve yazma (K3, K4/3–4, K7; testler 1, 10, 6 uçtan uca)

**Files:** `bin/formdan_takim.py`, `tests/test_formdan_takim.py`
**Interfaces:**
- `takim_md(bolum, form) -> str` · `kurallar_md(bolum, form) -> str`
- `yetenege_ekle(metin, bolum) -> str` — SKILL.md'nin `takimlar:` satırına ekler; zaten varsa aynen döner
- `uret(kok, bolum, kuru=False, yeniden=False) -> dict` — `{"durum": "yazildi"|"kuru"|"durdu", "sebepler": [...],
  "uyarilar": [...], "dosyalar": {göreli_yol: metin}, "farklar": [str]}`

Var olan koda dair:
- `ayar.frontmatter` tek satırlık `anahtar: değer` ve `[a, b]` listelerini okur, değerleri **string** döner
  (`bin/ayar.py:122-157`): `butce_usd` `"2"` olarak okunur.
- `ayar.takim_bilgisi` dosya yoksa `None`, frontmatter'sızsa `{}` döner (`bin/ayar.py:160-166`); kurulu olma
  `bool(takim_bilgisi(...))`.
- `tests/test_skills.py:83` her kurulu takımın `takim.md`'sinde **"kuyruk maddesini `tamam` yap"** arar; iskeletin
  4. adımı (`takimlar/_iskelet/takim.md`) bu cümleyi taşımıyor — üretilen metin taşımalı.
- `dagitici.kuyruga_yaz` `durum.json` boşsa/yoksa `False` döner ve yazmaz (`bin/dagitici.py:71-73`): `durum.json`
  iskeletten mutlaka yazılır.
- `r-` maddesinde CEO bulguları maddenin `not` alanındadır (`bin/dagitici.py:77`, `:409`).
- `agents_uret.uret(kok)` yalnız kurulu takımlar için `.claude/agents/<t>.md` yazar (`bin/agents_uret.py:73-90`).

- [ ] **Step 1: Testleri yaz:**

```python
import agents_uret  # noqa: E402
import dagitici  # noqa: E402


class _GeciciKok(unittest.TestCase):
    """Geçici kök: iskelet, kurul-yaniti, kurulumdaki kalite (yalnız başlıklı takim.md) ve onaylı form."""

    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.kok = Path(self._g.name)
        shutil.copytree(KOK / "takimlar/_iskelet", self.kok / "takimlar/_iskelet")
        shutil.copytree(KOK / "skills/kurul-yaniti", self.kok / "skills/kurul-yaniti")
        (self.kok / "takimlar/kalite").mkdir()
        (self.kok / "takimlar/kalite/takim.md").write_text("# Kalite Danışmanı\n", encoding="utf-8")
        self.form(FORM)

    def tearDown(self):
        self._g.cleanup()

    def form(self, metin):
        yol = self.kok / "formlar/onayli/kalite.md"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(metin, encoding="utf-8")

    def oku(self, yol):
        return (self.kok / yol).read_text(encoding="utf-8")


class UretimTesti(_GeciciKok):
    def test_tam_form_kurulu_danisman_uretir(self):
        """Test 1 + bağlantı: üretilen danışmanı sürücü, dağıtıcı ve ajan üretici kurulu sayar."""
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual((sonuc["durum"], sonuc["sebepler"]), ("yazildi", []))
        fm, govde = ayar.frontmatter(self.oku("takimlar/kalite/takim.md"))
        self.assertEqual(fm["name"], "kalite")
        self.assertTrue(fm["description"].startswith("Kalite danışmanı olarak"))
        self.assertEqual(fm["skills"], ["kurul-yaniti"])
        self.assertEqual(fm["anahtar_kelimeler"], ["kalite", "şikâyet", "memnuniyet", "denetim"])
        self.assertEqual(fm["gerekli_anahtarlar"], ["QA_READONLY_URL"])
        self.assertEqual((fm["model"], fm["renk"], fm["butce_usd"]), ("sonnet", "mor", "2"))
        self.assertIn("Sahibi: Kalite Müdürü", govde)
        self.assertIn("kuyruk maddesini `tamam` yap", govde)
        self.assertIn("| Kalite değerlendirmeleri |", govde)
        self.assertEqual(ayar.kurulu_takimlar(self.kok), ["kalite"])
        self.assertIn("şikâyet", dagitici.aktif_danismanlar(self.kok)[0]["kelimeler"])
        self.assertEqual(agents_uret.uret(self.kok), ["kalite"])
        skill_fm, _ = ayar.frontmatter(self.oku("skills/kurul-yaniti/SKILL.md"))
        self.assertEqual(skill_fm["takimlar"], ["kalite"])
        self.assertEqual(json.loads(self.oku("takimlar/kalite/durum.json"))["takim"], "kalite")
        self.assertIn("# Defter — kalite", self.oku("takimlar/kalite/defter.md"))
        for klasor in ("kosu", "cikti"):
            self.assertTrue((self.kok / "takimlar/kalite" / klasor).is_dir())
        kurallar = self.oku("takimlar/kalite/kurallar.md")
        self.assertIn("- Tek bir çağrıdan ekip geneli hakkında hüküm kurmak", kurallar)
        self.assertIn("- Değerlendirilen çağrı sayısı (n)", kurallar)
        self.assertIn("Bölüm ağırlıkları: Kalite Müdürü", kurallar)
        self.assertIn("Bölüm ağırlıklı kalite skoru", kurallar)

    def test_iskelet_kalite_olcutleri_korunur(self):
        """kurallar.md iskeletin 'Çıktı kalite ölçütleri' maddelerinin hepsini taşır (iskelet değişirse kırmızı)."""
        iskelet = (KOK / "takimlar/_iskelet/kurallar.md").read_text(encoding="utf-8")
        olcutler = [s for s in iskelet.split("## Çıktı kalite ölçütleri", 1)[1].splitlines() if s.startswith("- ")]
        self.assertEqual(len(olcutler), 2)
        uretilen = ft.kurallar_md("kalite", ft.oku(FORM))
        for satir in olcutler:
            with self.subTest(satir=satir):
                self.assertIn(satir, uretilen)

    def test_personel_adi_varsayilan_acik(self):
        """Test 10a."""
        self.assertIn("Personel adı ve unvanı yazılabilir.", ft.kurallar_md("kalite", ft.oku(FORM)))

    def test_personel_adi_hayir_ise_yasak(self):
        """Test 10b — hasta/müşteri yasağı her iki durumda da yazılır."""
        metin = FORM.replace("kapatmak için hayır):", "kapatmak için hayır): Hayır")
        kurallar = ft.kurallar_md("kalite", ft.oku(metin))
        self.assertIn("Personel adı yazılmaz.", kurallar)
        self.assertNotIn("Personel adı ve unvanı yazılabilir.", kurallar)
        self.assertIn("Hasta ve müşteri adı, telefon, e-posta, TC kimlik no yazılmaz", kurallar)

    def test_durunca_hicbir_dosya_yazilmaz(self):
        """Test 2 + 4 + 5 birlikte: üç sebep listelenir, kalite kurulumda kalır, yetenek dosyası değişmez."""
        skill_once = self.oku("skills/kurul-yaniti/SKILL.md")
        metin = FORM.replace("- Tek cümleyle mesleği: Kalite", "- Tek cümleyle mesleği:\n- x: Kalite")
        metin = metin.replace("değerlendirilen temsilcinin adı", "0532 123 45 67")
        metin = metin.replace("kendiliğinden eklenir):", "kendiliğinden eklenir): olmayan-yetenek")
        self.form(metin)
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual(sonuc["durum"], "durdu")
        self.assertEqual(sonuc["sebepler"], ["eksik: §1 Tek cümleyle mesleği",
                                             "kişisel veri: telefon numarası (3. Veri)",
                                             "yetenek yok: skills/olmayan-yetenek/SKILL.md"])
        self.assertTrue(ayar.kurulumda_mi("kalite", self.kok))
        self.assertFalse((self.kok / "takimlar/kalite/kurallar.md").exists())
        self.assertEqual(self.oku("skills/kurul-yaniti/SKILL.md"), skill_once)

    def test_cakisma_uyarir_ve_yazar(self):
        """Test 6 (uçtan uca): uyarı var, durum yazildi."""
        (self.kok / "takimlar/finans").mkdir()
        (self.kok / "takimlar/finans/takim.md").write_text(
            "---\nname: finans\ndescription: x\nanahtar_kelimeler: [şikâyet]\n---\n", encoding="utf-8")
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual(sonuc["durum"], "yazildi")
        self.assertEqual(len(sonuc["uyarilar"]), 1)
        self.assertTrue((self.kok / "takimlar/kalite/kurallar.md").exists())
```

`"- x: Kalite"` satırı meslek değerini başka bir etikete taşır; böylece meslek boş kalır.
`import agents_uret` ve `import dagitici` satırları dosyanın üstündeki `import ayar` satırının yanına gider.

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -5`
Expected: ERROR — `AttributeError: module 'formdan_takim' has no attribute 'uret'`

- [ ] **Step 3: `bin/formdan_takim.py`'ye ekle.** Sabitler dosyanın üstüne (`ZORUNLU`'nun altına):

```python
ORTAK_YETENEK = "kurul-yaniti"
AD_DESENI = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")   # bin/takim-olustur.sh ile aynı
ARACLAR = "[Read, Write, Glob, Grep]"                  # takimlar/_iskelet/takim.md ile aynı
PERSONEL_IZNI = "Personel adı ve unvanı yazılabilir."
PERSONEL_YASAGI = "Personel adı yazılmaz."
HER_ZAMAN_YASAK = "Hasta ve müşteri adı, telefon, e-posta, TC kimlik no yazılmaz (ANAYASA §2)."
```

Fonksiyonlar (`cakismalar`'ın altına):

```python
# --- üretim (K3, K7) --------------------------------------------------------

def _yetenekler(form):
    return [ORTAK_YETENEK] + [y for y in form["yetenekler"] if y != ORTAK_YETENEK]


def _fm_liste(degerler):
    return "[" + ", ".join(degerler) + "]"


def _maddeler(degerler, girinti=""):
    return [f"{girinti}- {d}" for d in degerler] or [f"{girinti}- (formda yok)"]


def takim_md(bolum, form):
    fm = ["---", f"name: {bolum}", f"description: {form['meslek']}", "saglayici: anthropic",
          f"model: {form['model'] or 'sonnet'}", f"tools: {ARACLAR}",
          f"gerekli_anahtarlar: {_fm_liste(form['anahtarlar'])}", f"skills: {_fm_liste(_yetenekler(form))}",
          f"anahtar_kelimeler: {_fm_liste(form['anahtar_kelimeler'])}"]
    if form["renk"]:
        fm.append(f"renk: {form['renk']}")
    fm += [f"butce_usd: {ayar.KOSU_BUTCESI_USD:g}", "---", ""]
    govde = [
        f"# {form['ad']} Danışmanı", "",
        f"> Formdan üretildi: `formlar/onayli/{bolum}.md` → `bin/formdan_takim.py`. Elle değiştirme: formu revize et,",
        f"> `python3 bin/formdan_takim.py {bolum} --yeniden` koştur.", ""]
    if form["sahibi"]:
        govde += [f"Sahibi: {form['sahibi']}", ""]
    govde += ["## Hangi soruları alır", *_maddeler(form["ornek_sorular"]), "",
              "## Hangi soruları almaz", *_maddeler(form["almaz"]), "",
              "## Koşu adımları",
              "1. `durum.json` kuyruğuna bak. `s-<soru-id>` yeni sorudur; `r-<soru-id>` CEO reddinden sonra",
              "   düzeltmedir — maddenin `not` alanındaki CEO bulgularını oku, yalnız onları düzelt.",
              "2. Soru kaydını oku: `sirket-log/sorular/<soru-id>.md`. Soru belirsizse hangi yorumla yanıtladığını yaz.",
              "3. Girdi kaynaklarına (aşağıda) yalnız salt okunur yollarla bak.",
              f"4. Taslağı `takimlar/{bolum}/cikti/<soru-id>-taslak.md`'ye `kurul-yaniti` düzeninde yaz.",
              "5. İş bitince kuyruk maddesini `tamam` yap; `durum.json`'da `son_kosu` ve `defter_son_ders`'i güncelle.",
              "6. `defter.md`'ye bu koşudan çıkan **tek** dersi ekle (ders yoksa ekleme).",
              "7. Koşu kaydını `SIRKET_KOSU` yoluna yaz: ne okudun, ne ürettin, ne kaldı, hangi kaynaklardan.", "",
              "## Yetenekler",
              *[f"- `{y}` — `skills/{y}/SKILL.md`" for y in _yetenekler(form)], "",
              "## Girdi kaynakları", *form["veri_baslik"], *form["veri"], "",
              "## Çıktı sözleşmesi",
              f"- Dosya: `takimlar/{bolum}/cikti/<soru-id>-taslak.md`",
              "- Düzen: `skills/kurul-yaniti/SKILL.md` — Kısa yanıt · Dayanak · Bilinmeyenler · Not", "",
              "### İyi yanıt örneği (formdan, §5)", form["iyi_yanit"] or "(formda yok)", "",
              "## Tempo",
              (form["tempo"] or "Yok — yalnız soruyla koşar.")
              + " Zamanlı koşu `gunluk.ZAMANLI`'ya elle eklenir; bu dosya koşu başlatmaz.", ""]
    return "\n".join(fm + govde)


def kurallar_md(bolum, form):
    personel = (PERSONEL_YASAGI if dagitici._tr_kucuk(form["personel_adi"]) in ("hayır", "hayir")
                else PERSONEL_IZNI)
    satirlar = [
        f"# Kurallar — {form['ad']} Danışmanı", "",
        "> Bekçi bu dosyayı okur ve koşu kaydını buna göre denetler. Yalnızca insan değiştirir.",
        f"> Formdan üretildi: `formlar/onayli/{bolum}.md` → `bin/formdan_takim.py`.", "",
        "## Neye göre çalışır", "- ANAYASA'nın tamamı geçerlidir; aşağıdakiler ona ektir.", "",
        "## Asla yapmaz", *_maddeler(form["asla"]), "",
        "## Çıktı kalite ölçütleri",
        "- Her iddia etiketli (✅/🟡/⛔) ve kaynaklı.",
        "- Çıktı Türkçe; teknik terimler orijinal hâliyle kalır.",
        *[f"- {m}" for m in form["mutlaka"]], "",
        "## Teyit ve hassas veri",
        f"- {personel} {HER_ZAMAN_YASAK}",
        "- Sayıyı kim teyit eder:", *_maddeler(form["teyit"], "  "),
        "- Hassas alanlar (KVKK):", *_maddeler(form["hassas"], "  "),
        "- Formülü teyitsiz göstergeler — hesaplanmaz, `—` gösterilir ve teyit sahibi yazılır:",
        *_maddeler(form["teyitsiz"], "  "), ""]
    return "\n".join(satirlar)


def yetenege_ekle(metin, bolum):
    """SKILL.md frontmatter'ındaki `takimlar: [...]` satırına danışmanı ekler; zaten varsa metni aynen döner.

    Alanın varlığını `yetenek_sorunlari` önceden denetler; burada yoksa bir şey değişmez."""
    mevcut = ayar.frontmatter(metin)[0].get("takimlar") or []
    if bolum in mevcut:
        return metin
    return re.sub(r"^takimlar:.*$", "takimlar: " + _fm_liste([*mevcut, bolum]), metin, count=1, flags=re.M)


def uret(kok, bolum, kuru=False, yeniden=False):
    """Formu denetler, dosya metinlerini bellekte üretir; durma yoksa ve kuru değilse yazar.

    Durma hâlinde hiçbir dosya yazılmaz: bütün kontroller yazımdan önce biter."""
    kok = Path(kok)
    sonuc = {"durum": "durdu", "sebepler": [], "uyarilar": [], "dosyalar": {}, "farklar": []}
    if not AD_DESENI.match(bolum or ""):
        sonuc["sebepler"] = [f"klasör adı ASCII kebab-case olmalı: {bolum!r}"]
        return sonuc
    form_yolu = kok / "formlar" / "onayli" / f"{bolum}.md"
    if not form_yolu.is_file():
        sonuc["sebepler"] = [f"form yok: formlar/onayli/{bolum}.md (Kağan revize edip buraya koyar)"]
        return sonuc
    metin = form_yolu.read_text(encoding="utf-8")
    form = oku(metin)
    hedef = kok / "takimlar" / bolum
    sebepler = eksikler(form) + kisisel_veri(metin) + yetenek_sorunlari(kok, _yetenekler(form))
    if ((hedef / "kurallar.md").exists() or ayar.takim_bilgisi(bolum, kok)) and not yeniden:
        sebepler.append(f"takimlar/{bolum} zaten kurulu (kurallar.md ya da tanımlı takim.md var) — "
                        "yeniden üretmek için --yeniden; önce farkı gösterir")
    sonuc["uyarilar"] = cakismalar(kok, bolum, form["anahtar_kelimeler"])
    if sebepler:
        sonuc["sebepler"] = sebepler
        return sonuc
    dosyalar = {f"takimlar/{bolum}/takim.md": takim_md(bolum, form),
                f"takimlar/{bolum}/kurallar.md": kurallar_md(bolum, form)}
    for ad in ("defter.md", "durum.json"):   # ajanın hafızası: varsa dokunulmaz
        if not (hedef / ad).exists():
            iskelet = (kok / "takimlar" / "_iskelet" / ad).read_text(encoding="utf-8")
            dosyalar[f"takimlar/{bolum}/{ad}"] = iskelet.replace("TAKIM", bolum)
    for ad in _yetenekler(form):
        yol = f"skills/{ad}/SKILL.md"
        eski = (kok / yol).read_text(encoding="utf-8")
        if yetenege_ekle(eski, bolum) != eski:
            dosyalar[yol] = yetenege_ekle(eski, bolum)
    if yeniden:
        for yol, yeni in dosyalar.items():
            if (kok / yol).exists() and (eski := (kok / yol).read_text(encoding="utf-8")) != yeni:
                sonuc["farklar"].append("".join(difflib.unified_diff(
                    eski.splitlines(True), yeni.splitlines(True), f"a/{yol}", f"b/{yol}")))
    sonuc["dosyalar"] = dosyalar
    if kuru:
        sonuc["durum"] = "kuru"
        return sonuc
    for yol, icerik in dosyalar.items():
        (kok / yol).parent.mkdir(parents=True, exist_ok=True)
        (kok / yol).write_text(icerik, encoding="utf-8")
    for ad in ("kosu", "cikti"):
        (hedef / ad).mkdir(parents=True, exist_ok=True)
    sonuc["durum"] = "yazildi"
    return sonuc
```

- [ ] **Step 4: Yeşili gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -3`
Expected: `Ran 18 tests` · `OK`

- [ ] **Step 5: Commit** — `feat(form): formdan_takim — takim.md, kurallar.md, iskelet ve yetenek bağı (K3, K7)`

---

### Task 8: Komut satırı (K1; testler 7, 8 + bağlantı)

**Files:** `bin/formdan_takim.py`, `tests/test_formdan_takim.py`, `CLAUDE.md`
**Interfaces:** `bas(sonuc, bolum) -> None` · `main(argv, kok=None) -> int` · `__main__` → `raise SystemExit(main(sys.argv[1:]))`

Var olan desen: `bin/agents_uret.py:93` ve `bin/karar_defter.py:173-190` — `main(argv)` + `SystemExit`.
Argümansız çağrıda rc 2 deseni `bin/takim-olustur.sh:7` ile aynı.

- [ ] **Step 1: Testleri yaz:**

```python
class KomutTesti(_GeciciKok):
    def kostur(self, *argv):
        cikti = io.StringIO()
        with redirect_stdout(cikti):
            rc = ft.main(["kalite", *argv], kok=self.kok)
        return rc, cikti.getvalue()

    def test_kuru_hicbir_dosya_yazmaz(self):
        """Test 8."""
        skill_once = self.oku("skills/kurul-yaniti/SKILL.md")
        rc, cikti = self.kostur("--kuru")
        self.assertEqual(rc, 0)
        self.assertIn("=== takimlar/kalite/takim.md ===", cikti)
        self.assertIn("(kuru koşu: hiçbir dosya yazılmadı)", cikti)
        self.assertEqual(self.oku("takimlar/kalite/takim.md"), "# Kalite Danışmanı\n")
        for yol in ("kurallar.md", "defter.md", "durum.json", "kosu", "cikti"):
            self.assertFalse((self.kok / "takimlar/kalite" / yol).exists(), yol)
        self.assertEqual(self.oku("skills/kurul-yaniti/SKILL.md"), skill_once)

    def test_kurulu_danisman_durur_yeniden_once_fark_gosterir(self):
        """Test 7."""
        self.assertEqual(self.kostur()[0], 0)
        rc, cikti = self.kostur()
        self.assertEqual(rc, 1)
        self.assertIn("takimlar/kalite zaten kurulu", cikti)
        self.form(FORM.replace("değerlendirme verisiyle yanıtlamak.", "değerlendirme ve şikâyet verisiyle yanıtlamak."))
        rc, cikti = self.kostur("--yeniden")
        self.assertEqual(rc, 0)
        self.assertIn("--- a/takimlar/kalite/takim.md", cikti)
        self.assertIn("+description: Kalite danışmanı olarak kurulun çağrı kalitesi ve şikâyet sorularını "
                      "değerlendirme ve şikâyet verisiyle yanıtlamak.", cikti)
        self.assertIn("şikâyet verisiyle", self.oku("takimlar/kalite/takim.md"))

    def test_yeniden_defteri_ve_durumu_korur(self):
        self.kostur()
        (self.kok / "takimlar/kalite/defter.md").write_text("# Defter — kalite\n\n- ders\n", encoding="utf-8")
        durum = self.oku("takimlar/kalite/durum.json")
        self.assertEqual(self.kostur("--yeniden")[0], 0)
        self.assertIn("- ders", self.oku("takimlar/kalite/defter.md"))
        self.assertEqual(self.oku("takimlar/kalite/durum.json"), durum)

    def test_durunca_sebepler_ve_rc1(self):
        self.form(FORM.replace("yönlendirir): kalite, şikâyet, memnuniyet, denetim", "yönlendirir):"))
        rc, cikti = self.kostur()
        self.assertEqual(rc, 1)
        self.assertIn("durdu — 1 sebep, hiçbir dosya yazılmadı:", cikti)
        self.assertIn("eksik: §2 Anahtar kelimeler (en az bir)", cikti)

    def test_yazinca_sonraki_adimlari_basar(self):
        rc, cikti = self.kostur()
        self.assertEqual(rc, 0)
        self.assertIn("python3 bin/agents_uret.py", cikti)
        self.assertIn("python3 -m unittest discover -s tests", cikti)


class GirisNoktasiTesti(unittest.TestCase):
    """Bağlantı: `python3 bin/formdan_takim.py` gerçekten `main`'i çağırıyor (yazmayan iki yol)."""

    def _kostur(self, *argv):
        return subprocess.run([sys.executable, str(KOK / "bin/formdan_takim.py"), *argv],
                              capture_output=True, text=True, cwd=KOK)

    def test_argumansiz_rc2(self):
        sonuc = self._kostur()
        self.assertEqual(sonuc.returncode, 2)
        self.assertIn("kullanım:", sonuc.stderr)

    def test_olmayan_form_rc1_ve_sebep(self):
        sonuc = self._kostur("olmayan-bolum", "--kuru")
        self.assertEqual(sonuc.returncode, 1)
        self.assertIn("form yok: formlar/onayli/olmayan-bolum.md", sonuc.stdout)
```

- [ ] **Step 2: Kırmızıyı gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -5`
Expected: ERROR — `AttributeError: module 'formdan_takim' has no attribute 'main'`; `GirisNoktasiTesti` rc 0 ≠ 2

- [ ] **Step 3: `bin/formdan_takim.py`'nin sonuna ekle:**

```python
# --- komut ------------------------------------------------------------------

SONRAKI_ADIMLAR = ("python3 bin/agents_uret.py", "python3 -m unittest discover -s tests")


def bas(sonuc, bolum):
    for uyari in sonuc["uyarilar"]:
        print(f"⚠ {uyari}")
    if sonuc["durum"] == "durdu":
        print(f"durdu — {len(sonuc['sebepler'])} sebep, hiçbir dosya yazılmadı:")
        for sebep in sonuc["sebepler"]:
            print(f"  - {sebep}")
        return
    for fark in sonuc["farklar"]:
        print(fark)
    if sonuc["durum"] == "kuru":
        for yol, icerik in sonuc["dosyalar"].items():
            print(f"=== {yol} ===\n{icerik}")
        print("(kuru koşu: hiçbir dosya yazılmadı)")
        return
    print("yazıldı:")
    for yol in sonuc["dosyalar"]:
        print(f"  {yol}")
    print(f"  takimlar/{bolum}/kosu/ · takimlar/{bolum}/cikti/")
    print("Sonraki adımlar (betik koşturmaz, sen koştur):")
    for komut in SONRAKI_ADIMLAR:
        print(f"  {komut}")


def main(argv, kok=None):
    adlar = [a for a in argv if not a.startswith("--")]
    bilinmeyen = [a for a in argv if a.startswith("--") and a not in ("--kuru", "--yeniden")]
    if len(adlar) != 1 or bilinmeyen:
        print("kullanım: python3 bin/formdan_takim.py <bolum> [--kuru] [--yeniden]", file=sys.stderr)
        return 2
    sonuc = uret(kok or ayar.KOK, adlar[0], kuru="--kuru" in argv, yeniden="--yeniden" in argv)
    bas(sonuc, adlar[0])
    return 1 if sonuc["durum"] == "durdu" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: `CLAUDE.md`** — Yasaklar'a madde ekle ve klasör yapısına iki satır:

```
- `bin/formdan_takim.py`'yi ajan yalnız `--kuru` ile koşturur; yazan koşu Kağan'ın (spec K1)
```
```
formlar/              DANISMAN-FORMU.md şablonu · gelen/ (git'e girmez) · onayli/ (insanın)
docs/superpowers/     PLANS.md · specs/ · plans/
```

- [ ] **Step 5: Yeşili gör**

Run: `python3 -m unittest tests.test_formdan_takim -v 2>&1 | tail -3`
Expected: `Ran 25 tests` · `OK`

- [ ] **Step 6: Commit** — `feat(form): formdan_takim komut satırı — --kuru, --yeniden, rc 0/1/2 (K1)`

---

### Task 9: Belgeler ve durum

**Files:** `NOVE-KURULUM.md`, `docs/superpowers/PLANS.md`, spec frontmatter

- [ ] **Step 1: `NOVE-KURULUM.md` §6** — satır 255–293'teki ```` ```markdown ```` şablon bloğunu ve altındaki kontrol listesini
  (295–302) şu paragrafla değiştir (iki kopya birbirinden sapmasın):

```
Şablon ve revize kontrol listesi: `formlar/DANISMAN-FORMU.md` (§1–§6 yönetici, §7 Revize Kağan). Betik bölümleri
numarasından bulur; zorunlu alan, kişisel veri ve yetenek eksikse durur, anahtar kelime çakışmasında uyarır
(`docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md`).
```

- [ ] **Step 2: `NOVE-KURULUM.md` Faz 4** — "Form hattı kurulur" maddesini `- [x]` yap, sonuna ` — 19.10.2026` ekle.
  `:133` satırındaki "henüz yok — Faz 4'ün ilk adımında kurulur" → "şablon: `DANISMAN-FORMU.md`".

- [ ] **Step 3: Durum** — plan ve spec frontmatter `durum: acik`; `PLANS.md` satırları aynı.

- [ ] **Step 4: Commit** — `docs(form): §6 şablonu DANISMAN-FORMU.md'ye bağlandı, Faz 4 form hattı işaretlendi`

---

## Self-Review

**Spec kapsamı**

| Spec | Task |
|---|---|
| Kapsam tablosu (7 dosya) | 1 (settings), 2 (bekci), 3 (SKILL), 4 (şablon), 5–8 (betik, testler) |
| K1 yalnız Kağan / `--kuru` / kurulu ise dur / `--yeniden` fark | 7 (`uret`), 8 (`main`, CLAUDE.md) |
| K2 numaralı başlık, bütün eksikler, "?" boş | 5 |
| K3 eşleme (frontmatter, gövde, kurallar, iskelet) | 7 |
| K4/1 kişisel veri · /2 çakışma · /3 yetenek + takimlar · /4 klasörler · /5 sonraki adımlar | 6, 7, 8 |
| K5 kurul-yaniti | 3 |
| K6 kilitler + CLAUDE.md | 1 |
| K7 personel adı, Sahibi, Denetçi | 2, 7 |
| Testler 1–11 | 1→9 · 2,3→Task 5 · 4,5,6→Task 6+7 · 1,10→Task 7 · 7,8→Task 8 · 11→Task 2 |
| Kapsam dışı | Dokunulmadı: Kalite formunun doldurulması, `takim-olustur.sh`, CEO tavanı, hasta adı |

Bilerek dışarıda: `formlar/onayli/` ve `formlar/gelen/` klasörleri git'e açılmaz (ilki ajana kapalı, ikincisi
`.gitignore`'da); betik form yoksa görünür sebeple durur.

**Yer tutucu taraması:** Kodda TBD/TODO yok. SKILL.md'deki `<…>` yer tutucuları bilerek: ajan örnek sayıyı kopyalamasın.

**Tür tutarlılığı:** `oku()` anahtarları Task 5'te tanımlı; Task 6–8 aynı adları kullanır (`anahtar_kelimeler`,
`yetenekler`, `personel_adi`, `veri_baslik`). `uret` dönüşü Task 7'de tanımlı, `bas` aynı anahtarları okur.
`ayar.frontmatter` değerleri string döner: `butce_usd` testte `"2"` ile karşılaştırılır.

**Bağlantı:** `oku`, `eksikler`, `kisisel_veri`, `yetenek_sorunlari`, `cakismalar`, `takim_md`, `kurallar_md`,
`yetenege_ekle` → `uret` içinden; `uret`, `bas` → `main`; `main` → `__main__`. `GirisNoktasiTesti` gerçek
süreçle koşar: `__main__` satırı silinirse rc 0 döner, test kırmızı. Üretilen dosyaların sistemdeki tüketicileri
`test_tam_form_kurulu_danisman_uretir` içinde gerçekten çağrılır: `ayar.kurulu_takimlar`, `dagitici.aktif_danismanlar`,
`agents_uret.uret`.

**Docstring ile teslim edilen:** "ilk eksikte durulmaz" → iki eksikli girdiyle sınanıyor. "Değer basılmaz" →
`assertNotIn("0532", …)`. "Büyük/küçük harf farkı çakışmayı gizlemez" → `Şikâyet` / `şikâyet`. "İskelet değişirse
kırmızı" → iskeletin maddeleri dosyadan okunuyor, sayısı (2) sabitlenmiş. "Durunca hiçbir dosya yazılmaz" →
kurallar.md yok, takim.md kurulumda, SKILL.md aynı — üçü de sınanıyor.

**Cevaplanabilirlik** (üretilen `takim.md` talimatları → cevaplayan yer):
1 kuyruk/`r-` bulguları → `durum.json` `kuyruk[].not` (`bin/dagitici.py:77`) · 2 soru kaydı →
`sirket-log/sorular/<id>.md` (`bin/soru_kaydi.py`, `AJAN-KIMLIGI.md` "Girdi") · 3 girdi kaynakları → aynı dosyadaki
tablo · 4 taslak düzeni → `skills/kurul-yaniti/SKILL.md` · 5 `son_kosu`, `defter_son_ders` → iskelet `durum.json`
alanları · 7 `SIRKET_KOSU` → `kos.py`'nin verdiği ortam değişkeni (`agents_uret.ONSOZ` aynı talimatı taşır).
`kurul-yaniti`'nin "Bilinmeyenler" talimatındaki "teyidi kim verecek" → `kurallar.md` "Sayıyı kim teyit eder".

## Bitirme

- [ ] `python3 -m unittest discover -s tests` → `Ran 441 tests` · `OK (skipped=8)` (414 taban + 25 `test_formdan_takim`
  + 1 `test_skills` + 1 `test_bekci_nove`)
- [ ] `python3 bin/agents_uret.py --check` → `OK: agents güncel`
- [ ] `python3 bin/ayar.py` → rc 0
- [ ] `python3 bin/dagitici.py --cakisma` → `çakışan anahtar kelime: 0 — revize için hazır`
- [ ] `python3 bin/formdan_takim.py kalite --kuru` → rc 1 · `form yok: formlar/onayli/kalite.md` (form henüz Kağan'da)
- [ ] Ölçümü tekrarla: `python3 -c "import sys; sys.path.insert(0,'bin'); import ayar; print(ayar.kurulu_takimlar())"`
  → `[]` (gerçek kökte hiçbir danışman kurulmadı) · `git status --short takimlar/` → boş
- [ ] **Kağan (isteğe bağlı, anahtar ve küçük ücret ister):** `python3 bin/bekci_karsilastir.py` — Denetçi istemi
  değişti; NIM'in 3/3 ölçümü (`bin/bekci.py:41-42`) eski isteme aitti.
