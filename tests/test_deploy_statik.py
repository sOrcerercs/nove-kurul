"""Docker paketinin statik sınamaları — dosyalar metin olarak okunur, YAML ayrıştırıcı yok.

python3 -m unittest tests.test_deploy_statik
"""
import re
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import zamanla  # noqa: E402

DOCKER = KOK / "deploy" / "docker"


def _oku(yol):
    return Path(yol).read_text(encoding="utf-8")


class ComposeTesti(unittest.TestCase):
    def setUp(self):
        self.metin = _oku(DOCKER / "compose.yaml")

    def test_port_yalniz_loopback(self):
        port_satirlari = [s for s in self.metin.splitlines() if s.strip().startswith("ports:")]
        self.assertTrue(port_satirlari)
        for satir in port_satirlari:
            degerler = re.findall(r'"([^"]+)"', satir)
            self.assertTrue(degerler)
            for deger in degerler:
                self.assertTrue(deger.startswith("127.0.0.1:"), deger)
        self.assertIn('"127.0.0.1:${NOVE_PORT:-8770}:8770"', self.metin)
        for satir in self.metin.splitlines():
            if "0.0.0.0" in satir:
                self.assertIn("--adres", satir)
                self.assertNotIn("ports:", satir)

    def test_env_file_yok_ve_sir_yok(self):
        self.assertNotIn("env_file", self.metin)
        for yasak in ("ANTHROPIC", "_API_KEY", "READONLY_URL", "POSTA_"):
            self.assertNotIn(yasak, self.metin)

    def test_iki_servis_ayni_baglama(self):
        self.assertIn("\n  panel:", self.metin)
        self.assertIn("\n  zamanlayici:", self.metin)
        self.assertEqual(self.metin.count("<<: *ortak"), 2)
        for parca in ("${NOVE_KOK:-/srv/nove-kurul}:/srv/nove-kurul", "working_dir: /srv/nove-kurul",
                      "restart: unless-stopped", "claude-ev:/home/nove-ajan/.claude"):
            self.assertIn(parca, self.metin)

    def test_komutlar(self):
        self.assertIn('"bin/panel.py", "--adres", "0.0.0.0", "--https-arkasinda"', self.metin)
        self.assertIn('"supercronic", "deploy/docker/crontab"', self.metin)


class CrontabTesti(unittest.TestCase):
    def setUp(self):
        self.satirlar = [s.strip() for s in _oku(DOCKER / "crontab").splitlines()
                         if s.strip() and not s.strip().startswith("#")]

    def test_dort_satir(self):
        self.assertEqual(self.satirlar, [
            "0 8 * * * python3 bin/gunluk.py --sabah",
            "30 9 * * 1-5 python3 bin/gunluk.py --rapor",
            "*/10 * * * * python3 bin/gunluk.py --ilerlet",
            "0 19 * * * python3 bin/gunluk.py --aksam",
        ])

    def test_saatler_ayarla_ayni(self):
        """ANAYASA §4: saatler ayar.py'den türer; crontab onunla ayrışmamalı."""
        self.assertEqual(8, ayar.MESAI_BASLANGIC)
        self.assertEqual(19, ayar.MESAI_BITIS - 1)
        rapor = {i["ad"]: i for i in zamanla.RAPOR_ISLERI}
        self.assertEqual((rapor["rapor"]["saat"], rapor["rapor"]["dakika"]), (9, 30))
        self.assertEqual(rapor["rapor"]["gunler"], [1, 2, 3, 4, 5])
        self.assertEqual(rapor["ilerlet"]["aralik_sn"], 600)


class DockerfileTesti(unittest.TestCase):
    def setUp(self):
        self.metin = _oku(DOCKER / "Dockerfile")
        self.satirlar = [s.strip() for s in self.metin.splitlines()]

    def test_saat_dilimi_ve_kullanici(self):
        self.assertIn("TZ=Europe/Istanbul", self.metin)
        kullanicilar = [s.split()[1] for s in self.satirlar if s.startswith("USER ")]
        self.assertTrue(kullanicilar)
        self.assertEqual(kullanicilar[-1], "nove-ajan")
        self.assertNotIn(kullanicilar[-1], ("root", "0"))

    def test_kodu_kopyalamaz(self):
        for s in self.satirlar:
            self.assertFalse(s.startswith("ADD "), s)
            if s.startswith("COPY "):
                self.assertTrue(s.startswith("COPY --from="), s)

    def test_surumler_sabit(self):
        for ad in ("PYTHON_SURUM", "NODE_SURUM", "CLAUDE_CODE_SURUM", "PSYCOPG_SURUM", "SUPERCRONIC_SURUM"):
            m = re.search(rf"^ARG {ad}=(\S+)$", self.metin, re.M)
            self.assertIsNotNone(m, ad)
            self.assertRegex(m.group(1), r"^\d+\.\d+\.\d+$", ad)
        self.assertTrue(re.search(r"^ARG PYTHON_SURUM=3\.12\.", self.metin, re.M))
        self.assertTrue(re.search(r"^ARG NODE_SURUM=22\.", self.metin, re.M))
        for mimari in ("AMD64", "ARM64"):
            m = re.search(rf"^ARG SUPERCRONIC_SHA1_{mimari}=(\S+)$", self.metin, re.M)
            self.assertIsNotNone(m, mimari)
            self.assertRegex(m.group(1), r"^[0-9a-f]{40}$")
        self.assertNotIn("latest", self.metin)
        self.assertIn("psycopg[binary]==", self.metin)
        self.assertIn("claude-code@$", self.metin)

    def test_uid_gid_ve_ev(self):
        for parca in ("ARG UID", "ARG GID", "getent group", "/home/nove-ajan/.claude",
                      "DISABLE_AUTOUPDATER=1", "tzdata"):
            self.assertIn(parca, self.metin)


class DockerignoreTesti(unittest.TestCase):
    def test_sir_ve_kisisel_veri(self):
        satirlar = {s.strip() for s in _oku(KOK / ".dockerignore").splitlines()}
        for beklenen in (".env", ".env.*", "yanitlar/", "sirket-log/", "deploy/*.json", "formlar/", "kasa/",
                         "takimlar/*/kosu/", "takimlar/*/cikti/", "takimlar/*/gelen/", "takimlar/*/veri/",
                         "takimlar/*/defter.md", "takimlar/*/durum.json"):
            self.assertIn(beklenen, satirlar)


class CaddyTesti(unittest.TestCase):
    def test_ornek(self):
        metin = _oku(KOK / "deploy" / "Caddyfile.example")
        for parca in ("reverse_proxy 127.0.0.1:8770", "remote_ip", "panel.example.com"):
            self.assertIn(parca, metin)
        self.assertNotIn("nove.group", metin)


if __name__ == "__main__":
    unittest.main()
