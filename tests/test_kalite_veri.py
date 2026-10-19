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


class CekirdekTesti(unittest.TestCase):
    def test_ay_siniri_dahil(self):
        from datetime import datetime
        bas, bit = kalite_veri.gun_siniri("2026-10-01", "2026-10-31")
        self.assertEqual(bas, datetime(2026, 10, 1, 0, 0, 0))
        self.assertEqual(bit, datetime(2026, 10, 31, 23, 59, 59))

    def test_ters_aralik_hata(self):
        with self.assertRaises(ValueError):
            kalite_veri.gun_siniri("2026-10-10", "2026-10-01")

    def test_js_yuvarla(self):
        self.assertEqual(kalite_veri.js_yuvarla(70.5), 71)
        self.assertEqual(kalite_veri.js_yuvarla(70.45, 1), 70.5)
        self.assertEqual(kalite_veri.js_yuvarla(-0.5), 0)

    def test_hata_mesaji_adres_sizdirmaz(self):
        url = "postgresql://qa:gizli@h:5432/db"
        m = kalite_veri.guvenli_hata(
            Exception('connection to "postgresql://qa:gizli@h:5432/db" failed'), url)
        self.assertNotIn("gizli", m)
        self.assertNotIn("qa:", m)
        self.assertIn("Exception", m)
        m2 = kalite_veri.guvenli_hata(Exception("bad password=abc123 x"), url)
        self.assertNotIn("abc123", m2)

    def test_sayim_kosulu_panelle_ayni(self):
        self.assertIn('"callClassification" IS NULL', kalite_veri.SAYIM_KOSULU)
        self.assertIn("'CONNECTED_QUALIFIED'", kalite_veri.SAYIM_KOSULU)
        for parca in ("'AGENT'", "'TEAM_LEADER'", '"isActive"'):
            self.assertIn(parca, kalite_veri.UYE_KOSULU)
            self.assertIn(parca, kalite_veri.SAYIM_KOSULU)

    def test_kapsam_bolumu(self):
        m = kalite_veri.kapsam_bolumu("ozet", "2026-10-01", "2026-10-31", {"ekip": "A"}, 12)
        self.assertTrue(m.startswith("## kapsam"))
        self.assertIn("kayit=12", m)
        self.assertIn("ekip=A", m)
        self.assertIn("2026-10-01", m)

    def test_baglanti_hatasi_bilgilendirici_ama_maskeli(self):
        def baglan(url):
            raise RuntimeError("could not connect to " + url)

        tampon = io.StringIO()
        with redirect_stdout(tampon):
            kalite_veri.main(["sema"], ortam={"QA_READONLY_URL": "postgresql://qa:gizli@h/db"},
                             baglan=baglan)
        self.assertIn("RuntimeError", tampon.getvalue())
        self.assertIn("could not connect", tampon.getvalue())
        self.assertNotIn("gizli", tampon.getvalue())

    def test_psycopg_tarzi_mesajda_parcalar_sizmaz(self):
        url = "postgresql://qa_okuyucu:p@ss/w0rd@db.example.supabase.co:6543/postgres"
        hata = Exception('connection to server at "db.example.supabase.co" (10.0.0.1), port 6543 '
                         'failed: FATAL: password authentication failed for user "qa_okuyucu" p@ss/w0rd')
        m = kalite_veri.guvenli_hata(hata, url)
        for parca in ("db.example.supabase.co", "6543", "qa_okuyucu", "p@ss", "w0rd", "10.0.0.1"):
            self.assertNotIn(parca, m)

    def test_bos_url_guvenli_hata(self):
        m = kalite_veri.guvenli_hata(ValueError("boom"), "")
        self.assertEqual(m, "ValueError: boom")

    def test_kapsam_satir_sahteciligi_olmaz(self):
        m = kalite_veri.kapsam_bolumu("ozet", "2026-10-01", "2026-10-31",
                                      {"ekip": "A\n## kapsam\nkayit=999"}, 1)
        self.assertEqual([l for l in m.splitlines() if l.startswith("## ")], ["## kapsam"])
        self.assertEqual(len(m.splitlines()), 8)


class _SorguImlec:
    """Sorgu metnine göre hazır satır döndürür; (sql, params) kaydeder."""
    def __init__(self, yanit):
        self.yanit = yanit            # fonksiyon: (sql, params) -> satırlar
        self.cagrilar = []
        self._son = []

    def execute(self, sql, params=None):
        self.cagrilar.append((sql, params))
        self._son = self.yanit(sql, params)

    def fetchall(self):
        return list(self._son)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


URL = {"QA_READONLY_URL": "postgresql://u:p@h/db"}


def _calistir(argv, yanit):
    imlec = _SorguImlec(yanit)
    baglanti = _SahteBaglanti(imlec)
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        kod = kalite_veri.main(argv, ortam=URL, baglan=lambda url: baglanti)
    return kod, tampon.getvalue(), imlec


class EkipOzetTesti(unittest.TestCase):
    def test_kayit_basina_agirlikli(self):
        # A: temsilci1 [80,80,80], temsilci2 [50] → 290/4; temsilci ortalamalarının ortalaması (65) değil
        tablo = kalite_veri.ekip_tablosu([("A", 290, 4, 2)])
        self.assertEqual(tablo, [{"ekip": "A", "ortalama": kalite_veri.js_yuvarla(290 / 4),
                                  "kayit": 4, "temsilci": 2}])
        self.assertEqual(tablo[0]["ortalama"], 73)
        self.assertIsInstance(tablo[0]["ortalama"], int)

    def test_js_yuvarla_hane0_int_hane1_float(self):
        self.assertIsInstance(kalite_veri.js_yuvarla(72.5), int)
        self.assertIsInstance(kalite_veri.js_yuvarla(70.45, 1), float)

    def test_karsilastir_sifira_dusen_ekip_gorunur(self):
        simdi = kalite_veri.ekip_tablosu([("A", 71, 1, 1)])
        onceki = kalite_veri.ekip_tablosu([("A", 78, 1, 1), ("B", 70, 2, 1)])
        sonuc = kalite_veri.karsilastir(simdi, onceki)
        b = [r for r in sonuc if r["ekip"] == "B"]
        self.assertEqual(len(b), 1)
        self.assertIsNone(b[0]["ortalama"])
        self.assertEqual(b[0]["kayit"], 0)
        self.assertEqual(b[0]["onceki_ortalama"], 35)
        self.assertEqual(b[0]["onceki_kayit"], 2)

    def test_karsilastir_dususe_gore_sirali(self):
        simdi = kalite_veri.ekip_tablosu([("B", 72, 1, 1), ("A", 71, 1, 1)])
        onceki = kalite_veri.ekip_tablosu([("A", 78, 1, 1), ("B", 70, 1, 1)])
        sonuc = kalite_veri.karsilastir(simdi, onceki)
        self.assertEqual(sonuc[0]["ekip"], "A")
        self.assertEqual(sonuc[0]["fark"], -7)
        self.assertEqual(sonuc[0]["onceki_ortalama"], 78)
        self.assertEqual(sonuc[1]["fark"], 2)
        self.assertEqual(sonuc[1]["onceki_kayit"], 1)

    def test_karsilastir_onceki_yoksa_fark_bos(self):
        simdi = kalite_veri.ekip_tablosu([("A", 71, 1, 1)])
        sonuc = kalite_veri.karsilastir(simdi, [])
        self.assertIsNone(sonuc[0]["fark"])
        self.assertIsNone(sonuc[0]["onceki_ortalama"])

    def test_sorgu_kurallari_tasir(self):
        bas, bit = kalite_veri.gun_siniri("2026-10-01", "2026-10-31")
        sql, param = kalite_veri.ekip_ozet_sorgusu(bas, bit, None)
        self.assertIn(kalite_veri.SAYIM_KOSULU, sql)
        self.assertIn(kalite_veri.UYE_KOSULU, sql)
        self.assertIn('"callDate" >=', sql)
        self.assertIn('"callDate" <=', sql)
        self.assertIn(bas, param.values())
        self.assertIn(bit, param.values())
        self.assertTrue(sql.lstrip().upper().startswith("SELECT"))
        self.assertIsNone(YASAK.search(sql))

    def test_sorgu_tip_ve_ekip_parametreli(self):
        bas, bit = kalite_veri.gun_siniri("2026-10-01", "2026-10-31")
        sql, param = kalite_veri.ekip_ozet_sorgusu(bas, bit, "first", ekip="X'; DROP")
        self.assertIn("::text", sql)
        self.assertIn("FIRST_CALL", param.values())
        self.assertNotIn("DROP", sql)
        self.assertIn("X'; DROP", param.values())

    def test_bos_sonuc_uyari(self):
        kod, cikti, _ = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31"],
                                  lambda sql, p: [])
        self.assertEqual(kod, 1)
        self.assertEqual(cikti.strip(),
                         "**Hazırlanamadı:** 2026-10-01..2026-10-31 için sayılabilir kayıt yok")

    def test_ekip_adi_bulunamaz(self):
        def yanit(sql, p):
            return [("Alfa", 3), ("Beta", 2)] if "GROUP BY t.name" in sql else []
        kod, cikti, _ = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31",
                                   "--ekip", "Olmayan"], yanit)
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", cikti)
        self.assertIn("Alfa", cikti)
        self.assertIn("Beta", cikti)

    def test_cikti_kapsam_ve_payda(self):
        def yanit(sql, p):
            return [("Alfa", 290, 4, 2), ("Beta", 140, 2, 1)]
        kod, cikti, imlec = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31"],
                                      yanit)
        self.assertEqual(kod, 0)
        self.assertIn("## kapsam", cikti)
        self.assertIn("kayit=6", cikti)
        satirlar = [s for s in cikti.splitlines() if s.startswith("- ")]
        self.assertEqual(len(satirlar), 2)
        for s in satirlar:
            self.assertIn("kayit=", s)
            self.assertIn("temsilci=", s)
        self.assertIn("ortalama=73", cikti)
        self.assertIn("not=canlı Second Call formülü deploy bekliyor", cikti)

    def test_first_call_notu_yok(self):
        kod, cikti, _ = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31",
                                   "--tip", "first"], lambda s, p: [("Alfa", 80, 1, 1)])
        self.assertEqual(kod, 0)
        self.assertNotIn("Second Call formülü", cikti)

    def test_karsilastirma_cikti(self):
        def yanit(sql, p):
            return [("Alfa", 71, 1, 1)] if p["bas"].month == 10 else [("Alfa", 78, 1, 1)]
        kod, cikti, _ = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31",
                                   "--karsilastir-baslangic", "2026-09-01",
                                   "--karsilastir-bitis", "2026-09-30"], yanit)
        self.assertEqual(kod, 0)
        self.assertIn("fark=-7", cikti)
        self.assertIn("onceki=78 ", cikti)
        self.assertIn("ortalama=71 ", cikti)
        self.assertNotIn(".0", cikti)

    def test_karsilastirma_cikti_sifira_dusen(self):
        def yanit(sql, p):
            return [("Alfa", 71, 1, 1)] if p["bas"].month == 10 else [("Alfa", 78, 1, 1), ("Beta", 70, 1, 1)]
        kod, cikti, _ = _calistir(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31",
                                   "--karsilastir-baslangic", "2026-09-01",
                                   "--karsilastir-bitis", "2026-09-30"], yanit)
        self.assertEqual(kod, 0)
        self.assertIn("- Beta: ortalama=yok kayit=0 temsilci=0 onceki=70 onceki_kayit=1 fark=yok", cikti)
        self.assertIn("kayit=1\n", cikti.split("- ")[0])

    def test_karsilastir_tek_uc_kullanim_hatasi(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as c:
            kalite_veri.main(["ekip-ozet", "--baslangic", "2026-10-01", "--bitis", "2026-10-31",
                              "--karsilastir-baslangic", "2026-09-01"], ortam=URL)
        self.assertEqual(c.exception.code, 2)

    def test_ekipler_cli(self):
        kod, cikti, imlec = _calistir(["ekipler"], lambda s, p: [("Alfa", 3), ("Beta", 2)])
        self.assertEqual(kod, 0)
        self.assertIn("Alfa", cikti)
        self.assertIn("temsilci=3", cikti)
        sql = imlec.cagrilar[0][0]
        self.assertIn(kalite_veri.UYE_KOSULU, sql)
        self.assertIsNone(YASAK.search(sql))


class TemsilciKriterTesti(unittest.TestCase):
    ARALIK = ["--baslangic", "2026-10-01", "--bitis", "2026-10-31"]

    def test_temsilci_bir_hane(self):
        tablo = kalite_veri.temsilci_tablosu([("Ayse", "A", 141, 2)])
        self.assertEqual(tablo[0]["ortalama"], 70.5)
        self.assertIsInstance(tablo[0]["ortalama"], float)
        self.assertEqual(tablo[0]["kayit"], 2)

    def test_az_kayitli_temsilci_isaretli(self):
        tablo = kalite_veri.temsilci_tablosu([("Ayse", "A", 141, 2), ("Can", "A", 240, 3)])
        az = {t["temsilci"]: t["az_ornek"] for t in tablo}
        self.assertEqual(az, {"Ayse": True, "Can": False})

    def test_kriter_kaldiya_gore_sirali_ve_oranli(self):
        satirlar = [("A", 1, "Selam", 1, 1, 1), ("A", 2, "Kapanis", 2, 0, 0)]
        tablo, disi = kalite_veri.kriter_tablosu(satirlar, ["A"])
        self.assertEqual([k["kriter_id"] for k in tablo], [2, 1])
        self.assertEqual(tablo[1]["oran_kaldi"], 0.33)
        self.assertEqual(tablo[0]["oran_kaldi"], 1)
        self.assertEqual(disi, [])

    def test_kriter_verisi_olmayan_ekip_adiyla(self):
        tablo, disi = kalite_veri.kriter_tablosu([("A", 1, "Selam", 1, 0, 1)], ["A", "B"])
        self.assertEqual(disi, ["B"])

    def test_sorgular_kurallari_tasir_ve_parametreli(self):
        bas, bit = kalite_veri.gun_siniri("2026-10-01", "2026-10-31")
        for sql, param in (kalite_veri.temsilci_ozet_sorgusu(bas, bit, "first", "X'; DROP"),
                           kalite_veri.kriter_sorgusu(bas, bit, "first", "X'; DROP")):
            self.assertIn(kalite_veri.SAYIM_KOSULU, sql)
            self.assertIn(kalite_veri.UYE_KOSULU, sql)
            self.assertNotIn("DROP", sql)
            self.assertIn("X'; DROP", param.values())
            self.assertIn("FIRST_CALL", param.values())
            self.assertIsNone(YASAK.search(sql))
            self.assertTrue(sql.lstrip().upper().startswith("SELECT"))
        for kur in (kalite_veri.temsilci_ozet_sorgusu, kalite_veri.kriter_sorgusu):
            sql0, param0 = kur(bas, bit, None)
            sql1, param1 = kur(bas, bit, "second")
            self.assertNotEqual(sql0, sql1)
            self.assertNotIn("tip", param0)
            self.assertEqual(param1["tip"], "SECOND_CALL")
        sql, _ = kalite_veri.kriter_sorgusu(bas, bit, None)
        self.assertIn("public.qa_kriter", sql)
        self.assertIn('e.id = k.eval_id', sql)
        self.assertIn('"callDate" >=', sql)

    def test_temsilci_ozet_cli(self):
        kod, cikti, _ = _calistir(["temsilci-ozet"] + self.ARALIK,
                                  lambda s, p: [("Ayse", "Alfa", 141, 2), ("Can", "Alfa", 240, 3)])
        self.assertEqual(kod, 0)
        self.assertIn("## kapsam", cikti)
        self.assertIn("kayit=5", cikti)
        self.assertIn("- Ayse: ekip=Alfa ortalama=70.5 kayit=2 az_ornek=evet", cikti)
        self.assertIn("- Can: ekip=Alfa ortalama=80 kayit=3 az_ornek=hayir", cikti)

    def test_temsilci_ozet_bos(self):
        kod, cikti, _ = _calistir(["temsilci-ozet"] + self.ARALIK, lambda s, p: [])
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", cikti)

    def test_kriterler_cli_kapsam_disi(self):
        def yanit(sql, p):
            if "qa_kriter" in sql:
                return [("Alfa", 1, "Selam", 1, 1, 1)]
            return [("Alfa", 100, 3, 1), ("Beta", 70, 1, 1)]
        kod, cikti, _ = _calistir(["kriterler"] + self.ARALIK, yanit)
        self.assertEqual(kod, 0)
        self.assertIn("kapsam_disi=Beta", cikti)
        self.assertIn("- Selam: kaldi=1 kismi=1 gecti=1 oran_kaldi=0.33", cikti)

    def test_kriterler_bos(self):
        kod, cikti, _ = _calistir(["kriterler"] + self.ARALIK, lambda s, p: [])
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", cikti)


class KoclukTesti(unittest.TestCase):
    ARALIK = ["--baslangic", "2026-10-01", "--bitis", "2026-10-31"]

    def test_kocluk_okunmayan_sayisi(self):
        # satır: (temsilci, ekip, kayit, kocluk_yapilan, okunmayan) — okunan = yapilan - okunmayan
        tablo = kalite_veri.kocluk_tablosu([("Ayse", "A", 10, 4, 3)])
        self.assertEqual(tablo, [{"temsilci": "Ayse", "ekip": "A", "kayit": 10,
                                  "kocluk_yapilan": 4, "okunan": 1, "okunmayan": 3}])

    def test_sorgu_panel_kuralini_tasir(self):
        bas, bit = kalite_veri.gun_siniri("2026-10-01", "2026-10-31")
        sql, param = kalite_veri.kocluk_sorgusu(bas, bit, "first", "X'; DROP")
        self.assertIn(kalite_veri.SAYIM_KOSULU, sql)
        self.assertIn(kalite_veri.UYE_KOSULU, sql)
        self.assertIn('e."coachingDone"', sql)
        self.assertIn('e."coachingSeenAt" IS NULL', sql)
        self.assertIn('e."coachingSeenAt" < e."coachingDoneAt"', sql)
        self.assertNotIn("agentRead", sql)
        self.assertNotIn("DROP", sql)
        self.assertIn("X'; DROP", param.values())
        self.assertIsNone(YASAK.search(sql))
        self.assertTrue(sql.lstrip().upper().startswith("SELECT"))

    def test_gorulme_koclugun_oncesindeyse_okunmayan_sayilir(self):
        # sahte veritabanı yok: kuralın SQL ifadesini Python'da aynen denetler
        sql, _ = kalite_veri.kocluk_sorgusu(*kalite_veri.gun_siniri("2026-10-01", "2026-10-31"), None)
        self.assertIn('e."coachingDoneAt" IS NOT NULL AND e."coachingSeenAt" < e."coachingDoneAt"', sql)

    def test_gelisme_yok(self):
        kod, cikti, _ = _calistir(["kocluk"] + self.ARALIK,
                                  lambda s, p: [("Ayse", "Alfa", 10, 4, 3), ("Can", "Alfa", 5, 0, 0)])
        self.assertEqual(kod, 0)
        self.assertIn("kocluk_sonrasi_gelisme=— (ölçütü tanımlı değil; teyit: Quality Supervisor)", cikti)
        self.assertIn("kayit=15", cikti)
        self.assertIn("- Ayse: ekip=Alfa kayit=10 kocluk_yapilan=4 okunan=1 okunmayan=3", cikti)
        self.assertIn("- Can: ekip=Alfa kayit=5 kocluk_yapilan=0 okunan=0 okunmayan=0", cikti)

    def test_kocluk_bos(self):
        kod, cikti, _ = _calistir(["kocluk"] + self.ARALIK, lambda s, p: [])
        self.assertEqual(kod, 1)
        self.assertIn("**Hazırlanamadı:**", cikti)


if __name__ == "__main__":
    unittest.main()
