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
import agents_uret  # noqa: E402
import ayar  # noqa: E402
import dagitici  # noqa: E402
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


class KontrolTesti(unittest.TestCase):
    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.kok = Path(self._g.name)
        shutil.copytree(KOK / "skills/kurul-yaniti", self.kok / "skills/kurul-yaniti")

    def tearDown(self):
        self._g.cleanup()

    def test_telefon_durdurur_degeri_basmaz(self):
        """Test 4a."""
        metin = FORM.replace("  - Tek bir çağrıdan", "  - Arayan 0532 123 45 67 ise\n  - Tek bir çağrıdan")
        sorunlar = ft.kisisel_veri(metin)
        self.assertEqual(sorunlar, ["kişisel veri: telefon numarası (4. Kurallar (kurallar.md'ye gidecek))"])
        self.assertNotIn("0532", " ".join(sorunlar))

    def test_tc_kimlik_durdurur(self):
        """Test 4b — sağlama hanesi geçerli sentetik numara."""
        metin = FORM.replace("değerlendirilen temsilcinin adı", "değerlendirilen temsilcinin adı, 10000000146")
        self.assertIn("kişisel veri: TC kimlik numarası (3. Veri)", ft.kisisel_veri(metin))

    def test_temiz_form_ve_bos_sablon_temiz(self):
        self.assertEqual(ft.kisisel_veri(FORM), [])
        self.assertEqual(ft.kisisel_veri((KOK / "formlar/DANISMAN-FORMU.md").read_text(encoding="utf-8")), [])

    def test_olmayan_yetenek_durdurur(self):
        """Test 5."""
        self.assertEqual(ft.yetenek_sorunlari(self.kok, ["kurul-yaniti", "olmayan-yetenek"]),
                         ["yetenek yok: skills/olmayan-yetenek/SKILL.md"])

    def test_takimlar_alani_olmayan_yetenek_durdurur(self):
        yol = self.kok / "skills/bozuk/SKILL.md"
        yol.parent.mkdir(parents=True)
        yol.write_text("---\nname: bozuk\n---\n\n# bozuk\n", encoding="utf-8")
        self.assertEqual(ft.yetenek_sorunlari(self.kok, ["bozuk"]),
                         ["yetenek bozuk: skills/bozuk/SKILL.md 'takimlar: [...]' alanı taşımıyor"])

    def test_cakisma_uyari_metni(self):
        """Test 6 (birim): kurulu finans 'Şikâyet' taşıyor; büyük/küçük harf farkı çakışmayı gizlemez."""
        (self.kok / "takimlar/finans").mkdir(parents=True)
        (self.kok / "takimlar/finans/takim.md").write_text(
            "---\nname: finans\ndescription: x\nanahtar_kelimeler: [bütçe, Şikâyet]\n---\n\n# Finans\n",
            encoding="utf-8")
        uyarilar = ft.cakismalar(self.kok, "kalite", ["kalite", "şikâyet"])
        self.assertEqual(len(uyarilar), 1)
        self.assertIn("'şikâyet' → finans", uyarilar[0])

    def test_kendi_kelimesi_cakisma_sayilmaz(self):
        """`--yeniden`de danışman zaten kurulu: kendi kelimeleri uyarı vermez."""
        (self.kok / "takimlar/kalite").mkdir(parents=True)
        (self.kok / "takimlar/kalite/takim.md").write_text(
            "---\nname: kalite\ndescription: x\nanahtar_kelimeler: [kalite]\n---\n", encoding="utf-8")
        self.assertEqual(ft.cakismalar(self.kok, "kalite", ["kalite"]), [])


class _GeciciKok(unittest.TestCase):
    """Geçici kök: iskelet, kurul-yaniti, kurulumdaki kalite (yalnız başlıklı takim.md) ve onaylı form."""

    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.kok = Path(self._g.name)
        shutil.copytree(KOK / "takimlar/_iskelet", self.kok / "takimlar/_iskelet")
        shutil.copytree(KOK / "skills/kurul-yaniti", self.kok / "skills/kurul-yaniti")
        (self.kok / "takimlar/kalite").mkdir()
        (self.kok / "takimlar/kalite/takim.md").write_text("# Kalite Danışmanı\n", encoding="utf-8")
        self.form(FORM)

    def tearDown(self):
        self._g.cleanup()

    def form(self, metin):
        yol = self.kok / "formlar/onayli/kalite.md"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(metin, encoding="utf-8")

    def oku(self, yol):
        return (self.kok / yol).read_text(encoding="utf-8")


class UretimTesti(_GeciciKok):
    def test_tam_form_kurulu_danisman_uretir(self):
        """Test 1 + bağlantı: üretilen danışmanı sürücü, dağıtıcı ve ajan üretici kurulu sayar."""
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual((sonuc["durum"], sonuc["sebepler"]), ("yazildi", []))
        fm, govde = ayar.frontmatter(self.oku("takimlar/kalite/takim.md"))
        self.assertEqual(fm["name"], "kalite")
        self.assertTrue(fm["description"].startswith("Kalite danışmanı olarak"))
        self.assertEqual(fm["skills"], ["kurul-yaniti"])
        self.assertEqual(fm["anahtar_kelimeler"], ["kalite", "şikâyet", "memnuniyet", "denetim"])
        self.assertEqual(fm["gerekli_anahtarlar"], ["QA_READONLY_URL"])
        self.assertEqual((fm["model"], fm["renk"], fm["butce_usd"]), ("sonnet", "mor", "2"))
        self.assertIn("Sahibi: Kalite Müdürü", govde)
        self.assertIn("kuyruk maddesini `tamam` yap", govde)
        self.assertIn("| Kalite değerlendirmeleri |", govde)
        self.assertEqual(ayar.kurulu_takimlar(self.kok), ["kalite"])
        self.assertIn("şikâyet", dagitici.aktif_danismanlar(self.kok)[0]["kelimeler"])
        self.assertEqual(agents_uret.uret(self.kok), ["kalite"])
        skill_fm, _ = ayar.frontmatter(self.oku("skills/kurul-yaniti/SKILL.md"))
        self.assertEqual(skill_fm["takimlar"], ["kalite"])
        self.assertEqual(json.loads(self.oku("takimlar/kalite/durum.json"))["takim"], "kalite")
        self.assertIn("# Defter — kalite", self.oku("takimlar/kalite/defter.md"))
        for klasor in ("kosu", "cikti"):
            self.assertTrue((self.kok / "takimlar/kalite" / klasor).is_dir())
        kurallar = self.oku("takimlar/kalite/kurallar.md")
        self.assertIn("- Tek bir çağrıdan ekip geneli hakkında hüküm kurmak", kurallar)
        self.assertIn("- Değerlendirilen çağrı sayısı (n)", kurallar)
        self.assertIn("Bölüm ağırlıkları: Kalite Müdürü", kurallar)
        self.assertIn("Bölüm ağırlıklı kalite skoru", kurallar)

    def test_iskelet_kalite_olcutleri_korunur(self):
        """kurallar.md iskeletin 'Çıktı kalite ölçütleri' maddelerinin hepsini taşır (iskelet değişirse kırmızı)."""
        iskelet = (KOK / "takimlar/_iskelet/kurallar.md").read_text(encoding="utf-8")
        olcutler = [s for s in iskelet.split("## Çıktı kalite ölçütleri", 1)[1].splitlines() if s.startswith("- ")]
        self.assertEqual(len(olcutler), 2)
        uretilen = ft.kurallar_md("kalite", ft.oku(FORM))
        for satir in olcutler:
            with self.subTest(satir=satir):
                self.assertIn(satir, uretilen)

    def test_personel_adi_varsayilan_acik(self):
        """Test 10a."""
        self.assertIn("Personel adı ve unvanı yazılabilir.", ft.kurallar_md("kalite", ft.oku(FORM)))

    def test_personel_adi_hayir_ise_yasak(self):
        """Test 10b — hasta/müşteri yasağı her iki durumda da yazılır."""
        metin = FORM.replace("kapatmak için hayır):", "kapatmak için hayır): Hayır")
        kurallar = ft.kurallar_md("kalite", ft.oku(metin))
        self.assertIn("Personel adı yazılmaz.", kurallar)
        self.assertNotIn("Personel adı ve unvanı yazılabilir.", kurallar)
        self.assertIn("Hasta ve müşteri adı, telefon, e-posta, TC kimlik no yazılmaz", kurallar)

    def test_durunca_hicbir_dosya_yazilmaz(self):
        """Test 2 + 4 + 5 birlikte: üç sebep listelenir, kalite kurulumda kalır, yetenek dosyası değişmez."""
        skill_once = self.oku("skills/kurul-yaniti/SKILL.md")
        metin = FORM.replace("- Tek cümleyle mesleği: Kalite", "- Tek cümleyle mesleği:\n- x: Kalite")
        metin = metin.replace("değerlendirilen temsilcinin adı", "0532 123 45 67")
        metin = metin.replace("kendiliğinden eklenir):", "kendiliğinden eklenir): olmayan-yetenek")
        self.form(metin)
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual(sonuc["durum"], "durdu")
        self.assertEqual(sonuc["sebepler"], ["eksik: §1 Tek cümleyle mesleği",
                                             "kişisel veri: telefon numarası (3. Veri)",
                                             "yetenek yok: skills/olmayan-yetenek/SKILL.md"])
        self.assertTrue(ayar.kurulumda_mi("kalite", self.kok))
        self.assertFalse((self.kok / "takimlar/kalite/kurallar.md").exists())
        self.assertEqual(self.oku("skills/kurul-yaniti/SKILL.md"), skill_once)

    def test_cakisma_uyarir_ve_yazar(self):
        """Test 6 (uçtan uca): uyarı var, durum yazildi."""
        (self.kok / "takimlar/finans").mkdir()
        (self.kok / "takimlar/finans/takim.md").write_text(
            "---\nname: finans\ndescription: x\nanahtar_kelimeler: [şikâyet]\n---\n", encoding="utf-8")
        sonuc = ft.uret(self.kok, "kalite")
        self.assertEqual(sonuc["durum"], "yazildi")
        self.assertEqual(len(sonuc["uyarilar"]), 1)
        self.assertTrue((self.kok / "takimlar/kalite/kurallar.md").exists())


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
