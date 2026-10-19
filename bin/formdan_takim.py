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
ORTAK_YETENEK = "kurul-yaniti"
AD_DESENI = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")   # bin/takim-olustur.sh ile aynı
ARACLAR = "[Read, Write, Glob, Grep]"                  # takimlar/_iskelet/takim.md ile aynı
PERSONEL_IZNI = "Personel adı ve unvanı yazılabilir."
PERSONEL_YASAGI = "Personel adı yazılmaz."
HER_ZAMAN_YASAK = "Hasta ve müşteri adı, telefon, e-posta, TC kimlik no yazılmaz (ANAYASA §2)."


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
