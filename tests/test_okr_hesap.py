"""okr_hesap.py testleri — Nove Performance sitesinin lib/domain testlerinin vektörleri aynen.

python3 -m unittest tests.test_okr_hesap -v
"""
import re
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import okr_hesap as h  # noqa: E402


def kr(start, current, target, weight=None, rollup=None):
    return {"start": start, "current": current, "target": target, "weight": weight, "rollup": rollup}


def o(pct, weight, period_id="p1"):
    return {"krs": [kr(0, pct, 100)], "weight": weight, "period_id": period_id}


def olculemez(weight, period_id="p1"):
    return {"krs": [kr(5, 5, 5)], "weight": weight, "period_id": period_id}


class KrPctTesti(unittest.TestCase):
    def test_kr_pct(self):
        self.assertEqual(h.kr_pct(kr(42000, 61000, 80000)), 50)
        self.assertEqual(h.kr_pct(kr(950, 720, 650)), 77)
        self.assertEqual(h.kr_pct(kr(100, 120, 50)), 0)
        self.assertEqual(h.kr_pct(kr(0, 500, 100)), 140)
        self.assertEqual(h.kr_pct(kr(50, 70, 50)), 0)
        self.assertEqual(h.kr_pct(kr(51500, 19167, 57500, rollup="sum")), 33)
        self.assertEqual(h.kr_pct(kr(950, 720, 650, rollup="avg")), 77)
        self.assertEqual(h.kr_pct(kr(950, 720, 650, rollup="last")), 77)

    def test_effective_start(self):
        self.assertEqual(h.effective_start(kr(51500, 0, 1, rollup="sum")), 0)
        self.assertEqual(h.effective_start(kr(950, 0, 1, rollup="avg")), 950)
        self.assertEqual(h.effective_start({"start": 7, "current": 0, "target": 1}), 7)

    def test_is_measurable(self):
        self.assertFalse(h.is_measurable(kr(77.5, 77.5, 77.5)))
        self.assertFalse(h.is_measurable(kr(0, 0, 0)))
        self.assertTrue(h.is_measurable(kr(0, 0, 100)))
        self.assertTrue(h.is_measurable(kr(110, 110, 100)))
        self.assertTrue(h.is_measurable(kr(100, 0, 100, rollup="sum")))
        self.assertFalse(h.is_measurable(kr(0, 0, 0, rollup="sum")))
        self.assertFalse(h.is_measurable(kr(100, 0, 100, rollup="avg")))

    def test_yarim_yukari_yuvarlanir(self):
        self.assertEqual(h.kr_pct(kr(0, 12.5, 100)), 13)
        self.assertEqual(h.obj_pct([kr(0, 62, 100), kr(0, 63, 100)]), 63)


class ObjDeptCompanyTesti(unittest.TestCase):
    def test_obj_pct(self):
        self.assertEqual(h.obj_pct([kr(0, 50, 100), kr(0, 80, 100)]), 65)
        self.assertEqual(h.obj_pct([]), 0)
        self.assertEqual(h.obj_pct([kr(0, 50, 100), kr(5, 5, 5)]), 50)
        self.assertEqual(h.obj_pct([kr(5, 5, 5)]), 0)
        self.assertEqual(h.obj_pct([kr(0, 80, 100, 75), kr(0, 40, 100, 25)]), 70)
        self.assertEqual(h.obj_pct([kr(0, 80, 100, 40), kr(0, 40, 100, 40), kr(5, 5, 5, 20)]), 60)
        self.assertEqual(h.obj_pct([kr(0, 80, 100), kr(0, 40, 100)]), 60)
        self.assertEqual(h.obj_pct([kr(0, 80, 100, None), kr(0, 40, 100, None)]), 60)
        self.assertEqual(h.obj_pct([kr(0, 80, 100, 90), kr(0, 40, 100, None)]), 60)

    def test_dept_pct(self):
        self.assertEqual(h.dept_pct([{"krs": [kr(0, 100, 100)]},
                                     {"krs": [kr(0, 0, 100), kr(0, 0, 100)]}]), 50)
        self.assertEqual(h.dept_pct([{"krs": [kr(0, 80, 100)]}, {"krs": [kr(5, 5, 5)]}]), 80)
        self.assertEqual(h.dept_pct([{"krs": [kr(5, 5, 5)]}]), 0)
        self.assertEqual(h.dept_pct([]), 0)
        self.assertEqual(h.dept_pct([o(80, 70), o(40, 30)]), 68)
        self.assertEqual(h.dept_pct([o(80, None), o(40, None)]), 60)
        self.assertEqual(h.dept_pct([o(80, 70), o(40, None)]), 60)
        self.assertEqual(h.dept_pct([o(80, 60), o(40, 30)]), 60)
        self.assertTrue(h.objective_weights_complete([o(80, 70), olculemez(30)]))
        self.assertEqual(h.dept_pct([o(80, 70), olculemez(30)]), 80)
        bosaltilmis = {"krs": [], "weight": 40, "period_id": "p1"}
        self.assertTrue(h.objective_weights_complete([o(80, 60), bosaltilmis]))
        self.assertEqual(h.dept_pct([o(80, 60), bosaltilmis]), 80)
        self.assertEqual(h.dept_pct([o(80, 100, "p1"), o(40, 50, "p2"), o(0, 50, "p2")]), 50)
        self.assertEqual(h.dept_pct([o(80, 100, "p1"), o(40, None, "p2"), o(0, None, "p2")]), 40)
        self.assertFalse(h.objective_weights_complete([]))

    def test_company_pct(self):
        self.assertEqual(h.company_pct([{"objectives": [{"krs": [kr(0, 40, 100)]}]},
                                        {"objectives": []}]), 40)
        self.assertEqual(h.company_pct([]), 0)
        self.assertEqual(h.company_pct([{"objectives": [{"krs": [kr(0, 60, 100)]}]},
                                        {"objectives": [{"krs": [kr(5, 5, 5)]}]}]), 60)
        self.assertEqual(h.company_pct([{"objectives": [{"krs": [kr(5, 5, 5)]}]}]), 0)
        self.assertEqual(h.company_pct([{"objectives": [o(80, 70), o(40, 30)]},
                                        {"objectives": [o(40, None)]}]), 54)


class AgirlikTesti(unittest.TestCase):
    def test_weight_set_state(self):
        self.assertEqual(h.weight_set_state([]), "none")
        self.assertEqual(h.weight_set_state([None, None]), "none")
        self.assertEqual(h.weight_set_state([60, 40]), "complete")
        self.assertEqual(h.weight_set_state([33.34, 33.33, 33.33]), "complete")
        self.assertEqual(h.weight_set_state([60, None]), "incomplete")
        self.assertEqual(h.weight_set_state([60, 30]), "incomplete")

    def test_check_weights(self):
        self.assertIsNone(h.check_weights([50, 30, 20], True))
        self.assertIsNone(h.check_weights([33.34, 33.33, 33.33], True))
        self.assertEqual(h.check_weights([33.33, 33.33, 33.33], True), "total")
        self.assertEqual(h.check_weights([50, 50.01], True), "total")
        self.assertEqual(h.check_weights([None, None], True), "missing")
        self.assertIsNone(h.check_weights([None, None], False))
        self.assertEqual(h.check_weights([100, None], False), "partial")
        self.assertEqual(h.check_weights([0, 100], True), "range")
        self.assertEqual(h.check_weights([-10, 110], True), "range")
        self.assertEqual(h.check_weights([33.333, 66.667], True), "range")

    def test_tolerans(self):
        self.assertEqual(h.WEIGHT_TOLERANCE, 0.005)


class DurumTesti(unittest.TestCase):
    def test_status_of(self):
        for p in (140, 130, 101):
            self.assertEqual(h.status_of(p), "above")
        for p in (100, 80):
            self.assertEqual(h.status_of(p), "expected")
        for p in (79, 60):
            self.assertEqual(h.status_of(p), "below")
        for p in (59, 1):
            self.assertEqual(h.status_of(p), "open")
        self.assertEqual(h.status_of(0), "none")
        self.assertTrue(h.is_open_to_development(59))
        self.assertFalse(h.is_open_to_development(60))

    def test_durum_adlari(self):
        self.assertEqual(h.DURUM_ADLARI, {
            "above": "Beklenenin Üzerinde", "expected": "Beklenen", "below": "Beklenenin Altında",
            "open": "Gelişime Açık", "none": "Başlamadı"})


class AyTesti(unittest.TestCase):
    def test_months_in_range(self):
        self.assertEqual(h.months_in_range("2026-03-12", "2026-05-20"), ["2026-03", "2026-04", "2026-05"])
        self.assertEqual(h.months_in_range("2026-03-28", "2026-04-02"), ["2026-03", "2026-04"])
        self.assertEqual(h.months_in_range("2026-03-15", "2026-03-15"), ["2026-03"])
        self.assertEqual(h.months_in_range("2025-11-20", "2026-02-03"),
                         ["2025-11", "2025-12", "2026-01", "2026-02"])
        self.assertEqual(h.months_in_range("2026-05-01", "2026-03-01"), [])

    def test_months_of_period(self):
        ay = h.months_of_period("2025-09-01", "2026-08-31")
        self.assertEqual(len(ay), 12)
        self.assertEqual((ay[0], ay[-1]), ("2025-09", "2026-08"))
        self.assertEqual(h.months_of_period("2028-02-01", "2028-02-29"), ["2028-02"])

    def test_rollup(self):
        self.assertEqual(h.rollup("sum", [10, 20, 30]), 60)
        self.assertEqual(h.rollup("avg", [90, 100, 80]), 90)
        self.assertEqual(h.rollup("last", [10, 20, 30]), 30)
        for kural in ("sum", "avg", "last"):
            self.assertIsNone(h.rollup(kural, []))

    def test_value_for_range_tasima(self):
        donem = ["2025-09", "2025-10", "2025-11", "2025-12"]
        s = h.value_for_range("last", ["2025-11", "2025-12"], {"2025-09": 42}, donem)
        self.assertEqual(s, {"value": 42, "carried_from": "2025-09", "latest_month": "2025-09"})
        for kural in ("sum", "avg"):
            self.assertEqual(h.value_for_range(kural, ["2025-11", "2025-12"], {"2025-09": 42}, donem),
                             {"value": None, "carried_from": None, "latest_month": None})

    def test_tasima_donem_disina_cikmaz(self):
        s = h.value_for_range("last", ["2025-10"], {"2025-08": 99}, ["2025-09", "2025-10"])
        self.assertEqual(s, {"value": None, "carried_from": None, "latest_month": None})

    def test_dolu_ay_tasinani_yener(self):
        s = h.value_for_range("last", ["2025-10", "2025-11"], {"2025-09": 42, "2025-11": 7},
                              ["2025-09", "2025-10", "2025-11", "2025-12"])
        self.assertEqual(s, {"value": 7, "carried_from": None, "latest_month": "2025-11"})

    def test_sirasiz_aylar(self):
        by = {"2025-10": 10, "2025-11": 20, "2025-12": 30}
        donem = ["2025-10", "2025-11", "2025-12"]
        s = h.value_for_range("last", ["2025-11", "2025-12", "2025-10"], by, donem)
        self.assertEqual((s["value"], s["latest_month"]), (30, "2025-12"))
        for kural in ("sum", "avg", "last"):
            self.assertEqual(h.value_for_range(kural, ["2025-12", "2025-10", "2025-11"], by, donem),
                             h.value_for_range(kural, donem, by, donem))

    def test_donem_sonunu_asan_aralik(self):
        donem = ["2026-06", "2026-07", "2026-08"]
        s = h.value_for_range("last", ["2026-08", "2026-09"], {"2026-07": 15}, donem)
        self.assertEqual(s, {"value": 15, "carried_from": "2026-07", "latest_month": "2026-07"})
        self.assertEqual(h.value_for_range("sum", ["2026-08", "2026-09"], {"2026-07": 15}, donem),
                         {"value": None, "carried_from": None, "latest_month": None})

    def test_latest_month(self):
        donem = ["2025-09", "2025-10", "2025-11"]
        for kural in ("sum", "avg", "last"):
            s = h.value_for_range(kural, donem, {"2025-09": 10, "2025-11": 30}, donem)
            self.assertEqual(s["latest_month"], "2025-11")
        self.assertEqual(h.value_for_range("last", donem, {"2025-09": 10}, donem)["latest_month"], "2025-09")
        s = h.value_for_range("last", donem, {"2025-09": 10, "2025-10": 0}, donem)
        self.assertEqual((s["value"], s["latest_month"]), (0, "2025-10"))


class MaliTakvimTesti(unittest.TestCase):
    def test_fiscal(self):
        self.assertEqual(h.FISCAL_START_MONTH, 9)
        for t in ("2025-09-01", "2025-12-31", "2026-08-31", "2026-01-01"):
            self.assertEqual(h.fiscal_year_of(t), 2025)
        self.assertEqual(h.fiscal_year_of("2026-09-01"), 2026)
        beklenen = [("2025-09-01", "2025-11-30"), ("2025-12-01", "2026-02-28"),
                    ("2026-03-01", "2026-05-31"), ("2026-06-01", "2026-08-31")]
        for q, (a, b) in enumerate(beklenen, 1):
            self.assertEqual(h.fiscal_quarter_range(2025, q), {"starts_on": a, "ends_on": b})
        self.assertEqual(h.fiscal_quarter_range(2027, 2)["ends_on"], "2028-02-29")
        self.assertEqual(h.fiscal_year_range(2025), {"starts_on": "2025-09-01", "ends_on": "2026-08-31"})


class TarihTesti(unittest.TestCase):
    def test_today_in_istanbul(self):
        from datetime import datetime, timezone
        self.assertEqual(h.today_in_istanbul(datetime(2026, 8, 9, 22, 30, tzinfo=timezone.utc)), "2026-08-10")
        self.assertEqual(h.today_in_istanbul(datetime(2026, 8, 9, 20, 0, tzinfo=timezone.utc)), "2026-08-09")

    def test_as_of_cutoff(self):
        self.assertEqual(h.as_of_cutoff("2026-08-31", "2026-03-15"), "2026-03-15")
        self.assertEqual(h.as_of_cutoff("2025-11-30", "2026-03-15"), "2025-11-30")
        self.assertEqual(h.as_of_cutoff("2026-08-10", "2026-08-10"), "2026-08-10")

    def test_is_valid_iso_date(self):
        for d in ("2026-08-10", "2028-02-29"):
            self.assertTrue(h.is_valid_iso_date(d))
        for d in ("2026-02-30", "2026-13-01", "2026-8-10", "yarın", "", "2026-08-10\n", "٢٠٢٦-08-10"):
            self.assertFalse(h.is_valid_iso_date(d), d)


class KaynakBasliklariTesti(unittest.TestCase):
    def test_kaynak_basliklari(self):
        satirlar = (KOK / "bin" / "okr_hesap.py").read_text(encoding="utf-8").splitlines()
        desen = re.compile(
            r"^# KAYNAK: Nove Performance lib/(domain|queries)/[a-z-]+\.ts:\d+(-\d+)?(,\d+(-\d+)?)* @ d5d0e5d$")
        kaynaklar = [s for s in satirlar if s.startswith("# KAYNAK:")]
        self.assertTrue(kaynaklar)
        for s in kaynaklar:
            self.assertRegex(s, desen)
        for i, s in enumerate(satirlar):
            if not s.startswith("def "):
                continue
            j = i - 1
            blok = []
            while j >= 0 and satirlar[j].startswith("#"):
                blok.append(satirlar[j])
                j -= 1
            self.assertTrue(any(b.startswith("# KAYNAK:") for b in blok), f"başlıksız: {s}")


if __name__ == "__main__":
    unittest.main()
