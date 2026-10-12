"""Soru kaydı — bir sorunun bütün hayatının yazıldığı dosya (NOVE-KURULUM.md §2).

`sirket-log/sorular/<soru-id>.md`. Q&A Danışmanı açar, İş Dağıtımcı `## Dağıtım`, sürücü `## Denetçi`,
CEO `## CEO — karar: …` bölümünü ekler. Bölümler yalnız eklenir; değişen tek satır başlıktaki `- durum:`.

python3 -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import soru_kaydi as sk  # noqa: E402

BASLIK = """# Soru 20261012-1000-abcd
- soran: uye@nove.group (rol: kurul)
- zaman: 2026-10-12T10:00:00+03:00
- soru: Q3 bütçe sapmasının ana nedenleri neler?
- bütçe: 5,00 USD
- durum: alındı
"""


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        self.yol = sk.yol("20261012-1000-abcd", self.kok)
        self.yol.parent.mkdir(parents=True)
        self.yol.write_text(BASLIK, encoding="utf-8")


class AlanTesti(Kurulum):
    def test_baslik_alanlari_okunur(self):
        metin = self.yol.read_text(encoding="utf-8")
        self.assertEqual(sk.alan(metin, "soru"), "Q3 bütçe sapmasının ana nedenleri neler?")
        self.assertEqual(sk.alan(metin, "durum"), "alındı")
        self.assertIsNone(sk.alan(metin, "yok"))

    def test_bolumdeki_ayni_adli_satir_baslik_alani_sayilmaz(self):
        sk.bolum_ekle(self.yol, "## Dağıtım\n- durum: başka\n")
        self.assertEqual(sk.alan(self.yol.read_text(encoding="utf-8"), "durum"), "alındı")

    def test_bolum_icinden_alan_okunur(self):
        sk.bolum_ekle(self.yol, "## Dağıtım\n- danışman: Finans\n")
        self.assertEqual(sk.bolum_alani(self.yol.read_text(encoding="utf-8"), "## Dağıtım", "danışman"), "Finans")


class DurumTesti(Kurulum):
    def test_durum_yalniz_baslik_satirinda_degisir(self):
        sk.bolum_ekle(self.yol, "## Dağıtım\n- durum: dokunma\n")
        sk.durum_yaz(self.yol, "danışmanda")
        metin = self.yol.read_text(encoding="utf-8")
        self.assertEqual(sk.alan(metin, "durum"), "danışmanda")
        self.assertIn("- durum: dokunma", metin)

    def test_bolum_ekle_sona_ekler_ve_bos_satirla_ayirir(self):
        sk.bolum_ekle(self.yol, "## Dağıtım\n- danışman: Finans")
        metin = self.yol.read_text(encoding="utf-8")
        self.assertTrue(metin.startswith(BASLIK))
        self.assertTrue(metin.endswith("\n## Dağıtım\n- danışman: Finans\n"))


class KararlarTesti(unittest.TestCase):
    def test_bolumler_sirayla(self):
        metin = (BASLIK + "\n## Denetçi\n- karar: **red**\n\n## Denetçi\n- karar: **kabul**\n"
                 "\n## CEO — karar: red\n- tur: 1/2\n\n## CEO — kontrol yapılmadı\n")
        self.assertEqual(sk.kararlar(metin), [("denetci", "red"), ("denetci", "kabul"), ("ceo", "red"),
                                              ("ceo", "yapilmadi")])


class HarcananTesti(unittest.TestCase):
    def test_bolumlerdeki_maliyet_satirlari_toplanir(self):
        metin = (BASLIK + "\n## Dağıtım\n- maliyet: 0.020 USD\n\n## Denetçi\n- maliyet: 1.500 USD\n"
                 "\n## CEO — karar: red\n- maliyet: 0.410 USD\n")
        self.assertAlmostEqual(sk.harcanan(metin), 1.93)

    def test_bolum_yoksa_sifir(self):
        self.assertEqual(sk.harcanan(BASLIK), 0.0)



class BolumTesti(unittest.TestCase):
    def test_son_bolumun_govdesi(self):
        metin = (BASLIK + "\n## CEO — karar: red\n- tur: 1/2\n- bulgular:\n  1. eski\n"
                 "\n## Denetçi\n- karar: **kabul**\n\n## CEO — karar: red\n- tur: 2/2\n- bulgular:\n  1. yeni\n  2. ikinci\n")
        self.assertEqual(sk.bolum(metin, "## CEO — karar: red"), "- tur: 2/2\n- bulgular:\n  1. yeni\n  2. ikinci")

    def test_bolum_yoksa_none(self):
        self.assertIsNone(sk.bolum(BASLIK, "## Dağıtım"))


if __name__ == "__main__":
    unittest.main()
