"""bin/tasima.py --paketle/--ac: S-1 durumu tek arşiv; .env asla; değer ve dosya adı basmaz. Geçici kök, kurgusal sırlar."""
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

    def test_kok_disina_cikan_sembolik_ust_klasor_atlanir(self):
        disari = Path(self.t.name) / "disari"
        yaz(disari, "kosu/k.md", "ANTHROPIC_API_KEY=sk-ant-GIZLI-4711\n")
        (self.kok / "takimlar" / "dis").symlink_to(disari)
        s = self.paketle()
        self.assertNotIn("takimlar/dis/kosu/k.md", uyeler(s["arsiv"]))
        self.assertEqual(uyeler(s["arsiv"]), IZINLI)
        self.assertEqual(s["atlanan"], 1)

    def test_sabit_bag_atlanir(self):
        os.link(self.kok / ".env", self.kok / "yanitlar" / "sert.md")
        s = self.paketle()
        self.assertEqual(uyeler(s["arsiv"]), IZINLI)
        self.assertEqual(s["atlanan"], 1)
        with tarfile.open(s["arsiv"], "r:gz") as t:
            for m in t.getmembers():
                self.assertNotIn(b"GIZLI-4711", t.extractfile(m).read())

    def test_atlanan_sayisi_basilir(self):
        (self.kok / "yanitlar" / "bag.md").symlink_to(self.kok / ".env")
        os.link(self.kok / ".env", self.kok / "yanitlar" / "sert.md")
        with mock.patch.object(tasima, "engeller", return_value=[]):
            kod, cikti = self.main(["--paketle", "--kuru"])
        self.assertEqual(kod, 0)
        self.assertIn("2 dosya atlandı", cikti)
        for yasak in ("bag.md", "sert.md", "GIZLI"):
            self.assertNotIn(yasak, cikti)

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


class AcTaban(Taban):
    """Kaynak `self.kok` (kur ile dolu), hedef `self.hedef` boş klasör; euid testlerde 1000."""

    def setUp(self):
        super().setUp()
        self.hedef = Path(self.t.name) / "hedef"
        self.hedef.mkdir()
        p = mock.patch.object(tasima, "_mac_denetimi", return_value=[])   # Mac'teki 8770/launchd'ye bakmasın
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(tasima, "_euid", return_value=1000)
        p.start()
        self.addCleanup(p.stop)

    def arsivle(self, kaynak=None):
        return tasima.paketle(kaynak or self.kok, self.cikti, simdi=SIMDI, mac_denetimi=BOS)["arsiv"]

    def elle_arsiv(self, uyeler, ad="elle.tar.gz"):
        """uyeler: (ad, tur, veri) — tur: 'dosya' | 'dizin' | 'sembolik' | 'sabit'; geçerli .sha256 ile."""
        arsiv = self.cikti / ad
        with tarfile.open(arsiv, "w:gz") as t:
            for uad, tur, veri in uyeler:
                b = tarfile.TarInfo(uad)
                if tur == "dosya":
                    b.size = len(veri)
                    t.addfile(b, io.BytesIO(veri))
                    continue
                b.type = {"dizin": tarfile.DIRTYPE, "sembolik": tarfile.SYMTYPE, "sabit": tarfile.LNKTYPE}[tur]
                if tur in ("sembolik", "sabit"):
                    b.linkname = veri
                t.addfile(b)
        h = hashlib.sha256(arsiv.read_bytes()).hexdigest()
        arsiv.with_name(arsiv.name + ".sha256").write_text(f"{h}  {arsiv.name}\n")
        return arsiv

    def ac(self, arsiv, **kw):
        kw.setdefault("euid", 1000)
        kw.setdefault("mac_denetimi", BOS)
        return tasima.ac(self.hedef, arsiv, **kw)

    def ac_main(self, argv, ortam=None):
        g = io.StringIO()
        with redirect_stdout(g):
            kod = tasima.main(argv, self.hedef, ortam=ortam if ortam is not None else {})
        return kod, g.getvalue()

    def hedef_icerik(self):
        return sorted(p.relative_to(self.hedef).as_posix() for p in self.hedef.rglob("*")
                      if p.name != ayar.KOSU_KILIDI)


class AcTest(AcTaban):
    def test_gidis_donus(self):
        s = self.ac(self.arsivle())
        self.assertEqual(s["yazilan"], 12)
        self.assertEqual(s["catisan"], [])
        self.assertIsNone(s["yedek"])
        self.assertEqual(tasima.dosyalar(self.hedef), tasima.dosyalar(self.kok))
        for g in tasima.dosyalar(self.kok):
            self.assertEqual((self.hedef / g).read_bytes(), (self.kok / g).read_bytes(), g)
            self.assertEqual((self.hedef / g).stat().st_mode & 0o777, 0o600, g)
        self.assertEqual((self.hedef / "deploy/kullanicilar.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.hedef / "yanitlar").stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.hedef / ".env").exists())
        self.assertFalse(any(".env" in p for p in self.hedef_icerik()))

    def test_saglama_toplami_tutmazsa_reddeder(self):
        arsiv = self.arsivle()
        sha = arsiv.with_name(arsiv.name + ".sha256")
        with open(arsiv, "ab") as f:
            f.write(b"\0")
        with self.assertRaises(tasima.TasimaHatasi) as b:
            self.ac(arsiv)
        self.assertIn("sağlama toplamı", str(b.exception))
        self.assertEqual(list(self.hedef.iterdir()), [])
        sha.write_text("0" * 64 + "  " + arsiv.name + "\n")
        with self.assertRaises(tasima.TasimaHatasi):
            self.ac(arsiv)
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_sha256_dosyasi_yoksa_reddeder(self):
        arsiv = self.arsivle()
        arsiv.with_name(arsiv.name + ".sha256").unlink()
        with self.assertRaises(tasima.TasimaHatasi) as b:
            self.ac(arsiv)
        self.assertIn("sağlama toplamı", str(b.exception))
        self.assertEqual(list(self.hedef.iterdir()), [])
        kod, _ = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_dusmanca_arsiv_tamamen_reddedilir(self):
        iyi = ("yanitlar/iyi.md", "dosya", b"iyi\n")
        durumlar = {
            "ust": [("../disari.md", "dosya", b"x")],
            "mutlak": [("/tmp/x.md", "dosya", b"x")],
            "env": [(".env", "dosya", b"ANTHROPIC_API_KEY=sk-ant-GIZLI-4711\n")],
            "alt_env": [("yanitlar/.env", "dosya", b"x")],
            "alt_env_buyuk": [("yanitlar/.ENV", "dosya", b"x")],
            "kod": [("bin/ayar.py", "dosya", b"x")],
            "kurallar": [("takimlar/kalite/kurallar.md", "dosya", b"x")],
            "dosya_kurali_alti": [("deploy/roller.json/x", "dosya", b"x")],
            "sembolik": [("yanitlar/bag.md", "sembolik", "/etc/passwd")],
            "sabit": [("yanitlar/sert.md", "sabit", "yanitlar/iyi.md")],
            "cift": [("yanitlar/iyi.md", "dosya", b"ikinci\n")],
            "dosya_ust_klasor": [("yanitlar/iyi.md/alt.md", "dosya", b"x")],
        }
        disari_once = sorted(p.name for p in Path(self.t.name).iterdir())
        for ad, kotu in durumlar.items():
            with self.subTest(ad):
                arsiv = self.elle_arsiv([iyi] + kotu, ad=f"{ad}.tar.gz")
                with self.assertRaises(tasima.TasimaHatasi) as b:
                    self.ac(arsiv)
                self.assertIn("arşivde beklenmeyen yol", str(b.exception))
                for yasak in ("disari.md", "passwd", "GIZLI", "ayar.py", "kurallar.md", "bag.md", "sert.md",
                              "iyi.md", "alt.md", "x.md", "roller.json"):
                    self.assertNotIn(yasak, str(b.exception))
                self.assertFalse((self.hedef / "yanitlar").exists())
                self.assertEqual(self.hedef_icerik(), [])
                self.assertEqual(sorted(p.name for p in Path(self.t.name).iterdir()), disari_once)
                self.assertFalse((self.hedef.parent / "disari.md").exists())

    def test_dusmanca_arsiv_adet_ve_ust_klasor_basar(self):
        arsiv = self.elle_arsiv([("yanitlar/a.md", "sembolik", "/etc/passwd"),
                                 ("yanitlar/b.md", "sembolik", "/etc/passwd"), ("bin/ayar.py", "dosya", b"x")])
        with self.assertRaises(tasima.TasimaHatasi) as b:
            self.ac(arsiv)
        self.assertIn("3 üye", str(b.exception))
        self.assertIn("yanitlar/", str(b.exception))
        self.assertIn("bin/", str(b.exception))

    def test_kesik_arsiv_okunamadi(self):
        tam = self.arsivle().read_bytes()
        for ad, veri in (("kesik", tam[:len(tam) // 2]), ("kesik_son", tam[:-12]),
                         ("bozuk", tam[:40] + bytes(b ^ 0xFF for b in tam[40:80]) + tam[80:])):
            with self.subTest(ad):
                arsiv = self.cikti / f"{ad}.tar.gz"
                arsiv.write_bytes(veri)
                h = hashlib.sha256(veri).hexdigest()
                arsiv.with_name(arsiv.name + ".sha256").write_text(f"{h}  {arsiv.name}\n")
                with self.assertRaises(tasima.TasimaHatasi) as b:
                    self.ac(arsiv)
                self.assertIn("arşiv okunamadı", str(b.exception))
                self.assertEqual(self.hedef_icerik(), [])

    def test_okuma_izni_yoksa_ayri_ileti(self):
        arsiv = self.arsivle()
        for hedef in ("read_text", "read_bytes"):
            with self.subTest(hedef), mock.patch.object(Path, hedef, side_effect=PermissionError(13, "izin")):
                with self.assertRaises(tasima.TasimaHatasi) as b:
                    self.ac(arsiv)
                self.assertIn("okuma izni yok", str(b.exception))
                self.assertNotIn("sağlama toplamı okunamadı", str(b.exception))
        with mock.patch.object(Path, "read_text", side_effect=PermissionError(13, "izin")):
            kod, cikti = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertIn("okuma izni yok", cikti)
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_izinli_dizin_uyesi_kabul(self):
        arsiv = self.elle_arsiv([("yanitlar/alt", "dizin", None), ("yanitlar/alt/a.md", "dosya", b"a\n")])
        s = self.ac(arsiv)
        self.assertEqual(s["yazilan"], 1)
        self.assertEqual((self.hedef / "yanitlar/alt/a.md").read_bytes(), b"a\n")

    def test_hedefte_sembolik_bag_reddedilir(self):
        disari = Path(self.t.name) / "disari"
        disari.mkdir()
        (self.hedef / "yanitlar").symlink_to(disari)
        with self.assertRaises(tasima.TasimaHatasi) as b:
            self.ac(self.arsivle())
        self.assertIn("hedefte beklenmeyen yol", str(b.exception))
        self.assertIn("yanitlar/", str(b.exception))
        self.assertNotIn("s1.md", str(b.exception))
        self.assertEqual(list(disari.iterdir()), [])
        self.assertFalse((self.hedef / "sirket-log").exists())

    def test_ikinci_kosu_zararsiz(self):
        arsiv = self.arsivle()
        self.ac(arsiv)
        once = {g: (self.hedef / g).stat().st_mtime_ns for g in tasima.dosyalar(self.hedef)}
        s = self.ac(arsiv)
        self.assertEqual((s["yazilan"], s["ayni"], s["catisan"]), (0, 12, []))
        self.assertEqual({g: (self.hedef / g).stat().st_mtime_ns for g in tasima.dosyalar(self.hedef)}, once)
        kod, _ = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 0)

    def test_catisma_varsa_hicbir_sey_yazmaz(self):
        arsiv = self.arsivle()
        yaz(self.hedef, "sirket-log/dagitici.log", "eski\n")
        s = self.ac(arsiv)
        self.assertEqual(s["catisan"], ["sirket-log/dagitici.log"])
        self.assertEqual(s["yazilan"], 0)
        kod, _ = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertFalse((self.hedef / "yanitlar").exists())
        self.assertEqual((self.hedef / "sirket-log/dagitici.log").read_text(), "eski\n")
        self.assertEqual(self.hedef_icerik(), ["sirket-log", "sirket-log/dagitici.log"])

    def test_ustune_yaz_yedekler(self):
        arsiv = self.arsivle()
        yaz(self.hedef, "sirket-log/dagitici.log", "eski\n")
        s = self.ac(arsiv, ustune_yaz=True, simdi=SIMDI)
        self.assertEqual((self.hedef / "sirket-log/dagitici.log").read_text(), "x\n")
        yedek = self.hedef / "sirket-log/tasima-yedek/20261124-084000"
        self.assertEqual((yedek / "sirket-log/dagitici.log").read_text(), "eski\n")
        self.assertEqual((yedek / "sirket-log/dagitici.log").stat().st_mode & 0o777, 0o600)
        self.assertEqual(s["yedek"], yedek)
        self.assertEqual(s["yazilan"], 12)
        self.assertEqual(s["catisan"], ["sirket-log/dagitici.log"])

    def test_hedefte_acik_soru_varsa_reddeder(self):
        arsiv = self.arsivle()
        yaz(self.hedef, "sirket-log/sorular/s9.md", "# Soru\n- durum: alindi\n")
        s = self.ac(arsiv)
        self.assertEqual(len(s["engeller"]), 1)
        self.assertIn("açık soru var: 1", s["engeller"][0])
        kod, cikti = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertIn("ENGEL", cikti)
        self.assertFalse((self.hedef / "yanitlar").exists())

    def test_hedef_kilit_doluysa_reddeder(self):
        arsiv = self.arsivle()
        with open(self.hedef / ayar.KOSU_KILIDI, "a") as k:
            fcntl.flock(k, fcntl.LOCK_EX)
            kod, cikti = self.ac_main(["--ac", str(arsiv)])
            self.assertEqual(kod, 1)
            self.assertIn("koşu kilidi dolu", cikti)
            self.assertFalse((self.hedef / "yanitlar").exists())

    def test_root_reddedilir(self):
        arsiv = self.arsivle()
        with self.assertRaises(tasima.TasimaHatasi) as b:
            self.ac(arsiv, euid=0)
        self.assertIn("root", str(b.exception))
        self.assertEqual(list(self.hedef.iterdir()), [])
        with mock.patch.object(tasima, "_euid", return_value=0):
            kod, cikti = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertIn("root", cikti)
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_kuru_yazmaz(self):
        arsiv = self.arsivle()
        kod, cikti = self.ac_main(["--ac", str(arsiv), "--kuru"], {"CLAUDECODE": "1"})
        self.assertEqual(kod, 0)
        self.assertIn("12", cikti)
        self.assertEqual(list(self.hedef.iterdir()), [])
        s = self.ac(arsiv, kuru=True)
        self.assertEqual((s["yazilan"], s["yazilacak"]), (0, 12))
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_ajan_ortaminda_yazan_ac_durur(self):
        arsiv = self.arsivle()
        kod, cikti = self.ac_main(["--ac", str(arsiv)], {"CLAUDECODE": "1"})
        self.assertEqual(kod, 1)
        self.assertIn("yalnız --kuru", cikti)
        self.assertEqual(list(self.hedef.iterdir()), [])

    def test_cikti_dosya_adi_tasimaz(self):
        arsiv = self.arsivle()
        yaz(self.hedef, "sirket-log/dagitici.log", "eski\n")
        kod, cikti = self.ac_main(["--ac", str(arsiv)])
        self.assertEqual(kod, 1)
        self.assertIn("sirket-log/", cikti)
        self.assertIn("1 dosya", cikti)
        self.assertIn("--ustune-yaz", cikti)
        for yasak in ("example.com", "GIZLI", "dagitici.log", "s1.md"):
            self.assertNotIn(yasak, cikti)

    def test_ac_kullanim_hatasi(self):
        for argv in (["--ac"], ["--ustune-yaz"], ["--ac", "x", "--cikti", "y"], ["--paketle", "--ustune-yaz"]):
            with mock.patch.object(sys, "stderr", io.StringIO()):
                self.assertEqual(self.ac_main(argv)[0], 2, argv)


if __name__ == "__main__":
    unittest.main()
