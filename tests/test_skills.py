"""`skills/` katmanı: her SKILL.md'nin sözleşmesi ve takim.md ↔ skills bağının bütünlüğü.

Nove Kurul Ofisi danışmanlarının yetenek sözleşmesi.
"""
import re
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import agents_uret as au  # noqa: E402
import ayar  # noqa: E402

ZORUNLU_ALANLAR = ("name", "description", "kaynak", "lisans", "uyarlayan", "takimlar")


def _skill_yollari():
    return sorted((KOK / "skills").glob("*/SKILL.md"))


def _takim_yollari():
    """Kurulu takımlar; kurulumdaki danışmanlar (frontmatter'sız takim.md) sözleşmeye henüz tabi değil."""
    return [KOK / "takimlar" / ad / "takim.md" for ad in ayar.kurulu_takimlar(KOK)]


class SkillSozlesmesiTesti(unittest.TestCase):
    def test_her_skill_zorunlu_frontmatteri_tasir(self):
        for yol in _skill_yollari():
            with self.subTest(skill=yol.parent.name):
                fm, govde = au.ayristir(yol.read_text(encoding="utf-8"))
                for alan in ZORUNLU_ALANLAR:
                    self.assertIn(alan, fm, f"{yol}: {alan} eksik")
                self.assertEqual(fm["name"], yol.parent.name, f"{yol}: name klasör adıyla eşleşmiyor")
                self.assertTrue(govde.strip(), f"{yol}: gövde boş")

    def test_skill_adlari_ascii_kebab_case(self):
        for yol in _skill_yollari():
            with self.subTest(skill=yol.parent.name):
                self.assertRegex(yol.parent.name, r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_her_skill_ogrenilenler_bolumu_tasir(self):
        """Ajan koşuda aldığı veriyle kendini geliştirir: her yetenek bunu yazılı taşır."""
        for yol in _skill_yollari():
            with self.subTest(skill=yol.parent.name):
                metin = yol.read_text(encoding="utf-8")
                self.assertIn("## Öğrenilenler", metin)
                self.assertIn("kendini geliştir", metin)
                self.assertIn("defter.md", metin)

    def test_uyarlanan_skiller_kaynak_ve_degisiklik_bolumu_tasir(self):
        """Dışarıdan alınan her yetenek nereden geldiğini ve neyin değiştiğini yazar."""
        for yol in _skill_yollari():
            fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
            if not str(fm.get("kaynak", "")).startswith("http"):
                continue
            with self.subTest(skill=yol.parent.name):
                metin = yol.read_text(encoding="utf-8")
                self.assertIn("## Kaynak ve değişiklikler", metin)
                self.assertIn("Orijinalden alınanlar", metin)
                self.assertIn("Değiştirilenler", metin)

    def test_skill_uzunlugu_sinirda(self):
        for yol in _skill_yollari():
            with self.subTest(skill=yol.parent.name):
                self.assertLessEqual(len(yol.read_text(encoding="utf-8").splitlines()), 250)


class KuyrukKapatmaTesti(unittest.TestCase):
    """Her takım işini bitirince kuyruk maddesini `tamam` yapmalı.

    Yapmazsa madde `bekliyor` kalır, `dagitici.bekleyen_sayisi` onu "iş var" sayar ve takım
    her sabah aynı işi para harcayarak tekrarlar. 2026-09-16'da canlıda görüldü: karar-takibi
    başarılı koştu (0.281 USD, bekçi kabul) ama maddesi bekliyor kaldı; haftalik-rapor'unki
    de o öğleden beri takılıydı. Talimat dört takımın da `takim.md`'sinde olmalı — biri
    unutulursa sessizce para yakar.
    """

    def test_her_takim_kuyruk_maddesini_kapatmayi_bildiriyor(self):
        for yol in _takim_yollari():
            with self.subTest(takim=yol.parent.name):
                metin = yol.read_text(encoding="utf-8")
                self.assertIn("kuyruk maddesini `tamam` yap", metin,
                              "%s: koşu adımlarında kuyruk kapatma talimatı yok" % yol.parent.name)


class TakimSkillBagiTesti(unittest.TestCase):
    def test_her_takim_en_az_bir_skill_bildirir(self):
        for yol in _takim_yollari():
            with self.subTest(takim=yol.parent.name):
                fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
                self.assertIn("skills", fm, f"{yol}: skills alanı yok")
                self.assertTrue(fm["skills"], f"{yol}: skills boş")

    def test_iskelet_bos_skills_alani_tasir(self):
        fm, govde = au.ayristir((KOK / "takimlar/_iskelet/takim.md").read_text(encoding="utf-8"))
        self.assertEqual(fm.get("skills"), [])
        self.assertIn("## Yetenekler", govde)

    def test_bildirilen_her_skill_diskte_var(self):
        mevcut = {y.parent.name for y in _skill_yollari()}
        for yol in _takim_yollari():
            fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
            for ad in fm.get("skills", []):
                with self.subTest(takim=yol.parent.name, skill=ad):
                    self.assertIn(ad, mevcut, f"{yol}: skills/{ad}/SKILL.md yok")

    def test_skill_takimlar_alani_takim_md_ile_tutarli(self):
        """skills/<ad>/SKILL.md takimlar: listesi ile takim.md skills: listesi çift yönlü tutarlı olmalı."""
        takim_skill = {}
        for yol in _takim_yollari():
            fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
            takim_skill[yol.parent.name] = set(fm.get("skills", []))
        for yol in _skill_yollari():
            fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
            for takim in fm.get("takimlar", []):
                with self.subTest(skill=yol.parent.name, takim=takim):
                    self.assertIn(takim, takim_skill, f"{yol}: bilinmeyen takım {takim}")
                    self.assertIn(yol.parent.name, takim_skill[takim],
                                  f"{yol}: {takim}/takim.md bu yeteneği bildirmiyor")

    def test_govdede_yetenekler_bolumu_var(self):
        for yol in _takim_yollari():
            with self.subTest(takim=yol.parent.name):
                self.assertIn("## Yetenekler", yol.read_text(encoding="utf-8"))


class YeteneklerKatalogTesti(unittest.TestCase):
    def test_katalog_her_skilli_listeler(self):
        katalog = (KOK / "sirket/YETENEKLER.md").read_text(encoding="utf-8")
        for yol in _skill_yollari():
            with self.subTest(skill=yol.parent.name):
                self.assertIn(yol.parent.name, katalog)

    def test_katalog_uc_gerekceyi_tasir(self):
        katalog = (KOK / "sirket/YETENEKLER.md").read_text(encoding="utf-8").lower()
        for parca in ("token", "hatırla", "geliş"):
            self.assertIn(parca, katalog)

    def test_katalog_kaynak_urllerini_tasir(self):
        katalog = (KOK / "sirket/YETENEKLER.md").read_text(encoding="utf-8")
        for yol in _skill_yollari():
            fm, _ = au.ayristir(yol.read_text(encoding="utf-8"))
            kaynak = str(fm.get("kaynak", ""))
            if not kaynak.startswith("http"):
                continue
            with self.subTest(skill=yol.parent.name):
                self.assertIn(re.split(r"\s", kaynak)[0], katalog)


class KimlikDosyasiTesti(unittest.TestCase):
    def test_kimlik_dosyasi_repoda_var_ve_kim_kimdir_anlatir(self):
        metin = (KOK / "sirket/AJAN-KIMLIGI.md").read_text(encoding="utf-8")
        for baslik in ("## Sen kimsin", "## Kim kimdir", "## Sistem nasıl döner",
                       "## Takıldığında", "## Asla"):
            self.assertIn(baslik, metin)
        for kisi in ("Kurul üyesi", "Denetçi", "İş Dağıtımcı", "CEO Ajanı"):
            self.assertIn(kisi, metin)

    def test_kimlik_dosyasi_diskteki_takimlari_kapsar(self):
        """Kimlik dosyası takım adını saymaz ama CLAUDE.md tablosuna yönlendirir; tablo diskle uyumlu olmalı."""
        metin = (KOK / "sirket/AJAN-KIMLIGI.md").read_text(encoding="utf-8")
        self.assertIn("CLAUDE.md", metin, "kimlik dosyası takım tablosuna yönlendirmiyor")
        tablo = (KOK / "CLAUDE.md").read_text(encoding="utf-8")
        for yol in _takim_yollari():
            with self.subTest(takim=yol.parent.name):
                self.assertIn(yol.parent.name, tablo, f"CLAUDE.md {yol.parent.name} takımını saymıyor")


if __name__ == "__main__":
    unittest.main()
