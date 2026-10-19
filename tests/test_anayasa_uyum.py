"""ANAYASA §2 revizesi (19.10.2026): hasta/müşteri ad soyadı yazılabilir; telefon, e-posta, TC kimlik no yasak.

Kuralı tekrar eden her belge ve istem aynı şeyi söylemeli — biri eski yasağı taşırsa danışman ya da Denetçi
çelişik kural görür (docs/superpowers/plans/2026-10-19-patient-name-policy.md).
python3 -m unittest discover -s tests
"""
import re
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import bekci  # noqa: E402
import formdan_takim  # noqa: E402

ESKI_YASAK = re.compile(r"hasta(/| ve | ya da )müşteri adı", re.IGNORECASE)
BELGELER = ("CLAUDE.md", "sirket/AJAN-KIMLIGI.md", "NOVE-KURULUM.md", "formlar/DANISMAN-FORMU.md",
            "sirket/DENETCI.md")


class AnayasaUyumTesti(unittest.TestCase):
    def test_anayasa_ad_soyadi_serbest_birakir(self):
        metin = (KOK / "ANAYASA.md").read_text(encoding="utf-8")
        self.assertIn("Hasta ve müşterinin adı soyadı yazılabilir", metin)
        self.assertIn("herkese açık bir depoya girmez", metin)

    def test_belgeler_eski_yasagi_tasimaz(self):
        """5 belgenin 5'i."""
        self.assertEqual(len(BELGELER), 5)
        for yol in BELGELER:
            with self.subTest(belge=yol):
                self.assertIsNone(ESKI_YASAK.search((KOK / yol).read_text(encoding="utf-8")))

    def test_denetci_istemi_ad_soyadi_ihlal_saymaz(self):
        istem = bekci._istem("anayasa", "kurallar", "kayıt")
        self.assertIsNone(ESKI_YASAK.search(istem))
        self.assertIn("hasta/müşteri ad soyadı ihlal değildir", istem)
        self.assertIn("hasta/müşteri telefonu/e-postası/TC kimlik no", istem)

    def test_kurallar_sablonu_ad_soyadi_serbest(self):
        self.assertIsNone(ESKI_YASAK.search(formdan_takim.HER_ZAMAN_YASAK))
        self.assertIn("adı soyadı yazılabilir", formdan_takim.HER_ZAMAN_YASAK)
        self.assertIn("TC kimlik no yazılmaz", formdan_takim.HER_ZAMAN_YASAK)


if __name__ == "__main__":
    unittest.main()
