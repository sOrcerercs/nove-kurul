"""Panel Yanıt defteri okuma: ayrıştırma, görünürlük, durum, kısa sebep, Markdown. Geçici kök, fikstür e-postaları."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import dagitici  # noqa: E402
import panel_defter as pd  # noqa: E402
import soru_kapisi as qa  # noqa: E402
import soru_kaydi  # noqa: E402
import yanit_defteri  # noqa: E402

TZ = ZoneInfo("Europe/Istanbul")
UYE, DIGER, YON = "uye@example.com", "diger@example.com", "yonetici@example.com"
HAM = "ISARET-HAM-GEREKCE"
GUN = [datetime(2026, 11, g, 12, 0, tzinfo=TZ) for g in (9, 10, 11)]   # Pzt-Çar, mesaide
MESAI_DISI = datetime(2026, 11, 10, 22, 0, tzinfo=TZ)


def kayit(etiket, govde, soran=UYE, tarih="2026-11-10T12:00:00+03:00", ek=""):
    return (f"# Yanıt — x\n- soru: Deneme soru metni\n- soran: {soran}\n- tarih: {tarih}\n- danışman: kalite\n"
            f"- etiket: {etiket}\n- Denetçi: ✔ · CEO: ✔\n{ek}- iletildi: {tarih}\n\n{govde}")


class Taban(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.kok = Path(self.t.name)
        (self.kok / "deploy").mkdir()
        (self.kok / "deploy" / "roller.json").write_text(
            json.dumps({UYE: "kurul", DIGER: "kurul", YON: "yonetici"}), encoding="utf-8")
        self.n = 0

    def soru(self, soran=UYE, simdi=None):
        self.n += 1
        s = qa.yeni(self.kok, f"Bu ay kalite puanı düşük {self.n} numaralı konu hangi ekipte yoğun", soran,
                    simdi=simdi or GUN[0])
        self.assertEqual(s["sonuc"], "acildi", s)
        return s["soru_id"]

    def defterle(self, soru_id, metin):
        yanit_defteri.yaz(self.kok, soru_id, metin)


class AyristirmaTest(unittest.TestCase):
    def test_onayli_kayit(self):
        d = pd.defter_oku(kayit("onaylı", "## Kurula not\nDikkat\n\n## Yanıt\n# Başlık\nmetin\n"))
        self.assertEqual((d["soru"], d["soran"], d["danisman"], d["etiket"]), ("Deneme soru metni", UYE, "kalite", "onaylı"))
        self.assertEqual(d["kurula_not"], "Dikkat")
        self.assertEqual(d["yanit"], "# Başlık\nmetin\n")
        self.assertIsNone(d["gerekce"])
        self.assertIsNone(d["gorunurluk"])

    def test_kurula_not_yok(self):
        d = pd.defter_oku(kayit("onaylı", "## Yanıt\nmetin\n"))
        self.assertIsNone(d["kurula_not"])
        self.assertEqual(d["yanit"], "metin\n")

    def test_onaylanamadi_kayit(self):
        d = pd.defter_oku(kayit("onaylanamadı", f"## Gerekçe\nDenetçi: red — {HAM}\n"))
        self.assertEqual(d["gerekce"], f"Denetçi: red — {HAM}")
        self.assertIsNone(d["yanit"])

    def test_yanit_icindeki_basliklar_bolmez(self):
        d = pd.defter_oku(kayit("onaylı", "## Yanıt\nGiriş\n## Özet\nx\n## Gerekçe\ny\n"))
        self.assertIn("## Özet", d["yanit"])
        self.assertIn("## Gerekçe", d["yanit"])
        self.assertIsNone(d["gerekce"])


class GorunurlukTest(Taban):
    def test_kurul_yalniz_kendini_gorur(self):
        self.assertTrue(pd.gorebilir_mi(UYE, None, UYE, "kurul"))
        self.assertFalse(pd.gorebilir_mi(DIGER, None, UYE, "kurul"))

    def test_kurul_gunluk_raporu_gorur(self):
        self.assertTrue(pd.gorebilir_mi("zamanlayıcı", "kurul", UYE, "kurul"))

    def test_yonetici_hepsini_gorur_ve_soran_alir(self):
        a = self.soru(UYE)
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n", soran=UYE))
        self.assertTrue(pd.gorebilir_mi(UYE, None, YON, "yonetici"))
        self.assertEqual(pd.liste(self.kok, YON, "yonetici")["kayitlar"][0]["soran"], UYE)

    def test_kurul_satirinda_soran_yok(self):
        a = self.soru(UYE)
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n", soran=UYE))
        satir = pd.liste(self.kok, UYE, "kurul")["kayitlar"][0]
        self.assertNotIn("soran", satir)
        self.assertEqual(set(satir), {"soru_id", "tarih", "soru", "danisman", "etiket", "gorunurluk"})


class KisaSebepTest(unittest.TestCase):
    def test_siniflar(self):
        ek = " " + pd.SON_EK
        durumlar = [
            ("Denetçi: red — nim ulaşılamadı: timeout → openai yolu · model bütçeyi reasoning'e harcadı",
             "Yanıt kalite denetiminden geçemedi."),
            ("CEO 2. kez reddetti — kaynak eksik", "Yanıt kalite denetiminden geçemedi."),
            ("CEO 2 kez başlatıldı, karar yazmadı (bkz. sirket-log/ceo.log)", "Süre doldu."),
            ("soru bütçesi doldu: 7.20 USD harcandı, CEO kontrolüne yetmiyor", "Bu sorunun bütçesi doldu."),
            (dagitici.KURULMADI + " — x", "Bu bölüm henüz kurulmadı."),
            ("yönlendirilemedi — Haiku JSON döndürmedi", "Bu soruya şu an güvenilir bir yanıt verilemedi."),
            ("", "Bu soruya şu an güvenilir bir yanıt verilemedi."),
        ]
        for girdi, beklenen in durumlar:
            with self.subTest(girdi=girdi):
                self.assertEqual(pd.kisa_sebep(girdi), beklenen + ek)


class DurumTest(Taban):
    def test_defterde_yoksa_arastiriliyor_ve_not(self):
        a = self.soru(UYE, simdi=MESAI_DISI)
        d = pd.durum(self.kok, a, UYE, "kurul")
        self.assertEqual(d["durum"], "arastiriliyor")
        self.assertIn("mesai dışı", d["not"])
        self.assertEqual(set(d) & {"soru_id", "soru", "zaman", "durum"}, {"soru_id", "soru", "zaman", "durum"})

    def test_onayli_yanitlandi(self):
        a = self.soru()
        self.defterle(a, kayit("onaylı", "## Kurula not\nNot var\n\n## Yanıt\n# Başlık\nmetin\n"))
        d = pd.durum(self.kok, a, UYE, "kurul")
        self.assertEqual(d["durum"], "yanitlandi")
        self.assertIn("<h3>", d["yanit_html"])
        self.assertIn("Not var", d["kurula_not_html"])
        self.assertEqual((d["etiket"], d["danisman"]), ("onaylı", "kalite"))

    def test_ceo_yapilmadi_de_yanitlandi(self):
        a = self.soru()
        self.defterle(a, kayit("CEO kontrolü yapılmadı", "## Yanıt\nmetin\n"))
        d = pd.durum(self.kok, a, UYE, "kurul")
        self.assertEqual((d["durum"], d["etiket"]), ("yanitlandi", "CEO kontrolü yapılmadı"))
        self.assertNotIn("kurula_not_html", d)

    def test_kurul_ham_gerekceyi_almaz(self):
        a = self.soru()
        qa.ilet(self.kok, a, simdi=GUN[0], onaylanamadi=f"Denetçi: red — {HAM}")
        d = pd.durum(self.kok, a, UYE, "kurul")
        self.assertEqual(d["durum"], "onaylanamadi")
        self.assertNotIn("gerekce", d)
        self.assertNotIn(HAM, json.dumps(d, ensure_ascii=False))
        self.assertTrue(d["sebep"].endswith(pd.SON_EK))

    def test_yonetici_ham_gerekceyi_alir(self):
        a = self.soru(UYE)
        qa.ilet(self.kok, a, simdi=GUN[0], onaylanamadi=f"Denetçi: red — {HAM}")
        d = pd.durum(self.kok, a, YON, "yonetici")
        self.assertIn(HAM, d["gerekce"])
        self.assertIn("sebep", d)

    def test_baskasinin_sorusu_none(self):
        a = self.soru(UYE)
        self.assertIsNone(pd.durum(self.kok, a, DIGER, "kurul"))
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n"))
        self.assertIsNone(pd.durum(self.kok, a, DIGER, "kurul"))
        self.assertIsNotNone(pd.durum(self.kok, a, YON, "yonetici"))

    def test_gecersiz_id_none(self):
        for kotu in ("../x", "A B", "", "x" * 65):
            self.assertIsNone(pd.durum(self.kok, kotu, YON, "yonetici"))
        self.assertIsNone(pd.durum(self.kok, "20261110-1200-yok0", YON, "yonetici"))

    def test_liste_siralama_ve_acik(self):
        a = self.soru(UYE, simdi=GUN[0])
        b = self.soru(UYE, simdi=GUN[1])
        c = self.soru(UYE, simdi=GUN[2])      # açık
        d = self.soru(DIGER, simdi=GUN[2])    # başkasının açığı
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n", tarih="2026-11-09T12:00:00+03:00"))
        self.defterle(b, kayit("onaylı", "## Yanıt\nx\n", tarih="2026-11-10T12:00:00+03:00"))
        (self.kok / "yanitlar" / "bozuk.md").write_bytes(b"\xff\xfe")
        s = pd.liste(self.kok, UYE, "kurul")
        self.assertEqual([k["soru_id"] for k in s["kayitlar"]], [b, a])
        self.assertEqual([k["soru_id"] for k in s["acik"]], [c])
        self.assertEqual([k["soru_id"] for k in pd.liste(self.kok, YON, "yonetici")["acik"]], [])
        self.assertEqual([k["soru_id"] for k in pd.liste(self.kok, DIGER, "kurul")["acik"]], [d])

    def test_liste_baskasinin_kaydini_gostermez(self):
        a = self.soru(UYE)
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n", soran=UYE))
        self.assertEqual(pd.liste(self.kok, DIGER, "kurul")["kayitlar"], [])
        b = self.soru(DIGER, simdi=GUN[1])
        self.defterle(b, kayit("onaylı", "## Yanıt\ny\n", soran=DIGER, tarih="2026-11-11T12:00:00+03:00"))
        yon = pd.liste(self.kok, YON, "yonetici")["kayitlar"]
        self.assertEqual([(k["soru_id"], k["soran"]) for k in yon], [(b, DIGER), (a, UYE)])
        self.assertEqual([k["soru_id"] for k in pd.liste(self.kok, UYE, "kurul")["kayitlar"]], [a])

    def test_gunluk_rapor_gorunurluk_satiri_parserdan_gecer(self):
        a, b = "20261110-1100-rpr1", "20261110-1100-rpr2"
        self.defterle(a, kayit("onaylı", "## Yanıt\nrapor\n", soran="zamanlayıcı", ek="- gorunurluk: kurul\n"))
        self.defterle(b, kayit("onaylı", "## Yanıt\nrapor\n", soran="zamanlayıcı"))
        ids = [k["soru_id"] for k in pd.liste(self.kok, UYE, "kurul")["kayitlar"]]
        self.assertEqual(ids, [a])
        self.assertIsNotNone(pd.durum(self.kok, a, UYE, "kurul"))
        self.assertIsNone(pd.durum(self.kok, b, UYE, "kurul"))

    def test_acik_sorular_bitmisleri_saymaz(self):
        a, b, c, d = (self.soru(UYE, simdi=GUN[i % 3]) for i in range(4))
        self.defterle(a, kayit("onaylı", "## Yanıt\nx\n"))
        soru_kaydi.durum_yaz(soru_kaydi.yol(b, self.kok), "yönlendirilemedi")
        soru_kaydi.durum_yaz(soru_kaydi.yol(c, self.kok), "iletildi")
        self.assertEqual(pd.acik_sorular(self.kok), [d])


class BitmisDeftersizTest(Taban):
    def _bitmis(self):
        a = self.soru(UYE, simdi=GUN[0])
        soru_kaydi.durum_yaz(soru_kaydi.yol(a, self.kok), "yönlendirilemedi")
        return a

    def test_durum_kurul_onaylanamadi_gerekcesiz(self):
        a = self._bitmis()
        d = pd.durum(self.kok, a, UYE, "kurul")
        self.assertEqual(d["durum"], "onaylanamadi")
        self.assertEqual(d["sebep"], pd.kisa_sebep(""))
        self.assertNotIn("gerekce", d)

    def test_durum_yonetici_gerekce_alir(self):
        a = self._bitmis()
        d = pd.durum(self.kok, a, UYE, "yonetici")
        self.assertEqual(d["durum"], "onaylanamadi")
        self.assertIn("yönlendirilemedi", d["gerekce"])
        self.assertIn("Yanıt defterinde kaydı yok", d["gerekce"])

    def test_liste_acik_bitmisi_saymaz(self):
        a = self._bitmis()
        c = self.soru(UYE, simdi=GUN[2])
        for rol in ("kurul", "yonetici"):
            ids = [k["soru_id"] for k in pd.liste(self.kok, UYE, rol)["acik"]]
            self.assertNotIn(a, ids)
        self.assertEqual([k["soru_id"] for k in pd.liste(self.kok, UYE, "kurul")["acik"]], [c])


class MarkdownTest(unittest.TestCase):
    def test_script_kacar(self):
        h = pd.md_html("<script>alert(1)</script>")
        self.assertNotIn("<script", h)
        self.assertIn("&lt;script&gt;", h)

    def test_kalin_baslik_liste(self):
        h = pd.md_html("# A\n## B\n#### C\n**kalın** ve `kod`\n- x\n* y\n1. bir\n2. iki")
        for parca in ("<h3>A</h3>", "<h4>B</h4>", "<h5>C</h5>", "<strong>kalın</strong>", "<code>kod</code>",
                      "<ul><li>x</li><li>y</li></ul>", "<ol><li>bir</li><li>iki</li></ol>"):
            self.assertIn(parca, h)

    def test_tablo(self):
        h = pd.md_html("| A | B |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<th>A</th>", h)
        self.assertIn("<td>1</td>", h)
        self.assertIn("<table>", h)

    def test_ayiricisiz_boru_tablo_degil(self):
        h = pd.md_html("| A | B |\n| 1 | 2 |")
        self.assertNotIn("<table", h)
        self.assertIn("<p>", h)

    def test_baglanti_a_uretmez(self):
        self.assertNotIn("<a", pd.md_html("[x](javascript:alert(1))"))

    def test_bos(self):
        self.assertEqual(pd.md_html(""), "")
        self.assertEqual(pd.md_html(None), "")


if __name__ == "__main__":
    unittest.main()
