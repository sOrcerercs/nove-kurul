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
