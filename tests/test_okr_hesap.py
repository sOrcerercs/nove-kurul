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

    def test_rollup_bilinmeyen_kural(self):
        # Sitedeki sessiz düşüşten bilerek ayrılır: bilinmeyen kural hata verir
        with self.assertRaises(ValueError):
            h.rollup("median", [1, 2])

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


class StdTesti(unittest.TestCase):
    FY = h.months_of_period("2026-09-01", "2027-08-31")

    def _std(self, kural, hedef, by, as_of):
        return h.std_figure(kural, hedef, self.FY, by, as_of)

    def test_last_completed_month(self):
        for as_of, beklenen in [("2026-11-04", "2026-10"), ("2026-11-30", "2026-11"),
                                ("2026-12-31", "2026-12"), ("2026-09-15", "2026-08"),
                                ("2027-08-31", "2027-08"), ("2028-02-28", "2028-01"),
                                ("2028-02-29", "2028-02"), ("2027-02-28", "2027-02")]:
            self.assertEqual(h.last_completed_month(as_of), beklenen, as_of)

    def test_monthly_target(self):
        self.assertEqual(h.monthly_target("sum", 3000, 12), 250)
        self.assertEqual(h.monthly_target("sum", 3000, 0), 3000)
        self.assertEqual(h.monthly_target("avg", 90, 12), 90)
        self.assertEqual(h.monthly_target("last", 90, 12), 90)

    def test_std_sum(self):
        by = {"2026-09": 200, "2026-10": 250, "2026-11": 200, "2026-12": 250}
        self.assertEqual(self._std("sum", 3000, by, "2026-12-31"),
                         {"current": 900, "target": 1000, "months_counted": 4, "months_filled": 4})

    def test_std_avg(self):
        self.assertEqual(self._std("avg", 90, {"2026-09": 95, "2026-10": 80}, "2026-11-04"),
                         {"current": 87.5, "target": 90, "months_counted": 2, "months_filled": 2})

    def test_icinde_bulunulan_ay_sayilmaz(self):
        self.assertEqual(self._std("sum", 3000, {"2026-09": 200, "2026-11": 999}, "2026-11-04"),
                         {"current": 200, "target": 500, "months_counted": 2, "months_filled": 1})

    def test_std_none(self):
        self.assertIsNone(self._std("sum", 3000, {"2026-09": 1}, "2026-09-15"))
        self.assertIsNone(self._std("sum", 3000, {"2026-11": 1}, "2026-11-04"))

    def test_kapali_donem(self):
        by = {m: 250 for m in self.FY}
        self.assertEqual(self._std("sum", 3000, by, "2027-08-31"),
                         {"current": 3000, "target": 3000, "months_counted": 12, "months_filled": 12})


# --- Task 4: ağaç, kesim, çiftler (site tree/std/range testlerinin bellek içi karşılığı) ---

M1, M2, M3, M4 = "2026-09", "2026-10", "2026-11", "2026-12"


def _tkr(id_, objective_id="o1", start=0, current=0, target=100, rollup="sum", unit="", weight=None):
    return {"id": id_, "objective_id": objective_id, "title_tr": f"KR {id_}", "start": start,
            "current": current, "target": target, "unit": unit, "rollup": rollup, "weight": weight,
            "owner_user_id": "u1"}


def _ay(kr_id, month, value):
    return {"key_result_id": kr_id, "month": month, "value": value}


def _satirlar(**ek):
    rows = {
        "periods": [
            {"id": "p26", "code": "p-2026-fy", "kind": "fiscal_year", "state": "active",
             "starts_on": "2026-09-01", "ends_on": "2027-08-31"},
            {"id": "p25", "code": "p-2025-fy", "kind": "fiscal_year", "state": "closed",
             "starts_on": "2025-09-01", "ends_on": "2026-08-31"},
        ],
        "departments": [{"id": "d-sat", "slug": "satis", "name_tr": "Satış"}],
        "users": [{"id": "u1", "name": "Deniz Örnek"}],
        "objectives": [{"id": "o1", "code": "O1", "department_id": "d-sat", "period_id": "p26",
                        "title_tr": "Örnek hedef", "owner_user_id": "u1", "weight": None}],
        "key_results": [],
        "monthly": [],
    }
    for anahtar, ekler in ek.items():
        rows[anahtar] = rows[anahtar] + list(ekler)
    return rows


def _kr_bul(depts, kr_id):
    for d in depts:
        for ob in d["objectives"]:
            for k in ob["krs"]:
                if k["id"] == kr_id:
                    return k
    raise AssertionError(f"KR yok: {kr_id}")


def _kr_idleri(depts):
    return [k["id"] for d in depts for ob in d["objectives"] for k in ob["krs"]]


class AgacTesti(unittest.TestCase):
    def _yukle(self, rows, as_of, period_ids=("p26",)):
        return h.load_tree(rows, list(period_ids), as_of)

    def test_aylik_satiri_olmayan_ozetini_korur(self):
        _, depts = self._yukle(_satirlar(key_results=[_tkr("k1", current=42)]), f"{M1}-15")
        k = _kr_bul(depts, "k1")
        self.assertEqual(k["current"], 42)
        self.assertTrue(k["measured_by_cutoff"])
        self.assertIsNone(k["latest_month"])
        self.assertIsNone(k["std"])
        self.assertTrue(k["bridge"])

    def test_dugum_alanlari(self):
        periods, depts = self._yukle(_satirlar(key_results=[_tkr("k1")]), f"{M1}-15")
        self.assertEqual(periods, [{"id": "p26", "code": "p-2026-fy"}])
        self.assertEqual(depts[0]["id"], "d-sat")
        self.assertEqual(depts[0]["slug"], "satis")
        self.assertEqual(depts[0]["name_tr"], "Satış")
        ob = depts[0]["objectives"][0]
        self.assertEqual((ob["code"], ob["owner_name"], ob["period_id"], ob["department_id"]),
                         ("O1", "Deniz Örnek", "p26", "d-sat"))
        self.assertEqual(ob["krs"][0]["owner_name"], "Deniz Örnek")

    def test_kesim_dahil_toplar(self):
        rows = _satirlar(key_results=[_tkr("k1")],
                         monthly=[_ay("k1", M1, 20), _ay("k1", M2, 40), _ay("k1", M4, 500)])
        k = _kr_bul(self._yukle(rows, f"{M2}-15")[1], "k1")
        self.assertEqual(k["current"], 60)
        self.assertEqual(k["latest_month"], M2)
        self.assertTrue(k["measured_by_cutoff"])
        self.assertFalse(k["bridge"])

    def test_ay_ortasi_kesim_tum_ayi_alir(self):
        rows = _satirlar(key_results=[_tkr("k1")], monthly=[_ay("k1", M1, 40)])
        self.assertEqual(_kr_bul(self._yukle(rows, f"{M1}-01")[1], "k1")["current"], 40)
        self.assertEqual(_kr_bul(self._yukle(rows, f"{M1}-28")[1], "k1")["current"], 40)

    def test_kesime_kadar_veri_yoksa_olculmemis(self):
        rows = _satirlar(key_results=[_tkr("k1", start=73, current=73, target=80, rollup="avg")],
                         monthly=[_ay("k1", M3, 60)])
        k = _kr_bul(self._yukle(rows, f"{M1}-15")[1], "k1")
        self.assertEqual(k["current"], 73)
        self.assertFalse(k["measured_by_cutoff"])
        self.assertIsNone(k["latest_month"])
        self.assertFalse(k["bridge"])

    def test_sum_kesimden_sonra_sifir_okur(self):
        rows = _satirlar(key_results=[_tkr("k1", start=51500, target=60000)],
                         monthly=[_ay("k1", M3, 4000)])
        k = _kr_bul(self._yukle(rows, f"{M1}-15")[1], "k1")
        self.assertEqual(k["current"], 0)
        self.assertFalse(k["measured_by_cutoff"])
        self.assertEqual(h.kr_pct(k), 0)

    def test_measured_only(self):
        rows = _satirlar(key_results=[_tkr("k1"), _tkr("k2", current=42)], monthly=[_ay("k1", M3, 60)])
        _, depts = self._yukle(rows, f"{M1}-15")
        once = _kr_idleri(depts)
        sonra = _kr_idleri(h.measured_only(depts))
        self.assertIn("k1", once)
        self.assertNotIn("k1", sonra)
        self.assertEqual(sonra, ["k2"])
        self.assertEqual(_kr_idleri(depts), once)  # girdi değişmez

    def test_her_kr_kendi_doneminin_aylari(self):
        rows = _satirlar(
            objectives=[{"id": "o25", "code": "OC1", "department_id": "d-sat", "period_id": "p25",
                         "title_tr": "Kesit hedefi", "owner_user_id": None, "weight": None}],
            key_results=[_tkr("k25", objective_id="o25"), _tkr("k26", current=42)],
            monthly=[_ay("k25", "2025-10", 10), _ay("k26", "2025-09", 70)])
        _, depts = self._yukle(rows, "2025-10-15", period_ids=("p25", "p26"))
        self.assertEqual(_kr_bul(depts, "k25")["current"], 10)
        k26 = _kr_bul(depts, "k26")
        self.assertEqual(k26["current"], 42)
        self.assertTrue(k26["measured_by_cutoff"])
        self.assertTrue(k26["bridge"])

    def test_donem_disi_satir_kopruye_duser(self):
        rows = _satirlar(key_results=[_tkr("k1", current=42)], monthly=[_ay("k1", "2027-09", 70)])
        _, depts = self._yukle(rows, f"{M1}-15")
        k = _kr_bul(depts, "k1")
        self.assertEqual(k["current"], 42)
        self.assertTrue(k["measured_by_cutoff"])
        self.assertIsNone(k["latest_month"])
        self.assertIn("k1", _kr_idleri(h.measured_only(depts)))

    def test_avg_dolu_aylar(self):
        rows = _satirlar(key_results=[_tkr("k1", start=4.25, current=4.25, target=5.3, rollup="avg")],
                         monthly=[_ay("k1", M1, 4.4), _ay("k1", M2, 4.5), _ay("k1", M3, 5.0)])
        k = _kr_bul(self._yukle(rows, f"{M3}-15")[1], "k1")
        self.assertAlmostEqual(k["current"], (4.4 + 4.5 + 5.0) / 3)
        self.assertTrue(k["measured_by_cutoff"])

    def test_last_bayat_ay(self):
        rows = _satirlar(key_results=[_tkr("k1", start=4.04, current=4.04, target=4.8, rollup="last")],
                         monthly=[_ay("k1", M1, 4.1), _ay("k1", M2, 4.2)])
        k = _kr_bul(self._yukle(rows, f"{M4}-15")[1], "k1")
        self.assertEqual(k["current"], 4.2)
        self.assertEqual(k["latest_month"], M2)
        self.assertTrue(k["measured_by_cutoff"])

    def test_kesit_uc_kural(self):
        rows = _satirlar(
            key_results=[_tkr("ks"), _tkr("ka", start=98.87, current=98.87, target=99.5, rollup="avg"),
                         _tkr("kl", rollup="last")],
            monthly=[_ay("ks", M1, 20), _ay("ks", M2, 20), _ay("ks", M3, 500),
                     _ay("ka", M1, 99), _ay("ka", M2, 99.4), _ay("ka", M3, 10),
                     _ay("kl", M1, 30), _ay("kl", M2, 45), _ay("kl", M3, 99)])
        _, depts = self._yukle(rows, f"{M2}-15")
        self.assertEqual(_kr_bul(depts, "ks")["current"], 40)
        self.assertAlmostEqual(_kr_bul(depts, "ka")["current"], 99.2, places=5)
        self.assertEqual(_kr_bul(depts, "kl")["current"], 45)
        for kid in ("ks", "ka", "kl"):
            self.assertEqual(_kr_bul(depts, kid)["latest_month"], M2)

    def test_std_tamamlanan_aylar(self):
        rows = _satirlar(key_results=[_tkr("k1", target=200)],
                         monthly=[_ay("k1", M1, 20), _ay("k1", M2, 30), _ay("k1", M3, 40)])
        std = _kr_bul(self._yukle(rows, f"{M3}-15")[1], "k1")["std"]
        self.assertEqual(std["months_counted"], 2)
        self.assertEqual(std["months_filled"], 2)
        self.assertEqual(std["current"], 50)
        self.assertAlmostEqual(std["target"], 200 / 12 * 2)

    def test_std_yalniz_kesim_ayi_doluysa_none(self):
        rows = _satirlar(key_results=[_tkr("k1", target=200)], monthly=[_ay("k1", M3, 40)])
        self.assertIsNone(_kr_bul(self._yukle(rows, f"{M3}-15")[1], "k1")["std"])

    def test_iki_donem_std(self):
        aylar = h.months_of_period("2025-09-01", "2026-08-31")
        rows = _satirlar(
            objectives=[{"id": "o25", "code": "OS1", "department_id": "d-sat", "period_id": "p25",
                         "title_tr": "StD hedefi", "owner_user_id": None, "weight": None}],
            key_results=[_tkr("k25", objective_id="o25", target=120)],
            monthly=[_ay("k25", m, 10) for m in aylar])
        _, depts = self._yukle(rows, "2026-11-15", period_ids=("p25", "p26"))
        std = _kr_bul(depts, "k25")["std"]
        self.assertEqual(std["months_counted"], 12)
        self.assertAlmostEqual(std["target"], 120)
        self.assertEqual(std["current"], 120)

    def test_bos_ya_da_bilinmeyen_donem(self):
        rows = _satirlar(key_results=[_tkr("k1")])
        self.assertEqual(h.load_tree(rows, [], f"{M1}-15"), ([], []))
        self.assertEqual(h.load_tree(rows, ["yok"], f"{M1}-15"), ([], []))


def _pkr(**ek):
    d = {"id": "k", "title_tr": "", "start": 0, "current": 900, "target": 3000, "unit": "", "rollup": "sum",
         "weight": None, "owner_name": "", "latest_month": None, "measured_by_cutoff": True, "std": None,
         "bridge": False}
    d.update(ek)
    return d


def _pstd(**ek):
    return _pkr(std={"current": 900, "target": 1000, "months_counted": 4, "months_filled": 4}, **ek)


def _pobj(krs, weight=None):
    return {"id": "o", "code": "O1", "title_tr": "", "owner_name": "", "department_id": "d", "period_id": "p",
            "weight": weight, "krs": krs}


def _pdept(objectives):
    return {"id": "d", "slug": "d", "name_tr": "", "objectives": objectives}


class CiftTesti(unittest.TestCase):
    def test_kr_pair(self):
        p = h.kr_pair(_pstd())
        self.assertEqual((p["annual"], p["std"], p["status_pct"]), (30, 90, 90))
        duz = h.kr_pair(_pkr())
        self.assertIsNone(duz["std"])
        self.assertEqual(duz["status_pct"], duz["annual"])
        self.assertEqual((duz["with_std"], duz["measurable"]), (0, 1))

    def test_obj_pair(self):
        p = h.obj_pair(_pobj([_pkr(id="a", weight=60), _pstd(id="b", weight=40)]))
        self.assertEqual(p["std"], 90)
        self.assertEqual((p["with_std"], p["measurable"]), (1, 2))

    def test_dept_pair(self):
        p = h.dept_pair(_pdept([_pobj([_pkr()])]))
        self.assertIsNone(p["std"])
        self.assertEqual(p["status_pct"], p["annual"])
        self.assertEqual((p["with_std"], p["measurable"]), (0, 1))

    def test_company_pair(self):
        p = h.company_pair([_pdept([_pobj([_pkr()])]), _pdept([_pobj([_pstd()])])])
        self.assertEqual(p["std"], 90)
        self.assertEqual((p["with_std"], p["measurable"]), (1, 2))

    def test_std_krs_of(self):
        out = h.std_krs_of([_pkr(), _pstd()])
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["current"], out[0]["target"]), (900, 1000))


class DonemAraligiTesti(unittest.TestCase):
    def test_periods_in_range(self):
        def p(id_, s, e):
            return {"id": id_, "code": "X", "kind": "quarter", "state": "planned", "starts_on": s, "ends_on": e}
        periods = [p("before", "2025-01-01", "2025-08-31"), p("ends-on-from", "2025-06-01", "2025-09-01"),
                   p("inside", "2025-10-01", "2025-12-31"), p("starts-on-to", "2026-08-10", "2026-10-31"),
                   p("after", "2026-08-11", "2026-12-31")]
        hit = h.periods_in_range(periods, "2025-09-01", "2026-08-10")
        self.assertEqual([x["id"] for x in hit], ["ends-on-from", "inside", "starts-on-to"])

    def test_eskiden_yeniye(self):
        periods = [{"id": "b", "starts_on": "2025-12-01", "ends_on": "2026-02-28"},
                   {"id": "a", "starts_on": "2025-09-01", "ends_on": "2025-11-30"}]
        hit = h.periods_in_range(periods, "2025-09-01", "2026-08-10")
        self.assertEqual([x["id"] for x in hit], ["a", "b"])


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
