"""Tebrik takvimi testleri — uydurma adlar, ağ yok.

python3 -m unittest tests.test_tebrik_takvim
"""
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import openpyxl

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import tebrik_takvim as tk  # noqa: E402


def _xlsx(basliklar, satirlar):
    d = tempfile.mkdtemp()
    yol = Path(d) / "t.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(basliklar)
    for s in satirlar:
        ws.append(s)
    wb.save(yol)
    return yol


class TakvimTesti(unittest.TestCase):
    def test_gun_ay_bicimleri(self):
        for d in (datetime(1900, 10, 15), "15.10", "15/10", "15.10.1990", "15/10/1990"):
            self.assertEqual(tk.gun_ay(d), (15, 10))
        for d in ("31.02", "abc", "", None):
            self.assertIsNone(tk.gun_ay(d))

    def test_tam_tarih(self):
        self.assertEqual(tk.tam_tarih("20.10.2026"), date(2026, 10, 20))
        self.assertEqual(tk.tam_tarih(datetime(2026, 10, 20)), date(2026, 10, 20))
        self.assertIsNone(tk.tam_tarih("20.10"))
        self.assertIsNone(tk.tam_tarih("31.02.2026"))

    def test_ad_yazildigi_gibi(self):
        self.assertEqual(tk.ad_temizle("  ebru  yıldız "), "ebru yıldız")
        self.assertEqual(tk.ad_temizle("İSMAİL"), "İSMAİL")

    def test_dogrula_eksikleri_adla_yazar(self):
        kisiler, eksik = tk.dogrula([
            {"Ad Soyad": "Çağla Işıkoğlu", "Ünvan": "Uzman", "Doğum günü": "31.02", "İşe giriş tarihi": None},
        ])
        self.assertEqual(len(kisiler), 1)
        self.assertIsNone(kisiler[0]["dogum"])
        self.assertEqual(eksik, ["Çağla Işıkoğlu — doğum günü okunamadı: '31.02'"])

    def test_bos_satir_atlanir_ad_yok_eksik(self):
        kisiler, eksik = tk.dogrula([
            {"Ad Soyad": None, "Ünvan": None, "Doğum günü": None, "İşe giriş tarihi": None},
            {"Ad Soyad": " ", "Ünvan": "Uzman", "Doğum günü": "15.10", "İşe giriş tarihi": None},
        ])
        self.assertEqual(kisiler, [])
        self.assertEqual(eksik, ["3. satır — ad yok"])

    def test_tekrarli_satir_tek_kisi(self):
        s = {"Ad Soyad": "Ömer Şükrü Güneş", "Ünvan": "Müdür", "Doğum günü": "01.01", "İşe giriş tarihi": None}
        kisiler, eksik = tk.dogrula([s, dict(s, **{"Ad Soyad": "ömer  şükrü güneş"})])
        self.assertEqual(len(kisiler), 1)
        self.assertTrue(any("tekrarlı satır" in e for e in eksik))

    def test_29_subat(self):
        k = [{"ad": "Ece Çınar", "unvan": "", "dogum": (29, 2), "giris": None}]
        self.assertEqual(len(tk.bugunun_tebrikleri(k, [], date(2027, 2, 28))), 1)
        self.assertEqual(tk.bugunun_tebrikleri(k, [], date(2028, 2, 28)), [])
        self.assertEqual(len(tk.bugunun_tebrikleri(k, [], date(2028, 2, 29))), 1)

    def test_hos_geldin_yalniz_ilk_gun(self):
        k = [{"ad": "Ece Çınar", "unvan": "Uzman", "dogum": None, "giris": date(2026, 10, 20)}]
        t = tk.bugunun_tebrikleri(k, [], date(2026, 10, 20))
        self.assertEqual([x["tur"] for x in t], ["hos_geldin"])
        self.assertEqual(tk.bugunun_tebrikleri(k, [], date(2027, 10, 20)), [])

    def test_bayram_ilk_gun(self):
        b = [{"ad": "Ramazan Bayramı", "baslangic": "2027-03-20", "tr": "t", "en": "e", "sablon": "s.png"}]
        t = tk.bugunun_tebrikleri([], b, date(2027, 3, 20))
        self.assertEqual(t[0]["tur"], "bayram")
        self.assertEqual(t[0]["bayram"]["ad"], "Ramazan Bayramı")
        self.assertEqual(tk.bugunun_tebrikleri([], b, date(2027, 3, 21)), [])
        self.assertIsNone(tk.bayram_bugun(b, date(2027, 3, 21)))

    def test_sira(self):
        b = [{"ad": "B", "baslangic": "2026-10-20", "tr": "", "en": "", "sablon": ""}]
        k = [{"ad": "Zeynep", "unvan": "", "dogum": (20, 10), "giris": None},
             {"ad": "Ahmet", "unvan": "", "dogum": (20, 10), "giris": None},
             {"ad": "Mert", "unvan": "", "dogum": None, "giris": date(2026, 10, 20)}]
        t = tk.bugunun_tebrikleri(k, b, date(2026, 10, 20))
        self.assertEqual([(x["tur"], x["ad"]) for x in t],
                         [("bayram", ""), ("hos_geldin", "Mert"), ("dogum_gunu", "Ahmet"), ("dogum_gunu", "Zeynep")])

    def test_xlsx_oku_eksik_sutun(self):
        yol = _xlsx(["Ad Soyad", "Doğum günü", "İşe giriş tarihi"], [["Ece Çınar", "15.10", None]])
        with self.assertRaises(ValueError) as c:
            tk.xlsx_oku(yol)
        self.assertIn("eksik sütun: Ünvan", str(c.exception))

    def test_xlsx_oku_baslik_esnek(self):
        yol = _xlsx([" ad soyad ", "ÜNVAN", "doğum GÜNÜ", "işe giriş tarihi"],
                    [["Ece Çınar", "Uzman", "15.10", None]])
        s = tk.xlsx_oku(yol)
        self.assertEqual(s[0]["Ad Soyad"], "Ece Çınar")
        self.assertEqual(s[0]["Ünvan"], "Uzman")


if __name__ == "__main__":
    unittest.main()
