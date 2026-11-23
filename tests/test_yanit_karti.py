"""panel/yanit-karti.js — kurul yanıtı kartı (node ile)."""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
from panel_defter import md_html  # noqa: E402

JS = KOK / "panel" / "yanit-karti.js"
KOD = ("const k=require(process.argv[1]);const [f,a]=JSON.parse(process.argv[2]);"
       "console.log(JSON.stringify(k[f](a)))")

TAM = ("# 20261120-x — Deneme\n\n## Kısa yanıt\nCevap **budur**.\n\n## Dayanak\n- Puan 80 ✅ — `veri/a.csv`, n=12\n"
       "- Pay 🟡\n\n## Bilinmeyenler\n- Ağırlık ⛔ — teyit bekliyor\n\n## Not\n- öneri: `okr`\n")


def cagir(fonk, arg):
    r = subprocess.run(["node", "-e", KOD, str(JS), json.dumps([fonk, arg])],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def kart(yanit, **ek):
    return cagir("kart", {"etiket_lbl": "CEO ONAYLI YANIT", "yanit_html": md_html(yanit), **ek})


@unittest.skipUnless(shutil.which("node"), "node yok")
class YanitKartiTest(unittest.TestCase):
    def test_dort_bolum_tanınır_baslik_atilir(self):
        b = cagir("bolumle", md_html(TAM))
        self.assertEqual([x["tur"] for x in b["bolumler"]], ["kisa", "dayanak", "bilinmeyen", "not"])
        self.assertEqual(b["on"], "")
        self.assertFalse(b["kontrol"])

    def test_tam_yanitta_uyari_yok_bolumler_sirali(self):
        h = kart(TAM)
        self.assertNotIn("Kontrol edilmesi gerekebilir", h)
        self.assertNotIn("20261120-x", h)
        sira = [h.index(s) for s in ("kart-kisa", "Dayanak", "kart-bilinmeyen", "kart-not")]
        self.assertEqual(sira, sorted(sira))

    def test_rozet_ve_aciklama(self):
        h = kart(TAM)
        self.assertIn('class="rozet r-bir" title="birincil">✅', h)
        self.assertIn('class="rozet r-yok" title="doğrulanamadı">⛔', h)
        self.assertIn("rozet-aciklama", h)

    def test_zorunlu_baslik_eksikse_uyari(self):
        h = kart(TAM.replace("## Bilinmeyenler\n", "## Belirsizler\n"))
        self.assertIn("Kontrol edilmesi gerekebilir", h)
        self.assertIn("Belirsizler", h)   # içerik kaybolmaz

    def test_not_yoksa_uyari_yok(self):
        self.assertNotIn("Kontrol edilmesi gerekebilir", kart(TAM.split("## Not")[0]))

    def test_basliksiz_yanit_duz_gosterilir_uyariyla(self):
        h = kart("Sadece düz metin.")
        self.assertIn("Kontrol edilmesi gerekebilir", h)
        self.assertIn("<p>Sadece düz metin.</p>", h)

    def test_kurula_not_ve_imza_en_altta(self):
        h = kart(TAM, kurula_not_html="<p>Kurula söz</p>", danisman_ad="Okr", tarih="20 Kasım 2026",
                 imzalar={"denetci": True, "ceo": True})
        self.assertLess(h.index("kart-not"), h.index("KURULA NOT"))
        self.assertLess(h.index("KURULA NOT"), h.index("kart-imza"))
        self.assertIn("Okr · 20 Kasım 2026 · Denetçi ✓ · CEO ✓", h)

    def test_ceo_imzasi_yoksa_tire(self):
        h = kart(TAM, imzalar={"denetci": True, "ceo": False})
        self.assertIn("Denetçi ✓ · CEO —", h)

    def test_danisman_adi_kacirilir(self):
        self.assertIn("&lt;b&gt;", kart(TAM, danisman_ad="<b>"))


if __name__ == "__main__":
    unittest.main()
