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

    def files(self):
        return self

    def get(self, fileId, fields):
        self.cagrilar.append(("get", fileId))
        return _Istek(self.hata or {"mimeType": self.mime})

    def export_media(self, fileId, mimeType):
        self.cagrilar.append(("export_media", mimeType))
        return _Istek(self.icerik)

    def get_media(self, fileId):
        self.cagrilar.append(("get_media", fileId))
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
