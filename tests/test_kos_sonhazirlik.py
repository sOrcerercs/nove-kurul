"""sonhazirlik: ajandan SONRA sürücüde koşar; hatası koşuyu düşürmez.

onhazirlik'in aynası — ikisi aynı ad türetmesini paylaşır, yönleri terstir.
python3 -m unittest discover -s tests
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import kos  # noqa: E402


class SonhazirlikTesti(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "takimlar" / "t").mkdir(parents=True)

    def test_bos_liste_hicbir_sey_yapmaz(self):
        self.assertEqual(kos.sonhazirlik_kos("t", [], kok=self.kok), [])

    def test_basarili_komut_tamam_doner(self):
        sonuc = kos.sonhazirlik_kos("t", ["python3 -c \"print('ok')\""], kok=self.kok)
        self.assertEqual(len(sonuc), 1)
        self.assertTrue(sonuc[0]["tamam"], sonuc[0]["neden"])

    def test_dusen_komut_kosuyu_dusurmez_sebep_doner(self):
        """Sessiz düşme yok (ANAYASA §2) ama koşu da patlamaz."""
        sonuc = kos.sonhazirlik_kos("t", ["python3 -c \"raise SystemExit(3)\""], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("3", sonuc[0]["neden"])

    def test_olmayan_komut_istisna_firlatmaz(self):
        sonuc = kos.sonhazirlik_kos("t", ["boyle-bir-komut-yok --x"], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIsNotNone(sonuc[0]["neden"])

    def test_sure_tavani_asilirsa_yakalanir(self):
        sonuc = kos.sonhazirlik_kos("t", ["python3 -c \"import time; time.sleep(5)\""],
                                    kok=self.kok, tavan_sn=1)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("süre", sonuc[0]["neden"])

    def test_ad_onhazirlik_ile_ayni_kuraldan_turer(self):
        sonuc = kos.sonhazirlik_kos("t", ["python3 bin/karar_defter.py --devral"], kok=self.kok)
        self.assertEqual(sonuc[0]["ad"], "karar_defter")

    def test_dengesiz_tirnak_istisna_firlatmaz_sebep_doner(self):
        """shlex.split dengesiz tırnakta ValueError atar — kos() bunu yutmalı."""
        sonuc = kos.sonhazirlik_kos("t", ['echo "kapanmamis'], kok=self.kok)
        self.assertEqual(len(sonuc), 1)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIsNotNone(sonuc[0]["neden"])

    def test_bos_komut_istisna_firlatmaz_sebep_doner(self):
        """subprocess.run([]) IndexError atar — boş komut önce yakalanmalı."""
        sonuc = kos.sonhazirlik_kos("t", [""], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIsNotNone(sonuc[0]["neden"])

    def test_bosluk_komut_istisna_firlatmaz_sebep_doner(self):
        sonuc = kos.sonhazirlik_kos("t", ["   "], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIsNotNone(sonuc[0]["neden"])


class OnhazirlikGuvenlikTesti(unittest.TestCase):
    """onhazirlik_kos aynı hatalı-komut deliğini paylaşıyordu — burada da kapatıldı.

    tests/test_kos_onhazirlik.py'ye dokunulmaz; bu sınıf onun yanına, bozuk komutlar
    için aynı sözleşmeyi (istisna yok, `**Hazırlanamadı:**` dosyası) sınar.
    """
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "takimlar" / "t").mkdir(parents=True)

    def _oku(self, ad):
        return (self.kok / "takimlar" / "t" / "veri" / (ad + ".txt")).read_text(encoding="utf-8")

    def test_dengesiz_tirnak_istisna_firlatmaz_dosyaya_yazar(self):
        sonuc = kos.onhazirlik_kos("t", ['echo "kapanmamis'], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("**Hazırlanamadı:**", self._oku(sonuc[0]["ad"]))

    def test_bos_komut_istisna_firlatmaz_dosyaya_yazar(self):
        sonuc = kos.onhazirlik_kos("t", [""], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("**Hazırlanamadı:**", self._oku(sonuc[0]["ad"]))

    def test_bosluk_komut_istisna_firlatmaz_dosyaya_yazar(self):
        sonuc = kos.onhazirlik_kos("t", ["   "], kok=self.kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("**Hazırlanamadı:**", self._oku(sonuc[0]["ad"]))


class SiraTesti(unittest.TestCase):
    def test_sonhazirlik_ajandan_sonra_cagrilir(self):
        """kos() gövdesinde sonhazirlik çağrısı _claude_kos'tan SONRA geçer.

        `\\b` sınırı `onhazirlik_kos(` deseninin `sonhazirlik_kos(` içine düşmesini önler.
        """
        kaynak = (KOK / "bin" / "kos.py").read_text(encoding="utf-8")
        govde = kaynak[kaynak.index("def kos("):]
        onhaz = re.search(r"\bonhazirlik_kos\(", govde)
        sonhaz = re.search(r"\bsonhazirlik_kos\(", govde)
        claude_konumu = govde.index("_claude_kos(")
        self.assertIsNotNone(onhaz, "onhazirlik_kos çağrısı bulunamadı")
        self.assertIsNotNone(sonhaz, "sonhazirlik_kos çağrısı bulunamadı")
        self.assertLess(claude_konumu, sonhaz.start(),
                        "sonhazirlik ajandan önce çağrılıyor")
        self.assertLess(onhaz.start(), claude_konumu,
                        "onhazirlik ajandan sonra çağrılıyor")


if __name__ == "__main__":
    unittest.main()
