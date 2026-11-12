#!/usr/bin/env python3
"""Panel için Yanıt defteri okuma — salt okunur (spec: panel canlı, B7/B8).

`yanitlar/` ve `sirket-log/sorular/` altında yalnız okur; hiçbir dosya yazmaz. Görünürlük süzgeci, soru durumu,
reddedilen yanıtın KISA sebebi (ham Denetçi/CEO gerekçesi `kurul` rolüne gitmez) ve güvenli Markdown→HTML burada.
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dagitici  # noqa: E402
import soru_kaydi  # noqa: E402
import yanit_defteri  # noqa: E402
from soru_kapisi import _soran_eposta  # noqa: E402

ID_DESENI = re.compile(r"^[a-z0-9-]{1,64}$")
BITMIS_DURUMLAR = ("iletildi", "onaylanamadı", "yönlendirilemedi")
SON_EK = "Yöneticiniz bilgilendirildi."
KISA_SEBEPLER = {
    "kurulmadi": "Bu bölüm henüz kurulmadı.",
    "denetim": "Yanıt kalite denetiminden geçemedi.",
    "sure": "Süre doldu.",
    "butce": "Bu sorunun bütçesi doldu.",
    "diger": "Bu soruya şu an güvenilir bir yanıt verilemedi.",
}
_CEO_RED = re.compile(r"^CEO \d+\. kez reddetti")
_CEO_SURE = re.compile(r"^CEO \d+ kez başlatıldı")


# --- defter ayrıştırma -----------------------------------------------------

def defter_oku(metin):
    """Defter kaydı → {soru, soran, tarih, danisman, etiket, gorunurluk, kurula_not, yanit, gerekce}."""
    baslik, _, govde = metin.partition("\n\n")
    sonuc = {"soru": soru_kaydi.alan(baslik, "soru"), "soran": soru_kaydi.alan(baslik, "soran"),
             "tarih": soru_kaydi.alan(baslik, "tarih"), "danisman": soru_kaydi.alan(baslik, "danışman"),
             "etiket": soru_kaydi.alan(baslik, "etiket"), "gorunurluk": soru_kaydi.alan(baslik, "gorunurluk"),
             "kurula_not": None, "yanit": None, "gerekce": None}
    if govde.startswith("## Gerekçe\n"):
        sonuc["gerekce"] = govde[len("## Gerekçe\n"):].strip()
        return sonuc
    eslesme = re.search(r"^## Yanıt\n", govde, re.MULTILINE)
    if eslesme:
        sonuc["yanit"] = govde[eslesme.end():]
        on = govde[:eslesme.start()]
        if on.startswith("## Kurula not\n"):
            sonuc["kurula_not"] = on[len("## Kurula not\n"):].strip() or None
    return sonuc


def gorebilir_mi(soran, gorunurluk, eposta, rol):
    return (rol == "yonetici" or (soran or "").strip().lower() == (eposta or "").strip().lower()
            or gorunurluk == "kurul")


def kisa_sebep(gerekce):
    g = (gerekce or "").strip()
    if g.startswith(dagitici.KURULMADI):
        anahtar = "kurulmadi"
    elif g.startswith("Denetçi:") or _CEO_RED.match(g):
        anahtar = "denetim"
    elif _CEO_SURE.match(g):
        anahtar = "sure"
    elif g.startswith("soru bütçesi doldu"):
        anahtar = "butce"
    else:
        anahtar = "diger"
    return f"{KISA_SEBEPLER[anahtar]} {SON_EK}"


# --- Markdown → güvenli HTML -----------------------------------------------

_KALIN = re.compile(r"\*\*(.+?)\*\*")
_SIRALI = re.compile(r"^\d+\. ")
_AYIRICI = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _satir_ici(s):
    parcalar = re.split(r"(`[^`]+`)", s)
    cikti = []
    for p in parcalar:
        if len(p) > 1 and p.startswith("`") and p.endswith("`"):
            cikti.append(f"<code>{p[1:-1]}</code>")
        else:
            cikti.append(_KALIN.sub(r"<strong>\1</strong>", p))
    return "".join(cikti)


def _hucreler(satir):
    s = satir.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [h.strip() for h in s.split("|")]


def md_html(metin):
    if not metin or not metin.strip():
        return ""
    satirlar = html.escape(metin).splitlines()
    cikti, i = [], 0
    while i < len(satirlar):
        s = satirlar[i].rstrip()
        if not s.strip():
            i += 1
            continue
        baslik = re.match(r"^(#{1,6})\s+(.*)$", s)
        if baslik:
            seviye = {1: 3, 2: 4}.get(len(baslik.group(1)), 5)
            cikti.append(f"<h{seviye}>{_satir_ici(baslik.group(2))}</h{seviye}>")
            i += 1
        elif re.match(r"^[-*] ", s):
            ogeler = []
            while i < len(satirlar) and re.match(r"^[-*] ", satirlar[i]):
                ogeler.append(f"<li>{_satir_ici(satirlar[i][2:].strip())}</li>")
                i += 1
            cikti.append("<ul>" + "".join(ogeler) + "</ul>")
        elif re.match(r"^\d+\. ", s):
            ogeler = []
            while i < len(satirlar) and re.match(r"^\d+\. ", satirlar[i]):
                ogeler.append(f"<li>{_satir_ici(_SIRALI.sub('', satirlar[i]).strip())}</li>")
                i += 1
            cikti.append("<ol>" + "".join(ogeler) + "</ol>")
        elif "|" in s and i + 1 < len(satirlar) and _AYIRICI.match(satirlar[i + 1]) and "|" in satirlar[i + 1]:
            ust = "".join(f"<th>{_satir_ici(h)}</th>" for h in _hucreler(s))
            i += 2
            govde = []
            while i < len(satirlar) and "|" in satirlar[i] and satirlar[i].strip():
                govde.append("<tr>" + "".join(f"<td>{_satir_ici(h)}</td>" for h in _hucreler(satirlar[i])) + "</tr>")
                i += 1
            cikti.append(f"<table><thead><tr>{ust}</tr></thead><tbody>{''.join(govde)}</tbody></table>")
        else:
            cikti.append(f"<p>{_satir_ici(s.strip())}</p>")
            i += 1
    return "".join(cikti)


# --- okuma -----------------------------------------------------------------

def _oku(yol):
    try:
        return yol.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _defter_yollari(kok):
    dizin = Path(kok) / "yanitlar"
    return sorted(dizin.glob("*.md")) if dizin.is_dir() else []


def _soru_yollari(kok):
    dizin = Path(kok) / "sirket-log" / "sorular"
    return sorted(dizin.glob("*.md")) if dizin.is_dir() else []


def durum(kok, soru_id, eposta, rol):
    """Soru durumu; None → 404 (geçersiz id, kayıt yok, göremez: ayırt edilmez)."""
    if not isinstance(soru_id, str) or not ID_DESENI.match(soru_id):
        return None
    defter_metni = _oku(yanit_defteri.yol(soru_id, kok))
    soru_metni = _oku(soru_kaydi.yol(soru_id, kok))
    if defter_metni is not None:
        d = defter_oku(defter_metni)
        if not gorebilir_mi(d["soran"], d["gorunurluk"], eposta, rol):
            return None
        sonuc = {"soru_id": soru_id, "soru": d["soru"], "zaman": d["tarih"]}
        if d["etiket"] == "onaylanamadı":
            sonuc["durum"] = "onaylanamadi"
            sonuc["sebep"] = kisa_sebep(d["gerekce"])
            if rol == "yonetici":
                sonuc["gerekce"] = d["gerekce"]
        else:
            sonuc.update(durum="yanitlandi", etiket=d["etiket"], danisman=d["danisman"],
                         yanit_html=md_html(d["yanit"]))
            if d["kurula_not"]:
                sonuc["kurula_not_html"] = md_html(d["kurula_not"])
        return sonuc
    if soru_metni is None:
        return None
    if not gorebilir_mi(_soran_eposta(soru_metni), soru_kaydi.alan(soru_metni, "gorunurluk"), eposta, rol):
        return None
    sonuc = {"soru_id": soru_id, "soru": soru_kaydi.alan(soru_metni, "soru"),
             "zaman": soru_kaydi.alan(soru_metni, "zaman"), "durum": "arastiriliyor"}
    kayit_durumu = soru_kaydi.alan(soru_metni, "durum")
    if kayit_durumu in BITMIS_DURUMLAR:  # iş bitmiş ama defterde yok: panel sonsuza dek beklemesin
        sonuc["durum"] = "onaylanamadi"
        sonuc["sebep"] = kisa_sebep("")
        if rol == "yonetici":
            sonuc["gerekce"] = f"Yanıt defterinde kaydı yok (kayıt durumu: {kayit_durumu})"
        return sonuc
    not_ = soru_kaydi.alan(soru_metni, "not")
    if not_:
        sonuc["not"] = not_
    return sonuc


def liste(kok, eposta, rol):
    kayitlar, defterdekiler = [], set()
    for yol in _defter_yollari(kok):
        defterdekiler.add(yol.stem)
        metin = _oku(yol)
        if metin is None:
            continue
        d = defter_oku(metin)
        if not gorebilir_mi(d["soran"], d["gorunurluk"], eposta, rol):
            continue
        satir = {"soru_id": yol.stem, "tarih": d["tarih"], "soru": d["soru"], "danisman": d["danisman"],
                 "etiket": d["etiket"], "gorunurluk": d["gorunurluk"]}
        if rol == "yonetici":
            satir["soran"] = d["soran"]
        kayitlar.append(satir)
    kayitlar.sort(key=lambda s: s["tarih"] or "", reverse=True)
    acik = []
    for yol in _soru_yollari(kok):
        if yol.stem in defterdekiler or not ID_DESENI.match(yol.stem):
            continue
        metin = _oku(yol)
        if metin is None or _soran_eposta(metin) != (eposta or "").strip().lower():
            continue
        if soru_kaydi.alan(metin, "durum") in BITMIS_DURUMLAR:
            continue
        satir = {"soru_id": yol.stem, "soru": soru_kaydi.alan(metin, "soru"), "zaman": soru_kaydi.alan(metin, "zaman")}
        not_ = soru_kaydi.alan(metin, "not")
        if not_:
            satir["not"] = not_
        acik.append(satir)
    acik.sort(key=lambda s: s["zaman"] or "", reverse=True)
    return {"kayitlar": kayitlar, "acik": acik}


def acik_sorular(kok):
    """Defterde olmayan ve bitmiş durumda olmayan soru kayıtlarının id'leri."""
    sonuc = []
    for yol in _soru_yollari(kok):
        if yanit_defteri.yol(yol.stem, kok).exists():
            continue
        metin = _oku(yol)
        if metin is None or soru_kaydi.alan(metin, "durum") in BITMIS_DURUMLAR:
            continue
        sonuc.append(yol.stem)
    return sonuc
