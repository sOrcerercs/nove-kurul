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

Bu dosyadaki kısım saftır: ağa çıkmaz, dosya yazmaz. Gönderim ve komut satırı sonraki görevlerde eklenir.

Kullanım (kilitler ve CLI eklenince):
    python3 bin/rapor_postasi.py --kuru     # ne gideceğini gösterir, göndermez
    python3 bin/rapor_postasi.py            # gönderir (yalnız insan)
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import soru_kaydi  # noqa: E402

KOK = ayar.KOK
RAPOR_ADLARI = {"kalite-gunluk": "Kalite günlük raporu"}
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
        metin = dosya.read_text(encoding="utf-8")
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
