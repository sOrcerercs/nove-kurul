"""bin/tasima.py --paketle: S-1 durumu tek arşiv; .env asla; değer ve dosya adı basmaz. Geçici kök, kurgusal sırlar."""
import fcntl
import hashlib
import io
import os
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import tasima  # noqa: E402

BOS = lambda kok: []  # noqa: E731
SIMDI = datetime(2026, 11, 24, 8, 40)
IZINLI = {
    "yanitlar/s1.md", "sirket-log/sorular/s1.md", "sirket-log/dagitici.log",
    "deploy/roller.json", "deploy/kullanicilar.json", "deploy/posta-alicilari.json",
    "formlar/onayli/kalite.md", "takimlar/kalite/defter.md", "takimlar/kalite/durum.json",
    "takimlar/kalite/kosu/k.md", "takimlar/kalite/cikti/c.md", "takimlar/bekci-telemetri.jsonl",
}


def yaz(kok, yol, icerik="x\n"):
    p = Path(kok) / yol
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(icerik, encoding="utf-8")


def kur(kok):
    yaz(kok, "yanitlar/s1.md")
    yaz(kok, "sirket-log/sorular/s1.md", "# Soru\n- durum: iletildi\n")
    yaz(kok, "sirket-log/dagitici.log")
    yaz(kok, "sirket-log/posta/.kilit")
    yaz(kok, "sirket-log/.env.yedek", "ANTHROPIC_API_KEY=sk-ant-GIZLI-4711\n")
    for a in ("roller", "kullanicilar", "posta-alicilari"):
        yaz(kok, f"deploy/{a}.json", '{"uye@example.com": "kurul"}')
    yaz(kok, "deploy/roller.json.example")
    yaz(kok, "formlar/onayli/kalite.md")
    yaz(kok, "formlar/gelen/x.md")
    for a in ("defter.md", "durum.json", "kurallar.md", "takim.md", "kosu/k.md", "cikti/c.md", "veri/v.csv"):
        yaz(kok, f"takimlar/kalite/{a}")
    yaz(kok, "takimlar/_iskelet/defter.md")
    yaz(kok, "takimlar/bekci-telemetri.jsonl")
    yaz(kok, ".env", "ANTHROPIC_API_KEY=sk-ant-GIZLI-4711\n")
    yaz(kok, ".DS_Store")


def uyeler(arsiv):
    with tarfile.open(arsiv, "r:gz") as t:
        return set(t.getnames())


class Taban(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.kok = Path(self.t.name) / "kok"
        self.kok.mkdir()
        self.cikti = Path(self.t.name) / "cikti"
        self.cikti.mkdir()
        kur(self.kok)

    def main(self, argv, ortam=None):
        g = io.StringIO()
        with redirect_stdout(g):
            kod = tasima.main(argv, self.kok, ortam=ortam if ortam is not None else {})
        return kod, g.getvalue()


class IzinTest(unittest.TestCase):
    def test_izinli_mi(self):
        for y in ("yanitlar/a.md", "sirket-log/sorular/a.md", "deploy/roller.json",
                  "takimlar/kalite/kosu/k.md", "takimlar/bekci-telemetri.jsonl"):
            self.assertTrue(tasima.izinli_mi(y), y)
        for y in (".env", "sirket-log/.env.yedek", "yanitlar/../.env", "/etc/passwd",
                  "deploy/roller.json.example", "deploy/x.json", "takimlar/kalite/kurallar.md",
                  "takimlar/kalite/veri/v.csv", "takimlar/_iskelet/defter.md", "formlar/gelen/x.md",
                  "bin/ayar.py", "sirket-log/posta/.kilit", "yanitlar/.DS_Store", ""):
            self.assertFalse(tasima.izinli_mi(y), y)

    def test_dosya_kurali_yalniz_birebir(self):
        for y in ("deploy/roller.json/x", "takimlar/bekci-telemetri.jsonl/x", "takimlar/kalite/defter.md/y",
                  "takimlar/kalite/durum.json/z", "deploy/posta-alicilari.json/a/b"):
            self.assertFalse(tasima.izinli_mi(y), y)
        for y in ("formlar/onayli/a/b.md", "takimlar/kalite/kosu/a/b.md", "sirket-log/a/b/c.log"):
            self.assertTrue(tasima.izinli_mi(y), y)

    def test_env_buyuk_kucuk_harf_duyarsiz(self):
        for y in ("yanitlar/.ENV", "yanitlar/.Env.yedek", "sirket-log/.eNv/x.md"):
            self.assertFalse(tasima.izinli_mi(y), y)


class PaketTest(Taban):
    def paketle(self, **kw):
        kw.setdefault("mac_denetimi", BOS)
        kw.setdefault("simdi", SIMDI)
        return tasima.paketle(self.kok, self.cikti, **kw)

    def test_paketler_s1_listesini(self):
        s = self.paketle()
        self.assertEqual(uyeler(s["arsiv"]), IZINLI)
        self.assertEqual(s["toplam"], 12)
        self.assertEqual(s["arsiv"].name, "nove-tasima-20261124-0840.tar.gz")

    def test_env_asla_paketlenmez(self):
        s = self.paketle()
        for u in uyeler(s["arsiv"]):
            self.assertFalse(any(p.startswith(".env") for p in u.split("/")), u)
        with tarfile.open(s["arsiv"], "r:gz") as t:
            for m in t.getmembers():
                self.assertNotIn(b"GIZLI-4711", t.extractfile(m).read())

    def test_saglama_toplami(self):
        s = self.paketle()
        a = s["arsiv"]
        h = hashlib.sha256(a.read_bytes()).hexdigest()
        sha = a.with_name(a.name + ".sha256")
        self.assertEqual(sha.read_text(), h + "  " + a.name + "\n")
        self.assertEqual(s["sha256"], h)
        self.assertEqual(a.stat().st_mode & 0o777, 0o600)
        self.assertEqual(sha.stat().st_mode & 0o777, 0o600)

    def test_acik_soru_varsa_reddeder(self):
        yaz(self.kok, "sirket-log/sorular/s2.md", "# Soru\n- durum: alindi\n")
        e = tasima.engeller(self.kok, BOS)
        self.assertEqual(len(e), 1)
        self.assertIn("açık soru var: 1", e[0])
        self.assertIn("s2", e[0])
        s = self.paketle()
        self.assertIsNone(s["arsiv"])
        self.assertEqual(list(self.cikti.iterdir()), [])
        with mock.patch.object(tasima, "engeller", return_value=e):
            kod, _ = self.main(["--paketle", "--cikti", str(self.cikti)])
        self.assertEqual(kod, 1)

    def test_kilit_doluysa_reddeder(self):
        with open(self.kok / ayar.KOSU_KILIDI, "a") as k:
            fcntl.flock(k, fcntl.LOCK_EX)
            with mock.patch.object(tasima, "engeller", return_value=[]):
                kod, cikti = self.main(["--paketle", "--cikti", str(self.cikti)])
            self.assertEqual(kod, 1)
            self.assertIn("koşu kilidi dolu", cikti)
            self.assertEqual(list(self.cikti.iterdir()), [])
        s = self.paketle()
        self.assertIsNotNone(s["arsiv"])

    def test_paketlerken_kilidi_tutar(self):
        gorulen = []

        def yoklayici(*a, **k):
            gorulen.append(ayar.kosu_suruyor(self.kok))
            raise OSError("durdur")

        with mock.patch.object(tasima.tarfile, "open", side_effect=yoklayici):
            with self.assertRaises(OSError):
                self.paketle()
        self.assertEqual(gorulen, [True])
        self.assertFalse(ayar.kosu_suruyor(self.kok))

    def test_mac_servisleri_acikken_reddeder(self):
        neden = "zamanlayıcı kurulu — önce: python3 bin/zamanla.py --kaldir"
        s = self.paketle(mac_denetimi=lambda k: [neden])
        self.assertIsNone(s["arsiv"])
        self.assertEqual(s["engeller"], [neden])
        self.assertEqual(list(self.cikti.iterdir()), [])
        with mock.patch.object(tasima.zamanla, "durum", return_value=[{"ad": "rapor", "yuklu": True}]), \
                mock.patch.object(tasima.sys, "platform", "darwin"), \
                mock.patch.object(tasima.socket, "create_connection", side_effect=OSError):
            e = tasima.engeller(self.kok)
        self.assertEqual(len(e), 1)
        self.assertIn("--kaldir", e[0])
        with mock.patch.object(tasima.zamanla, "durum") as d, mock.patch.object(tasima.sys, "platform", "linux"):
            self.assertEqual(tasima.engeller(self.kok), [])
            d.assert_not_called()

    def test_eski_etiketli_zamanlayici_engeller(self):
        with mock.patch.object(tasima.zamanla, "durum", return_value=[
                    {"ad": "rapor", "yuklu": False, "eski_yuklu": True, "eski_etiket": "com.nove.rapor"}]), \
                mock.patch.object(tasima.sys, "platform", "darwin"), \
                mock.patch.object(tasima.socket, "create_connection", side_effect=OSError):
            e = tasima.engeller(self.kok)
        self.assertEqual(len(e), 1)
        self.assertIn("zamanlayıcı", e[0])
        self.assertIn("eski etiket", e[0])

    def test_hata_temizligi_rakip_arsivi_silmez(self):
        ad = "nove-tasima-20261124-0840.tar.gz"
        asil = tasima._yeni_dosya

        def rakip_once(hedef):
            def sahte(yol):
                if yol.name == hedef:
                    yol.write_bytes(b"RAKIP")
                return asil(yol)
            return sahte

        for hedef in (ad, ad + ".sha256"):
            with self.subTest(hedef=hedef):
                for f in self.cikti.iterdir():
                    f.unlink()
                with mock.patch.object(tasima, "_yeni_dosya", side_effect=rakip_once(hedef)):
                    with self.assertRaises(tasima.TasimaHatasi):
                        self.paketle()
                self.assertEqual((self.cikti / hedef).read_bytes(), b"RAKIP")
                self.assertEqual([f.name for f in self.cikti.iterdir()], [hedef])

    def test_panel_portu_dinliyorsa_engeller(self):
        with mock.patch.object(tasima.zamanla, "durum", return_value=[]), \
                mock.patch.object(tasima.sys, "platform", "darwin"), \
                mock.patch.object(tasima.socket, "create_connection", return_value=mock.MagicMock()):
            e = tasima.engeller(self.kok)
        self.assertEqual(len(e), 1)
        self.assertIn("8770", e[0])

    def test_sembolik_bag_atlanir(self):
        (self.kok / "yanitlar" / "bag.md").symlink_to(self.kok / ".env")
        self.assertNotIn("yanitlar/bag.md", uyeler(self.paketle()["arsiv"]))

    def test_cikti_depo_icinde_olamaz(self):
        with self.assertRaises(tasima.TasimaHatasi):
            tasima.paketle(self.kok, self.kok / "sirket-log", simdi=SIMDI, mac_denetimi=BOS)
        kod, _ = self.main(["--paketle", "--cikti", str(self.kok / "sirket-log")])
        self.assertEqual(kod, 1)

    def test_ayni_adli_arsiv_ezilmez(self):
        s = self.paketle()
        ilk = s["arsiv"].read_bytes()
        with self.assertRaises(tasima.TasimaHatasi):
            self.paketle()
        self.assertEqual(s["arsiv"].read_bytes(), ilk)
        with mock.patch.object(tasima, "engeller", return_value=[]), \
                mock.patch.object(tasima, "_simdi", return_value=SIMDI):
            kod, _ = self.main(["--paketle", "--cikti", str(self.cikti)])
        self.assertEqual(kod, 1)
        self.assertEqual(s["arsiv"].read_bytes(), ilk)


class MainTest(Taban):
    def test_kuru_yazmaz(self):
        with mock.patch.object(tasima, "engeller", return_value=[]):
            kod, cikti = self.main(["--paketle", "--cikti", str(self.cikti), "--kuru"], {"CLAUDECODE": "1"})
        self.assertEqual(kod, 0)
        self.assertEqual(list(self.cikti.iterdir()), [])
        self.assertIn("→ 12 dosya", cikti)
        self.assertIn("yanitlar/", cikti)
        yaz(self.kok, "sirket-log/sorular/s2.md", "# Soru\n- durum: alindi\n")
        with mock.patch.object(tasima, "engeller", return_value=["açık soru var: 1 (s2)"]):
            kod, cikti = self.main(["--paketle", "--kuru"], {"CLAUDECODE": "1"})
        self.assertEqual(kod, 0)
        self.assertIn("ENGEL", cikti)

    def test_ajan_ortaminda_yazan_kosu_durur(self):
        kod, cikti = self.main(["--paketle", "--cikti", str(self.cikti)], {"CLAUDECODE": "1"})
        self.assertEqual(kod, 1)
        self.assertIn("yalnız --kuru", cikti)
        self.assertEqual(list(self.cikti.iterdir()), [])

    def test_cikti_deger_ve_dosya_adi_tasimaz(self):
        with mock.patch.object(tasima, "engeller", return_value=[]):
            kod, cikti = self.main(["--paketle", "--kuru"])
            self.assertEqual(kod, 0)
            kod2, cikti2 = self.main(["--paketle", "--cikti", str(self.cikti)])
        self.assertEqual(kod2, 0)
        for c in (cikti, cikti2):
            for yasak in ("GIZLI", "example.com", "kalite.md", "s1.md"):
                self.assertNotIn(yasak, c)

    def test_kullanim_hatasi(self):
        for argv in ([], ["--paketle", "--ac", "x"], ["--x"]):
            with mock.patch.object(sys, "stderr", io.StringIO()):
                self.assertEqual(self.main(argv)[0], 2, argv)


if __name__ == "__main__":
    unittest.main()
