#!/usr/bin/env python3
"""Kalite günlük raporunun takvimi — iş günü, rapor aralığı, tatil listesi (spec: kalite-gunluk-rapor).

Saf tarih hesabı; dosya yalnız `takimlar/kalite/tatiller.json` (`[{"tarih": "YYYY-MM-DD", "ad": "..."}]`).
İş günü: pazartesi–cuma ve tatil listesinde olmayan gün.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


def is_gunu_mu(gun, tatiller):
    return gun.weekday() < 5 and gun not in tatiller


def _onceki_is_gunu(gun, tatiller):
    gun -= timedelta(days=1)
    while not is_gunu_mu(gun, tatiller):
        gun -= timedelta(days=1)
    return gun


def rapor_araligi(gun, tatiller):
    """((aralık başı, sonu), (karşılaştırma başı, sonu)); `gun` iş günü değilse None.

    Aralık: bir önceki iş gününden (dahil) dünkü güne. Tek günse karşılaştırma bir önceki iş günü,
    çok günse aynı aralık 7 gün geri."""
    if not is_gunu_mu(gun, tatiller):
        return None
    bas = _onceki_is_gunu(gun, tatiller)
    son = gun - timedelta(days=1)
    if bas == son:
        onceki = _onceki_is_gunu(bas, tatiller)
        return (bas, son), (onceki, onceki)
    yedi = timedelta(days=7)
    return (bas, son), (bas - yedi, son - yedi)


def tatiller_oku(kok):
    """`takimlar/kalite/tatiller.json` → tarih kümesi. Dosya yoksa ya da bozuksa boş küme."""
    try:
        ham = json.loads((Path(kok) / "takimlar" / "kalite" / "tatiller.json").read_text(encoding="utf-8"))
        return {date.fromisoformat(str(o["tarih"])) for o in ham}
    except (OSError, ValueError, KeyError, TypeError):
        return set()
