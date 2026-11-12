"""panel/sahne-sira.js — sahnenin hangi aşamaları oynayacağı (node ile)."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

JS = Path(__file__).resolve().parent.parent / "panel" / "sahne-sira.js"
KOD = ("const s=require(process.argv[1]);"
       "console.log(JSON.stringify(s.sira(...JSON.parse(process.argv[2]))))")


def sira(*args):
    r = subprocess.run(["node", "-e", KOD, str(JS), json.dumps(list(args))],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node yok")
class SahneSiraTest(unittest.TestCase):
    def test_ilk_goruste_yalniz_son_asama(self):
        r = sira(None, ["qa_al", "dagit", "analiz", "denetim"], "kalite")
        self.assertEqual(r["oyna"], ["denetim"])
        self.assertEqual(r["gorulen"], 4)
        self.assertEqual(r["dept"], "kalite")

    def test_taze_soru_qa_al(self):
        r = sira(None, ["qa_al"], None)
        self.assertEqual(r["oyna"], ["qa_al"])
        self.assertEqual(r["gorulen"], 1)

    def test_ayni_yoklamada_gelenler_sirayla(self):
        r = sira(1, ["qa_al", "dagit", "analiz"], "kalite")
        self.assertEqual(r["oyna"], ["dagit", "analiz"])
        self.assertEqual(r["gorulen"], 3)

    def test_degisiklik_yoksa_bos(self):
        self.assertEqual(sira(3, ["qa_al", "dagit", "analiz"], "kalite")["oyna"], [])

    def test_liste_kisalirsa_bos(self):
        r = sira(3, ["qa_al"], "kalite")
        self.assertEqual(r["oyna"], [])
        self.assertEqual(r["gorulen"], 3)

    def test_bilinmeyen_tip_atilir(self):
        r = sira(0, ["qa_al", "<script>", "dagit"], "kalite")
        self.assertEqual(r["oyna"], ["qa_al", "dagit"])

    def test_sahnede_olmayan_danisman_yalniz_qa_al(self):
        for d in ("sdr", None):
            r = sira(0, ["qa_al", "dagit", "analiz"], d)
            self.assertEqual(r["oyna"], ["qa_al"])
            self.assertIsNone(r["dept"])

    def test_anahtar_eslemesi(self):
        self.assertEqual(sira(0, [], "raporlama")["dept"], "rapor")
        self.assertEqual(sira(0, [], "satis-muduru")["dept"], "satisMuduru")

    def test_dizi_degilse_bos(self):
        r = sira(None, None, "kalite")
        self.assertEqual(r["oyna"], [])
        self.assertEqual(r["gorulen"], 0)


if __name__ == "__main__":
    unittest.main()
