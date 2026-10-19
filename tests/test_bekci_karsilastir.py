"""Bekçi karşılaştırma aracı: aynı fikstürü birden çok yola verip kararları yan yana koyar.

Amaç ölçmek, karar vermek değil. Araç hiçbir dosyaya yazmaz — `durum.json`'a da,
koşu kaydına da dokunmaz; `bekci.denetle` bilerek ÇAĞRILMAZ.

python3 -m unittest discover -s tests
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import bekci  # noqa: E402
import bekci_karsilastir as bk  # noqa: E402


class FiksturTesti(unittest.TestCase):
    def test_sekiz_fikstur_var_ve_hepsi_diskte(self):
        self.assertEqual(len(bk.FIKSTURLER), 8)
        for f in bk.FIKSTURLER:
            with self.subTest(fikstur=f["ad"]):
                self.assertTrue((bk.FIKSTUR_DIZINI / f["dosya"]).is_file(), f["dosya"])

    def test_hasta_ad_soyadi_fiksturu_kabul_bekler(self):
        """ANAYASA §2 revize 19.10.2026: ad soyad ihlal değil; ön kontrol de onu yakalamaz."""
        f = next(f for f in bk.FIKSTURLER if f["ad"] == "hasta-ad-soyadi")
        self.assertEqual(f["beklenen"], "kabul")
        self.assertEqual(bekci.on_kontrol((bk.FIKSTUR_DIZINI / f["dosya"]).read_text(encoding="utf-8")), [])

    def test_beklenen_degerler_sadece_kabul_veya_red(self):
        for f in bk.FIKSTURLER:
            self.assertIn(f["beklenen"], ("kabul", "red"), f["ad"])


class OnKontrolTesti(unittest.TestCase):
    """Ön kontrol LLM'siz çalışır: yakaladığı kayıt modele HİÇ gitmez."""

    def test_eposta_telefon_ve_bos_kayit_llm_cagirmadan_red_olur(self):
        with mock.patch.object(bk.bekci, "nim_sor") as n, \
             mock.patch.object(bk.bekci, "haiku_sor") as h, \
             mock.patch.object(bk.bekci, "openai_sor") as o:
            satirlar = bk.calistir(["nim"], {"NVIDIA_API_KEY": "nvapi-x"})
        onkontrol = {s["ad"]: s for s in satirlar if s["on_kontrol"]}
        self.assertEqual(sorted(onkontrol), ["bos", "eposta-sizmis", "telefon-sizmis"])
        for s in onkontrol.values():
            self.assertEqual(s["sonuclar"]["nim"], "red")
        self.assertEqual(n.call_count, 5, "ön kontrolü geçen beş fikstür modele gitmeli")
        h.assert_not_called()
        o.assert_not_called()


class TabloTesti(unittest.TestCase):
    def _satirlar(self, kararlar):
        with mock.patch.object(bk.bekci, "nim_sor", side_effect=[{"karar": k} for k in kararlar]):
            return bk.calistir(["nim"], {"NVIDIA_API_KEY": "nvapi-x"})

    def test_beklenenle_uyusan_satir_isaretlenmez(self):
        satirlar = self._satirlar(["kabul", "red", "red", "red", "kabul"])
        self.assertTrue(all(s["sapma"] is False for s in satirlar), [s["ad"] for s in satirlar if s["sapma"]])

    def test_sapan_satir_isaretlenir(self):
        satirlar = self._satirlar(["red", "red", "red", "red", "kabul"])   # temiz'e yanlışlıkla red
        sapanlar = [s["ad"] for s in satirlar if s["sapma"]]
        self.assertEqual(sapanlar, ["temiz"])

    def test_tablo_her_fikstur_icin_satir_basar(self):
        metin = bk.tablo(self._satirlar(["kabul", "red", "red", "red", "kabul"]), ["nim"])
        for f in bk.FIKSTURLER:
            self.assertIn(f["ad"], metin)
        self.assertIn("beklenen", metin)


if __name__ == "__main__":
    unittest.main()
