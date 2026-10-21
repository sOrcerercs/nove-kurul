"""Tebrik tablosunu Google Drive'dan salt okunur indirir.

Kapsam yalnız `drive.readonly`. Hata mesajlarına dosya kimliği ve anahtar yolu yazılmaz.
Google kütüphaneleri yalnız gerçek servis kurulurken (fonksiyon içinde) import edilir.
"""
from __future__ import annotations

from pathlib import Path

KAPSAMLAR = ["https://www.googleapis.com/auth/drive.readonly"]
SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _servis_kur(anahtar_yolu, kapsamlar):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    kimlik = service_account.Credentials.from_service_account_file(
        str(anahtar_yolu), scopes=list(kapsamlar))
    return build("drive", "v3", credentials=kimlik, cache_discovery=False)


def tablo_indir(ortam: dict, hedef: Path, servis_kur=None) -> Path:
    """Tabloyu `hedef`e yazar ve yolunu döner. Hata: RuntimeError("Drive okunamadı: <tür>")."""
    for ad in ("TEBRIK_DRIVE_DOSYA", "TEBRIK_DRIVE_ANAHTAR"):
        if not (ortam.get(ad) or "").strip():
            raise RuntimeError(f"Drive okunamadı: {ad} tanımlı değil")
    dosya, anahtar = ortam["TEBRIK_DRIVE_DOSYA"].strip(), ortam["TEBRIK_DRIVE_ANAHTAR"].strip()
    hedef = Path(hedef)
    try:
        servis = (servis_kur or _servis_kur)(anahtar, list(KAPSAMLAR))
        mime = servis.files().get(fileId=dosya, fields="mimeType", supportsAllDrives=True).execute().get("mimeType")
        if mime == SHEETS_MIME:
            veri = servis.files().export_media(fileId=dosya, mimeType=XLSX_MIME, supportsAllDrives=True).execute()
        else:
            veri = servis.files().get_media(fileId=dosya, supportsAllDrives=True).execute()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici = hedef.with_name(hedef.name + ".tmp")
        gecici.write_bytes(veri)
        gecici.replace(hedef)
    except Exception as hata:
        durum = getattr(getattr(hata, "resp", None), "status", None)
        ek = f" {durum}" if durum else ""
        raise RuntimeError(f"Drive okunamadı: {type(hata).__name__}{ek}") from None
    return hedef
