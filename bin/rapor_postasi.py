#!/usr/bin/env python3
"""Rapor postası — onaylı zamanlı raporların YALNIZ haberini yöneticilere postalar (spec: rapor postası betiği).

Ne yapar: Yanıt defterinde (`yanitlar/`) `onaylı` etiketli, kurula görünür, id'si `rapor-<danışman>-<GGAAYYYY>`
kalıbındaki kayıtları aday sayar; her biri için bir haber maili hazırlar (konu: rapor adı + tarih; gövde: tek cümle
+ panel bağlantısı). Mailde yalnız haber vardır — soru, Kurula not ve yanıt metni hiçbir yere girmez, ek ve HTML yok
(ANAYASA §1 istisnası — "İstisna — rapor postası"; ayrıntı spec'te).

Üç kilit (biri tutmazsa gönderim yok, kayıt yazılmaz, nedeni söylenir):
  1. `ANAYASA.md`'de `İstisna — rapor postası` metni var
  2. `.env`'de POSTA_SMTP_SUNUCU, POSTA_SMTP_PORT, POSTA_KULLANICI, POSTA_SIFRE, POSTA_GONDEREN, PANEL_ADRES var
  3. `CLAUDECODE` ortamında değil (ajan göndermez; yalnız `--kuru`)

Adres hiçbir çıktıya, kayda ya da hata iletisine yazılmaz; kayıtta yalnız alıcı sayısı ve istisna sınıf adı kalır.
Komut satırı sonraki görevde eklenir.

Kullanım (kilitler ve CLI eklenince):
    python3 bin/rapor_postasi.py --kuru     # ne gideceğini gösterir, göndermez
    python3 bin/rapor_postasi.py            # gönderir (yalnız insan)
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import smtplib
import sys
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import soru_kaydi  # noqa: E402

KOK = ayar.KOK
ISTISNA_ISARETI = "İstisna — rapor postası"
AJAN_ISARETI = "CLAUDECODE"
GEREKLI_ANAHTARLAR = ("POSTA_SMTP_SUNUCU", "POSTA_SMTP_PORT", "POSTA_KULLANICI", "POSTA_SIFRE",
                      "POSTA_GONDEREN", "PANEL_ADRES")
ISTANBUL = timezone(timedelta(hours=3))  # Türkiye'de yaz saati yok
RAPOR_ADLARI = {"kalite-gunluk": "Kalite günlük raporu"}
_ADRES = re.compile(r"[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]{2,}")
_RAPOR_ID = re.compile(r"^rapor-([a-z0-9-]+)-(\d{8})$")


def tur_ve_tarih(soru_id: str):
    """`rapor-kalite-20261123` → ("kalite-gunluk", date(2026, 11, 23)); kalıba uymayan ya da geçersiz tarih → None."""
    e = _RAPOR_ID.match(soru_id)
    if not e:
        return None
    s = e.group(2)
    try:
        tarih = date(int(s[:4]), int(s[4:6]), int(s[6:]))
    except ValueError:
        return None
    return f"{e.group(1)}-gunluk", tarih


def adaylar(kok=None) -> list:
    """Haberi gidebilecek kayıtlar: `gorunurluk` taşıyan, `etiket: onaylı`, id'si rapor kalıbında. Id sırasıyla."""
    klasor = Path(kok or KOK) / "yanitlar"
    if not klasor.is_dir():
        return []
    sonuc = []
    for dosya in sorted(klasor.glob("*.md")):
        tt = tur_ve_tarih(dosya.stem)
        if tt is None:
            continue
        try:
            metin = dosya.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # okunamayan kayıt tüm koşuyu düşürmez
        if soru_kaydi.alan(metin, "gorunurluk") is None or soru_kaydi.alan(metin, "etiket") != "onaylı":
            continue
        sonuc.append({"id": dosya.stem, "tur": tt[0], "tarih": tt[1]})
    return sonuc


def sablon(tur: str, tarih: date, soru_id: str, panel_adres: str):
    """(konu, gövde). Defter metnini almaz — yalnız rapor adı, tarih ve bağlantı. `tur` bilinmiyorsa KeyError."""
    ad = RAPOR_ADLARI[tur]
    gun = f"{tarih:%d.%m.%Y}"
    baglanti = f"{panel_adres.rstrip('/')}/?soru={soru_id}"
    return (f"{ad} hazır — {gun}",
            f"{ad} ({gun}) panelde hazır; okumak için giriş yapın:\n{baglanti}\n")


class PostaHatasi(Exception):
    """İletisi adres taşımaz."""


def kilitler(kok, ortam: dict) -> list:
    """Tutmayan kilitlerin nedenleri (boş liste = üçü de tutuyor). Nedenler yalnız anahtar adı yazar, değer yazmaz."""
    nedenler = []
    try:
        anayasa = (Path(kok) / "ANAYASA.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        anayasa = ""
    if ISTISNA_ISARETI not in anayasa:
        nedenler.append(f"ANAYASA.md'de '{ISTISNA_ISARETI}' metni yok")
    eksik = [a for a in GEREKLI_ANAHTARLAR if not str(ortam.get(a, "")).strip()]
    if eksik:
        nedenler.append(".env'de eksik anahtar: " + ", ".join(eksik))
    else:
        bozuk = []
        if not str(ortam["POSTA_SMTP_PORT"]).strip().isdigit():
            bozuk.append("POSTA_SMTP_PORT")
        if not str(ortam["PANEL_ADRES"]).strip().startswith(("http://", "https://")):
            bozuk.append("PANEL_ADRES")
        if bozuk:
            nedenler.append(".env'de biçimi bozuk anahtar: " + ", ".join(bozuk))
    if ortam.get(AJAN_ISARETI):
        nedenler.append("ajan ortamında (CLAUDECODE) gönderim yok; yalnız --kuru")
    return nedenler


def alicilari_oku(kok) -> dict:
    """`deploy/posta-alicilari.json` → {tür: [adres]}. Dosya yoksa {}. Tek kusur bütün dosyayı reddeder."""
    yol = Path(kok) / "deploy" / "posta-alicilari.json"
    if not yol.exists():
        return {}
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PostaHatasi("alıcı dosyası bozuk: kök") from None
    if not isinstance(veri, dict):
        raise PostaHatasi("alıcı dosyası bozuk: kök")
    sonek = "@" + ayar.POSTA_IZINLI_ALAN.lower()
    sonuc = {}
    for tur, liste in veri.items():
        if not isinstance(liste, list):
            raise PostaHatasi(f"alıcı dosyası bozuk: {tur}")
        temiz = []
        for adres in liste:
            if not isinstance(adres, str):
                raise PostaHatasi(f"alıcı dosyası bozuk: {tur}")
            a = adres.strip().lower()
            if not _ADRES.fullmatch(a) or not a.endswith(sonek):
                raise PostaHatasi(f"alıcı dosyası bozuk: {tur}")
            if a not in temiz:
                temiz.append(a)
        sonuc[tur] = temiz
    return sonuc


def kayit_yolu(kok, soru_id: str) -> Path:
    return Path(kok) / "sirket-log" / "posta" / f"{soru_id}.json"


def kayit_oku(kok, soru_id: str):
    """Gönderim kaydı; yoksa ya da bozuksa None."""
    try:
        veri = json.loads(kayit_yolu(kok, soru_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return veri if isinstance(veri, dict) else None


def _kayit_yaz(kok, kayit: dict) -> None:
    yol = kayit_yolu(kok, kayit["id"])
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(kayit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(gecici, yol)


def _bugun_gonderilen(kok, bugun: date) -> int:
    klasor = Path(kok) / "sirket-log" / "posta"
    if not klasor.is_dir():
        return 0
    sayi = 0
    for yol in klasor.glob("*.json"):
        k = kayit_oku(kok, yol.stem)
        if not k or k.get("durum") != "gonderildi":
            continue
        try:
            if datetime.fromisoformat(k["zaman"]).astimezone(ISTANBUL).date() == bugun:
                sayi += 1
        except (KeyError, ValueError, TypeError):
            continue
    return sayi


def _baglan(ortam: dict):
    sunucu, port = ortam["POSTA_SMTP_SUNUCU"], int(ortam["POSTA_SMTP_PORT"])
    zaman_asimi = ayar.POSTA_SMTP_ZAMAN_ASIMI_SN
    if port == 465:
        smtp = smtplib.SMTP_SSL(sunucu, port, timeout=zaman_asimi)
    else:
        smtp = smtplib.SMTP(sunucu, port, timeout=zaman_asimi)
        smtp.starttls()
    smtp.login(ortam["POSTA_KULLANICI"], ortam["POSTA_SIFRE"])
    return smtp


def _mesaj(ortam: dict, konu: str, govde: str) -> EmailMessage:
    """Alıcılar yalnız zarfta: başlıkta To = gönderen, Bcc/Cc yok; alıcılar birbirini görmez."""
    msg = EmailMessage()
    msg["From"] = ortam["POSTA_GONDEREN"]
    msg["To"] = ortam["POSTA_GONDEREN"]
    msg["Subject"] = konu
    msg.set_content(govde)
    return msg


def calistir(kok=None, simdi=None, kuru=False, ortam=None) -> dict:
    """Adayları sırayla işler; ayrıntı için dosya başındaki açıklama ve spec."""
    kok = Path(kok or KOK)
    simdi = (simdi or datetime.now(ISTANBUL)).astimezone(ISTANBUL)
    bugun = simdi.date()
    if ortam is None:
        ortam = {**os.environ, **ayar.env_yukle(kok / ".env")}
    tavan = ayar.POSTA_GUNLUK_TAVAN
    nedenler = kilitler(kok, ortam)
    alicilar, alici_bozuk = {}, False
    try:
        alicilar = alicilari_oku(kok)
    except PostaHatasi as e:
        alici_bozuk = True
        nedenler.append(str(e))
    engel = alici_bozuk or (bool(nedenler) and not kuru)

    kilit_dosyasi = None
    if not kuru and not nedenler:
        (kok / "sirket-log" / "posta").mkdir(parents=True, exist_ok=True)
        kilit_dosyasi = open(kok / "sirket-log" / "posta" / ".kilit", "w")
        try:
            fcntl.flock(kilit_dosyasi, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            kilit_dosyasi.close()
            return {"kilitler": ["başka bir gönderim sürüyor"], "sonuclar": [], "bugun": 0, "tavan": tavan}
    try:
        return _isle(kok, simdi, bugun, kuru, ortam, alicilar, engel, nedenler, tavan)
    finally:
        if kilit_dosyasi is not None:
            kilit_dosyasi.close()


def _isle(kok, simdi, bugun, kuru, ortam, alicilar, engel, nedenler, tavan) -> dict:
    sonuclar = []
    sayi = _bugun_gonderilen(kok, bugun)
    smtp = None
    bitti = False

    def ekle(a, sonuc, alici_sayisi=0, konu=None):
        sonuclar.append({"id": a["id"], "tur": a["tur"], "sonuc": sonuc, "alici_sayisi": alici_sayisi, "konu": konu})

    def yaz(a, durum, alici_sayisi, deneme, hata=None):
        kayit = {"id": a["id"], "tur": a["tur"], "durum": durum, "zaman": simdi.isoformat(timespec="seconds"),
                 "alici_sayisi": alici_sayisi, "deneme": deneme}
        if hata:
            kayit["hata"] = hata
        _kayit_yaz(kok, kayit)

    try:
        for a in adaylar(kok):
            onceki = kayit_oku(kok, a["id"]) or {}
            if onceki.get("durum") == "gonderildi":
                continue
            if bitti:
                break
            if a["tarih"] < bugun - timedelta(days=ayar.POSTA_EN_FAZLA_GUN):
                ekle(a, "eski")
                continue
            if a["tur"] not in RAPOR_ADLARI:
                ekle(a, "ad-yok")
                continue
            if engel:
                ekle(a, "kilitli")
                continue
            liste = alicilar.get(a["tur"]) or []
            if not liste:
                if not kuru:
                    yaz(a, "alici-yok", 0, onceki.get("deneme", 0))
                ekle(a, "alici-yok")
                continue
            if sayi >= tavan:
                ekle(a, "tavan", len(liste))
                continue
            konu, govde = sablon(a["tur"], a["tarih"], a["id"], ortam["PANEL_ADRES"])
            deneme = onceki.get("deneme", 0)
            if kuru:
                sayi += 1
                ekle(a, "gonderilecek", len(liste), konu)
                continue
            try:
                if smtp is None:
                    smtp = _baglan(ortam)
            except Exception as e:  # bağlantı/giriş: döngü biter
                yaz(a, "hata", len(liste), deneme + 1, type(e).__name__)
                ekle(a, "hata", len(liste), konu)
                bitti = True
                continue
            try:
                smtp.send_message(_mesaj(ortam, konu, govde), to_addrs=liste)
            except Exception as e:  # tek mail: sıradakine geç
                yaz(a, "hata", len(liste), deneme + 1, type(e).__name__)
                ekle(a, "hata", len(liste), konu)
                continue
            yaz(a, "gonderildi", len(liste), deneme)
            sayi += 1
            ekle(a, "gonderildi", len(liste), konu)
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass
    return {"kilitler": nedenler, "sonuclar": sonuclar, "bugun": sayi, "tavan": tavan}
