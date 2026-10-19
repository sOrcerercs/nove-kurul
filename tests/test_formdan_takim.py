"""Danışman formu hattı (docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md).

Ağ yok, para harcamaz; betik geçici bir kökte koşar, gerçek `takimlar/`'a dokunmaz.
python3 -m unittest discover -s tests
"""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import formdan_takim as ft  # noqa: E402

FORM = (KOK / "tests/fikstur/form/kalite.md").read_text(encoding="utf-8")


class OkumaTesti(unittest.TestCase):
    def test_tam_form_okunur(self):
        form = ft.oku(FORM)
        self.assertEqual(form["ad"], "Kalite")                       # `>` örnek satırı ezmez
        self.assertEqual(form["sahibi"], "Kalite Müdürü")
        self.assertTrue(form["meslek"].startswith("Kalite danışmanı olarak"))
        self.assertEqual(form["anahtar_kelimeler"], ["kalite", "şikâyet", "memnuniyet", "denetim"])
        self.assertEqual(len(form["ornek_sorular"]), 2)              # "3. ?" ve boş 4., 5. düşer
        self.assertEqual(len(form["veri"]), 1)                       # boş tablo satırı sayılmaz
        self.assertEqual(form["teyit"], ["Bölüm ağırlıkları: Kalite Müdürü"])  # girintili iki noktalı satır
        self.assertEqual(form["iyi_yanit"], "Önce tek cümlelik cevap.\nSonra kaynaklı dayanak tablosu.")
        self.assertEqual(form["tempo"], "")                          # yalnız "?" boş
        self.assertEqual(form["anahtarlar"], ["QA_READONLY_URL"])
        self.assertEqual(ft.eksikler(form), [])

    def test_bos_sablon_butun_zorunlulari_listeler(self):
        sablon = (KOK / "formlar/DANISMAN-FORMU.md").read_text(encoding="utf-8")
        self.assertEqual(len(ft.eksikler(ft.oku(sablon))), len(ft.ZORUNLU))

    def test_iki_eksik_birden_listelenir(self):
        """Test 2: ilk eksikte durulmaz."""
        metin = FORM.replace("- Tek cümleyle mesleği: Kalite danışmanı olarak kurulun çağrı kalitesi ve şikâyet "
                             "sorularını değerlendirme verisiyle yanıtlamak.", "- Tek cümleyle mesleği:")
        metin = metin.replace("| Kalite değerlendirmeleri | çağrı puanları, bölüm skorları | QA veritabanı (salt okunur rol) "
                              "| BT | günlük |\n", "")
        self.assertEqual(ft.eksikler(ft.oku(metin)),
                         ["eksik: §1 Tek cümleyle mesleği", "eksik: §3 Veri tablosu (en az bir dolu satır)"])

    def test_soru_isareti_bos_sayilir(self):
        """Test 3."""
        metin = FORM.replace("yönlendirir): kalite, şikâyet, memnuniyet, denetim", "yönlendirir): ?")
        self.assertEqual(ft.eksikler(ft.oku(metin)), ["eksik: §2 Anahtar kelimeler (en az bir)"])


class KilitTesti(unittest.TestCase):
    """K6: insanın dosyaları kuralla değil yetkiyle kapalı; eski altı kilit de yerinde (12'nin 12'si)."""

    def test_insan_dosyalari_yetkiyle_kilitli(self):
        deny = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]["deny"]
        beklenen = ["Read(./.env)", "Read(./.env.*)"]
        for yol in ("./yanitlar/**", "./formlar/onayli/**", "./takimlar/*/kurallar.md",
                    "./ANAYASA.md", "./sirket/CEO-KIMLIGI.md"):
            beklenen += [f"Write({yol})", f"Edit({yol})"]
        self.assertEqual(len(beklenen), 12)
        for satir in beklenen:
            with self.subTest(satir=satir):
                self.assertIn(satir, deny)


if __name__ == "__main__":
    unittest.main()
