"""panel.js / stil.css üzerinde statik denetim (tarayıcı gerekmez)."""
import re
import unittest
from pathlib import Path

PANEL = Path(__file__).resolve().parent.parent / "panel"


class PanelStatikTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (PANEL / "panel.js").read_text(encoding="utf-8")
        cls.css = (PANEL / "stil.css").read_text(encoding="utf-8")

    def test_gercek_mod_metinleri_ve_uclari(self):
        for parca in ("Sizin için araştırılıyor", "/api/ben", "'/api/soru'", "/api/sorular/",
                      "/api/yanitlar", "YOKLAMA_MS = 10000"):
            self.assertIn(parca, self.js)

    def test_demo_yolu_yerinde(self):
        self.assertIn("has('demo')", self.js)
        self.assertIn("SEED_DEFTER", self.js)
        for ad in ("yonlendir", "adimUret", "adimGonder", "ilerle"):
            self.assertIn("function %s(" % ad, self.js)

    def test_olaylar_ucu_kullanilmaz(self):
        self.assertNotIn("/api/olaylar", self.js)

    def test_demo_kosulu_yeterince_var(self):
        self.assertGreaterEqual(len(re.findall(r"if *\(!?DEMO\)|!?DEMO &&", self.js)), 4)

    def test_cikis_sonrasi_gelen_yanit_yok_sayilir(self):
        self.assertIn("oturumNo++", self.js)
        self.assertGreaterEqual(self.js.count("oturumNo"), 10)

    def test_tekrar_sonucu_arastirilmiyorsa_dogrudan_gosterilir(self):
        self.assertIn("s.veri.durum !== 'arastiriliyor'", self.js)

    def test_defter_hatasi_gorunur(self):
        self.assertIn("Yanıt defteri yüklenemedi", self.js)
        self.assertIn("Yeniden dene", self.js)

    def test_md_kurali(self):
        self.assertRegex(self.css, r"(^|\n)\.md[\s{,]")


if __name__ == "__main__":
    unittest.main()
