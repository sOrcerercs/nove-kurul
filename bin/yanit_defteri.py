#!/usr/bin/env python3
"""Yanıt defteri — kurul sorularının onaylı (ya da onaylanamamış) yanıtları (NOVE-KURULUM.md §8b, N8).

`yanitlar/<soru-id>.md`, soru başına bir kayıt. **Yalnız sürücü yazar** (`soru_kapisi.py --ilet`);
kayıt silinmez, değiştirilmez: aynı soru için ikinci yazım reddedilir. Ajanlara `.claude/settings.json`
deny listesiyle kapalıdır.

Kurul üyesi panelde yalnız kendi sorularını görür (N10); süzme `panel.py`'nin işidir (Faz 5).
"""
from pathlib import Path

import ayar


def yol(soru_id, kok=None):
    return Path(kok or ayar.KOK) / "yanitlar" / f"{soru_id}.md"


def yaz(kok, soru_id, metin):
    """Yeni kayıt yazar. Kayıt zaten varsa FileExistsError — defter değiştirilmez."""
    hedef = yol(soru_id, kok)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with open(hedef, "x", encoding="utf-8") as dosya:   # "x": varsa yazmaz
        dosya.write(metin)
    return hedef
