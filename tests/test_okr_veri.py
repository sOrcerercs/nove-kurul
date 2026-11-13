"""okr_veri.py testleri — ağ yok, veritabanı yok; bağlantı `baglan` ile enjekte edilir.

python3 -m unittest discover -s tests
"""
import io
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import okr_veri  # noqa: E402

URL = "postgresql://okr_okuyucu.proje:gizli-parola@ornek.pooler.test:5432/postgres"
ORTAM = {"OKR_READONLY_URL": URL}
KR_SUTUNLARI = ["id", "objective_id", "title_tr", "start", "current", "target", "unit",
                "rollup", "weight", "owner_user_id"]


class _SahteImlec:
    def __init__(self, sonuclar=None, hata_adi=None, hata=None, sutunlar=None):
        self.sonuclar = sonuclar or {}
        self.hata_adi = hata_adi
        self.hata = hata
        self.sutunlar = sutunlar or {}
        self.sql = []
        self._son = []
        self.description = []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        if self.hata:
            raise self.hata
        if self.hata_adi and self.hata_adi in sql:
            raise PermissionError("izin yok")
        self._son = self.sonuclar.get(sql, [])
        self.description = [(c,) for c in self.sutunlar.get(sql, [])]

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


def _kos(argv, baglanti=None, ortam=ORTAM, baglan=None):
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        kod = okr_veri.main(argv, ortam=ortam, baglan=baglan or (lambda url: baglanti), bugun="2026-11-13")
    return kod, tampon.getvalue()


class SemaTesti(unittest.TestCase):
    def test_url_yoksa_hazirlanamadi_rc1(self):
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kod = okr_veri.main(["sema"], ortam={})
        self.assertEqual(kod, 1)
        self.assertEqual(tampon.getvalue().strip(), "**Hazırlanamadı:** OKR_READONLY_URL yok")

    def test_kullanim_hatasi_rc2(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as c:
            okr_veri.main(["yok-boyle-komut"], ortam={})
        self.assertEqual(c.exception.code, 2)

    def test_baglanti_salt_okunur_ve_kapanir(self):
        imlec = _SahteImlec()
        b = _SahteBaglanti(imlec)
        kod, _ = _kos(["sema"], b)
        self.assertEqual(kod, 0)
        self.assertIs(b.read_only, True)
        self.assertTrue(b.kapandi)
        self.assertFalse(any(re.search(r"\bSET\b|set_config", s, re.I) for s in imlec.sql))

    def test_baglanti_hatasi_urli_sizdirmaz(self):
        def baglan(url):
            raise RuntimeError("could not connect to " + url)
        kod, cikti = _kos(["sema"], baglan=baglan)
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", cikti)
        for parca in ("gizli-parola", "ornek.pooler.test", "okr_okuyucu.proje"):
            self.assertNotIn(parca, cikti)

    def test_sorgu_hatasi_hazirlanamadi_rc1(self):
        # sema her sorguyu yakalar; main'in dış yakalayıcısı sema_bas dışına çıkan hatayı (ör. kopan bağlantı) maskeler
        b = _SahteBaglanti(_SahteImlec())
        with mock.patch.object(okr_veri, "sema_bas", side_effect=RuntimeError("fail " + URL)):
            kod, cikti = _kos(["sema"], b)
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** sorgu başarısız (", cikti)
        for parca in ("gizli-parola", "ornek.pooler.test", "okr_okuyucu.proje", URL):
            self.assertNotIn(parca, cikti)
        self.assertTrue(b.kapandi)

    def test_sema_hatada_durmaz(self):
        b = _SahteBaglanti(_SahteImlec(hata_adi="column_privileges"))
        kod, cikti = _kos(["sema"], b)
        self.assertEqual(kod, 0)
        self.assertIn("- users_sutun_izinleri: okunamadı (PermissionError)", cikti)
        self.assertIn("- oturum:", cikti)
        self.assertGreaterEqual(b.rollback_sayisi, 1)

    def test_sema_bes_baslik(self):
        kod, cikti = _kos(["sema"], _SahteBaglanti(_SahteImlec()))
        for ad in ("satir_sayilari", "users_sutun_izinleri", "eposta_izni", "app_settings_okunur", "oturum"):
            self.assertIn("- %s:" % ad, cikti)

    def test_sorgular_yalniz_select_ve_yasak_sutun_yok(self):
        sorgular = list(okr_veri.TABLO_SORGULARI.values()) + [s for _, s in okr_veri.sema_sorgulari()]
        sorgular.append("SELECT count(*) FROM public.checkins")
        self.assertEqual(sorted(okr_veri.TABLO_SORGULARI),
                         sorted(["periods", "departments", "users", "objectives", "key_results", "monthly"]))
        for sql in sorgular:
            with self.subTest(sql=sql[:50]):
                self.assertTrue(sql.lstrip().startswith("SELECT"))
                self.assertIsNone(re.search(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|GRANT)\b", sql))
                self.assertNotIn("SELECT *", sql)
                self.assertIsNone(re.search(r"password|login_attempts|help_articles|\bnote\b", sql, re.I))
                kalan = re.sub(r"has_column_privilege\([^)]*\)", "", sql)
                self.assertNotIn("email", kalan)

    def test_siralama_sitedeki_gibi(self):
        q = okr_veri.TABLO_SORGULARI
        self.assertIn("ORDER BY starts_on", q["periods"])
        self.assertIn("ORDER BY sort_order", q["departments"])
        self.assertIn("ORDER BY code", q["objectives"])
        self.assertIn("ORDER BY id", q["key_results"])
        self.assertIn('"start"', q["key_results"])
        self.assertIn('"current"', q["key_results"])
        self.assertIn("rollup::text", q["key_results"])

    def test_tablolari_oku_sozluk_bicimi(self):
        sonuc, sutun = {}, {}
        for ad, sql in okr_veri.TABLO_SORGULARI.items():
            sonuc[sql], sutun[sql] = [], []
        kr = okr_veri.TABLO_SORGULARI["key_results"]
        sutun[kr] = KR_SUTUNLARI
        sonuc[kr] = [("k1", "o1", "KR bir", 0.0, 5.0, 10.0, "%", "avg", None, "u1")]
        b = _SahteBaglanti(_SahteImlec(sonuc, sutunlar=sutun))
        rows = okr_veri.tablolari_oku(b)
        self.assertEqual(sorted(rows), sorted(okr_veri.TABLO_SORGULARI))
        self.assertEqual(list(rows["key_results"][0]), KR_SUTUNLARI)
        self.assertEqual(rows["key_results"][0]["rollup"], "avg")
        self.assertEqual(rows["periods"], [])

    def test_checkin_sayisi(self):
        sql = "SELECT count(*) FROM public.checkins"
        b = _SahteBaglanti(_SahteImlec({sql: [(42,)]}))
        self.assertEqual(okr_veri.checkin_sayisi(b), 42)


class IzinDosyasiTesti(unittest.TestCase):
    YOL = KOK / "docs" / "okr-veri-izin.sql"

    def _ifadeler(self):
        govde = "\n".join(s for s in self.YOL.read_text(encoding="utf-8").splitlines()
                          if not s.strip().startswith("--"))
        return [i.strip() for i in govde.split(";") if i.strip()]

    def test_dosya_var_ve_ifadeler_dar(self):
        self.assertTrue(self.YOL.exists())
        ifadeler = self._ifadeler()
        self.assertEqual(len(ifadeler), 5)
        for i in ifadeler:
            with self.subTest(ifade=i[:40]):
                self.assertRegex(i, r"^(SELECT\b|GRANT SELECT ON public\.app_settings TO okr_okuyucu$|"
                                    r"CREATE POLICY okr_okuyucu_aralik ON public\.app_settings FOR SELECT "
                                    r"TO okr_okuyucu USING \(key = 'default_range_start'\)$)")
                self.assertIsNone(re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|REVOKE|TRUNCATE)\b", i, re.I))

    def test_anayasa_atfi_birebir(self):
        def duz(m):
            return re.sub(r"(?m)^-- ?", "", m).replace("\n", " ")

        def sade(m):
            return " ".join(m.split())

        dosya = sade(duz(self.YOL.read_text(encoding="utf-8")))
        anayasa = sade((KOK / "ANAYASA.md").read_text(encoding="utf-8"))
        claude = sade((KOK / "CLAUDE.md").read_text(encoding="utf-8"))
        alinti = "Prod veritabanına yazma yoktur: `INSERT`/`UPDATE`/`DELETE`, DDL ve migration yasak."
        self.assertIn(alinti, dosya)
        self.assertIn(alinti, anayasa)
        yasak = "Veri kaynaklarına, prod veritabanına yazma; DDL ya da migration"
        self.assertIn(yasak, dosya)
        self.assertIn(yasak, claude)


if __name__ == "__main__":
    unittest.main()
