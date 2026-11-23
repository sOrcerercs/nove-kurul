#!/usr/bin/env python3
"""Taşıma — Mac'teki çalışma durumunu tek arşivle sunucuya taşır (spec: sunucu teslimi, S-1/S-2).

S-1 sırası (Kağan, taşıma günü): 1) zamanlayıcıyı kaldır: `python3 bin/zamanla.py --kaldir`
2) panel/sahneyi durdur (8770) 3) açık soru kalmasın 4) paketle. Bu betik 1-3'ü denetler, sağlanmazsa paketlemez;
zorlama bayrağı yoktur. Paketleme boyunca koşu kilidi (`.kos.lock`) tutulur: arada koşu başlayamaz.

`.env` paketlenmez (S-2): sunucuda yazılımcı yazar. Hiçbir parçası `.env` ile başlayan yol paketlenmez ve açılmaz.
Çıktıya dosya adı ya da içerik yazılmaz; yalnız üst klasör başına adet.

Açma (sunucu, konteyner kullanıcısıyla; root reddedilir): önce sağlama toplamı ve arşivin bütün üyeleri denetlenir,
denetim bitmeden tek bayt yazılmaz. Hedefte aynı içerikli dosyaya dokunulmaz; farklı içerikli dosya varsa hiçbir şey
yazılmaz (`--ustune-yaz` ile eskisi `sirket-log/tasima-yedek/<zaman>/`'a kopyalanıp yazılır).

Kullanım:
    python3 bin/tasima.py --paketle [--cikti DIZIN] [--kuru]   # varsayılan çıktı: ev klasörü
    python3 bin/tasima.py --ac ARSIV [--ustune-yaz] [--kuru]   # ARSIV.sha256 yanında olmalı
    --kuru: denetler ve sayıları basar; arşiv/dosya yazmaz, kilit almaz.
Çıkış: 0 tamam · 1 reddedildi · 2 kullanım hatası. Ajan ortamında (CLAUDECODE) yalnız --kuru çalışır.
"""
from __future__ import annotations

import fcntl
import fnmatch
import gzip
import hashlib
import io
import os
import socket
import stat
import sys
import tarfile
import tempfile
import zlib
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
# Bunların altı taşınır; TASINANLAR'daki öteki girdiler dosyadır ve yalnız birebir eşleşir.
DIZIN_KURALLARI = ("yanitlar", "sirket-log", "formlar/onayli", "takimlar/*/kosu", "takimlar/*/cikti")
ATLANAN_ADLAR = (".DS_Store", ".kilit", "__pycache__")


class TasimaHatasi(Exception):
    """İletisi dosya içeriği ya da adı taşımaz."""


def izinli_mi(goreli: str) -> bool:
    """Paketleme ve açma aynı kuralı kullanır."""
    if not goreli or goreli.startswith("/") or "\\" in goreli or "\0" in goreli:
        return False
    parcalar = goreli.split("/")
    if any(p in ("", ".", "..") or p.lower().startswith(".env") for p in parcalar):
        return False
    if parcalar[-1] in ATLANAN_ADLAR:
        return False
    if parcalar[0] == "takimlar" and len(parcalar) > 1 and parcalar[1].startswith("_"):
        return False
    for kural in TASINANLAR:
        kp = kural.split("/")
        uygun_boy = len(parcalar) > len(kp) if kural in DIZIN_KURALLARI else len(parcalar) == len(kp)
        if uygun_boy and all(fnmatch.fnmatchcase(p, k) for p, k in zip(parcalar, kp)):
            return True
    return False


def dosyalar(kok) -> list:
    """İzinli düzenli dosyalar, sıralı; sembolik bağ, sabit bağ, kök dışı ve özel dosya atlanır."""
    return _tara(kok)[0]


def _tara(kok):
    """(izinli dosyalar, atlanan adet). İzinli yoldaki bir dosya şunlarda atlanır: sembolik bağ, düzenli dosya değil,
    gerçek yolu kökün dışında (sembolik üst klasör), birden çok sabit bağı var (`.env` başka adla taşınamasın)."""
    kok = Path(kok)
    gercek_kok = kok.resolve()
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
    gecenler, atlanan = [], 0
    for yol in sonuc:
        goreli = yol.relative_to(kok).as_posix()
        if not izinli_mi(goreli):
            continue
        if _guvenli_dosya_mi(yol, gercek_kok):
            gecenler.append(goreli)
        else:
            atlanan += 1
    return sorted(gecenler), atlanan


def _guvenli_dosya_mi(yol: Path, gercek_kok: Path) -> bool:
    try:
        bilgi = os.lstat(yol)
        yol.resolve().relative_to(gercek_kok)
    except (OSError, ValueError):
        return False
    return stat.S_ISREG(bilgi.st_mode) and bilgi.st_nlink == 1


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
    isler = zamanla.durum(kok)
    if any(is_["yuklu"] for is_ in isler):
        nedenler.append("zamanlayıcı kurulu — önce: python3 bin/zamanla.py --kaldir")
    eskiler = [is_.get("eski_etiket", "?") for is_ in isler if is_.get("eski_yuklu")]
    if eskiler:
        nedenler.append(f"zamanlayıcı kurulu (eski etiket: {', '.join(eskiler)}) — önce her biri için: "
                        "launchctl bootout gui/$(id -u)/<etiket>")
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
    sonuc = {"engeller": [], "ozet": {}, "toplam": 0, "atlanan": 0, "arsiv": None, "sha256": None}

    def hazirla():
        liste, sonuc["atlanan"] = _tara(kok)
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
        olusan = []   # temizlik yalnız bu koşunun yarattığını siler; yarışan başka arşive dokunmaz
        try:
            ham = _yeni_dosya(arsiv)
            olusan.append(arsiv)
            with ham:
                with tarfile.open(fileobj=ham, mode="w:gz") as t:
                    for g in liste:
                        t.add(kok / g, arcname=g, recursive=False, filter=_kimliksiz)
            hesap = hashlib.sha256(arsiv.read_bytes()).hexdigest()
            f = _yeni_dosya(sha_yolu)
            olusan.append(sha_yolu)
            with f:
                f.write(f"{hesap}  {arsiv.name}\n".encode())
        except BaseException:
            for yol in olusan:
                yol.unlink(missing_ok=True)
            raise
        sonuc["arsiv"], sonuc["sha256"] = arsiv, hesap
    return sonuc


def _euid():
    return os.geteuid()


IZIN_YOK = ("okuma izni yok — arşivi ve .sha256'yı konteyner kullanıcısının okuyabileceği hâle getirin "
            "(sahibi 3. bölümdeki kullanıcı olsun)")


def _ust(goreli: str) -> str:
    """Hata iletisi için yalnız üst klasör; dosya adı basılmaz."""
    parca = goreli.split("/")
    return parca[0] + "/" if len(parca) > 1 and parca[0] else "(kök)"


def _yol_hatasi(nerede: str, kotuler) -> TasimaHatasi:
    ustler = sorted({_ust(g) for g in kotuler})
    return TasimaHatasi(f"{nerede} beklenmeyen yol: {len(kotuler)} üye ({', '.join(ustler)})")


def _arsiv_oku(arsiv: Path) -> bytes:
    """Arşivin baytları — yalnız yanındaki .sha256 ile tutarsa. Tek okuma: denetlenen bayt açılan bayttır."""
    sha_yolu = arsiv.with_name(arsiv.name + ".sha256")
    try:
        beklenen = sha_yolu.read_text(encoding="ascii").split()[0].lower()
    except PermissionError:
        raise TasimaHatasi(IZIN_YOK) from None
    except (OSError, UnicodeDecodeError, IndexError):
        raise TasimaHatasi("sağlama toplamı okunamadı — ARSIV.sha256 arşivin yanında olmalı") from None
    try:
        veri = arsiv.read_bytes()
    except PermissionError:
        raise TasimaHatasi(IZIN_YOK) from None
    if hashlib.sha256(veri).hexdigest() != beklenen:
        raise TasimaHatasi("sağlama toplamı tutmuyor — arşiv bozuk ya da değişmiş")
    return veri


def _uyeleri_oku(veri: bytes) -> dict:
    """{goreli: içerik}. Tek bir izinsiz üye bütün arşivi reddeder; extractall kullanılmaz."""
    icerik, gorulen, kotuler = {}, set(), []
    try:   # gzip önce bütünüyle açılır: CRC ve uzunluk denetlenir, kesik ya da bozuk akış sessizce geçmez
        with tarfile.open(fileobj=io.BytesIO(gzip.decompress(veri)), mode="r:") as t:
            for m in t.getmembers():
                if not (m.isreg() or m.isdir()) or not izinli_mi(m.name) or m.name in gorulen:
                    kotuler.append(m.name)
                    continue
                gorulen.add(m.name)
                if m.isreg():
                    icerik[m.name] = t.extractfile(m).read()
    except (tarfile.TarError, EOFError, zlib.error, OSError):   # OSError: gzip.BadGzipFile
        raise TasimaHatasi("arşiv okunamadı") from None
    for g in icerik:   # bir dosya başka bir dosyanın üst klasörü olamaz
        parca = g.split("/")
        if any("/".join(parca[:i]) in icerik for i in range(1, len(parca))):
            kotuler.append(g)
    if kotuler:
        raise _yol_hatasi("arşivde", kotuler)
    return icerik


def _hedef_yolu(kok: Path, goreli: str) -> Path:
    """Hedefte her mevcut üst parça gerçek dizin, yolun kendisi yok ya da düzenli dosya olmalı (sembolik bağ değil)."""
    yol, parca = kok, goreli.split("/")
    for i, p in enumerate(parca):
        yol = yol / p
        son = i == len(parca) - 1
        if yol.is_symlink() or (yol.exists() and not (yol.is_file() if son else yol.is_dir())):
            raise _yol_hatasi("hedefte", [goreli])
    return yol


def _dosya_yaz(kok: Path, goreli: str, icerik: bytes):
    """Eksik dizinler 0o700, dosya 0o600; geçici dosya + os.replace (yarım dosya kalmaz)."""
    yol = kok
    for p in goreli.split("/")[:-1]:
        yol = yol / p
        if not yol.exists():
            os.mkdir(yol, 0o700)
            os.chmod(yol, 0o700)
    hedef = kok / goreli
    fd, gecici = tempfile.mkstemp(dir=hedef.parent, prefix=".tasima-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(icerik)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(gecici, 0o600)
        os.replace(gecici, hedef)
    except BaseException:
        Path(gecici).unlink(missing_ok=True)
        raise


def ac(kok, arsiv, ustune_yaz=False, kuru=False, simdi=None, euid=None, mac_denetimi=None) -> dict:
    kok, arsiv = Path(kok), Path(arsiv)
    veri = _arsiv_oku(arsiv)                                        # 1 sağlama toplamı
    if (_euid() if euid is None else euid) == 0:                    # 2 root değil
        raise TasimaHatasi("root olarak açılmaz — konteyner kullanıcısıyla koştur")
    sonuc = {"engeller": [], "toplam": 0, "yazilacak": 0, "yazilan": 0, "ayni": 0, "catisan": [],
             "catisan_ozet": {}, "yedek": None}

    def sinifla():                                                  # 4 üyeler · 5 sınıflama
        icerik = _uyeleri_oku(veri)
        yeni, catisan, eski = [], [], {}
        for g in sorted(icerik):
            yol = _hedef_yolu(kok, g)
            if not yol.exists():
                yeni.append(g)
                continue
            eski[g] = yol.read_bytes()
            if eski[g] == icerik[g]:
                sonuc["ayni"] += 1
            else:
                catisan.append(g)
        sonuc["toplam"], sonuc["catisan"], sonuc["catisan_ozet"] = len(icerik), catisan, _ozet(catisan)
        sonuc["yazilacak"] = len(yeni) + (len(catisan) if ustune_yaz else 0)
        return icerik, yeni, catisan, eski

    if kuru:
        sinifla()
        return sonuc
    with kos_kilidi(kok):                                           # 3 engel ve kilit
        sonuc["engeller"] = engeller(kok, mac_denetimi)
        if sonuc["engeller"]:
            return sonuc
        icerik, yeni, catisan, eski = sinifla()
        if catisan and not ustune_yaz:                              # 6 sessiz ezme yok
            return sonuc
        yedekler = []
        if catisan:                                                 # 7 önce yedek (yollar yazmadan denetlenir)
            yedek_goreli = f"sirket-log/tasima-yedek/{(simdi or _simdi()):%Y%m%d-%H%M%S}"
            if _hedef_yolu(kok, yedek_goreli).exists():
                raise TasimaHatasi("yedek klasörü zaten var — bir dakika sonra yeniden dene")
            yedekler = [(f"{yedek_goreli}/{g}", eski[g]) for g in catisan]
            for y, _ in yedekler:
                _hedef_yolu(kok, y)
            sonuc["yedek"] = kok / yedek_goreli
        for y, b in yedekler:
            _dosya_yaz(kok, y, b)
        for g in yeni + catisan:                                    # 8 yazım
            _dosya_yaz(kok, g, icerik[g])
            sonuc["yazilan"] += 1
    return sonuc


def _yazdir_ac(sonuc, kuru, ustune_yaz, simdi):
    print(f"taşıma açma — {simdi:%Y-%m-%d %H:%M}")
    for e in sonuc["engeller"]:
        print(f"  ENGEL {e}")
    if sonuc["engeller"] and not kuru:
        return
    print(f"  → {sonuc['toplam']} dosya · {sonuc['yazilacak']} yazılacak · {sonuc['ayni']} aynı (dokunulmadı) · "
          f"{len(sonuc['catisan'])} farklı" + (" · kuru: yazılmadı" if kuru else ""))
    for ust, adet in sorted(sonuc["catisan_ozet"].items()):
        print(f"  ÇATIŞMA {ust + '/':<16}{adet} dosya")
    if sonuc["catisan"] and not ustune_yaz:
        print("  farklı içerikli dosyalar ezilmedi" + ("" if kuru else ", hiçbir dosya yazılmadı") +
              " — Mac'teki hâli yazmak için: --ustune-yaz (eskiler sirket-log/tasima-yedek/'e kopyalanır)")
    if sonuc["yedek"]:
        print(f"  yedek: {sonuc['yedek']}")
    if not kuru:
        print(f"  {sonuc['yazilan']} dosya yazıldı.")
    print("  .env açılmadı (S-2): sunucuda yazılımcı yazar.")


def _yazdir(sonuc, kuru, simdi):
    print(f"taşıma paketi — {simdi:%Y-%m-%d %H:%M}")
    for e in sonuc["engeller"]:
        print(f"  ENGEL {e}")
    for ust, adet in sorted(sonuc["ozet"].items()):
        print(f"  {ust + '/':<16}{adet} dosya")
    if sonuc.get("atlanan"):
        print(f"  {sonuc['atlanan']} dosya atlandı (sembolik bağ, sabit bağ ya da depo dışını gösteren yol)")
    if sonuc["arsiv"]:
        print(f"  → {sonuc['toplam']} dosya · arşiv: {sonuc['arsiv']} · sha256: {sonuc['sha256']}")
    elif not sonuc["engeller"] or kuru:
        print(f"  → {sonuc['toplam']} dosya" + (" · kuru: arşiv yazılmadı" if kuru else ""))
    print("  .env paketlenmedi (S-2): sunucuda yazılımcı yazar.")


def main(argv, kok=None, ortam=None) -> int:
    ortam = os.environ if ortam is None else ortam
    kok = Path(kok or KOK)
    argv = list(argv)
    paketle_mi = kuru = ustune_yaz = False
    cikti = arsiv = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--paketle":
            paketle_mi = True
        elif a == "--kuru":
            kuru = True
        elif a == "--ustune-yaz":
            ustune_yaz = True
        elif a == "--cikti" and i + 1 < len(argv):
            i += 1
            cikti = argv[i]
        elif a == "--ac" and i + 1 < len(argv):
            i += 1
            arsiv = argv[i]
        else:
            print("kullanım hatası: bilinmeyen ya da eksik bayrak", file=sys.stderr)
            return 2
        i += 1
    ac_mi = arsiv is not None
    if paketle_mi == ac_mi or (paketle_mi and ustune_yaz) or (ac_mi and cikti is not None):
        print("kullanım: python3 bin/tasima.py --paketle [--cikti DIZIN] [--kuru]\n"
              "          python3 bin/tasima.py --ac ARSIV [--ustune-yaz] [--kuru]", file=sys.stderr)
        return 2
    if not kuru and ortam.get(AJAN_ISARETI):
        print("durdu — ajan ortamında taşıma kapalı; yalnız --kuru.")
        return 1
    simdi = _simdi()
    try:
        if ac_mi:
            sonuc = ac(kok, Path(arsiv), ustune_yaz=ustune_yaz, kuru=kuru, simdi=simdi)
        else:
            sonuc = paketle(kok, Path(cikti) if cikti else Path.home(), simdi=simdi, kuru=kuru)
    except TasimaHatasi as e:
        print(f"reddedildi: {e}")
        return 1
    except OSError as e:
        print(f"reddedildi: {type(e).__name__}")
        return 1
    if ac_mi:
        _yazdir_ac(sonuc, kuru, ustune_yaz, simdi)
        if kuru:
            return 0
        return 1 if sonuc["engeller"] or (sonuc["catisan"] and not ustune_yaz) else 0
    _yazdir(sonuc, kuru, simdi)
    if kuru:
        return 0
    return 0 if sonuc["arsiv"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
