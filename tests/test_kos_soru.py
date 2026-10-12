"""Danışman koşusu kurul sorusunu işler (NOVE-KURULUM.md §2 adım 3–4 ve 6).

Kuyruktaki `s-<soru-id>` (yeni soru) ya da `r-<soru-id>` (CEO red sonrası düzeltme) maddesi isteme girer;
yanıt `cikti/<soru-id>-taslak.md`'ye yazılır; Denetçi taslağı denetler; sürücü kararı soru kaydına kopyalar.
claude çağrılmaz, para harcanmaz. python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import kos  # noqa: E402
import soru_kaydi as sk  # noqa: E402

SID = "20261012-1200-abcd"
SORU = "Q3 bütçe sapmasının ana nedenleri neler?"
KABUL = {"karar": "kabul", "gerekce": "kaynaklı ve hesap tutuyor", "ihlal_edilen_kural": None,
         "kontrol": {"kaynak": "gecti", "hesap": "gecti", "tutarlilik": "gecti"}}


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        dizin = self.kok / "takimlar" / "finans"
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text("---\nname: finans\ndescription: Finans danışmanı\nskills: []\n---\n# finans\n",
                                        encoding="utf-8")
        self.kuyruk([{"id": f"s-{SID}", "durum": "bekliyor", "not": SORU}])
        yol = sk.yol(SID, self.kok)
        yol.parent.mkdir(parents=True)
        yol.write_text(f"# Soru {SID}\n- soran: uye@nove.group (rol: kurul)\n- soru: {SORU}\n- durum: danışmanda\n"
                       "\n## Dağıtım\n- danışman: finans\n", encoding="utf-8")
        self.yamalar = [mock.patch.object(ayar, "KOK", self.kok), mock.patch.object(kos, "KOK", self.kok),
                        mock.patch.object(kos.agents_uret, "uret")]
        for y in self.yamalar:
            y.start()

    def tearDown(self):
        for y in reversed(self.yamalar):
            y.stop()

    def kuyruk(self, maddeler):
        ayar.durum_guncelle("finans", {"takim": "finans", "kuyruk": maddeler}, self.kok)

    def taslak(self):
        return self.kok / "takimlar" / "finans" / "cikti" / f"{SID}-taslak.md"

    def sahte_claude(self, taslak_yaz=True, maliyet=1.2):
        """Ajanın yerine: koşu kaydını ve (isteğe bağlı) taslağı yazar."""
        def kos_(metin, fm, takim, kosu, taslak=None):
            self.istem, self.taslak_arg = metin, taslak
            Path(kosu).parent.mkdir(parents=True, exist_ok=True)
            Path(kosu).write_text("# Koşu\nveri/q3.csv okundu (n=2.140)\n", encoding="utf-8")
            if taslak_yaz:
                self.taslak().parent.mkdir(parents=True, exist_ok=True)
                self.taslak().write_text("Sapmanın %70'i pazarlamadan (n=2.140).\n", encoding="utf-8")
            return {"hata": False, "maliyet": maliyet, "tur": 5, "metin": "özet"}
        return kos_

    def kostur(self, claude=None, llm=KABUL):
        with mock.patch.object(kos, "_claude_kos", side_effect=claude or self.sahte_claude()), \
             mock.patch.object(bekci, "llm_karari", return_value=llm):
            kos.kos("finans", zorla=True)

    def kayit(self):
        return sk.yol(SID, self.kok).read_text(encoding="utf-8")


class MaddeSecimiTesti(Kurulum):
    def test_ilk_bekleyen_soru_maddesi_secilir(self):
        self.kuyruk([{"id": "x-1", "durum": "bekliyor"}, {"id": f"s-{SID}", "durum": "tamam"},
                     {"id": f"r-{SID}", "durum": "bekliyor", "not": "Neden kırılımı ekle."}])
        madde = kos.soru_maddesi("finans", self.kok)
        self.assertEqual((madde["tur"], madde["soru_id"]), ("r", SID))

    def test_soru_maddesi_yoksa_none(self):
        self.kuyruk([])
        self.assertIsNone(kos.soru_maddesi("finans", self.kok))


class IstemTesti(Kurulum):
    def test_yeni_soru_istemi_soruyu_ve_taslak_yolunu_soyler(self):
        self.kostur()
        self.assertIn(SORU, self.istem)
        self.assertIn(f"takimlar/finans/cikti/{SID}-taslak.md", self.istem)
        self.assertEqual(self.taslak_arg, self.taslak())

    def test_duzeltme_istemi_ceo_bulgularini_tasir(self):
        self.kuyruk([{"id": f"r-{SID}", "durum": "bekliyor", "not": "1. Neden kırılımı ekle."}])
        self.kostur()
        self.assertIn(SORU, self.istem, "soru metni soru kaydından okunur")
        self.assertIn("1. Neden kırılımı ekle.", self.istem)
        self.assertIn("düzelt", self.istem)

    def test_soru_maddesi_yoksa_istemde_soru_yok(self):
        self.kuyruk([])
        self.kostur(claude=self.sahte_claude(taslak_yaz=False))
        self.assertNotIn("kurul sorusu", self.istem.lower())
        self.assertIsNone(self.taslak_arg)


class SoruKaydinaKopyaTesti(Kurulum):
    def test_denetci_karari_soru_kaydina_yazilir(self):
        self.kostur()
        metin = self.kayit()
        self.assertEqual(sk.kararlar(metin), [("denetci", "kabul")])
        self.assertEqual(sk.bolum_alani(metin, "## Denetçi", "gerekçe"), "kaynaklı ve hesap tutuyor")
        self.assertEqual(sk.bolum_alani(metin, "## Denetçi", "kontrol"), "kaynak gecti · hesap gecti · tutarlilik gecti")
        self.assertEqual(sk.bolum_alani(metin, "## Denetçi", "maliyet"), "1.200 USD")
        self.assertTrue(sk.bolum_alani(metin, "## Denetçi", "koşu").startswith("takimlar/finans/kosu/"))

    def test_kuyruk_maddesi_tamam_olur(self):
        self.kostur()
        madde = ayar.durum_oku("finans", self.kok)["kuyruk"][0]
        self.assertEqual(madde["durum"], "tamam")

    def test_taslak_yazilmadiysa_denetci_red_ve_kayitta_gorunur(self):
        self.kostur(claude=self.sahte_claude(taslak_yaz=False))
        metin = self.kayit()
        self.assertEqual(sk.kararlar(metin), [("denetci", "red")])
        self.assertIn("taslak", sk.bolum_alani(metin, "## Denetçi", "gerekçe"))

    def test_claude_hatasinda_denetci_atlandi_soru_kaybolmaz(self):
        def hata(metin, fm, takim, kosu, taslak=None):
            return {"hata": True, "maliyet": 0.3, "tur": 0, "metin": "süre tavanı aşıldı"}
        self.kostur(claude=hata)
        metin = self.kayit()
        self.assertEqual(sk.kararlar(metin), [("denetci", "atlandi")])
        self.assertIn("süre tavanı aşıldı", sk.bolum_alani(metin, "## Denetçi", "gerekçe"))
        self.assertEqual(ayar.durum_oku("finans", self.kok)["kuyruk"][0]["durum"], "kacti")

    def test_madde_kosu_sirasinda_yapiliyor(self):
        """Dağıtıcı aynı maddeyi ikinci kez koşturmasın: koşu başlarken madde 'bekliyor' değildir."""
        gorulen = {}

        def claude(metin, fm, takim, kosu, taslak=None):
            gorulen["durum"] = ayar.durum_oku("finans", self.kok)["kuyruk"][0]["durum"]
            return self.sahte_claude()(metin, fm, takim, kosu, taslak)
        self.kostur(claude=claude)
        self.assertEqual(gorulen["durum"], "yapiliyor")


if __name__ == "__main__":
    unittest.main()
