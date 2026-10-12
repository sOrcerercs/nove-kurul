#!/usr/bin/env python3
"""Karar defterinin tek kapısı — doğrula, devral, kapat.

Kullanım:
  python3 bin/karar_defter.py --devral    # cikti/karar-*.json -> kararlar/ (sürücü çağırır)
  python3 bin/karar_defter.py --acik      # açık kararları JSON olarak bas

Ajan `kararlar/` altına hiç uğramaz: yeni kaydı `cikti/karar-<id>.json`'a yazar, bu betik
şemayı doğrulayıp taşır. Ajanın `Write` aracı "yeni dosya" ile "üzerine yaz"ı ayırt edemediği
için, dokunmaması gereken dizine hiç uğratmamak tek yapısal çözümdür (spec E2).

Kapatma da buradadır ki panel HTTP katmanında iş mantığı taşımasın ve defter tek yerden
sınanabilsin (spec E3).
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

TAKIM = "karar-takibi"
ZORUNLU = ("id", "kaynak", "acilis", "baslik", "karar", "durum")
DURUMLAR = ("acik", "uygulandi", "vazgecildi")
KAPANIS_DURUMLARI = ("uygulandi", "vazgecildi")
PANEL_ALANLARI = ("durum", "kapanis", "kapanis_zamani")
KIMLIK_DESENI = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
TARIH_DESENI = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _taban(kok=None):
    return Path(kok or ayar.KOK) / "takimlar" / TAKIM


def dogrula(kayit):
    """(tamam, sebep) — deftere girecek kaydın kapı denetimi."""
    if not isinstance(kayit, dict):
        return False, "kayıt sözlük değil"
    for alan in ZORUNLU:
        if alan not in kayit:
            return False, "zorunlu alan eksik: %s" % alan
        if not str(kayit[alan] or "").strip():
            return False, "zorunlu alan boş: %s" % alan
    if kayit["durum"] != "acik":
        return False, "yeni kayıt 'acik' olmalı, gelen: %r" % kayit["durum"]
    if not KIMLIK_DESENI.match(str(kayit["id"])):
        return False, "id yalnız harf, rakam, '-' ve '_' içerebilir: %r" % kayit["id"]
    if not TARIH_DESENI.match(str(kayit["acilis"])):
        return False, "acilis ISO tarihle başlamalı (YYYY-AA-GG): %r" % kayit["acilis"]
    for alan in ("kapanis", "kapanis_zamani"):
        if kayit.get(alan) is not None:
            return False, "%s panele ayrılmış, yeni kayıtta boş/null olmalı: %r" % (alan, kayit[alan])
    return True, None


def hedef_yolu(kok, kayit):
    """`kararlar/<acilis tarihi>-<id>.json` — ad kaydın kendi alanından kurulur,
    dosya adına güvenilmez."""
    return _taban(kok) / "kararlar" / ("%s-%s.json" % (str(kayit["acilis"])[:10], kayit["id"]))


def devral(kok=None):
    """`cikti/karar-*.json`'u doğrulayıp `kararlar/` altına taşır. Sonuç listesi döner.

    Reddedilen dosya `cikti/`'da kalır — sessizce kaybolmaz (ANAYASA §2)."""
    taban = _taban(kok)
    cikti, defter = taban / "cikti", taban / "kararlar"
    if not cikti.is_dir():
        return []
    defter.mkdir(parents=True, exist_ok=True)
    sonuclar = []
    for yol in sorted(cikti.glob("karar-*.json")):
        try:
            kayit = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, ValueError) as hata:
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": None,
                             "sebep": "okunamadı: %s" % type(hata).__name__})
            continue
        tamam, sebep = dogrula(kayit)
        if not tamam:
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": None, "sebep": sebep})
            continue
        if any(k.get("id") == kayit["id"] for k in kararlar(kok)):
            # Dosya adı değil `id` denetimi: aynı id farklı `acilis` ile farklı bir
            # dosya adına düşebilir (bkz. hedef_yolu) — o zaman aşağıdaki hedef.exists()
            # bunu yakalayamaz ve aynı karar deftere iki kez, iki ayrı dosya olarak girer.
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": None,
                             "sebep": "defterde id zaten var: %s" % kayit["id"]})
            continue
        hedef = hedef_yolu(kok, kayit)
        try:
            hedef.resolve().relative_to(defter.resolve())
        except ValueError:
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": None,
                             "sebep": "hedef defter dışına çıkıyor"})
            continue
        if hedef.exists():
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": hedef,
                             "sebep": "defterde zaten var: %s" % hedef.name})
            continue
        try:
            hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
            yol.unlink()
        except OSError as hata:
            sonuclar.append({"kaynak": yol, "tamam": False, "hedef": hedef,
                             "sebep": "yazılamadı: %s" % type(hata).__name__})
            continue
        sonuclar.append({"kaynak": yol, "tamam": True, "hedef": hedef, "sebep": None})
    return sonuclar


def kararlar(kok=None):
    """Defterdeki tüm kayıtlar, `acilis`'a göre artan. Bozuk dosya atlanır."""
    defter = _taban(kok) / "kararlar"
    cikan = []
    if not defter.is_dir():
        return cikan
    for yol in sorted(defter.glob("*.json")):
        try:
            cikan.append(json.loads(yol.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(cikan, key=lambda k: str(k.get("acilis") or ""))


def acik_kararlar(kok=None):
    return [k for k in kararlar(kok) if k.get("durum") == "acik"]


def kapat(kok, id_, durum, kapanis=None):
    """(tamam, sebep) — var olan bir kaydın YALNIZ üç alanını değiştirir (spec E3).

    Yeni dosya yaratmaz, silmez, `acik` olmayanı ikinci kez kapatmaz. Yazma aynı dizinde
    geçici dosyaya yapılıp `os.replace` ile atomik olarak yerine konur (POSIX). Bu, tek
    yazıcı varsayar: sürücü sıralı çalışır, eşzamanlı iki `kapat` çağrısı ikisi de
    yazmadan önce `durum == 'acik'`i görebilir (yarış koşulu, kilitleme yok)."""
    if durum not in KAPANIS_DURUMLARI:
        return False, "durum 'uygulandi' ya da 'vazgecildi' olmalı, gelen: %r" % durum
    defter = _taban(kok) / "kararlar"
    if not defter.is_dir():
        return False, "defter yok"
    for yol in sorted(defter.glob("*.json")):
        try:
            kayit = json.loads(yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if kayit.get("id") != id_:
            continue
        if kayit.get("durum") != "acik":
            return False, "kayıt zaten kapalı (%s) — yalnız 'acik' kayıt kapatılır" % kayit.get("durum")
        yeni = {**kayit, "durum": durum, "kapanis": (kapanis or None),
                "kapanis_zamani": ayar.simdi_iso()}
        gecici_fd, gecici_ad = tempfile.mkstemp(dir=str(yol.parent), prefix=".gecici-",
                                                 suffix=".json")
        try:
            with os.fdopen(gecici_fd, "w", encoding="utf-8") as dosya:
                dosya.write(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n")
            os.replace(gecici_ad, str(yol))
        except OSError:
            try:
                os.unlink(gecici_ad)
            except OSError:
                pass
            raise
        return True, "kapatıldı: %s" % durum
    return False, "karar bulunamadı: %s" % id_


def main(argv):
    if "--devral" in argv:
        sonuc = devral()
        for s in sonuc:
            if s["tamam"]:
                print("devralındı: %s" % s["hedef"].name)
            else:
                print("REDDEDİLDİ %s — %s" % (s["kaynak"].name, s["sebep"]), file=sys.stderr)
        return 0
    if "--acik" in argv:
        print(json.dumps(acik_kararlar(), ensure_ascii=False, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
