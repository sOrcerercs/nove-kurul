import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import sunucu_kontrol  # noqa: E402

TAM_ENV = (
    "ANTHROPIC_API_KEY=sk-ant-GIZLI-4711\n"
    "QA_READONLY_URL=postgresql://okuyucu:PAROLA-9911@db.ornek:5432/qa\n"
    "OKR_READONLY_URL=postgresql://okuyucu:PAROLA-9922@localhost:5432/pys\n"
    "NVIDIA_API_KEY=nvapi-GIZLI-1\n"
)
ISTANBUL_FARK = timedelta(hours=3)


def tamam_calistir():
    return mock.Mock(return_value=mock.Mock(returncode=0, stdout="9.9.9 (Claude Code)\n"))


def kur(kok, env=TAM_ENV, izin=0o600):
    kok = Path(kok)
    for takim, anahtar in (("kalite", "QA_READONLY_URL"), ("okr", "OKR_READONLY_URL")):
        d = kok / "takimlar" / takim
        d.mkdir(parents=True)
        (d / "takim.md").write_text("---\nad: %s\ngerekli_anahtarlar: [%s]\n---\ngövde\n" % (takim, anahtar),
                                    encoding="utf-8")
    (kok / "deploy").mkdir()
    (kok / "deploy" / "roller.json").write_text(json.dumps({"uye@example.com": "kurul"}), encoding="utf-8")
    (kok / "deploy" / "kullanicilar.json").write_text("{}", encoding="utf-8")
    (kok / "yanitlar").mkdir()
    (kok / "sirket-log").mkdir()
    if env is not None:
        (kok / ".env").write_text(env, encoding="utf-8")
        os.chmod(kok / ".env", izin)
    return kok


def durumlar(sonuclar):
    return {x["ad"]: x["durum"] for x in sonuclar}


def iletiler(sonuclar):
    return {x["ad"]: x["ileti"] for x in sonuclar}


def baglan_mock():
    baglanti = mock.MagicMock()
    return mock.Mock(return_value=baglanti), baglanti


class SunucuKontrolTest(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self.gecici.cleanup)
        self.kok = kur(self.gecici.name)

    def kos(self, **kw):
        kw.setdefault("calistir", tamam_calistir())
        kw.setdefault("yerel_fark", ISTANBUL_FARK)
        kw.setdefault("euid", os.geteuid() or 1000)
        return sunucu_kontrol.kontroller(self.kok, **kw)

    def ana(self, argv, **kw):
        kw.setdefault("calistir", tamam_calistir())
        kw.setdefault("yerel_fark", ISTANBUL_FARK)
        kw.setdefault("euid", os.geteuid() or 1000)
        cikti, hata = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(hata):
            kod = sunucu_kontrol.main(argv, self.kok, **kw)
        return kod, cikti.getvalue() + hata.getvalue()

    def test_temiz_kurulum_cikis_0(self):
        d = durumlar(self.kos())
        for ad, durum in d.items():
            if ad == "posta-anahtarlari":
                self.assertEqual(durum, "bilgi")
            else:
                self.assertEqual(durum, "tamam", ad)
        kod, _ = self.ana([])
        if os.geteuid() == 0:
            self.skipTest("root")
        self.assertEqual(kod, 0)

    def test_env_yok_ve_izin(self):
        (self.kok / ".env").unlink()
        self.assertEqual(durumlar(self.kos())["env-dosyasi"], "hata")
        self.assertEqual(self.ana([])[0], 1)
        (self.kok / ".env").write_text(TAM_ENV, encoding="utf-8")
        os.chmod(self.kok / ".env", 0o644)
        s = self.kos()
        self.assertEqual(durumlar(s)["env-dosyasi"], "hata")
        self.assertIn("644", iletiler(s)["env-dosyasi"])

    def test_zorunlu_anahtar_eksik(self):
        (self.kok / ".env").write_text(TAM_ENV.replace("OKR_READONLY_URL", "BASKA_AD"), encoding="utf-8")
        with mock.patch.dict(os.environ, {"OKR_READONLY_URL": "x"}):
            s = self.kos()
        self.assertEqual(durumlar(s)["zorunlu-anahtarlar"], "hata")
        self.assertIn("OKR_READONLY_URL", iletiler(s)["zorunlu-anahtarlar"])

    def test_kurulumdaki_danismanin_anahtari_istenmez(self):
        d = self.kok / "takimlar" / "finans"
        d.mkdir()
        (d / "takim.md").write_text("gövde, frontmatter yok\n", encoding="utf-8")
        (self.kok / ".env").write_text("ANTHROPIC_API_KEY=x\n", encoding="utf-8")
        os.chmod(self.kok / ".env", 0o600)
        ileti = iletiler(self.kos())["zorunlu-anahtarlar"]
        self.assertIn("QA_READONLY_URL", ileti)
        self.assertIn("OKR_READONLY_URL", ileti)
        self.assertNotIn("FINANS", ileti.upper())

    def test_denetci_anahtari_yoksa_uyari_cikis_0(self):
        (self.kok / ".env").write_text(TAM_ENV.replace("NVIDIA_API_KEY", "BASKA"), encoding="utf-8")
        os.chmod(self.kok / ".env", 0o600)
        self.assertEqual(durumlar(self.kos())["denetci"], "uyari")
        if os.geteuid() != 0:
            self.assertEqual(self.ana([])[0], 0)

    def test_claude_yok(self):
        c = mock.Mock(side_effect=FileNotFoundError("claude"))
        self.assertEqual(durumlar(self.kos(calistir=c))["claude"], "hata")
        self.assertEqual(c.call_count, 1)
        self.assertEqual(c.call_args[0][0], ["claude", "--version"])
        c2 = mock.Mock(return_value=mock.Mock(returncode=1, stdout=""))
        self.assertEqual(durumlar(self.kos(calistir=c2))["claude"], "hata")
        self.assertEqual(c2.call_count, 1)

    def test_saat_dilimi(self):
        self.assertEqual(durumlar(self.kos(yerel_fark=timedelta(0)))["saat-dilimi"], "hata")
        self.assertEqual(durumlar(self.kos(yerel_fark=timedelta(hours=3)))["saat-dilimi"], "tamam")

    def test_sahiplik(self):
        s = self.kos(euid=0)
        self.assertEqual(durumlar(s)["sahiplik"], "hata")
        self.assertIn("root", iletiler(s)["sahiplik"])
        s = self.kos(euid=os.geteuid() + 1)
        self.assertEqual(durumlar(s)["sahiplik"], "hata")
        self.assertTrue(any(c.isdigit() for c in iletiler(s)["sahiplik"]))

    def test_depo_yazilamaz(self):
        if os.geteuid() == 0:
            self.skipTest("root her yere yazar")
        yol = self.kok / "sirket-log"
        os.chmod(yol, 0o500)
        self.addCleanup(os.chmod, yol, 0o700)
        s = self.kos()
        self.assertEqual(durumlar(s)["depo-yazilabilir"], "hata")
        self.assertIn("sirket-log", iletiler(s)["depo-yazilabilir"])

    def test_roller_kullanicilar(self):
        (self.kok / "deploy" / "kullanicilar.json").unlink()
        s = self.kos()
        self.assertEqual(durumlar(s)["kullanicilar"], "hata")
        self.assertEqual(self.ana([])[0], 1)
        s = self.kos(tasima_oncesi=True)
        self.assertEqual(durumlar(s)["kullanicilar"], "uyari")
        self.assertIn("taşımadan sonra gelir", iletiler(s)["kullanicilar"])
        (self.kok / "deploy" / "kullanicilar.json").write_text("{bozuk", encoding="utf-8")
        self.assertEqual(durumlar(self.kos(tasima_oncesi=True))["kullanicilar"], "hata")
        (self.kok / "deploy" / "kullanicilar.json").write_text("[]", encoding="utf-8")
        self.assertEqual(durumlar(self.kos())["kullanicilar"], "hata")

    def test_db_bayragi_yokken_baglanmaz(self):
        baglan, _ = baglan_mock()
        s = self.kos(baglan=baglan)
        baglan.assert_not_called()
        self.assertFalse([x for x in s if x["ad"].startswith("db-")])

    def test_db_basarili(self):
        baglan, baglanti = baglan_mock()
        d = durumlar(self.kos(db=True, baglan=baglan))
        self.assertEqual(d["db-kalite"], "tamam")
        self.assertEqual(d["db-okr"], "tamam")
        self.assertEqual(baglanti.close.call_count, 2)
        imlec = baglanti.cursor.return_value.__enter__.return_value
        imlec.execute.assert_called_with("SELECT 1")

    def test_db_anahtar_yoksa_atlanir(self):
        (self.kok / ".env").write_text(TAM_ENV.replace("QA_READONLY_URL", "BASKA"), encoding="utf-8")
        os.chmod(self.kok / ".env", 0o600)
        baglan, _ = baglan_mock()
        s = self.kos(db=True, baglan=baglan)
        self.assertEqual(durumlar(s)["db-kalite"], "bilgi")
        self.assertIn("atlandı", iletiler(s)["db-kalite"])

    def test_db_hatasi_url_sizdirmaz(self):
        baglan = mock.Mock(side_effect=RuntimeError(
            "connection to postgresql://okuyucu:PAROLA-9911@db.ornek:5432/qa failed"))
        s = self.kos(db=True, baglan=baglan)
        self.assertEqual(durumlar(s)["db-kalite"], "hata")
        self.assertIn("RuntimeError", iletiler(s)["db-kalite"])
        self.assertNotIn("PAROLA", iletiler(s)["db-kalite"])
        self.assertIn("adres localhost", iletiler(s)["db-okr"])

    def test_cikti_deger_tasimaz(self):
        baglan = mock.Mock(side_effect=RuntimeError(
            "connection to postgresql://okuyucu:PAROLA-9911@db.ornek:5432/qa failed"))
        for calistir in (mock.Mock(side_effect=OSError("sk-ant-GIZLI-4711")), tamam_calistir()):
            _, cikti = self.ana(["--db"], baglan=baglan, calistir=calistir)
            for yasak in ("GIZLI", "PAROLA", "db.ornek", "okuyucu", "postgresql://", "example.com",
                          "Traceback", "ANTHROPIC_API_KEY"):
                self.assertNotIn(yasak, cikti)
            self.assertIn("sunucu kontrolü", cikti)

    def test_hicbir_sey_yazmaz(self):
        def goruntu():
            return {str(p.relative_to(self.kok)): p.stat().st_mtime_ns for p in self.kok.rglob("*")}
        once = goruntu()
        baglan, _ = baglan_mock()
        self.ana(["--db"], baglan=baglan)
        self.assertEqual(goruntu(), once)

    def test_kullanim_hatasi(self):
        self.assertEqual(self.ana(["--x"])[0], 2)

    def test_bas_ozet(self):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            sunucu_kontrol.bas(self.kok, [{"ad": "a", "durum": "hata", "ileti": "x"},
                                           {"ad": "b", "durum": "uyari", "ileti": "y"}])
        self.assertIn("[HATA ] a — x", cikti.getvalue())
        self.assertIn("sonuç: 1 hata, 1 uyarı", cikti.getvalue())


if __name__ == "__main__":
    unittest.main()
