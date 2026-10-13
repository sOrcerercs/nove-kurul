"""Uçtan uca soru akışı (NOVE-KURULUM.md §2, §12 kabul ölçütleri) — sekiz adım, gerçek sürücü kodu.

Sahte olan yalnız LLM'ler: danışmanın claude koşusu, Denetçi'nin modeli, CEO'nun claude koşusu.
Q&A Danışmanı → İş Dağıtımcı → danışman → Denetçi → CEO → (r- düzeltme →) → Yanıt defteri.
python3 -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import ceo  # noqa: E402
import dagitici  # noqa: E402
import kos  # noqa: E402
import soru_kapisi  # noqa: E402
import soru_kaydi as sk  # noqa: E402

TR = timezone(timedelta(hours=3))
OGLEN = datetime(2026, 10, 12, 12, 0, tzinfo=TR)
UYE = "uye@nove.group"
SORU = "Q3 bütçe sapmasının ana nedenleri neler?"
GECTI = {"kaynak": "gecti", "hesap": "gecti", "tutarlilik": "gecti"}


class UctanUcaTesti(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "deploy").mkdir()
        (self.kok / "deploy" / "roller.json").write_text(json.dumps({UYE: "kurul"}), encoding="utf-8")
        (self.kok / "sirket").mkdir()
        shutil.copy(KOK / "sirket" / "CEO-KIMLIGI.md", self.kok / "sirket")
        dizin = self.kok / "takimlar" / "finans"
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text("---\nname: finans\ndescription: Finans danışmanı\nskills: []\n"
                                        "anahtar_kelimeler: [bütçe, nakit, sapma]\n---\n", encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps({"takim": "finans", "kuyruk": []}), encoding="utf-8")
        self.denetci_kararlari, self.ceo_kararlari = [], []
        self.ceo_cagri = 0
        yamalar = [
            mock.patch.object(ayar, "KOK", self.kok), mock.patch.object(kos, "KOK", self.kok),
            # tek saat: kos.py koşu zamanını ayar.simdi_iso'dan alır, dağıtıcı `simdi`den — ikisi aynı olmalı
            mock.patch.object(ayar, "simdi_iso", return_value=OGLEN.isoformat(timespec="seconds")),
            mock.patch.object(kos.agents_uret, "uret"),
            mock.patch.object(kos, "_claude_kos", side_effect=self._danisman),
            mock.patch.object(bekci, "llm_karari", side_effect=lambda ortam, istem: self.denetci_kararlari.pop(0)),
            mock.patch.object(dagitici, "_kostur", side_effect=lambda kok, takim: kos.kos(takim, zorla=True)),
            mock.patch.object(dagitici, "_ceo_baslat",
                              side_effect=lambda kok, sid: ceo.kontrol_et(kok, sid, calistir=self._ceo)),
            mock.patch.object(dagitici, "haiku_sinifla", side_effect=AssertionError("Haiku çağrılmamalı")),
        ]
        for y in yamalar:
            y.start()
            self.addCleanup(y.stop)

    def _danisman(self, metin, fm, takim, kosu, taslak=None):
        Path(kosu).parent.mkdir(parents=True, exist_ok=True)
        Path(kosu).write_text("# Koşu\nveri/q3.csv okundu (n=2.140)\n", encoding="utf-8")
        Path(taslak).parent.mkdir(parents=True, exist_ok=True)
        surum = "düzeltilmiş" if "ceo_bulgulari" in metin else "ilk"
        Path(taslak).write_text(f"Yanıt ({surum}): sapmanın %70'i pazarlamadan (n=2.140, veri/q3.csv).\n",
                                encoding="utf-8")
        return {"hata": False, "maliyet": 1.0, "tur": 5, "metin": "özet"}

    def _ceo(self, istem):
        self.ceo_cagri += 1
        return {"hata": False, "maliyet": 0.4, "tur": 3, "metin": json.dumps(self.ceo_kararlari.pop(0))}

    def surdur(self, sid, en_fazla=8):
        for _ in range(en_fazla):
            dagitici.dagit(self.kok, simdi=OGLEN)
            if sk.alan(sk.yol(sid, self.kok).read_text(encoding="utf-8"), "durum") in ("iletildi", "onaylanamadı"):
                return
        self.fail("soru bitmedi: " + sk.yol(sid, self.kok).read_text(encoding="utf-8"))

    def test_ceo_bir_kez_reddeder_duzeltme_sonra_iki_imzayla_iletilir(self):
        self.denetci_kararlari = [{"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None, "kontrol": GECTI}] * 2
        self.ceo_kararlari = [
            {"karar": "red", "bulgular": ["Neden kırılımı ekle."], "gerekce": "neden yok", "kurula_not": ""},
            {"karar": "onay", "bulgular": [], "gerekce": "tamam", "kurula_not": "Veri 30 Eylül'e kadar."}]
        sid = soru_kapisi.yeni(self.kok, SORU, UYE, simdi=OGLEN)["soru_id"]
        self.surdur(sid)

        metin = sk.yol(sid, self.kok).read_text(encoding="utf-8")
        self.assertEqual(sk.kararlar(metin), [("denetci", "kabul"), ("ceo", "red"), ("denetci", "kabul"), ("ceo", "onay")])
        self.assertEqual(sk.alan(metin, "durum"), "iletildi")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "eşleşen ifadeler"), "bütçe, sapma")
        self.assertAlmostEqual(sk.harcanan(metin), 2.8)
        defter = (self.kok / "yanitlar" / f"{sid}.md").read_text(encoding="utf-8")
        self.assertIn("- etiket: onaylı", defter)
        self.assertIn("Yanıt (düzeltilmiş)", defter)
        self.assertIn("Veri 30 Eylül'e kadar.", defter)
        kuyruk = [(m["id"], m["durum"]) for m in ayar.durum_oku("finans", self.kok)["kuyruk"]]
        self.assertEqual(kuyruk, [(f"s-{sid}", "tamam"), (f"r-{sid}", "tamam")])

    def test_denetci_reddettigi_yanit_ceoya_ulasmaz(self):
        red = {"karar": "red", "gerekce": "412 + 388 = 900 yazılmış", "ihlal_edilen_kural": "üçlü kontrol: hesap",
               "kontrol": {**GECTI, "hesap": "kaldi"}}
        self.denetci_kararlari = [red, red]   # Stop hook yok: sürücü bir kez denetler; yedek ikinci
        sid = soru_kapisi.yeni(self.kok, SORU, UYE, simdi=OGLEN)["soru_id"]
        self.surdur(sid)
        self.assertEqual(self.ceo_cagri, 0)
        defter = (self.kok / "yanitlar" / f"{sid}.md").read_text(encoding="utf-8")
        self.assertIn("- etiket: onaylanamadı", defter)
        self.assertIn("412 + 388 = 900", defter)
        self.assertNotIn("Yanıt (ilk)", defter)

    def test_ceo_iki_kez_reddederse_kurula_gitmez(self):
        self.denetci_kararlari = [{"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None, "kontrol": GECTI}] * 2
        self.ceo_kararlari = [{"karar": "red", "bulgular": ["x"], "gerekce": "ilk red", "kurula_not": ""},
                              {"karar": "red", "bulgular": ["y"], "gerekce": "hâlâ eksik", "kurula_not": ""}]
        sid = soru_kapisi.yeni(self.kok, SORU, UYE, simdi=OGLEN)["soru_id"]
        self.surdur(sid)
        self.assertEqual(self.ceo_cagri, 2)
        defter = (self.kok / "yanitlar" / f"{sid}.md").read_text(encoding="utf-8")
        self.assertIn("- etiket: onaylanamadı", defter)
        self.assertIn("hâlâ eksik", defter)
        self.assertNotIn("Yanıt (", defter)


if __name__ == "__main__":
    unittest.main()
