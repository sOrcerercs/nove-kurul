#!/usr/bin/env python3
"""Panel kimliği: kullanıcı dosyası, şifre özeti, bellekte oturum, deneme freni. Yalnız stdlib.

Şifre ve belirteç hiçbir dosyaya ya da loga düz metin yazılmaz. Oturum bellekte tutulur.
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soru_kapisi  # noqa: E402

CEREZ_ADI = "nove_oturum"
OTURUM_SURESI_SN = 12 * 3600
DENEME_SINIRI = 5
DENEME_PENCERESI_SN = 15 * 60
PBKDF2_TUR = 600_000
SIFRE_EN_AZ = 8

_SCRYPT = dict(n=2 ** 14, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def _dosya(kok):
    return Path(kok) / "deploy" / "kullanicilar.json"


def kullanicilar(kok):
    """`deploy/kullanicilar.json`; yoksa ya da bozuksa boş."""
    try:
        ham = json.loads(_dosya(kok).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return ham if isinstance(ham, dict) else {}


def _yontemler():
    y = ["pbkdf2-sha256"]
    if hasattr(hashlib, "scrypt"):
        y.append("scrypt")
    return y


def _ozet(yontem, sifre, tuz):
    veri = sifre.encode("utf-8")
    if yontem == "scrypt":
        return hashlib.scrypt(veri, salt=tuz, **_SCRYPT)
    if yontem == "pbkdf2-sha256":
        return hashlib.pbkdf2_hmac("sha256", veri, tuz, PBKDF2_TUR)
    raise ValueError("bilinmeyen yöntem")


def _eposta(e):
    return str(e).strip().lower()


def kullanici_ekle(kok, eposta, ad, sifre):
    """Kullanıcıyı yazar; aynı e-posta varsa şifreyi yeniler."""
    if len(sifre) < SIFRE_EN_AZ:
        raise ValueError(f"şifre en az {SIFRE_EN_AZ} karakter olmalı")
    yontem = "scrypt" if hasattr(hashlib, "scrypt") else "pbkdf2-sha256"
    tuz = secrets.token_bytes(16)
    tum = kullanicilar(kok)
    tum[_eposta(eposta)] = {"ad": str(ad), "yontem": yontem, "tuz": tuz.hex(),
                            "ozet": _ozet(yontem, sifre, tuz).hex()}
    yol = _dosya(kok)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + f".{os.getpid()}.tmp")
    fd = os.open(str(gecici), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(tum, f, ensure_ascii=False, indent=2)
        os.chmod(gecici, 0o600)
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def dogrula(kok, eposta, sifre):
    """{"eposta", "ad", "rol"} ya da None (yok, yanlış şifre, rol dışı, yöntem yok)."""
    eposta = _eposta(eposta)
    kayit = kullanicilar(kok).get(eposta)
    if not isinstance(kayit, dict):
        _ozet(_yontemler()[-1], str(sifre), b"\0" * 16)  # süre farkı kullanıcı adını sızdırmasın
        return None
    try:
        beklenen = bytes.fromhex(kayit["ozet"])
        bulunan = _ozet(kayit["yontem"], str(sifre), bytes.fromhex(kayit["tuz"]))
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    if not hmac.compare_digest(beklenen, bulunan):
        return None
    rol = soru_kapisi.roller(kok).get(eposta)
    if rol not in soru_kapisi.SORABILEN_ROLLER:
        return None
    return {"eposta": eposta, "ad": str(kayit.get("ad", "")), "rol": rol}


def bas_harf(ad):
    """İlk iki kelimenin baş harfi: "Deneme Üye" -> "DÜ"."""
    return "".join(k[0].replace("i", "İ").upper() for k in str(ad).split()[:2])


class Oturumlar:
    def __init__(self, saat=time.time):
        self._saat = saat
        self._kilit = threading.Lock()
        self._oturumlar = {}

    def ac(self, eposta, ad):
        belirtec = secrets.token_urlsafe(32)
        with self._kilit:
            self._oturumlar[belirtec] = {"eposta": eposta, "ad": ad, "bitis": self._saat() + OTURUM_SURESI_SN}
        return belirtec

    def bul(self, belirtec):
        with self._kilit:
            o = self._oturumlar.get(belirtec)
            if o is None:
                return None
            if self._saat() > o["bitis"]:
                del self._oturumlar[belirtec]
                return None
            return {"eposta": o["eposta"], "ad": o["ad"]}

    def kapat(self, belirtec):
        with self._kilit:
            self._oturumlar.pop(belirtec, None)


class DenemeFreni:
    def __init__(self, saat=time.time):
        self._saat = saat
        self._kilit = threading.Lock()
        self._eposta = {}
        self._ip = {}

    def _taze(self, tablo, anahtar):
        sinir = self._saat() - DENEME_PENCERESI_SN
        liste = [t for t in tablo.get(anahtar, []) if t > sinir]
        if liste:
            tablo[anahtar] = liste
        else:
            tablo.pop(anahtar, None)
        return liste

    def engelli_mi(self, eposta, ip):
        eposta = _eposta(eposta)
        with self._kilit:
            return (len(self._taze(self._eposta, eposta)) >= DENEME_SINIRI
                    or len(self._taze(self._ip, ip)) >= DENEME_SINIRI)

    def basarisiz(self, eposta, ip):
        eposta, t = _eposta(eposta), self._saat()
        with self._kilit:
            self._taze(self._eposta, eposta)
            self._taze(self._ip, ip)
            self._eposta.setdefault(eposta, []).append(t)
            self._ip.setdefault(ip, []).append(t)

    def basarili(self, eposta):
        with self._kilit:
            self._eposta.pop(_eposta(eposta), None)
