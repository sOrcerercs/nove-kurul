"""Temiz klon testinde çıkan kırılmaların testleri — ağ yok, claude çağrısı yok, para harcamaz.

Kapsam: `.env` önceliği (K1), launchd etiketinin köke bağlanması (K2), `bin/ayar.py`'nin
`.env` okuması (K3), bekçinin geçersiz
OpenAI anahtarında Haiku yedeğine düşmesi (K5), `bin/takim-olustur.sh` uyarıları (K6) ve
belgelerin koda uyması (K7 + küçük düzeltmeler).

python3 -m unittest discover -s tests
"""
import io
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import zamanla  # noqa: E402


def _http_hatasi(kod):
    return urllib.error.HTTPError("https://ornek", kod, "hata", {}, None)


def _belge(test, yol):
    """Belge dosyasını okur; bu kökte yoksa testi atlar.

    Kitin canlı kopyası (`~/nove-kurul`) `docs/`, `README.md`, `KURULUM.md` ve `prompts/`
    taşımaz — oradaki koşuda belge testleri kırmızı değil, atlanmış görünür."""
    tam = KOK / yol
    if not tam.is_file():
        test.skipTest(f"{yol} bu kökte yok")
    return tam.read_text(encoding="utf-8")


# --- K1 + K3 · .env kabuğu ezer --------------------------------------------

class EnvOnceligiTesti(unittest.TestCase):
    def test_ortam_yukle_kabuktaki_degeri_ezer(self):
        """Proje `.env`'i kazanır: izleyici .env'e ne yazdıysa onu görür."""
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("APIFY_TOKEN=dosyadan\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"APIFY_TOKEN": "kabuktan"}, clear=False):
                ayar.ortam_yukle(env)
                self.assertEqual(os.environ["APIFY_TOKEN"], "dosyadan")

    def test_env_de_olmayan_degisken_ortamda_kalir(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("APIFY_TOKEN=dosyadan\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"BASKA_DEGISKEN": "dokunma"}, clear=False):
                ayar.ortam_yukle(env)
                self.assertEqual(os.environ["BASKA_DEGISKEN"], "dokunma")

    def test_sorun_giderme_belgesi_yeni_davranisi_anlatir(self):
        metin = _belge(self, "docs/06-sorun-giderme.md")
        self.assertNotIn("os.environ.setdefault", metin)
        self.assertIn(".env", metin)
        self.assertIn("ezer", metin)

    def test_kurulum_adim1_env_onceligini_soyler(self):
        metin = _belge(self, "KURULUM.md")
        self.assertIn("`.env` her zaman kabuğu ezer", metin)


# --- K2 · launchd etiketi köke bağlı ----------------------------------------

class LaunchdEtiketiTesti(unittest.TestCase):
    def test_etiket_kok_klasor_adini_ve_hash_tasir(self):
        etiket = zamanla.etiket("sabah", "/Users/biri/nove-kurul")
        self.assertRegex(etiket, r"^com\.nove-kurul\.nove-kurul-[0-9a-f]{6}\.sabah$")

    def test_iki_kok_farkli_etiket_uretir(self):
        self.assertNotEqual(zamanla.etiket("sabah", "/bir/nove-kurul"),
                            zamanla.etiket("sabah", "/baska/nove-kurul"))

    def test_plist_etiketi_ve_yolu_ayni_koke_bakar(self):
        icerik = zamanla.plist_icerigi(zamanla.TETIKLER[0], kok="/tmp/kok", python="/usr/bin/python3")
        self.assertEqual(icerik["Label"], zamanla.etiket("sabah", "/tmp/kok"))
        self.assertIn(zamanla.etiket("sabah", "/tmp/kok"), zamanla.plist_yolu("sabah", "/tmp/kok").name)

    def test_durum_baska_koke_ait_plisti_yuklu_saymaz(self):
        with tempfile.TemporaryDirectory() as d:
            ajanlar, kok, yabanci = Path(d) / "agents", Path(d) / "kok", Path(d) / "baska"
            ajanlar.mkdir()
            yabanci_gunluk = yabanci / "bin" / "gunluk.py"
            with mock.patch.object(zamanla, "AJANLAR", ajanlar), \
                 mock.patch.object(zamanla, "_launchctl", return_value=(0, "")):
                with open(zamanla.plist_yolu("sabah", kok), "wb") as dosya:
                    plistlib.dump({"Label": zamanla.etiket("sabah", kok),
                                   "ProgramArguments": ["python3", str(yabanci_gunluk), "--sabah"]},
                                  dosya)
                sabah = {s["ad"]: s for s in zamanla.durum(kok)}["sabah"]
        self.assertEqual(sabah["baska_kok"], str(yabanci_gunluk))

    def test_durum_kendi_kokune_ait_plisti_yuklu_sayar(self):
        with tempfile.TemporaryDirectory() as d:
            ajanlar, kok = Path(d) / "agents", Path(d) / "kok"
            ajanlar.mkdir()
            with mock.patch.object(zamanla, "AJANLAR", ajanlar), \
                 mock.patch.object(zamanla, "_launchctl", return_value=(0, "")):
                zamanla.kur(kok)
                sabah = {s["ad"]: s for s in zamanla.durum(kok)}["sabah"]
        self.assertIsNone(sabah["baska_kok"])
        self.assertTrue(sabah["yuklu"])

    def test_durum_eski_etiketi_raporlar(self):
        def sahte_launchctl(*argv):
            return (0, "") if argv[-1].endswith("com.nove-kurul.sabah") else (1, "bulunamadı")

        with tempfile.TemporaryDirectory() as d:
            ajanlar, kok = Path(d) / "agents", Path(d) / "kok"
            ajanlar.mkdir()
            with mock.patch.object(zamanla, "AJANLAR", ajanlar), \
                 mock.patch.object(zamanla, "_launchctl", sahte_launchctl):
                sonuc = {s["ad"]: s for s in zamanla.durum(kok)}
                yakalanan = io.StringIO()
                with redirect_stdout(yakalanan):
                    zamanla.main(["--durum"])
        self.assertTrue(sonuc["sabah"]["eski_yuklu"])
        self.assertFalse(sonuc["aksam"]["eski_yuklu"])
        self.assertEqual(sonuc["sabah"]["eski_etiket"], "com.nove-kurul.sabah")
        cikti = yakalanan.getvalue()
        self.assertIn("eski etiket", cikti)
        self.assertIn("--kur", cikti)

    def test_kur_ve_kaldir_yeni_etiketi_kullanir(self):
        cagrilar = []

        def sahte_launchctl(*argv):
            cagrilar.append(argv)
            return 0, ""

        with tempfile.TemporaryDirectory() as d:
            ajanlar, kok = Path(d) / "agents", Path(d) / "kok"
            ajanlar.mkdir()
            with mock.patch.object(zamanla, "AJANLAR", ajanlar), \
                 mock.patch.object(zamanla, "_launchctl", sahte_launchctl):
                zamanla.kur(kok)
                yazilan = sorted(y.name for y in ajanlar.glob("*.plist"))
                zamanla.kaldir(kok)
                kalan = list(ajanlar.glob("*.plist"))
        self.assertEqual(yazilan, sorted(f"{zamanla.etiket(i['ad'], kok)}.plist" for i in zamanla.TUM_ISLER))
        self.assertEqual(kalan, [])
        hedefler = " ".join(a[-1] for a in cagrilar)
        self.assertNotIn("com.nove-kurul.sabah ", hedefler + " ")
        self.assertIn(zamanla.etiket("sabah", kok), hedefler)

    def test_dongu_belgesi_etiket_desenini_anlatir(self):
        metin = _belge(self, "docs/02-dongu.md")
        self.assertIn("<klasor>-<hash6>", metin)


class BekciYedegiTesti(unittest.TestCase):
    def test_openai_401_atlandi_gerekcesi_verir(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", side_effect=_http_hatasi(401)):
            karar = bekci.openai_sor("sk-gecersiz", "istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertIn("openai 401", karar["gerekce"])

    def test_gecersiz_anahtar_haiku_yedegine_duser(self):
        yedek = {"karar": "kabul", "gerekce": "[bekçi aynı aileden — uyarı] temiz",
                 "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "atlandi", "gerekce": "openai 401",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor", return_value=yedek) as sahte_haiku:
            karar = bekci.llm_karari({"OPENAI_API_KEY": "sk-gecersiz"}, "istem")
        sahte_haiku.assert_called_once()
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn("openai 401 → haiku yedeği", karar["gerekce"])

    def test_ag_hatasi_da_yedege_duser(self):
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "atlandi", "gerekce": "openai ulaşılamadı: URLError",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor",
                               return_value={"karar": "red", "gerekce": "boş", "ihlal_edilen_kural": "x"}):
            karar = bekci.llm_karari({"OPENAI_API_KEY": "sk-gecersiz"}, "istem")
        self.assertEqual(karar["karar"], "red")
        self.assertIn("haiku yedeği", karar["gerekce"])

    def test_calisan_anahtar_yedege_dusmez(self):
        with mock.patch.object(bekci, "openai_sor",
                               return_value={"karar": "kabul", "gerekce": "temiz",
                                             "ihlal_edilen_kural": None}), \
             mock.patch.object(bekci, "haiku_sor") as sahte_haiku:
            karar = bekci.llm_karari({"OPENAI_API_KEY": "sk-gecerli"}, "istem")
        sahte_haiku.assert_not_called()
        self.assertEqual(karar["gerekce"], "temiz")

    def test_denetle_gecersiz_anahtarla_atlandi_birakmaz(self):
        with tempfile.TemporaryDirectory() as d:
            kok = Path(d)
            (kok / "takimlar" / "deneme" / "kosu").mkdir(parents=True)
            kosu = kok / "takimlar" / "deneme" / "kosu" / "2026-09-15.md"
            kosu.write_text("# Koşu\n\nİki dosya okundu, bir çıktı yazıldı.\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-gecersiz"}), \
                 mock.patch.object(bekci.urllib.request, "urlopen", side_effect=_http_hatasi(401)), \
                 mock.patch.object(bekci, "haiku_sor",
                                   return_value={"karar": "kabul", "gerekce": "temiz",
                                                 "ihlal_edilen_kural": None}):
                karar = bekci.denetle(kok, "deneme", kosu)
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn("openai 401 → haiku yedeği", karar["gerekce"])

    def test_belgeler_gecersiz_anahtari_da_anlatir(self):
        for ad in ("README.md", "KURULUM.md"):
            with self.subTest(dosya=ad):
                self.assertIn("yoksa ya da geçersizse", _belge(self, ad))


# --- K6 · takim-olustur.sh ---------------------------------------------------

def _betik_kokunu_kur(hedef):
    (hedef / "bin").mkdir(parents=True)
    shutil.copy2(KOK / "bin" / "takim-olustur.sh", hedef / "bin" / "takim-olustur.sh")
    shutil.copytree(KOK / "takimlar" / "_iskelet", hedef / "takimlar" / "_iskelet")
    return hedef / "bin" / "takim-olustur.sh"


class TakimOlusturTesti(unittest.TestCase):
    def test_argumansiz_cagri_temiz_turkce_mesaj_ve_rc2(self):
        with tempfile.TemporaryDirectory() as d:
            betik = _betik_kokunu_kur(Path(d))
            sonuc = subprocess.run(["bash", str(betik)], capture_output=True, text=True)
        self.assertEqual(sonuc.returncode, 2)
        self.assertIn("takım adı gerekli", sonuc.stderr)
        self.assertNotIn("parameter", sonuc.stderr.lower())

    def test_kurulan_takim_skills_uyarisi_basar(self):
        with tempfile.TemporaryDirectory() as d:
            betik = _betik_kokunu_kur(Path(d))
            sonuc = subprocess.run(["bash", str(betik), "deneme"], capture_output=True, text=True)
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        self.assertIn("skills:", sonuc.stdout)
        self.assertIn("testler kırmızı", sonuc.stdout)

    def test_kurulum_adim4_ayni_notu_tasir(self):
        metin = _belge(self, "KURULUM.md")
        self.assertIn("testler kırmızı", metin)


# --- K7 + küçükler · belgeler koda uyuyor ------------------------------------

class BelgeDuzeltmeTesti(unittest.TestCase):
    def test_windows_icin_wsl_gerektigi_yaziyor(self):
        metin = _belge(self, "docs/07-farkli-model.md")
        self.assertIn("fcntl", metin)
        self.assertIn("WSL", metin)
        self.assertNotIn("`bin/model_proxy.py` ve `bin/kos.py` çalışır", metin)

    def test_readme_zamanlayici_platform_notu_tasir(self):
        metin = _belge(self, "README.md")
        self.assertIn("WSL", metin)
        self.assertIn("cron", metin)

    def test_kos_py_gercekten_fcntl_kullaniyor(self):
        """Belgedeki iddianın kaynağı: kilit POSIX'e bağlı."""
        self.assertIn("import fcntl", (KOK / "bin" / "kos.py").read_text(encoding="utf-8"))

    def test_kurulum_anahtar_tablosu_env_ornegiyle_ayni(self):
        metin = _belge(self, "KURULUM.md")
        ornek = ayar.env_yukle(KOK / ".env.example")
        for anahtar in ornek:
            self.assertIn(anahtar, metin, f"{anahtar} .env.example'da var ama KURULUM'da yok")
        self.assertIn(f"{len(ornek)} anahtar", metin.replace("Sekiz", "8"))

    def test_readme_kurulum_adimlarinda_python3_bin_oneki(self):
        satirlar = _belge(self, "README.md").splitlines()
        adimlar = [s for s in satirlar if s.startswith(("5. ", "6. "))]
        self.assertEqual(len(adimlar), 2)
        for satir in adimlar:
            for komut in ("kos.py", "dagitici.py", "zamanla.py"):
                for parca in satir.split("`"):
                    if komut in parca:
                        self.assertTrue(parca.startswith("python3 bin/"),
                                        f"öneksiz komut: {parca}")

    def test_kurulum_push_oncesi_durum_json_notu(self):
        metin = _belge(self, "KURULUM.md")
        self.assertIn("git restore takimlar/*/durum.json", metin)


if __name__ == "__main__":
    unittest.main()
