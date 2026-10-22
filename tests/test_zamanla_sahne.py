"""Panel sunucusunun launchd kaydı — launchctl çağrılmaz, yalnız plist içeriği sınanır.

Sabah/akşam tetikleri takvimlidir: belirli saatte bir kez koşar, biter. Panel sunucusu
sürekli iştir: açılışta başlar ve ayakta kalır. İkisi aynı kurucudan çıkar ama plist
şekilleri farklıdır — bu dosya o farkı sabitler.

python3 -m unittest discover -s tests
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import zamanla  # noqa: E402


def _sahne_isi():
    return {i["ad"]: i for i in zamanla.SUREKLI}["sahne"]


class KayitTesti(unittest.TestCase):
    def test_sahne_surekli_isler_arasinda(self):
        self.assertIn("sahne", [i["ad"] for i in zamanla.SUREKLI])

    def test_tum_isler_takvimli_ve_surekliyi_birlestirir(self):
        # This is the single place the complete job list is asserted globally.
        # When adding a new job (TETIKLER or SUREKLI), update this list and only this file.
        adlar = [i["ad"] for i in zamanla.TUM_ISLER]
        self.assertEqual(sorted(adlar), ["aksam", "ilerlet", "rapor", "sabah", "sahne"])

    def test_sahnenin_etiketi_kokten_turer(self):
        self.assertNotEqual(zamanla.etiket("sahne", "/bir/kok"),
                            zamanla.etiket("sahne", "/baska/kok"))


class PlistSekliTesti(unittest.TestCase):
    """Sürekli iş: açılışta başlar, düşerse kalkar, takvimi yoktur."""

    def setUp(self):
        self.icerik = zamanla.plist_icerigi(_sahne_isi(), kok="/tmp/kok", python="/usr/bin/python3")

    def test_acilista_baslar_ve_ayakta_kalir(self):
        self.assertTrue(self.icerik["RunAtLoad"])
        self.assertTrue(self.icerik["KeepAlive"])

    def test_takvim_araligi_yok(self):
        self.assertNotIn("StartCalendarInterval", self.icerik)

    def test_sahne_betigini_porta_gore_cagirir(self):
        argv = self.icerik["ProgramArguments"]
        self.assertTrue(argv[1].endswith("bin/sahne.py"), argv[1])
        self.assertIn("--port", argv)
        self.assertIn(str(zamanla.SAHNE_PORTU), argv)

    def test_etiket_ve_calisma_dizini_koke_bagli(self):
        self.assertEqual(self.icerik["Label"], zamanla.etiket("sahne", "/tmp/kok"))
        self.assertEqual(self.icerik["WorkingDirectory"], "/tmp/kok")


class TakvimliBozulmadiTesti(unittest.TestCase):
    """Sabah/akşam eski davranışını korur: kurulumda koşmaz, takvimi vardır."""

    def setUp(self):
        self.icerik = zamanla.plist_icerigi(zamanla.TETIKLER[0], kok="/tmp/kok",
                                            python="/usr/bin/python3")

    def test_kurulumda_kosmaz(self):
        self.assertFalse(self.icerik["RunAtLoad"])
        self.assertNotIn("KeepAlive", self.icerik)

    def test_takvimi_ayardan_turer(self):
        self.assertEqual(self.icerik["StartCalendarInterval"],
                         {"Hour": zamanla.TETIKLER[0]["saat"], "Minute": zamanla.TETIKLER[0]["dakika"]})

    def test_gunluk_betigini_cagirir(self):
        argv = self.icerik["ProgramArguments"]
        self.assertTrue(argv[1].endswith("bin/gunluk.py"), argv[1])
        self.assertIn("--sabah", argv)


def _is(ad):
    return {i["ad"]: i for i in zamanla.TUM_ISLER}[ad]


class RaporIlerletTesti(unittest.TestCase):
    def test_rapor_isi_hafta_ici(self):
        icerik = zamanla.plist_icerigi(_is("rapor"), kok="/tmp/kok", python="/usr/bin/python3")
        self.assertEqual(icerik["StartCalendarInterval"],
                         [{"Weekday": g, "Hour": 9, "Minute": 30} for g in range(1, 6)])
        self.assertIn("--rapor", icerik["ProgramArguments"])
        self.assertTrue(icerik["ProgramArguments"][1].endswith("bin/gunluk.py"))
        self.assertFalse(icerik["RunAtLoad"])
        self.assertNotIn("KeepAlive", icerik)
        self.assertNotIn("StartInterval", icerik)

    def test_ilerlet_isi_aralikli(self):
        icerik = zamanla.plist_icerigi(_is("ilerlet"), kok="/tmp/kok", python="/usr/bin/python3")
        self.assertEqual(icerik["StartInterval"], 600)
        self.assertNotIn("StartCalendarInterval", icerik)
        self.assertFalse(icerik["RunAtLoad"])
        self.assertNotIn("KeepAlive", icerik)
        self.assertIn("--ilerlet", icerik["ProgramArguments"])
        self.assertTrue(icerik["ProgramArguments"][1].endswith("bin/gunluk.py"))

    def test_ne_zaman_metinleri(self):
        self.assertEqual(zamanla._ne_zaman(_is("rapor")), "hafta içi 09:30")
        self.assertEqual(zamanla._ne_zaman(_is("ilerlet")), "her 10 dk")
        self.assertEqual(zamanla._ne_zaman(zamanla.TETIKLER[0]),
                         f"her gün {zamanla.TETIKLER[0]['saat']:02d}:00")

    def test_kuru_metni_yeni_isleri_basar(self):
        cikti = io.StringIO()
        with redirect_stdout(cikti):
            self.assertEqual(zamanla.main(["--kuru"]), 0)
        metin = cikti.getvalue()
        self.assertIn("rapor · hafta içi 09:30", metin)
        self.assertIn("ilerlet · her 10 dk", metin)
        self.assertIn("<key>StartInterval</key>", metin)


if __name__ == "__main__":
    unittest.main()
