"""OKR hesabı — Nove Performance sitesinin `lib/domain` hesabının Python karşılığı (B1: taşınır, icat edilmez).

Kaynak: `/Users/sorcerer/Desktop/Nove Performance`, HEAD `d5d0e5d`; ajan için salt okunur. Fonksiyon adları
sitedekinin snake_case'idir; her taşınan bloğun üstünde `# KAYNAK:` satırı vardır.

B1a: sitenin `lib/domain` ya da `lib/queries/{tree,std,range}.ts` hesabı değişirse bu dosya güncellenir;
Kağan'ın üç sayılık karşılaştırması yinelenir.

Yuvarlama `kalite_veri.js_yuvarla` ile (JS `Math.round`, yarımlar yukarı). Toplamlar soldan sağa düz döngüyle.

KR bir sözlüktür: `start, current, target` zorunlu; `weight`, `rollup` yoksa `None`.
"""
import calendar
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

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


# KAYNAK: Nove Performance lib/domain/monthly.ts:27-45 @ d5d0e5d
def months_in_range(from_, to):
    yil, ay = int(from_.split("-")[0]), int(from_.split("-")[1])
    son = to[:7]
    aylar = []
    while True:
        ay_dizgi = f"{yil:04d}-{ay:02d}"
        if ay_dizgi > son:
            break
        aylar.append(ay_dizgi)
        ay += 1
        if ay > 12:
            ay = 1
            yil += 1
    return aylar


# KAYNAK: Nove Performance lib/domain/monthly.ts:52-54 @ d5d0e5d
def months_of_period(starts_on, ends_on):
    return months_in_range(starts_on, ends_on)


# KAYNAK: Nove Performance lib/domain/monthly.ts:66-76 @ d5d0e5d
def rollup(rule, values):
    if len(values) == 0:
        return None
    if rule == "sum":
        toplam = 0
        for v in values:
            toplam = toplam + v
        return toplam
    if rule == "avg":
        toplam = 0
        for v in values:
            toplam = toplam + v
        return toplam / len(values)
    if rule == "last":
        return values[-1]
    raise ValueError(f"bilinmeyen toplama kuralı: {rule}")


# KAYNAK: Nove Performance lib/domain/monthly.ts:97-134 @ d5d0e5d
def value_for_range(rule, months, by_month, period_months):
    bos = {"value": None, "carried_from": None, "latest_month": None}
    ordered = sorted(months)
    dolu_aylar = [m for m in ordered if m in by_month]
    dolu = [by_month[m] for m in dolu_aylar]
    value = rollup(rule, dolu)
    if value is not None:
        return {"value": value, "carried_from": None, "latest_month": dolu_aylar[-1]}
    if rule != "last":
        return bos
    if len(ordered) == 0:
        return bos
    aralik_basi = ordered[0]
    for aday in reversed(period_months):
        if aday >= aralik_basi:
            continue
        tasinan = by_month.get(aday)
        if tasinan is not None:
            return {"value": tasinan, "carried_from": aday, "latest_month": aday}
    return bos


# KAYNAK: Nove Performance lib/domain/fiscal.ts:14 @ d5d0e5d
FISCAL_START_MONTH = 9


# KAYNAK: Nove Performance lib/domain/fiscal.ts:19-24 @ d5d0e5d
def fiscal_year_of(date):
    parcalar = date.split("-")
    yil, ay = int(parcalar[0]), int(parcalar[1])
    return yil if ay >= FISCAL_START_MONTH else yil - 1


# KAYNAK: Nove Performance lib/domain/fiscal.ts:33-42 @ d5d0e5d
def fiscal_quarter_range(fiscal_year, quarter):
    baslangic_ay_indeksi = FISCAL_START_MONTH - 1 + 3 * (quarter - 1)
    # Ay taşması tam sayı aritmetiğiyle: indeks 12 = gelecek yılın Ocak'ı
    bas_yil, bas_ay = fiscal_year + baslangic_ay_indeksi // 12, baslangic_ay_indeksi % 12 + 1
    son_indeks = baslangic_ay_indeksi + 2
    son_yil, son_ay = fiscal_year + son_indeks // 12, son_indeks % 12 + 1
    son_gun = calendar.monthrange(son_yil, son_ay)[1]
    return {
        "starts_on": f"{bas_yil:04d}-{bas_ay:02d}-01",
        "ends_on": f"{son_yil:04d}-{son_ay:02d}-{son_gun:02d}",
    }


# KAYNAK: Nove Performance lib/domain/fiscal.ts:45-50 @ d5d0e5d
def fiscal_year_range(fiscal_year):
    return {
        "starts_on": fiscal_quarter_range(fiscal_year, 1)["starts_on"],
        "ends_on": fiscal_quarter_range(fiscal_year, 4)["ends_on"],
    }


# KAYNAK: Nove Performance lib/domain/dates.ts:23-32 @ d5d0e5d
def today_in_istanbul(now=None):
    if now is None:
        now = datetime.now(ZoneInfo("UTC"))
    return now.astimezone(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")


# KAYNAK: Nove Performance lib/domain/dates.ts:56-59 @ d5d0e5d
def as_of_cutoff(to, today):
    return to if to < today else today


# KAYNAK: Nove Performance lib/domain/dates.ts:34,62-67 @ d5d0e5d
def is_valid_iso_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    yil, ay, gun = (int(x) for x in value.split("-"))
    if ay < 1 or ay > 12:
        return False
    return 1 <= gun <= calendar.monthrange(yil, ay)[1]


# KAYNAK: Nove Performance lib/domain/std.ts:15-21 @ d5d0e5d
def last_completed_month(as_of):
    yil, ay, gun = (int(x) for x in as_of.split("-"))
    son_gun = calendar.monthrange(yil, ay)[1]
    if gun == son_gun:
        return as_of[:7]
    onceki_yil, onceki_ay = (yil, ay - 1) if ay > 1 else (yil - 1, 12)
    return f"{onceki_yil:04d}-{onceki_ay:02d}"


# KAYNAK: Nove Performance lib/domain/monthly-table.ts:14-16 @ d5d0e5d
def monthly_target(rule, target, month_count):
    return target / month_count if rule == "sum" and month_count > 0 else target


# KAYNAK: Nove Performance lib/domain/std.ts:44-47,55-68 @ d5d0e5d
def std_figure(rollup, target, period_months, by_month, as_of):
    kesim = last_completed_month(as_of)
    sayilan = [m for m in period_months if m <= kesim]
    k = len(sayilan)
    if k == 0:
        return None
    deger = value_for_range(rollup, sayilan, by_month, period_months)["value"]
    if deger is None:
        return None
    return {
        "current": deger,
        "target": monthly_target("sum", target, len(period_months)) * k if rollup == "sum" else target,
        "months_counted": k,
        "months_filled": len([m for m in sayilan if m in by_month]),
    }
