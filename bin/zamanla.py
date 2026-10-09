#!/usr/bin/env python3
"""Zamanlayıcı kurucusu — macOS launchd. Üç iş kurar, başka hiçbir şey yapmaz.

Takvimli (saatinde bir kez koşar, biter):
  sabah  → `bin/gunluk.py --sabah`  · dağıtıcıyı koşturur, sabah raporunu yazar
  akşam  → `bin/gunluk.py --aksam`  · günün koşularını ve bekçi kararlarını denetler

Sürekli (açılışta başlar, ayakta kalır):
  sahne  → `bin/sahne.py`           · yerel panel, yalnız 127.0.0.1; iki yazma yeri var
                                      (kuyruk notu, karar kapatma)

Saatler `bin/ayar.py`'den türer (ANAYASA §4 tek yerde): sabah mesai açılışında, denetim
mesai kapanışından bir saat önce. Bilgisayar o saatte kapalı/uykudaysa launchd kaçan işi
açılışta koşturur — saat kaçmaz, iş kaçmaz. Panel hiçbir şey zamanlamaz — zamanlama
launchd'nin işi — ama istek üzerine bir takım koşusu başlatabilir; tavanı, mesai
kontrolünü ve kilidi `kos.py` uygular, panel değil.

Kullanım:
  python3 bin/zamanla.py --kuru     # kurulacak plist'leri bas, hiçbir şeye dokunma
  python3 bin/zamanla.py --kur      # plist'leri yaz ve launchd'ye yükle
  python3 bin/zamanla.py --durum    # yüklü mü, ne zaman koşacak
  python3 bin/zamanla.py --kaldir   # tetikleri kaldır (rapor dosyalarına dokunmaz)
"""
import hashlib
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

KOK = ayar.KOK
AJANLAR = Path.home() / "Library" / "LaunchAgents"
ON_EK = "com.nove-kurul"
LOG = "sirket-log/zamanlayici.log"

# Etiket köke bağlıdır: iki klon aynı launchd kaydını ele geçirmesin (klasör adı + yol hash'i).
# `com.nove-kurul.<klasor>-<hash6>.<tetik>`. Eski sürüm köksüz `com.nove-kurul.<tetik>` kullanırdı;
# `--durum` onu görürse "eski etiket" diye raporlar, kendiliğinden kaldırmaz.
IMZA_UZUNLUGU = 6

SAHNE_PORTU = 8770

# Saatler ayar.py'den türer; ikinci bir yerde sayı yazmaz.
TETIKLER = [
    {"ad": "sabah", "saat": ayar.MESAI_BASLANGIC, "dakika": 0, "bayrak": "--sabah",
     "ne": "dağıtıcı + sabah raporu"},
    {"ad": "aksam", "saat": ayar.MESAI_BITIS - 1, "dakika": 0, "bayrak": "--aksam",
     "ne": "günün koşuları + bekçi kararları"},
]

# Sürekli işler: takvimi yok, açılışta başlar ve ayakta kalır. Panel yalnız 127.0.0.1'e
# bağlanır, dışarıya açılmaz; yazdığı iki yer (kuyruk notu, karar kapatma) için bkz. bin/sahne.py.
SUREKLI = [
    {"ad": "sahne", "betik": "sahne.py", "argv": ["--port", str(SAHNE_PORTU)], "surekli": True,
     "ne": f"yerel panel · http://127.0.0.1:{SAHNE_PORTU}"},
]

TUM_ISLER = TETIKLER + SUREKLI


def _yol_degeri():
    """launchd'nin dar PATH'i `claude`'u bulamaz; bulunduğu dizin öne eklenir."""
    dizinler = ["/usr/bin", "/bin", "/usr/sbin", "/sbin", "/usr/local/bin", "/opt/homebrew/bin",
                str(Path.home() / ".local" / "bin")]
    claude = shutil.which("claude")
    if claude:
        dizinler.insert(0, str(Path(claude).parent))
    return ":".join(dict.fromkeys(dizinler))


def kok_imzasi(kok=None):
    """Kökü tek kelimeyle tanıtan imza: `<klasor>-<hash6>`. Aynı adlı iki klon çakışmaz."""
    yol = Path(kok or KOK).resolve()
    ozet = hashlib.sha1(str(yol).encode("utf-8")).hexdigest()[:IMZA_UZUNLUGU]
    return f"{yol.name}-{ozet}"


def etiket(ad, kok=None):
    return f"{ON_EK}.{kok_imzasi(kok)}.{ad}"


def eski_etiket(ad):
    """Köksüz eski etiket — yalnızca teşhis için; `--kur`/`--kaldir` buna dokunmaz."""
    return f"{ON_EK}.{ad}"


def plist_yolu(ad, kok=None):
    return AJANLAR / f"{etiket(ad, kok)}.plist"


def _plist_programi(yol):
    """plist'in çalıştırdığı betiğin yolu; dosya yoksa/bozuksa None."""
    try:
        with open(yol, "rb") as dosya:
            argv = plistlib.load(dosya).get("ProgramArguments") or []
    except (OSError, ValueError, plistlib.InvalidFileException):
        return None
    return argv[1] if len(argv) > 1 else None


def plist_icerigi(is_, kok=None, python=None):
    """Bir işin plist sözlüğü.

    Takvimli iş (sabah/akşam): `StartCalendarInterval` taşır, `RunAtLoad` yoktur —
    kurulum anında koşu başlatmaz, saatini bekler.
    Sürekli iş (sahne): açılışta başlar (`RunAtLoad`), düşerse launchd kaldırır
    (`KeepAlive`); takvimi yoktur.
    """
    kok = Path(kok or KOK)
    surekli = bool(is_.get("surekli"))
    betik = is_.get("betik", "gunluk.py")
    argv = list(is_.get("argv") or ([is_["bayrak"]] if is_.get("bayrak") else []))
    icerik = {
        "Label": etiket(is_["ad"], kok),
        "ProgramArguments": [python or sys.executable, str(kok / "bin" / betik), *argv],
        "WorkingDirectory": str(kok),
        "EnvironmentVariables": {"PATH": _yol_degeri()},
        "StandardOutPath": str(kok / LOG),
        "StandardErrorPath": str(kok / LOG),
        "RunAtLoad": surekli,
        "ProcessType": "Background",
    }
    if surekli:
        icerik["KeepAlive"] = True
    else:
        icerik["StartCalendarInterval"] = {"Hour": is_["saat"], "Minute": is_["dakika"]}
    return icerik


def _ne_zaman(is_):
    """İnsan için tek kelime: takvimli işin saati, sürekli işin 'açılışta'."""
    if is_.get("surekli"):
        return "açılışta · sürekli"
    return f"her gün {is_['saat']:02d}:{is_['dakika']:02d}"


def _launchctl(*argv):
    """launchctl çağrısı — (kod, çıktı). launchd yoksa ya da hata verirse istisna fırlatmaz."""
    try:
        sonuc = subprocess.run(["launchctl", *argv], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, f"launchctl çağrılamadı: {type(exc).__name__}"
    return sonuc.returncode, (sonuc.stdout + sonuc.stderr).strip()


def _hedef():
    return f"gui/{os.getuid()}"


def kur(kok=None):
    """plist'leri yazar ve yükler. Her tetik için (ad, yol, mesaj) döner."""
    AJANLAR.mkdir(parents=True, exist_ok=True)
    (Path(kok or KOK) / LOG).parent.mkdir(parents=True, exist_ok=True)
    sonuclar = []
    for tetik in TUM_ISLER:
        yol = plist_yolu(tetik["ad"], kok)
        with open(yol, "wb") as dosya:
            plistlib.dump(plist_icerigi(tetik, kok), dosya)
        _launchctl("bootout", f"{_hedef()}/{etiket(tetik['ad'], kok)}")   # varsa önce indir
        kod, cikti = _launchctl("bootstrap", _hedef(), str(yol))
        sonuclar.append({"ad": tetik["ad"], "yol": yol,
                         "mesaj": "yüklendi" if kod == 0 else f"yüklenemedi: {cikti or kod}"})
    return sonuclar


def kaldir(kok=None):
    sonuclar = []
    for tetik in TUM_ISLER:
        kod, cikti = _launchctl("bootout", f"{_hedef()}/{etiket(tetik['ad'], kok)}")
        yol = plist_yolu(tetik["ad"], kok)
        vardi = yol.exists()
        yol.unlink(missing_ok=True)
        sonuclar.append({"ad": tetik["ad"], "yol": yol,
                         "mesaj": "kaldırıldı" if (kod == 0 or vardi) else f"zaten yoktu ({cikti or kod})"})
    return sonuclar


def durum(kok=None):
    """Her tetik için: bu köke ait mi, yüklü mü, eski etiketle yüklü bir kalıntı var mı."""
    kok = Path(kok or KOK)
    bin_dizini = str((kok / "bin").resolve())
    sonuclar = []
    for tetik in TUM_ISLER:
        yol = plist_yolu(tetik["ad"], kok)
        program = _plist_programi(yol)
        # sembolik bağ farkı yanıltmasın: iki taraf da çözülerek karşılaştırılır
        baska = program if (program and not str(Path(program).resolve()).startswith(bin_dizini)) else None
        kod, _ = _launchctl("print", f"{_hedef()}/{etiket(tetik['ad'], kok)}")
        eski = eski_etiket(tetik["ad"])
        eski_kod, _ = _launchctl("print", f"{_hedef()}/{eski}")
        eski_yol = AJANLAR / f"{eski}.plist"
        sonuclar.append({**tetik, "etiket": etiket(tetik["ad"], kok),
                         "yuklu": kod == 0 and baska is None, "plist": yol.exists(),
                         "baska_kok": baska, "eski_etiket": eski,
                         "eski_yuklu": eski_kod == 0 or eski_yol.exists(),
                         "eski_kok": _plist_programi(eski_yol)})
    return sonuclar


def _eski_etiket_uyarisi():
    """Köksüz eski etiket hâlâ duruyorsa söyle — kaldırmak insanın kararı."""
    for tetik in TUM_ISLER:
        eski = eski_etiket(tetik["ad"])
        if (AJANLAR / f"{eski}.plist").exists() or _launchctl("print", f"{_hedef()}/{eski}")[0] == 0:
            print(f"⚠ eski etiket {eski} hâlâ yüklü — çift tetik olmasın diye kaldır: "
                  f"launchctl bootout {_hedef()}/{eski}")


def main(argv):
    if "--kuru" in argv:
        for tetik in TUM_ISLER:
            print(f"--- {etiket(tetik['ad'])} · {_ne_zaman(tetik)} · {tetik['ne']}")
            print(plistlib.dumps(plist_icerigi(tetik)).decode("utf-8"))
        print("(kuru koşu: hiçbir dosya yazılmadı, launchd'ye dokunulmadı)")
        return 0
    if "--kur" in argv:
        for s in kur():
            print(f"{s['ad']:<6} {s['mesaj']} — {s['yol']}")
        _eski_etiket_uyarisi()
        return 0
    if "--kaldir" in argv:
        for s in kaldir():
            print(f"{s['ad']:<6} {s['mesaj']}")
        _eski_etiket_uyarisi()
        return 0
    if "--durum" in argv:
        print(f"etiket: {ON_EK}.{kok_imzasi()}.<tetik>  ({KOK})")
        for s in durum():
            if s["baska_kok"]:
                isaret = f"· başka kök için yüklü: {s['baska_kok']}"
            elif s["yuklu"]:
                isaret = "✓ yüklü"
            else:
                isaret = "· plist var, yüklü değil" if s["plist"] else "· kurulu değil"
            print(f"{s['ad']:<6} {_ne_zaman(s):<16} {isaret:<40} {s['ne']}")
            if s["eski_yuklu"]:
                nere = f" (→ {s['eski_kok']})" if s["eski_kok"] else ""
                print(f"       ⚠ eski etiket {s['eski_etiket']} yüklü{nere} — "
                      f"`python3 bin/zamanla.py --kur` ile yenile")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
