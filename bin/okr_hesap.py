"""OKR hesabı — Nove Performance sitesinin `lib/domain` hesabının Python karşılığı (B1: taşınır, icat edilmez).

Kaynak: `/Users/sorcerer/Desktop/Nove Performance`, HEAD `d5d0e5d`; ajan için salt okunur. Fonksiyon adları
sitedekinin snake_case'idir; her taşınan bloğun üstünde `# KAYNAK:` satırı vardır.

B1a: sitenin `lib/domain` ya da `lib/queries/{tree,std,range}.ts` hesabı değişirse bu dosya güncellenir;
Kağan'ın üç sayılık karşılaştırması yinelenir.

Yuvarlama `kalite_veri.js_yuvarla` ile (JS `Math.round`, yarımlar yukarı). Toplamlar soldan sağa düz döngüyle.

KR bir sözlüktür: `start, current, target` zorunlu; `weight`, `rollup` yoksa `None`.
"""
import math

from kalite_veri import js_yuvarla

# KAYNAK: Nove Performance lib/domain/status.ts:3-14 @ d5d0e5d
DURUM_ADLARI = {
    "above": "Beklenenin Üzerinde",
    "expected": "Beklenen",
    "below": "Beklenenin Altında",
    "open": "Gelişime Açık",
    "none": "Başlamadı",
}

# KAYNAK: Nove Performance lib/domain/status.ts:18-24 @ d5d0e5d
def status_of(pct):
    if pct >= 101:
        return "above"
    if pct >= 80:
        return "expected"
    if pct >= 60:
        return "below"
    if pct >= 1:
        return "open"
    return "none"


# KAYNAK: Nove Performance lib/domain/status.ts:27 @ d5d0e5d
def is_open_to_development(pct):
    return pct <= 59


# KAYNAK: Nove Performance lib/domain/weights.ts:11 @ d5d0e5d
WEIGHT_TOLERANCE = 0.005


# KAYNAK: Nove Performance lib/domain/weights.ts:15 @ d5d0e5d
def _is_set(w):
    return isinstance(w, (int, float)) and not isinstance(w, bool) and math.isfinite(w)


# KAYNAK: Nove Performance lib/domain/weights.ts:21-31 @ d5d0e5d
def check_weights(ws, required):
    set_ = [w for w in ws if _is_set(w)]
    if len(set_) == 0:
        return "missing" if required else None
    if len(set_) != len(ws):
        return "partial"
    if any(w <= 0 or w > 100 or abs(w * 100 - js_yuvarla(w * 100)) > 1e-6 for w in set_):
        return "range"
    toplam = 0
    for w in set_:
        toplam = toplam + w
    if abs(toplam - 100) > WEIGHT_TOLERANCE:
        return "total"
    return None


# KAYNAK: Nove Performance lib/domain/weights.ts:49-52 @ d5d0e5d
def weight_set_state(ws):
    if not any(_is_set(w) for w in ws):
        return "none"
    return "complete" if check_weights(ws, True) is None else "incomplete"


# KAYNAK: Nove Performance lib/domain/progress.ts:8-10 @ d5d0e5d
def effective_start(kr):
    return 0 if kr.get("rollup") == "sum" else kr["start"]


# KAYNAK: Nove Performance lib/domain/progress.ts:25-31 @ d5d0e5d
def kr_pct(kr):
    start = effective_start(kr)
    span = kr["target"] - start
    if span == 0:
        return 0
    p = ((kr["current"] - start) / span) * 100
    return max(0, min(140, js_yuvarla(p)))


# KAYNAK: Nove Performance lib/domain/progress.ts:42-44 @ d5d0e5d
def is_measurable(kr):
    return kr["target"] != effective_start(kr)


# KAYNAK: Nove Performance lib/domain/progress.ts:46-47 @ d5d0e5d
def _mean(xs):
    if len(xs) == 0:
        return 0
    toplam = 0
    for x in xs:
        toplam = toplam + x
    return js_yuvarla(toplam / len(xs))


# KAYNAK: Nove Performance lib/domain/progress.ts:55-62 @ d5d0e5d
def obj_pct(krs):
    measurable = [k for k in krs if is_measurable(k)]
    weighted = len(measurable) > 0 and all(_is_set(k.get("weight")) and k["weight"] > 0 for k in measurable)
    if not weighted:
        return _mean([kr_pct(k) for k in measurable])
    total = 0
    for k in measurable:
        total = total + k["weight"]
    pay = 0
    for k in measurable:
        pay = pay + kr_pct(k) * k["weight"]
    return js_yuvarla(pay / total)


# KAYNAK: Nove Performance lib/domain/progress.ts:73 @ d5d0e5d
def _has_measurable_kr(o):
    return any(is_measurable(k) for k in o["krs"])


# KAYNAK: Nove Performance lib/domain/progress.ts:83-93 @ d5d0e5d
def objective_weights_complete(objectives):
    if len(objectives) == 0:
        return False
    by_period = {}
    for o in objectives:
        by_period.setdefault(o.get("period_id") or "", []).append(o.get("weight"))
    return all(weight_set_state(ws) == "complete" for ws in by_period.values())


# KAYNAK: Nove Performance lib/domain/progress.ts:106-113 @ d5d0e5d
def dept_pct(objectives):
    measurable = [o for o in objectives if _has_measurable_kr(o)]
    if len(measurable) == 0 or not objective_weights_complete(objectives):
        return _mean([obj_pct(o["krs"]) for o in measurable])
    total = 0
    for o in measurable:
        total = total + o["weight"]
    pay = 0
    for o in measurable:
        pay = pay + obj_pct(o["krs"]) * o["weight"]
    return js_yuvarla(pay / total)


# KAYNAK: Nove Performance lib/domain/progress.ts:121-125 @ d5d0e5d
def company_pct(depts):
    return _mean([dept_pct(d["objectives"]) for d in depts
                  if any(_has_measurable_kr(o) for o in d["objectives"])])
