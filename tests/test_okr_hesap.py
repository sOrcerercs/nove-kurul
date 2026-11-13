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
