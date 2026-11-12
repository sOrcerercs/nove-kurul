"""Panel kimliği: kullanıcı dosyası, oturum, deneme freni. Geçici kök, fikstür e-postaları."""
import hashlib
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import panel_kimlik  # noqa: E402

SIFRE = "gizli-sifre-123"


class Saat:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class KimlikTesti(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self._gecici.cleanup)
        self.kok = Path(self._gecici.name)
        (self.kok / "deploy").mkdir()
        self.roller({"uye@example.com": "kurul"})
        p = mock.patch.object(panel_kimlik, "PBKDF2_TUR", 1000)
        p.start()
        self.addCleanup(p.stop)

    def roller(self, d):
        (self.kok / "deploy" / "roller.json").write_text(json.dumps(d), encoding="utf-8")

    def dosya(self):
        return self.kok / "deploy" / "kullanicilar.json"

    def test_ekle_izin_600_ve_duz_sifre_yok(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertEqual(stat.S_IMODE(self.dosya().stat().st_mode), 0o600)
        metin = self.dosya().read_text(encoding="utf-8")
        self.assertNotIn(SIFRE, metin)
        kayit = panel_kimlik.kullanicilar(self.kok)["uye@example.com"]
        for alan in ("tuz", "ozet", "yontem"):
            self.assertIn(alan, kayit)

    def test_dogru_sifre(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertEqual(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE),
                         {"eposta": "uye@example.com", "ad": "Deneme Üye", "rol": "kurul"})

    def test_yanlis_sifre_none(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", "yanlis-sifre-1"))

    def test_bilinmeyen_eposta_none(self):
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "yok@example.com", SIFRE))

    def test_rolde_olmayan_giremez(self):
        panel_kimlik.kullanici_ekle(self.kok, "diger@example.com", "Diğer", SIFRE)
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "diger@example.com", SIFRE))

    def test_pasif_rol_giremez(self):
        self.roller({"uye@example.com": "pasif"})
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE))

    def test_eposta_buyuk_harf_ve_bosluk(self):
        panel_kimlik.kullanici_ekle(self.kok, " UYE@Example.com ", "Deneme Üye", SIFRE)
        self.assertIn("uye@example.com", panel_kimlik.kullanicilar(self.kok))
        self.assertIsNotNone(panel_kimlik.dogrula(self.kok, " UYE@Example.com ", SIFRE))

    def test_ayni_sifre_farkli_ozet(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "A", SIFRE)
        a = panel_kimlik.kullanicilar(self.kok)["uye@example.com"]
        panel_kimlik.kullanici_ekle(self.kok, "diger@example.com", "B", SIFRE)
        b = panel_kimlik.kullanicilar(self.kok)["diger@example.com"]
        self.assertNotEqual(a["tuz"], b["tuz"])
        self.assertNotEqual(a["ozet"], b["ozet"])

    def test_bozuk_dosya_none(self):
        self.dosya().write_text("{bozuk", encoding="utf-8")
        self.assertEqual(panel_kimlik.kullanicilar(self.kok), {})
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE))

    def test_bilinmeyen_yontem_none(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        ham = json.loads(self.dosya().read_text(encoding="utf-8"))
        ham["uye@example.com"]["yontem"] = "argon2id"
        self.dosya().write_text(json.dumps(ham), encoding="utf-8")
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE))

    def test_kisa_sifre_valueerror(self):
        with self.assertRaises(ValueError):
            panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", "kisa")
        self.assertFalse(self.dosya().exists())

    def test_ikinci_ekleme_sifreyi_yeniler(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", "yeni-sifre-456")
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE))
        self.assertIsNotNone(panel_kimlik.dogrula(self.kok, "uye@example.com", "yeni-sifre-456"))

    @unittest.skipUnless(hasattr(hashlib, "scrypt"), "scrypt bu makinede yok")
    def test_scrypt_varsa_kullanilir(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertEqual(panel_kimlik.kullanicilar(self.kok)["uye@example.com"]["yontem"], "scrypt")
        self.assertIsNotNone(panel_kimlik.dogrula(self.kok, "uye@example.com", SIFRE))

    def test_kodlanamayan_sifre_none(self):
        panel_kimlik.kullanici_ekle(self.kok, "uye@example.com", "Deneme Üye", SIFRE)
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "uye@example.com", "\ud800"))
        self.assertIsNone(panel_kimlik.dogrula(self.kok, "yok@example.com", "\ud800"))

    def test_bas_harf(self):
        self.assertEqual(panel_kimlik.bas_harf("Deneme Üye"), "DÜ")
        self.assertEqual(panel_kimlik.bas_harf("Tek"), "T")
        self.assertEqual(panel_kimlik.bas_harf("bir iki üç"), "Bİ")


class OturumTesti(unittest.TestCase):
    def test_oturum_ac_bul_kapat(self):
        o = panel_kimlik.Oturumlar(saat=Saat())
        b = o.ac("uye@example.com", "Deneme Üye")
        self.assertEqual(o.bul(b), {"eposta": "uye@example.com", "ad": "Deneme Üye"})
        o.kapat(b)
        self.assertIsNone(o.bul(b))
        self.assertIsNone(o.bul("yok"))

    def test_oturum_12_saat_sonra_duser(self):
        s = Saat()
        o = panel_kimlik.Oturumlar(saat=s)
        b = o.ac("uye@example.com", "Deneme Üye")
        s.t += 12 * 3600 + 1
        self.assertIsNone(o.bul(b))

    def test_belirtecler_farkli_ve_uzun(self):
        o = panel_kimlik.Oturumlar(saat=Saat())
        a, b = o.ac("uye@example.com", "A"), o.ac("uye@example.com", "A")
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a), 32)


class FrenTesti(unittest.TestCase):
    def test_fren_ayni_eposta_5(self):
        f = panel_kimlik.DenemeFreni(saat=Saat())
        for i in range(4):
            f.basarisiz("uye@example.com", f"10.0.0.{i}")
        self.assertFalse(f.engelli_mi("uye@example.com", "10.0.0.99"))
        f.basarisiz("uye@example.com", "10.0.0.4")
        self.assertTrue(f.engelli_mi("uye@example.com", "10.0.0.99"))

    def test_fren_ayni_ip_5(self):
        f = panel_kimlik.DenemeFreni(saat=Saat())
        for i in range(5):
            f.basarisiz(f"u{i}@example.com", "10.0.0.1")
        self.assertTrue(f.engelli_mi("yeni@example.com", "10.0.0.1"))
        self.assertFalse(f.engelli_mi("yeni@example.com", "10.0.0.2"))

    def test_fren_15_dk_sonra_acilir(self):
        s = Saat()
        f = panel_kimlik.DenemeFreni(saat=s)
        for _ in range(5):
            f.basarisiz("uye@example.com", "10.0.0.1")
        s.t += 15 * 60 + 1
        self.assertFalse(f.engelli_mi("uye@example.com", "10.0.0.1"))

    def test_basarili_giris_eposta_sayacini_siler(self):
        f = panel_kimlik.DenemeFreni(saat=Saat())
        for _ in range(4):
            f.basarisiz("uye@example.com", "10.0.0.1")
        f.basarili("uye@example.com")
        f.basarisiz("uye@example.com", "10.0.0.2")
        self.assertFalse(f.engelli_mi("uye@example.com", "10.0.0.3"))


if __name__ == "__main__":
    unittest.main()
