"""Tebrik Danışmanı — posta: alıcı kapısı, ANAYASA istisnası, mail kurma, SMTP.

Tek iç alıcıya, günde tek mail. Adres ve şifre hiçbir hata mesajına yazılmaz.
"""
from __future__ import annotations

import re
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from pathlib import Path

ALAN_ADI = "nove.group"
ISTISNA_BASLIGI = "İstisna — tebrik postası"

DOGUM_TR = "Yeni yaşınızda, tüm hayallerinizin gerçeğe dönüşmesini dileriz."
DOGUM_EN = "In your new age, we wish all your dreams come true."
HOS_GELDIN_EN = "Welcome to the Team!"

_ADRES = re.compile(r"^[^@\s,;<>]+@" + re.escape(ALAN_ADI) + r"$", re.IGNORECASE)
_ASCII = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "İ": "i", "ö": "o", "ş": "s", "ü": "u",
                        "Ç": "c", "Ğ": "g", "I": "i", "Ö": "o", "Ş": "s", "Ü": "u"})
_TUR_ADI = {"dogum_gunu": "Doğum günü", "hos_geldin": "Hoş geldin", "bayram": "Bayram"}


def alici_dogrula(adres: str) -> str:
    """Tek, `@nove.group` adresi ise kırpılmış halini verir; değilse ValueError (adres mesajda yok)."""
    temiz = (adres or "").strip()
    if not _ADRES.match(temiz):
        raise ValueError("alıcı geçersiz: tek bir şirket adresi olmalı")
    return temiz


def istisna_var(anayasa_metni: str) -> bool:
    """ANAYASA metninde istisna başlığı (tam başlık satırı) var mı."""
    kalip = re.compile(r"^\s{0,3}#{1,6}\s*" + re.escape(ISTISNA_BASLIGI) + r"\s*#*\s*$", re.MULTILINE)
    return bool(kalip.search(anayasa_metni or ""))


def _slug(metin: str) -> str:
    s = (metin or "").translate(_ASCII).lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s)).strip("-")


def ek_adi(gun: date, tebrik: dict) -> str:
    """Ek dosya adı: ASCII, küçük harf, tire ayraçlı."""
    if tebrik["tur"] == "bayram":
        son = "bayram-" + _slug(tebrik["bayram"]["ad"])
    else:
        son = _slug(tebrik["tur"].replace("_", "-")) + "-" + _slug(tebrik["ad"])
    return f"{gun.isoformat()}-{son}.png"


def _metinler(t: dict) -> tuple[str, str]:
    if t["tur"] == "dogum_gunu":
        return DOGUM_TR, DOGUM_EN
    if t["tur"] == "hos_geldin":
        return "", HOS_GELDIN_EN
    return t["bayram"]["tr"], t["bayram"]["en"]


def mail_kur(tebrikler: list, gorseller: list, notlar: list, gonderen: str, alici: str,
             gun: date) -> EmailMessage:
    tarih = gun.strftime("%d.%m.%Y")
    m = EmailMessage()
    m["Subject"] = (f"Tebrikler — {tarih}" if tebrikler else f"Tebrik tablosu — {tarih}")
    m["From"] = gonderen
    m["To"] = alici
    satirlar = []
    for t in tebrikler:
        tr, en = _metinler(t)
        baslik = _TUR_ADI[t["tur"]] + (f" — {t['ad']}" if t["ad"] else f" — {t['bayram']['ad']}")
        if t.get("unvan"):
            baslik += f" ({t['unvan']})"
        satirlar.append(baslik)
        if tr:
            satirlar.append(f"TR: {tr}")
        satirlar.append(f"EN: {en}")
        satirlar.append("")
    if notlar:
        satirlar.append("Notlar:")
        satirlar.extend(f"- {n}" for n in notlar)
    m.set_content("\n".join(satirlar).rstrip() + "\n")
    for yol in gorseller:
        yol = Path(yol)
        m.add_attachment(yol.read_bytes(), maintype="image", subtype="png", filename=yol.name)
    return m


def gonder(mesaj: EmailMessage, ortam: dict, smtp_kur=smtplib.SMTP) -> None:
    """Tek alıcıya yollar. Alıcıyı burada da doğrular; hata → RuntimeError("SMTP: <tür>")."""
    alici = alici_dogrula(ortam.get("TEBRIK_ALICI", ""))
    try:
        sunucu, port = ortam["TEBRIK_SMTP_SUNUCU"], int(ortam["TEBRIK_SMTP_PORT"])
        baglam = ssl.create_default_context()
        if port == 465:
            baglan = (smtp_kur if smtp_kur is not smtplib.SMTP else smtplib.SMTP_SSL)
            kur = lambda: baglan(sunucu, port, context=baglam, timeout=30)  # noqa: E731
        else:
            kur = lambda: smtp_kur(sunucu, port, timeout=30)  # noqa: E731
        with kur() as s:
            if port != 465:
                s.starttls(context=baglam)
            s.login(ortam["TEBRIK_SMTP_KULLANICI"], ortam["TEBRIK_SMTP_SIFRE"])
            s.send_message(mesaj, to_addrs=[alici])
    except Exception as hata:
        raise RuntimeError(f"SMTP: {type(hata).__name__}") from None
