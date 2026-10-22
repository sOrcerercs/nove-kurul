"""`gunluk.py --rapor` — zamanlı Kalite raporu (spec: kalite-gunluk-rapor, Görev 2)."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import gunluk  # noqa: E402
import soru_kaydi as sk  # noqa: E402

TR = timezone(timedelta(hours=3))
SALI = datetime(2026, 10, 20, 9, 30, tzinfo=TR)
CUMARTESI = datetime(2026, 10, 24, 9, 30, tzinfo=TR)
SAHTE_DAGIT = {"kararlar": [], "zincir": []}


class RaporTesti(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        dizin = self.kok / "takimlar" / "kalite"
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text("---\nname: kalite\ndescription: Kalite\n---\n", encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps({"takim": "kalite", "kuyruk": []}), encoding="utf-8")

    def kayit(self, sid):
        return sk.yol(sid, self.kok)

    def test_rapor_acar_ve_dagitir(self):
        with mock.patch.object(gunluk.dagitici, "dagit", return_value=SAHTE_DAGIT) as dagit:
            sonuc = gunluk.rapor(self.kok, SALI)
        dagit.assert_called_once()
        self.assertEqual(sonuc["acilan"][0]["sonuc"], "acildi")
        metin = self.kayit("rapor-kalite-20261020").read_text(encoding="utf-8")
        self.assertEqual(sk.alan(metin, "aralik"), "2026-10-19..2026-10-19")
        self.assertEqual(sk.alan(metin, "karsilastir"), "2026-10-16..2026-10-16")
        self.assertIn("20.10.2026 (Salı) günlük kalite raporu:", sk.alan(metin, "soru"))

    def test_utc_gecesi_istanbul_gunu(self):
        utc = datetime(2026, 10, 19, 21, 30, tzinfo=timezone.utc)   # İstanbul: salı 20.10 00:30
        with mock.patch.object(gunluk.dagitici, "dagit", return_value=SAHTE_DAGIT):
            gunluk.rapor(self.kok, utc)
        metin = self.kayit("rapor-kalite-20261020").read_text(encoding="utf-8")
        self.assertEqual(sk.alan(metin, "aralik"), "2026-10-19..2026-10-19")

    def test_ikinci_cagri_tekrar_acmaz(self):
        with mock.patch.object(gunluk.dagitici, "dagit", return_value=SAHTE_DAGIT):
            gunluk.rapor(self.kok, SALI)
            sonuc = gunluk.rapor(self.kok, SALI)
        self.assertEqual(sonuc["acilan"][0]["sonuc"], "var")

    def test_rapor_hafta_sonu_bos(self):
        with mock.patch.object(gunluk.dagitici, "dagit") as dagit:
            sonuc = gunluk.rapor(self.kok, CUMARTESI)
        dagit.assert_not_called()
        self.assertEqual(sonuc["acilan"], [])
        self.assertIn("hafta sonu", sonuc["atlandi"])
        self.assertFalse((self.kok / "sirket-log").exists())

    def test_tatil_gunu_bos(self):
        (self.kok / "takimlar" / "kalite" / "tatiller.json").write_text(
            json.dumps([{"tarih": "2026-10-20", "ad": "x"}]), encoding="utf-8")
        with mock.patch.object(gunluk.dagitici, "dagit") as dagit:
            sonuc = gunluk.rapor(self.kok, SALI)
        dagit.assert_not_called()
        self.assertIn("tatil", sonuc["atlandi"])

    def test_rapor_kuru_yazmaz(self):
        with mock.patch.object(gunluk.dagitici, "dagit", return_value=SAHTE_DAGIT) as dagit:
            gunluk.rapor(self.kok, SALI, kuru=True)
        self.assertTrue(dagit.call_args.kwargs["kuru"])
        self.assertFalse(self.kayit("rapor-kalite-20261020").exists())
        self.assertEqual(json.loads((self.kok / "takimlar" / "kalite" / "durum.json").read_text())["kuyruk"], [])

    def test_bozuk_tatiller_yuksek_sesle(self):
        (self.kok / "takimlar" / "kalite" / "tatiller.json").write_text("{bozuk", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "tatiller.json okunamadı"):
            gunluk.rapor(self.kok, SALI)
        self.assertFalse(self.kayit("rapor-kalite-20261020").exists())

    def cli(self, argv, rapor_sonucu=None, hata=None):
        out, err = io.StringIO(), io.StringIO()
        yan = {"side_effect": hata} if hata else {"return_value": rapor_sonucu}
        with mock.patch.object(gunluk, "KOK", self.kok), mock.patch.object(gunluk, "rapor", **yan), \
                redirect_stdout(out), redirect_stderr(err):
            rc = gunluk.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_cli_bayragi(self):
        sonuc = {"simdi": SALI, "gun": SALI.date(), "atlandi": None, "dagitim": SAHTE_DAGIT,
                 "acilan": [{"danisman": "kalite", "sonuc": "acildi", "soru_id": "rapor-kalite-20261020", "sebep": ""}]}
        rc, out, _ = self.cli(["--rapor"], sonuc)
        self.assertEqual(rc, 0)
        yol = self.kok / "sirket-log" / "rapor" / "2026-10-20-rapor.md"
        self.assertIn("rapor-kalite-20261020", yol.read_text(encoding="utf-8"))

    def test_cli_hafta_sonu_rc0_sebep(self):
        sonuc = {"simdi": CUMARTESI, "gun": CUMARTESI.date(), "atlandi": "hafta sonu — rapor açılmadı",
                 "acilan": [], "dagitim": None}
        rc, out, _ = self.cli(["--rapor"], sonuc)
        self.assertEqual(rc, 0)
        self.assertIn("hafta sonu", out)

    def test_cli_bozuk_tatil_rc1_tek_satir(self):
        rc, out, err = self.cli(["--rapor"], hata=ValueError("tatiller.json okunamadı: x"))
        self.assertEqual(rc, 1)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("tatiller.json okunamadı", err)

    def test_cli_reddedilen_rapor_rc1(self):
        sonuc = {"simdi": SALI, "gun": SALI.date(), "atlandi": None, "dagitim": SAHTE_DAGIT,
                 "acilan": [{"danisman": "kalite", "sonuc": "reddedildi", "sebep": "kalite kuyruğu yok"}]}
        rc, out, err = self.cli(["--rapor"], sonuc)
        self.assertEqual(rc, 1)
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("kalite kuyruğu yok", err)

    def test_cli_ikinci_cagri_sabah_raporunu_ezmez(self):
        ilk = {"simdi": SALI, "gun": SALI.date(), "atlandi": None, "dagitim": SAHTE_DAGIT,
               "acilan": [{"danisman": "kalite", "sonuc": "acildi", "soru_id": "rapor-kalite-20261020", "sebep": ""}]}
        ikinci = {**ilk, "simdi": SALI + timedelta(hours=3),
                  "acilan": [{"danisman": "kalite", "sonuc": "var", "soru_id": "rapor-kalite-20261020",
                              "sebep": "bu gün için rapor zaten açıldı"}]}
        self.cli(["--rapor"], ilk)
        self.cli(["--rapor"], ikinci)
        metin = (self.kok / "sirket-log" / "rapor" / "2026-10-20-rapor.md").read_text(encoding="utf-8")
        self.assertIn("kalite` `rapor-kalite-20261020`: acildi", metin)
        self.assertIn("12:30", metin)
        self.assertIn(": var", metin)


class IlerletTesti(unittest.TestCase):
    def test_yalniz_dagitici_calisir(self):
        with mock.patch.object(gunluk.dagitici, "dagit", return_value={"kararlar": []}) as dagit, \
                mock.patch.object(gunluk, "rapor") as rapor, mock.patch.object(gunluk, "yaz") as yaz, \
                mock.patch.object(gunluk, "sabah") as sabah:
            rc = gunluk.main(["--ilerlet"])
        self.assertEqual(rc, 0)
        dagit.assert_called_once_with(gunluk.KOK)
        rapor.assert_not_called()
        yaz.assert_not_called()
        sabah.assert_not_called()


if __name__ == "__main__":
    unittest.main()
