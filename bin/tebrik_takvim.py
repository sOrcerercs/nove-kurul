"""Tebrik takvimi — tablo okuma, doğrulama, bugünün tebrikleri.

Salt okunur, ağ yok. Ad yazıldığı gibi basılır (büyük/küçük harf dönüşümü yok).
"""
from __future__ import annotations

import calendar
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dagitici import _tr_kucuk  # noqa: E402

SUTUNLAR = ("Ad Soyad", "Ünvan", "Doğum günü", "İşe giriş tarihi")

_GG_AA = re.compile(r"^(\d{1,2})[./](\d{1,2})$")
_GG_AA_YYYY = re.compile(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$")


def _bos(deger) -> bool:
    return deger is None or str(deger).strip() == ""


def xlsx_oku(yol: Path) -> list:
    """İlk sayfa, ilk satır başlık. Başlık kırpılır, büyük/küçük harf duyarsız eşleşir."""
    import openpyxl
    wb = openpyxl.load_workbook(str(yol), read_only=True, data_only=True)
    try:
        satirlar = list(wb.worksheets[0].iter_rows(values_only=True))
    finally:
        wb.close()
    basliklar = [_tr_kucuk(str(b).strip()) if b is not None else "" for b in (satirlar[0] if satirlar else ())]
    sira = {}
    for sutun in SUTUNLAR:
        anahtar = _tr_kucuk(sutun)
        if anahtar not in basliklar:
            raise ValueError(f"eksik sütun: {sutun}")
        sira[sutun] = basliklar.index(anahtar)
    sonuc = []
    for s in satirlar[1:]:
        sonuc.append({sutun: (s[i] if i < len(s) else None) for sutun, i in sira.items()})
    return sonuc


def ad_temizle(ad) -> str:
    return " ".join(str(ad or "").split())


def gun_ay(deger):
    if isinstance(deger, (datetime, date)):
        return (deger.day, deger.month)
    if _bos(deger):
        return None
    metin = str(deger).strip()
    m = _GG_AA.match(metin) or _GG_AA_YYYY.match(metin)
    if not m:
        return None
    g, a = int(m.group(1)), int(m.group(2))
    try:
        date(2024, a, g)  # artık yıl: 29.02 geçerli
    except ValueError:
        return None
    return (g, a)


def tam_tarih(deger):
    if isinstance(deger, datetime):
        return deger.date()
    if isinstance(deger, date):
        return deger
    if _bos(deger):
        return None
    m = _GG_AA_YYYY.match(str(deger).strip())
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def dogrula(satirlar: list):
    """(kişiler, eksikler). Eksik metni ad + sorun; boş satır sessizce atlanır."""
    kisiler, eksik, gorulen = [], [], set()
    for no, satir in enumerate(satirlar, start=2):  # 1. satır başlık
        if all(_bos(satir.get(s)) for s in SUTUNLAR):
            continue
        ad = ad_temizle(satir.get("Ad Soyad"))
        if not ad:
            eksik.append(f"{no}. satır — ad yok")
            continue
        anahtar = _tr_kucuk(ad)
        if anahtar in gorulen:
            eksik.append(f"{ad} — tekrarlı satır")
            continue
        gorulen.add(anahtar)
        dogum_ham, giris_ham = satir.get("Doğum günü"), satir.get("İşe giriş tarihi")
        dogum, giris = gun_ay(dogum_ham), tam_tarih(giris_ham)
        if _bos(dogum_ham):
            eksik.append(f"{ad} — doğum günü yok")
        elif dogum is None:
            eksik.append(f"{ad} — doğum günü okunamadı: '{str(dogum_ham).strip()}'")
        if not _bos(giris_ham) and giris is None:
            eksik.append(f"{ad} — işe giriş tarihi okunamadı: '{str(giris_ham).strip()}'")
        kisiler.append({"ad": ad, "unvan": ad_temizle(satir.get("Ünvan")), "dogum": dogum, "giris": giris})
    return kisiler, eksik


def bayram_bugun(bayramlar: list, gun: date):
    """Yalnız başlangıç günü eşleşir (çok günlü bayramda ilk gün)."""
    iso = gun.isoformat()
    for b in bayramlar:
        if b.get("baslangic") == iso:
            return b
    return None


def _dogum_gunu_mu(dogum, gun: date) -> bool:
    if not dogum:
        return False
    if dogum == (29, 2) and not calendar.isleap(gun.year):
        return (gun.day, gun.month) == (28, 2)  # artık olmayan yılda 28 Şubat
    return dogum == (gun.day, gun.month)


def bugunun_tebrikleri(kisiler: list, bayramlar: list, gun: date) -> list:
    """Sıra: bayram, hoş geldin, doğum günü; kendi içinde ada göre."""
    sonuc = []
    b = bayram_bugun(bayramlar, gun)
    if b:
        sonuc.append({"tur": "bayram", "ad": "", "unvan": "", "bayram": b})
    for tur, uygun in (("hos_geldin", lambda k: k.get("giris") == gun),
                       ("dogum_gunu", lambda k: _dogum_gunu_mu(k.get("dogum"), gun))):
        for k in sorted((k for k in kisiler if uygun(k)), key=lambda k: _tr_kucuk(k["ad"])):
            sonuc.append({"tur": tur, "ad": k["ad"], "unvan": k["unvan"], "bayram": None})
    return sonuc
