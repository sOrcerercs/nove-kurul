"""okr_veri.py testleri — ağ yok, veritabanı yok; bağlantı `baglan` ile enjekte edilir.

python3 -m unittest discover -s tests
"""
import argparse
import io
import re
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as c:
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


PERIOD_SUTUN = ["id", "code", "kind", "state", "starts_on", "ends_on"]
AYAR_SQL = "SELECT value FROM public.app_settings WHERE key = 'default_range_start'"
BUGUN = "2026-11-13"


def _aralik_baglantisi(ayar=None, hata_adi=None):
    q = okr_veri.TABLO_SORGULARI
    sonuc = {q["periods"]: [("a", "p-2025-fy", "fiscal_year", "closed", "2025-09-01", "2026-08-31"),
                            ("b", "p-2026-fy", "fiscal_year", "active", "2026-09-01", "2027-08-31")],
             q["objectives"]: [("o1", "S1", "d1", "b", "x", None, None)],
             "SELECT count(*) FROM public.checkins": [(0,)]}
    sutun = {q["periods"]: PERIOD_SUTUN,
             q["objectives"]: ["id", "code", "department_id", "period_id", "title_tr", "owner_user_id", "weight"]}
    if ayar is not None:
        sonuc[AYAR_SQL] = ayar
    return _SahteBaglanti(_SahteImlec(sonuc, hata_adi=hata_adi, sutunlar=sutun))


def _aralik_kos(argv, baglanti, ek=None):
    """Task 7 komutlarının yaptığı: bayrak → doğrula → agac_hazirla → kapsam. (Kod, çıktı) döner."""
    ap = argparse.ArgumentParser()
    okr_veri.aralik_bayraklari_ekle(ap)
    args = ap.parse_args(argv)
    okr_veri.aralik_bayraklari_dogrula(ap, args)
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        sonuc = okr_veri.agac_hazirla(baglanti, args, BUGUN)
        if sonuc is None:
            return 1, tampon.getvalue()
        aralik = sonuc[0]
        print(okr_veri.kapsam_bolumu("deneme", aralik, ek, 0))
    return 0, tampon.getvalue()


class AralikTesti(unittest.TestCase):
    def test_varsayilan_aralik_iki_donemi_birlestirir(self):
        kod, c = _aralik_kos([], _aralik_baglantisi())
        self.assertEqual(kod, 0)
        self.assertTrue(c.startswith("## kapsam\n"))
        for satir in ("aralik=2025-09-01..2026-11-13", "donemler=p-2025-fy,p-2026-fy",
                      "birlesik=evet — aralık 2 dönemi kapsıyor; site gibi birleştirildi",
                      "kesim=2026-11-13 (aralık sonu ile bugünün küçüğü; Europe/Istanbul)",
                      "son_tamamlanan_ay=2026-10"):
            self.assertIn(satir, c.splitlines())
        self.assertIn("aralik_kaynagi=varsayılan (yerleşik varsayılan — app_settings satırı yok)", c)

    def test_app_settings_degeri_kullanilir(self):
        kod, c = _aralik_kos([], _aralik_baglantisi(ayar=[("2026-09-01",)]))
        self.assertEqual(kod, 0)
        self.assertIn("aralik=2026-09-01..2026-11-13", c)
        self.assertIn("aralik_kaynagi=varsayılan (app_settings.default_range_start)", c)
        self.assertNotIn("birlesik=", c)

    def test_app_settings_okunamazsa_dusus_gorunur(self):
        b = _aralik_baglantisi(hata_adi="app_settings")
        kod, c = _aralik_kos([], b)
        self.assertEqual(kod, 0)
        self.assertIn("aralik_kaynagi=varsayılan (yerleşik varsayılan — app_settings okunamadı (PermissionError))", c)
        self.assertIn("aralik=2025-09-01..2026-11-13", c)
        self.assertGreaterEqual(b.rollback_sayisi, 1)
        self.assertIn("SELECT count(*) FROM public.checkins", b.imlec.sql)      # sonraki sorgu çalıştı

    def test_app_settings_yok_ve_gecersiz_deger(self):
        _, c = _aralik_kos([], _aralik_baglantisi(ayar=[("2026-02-30",)]))
        self.assertIn("(yerleşik varsayılan — app_settings değeri geçersiz)", c)
        self.assertIn("aralik=2025-09-01..", c)
        _, c = _aralik_kos([], _aralik_baglantisi(ayar=[]))
        self.assertIn("(yerleşik varsayılan — app_settings satırı yok)", c)

    def test_donem_bayragi(self):
        _, c = _aralik_kos(["--donem", "p-2026-fy"], _aralik_baglantisi())
        self.assertIn("aralik=2026-09-01..2027-08-31", c)
        self.assertIn("kesim=2026-11-13 ", c)
        self.assertIn("aralik_kaynagi=dönem p-2026-fy", c)

    def test_gecmis_aralik_kesilmez(self):
        _, c = _aralik_kos(["--baslangic", "2025-09-01", "--bitis", "2026-02-28"], _aralik_baglantisi())
        self.assertIn("kesim=2026-02-28 ", c)
        self.assertIn("son_tamamlanan_ay=2026-02", c)
        self.assertIn("aralik_kaynagi=verilen tarih", c)

    def test_bilinmeyen_donem_sebepli_durur(self):
        kod, c = _aralik_kos(["--donem", "p-2030-fy"], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertEqual(c.strip(), "**Hazırlanamadı:** dönem bulunamadı: p-2030-fy (geçerli: p-2025-fy, p-2026-fy)")

    def test_gecersiz_tarih_sebepli_durur(self):
        kod, c = _aralik_kos(["--baslangic", "2026-01-01", "--bitis", "2026-02-30"], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** tarih geçersiz", c)
        kod, c = _aralik_kos(["--baslangic", "2026-03-01", "--bitis", "2026-02-01"], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** aralık ters", c)

    def test_tek_uc_ve_cifte_bayrak_kullanim_hatasi(self):
        for argv in (["--baslangic", "2026-01-01"], ["--bitis", "2026-01-01"],
                     ["--donem", "p-2026-fy", "--baslangic", "2026-01-01", "--bitis", "2026-02-01"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as c:
                _aralik_kos(argv, _aralik_baglantisi())
            self.assertEqual(c.exception.code, 2)

    def test_bos_bayrak_sessizce_varsayilana_dusmez(self):
        kod, c = _aralik_kos(["--donem", ""], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** dönem bulunamadı: ", c)
        kod, c = _aralik_kos(["--baslangic", "", "--bitis", ""], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** tarih geçersiz", c)
        kod, c = _aralik_kos(["--baslangic", "", "--bitis", "2026-01-01"], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** tarih geçersiz", c)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            _aralik_kos(["--donem", "", "--bitis", "2026-01-01"], _aralik_baglantisi())
        self.assertEqual(e.exception.code, 2)

    def test_araliga_donem_dusmuyor(self):
        kod, c = _aralik_kos(["--baslangic", "2020-01-01", "--bitis", "2020-12-31"], _aralik_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** 2020-01-01..2020-12-31 aralığına düşen dönem yok", c)

    def test_varsayilan_baslangic_bugunden_sonraysa_durur(self):
        kod, c = _aralik_kos([], _aralik_baglantisi(ayar=[("2027-01-01",)]))
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", c)

    def test_kapsam_satir_sahteciligi_olmaz(self):
        _, c = _aralik_kos([], _aralik_baglantisi(), ek={"bolum": "x\nkayit=999"})
        self.assertNotIn("kayit=999", c.splitlines())
        self.assertIn("bolum=x kayit=999", c.splitlines())
        self.assertEqual(c.splitlines()[-1], "kayit=0")

    def test_bugun_gecersizse_sebepli_durur(self):
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kod = okr_veri.main(["donemler"], ortam=ORTAM, baglan=lambda u: _aralik_baglantisi(), bugun="2026-13-40")
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** bugün geçersiz", tampon.getvalue())


class DonemlerKomutuTesti(unittest.TestCase):
    def test_donemler_cli(self):
        kod, c = _kos(["donemler"], _aralik_baglantisi())
        self.assertEqual(kod, 0)
        self.assertTrue(c.startswith("## kapsam\n"))
        self.assertNotIn("birlesik=", c)
        satirlar = c.splitlines()
        self.assertIn("- p-2025-fy: tur=fiscal_year durum=closed aralik=2025-09-01..2026-08-31 objective=0", satirlar)
        self.assertIn("- p-2026-fy: tur=fiscal_year durum=active aralik=2026-09-01..2027-08-31 objective=1", satirlar)
        alt = satirlar[satirlar.index("## mali ceyrekler"):]
        self.assertEqual(alt[1], "- Ç1: 2026-09-01..2026-11-30 (bugün)")
        self.assertEqual(alt[2], "- Ç2: 2026-12-01..2027-02-28")
        self.assertEqual(len([a for a in alt if a.startswith("- Ç")]), 4)
        self.assertTrue(alt[-1].startswith("not=dönemler yıllıktır;"))


DEPT_SUTUN = ["id", "slug", "name_tr"]
USER_SUTUN = ["id", "name"]
OBJ_SUTUN = ["id", "code", "department_id", "period_id", "title_tr", "owner_user_id", "weight"]
AYLIK_SUTUN = ["key_result_id", "month", "value"]
KR2_BASLIK = "Satış KR iki deneme oranı"


def _okr_baglantisi(agirliklar=(None, None), yalniz_finans=False, checkin=0, kesimden_sonra=False,
                    kopru_k2=False):
    """Task 7 fikstürü — adlar uydurmadır (B4). Satış O1: KR1 sum, KR2 avg %; Finans O1: ölçülemez KR; Pazarlama boş."""
    q = okr_veri.TABLO_SORGULARI
    krlar = [("k3", "of", "Finans KR deneme", 5.0, 5.0, 5.0, "adet", "last", None, "u2")]
    aylik = [("k3", "2026-09", 5.0), ("k3", "2026-10", 5.0)]
    objler = [("of", "O1", "dfin", "b", "Finans deneme hedefi", "u2", None)]
    if not yalniz_finans:
        krlar = [("k1", "os", "Satış KR bir deneme cirosu", 0.0, 0.0, 1200.0, "TL", "sum", agirliklar[0], "u1"),
                 ("k2", "os", KR2_BASLIK, 50.0, 60.0 if kopru_k2 else 50.0, 90.0, "%", "avg", agirliklar[1],
                  "u1")] + krlar
        aylik = [("k1", "2026-09", 100.0), ("k1", "2026-10", 100.0),
                 ("k2", "2026-09", 70.0), ("k2", "2026-10", 80.0)] + aylik
        objler = objler + [("os", "O1", "dsat", "b", "Satış deneme hedefi", "u1", None)]
    if kopru_k2:                                          # k2: aylık satırı yok → saklı özet (köprü)
        aylik = [x for x in aylik if x[0] != "k2"]
    if kesimden_sonra:                                    # tüm aylık satırlar kesimden (2026-11-13) sonra
        aylik = [(x[0], {"2026-09": "2026-12", "2026-10": "2027-01"}[x[1]], x[2]) for x in aylik]
    sonuc = {q["periods"]: [("a", "p-2025-fy", "fiscal_year", "closed", "2025-09-01", "2026-08-31"),
                            ("b", "p-2026-fy", "fiscal_year", "active", "2026-09-01", "2027-08-31")],
             q["departments"]: [("dfin", "finans", "Finans"), ("dpaz", "pazarlama", "Pazarlama"),
                                ("dsat", "satis", "Satış")],
             q["users"]: [("u1", "Deniz Örnek"), ("u2", "Ada Deneme")],
             q["objectives"]: objler,
             q["key_results"]: krlar,
             q["monthly"]: aylik,
             "SELECT count(*) FROM public.checkins": [(checkin,)]}
    sutun = {q["periods"]: PERIOD_SUTUN, q["departments"]: DEPT_SUTUN, q["users"]: USER_SUTUN,
             q["objectives"]: OBJ_SUTUN, q["key_results"]: KR_SUTUNLARI, q["monthly"]: AYLIK_SUTUN}
    return _SahteBaglanti(_SahteImlec(sonuc, sutunlar=sutun))


def _satir(cikti, bas):
    bulunan = [s for s in cikti.splitlines() if s.startswith(bas)]
    if len(bulunan) != 1:
        raise AssertionError("%r ile başlayan tek satır yok:\n%s" % (bas, cikti))
    return bulunan[0]


class YardimciTesti(unittest.TestCase):
    def test_sayi_yaz(self):
        self.assertEqual(okr_veri.sayi_yaz(57500), "57500")
        self.assertEqual(okr_veri.sayi_yaz(99.2), "99.2")
        self.assertEqual(okr_veri.sayi_yaz(4.4666), "4.47")
        self.assertEqual(okr_veri.sayi_yaz(0.0), "0")
        self.assertEqual(okr_veri.sayi_yaz(-0.001), "0")

    def test_cift_yaz(self):
        cift = {"annual": 40, "std": None, "status_pct": 40, "with_std": 0, "measurable": 2}
        self.assertEqual(okr_veri.cift_yaz(cift, True),
                         "yuzde=40 std=yok yillik=40 durum=Gelişime Açık std_kapsam=0/2")
        self.assertEqual(okr_veri.cift_yaz(cift, False),
                         "yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok")


class BolumlerKomutuTesti(unittest.TestCase):
    def test_bolumler_cli(self):
        kod, c = _kos(["bolumler", "--donem", "p-2026-fy"], _okr_baglantisi())
        self.assertEqual(kod, 0)
        self.assertTrue(c.startswith("## kapsam\n"))
        self.assertIn("komut=bolumler", c.splitlines())
        self.assertIn("kayit=3", c.splitlines())
        self.assertEqual(_satir(c, "- Satış:"),
                         "- Satış: yuzde=82 std=82 yillik=40 durum=Beklenen std_kapsam=2/2 objective=1 kr=2")

    def test_bolumler_olculemez_bolum_tire(self):
        kod, c = _kos(["bolumler", "--donem", "p-2026-fy"], _okr_baglantisi())
        self.assertEqual(kod, 0)
        self.assertEqual(_satir(c, "- Finans:"),
                         "- Finans: yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok objective=1 kr=1")
        self.assertEqual(_satir(c, "- Pazarlama:"),
                         "- Pazarlama: yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok objective=0 kr=0")

    def test_bolum_adi_buyuk_kucuk_ve_slug(self):
        beklenen = "- Satış: yuzde=82 std=82 yillik=40 durum=Beklenen std_kapsam=2/2 objective=1 kr=2"
        for ad in ("satış", "SATIŞ", "satis", "Satış"):
            with self.subTest(ad=ad):
                kod, c = _kos(["bolumler", "--donem", "p-2026-fy", "--bolum", ad], _okr_baglantisi())
                self.assertEqual(kod, 0)
                self.assertEqual([s for s in c.splitlines() if s.startswith("- ")], [beklenen])
                self.assertIn("bolum=Satış", c.splitlines())
                self.assertIn("kayit=1", c.splitlines())

    def test_bolum_bulunamaz(self):
        kod, c = _kos(["bolumler", "--donem", "p-2026-fy", "--bolum", "Lojistik"], _okr_baglantisi())
        self.assertEqual(kod, 1)
        self.assertEqual(c.strip(),
                         "**Hazırlanamadı:** bölüm bulunamadı: Lojistik (geçerli: Finans, Pazarlama, Satış)")

    def test_bos_bolum_tum_bolumlere_dusmez(self):
        kod, c = _kos(["bolumler", "--donem", "p-2026-fy", "--bolum", ""], _okr_baglantisi())
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:** bölüm bulunamadı: ", c)

    def test_aralik_bayraklari_dogrulanir(self):
        for komut in ("bolumler", "objektifler", "sirket"):
            with self.subTest(komut=komut), redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as e:
                _kos([komut, "--baslangic", "2026-09-01"], _okr_baglantisi())
            self.assertEqual(e.exception.code, 2)

    def test_bolum_bul_turkce_harf(self):
        depts = [{"name_tr": "İnsan Kaynakları", "slug": "ik"}, {"name_tr": "Satış", "slug": "satis"}]
        with redirect_stdout(io.StringIO()):
            self.assertIs(okr_veri.bolum_bul(depts, "insan kaynakları"), depts[0])
            self.assertIs(okr_veri.bolum_bul(depts, "İNSAN KAYNAKLARI"), depts[0])
            self.assertIs(okr_veri.bolum_bul(depts, "IK"), None)       # I → ı: "ık" ≠ "ik"
            self.assertIs(okr_veri.bolum_bul(depts, "ik"), depts[0])


class ObjektiflerKomutuTesti(unittest.TestCase):
    def test_objektifler_en_dusuk_kr(self):
        kod, c = _kos(["objektifler", "--donem", "p-2026-fy"], _okr_baglantisi())
        self.assertEqual(kod, 0)
        self.assertTrue(c.startswith("## kapsam\n"))
        self.assertIn("kayit=2", c.splitlines())
        self.assertEqual(
            _satir(c, "- Satış / O1 "),
            "- Satış / O1 Satış deneme hedefi: donem=p-2026-fy agirlik=yok yuzde=82 std=82 yillik=40 "
            "durum=Beklenen std_kapsam=2/2 kr=2 olculmeyen=0 olculemeyen=0 sorumlu=Deniz Örnek "
            "en_dusuk_kr=%s (%%63, agirlik=yok)" % KR2_BASLIK)
        self.assertEqual(
            _satir(c, "- Finans / O1 "),
            "- Finans / O1 Finans deneme hedefi: donem=p-2026-fy agirlik=yok yuzde=— std=yok yillik=— durum=— "
            "sebep=ölçülebilir KR yok kr=1 olculmeyen=0 olculemeyen=1 sorumlu=Ada Deneme en_dusuk_kr=yok")

    def test_objektifler_agirlikli(self):
        kod, c = _kos(["objektifler", "--donem", "p-2026-fy", "--bolum", "satis"],
                      _okr_baglantisi(agirliklar=(75.0, 25.0)))
        self.assertEqual(kod, 0)
        satir = _satir(c, "- Satış / O1 ")
        self.assertIn(" yuzde=91 std=91 ", satir)
        self.assertTrue(satir.endswith("en_dusuk_kr=%s (%%63, agirlik=25)" % KR2_BASLIK))
        self.assertNotIn("- Finans", c)

    def test_en_dusuk_kr_esitlikte_buyuk_agirlik(self):
        def kr(id_, pct_current, w):
            return {"id": id_, "title_tr": id_, "start": 0, "current": pct_current, "target": 100,
                    "rollup": "last", "weight": w, "measured_by_cutoff": True, "std": None}
        o = {"krs": [kr("a", 40, 10.0), kr("b", 40, 30.0), kr("c", 40, None), kr("d", 90, 60.0)]}
        self.assertEqual(okr_veri.en_dusuk_kr(o)["id"], "b")
        o = {"krs": [kr("a", 40, None), kr("b", 40, None)]}
        self.assertEqual(okr_veri.en_dusuk_kr(o)["id"], "a")
        o = {"krs": [dict(kr("a", 10, 5.0), measured_by_cutoff=False), kr("b", 50, None)]}
        self.assertEqual(okr_veri.en_dusuk_kr(o)["id"], "b")
        self.assertIsNone(okr_veri.en_dusuk_kr({"krs": []}))


class SirketKomutuTesti(unittest.TestCase):
    def test_sirket_cli(self):
        kod, c = _kos(["sirket", "--donem", "p-2026-fy"], _okr_baglantisi())
        self.assertEqual(kod, 0)
        self.assertTrue(c.startswith("## kapsam\n"))
        satirlar = c.splitlines()
        self.assertIn("paylar=betik hesabı; sitede sayım var, pay yok", satirlar)
        self.assertIn("checkin_notu=Nove PYS'de check-in kaydı yok", satirlar)
        govde = satirlar[satirlar.index("kayit=3") + 1:]
        self.assertEqual(govde, [
            "- sirket: yuzde=82 std=82 yillik=40 durum=Beklenen std_kapsam=2/2",
            "- sayim: bolum=3 objective=2 kr=3 olculebilir=2 olculmeyen=0 olculemeyen=1 ozetten=0",
            "- kr_dagilimi (n=2): Beklenenin Üzerinde=0 (%0) · Beklenen=1 (%50) · Beklenenin Altında=1 (%50) · "
            "Gelişime Açık=0 (%0) · Başlamadı=0 (%0)",
            "- objective_dagilimi (n=1): Beklenenin Üzerinde=0 (%0) · Beklenen=1 (%100) · "
            "Beklenenin Altında=0 (%0) · Gelişime Açık=0 (%0) · Başlamadı=0 (%0)",
            "- gelisime_acik_kr=0 (%59 ve altı; Başlamadı dahil)",
            "- checkin=0",
        ])

    def test_sirket_checkin_varsa_not_yok(self):
        _, c = _kos(["sirket", "--donem", "p-2026-fy"], _okr_baglantisi(checkin=4))
        self.assertNotIn("checkin_notu=", c)
        self.assertIn("- checkin=4", c.splitlines())

    def test_sirket_bos_dagilim_pay_tire(self):
        kod, c = _kos(["sirket", "--donem", "p-2026-fy"], _okr_baglantisi(yalniz_finans=True))
        self.assertEqual(kod, 0)
        self.assertEqual(_satir(c, "- sirket:"),
                         "- sirket: yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok")
        self.assertEqual(_satir(c, "- kr_dagilimi"),
                         "- kr_dagilimi (n=0): Beklenenin Üzerinde=0 (—) · Beklenen=0 (—) · "
                         "Beklenenin Altında=0 (—) · Gelişime Açık=0 (—) · Başlamadı=0 (—)")
        self.assertTrue(_satir(c, "- objective_dagilimi").startswith("- objective_dagilimi (n=0): "))

    def test_sirket_bolum_almaz(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            _kos(["sirket", "--bolum", "Satış"], _okr_baglantisi())
        self.assertEqual(e.exception.code, 2)


class SebepTesti(unittest.TestCase):
    """B7: ölçülebilir KR var ama kesime kadar ölçülmemişse sebep `kesime kadar aylık veri yok`'tur."""
    VERI_YOK = "yuzde=— std=yok yillik=— durum=— sebep=kesime kadar aylık veri yok"
    OLCULEBILIR_YOK = "yuzde=— std=yok yillik=— durum=— sebep=ölçülebilir KR yok"

    def test_bolumler_kesimden_sonra(self):
        kod, c = _kos(["bolumler", "--donem", "p-2026-fy"], _okr_baglantisi(kesimden_sonra=True))
        self.assertEqual(kod, 0)
        self.assertEqual(_satir(c, "- Satış:"), "- Satış: %s objective=1 kr=2" % self.VERI_YOK)
        self.assertEqual(_satir(c, "- Finans:"), "- Finans: %s objective=1 kr=1" % self.OLCULEBILIR_YOK)

    def test_objektifler_kesimden_sonra(self):
        kod, c = _kos(["objektifler", "--donem", "p-2026-fy"], _okr_baglantisi(kesimden_sonra=True))
        self.assertEqual(kod, 0)
        satir = _satir(c, "- Satış / O1 ")
        self.assertIn(" %s kr=2 olculmeyen=2 olculemeyen=0 " % self.VERI_YOK, satir)
        self.assertTrue(satir.endswith("en_dusuk_kr=yok"))
        self.assertIn(" %s kr=1 " % self.OLCULEBILIR_YOK, _satir(c, "- Finans / O1 "))

    def test_sirket_kesimden_sonra(self):
        kod, c = _kos(["sirket", "--donem", "p-2026-fy"], _okr_baglantisi(kesimden_sonra=True))
        self.assertEqual(kod, 0)
        self.assertEqual(_satir(c, "- sirket:"), "- sirket: %s" % self.VERI_YOK)
        self.assertEqual(_satir(c, "- sayim:"),
                         "- sayim: bolum=3 objective=2 kr=3 olculebilir=2 olculmeyen=2 olculemeyen=1 ozetten=0")
        self.assertTrue(_satir(c, "- kr_dagilimi").startswith("- kr_dagilimi (n=0): "))

    def test_en_dusuk_kr_ozetten_isaretli(self):
        kod, c = _kos(["objektifler", "--donem", "p-2026-fy", "--bolum", "Satış"], _okr_baglantisi(kopru_k2=True))
        self.assertEqual(kod, 0)
        self.assertTrue(_satir(c, "- Satış / O1 ").endswith(
            "en_dusuk_kr=%s (%%25, agirlik=yok, özetten)" % KR2_BASLIK))
        _, c = _kos(["objektifler", "--donem", "p-2026-fy", "--bolum", "Satış"], _okr_baglantisi())
        self.assertNotIn("özetten", c)

    def test_objektifler_bos_bolum(self):
        kod, c = _kos(["objektifler", "--donem", "p-2026-fy", "--bolum", "Pazarlama"], _okr_baglantisi())
        self.assertEqual(kod, 0)
        satirlar = c.splitlines()
        self.assertEqual(satirlar[-1], "- objective yok")
        self.assertEqual(satirlar[-2], "kayit=0")


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
