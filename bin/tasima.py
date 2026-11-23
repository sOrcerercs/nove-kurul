#!/usr/bin/env python3
"""Taşıma — Mac'teki çalışma durumunu tek arşivle sunucuya taşır (spec: sunucu teslimi, S-1/S-2).

S-1 sırası (Kağan, taşıma günü): 1) zamanlayıcıyı kaldır: `python3 bin/zamanla.py --kaldir`
2) panel/sahneyi durdur (8770) 3) açık soru kalmasın 4) paketle. Bu betik 1-3'ü denetler, sağlanmazsa paketlemez;
zorlama bayrağı yoktur. Paketleme boyunca koşu kilidi (`.kos.lock`) tutulur: arada koşu başlayamaz.

`.env` paketlenmez (S-2): sunucuda yazılımcı yazar. Hiçbir parçası `.env` ile başlayan yol paketlenmez ve açılmaz.
Çıktıya dosya adı ya da içerik yazılmaz; yalnız üst klasör başına adet.

Kullanım:
    python3 bin/tasima.py --paketle [--cikti DIZIN] [--kuru]   # varsayılan çıktı: ev klasörü
    --kuru: engelleri ve özeti basar, arşiv yazmaz, kilit almaz.
Çıkış: 0 tamam · 1 reddedildi · 2 kullanım hatası. Ajan ortamında (CLAUDECODE) yalnız --kuru çalışır.
"""
from __future__ import annotations

import fcntl
import fnmatch
import hashlib
import os
import socket
import sys
import tarfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import panel_defter  # noqa: E402
import zamanla  # noqa: E402

KOK = ayar.KOK
AJAN_ISARETI = "CLAUDECODE"
PANEL_PORTU = 8770
TASINANLAR = ("yanitlar", "sirket-log", "deploy/roller.json", "deploy/kullanicilar.json",
              "deploy/posta-alicilari.json", "formlar/onayli", "takimlar/*/defter.md", "takimlar/*/durum.json",
              "takimlar/*/kosu", "takimlar/*/cikti", "takimlar/bekci-telemetri.jsonl")
ATLANAN_ADLAR = (".DS_Store", ".kilit", "__pycache__")


class TasimaHatasi(Exception):
    """İletisi dosya içeriği ya da adı taşımaz."""


def izinli_mi(goreli: str) -> bool:
    """Paketleme ve açma aynı kuralı kullanır."""
    if not goreli or goreli.startswith("/") or "\\" in goreli or "\0" in goreli:
        return False
    parcalar = goreli.split("/")
    if any(p in ("", ".", "..") or p.startswith(".env") for p in parcalar):
        return False
    if parcalar[-1] in ATLANAN_ADLAR:
        return False
    if parcalar[0] == "takimlar" and len(parcalar) > 1 and parcalar[1].startswith("_"):
        return False
    for kural in TASINANLAR:
        kp = kural.split("/")
        if len(parcalar) >= len(kp) and all(fnmatch.fnmatchcase(p, k) for p, k in zip(parcalar, kp)):
            return True
    return False


def dosyalar(kok) -> list:
    """İzinli düzenli dosyalar, sıralı; sembolik bağ ve özel dosya atlanır."""
    kok = Path(kok)
    sonuc = set()
    for kural in TASINANLAR:
        for yol in kok.glob(kural):
            if yol.is_symlink():
                continue
            if yol.is_dir():
                for dizin, _, adlar in os.walk(yol):
                    for ad in adlar:
                        sonuc.add(Path(dizin) / ad)
            else:
                sonuc.add(yol)
    gecenler = []
    for yol in sonuc:
        goreli = yol.relative_to(kok).as_posix()
        if izinli_mi(goreli) and not yol.is_symlink() and yol.is_file():
            gecenler.append(goreli)
    return sorted(gecenler)


@contextmanager
def kos_kilidi(kok):
    """Koşu kilidini paketleme/açma boyunca tutar; alınamazsa TasimaHatasi."""
    with open(Path(kok) / ayar.KOSU_KILIDI, "a") as kilit:
        try:
            fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TasimaHatasi("koşu kilidi dolu — süren koşu bitsin") from None
        try:
            yield
        finally:
            fcntl.flock(kilit, fcntl.LOCK_UN)


def _mac_denetimi(kok) -> list:
    if sys.platform != "darwin":
        return []
    nedenler = []
    if any(is_["yuklu"] for is_ in zamanla.durum(kok)):
        nedenler.append("zamanlayıcı kurulu — önce: python3 bin/zamanla.py --kaldir")
    try:
        socket.create_connection(("127.0.0.1", PANEL_PORTU), timeout=1).close()
        nedenler.append(f"{PANEL_PORTU}'te panel/sahne çalışıyor — önce durdur")
    except OSError:
        pass
    return nedenler


def engeller(kok, mac_denetimi=None) -> list:
    sonuc = []
    acik = panel_defter.acik_sorular(kok)
    if acik:
        sonuc.append(f"açık soru var: {len(acik)} ({', '.join(acik)})")
    sonuc.extend((mac_denetimi or _mac_denetimi)(kok))
    return sonuc


def _ozet(liste) -> dict:
    ozet = {}
    for g in liste:
        ust = g.split("/")[0]
        ozet[ust] = ozet.get(ust, 0) + 1
    return ozet


def _simdi():
    return datetime.now()


def _ici_mi(dizin: Path, kok: Path) -> bool:
    try:
        dizin.resolve().relative_to(kok.resolve())
        return True
    except ValueError:
        return False


def _yeni_dosya(yol: Path):
    try:
        return os.fdopen(os.open(yol, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")
    except FileExistsError:
        raise TasimaHatasi("aynı adlı arşiv var — ezilmez") from None


def _kimliksiz(bilgi: tarfile.TarInfo) -> tarfile.TarInfo:
    bilgi.uid = bilgi.gid = 0
    bilgi.uname = bilgi.gname = ""
    return bilgi


def paketle(kok, cikti_dizini, simdi=None, kuru=False, mac_denetimi=None) -> dict:
    kok, cikti_dizini = Path(kok), Path(cikti_dizini)
    if _ici_mi(cikti_dizini, kok):
        raise TasimaHatasi("çıktı dizini deponun içinde olamaz")
    simdi = simdi or _simdi()
    arsiv = cikti_dizini / f"nove-tasima-{simdi:%Y%m%d-%H%M}.tar.gz"
    sonuc = {"engeller": [], "ozet": {}, "toplam": 0, "arsiv": None, "sha256": None}

    def hazirla():
        liste = dosyalar(kok)
        sonuc["ozet"], sonuc["toplam"] = _ozet(liste), len(liste)
        return liste

    if kuru:
        sonuc["engeller"] = engeller(kok, mac_denetimi)
        hazirla()
        return sonuc
    with kos_kilidi(kok):
        sonuc["engeller"] = engeller(kok, mac_denetimi)
        if sonuc["engeller"]:
            return sonuc
        liste = hazirla()
        cikti_dizini.mkdir(parents=True, exist_ok=True)
        sha_yolu = arsiv.with_name(arsiv.name + ".sha256")
        if arsiv.exists() or sha_yolu.exists():
            raise TasimaHatasi("aynı adlı arşiv var — ezilmez")
        try:
            with _yeni_dosya(arsiv) as ham:
                with tarfile.open(fileobj=ham, mode="w:gz") as t:
                    for g in liste:
                        t.add(kok / g, arcname=g, recursive=False, filter=_kimliksiz)
            hesap = hashlib.sha256(arsiv.read_bytes()).hexdigest()
            with _yeni_dosya(sha_yolu) as f:
                f.write(f"{hesap}  {arsiv.name}\n".encode())
        except BaseException:
            arsiv.unlink(missing_ok=True)
            sha_yolu.unlink(missing_ok=True)
            raise
        sonuc["arsiv"], sonuc["sha256"] = arsiv, hesap
    return sonuc


def _yazdir(sonuc, kuru, simdi):
    print(f"taşıma paketi — {simdi:%Y-%m-%d %H:%M}")
    for e in sonuc["engeller"]:
        print(f"  ENGEL {e}")
    for ust, adet in sorted(sonuc["ozet"].items()):
        print(f"  {ust + '/':<16}{adet} dosya")
    if sonuc["arsiv"]:
        print(f"  → {sonuc['toplam']} dosya · arşiv: {sonuc['arsiv']} · sha256: {sonuc['sha256']}")
    elif not sonuc["engeller"] or kuru:
        print(f"  → {sonuc['toplam']} dosya" + (" · kuru: arşiv yazılmadı" if kuru else ""))
    print("  .env paketlenmedi (S-2): sunucuda yazılımcı yazar.")


def main(argv, kok=None, ortam=None) -> int:
    ortam = os.environ if ortam is None else ortam
    kok = Path(kok or KOK)
    argv = list(argv)
    paketle_mi = kuru = False
    cikti = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--paketle":
            paketle_mi = True
        elif a == "--kuru":
            kuru = True
        elif a == "--cikti" and i + 1 < len(argv):
            i += 1
            cikti = argv[i]
        else:
            print(f"kullanım hatası: {a if a in ('--ac',) else 'bilinmeyen ya da eksik bayrak'}", file=sys.stderr)
            return 2
        i += 1
    if not paketle_mi:
        print("kullanım: python3 bin/tasima.py --paketle [--cikti DIZIN] [--kuru]", file=sys.stderr)
        return 2
    if not kuru and ortam.get(AJAN_ISARETI):
        print("durdu — ajan ortamında taşıma kapalı; yalnız --kuru.")
        return 1
    simdi = _simdi()
    try:
        sonuc = paketle(kok, Path(cikti) if cikti else Path.home(), simdi=simdi, kuru=kuru)
    except TasimaHatasi as e:
        print(f"reddedildi: {e}")
        return 1
    except OSError as e:
        print(f"reddedildi: {type(e).__name__}")
        return 1
    _yazdir(sonuc, kuru, simdi)
    if kuru:
        return 0
    return 0 if sonuc["arsiv"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
