"""Kalite günlük raporu — takvim hesabı ve sistem sorusu (spec: kalite-gunluk-rapor, Görev 1)."""
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import dagitici  # noqa: E402
import rapor_takvimi as rt  # noqa: E402
import soru_kapisi  # noqa: E402
import soru_kaydi as sk  # noqa: E402

TR = timezone(timedelta(hours=3))
SORU = "26.10.2026 (pazartesi) günlük kalite raporu: ..."


def d(s):
    return date.fromisoformat(s)


class TakvimTesti(unittest.TestCase):
    def test_aralik_sali(self):
        self.assertEqual(rt.rapor_araligi(d("2026-10-20"), set()),
                         ((d("2026-10-19"), d("2026-10-19")), (d("2026-10-16"), d("2026-10-16"))))

    def test_aralik_pazartesi(self):
        self.assertEqual(rt.rapor_araligi(d("2026-10-26"), set()),
                         ((d("2026-10-23"), d("2026-10-25")), (d("2026-10-16"), d("2026-10-18"))))

    def test_aralik_yil_basi(self):
        (a, b), _ = rt.rapor_araligi(d("2029-01-01"), set())
        self.assertEqual((a, b), (d("2028-12-29"), d("2028-12-31")))

    def test_hafta_sonu_none(self):
        self.assertIsNone(rt.rapor_araligi(d("2026-10-24"), set()))
        self.assertIsNone(rt.rapor_araligi(d("2026-10-25"), set()))

    def test_tatil_none(self):
        self.assertIsNone(rt.rapor_araligi(d("2026-10-29"), {d("2026-10-29")}))

    def test_tatil_sonrasi_aralik(self):
        self.assertEqual(rt.rapor_araligi(d("2026-10-30"), {d("2026-10-29")}),
                         ((d("2026-10-28"), d("2026-10-29")), (d("2026-10-21"), d("2026-10-22"))))

    def test_tatiller_oku(self):
        kok = Path(tempfile.mkdtemp())
        self.assertEqual(rt.tatiller_oku(kok), set())
        (kok / "takimlar" / "kalite").mkdir(parents=True)
        (kok / "takimlar" / "kalite" / "tatiller.json").write_text(
            json.dumps([{"tarih": "2026-10-29", "ad": "x"}]), encoding="utf-8")
        self.assertEqual(rt.tatiller_oku(kok), {d("2026-10-29")})
        self.assertIn(d("2027-05-19"), rt.tatiller_oku(KOK))   # depodaki gerçek liste

    def test_bozuk_tatiller_hata(self):
        kok = Path(tempfile.mkdtemp())
        (kok / "takimlar" / "kalite").mkdir(parents=True)
        yol = kok / "takimlar" / "kalite" / "tatiller.json"
        for icerik in ("{bozuk", '[{"tarih": "yarın"}]', '[{"ad": "x"}]'):
            yol.write_text(icerik, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "tatiller.json okunamadı"):
                rt.tatiller_oku(kok)


class SistemSorusuTesti(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        dizin = self.kok / "takimlar" / "kalite"
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text("---\nname: kalite\ndescription: Kalite\n---\n", encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps({"takim": "kalite", "kuyruk": []}), encoding="utf-8")
        self.aralik = (d("2026-10-23"), d("2026-10-25"))
        self.karsi = (d("2026-10-16"), d("2026-10-18"))

    def ac(self, simdi=datetime(2026, 10, 26, 8, 0, tzinfo=TR), sid="rapor-kalite-20261026", **kw):
        return soru_kapisi.sistem_sorusu(self.kok, "kalite", SORU, sid, self.aralik, self.karsi, simdi, **kw)

    def metin(self, sid="rapor-kalite-20261026"):
        return sk.yol(sid, self.kok).read_text(encoding="utf-8")

    def test_kayit_ve_kuyruk(self):
        self.assertEqual(self.ac(), {"sonuc": "acildi", "soru_id": "rapor-kalite-20261026", "sebep": ""})
        m = self.metin()
        self.assertEqual(sk.alan(m, "aralik"), "2026-10-23..2026-10-25")
        self.assertEqual(sk.alan(m, "karsilastir"), "2026-10-16..2026-10-18")
        self.assertEqual(sk.alan(m, "gorunurluk"), "kurul")
        self.assertEqual(sk.alan(m, "durum"), "danışmanda")
        self.assertEqual(sk.alan(m, "soran"), "Zamanlayıcı (kalite günlük raporu)")
        self.assertEqual(sk.bolum_alani(m, "## Dağıtım", "danışman"), "kalite")
        self.assertEqual(sk.bolum_alani(m, "## Dağıtım", "gerekçe"), "zamanlı rapor")

    def test_kuyrukta_s_maddesi(self):
        self.ac()
        self.assertEqual(ayar.durum_oku("kalite", self.kok)["kuyruk"],
                         [{"id": "s-rapor-kalite-20261026", "durum": "bekliyor", "not": SORU}])

    def test_ayni_gun_ikinci_kez_var(self):
        self.ac()
        once = self.metin()
        self.assertEqual(self.ac()["sonuc"], "var")
        self.assertEqual(self.metin(), once)
        self.assertEqual(len(ayar.durum_oku("kalite", self.kok)["kuyruk"]), 1)

    def test_dagitim_yazili_yonlendir_none(self):
        self.ac()
        haiku = mock.MagicMock()
        self.assertIsNone(dagitici.yonlendir(self.kok, "rapor-kalite-20261026", haiku=haiku))
        haiku.assert_not_called()
        self.assertEqual(dagitici.yonlendirilecek_sorular(self.kok), [])

    def test_utc_gecesi_istanbul_gunu(self):
        utc = datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc)   # İstanbul: 26.10 02:30
        self.ac(simdi=utc)
        self.assertEqual(sk.alan(self.metin(), "zaman"), "2026-10-26T02:30:00+03:00")

    def test_kuyruk_yoksa_reddedilir_yazmaz(self):
        (self.kok / "takimlar" / "kalite" / "durum.json").unlink()
        sonuc = self.ac()
        self.assertEqual(sonuc["sonuc"], "reddedildi")
        self.assertFalse(sk.yol("rapor-kalite-20261026", self.kok).exists())

    def test_kayit_var_kuyruk_eksik_yeniden_yazilir(self):
        self.ac()
        ayar.durum_guncelle("kalite", {"kuyruk": []}, self.kok)
        sonuc = self.ac()
        self.assertEqual(sonuc["sonuc"], "var")
        self.assertIn("yeniden kuyruğa", sonuc["sebep"])
        self.assertEqual([o["id"] for o in ayar.durum_oku("kalite", self.kok)["kuyruk"]],
                         ["s-rapor-kalite-20261026"])

    def test_kuyruga_yaz_false_gorunur_hata(self):
        with mock.patch.object(dagitici, "kuyruga_yaz", return_value=False):
            sonuc = self.ac()
        self.assertEqual(sonuc["sonuc"], "reddedildi")
        self.assertIn("kuyruğuna yazılamadı", sonuc["sebep"])
        self.assertTrue(sk.yol("rapor-kalite-20261026", self.kok).exists())   # kayıt kalır
        self.assertEqual(self.ac()["sonuc"], "var")                           # sonraki çağrı kuyruğa yazar
        self.assertEqual(len(ayar.durum_oku("kalite", self.kok)["kuyruk"]), 1)

    def test_es_zamanli_yaris_x_modu(self):
        yol = sk.yol("rapor-kalite-20261026", self.kok)
        gercek = Path.exists
        with mock.patch.object(Path, "exists", lambda self_: False if self_ == yol else gercek(self_)):
            self.ac()                      # exists() "yok" der, ama dosya yazıldı
            once = self.metin()
            self.assertEqual(self.ac()["sonuc"], "var")   # "x" FileExistsError -> var yolu
        self.assertEqual(self.metin(), once)
        self.assertEqual(len(ayar.durum_oku("kalite", self.kok)["kuyruk"]), 1)

    def test_kuru_yazmaz(self):
        self.assertEqual(self.ac(kuru=True)["sonuc"], "acildi")
        self.assertFalse(sk.yol("rapor-kalite-20261026", self.kok).exists())
        self.assertEqual(ayar.durum_oku("kalite", self.kok)["kuyruk"], [])


if __name__ == "__main__":
    unittest.main()
