"""Panel sunucusu: İlerletici, HTTP adaptörü, komut satırı. Gerçek dagitici.dagit asla çağrılmaz."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import panel  # noqa: E402
import panel_kimlik  # noqa: E402
import soru_kapisi  # noqa: E402

SIFRE = "gizli-sifre-123"
UYE = "uye@example.com"


def _ilerletici(kok, adim, acik=lambda k: ["x"], kilit=lambda k: False, aralik=60):
    return panel.Ilerletici(kok, adim=adim, aralik_sn=aralik, kilit_dolu=kilit, acik=acik)


class IlerleticiTesti(unittest.TestCase):
    def test_tur_bos_adim_cagirmaz(self):
        adim = mock.Mock()
        self.assertEqual(_ilerletici("k", adim, acik=lambda k: []).tur(), "bos")
        adim.assert_not_called()

    def test_tur_kilit_doluyken_atlar(self):
        adim = mock.Mock()
        self.assertEqual(_ilerletici("k", adim, kilit=lambda k: True).tur(), "kilit")
        adim.assert_not_called()

    def test_tur_adim_kokle_cagrilir(self):
        adim = mock.Mock()
        self.assertEqual(_ilerletici("k", adim).tur(), "adim")
        adim.assert_called_once_with("k")

    def test_tur_hata_yutulur(self):
        adim = mock.Mock(side_effect=RuntimeError("x"))
        with mock.patch("sys.stderr"):
            self.assertEqual(_ilerletici("k", adim).tur(), "hata")

    def test_baslat_acik_soru_varsa_hemen_adim_atar(self):
        olay = threading.Event()
        il = _ilerletici("k", lambda k: olay.set())
        il.baslat()
        self.addCleanup(il.durdur)
        self.assertTrue(olay.wait(2))

    def test_tetikle_bekleyeni_uyandirir(self):
        durum = {"acik": []}
        olay = threading.Event()
        il = _ilerletici("k", lambda k: olay.set(), acik=lambda k: durum["acik"], aralik=3600)
        il.baslat()
        self.addCleanup(il.durdur)
        time.sleep(0.2)
        self.assertFalse(olay.is_set())
        durum["acik"] = ["x"]
        il.tetikle()
        self.assertTrue(olay.wait(2))

    def test_ayni_anda_tek_adim(self):
        sayac = {"simdi": 0, "en": 0}
        kilit = threading.Lock()

        def adim(k):
            with kilit:
                sayac["simdi"] += 1
                sayac["en"] = max(sayac["en"], sayac["simdi"])
            time.sleep(0.2)
            with kilit:
                sayac["simdi"] -= 1

        il = _ilerletici("k", adim, aralik=3600)
        il.baslat()
        self.addCleanup(il.durdur)
        for _ in range(5):
            il.tetikle()
        time.sleep(0.7)
        self.assertEqual(sayac["en"], 1)

    def test_ilerletme_yok_tetiklemez(self):
        with tempfile.TemporaryDirectory() as g:
            kok = Path(g)
            (kok / "deploy").mkdir()
            (kok / "deploy" / "roller.json").write_text(json.dumps({UYE: "kurul"}), encoding="utf-8")
            panel_kimlik.kullanici_ekle(kok, UYE, "Üye", SIFRE)
            yeni = mock.Mock(return_value={"sonuc": "acildi", "soru_id": "s1", "sebep": ""})
            u = panel.Uygulama(kok, ilerletici=None, yeni=yeni)
            kod, _, ek = u.istek("POST", "/api/giris", json.dumps({"eposta": UYE, "sifre": SIFRE}).encode())
            cerez = ek[0][1].split(";")[0].split("=", 1)[1]
            kod, _, _ = u.istek("POST", "/api/soru", json.dumps({"soru": "kalite nasıl"}).encode(), cerez=cerez)
            self.assertEqual(kod, 200)


class KomutSatiriTesti(unittest.TestCase):
    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.addCleanup(self._g.cleanup)
        self.kok = Path(self._g.name)
        (self.kok / "deploy").mkdir()
        (self.kok / "deploy" / "roller.json").write_text(json.dumps({UYE: "kurul"}), encoding="utf-8")
        p = mock.patch.object(panel, "KOK", self.kok)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(panel_kimlik, "PBKDF2_TUR", 1000)
        p.start()
        self.addCleanup(p.stop)
        self.dosya = self.kok / "deploy" / "kullanicilar.json"

    def test_kullanici_ekle_claudecode_altinda_yazmaz(self):
        with mock.patch.dict(os.environ, {"CLAUDECODE": "1"}), mock.patch("sys.stderr"):
            self.assertEqual(panel.main(["--kullanici-ekle", UYE, "--ad", "Üye"]), 2)
        self.assertFalse(self.dosya.exists())

    def test_kullanici_ekle_yazar(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CLAUDECODE", None)
            with mock.patch("getpass.getpass", return_value=SIFRE), mock.patch("sys.stdout"):
                self.assertEqual(panel.main(["--kullanici-ekle", UYE, "--ad", "Üye"]), 0)
        self.assertIsNotNone(panel_kimlik.dogrula(self.kok, UYE, SIFRE))

    def test_kullanici_ekle_sifreler_uyusmazsa_1(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CLAUDECODE", None)
            with mock.patch("getpass.getpass", side_effect=[SIFRE, "baska-sifre-1"]), \
                    mock.patch("sys.stderr"), mock.patch("sys.stdout"):
                self.assertEqual(panel.main(["--kullanici-ekle", UYE, "--ad", "Üye"]), 1)
        self.assertFalse(self.dosya.exists())


class AdaptorTesti(unittest.TestCase):
    def test_adaptor_duman(self):
        with tempfile.TemporaryDirectory() as g:
            uyg = panel.Uygulama(Path(g))
            try:
                sunucu = ThreadingHTTPServer(("127.0.0.1", 0), panel.yakala(uyg))
            except OSError:
                self.skipTest("yerel soket açılamadı")
            self.addCleanup(sunucu.server_close)
            threading.Thread(target=sunucu.serve_forever, daemon=True).start()
            self.addCleanup(sunucu.shutdown)
            taban = f"http://127.0.0.1:{sunucu.server_address[1]}"
            with urllib.request.urlopen(taban + "/", timeout=5) as r:
                self.assertEqual(r.status, 200)
                self.assertIn("Nove AI", r.read().decode("utf-8"))
            with self.assertRaises(urllib.error.HTTPError) as c:
                urllib.request.urlopen(taban + "/api/ben", timeout=5)
            self.assertEqual(c.exception.code, 401)
            self.assertEqual(c.exception.headers["Cache-Control"], "no-store")
            self.assertEqual(json.loads(c.exception.read()), {"hata": "oturum yok"})
            with self.assertRaises(urllib.error.HTTPError) as c:
                urllib.request.urlopen(taban + "/deploy/kullanicilar.json", timeout=5)
            self.assertEqual(c.exception.code, 404)
            istek = urllib.request.Request(taban + "/api/ben", method="PUT")
            with self.assertRaises(urllib.error.HTTPError) as c:
                urllib.request.urlopen(istek, timeout=5)
            self.assertEqual(c.exception.code, 405)


if __name__ == "__main__":
    unittest.main()
