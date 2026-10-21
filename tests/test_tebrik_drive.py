import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import tebrik_drive  # noqa: E402

KIMLIK = "1AbCdEfGizliDosyaKimligi"
ANAHTAR = "/gizli/yol/hizmet-hesabi.json"
SHEETS = "application/vnd.google-apps.spreadsheet"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class _Istek:
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        if isinstance(self._sonuc, Exception):
            raise self._sonuc
        return self._sonuc


class SahteServis:
    def __init__(self, mime=XLSX, icerik=b"PK-sahte", hata=None):
        self.mime, self.icerik, self.hata = mime, icerik, hata
        self.cagrilar = []
        self.ortak = []

    def files(self):
        return self

    def get(self, fileId, fields, supportsAllDrives=False):
        self.cagrilar.append(("get", fileId))
        self.ortak.append(("get", supportsAllDrives))
        return _Istek(self.hata or {"mimeType": self.mime})

    def export_media(self, fileId, mimeType, supportsAllDrives=False):
        self.cagrilar.append(("export_media", mimeType))
        self.ortak.append(("export_media", supportsAllDrives))
        return _Istek(self.icerik)

    def get_media(self, fileId, supportsAllDrives=False):
        self.cagrilar.append(("get_media", fileId))
        self.ortak.append(("get_media", supportsAllDrives))
        return _Istek(self.icerik)


def _ortam():
    return {"TEBRIK_DRIVE_DOSYA": KIMLIK, "TEBRIK_DRIVE_ANAHTAR": ANAHTAR}


class DriveTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self.gecici.cleanup)
        self.hedef = Path(self.gecici.name) / "alt" / "tablo.xlsx"

    def test_eksik_anahtar(self):
        with self.assertRaises(RuntimeError) as c:
            tebrik_drive.tablo_indir({"TEBRIK_DRIVE_ANAHTAR": ANAHTAR}, self.hedef,
                                     servis_kur=lambda a, k: SahteServis())
        self.assertIn("TEBRIK_DRIVE_DOSYA", str(c.exception))
        self.assertNotIn(ANAHTAR, str(c.exception))

    def test_bos_anahtar_ve_yalniz_bosluk(self):
        for ortam in ({"TEBRIK_DRIVE_DOSYA": KIMLIK},
                      {"TEBRIK_DRIVE_DOSYA": KIMLIK, "TEBRIK_DRIVE_ANAHTAR": "   "}):
            with self.assertRaises(RuntimeError) as c:
                tebrik_drive.tablo_indir(ortam, self.hedef, servis_kur=lambda a, k: SahteServis())
            self.assertIn("TEBRIK_DRIVE_ANAHTAR", str(c.exception))
            self.assertNotIn(ANAHTAR, str(c.exception))

    def test_ortak_drive_bayragi_gider(self):
        for mime, cagri in ((XLSX, "get_media"), (SHEETS, "export_media")):
            s = SahteServis(mime=mime)
            tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
            self.assertEqual(sorted(s.ortak), sorted([("get", True), (cagri, True)]))

    def test_http_durumu_mesajda(self):
        class HttpHata(Exception):
            resp = type("R", (), {"status": 404})()
        s = SahteServis(hata=HttpHata(f"{KIMLIK} {ANAHTAR}"))
        with self.assertRaises(RuntimeError) as c:
            tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertEqual(str(c.exception), "Drive okunamadı: HttpHata 404")

    def test_yazim_atomik_eski_dosya_bozulmaz(self):
        self.hedef.parent.mkdir(parents=True)
        self.hedef.write_bytes(b"ESKI")
        s = SahteServis(icerik=b"YENI")
        from unittest import mock
        with mock.patch.object(Path, "replace", side_effect=OSError("disk")):
            with self.assertRaises(RuntimeError):
                tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertEqual(self.hedef.read_bytes(), b"ESKI")
        tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertEqual(self.hedef.read_bytes(), b"YENI")
        self.assertEqual([y.name for y in self.hedef.parent.iterdir()], ["tablo.xlsx"])

    def test_sahte_servisle_indirir(self):
        s = SahteServis(icerik=b"PK-tablo-baytlari")
        yol = tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertEqual(yol, self.hedef)
        self.assertEqual(self.hedef.read_bytes(), b"PK-tablo-baytlari")
        self.assertIn(("get_media", KIMLIK), s.cagrilar)

    def test_sheets_ise_xlsx_disa_aktarir(self):
        s = SahteServis(mime=SHEETS)
        tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertIn(("export_media", XLSX), s.cagrilar)
        self.assertFalse(any(c[0] == "get_media" for c in s.cagrilar))

    def test_hata_mesaji_kimlik_sizdirmaz(self):
        s = SahteServis(hata=ConnectionError(f"404 {KIMLIK} {ANAHTAR}"))
        with self.assertRaises(RuntimeError) as c:
            tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=lambda a, k: s)
        self.assertIn("ConnectionError", str(c.exception))
        self.assertNotIn(KIMLIK, str(c.exception))
        self.assertNotIn(ANAHTAR, str(c.exception))
        self.assertFalse(self.hedef.exists())

    def test_servis_kurma_hatasi_da_sizdirmaz(self):
        def kur(a, k):
            raise FileNotFoundError(a)
        with self.assertRaises(RuntimeError) as c:
            tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=kur)
        self.assertNotIn(ANAHTAR, str(c.exception))

    def test_kapsam_yalniz_okuma(self):
        alinan = {}

        def kur(anahtar, kapsamlar):
            alinan["anahtar"], alinan["kapsamlar"] = anahtar, kapsamlar
            return SahteServis()
        tebrik_drive.tablo_indir(_ortam(), self.hedef, servis_kur=kur)
        self.assertEqual(alinan["kapsamlar"], ["https://www.googleapis.com/auth/drive.readonly"])
        self.assertEqual(alinan["anahtar"], ANAHTAR)


if __name__ == "__main__":
    unittest.main()
