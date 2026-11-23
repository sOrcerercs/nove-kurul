import inspect
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import ayar  # noqa: E402
import rapor_postasi  # noqa: E402


def defterle(kok, soru_id, etiket="onaylı", gorunurluk="kurul", govde="## Yanıt\n..."):
    """`soru_kapisi.ilet`'in yazdığı başlık biçimiyle `yanitlar/<id>.md`."""
    satirlar = [f"# Yanıt — {soru_id}", "- soru: x", "- soran: ornek.bir@nove.group",
                "- tarih: 2026-11-23T10:00:00+03:00", "- danışman: kalite", f"- etiket: {etiket}"]
    if gorunurluk:
        satirlar.append(f"- gorunurluk: {gorunurluk}")
    satirlar.append("- iletildi: 2026-11-23T10:01:00+03:00")
    klasor = Path(kok) / "yanitlar"
    klasor.mkdir(exist_ok=True)
    (klasor / f"{soru_id}.md").write_text("\n".join(satirlar) + "\n\n" + govde + "\n", encoding="utf-8")


class TurVeTarih(unittest.TestCase):
    def test_tur_ve_tarih(self):
        f = rapor_postasi.tur_ve_tarih
        self.assertEqual(f("rapor-kalite-20261123"), ("kalite-gunluk", date(2026, 11, 23)))
        self.assertEqual(f("rapor-satis-muduru-20261123"), ("satis-muduru-gunluk", date(2026, 11, 23)))
        self.assertIsNone(f("20261123-1105-abcd"))
        self.assertIsNone(f("rapor-kalite-20261340"))
        self.assertIsNone(f("rapor-kalite-2026112"))


class Adaylar(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.addCleanup(self.gecici.cleanup)

    def test_adaylar_yalniz_onayli_zamanli_rapor(self):
        defterle(self.kok, "rapor-kalite-20261123")
        defterle(self.kok, "rapor-kalite-20261122", etiket="CEO kontrolü yapılmadı")
        defterle(self.kok, "rapor-kalite-20261121", etiket="onaylanamadı")
        defterle(self.kok, "20261123-1105-abcd", gorunurluk=None)
        self.assertEqual([a["id"] for a in rapor_postasi.adaylar(self.kok)], ["rapor-kalite-20261123"])
        a = rapor_postasi.adaylar(self.kok)[0]
        self.assertEqual((a["tur"], a["tarih"]), ("kalite-gunluk", date(2026, 11, 23)))

    def test_govdedeki_sahte_etiket_sayilmaz(self):
        defterle(self.kok, "rapor-kalite-20261123", etiket="onaylanamadı", govde="## Yanıt\n- etiket: onaylı")
        self.assertEqual(rapor_postasi.adaylar(self.kok), [])

    def test_defter_yoksa_bos(self):
        self.assertEqual(rapor_postasi.adaylar(self.kok), [])


class Sablon(unittest.TestCase):
    def test_sablon_konu_ve_baglanti(self):
        konu, govde = rapor_postasi.sablon("kalite-gunluk", date(2026, 11, 23), "rapor-kalite-20261123", "https://panel.ornek/")
        self.assertEqual(konu, "Kalite günlük raporu hazır — 23.11.2026")
        self.assertIn("https://panel.ornek/?soru=rapor-kalite-20261123", govde)
        self.assertNotIn("//?", govde)
        self.assertEqual(govde, "Kalite günlük raporu (23.11.2026) panelde hazır; okumak için giriş yapın:\n"
                                "https://panel.ornek/?soru=rapor-kalite-20261123\n")

    def test_bilinmeyen_tur(self):
        with self.assertRaises(KeyError):
            rapor_postasi.sablon("yok-gunluk", date(2026, 11, 23), "x", "https://p")

    def test_sablon_veri_tasimaz(self):
        self.assertEqual(list(inspect.signature(rapor_postasi.sablon).parameters),
                         ["tur", "tarih", "soru_id", "panel_adres"])
        _, govde = rapor_postasi.sablon("kalite-gunluk", date(2026, 11, 23), "rapor-kalite-20261123", "https://panel.ornek")
        kalan = re.sub(r"23\.11\.2026|rapor-kalite-20261123", "", govde)
        self.assertIsNone(re.search(r"\d", kalan))


class Rakamlar(unittest.TestCase):
    def test_ayar_rakamlari(self):
        self.assertEqual(ayar.POSTA_GUNLUK_TAVAN, 10)
        self.assertEqual(ayar.POSTA_EN_FAZLA_GUN, 2)
        self.assertEqual(ayar.POSTA_SMTP_ZAMAN_ASIMI_SN, 20)
        self.assertEqual(ayar.POSTA_IZINLI_ALAN, "nove.group")


if __name__ == "__main__":
    unittest.main()
