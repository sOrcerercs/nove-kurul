#!/usr/bin/env python3
"""Soru kaydı — bir sorunun bütün hayatı tek dosyada (NOVE-KURULUM.md §2).

`sirket-log/sorular/<soru-id>.md`. Q&A Danışmanı başlığı açar (`soru_kapisi.py`), İş Dağıtımcı `## Dağıtım`,
sürücü `## Denetçi` (`kos.py`), CEO `## CEO — karar: …` (`ceo.py`) bölümünü ekler.

Bölümler yalnız **eklenir**; değişen tek satır başlıktaki `- durum:`. Akışın gerçeği bölümlerdir — `durum`
panelde gösterilecek etikettir, dağıtıcı kararını bölümlere bakarak verir.
"""
import re
from pathlib import Path

import ayar

BOLUM = re.compile(r"^## (Denetçi|CEO — karar: (onay|red)|CEO — kontrol yapılmadı)\s*$", re.MULTILINE)
DENETCI_KARARI = re.compile(r"^- karar: \*\*(\w+)\*\*", re.MULTILINE)


def yol(soru_id, kok=None):
    return Path(kok or ayar.KOK) / "sirket-log" / "sorular" / f"{soru_id}.md"


def _baslik(metin):
    """İlk `## ` bölümüne kadarki kısım — Q&A Danışmanı'nın yazdığı başlık."""
    return re.split(r"^## ", metin, maxsplit=1, flags=re.MULTILINE)[0]


def _satir(metin, ad):
    return re.compile(rf"^- {re.escape(ad)}:[ \t]*(.*?)[ \t]*$", re.MULTILINE).search(metin)


def alan(metin, ad):
    """Başlıktaki `- <ad>: değer`; yoksa None."""
    eslesme = _satir(_baslik(metin), ad)
    return eslesme.group(1) if eslesme else None


def bolum_alani(metin, baslik, ad):
    """Son `<baslik>` bölümündeki `- <ad>: değer`; yoksa None."""
    parcalar = metin.split(baslik + "\n")
    if len(parcalar) < 2:
        return None
    bolum = re.split(r"^## ", parcalar[-1], maxsplit=1, flags=re.MULTILINE)[0]
    eslesme = _satir(bolum, ad)
    return eslesme.group(1) if eslesme else None


def durum_yaz(dosya, durum):
    """Başlıktaki `- durum:` satırını değiştirir; bölümlere dokunmaz."""
    metin = Path(dosya).read_text(encoding="utf-8")
    baslik = _baslik(metin)
    yeni = re.sub(r"^- durum:.*$", f"- durum: {durum}", baslik, count=1, flags=re.MULTILINE)
    Path(dosya).write_text(yeni + metin[len(baslik):], encoding="utf-8")


def bolum_ekle(dosya, bolum):
    """Kaydın sonuna bir bölüm ekler; öncesinde boş satır, sonunda satır sonu."""
    with open(dosya, "a", encoding="utf-8") as f:
        f.write("\n" + bolum.strip("\n") + "\n")


def kararlar(metin):
    """Karar bölümleri geliş sırasıyla: [("denetci", "kabul"), ("ceo", "red"), ("ceo", "yapilmadi"), …]."""
    sonuc = []
    eslesmeler = list(BOLUM.finditer(metin))
    for i, e in enumerate(eslesmeler):
        if e.group(1) == "CEO — kontrol yapılmadı":
            sonuc.append(("ceo", "yapilmadi"))
        elif e.group(2):
            sonuc.append(("ceo", e.group(2)))
        else:
            son = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(metin)
            karar = DENETCI_KARARI.search(metin, e.end(), son)
            sonuc.append(("denetci", karar.group(1) if karar else "?"))
    return sonuc


def harcanan(metin):
    """Bölümlerdeki `maliyet: N USD` satırlarının toplamı — sorunun 5 USD'lik bütçesinden düşen (§9)."""
    toplam = 0.0
    for ham in ayar.MALIYET_DESENI.findall(metin[len(_baslik(metin)):]):
        try:
            toplam += float(ham)
        except ValueError:
            continue
    return toplam
