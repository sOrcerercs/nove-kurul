"""kalite_veri.py testleri — ağ yok, veritabanı yok; bağlantı `baglan` ile enjekte edilir.

python3 -m unittest discover -s tests
"""
import io
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import kalite_veri  # noqa: E402

YASAK = re.compile(r'transcript|report"|customerName|evidence|medicalFlags')


class _SahteImlec:
    def __init__(self, sonuclar, hata_adi=None):
        self.sonuclar = sonuclar
        self.hata_adi = hata_adi
        self.sql = []
        self._son = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        if self.hata_adi and self.hata_adi in sql:
            raise PermissionError("izin yok")
        self._son = self.sonuclar.get(sql, [])

    def fetchall(self):
        return list(self._son)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _SahteBaglanti:
    def __init__(self, imlec):
        self.imlec = imlec
        self.read_only = None
        self.kapandi = False
        self.rollback_sayisi = 0

    def cursor(self):
        return self.imlec

    def rollback(self):
        self.rollback_sayisi += 1

    def close(self):
        self.kapandi = True


class SemaTesti(unittest.TestCase):
    def test_url_yoksa_hazirlanamadi_rc1(self):
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kod = kalite_veri.main(["sema"], ortam={})
        self.assertEqual(kod, 1)
        self.assertEqual(tampon.getvalue().strip(), "**Hazırlanamadı:** QA_READONLY_URL yok")

    def test_kullanim_hatasi_rc2(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as c:
            kalite_veri.main(["yok-komut"], ortam={})
        self.assertEqual(c.exception.code, 2)

    def test_hazirlanamadi_bicimi(self):
        self.assertEqual(kalite_veri.hazirlanamadi("x"), "**Hazırlanamadı:** x")

    def test_sema_sorgulari_icerik_okumaz(self):
        for ad, sql in kalite_veri.sema_sorgulari():
            with self.subTest(sorgu=ad):
                self.assertIsNone(YASAK.search(sql))
                self.assertTrue(sql.lstrip().upper().startswith("SELECT"),
                                "%s SELECT ile başlamıyor" % ad)

    def test_sema_sorgulari_sayim_ve_izin_kapsar(self):
        sorgular = dict(kalite_veri.sema_sorgulari())
        for ad in ("izinler", "sinif_farki", "saat_dilimi"):
            self.assertIn(ad, sorgular)
        izin = sorgular["izinler"]
        self.assertIn("information_schema.column_privileges", izin)
        self.assertIn("grantee = current_user", izin)
        for t in ('Evaluation', 'User', 'Team', 'weekly', 'nomination'):
            self.assertIn(t, izin)
        sinif = sorgular["sinif_farki"]
        self.assertIn("count(*)", sinif)
        self.assertIn("reportData\"->>'callClassification'", sinif)
        self.assertIn("timezone", sorgular["saat_dilimi"])

    def test_sema_baglantiyi_salt_okunur_acar_ve_hatada_durmaz(self):
        sorgular = kalite_veri.sema_sorgulari()
        sonuclar = {sorgular[0][1]: [("a", "b")]}
        imlec = _SahteImlec(sonuclar, hata_adi="column_privileges")
        baglanti = _SahteBaglanti(imlec)
        gorulen = []

        def baglan(url):
            gorulen.append(url)
            return baglanti

        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kod = kalite_veri.main(["sema"], ortam={"QA_READONLY_URL": "postgresql://gizli-url"},
                                   baglan=baglan)
        cikti = tampon.getvalue()
        self.assertEqual(kod, 0)
        self.assertIs(baglanti.read_only, True)
        self.assertFalse(any("statement_timeout" in s for s in imlec.sql),
                         "SET işlem içinde kalır, rollback geri alır; bağlantı seçeneği olmalı")
        self.assertIn("- izinler: okunamadı (PermissionError)", cikti)
        self.assertNotIn("gizli-url", cikti)
        self.assertTrue(baglanti.kapandi)
        self.assertGreaterEqual(baglanti.rollback_sayisi, 1)

    def test_zaman_asimi_baglanti_seceneginde_rollback_etkilemez(self):
        from unittest import mock
        import types
        sahte = types.SimpleNamespace(connect=mock.Mock(return_value="b"))
        with mock.patch.dict(sys.modules, {"psycopg": sahte}):
            self.assertEqual(kalite_veri.baglan_varsayilan("postgresql://x"), "b")
        sahte.connect.assert_called_once_with(
            "postgresql://x", connect_timeout=20, options="-c statement_timeout=15000")

    def test_sinif_farki_enum_metne_cevrilir(self):
        sql = dict(kalite_veri.sema_sorgulari())["sinif_farki"]
        self.assertIn('"callClassification"::text', sql)

    def test_read_only_atanamazsa_baglanti_kapanir(self):
        class Bozuk(_SahteBaglanti):
            hazir = False

            def __setattr__(self, ad, v):
                if ad == "read_only" and self.hazir:
                    raise RuntimeError("x")
                object.__setattr__(self, ad, v)

        b = Bozuk(_SahteImlec({}))
        b.hazir = True
        with self.assertRaises(RuntimeError):
            kalite_veri.baglanti_ac("u", lambda url: b)
        self.assertTrue(b.kapandi)

    def test_baglanti_hatasi_urli_sizdirmaz(self):
        def baglan(url):
            raise RuntimeError("could not connect to " + url)

        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kod = kalite_veri.main(["sema"], ortam={"QA_READONLY_URL": "postgresql://gizli-url"},
                                   baglan=baglan)
        self.assertEqual(kod, 1)
        self.assertTrue(tampon.getvalue().startswith("**Hazırlanamadı:**"))
        self.assertNotIn("gizli-url", tampon.getvalue())


if __name__ == "__main__":
    unittest.main()
