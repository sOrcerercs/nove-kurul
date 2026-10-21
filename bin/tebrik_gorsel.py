"""Tebrik görseli — sabit şablona yazı basma, sığdırma, şeffaf logo.

Şablon metinsizdir; ad/ünvan/sabit metin yerleşim JSON'una göre basılır.
Ad yazıldığı gibi basılır (kırpma + iç boşluk teke; harf dönüşümü yok).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

SATIR_CARPANI = 1.25
LOGO_DOSYASI = Path(__file__).resolve().parent.parent / "tebrik" / "logo.png"


def _temizle(metin) -> str:
    return " ".join(str(metin or "").split())


def _font(yol: Path, boyut: int):
    return ImageFont.truetype(str(yol), boyut)


def _genislik(font, metin: str) -> float:
    return font.getlength(metin)


def _iki_satira_bol(metin: str, font) -> Optional[list]:
    """En dengeli boşluktan böler (iki satırın en geniş olanı en küçük)."""
    kelimeler = metin.split(" ")
    if len(kelimeler) < 2:
        return None
    en_iyi, en_iyi_g = None, None
    for i in range(1, len(kelimeler)):
        a, b = " ".join(kelimeler[:i]), " ".join(kelimeler[i:])
        w = max(_genislik(font, a), _genislik(font, b))
        if en_iyi_g is None or w < en_iyi_g:
            en_iyi, en_iyi_g = [a, b], w
    return en_iyi


def yazi_sigdir(metin, yazi_tipi_yolu, boyut, en_kucuk, genislik, yukseklik, satir_max):
    """Tek satırda boyutu 2'şer küçültür; en_kucuk'te sığmazsa iki satıra böler.

    Dönüş: (satırlar, boyut) ya da sığmazsa None.
    """
    metin = _temizle(metin)
    if not metin:
        return None
    yol = Path(yazi_tipi_yolu)
    b = boyut
    while True:
        font = _font(yol, b)
        if _genislik(font, metin) <= genislik and b * SATIR_CARPANI <= yukseklik:
            return [metin], b
        if b <= en_kucuk:
            break
        b = max(en_kucuk, b - 2)
    if satir_max >= 2:
        font = _font(yol, en_kucuk)
        satirlar = _iki_satira_bol(metin, font)
        if (satirlar
                and max(_genislik(font, s) for s in satirlar) <= genislik
                and 2 * en_kucuk * SATIR_CARPANI <= yukseklik):
            return satirlar, en_kucuk
    return None


def _renk(hex_):
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _alan_metni(alan, tebrik):
    a = alan["anahtar"]
    if a == "ad":
        return _temizle(tebrik.get("ad"))
    if a == "unvan":
        return _temizle(tebrik.get("unvan"))
    if tebrik["tur"] == "bayram" and a in ("tr", "en"):
        return _temizle((tebrik.get("bayram") or {}).get(a))
    return _temizle(alan.get("metin"))


def gorsel_uret(tebrik, sablon_klasoru, cikis, yazi_klasoru):
    """Şablona yazıyı basar, `cikis` PNG yoluna yazar. Sığmazsa None (dosya yazılmaz).

    Şablon PNG/JSON yoksa FileNotFoundError; yerleşimde logo var ama logo dosyası yoksa
    FileNotFoundError("logo yok").
    """
    sablon_klasoru, cikis, yazi_klasoru = Path(sablon_klasoru), Path(cikis), Path(yazi_klasoru)
    ad = tebrik["bayram"]["sablon"] if tebrik["tur"] == "bayram" else tebrik["tur"]
    yerlesim = json.loads((sablon_klasoru / f"{ad}.json").read_text(encoding="utf-8"))
    gorsel = Image.open(sablon_klasoru / yerlesim["gorsel"]).convert("RGB")
    cizici = ImageDraw.Draw(gorsel)

    isler = []
    for alan in yerlesim["alanlar"]:
        metin = _alan_metni(alan, tebrik)
        if not metin:
            continue
        x, y, w, h = alan["kutu"]
        yol = yazi_klasoru / alan["yazi_tipi"]
        sonuc = yazi_sigdir(metin, yol, alan["boyut"], alan["en_kucuk"], w, h,
                            alan.get("satir_max", 1))
        if sonuc is None:
            return None
        isler.append((alan, yol, sonuc))

    for alan, yol, (satirlar, boyut) in isler:
        x, y, w, h = alan["kutu"]
        font = _font(yol, boyut)
        satir_h = boyut * SATIR_CARPANI
        cx, cy = x + w / 2, y + h / 2
        for i, satir in enumerate(satirlar):
            sy = cy + (i - (len(satirlar) - 1) / 2) * satir_h
            cizici.text((cx, sy), satir, font=font, fill=_renk(alan["renk"]), anchor="mm")

    logo_yol = yerlesim.get("logo")
    if logo_yol:
        if not LOGO_DOSYASI.exists():
            raise FileNotFoundError("logo yok")
        lx, ly, lw = logo_yol
        logo = Image.open(LOGO_DOSYASI).convert("RGBA")
        logo = logo.resize((lw, max(1, round(logo.height * lw / logo.width))), Image.LANCZOS)
        gorsel.paste(logo, (lx, ly), logo)

    cikis.parent.mkdir(parents=True, exist_ok=True)
    gorsel.save(cikis, "PNG")
    return cikis


def logo_hazirla(kaynak, hedef):
    """Beyaz harfleri ayırır, kırpar, altına Poppins-Regular ile 'Group' yazar.

    Alfa, beyazlık = min(R,G,B) ölçüsünden: >= 200 opak beyaz, <= 120 şeffaf, arası doğrusal.
    (Parlaklık değil: gradyanın açık mavisi parlak ama beyaz değildir.)
    """
    im = Image.open(kaynak).convert("RGB")
    r, g_, b = im.split()
    beyazlik = ImageChops.darker(ImageChops.darker(r, g_), b)
    alt = 120
    alfa = beyazlik.point(
        lambda v: 0 if v <= alt else (255 if v >= 200 else round((v - alt) * 255 / (200 - alt))))
    kutu = alfa.getbbox()
    if kutu is None:
        raise ValueError("kaynakta beyaz harf bulunamadı")
    alfa = alfa.crop(kutu)
    w, h = alfa.size
    marka = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    marka.putalpha(alfa)

    font = ImageFont.truetype(
        str(Path(__file__).resolve().parent.parent / "tebrik" / "yazi-tipleri" / "Poppins-Regular.ttf"),
        max(1, round(h * 0.4)))
    metin_kutu = font.getbbox("Group")
    tw, th = metin_kutu[2] - metin_kutu[0], metin_kutu[3] - metin_kutu[1]
    bosluk = round(h * 0.1)
    tuval = Image.new("RGBA", (max(w, tw), h + bosluk + th), (255, 255, 255, 0))
    tuval.paste(marka, ((tuval.width - w) // 2, 0))
    ImageDraw.Draw(tuval).text(((tuval.width - tw) // 2 - metin_kutu[0], h + bosluk - metin_kutu[1]),
                               "Group", font=font, fill=(255, 255, 255, 255))
    Path(hedef).parent.mkdir(parents=True, exist_ok=True)
    tuval.save(hedef, "PNG")
