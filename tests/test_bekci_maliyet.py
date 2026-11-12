"""Denetçi'nin kendi maliyeti koşu kaydına yazılır; soru bütçesine ve gün tavanına sayılır."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import soru_kaydi as sk  # noqa: E402

KABUL = {"karar": "kabul", "gerekce": "kaynaklı", "ihlal_edilen_kural": None,
         "kontrol": {"kaynak": "gecti", "hesap": "gecti", "tutarlilik": "gecti"}}


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "ANAYASA.md").write_text("anayasa", encoding="utf-8")
        d = self.kok / "takimlar" / "x"
        (d / "kosu").mkdir(parents=True)
        (d / "kurallar.md").write_text("kurallar", encoding="utf-8")
        self.kosu = d / "kosu" / "2026-11-12-1200.md"
        self.kosu.write_text("# Koşu\nveri okundu\n", encoding="utf-8")
        y = mock.patch.object(ayar, "KOK", self.kok)
        y.start()
        self.addCleanup(y.stop)

    def denetle(self, karar):
        with mock.patch.object(bekci, "llm_karari", return_value=karar):
            return bekci.denetle(self.kok, "x", self.kosu)

    def kayit(self):
        return self.kosu.read_text(encoding="utf-8")


class BekciMaliyetTesti(Kurulum):
    def test_kaydet_maliyet_satiri_yazar(self):
        self.denetle({**KABUL, "maliyet": 0.3})
        self.assertIn("- denetçi maliyeti: 0.300 USD", self.kayit())
        satir = (self.kok / "takimlar" / "bekci-telemetri.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        self.assertEqual(json.loads(satir)["maliyet"], 0.3)

    def test_atlandi_maliyeti_de_yazilir(self):
        self.denetle({"karar": "atlandi", "gerekce": "… yedek bekçi JSON döndürmedi",
                      "ihlal_edilen_kural": None, "maliyet": 0.75})
        self.assertIn("- denetçi maliyeti: 0.750 USD", self.kayit())

    def test_maliyet_yoksa_satir_yok(self):
        self.kosu.write_text("# Koşu\nanahtar sk-gizli123456\n", encoding="utf-8")
        self.denetle(KABUL)
        self.assertNotIn("denetçi maliyeti", self.kayit())

    def test_iki_denetim_toplanir(self):
        self.denetle({**KABUL, "maliyet": 0.3})
        self.denetle({**KABUL, "maliyet": 0.45})
        self.assertAlmostEqual(bekci.denetim_maliyeti(self.kosu), 0.75)

    def test_dosya_yoksa_sifir(self):
        self.assertEqual(bekci.denetim_maliyeti(self.kok / "yok.md"), 0.0)


class SayimTesti(Kurulum):
    def test_gunluk_maliyet_denetciyi_sayar(self):
        self.kosu.write_text("- maliyet: 1.000 USD · tur: 3\n- denetçi maliyeti: 0.300 USD\n", encoding="utf-8")
        self.assertAlmostEqual(ayar.gunluk_maliyet(self.kok, "2026-11-12"), 1.3)

    def test_harcanan_denetciyi_sayar(self):
        metin = ("# Soru s\n- soru: x\n\n## Dağıtım\n- maliyet: 0.004 USD\n\n"
                 "## Denetçi\n- maliyet: 1.200 USD\n- denetçi maliyeti: 0.750 USD\n\n"
                 "## CEO — karar: onay\n- maliyet: 0.400 USD\n")
        self.assertAlmostEqual(sk.harcanan(metin), 2.354)

    def test_metindeki_maliyeti_sayilmaz(self):
        self.kosu.write_text("kampanya maliyeti: 500 USD\n", encoding="utf-8")
        self.assertEqual(ayar.gunluk_maliyet(self.kok, "2026-11-12"), 0)


if __name__ == "__main__":
    unittest.main()
