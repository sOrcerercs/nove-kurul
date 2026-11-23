"""panel/soru-baglantisi.js — ?soru=<id> bağlantısı (node ile)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
JS = KOK / "panel" / "soru-baglantisi.js"
KOD = ("const k=require(process.argv[1]);const [f,a]=JSON.parse(process.argv[2]);"
       "console.log(JSON.stringify(k[f](a)))")


def cagir(fonk, arg):
    r = subprocess.run(["node", "-e", KOD, str(JS), json.dumps([fonk, arg])],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node yok")
class SoruBaglantisiTest(unittest.TestCase):
    def test_gecerli_id(self):
        self.assertEqual(cagir("oku", "?soru=rapor-kalite-20261123"), "rapor-kalite-20261123")
        self.assertEqual(cagir("oku", "?a=1&soru=x1"), "x1")

    def test_bozuk_deger_null(self):
        for s in ("?soru=", "?soru=../../etc", "?soru=Rapor-Kalite", "?soru=a%20b",
                  "?soru=" + "a" * 65, "", "?demo"):
            with self.subTest(s=s):
                self.assertIsNone(cagir("oku", s))

    def test_ilk_parametre(self):
        self.assertEqual(cagir("oku", "?soru=a&soru=b"), "a")

    def test_temiz(self):
        self.assertEqual(cagir("temiz", "?soru=x"), "")
        self.assertEqual(cagir("temiz", "?soru=x&a=1"), "?a=1")
        self.assertEqual(cagir("temiz", "?a=1"), "?a=1")


if __name__ == "__main__":
    unittest.main()
