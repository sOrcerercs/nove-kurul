"""Panel API: Uygulama.istek uçları. Geçici kök, fikstür e-postaları, soketsiz."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import panel  # noqa: E402
import panel_kimlik  # noqa: E402
import soru_kapisi  # noqa: E402

SIFRE = "gizli-sifre-123"
SORU = "geçen ay satış görüşmelerinde kalite nasıl gitti"
UYE, DIGER, YON = "uye@example.com", "diger@example.com", "yonetici@example.com"


class ApiTesti(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self._gecici.cleanup)
        self.kok = Path(self._gecici.name)
        (self.kok / "deploy").mkdir()
        self.roller({UYE: "kurul", DIGER: "kurul", YON: "yonetici"})
        p = mock.patch.object(panel_kimlik, "PBKDF2_TUR", 1000)
        p.start()
        self.addCleanup(p.stop)
        panel_kimlik.kullanici_ekle(self.kok, UYE, "Deneme Üye", SIFRE)
        panel_kimlik.kullanici_ekle(self.kok, DIGER, "Diğer Üye", SIFRE)
        panel_kimlik.kullanici_ekle(self.kok, YON, "Deneme Yönetici", SIFRE)
        self.yeni = mock.MagicMock(wraps=soru_kapisi.yeni)
        self.ilerletici = mock.MagicMock()
        self.uyg = panel.Uygulama(self.kok, ilerletici=self.ilerletici, yeni=self.yeni)

    def roller(self, d):
        (self.kok / "deploy" / "roller.json").write_text(json.dumps(d), encoding="utf-8")

    def giris(self, eposta=UYE, sifre=SIFRE, uyg=None, ip="127.0.0.1"):
        uyg = uyg or self.uyg
        govde = json.dumps({"eposta": eposta, "sifre": sifre}).encode()
        kod, g, basliklar = uyg.istek("POST", "/api/giris", govde, None, ip)
        cerez = None
        for ad, deger in basliklar:
            if ad == "Set-Cookie":
                cerez = deger.split(";")[0].split("=", 1)[1]
        return kod, g, basliklar, cerez

    def soru(self, cerez, metin=SORU, ekstra=None):
        d = {"soru": metin}
        d.update(ekstra or {})
        return self.uyg.istek("POST", "/api/soru", json.dumps(d).encode(), cerez)

    def test_cerezsiz_bes_uc_401(self):
        for yontem, yol in (("GET", "/api/ben"), ("POST", "/api/cikis"), ("POST", "/api/soru"),
                            ("GET", "/api/sorular/x"), ("GET", "/api/yanitlar")):
            kod, g, _ = self.uyg.istek(yontem, yol, b"{}", None)
            self.assertEqual((kod, g), (401, {"hata": "oturum yok"}), yol)

    def test_giris_govdesi_ve_cerez(self):
        kod, g, basliklar, cerez = self.giris()
        self.assertEqual(kod, 200)
        self.assertEqual(g, {"ad": "Deneme Üye", "basHarf": "DÜ", "rol": "kurul"})
        c = dict(basliklar)["Set-Cookie"]
        self.assertTrue(c.startswith("nove_oturum="))
        for parca in ("HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=43200"):
            self.assertIn(parca, c)
        self.assertNotIn("Secure", c)
        self.assertTrue(cerez)
        kod, g, _ = self.uyg.istek("GET", "/api/ben", b"", cerez)
        self.assertEqual((kod, g["rol"]), (200, "kurul"))

    def test_https_arkasinda_secure(self):
        uyg = panel.Uygulama(self.kok, https=True)
        _, _, basliklar, _ = self.giris(uyg=uyg)
        self.assertTrue(dict(basliklar)["Set-Cookie"].endswith("; Secure"))

    def test_yanlis_sifre_401_altincida_429(self):
        for _ in range(5):
            self.assertEqual(self.giris(sifre="yanlis-sifre-1")[0], 401)
        self.assertEqual(self.giris(sifre="yanlis-sifre-1")[0], 429)
        self.assertEqual(self.giris()[0], 429)

    def test_soran_oturumdan_alinir(self):
        _, _, _, c = self.giris()
        self.soru(c, ekstra={"soran": YON})
        self.assertEqual(self.yeni.call_args[0][2], UYE)

    def test_soru_acildi_arastiriliyor_ve_tetikler(self):
        _, _, _, c = self.giris()
        kod, g, _ = self.soru(c)
        self.assertEqual(kod, 200)
        self.assertEqual(g["durum"], "arastiriliyor")
        self.assertTrue(g["soru_id"])
        self.ilerletici.tetikle.assert_called_once()

    def test_kisa_soru_reddedildi_tetiklemez(self):
        _, _, _, c = self.giris()
        kod, g, _ = self.soru(c, "ne oldu")
        self.assertEqual(kod, 200)
        self.assertEqual(g["durum"], "reddedildi")
        self.assertIn("soru çok kısa", g["sebep"])
        self.ilerletici.tetikle.assert_not_called()

    def test_gunluk_hak_yeniden_gelir(self):
        _, _, _, c = self.giris()
        with mock.patch.object(ayar, "KURUL_UYESI_GUNLUK_SORU", 1):
            self.assertEqual(self.soru(c)[1]["durum"], "arastiriliyor")
            g = self.soru(c, "bu hafta hangi temsilci en çok geliştirme gerektiriyor")[1]
        self.assertEqual(g["durum"], "reddedildi")
        self.assertIn("soru hakkın doldu", g["sebep"])

    def test_ayni_soru_iki_kez_tek_kayit(self):
        _, _, _, c = self.giris()
        ilk = self.soru(c)[1]
        ikinci = self.soru(c)[1]
        self.assertEqual(ikinci["soru_id"], ilk["soru_id"])
        self.assertIn("bilgi", ikinci)
        self.assertEqual(len(list((self.kok / "sirket-log" / "sorular").iterdir())), 1)
        self.ilerletici.tetikle.assert_called_once()

    def test_mesai_disi_notu(self):
        _, _, _, c = self.giris()
        with mock.patch.object(ayar, "mesaide_mi", return_value=False):
            g = self.soru(c)[1]
        self.assertIn("mesai dışı", g["not"])

    def test_baskasinin_sorusu_404(self):
        _, _, _, c = self.giris()
        sid = self.soru(c)[1]["soru_id"]
        _, _, _, c2 = self.giris(DIGER)
        kod, g, _ = self.uyg.istek("GET", f"/api/sorular/{sid}", b"", c2)
        self.assertEqual((kod, g), (404, {"hata": "bulunamadı"}))
        self.assertEqual(self.uyg.istek("GET", f"/api/sorular/{sid}", b"", c)[0], 200)

    def test_gecersiz_id_404(self):
        _, _, _, c = self.giris()
        self.assertEqual(self.uyg.istek("GET", "/api/sorular/..%2F..%2Fdeploy", b"", c)[0], 404)

    def test_kurul_ham_gerekceyi_almaz_yonetici_alir(self):
        import yanit_defteri
        _, _, _, c = self.giris()
        sid = self.soru(c)[1]["soru_id"]
        gizli = "HAM-GEREKCE-METNI"
        yol = yanit_defteri.yol(sid, self.kok)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(f"# {sid}\n- soru: {SORU}\n- soran: {UYE}\n- etiket: onaylanamadı\n"
                       f"- gorunurluk: yonetici\n\n## Gerekçe\n{gizli}\n", encoding="utf-8")
        _, kurul_g, _ = self.uyg.istek("GET", f"/api/sorular/{sid}", b"", c)
        self.assertNotIn(gizli, json.dumps(kurul_g, ensure_ascii=False))
        _, _, _, cy = self.giris(YON)
        _, yon_g, _ = self.uyg.istek("GET", f"/api/sorular/{sid}", b"", cy)
        self.assertIn(gizli, json.dumps(yon_g, ensure_ascii=False))
        kod, liste, _ = self.uyg.istek("GET", "/api/yanitlar", b"", c)
        self.assertEqual(kod, 200)
        self.assertNotIn(gizli, json.dumps(liste, ensure_ascii=False))

    def test_cikis_sonrasi_401(self):
        _, _, _, c = self.giris()
        kod, g, basliklar = self.uyg.istek("POST", "/api/cikis", b"", c)
        self.assertEqual((kod, g), (200, {}))
        self.assertIn("Max-Age=0", dict(basliklar)["Set-Cookie"])
        self.assertEqual(self.uyg.istek("GET", "/api/ben", b"", c)[0], 401)

    def test_rol_silinince_401(self):
        _, _, _, c = self.giris()
        self.roller({DIGER: "kurul"})
        self.assertEqual(self.uyg.istek("GET", "/api/ben", b"", c)[0], 401)

    def test_bozuk_json_400(self):
        _, _, _, c = self.giris()
        for govde in (b"{bozuk", b"[1]", b'"x"'):
            self.assertEqual(self.uyg.istek("POST", "/api/soru", govde, c)[0], 400)
        self.assertEqual(self.uyg.istek("POST", "/api/soru", b'{"soru": 5}', c)[0], 400)
        self.assertEqual(self.uyg.istek("POST", "/api/soru", b'{"soru": "  "}', c)[0], 400)

    def test_buyuk_govde_413(self):
        _, _, _, c = self.giris()
        govde = b'{"soru": "' + b"a" * panel.GOVDE_SINIRI + b'"}'
        self.assertEqual(self.uyg.istek("POST", "/api/soru", govde, c)[0], 413)

    def test_yanlis_yontem_405(self):
        _, _, _, c = self.giris()
        self.assertEqual(self.uyg.istek("GET", "/api/soru", b"", c)[0], 405)
        self.assertEqual(self.uyg.istek("GET", "/api/olmayan", b"", c)[0], 404)

    def test_beklenmeyen_istisna_500_ayrintisiz(self):
        _, _, _, c = self.giris()
        self.yeni.side_effect = RuntimeError("SIR-AYRINTI")
        kod, g, _ = self.soru(c)
        self.assertEqual((kod, g), (500, {"hata": "sunucu hatası"}))

    def test_belirtec_ve_sifre_dosyaya_yazilmaz(self):
        _, _, _, c = self.giris()
        self.soru(c)
        for yol in self.kok.rglob("*"):
            if yol.is_file():
                metin = yol.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn(c, metin, yol)
                self.assertNotIn(SIFRE, metin, yol)

    def test_panel_yanitlara_yazmaz(self):
        _, _, _, c = self.giris()
        self.soru(c)
        self.assertFalse((self.kok / "yanitlar").exists())


if __name__ == "__main__":
    unittest.main()
