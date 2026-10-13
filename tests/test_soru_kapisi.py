"""Q&A Danışmanı — giriş ve çıkış kapısı (sirket/QA-DANISMANI.md, NOVE-KURULUM.md §2 adım 1 ve 8).

LLM yok, para yok. python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import soru_kaydi as sk  # noqa: E402
import soru_kapisi as qa  # noqa: E402

TR = timezone(timedelta(hours=3))
OGLEN = datetime(2026, 10, 12, 12, 0, tzinfo=TR)
SORU = "Q3 bütçe sapmasının ana nedenleri neler?"
UYE = "uye@nove.group"


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "deploy").mkdir()
        (self.kok / "deploy" / "roller.json").write_text(
            json.dumps({UYE: "kurul", "kagan@nove.group": "yonetici", "eski@nove.group": "pasif"}),
            encoding="utf-8")

    def yeni(self, soru=SORU, soran=UYE, simdi=OGLEN, **kw):
        return qa.yeni(self.kok, soru, soran, simdi=simdi, **kw)

    def kayit(self, soru_id):
        return sk.yol(soru_id, self.kok).read_text(encoding="utf-8")


class KayitAcmaTesti(Kurulum):
    def test_soru_kaydi_ve_gelen_dosyasi_acilir(self):
        sonuc = self.yeni()
        self.assertEqual(sonuc["sonuc"], "acildi")
        self.assertRegex(sonuc["soru_id"], r"^20261012-1200-[a-z]{4}$")
        metin = self.kayit(sonuc["soru_id"])
        self.assertEqual(sk.alan(metin, "soru"), SORU)
        self.assertEqual(sk.alan(metin, "soran"), f"{UYE} (rol: kurul)")
        self.assertEqual(sk.alan(metin, "durum"), "alındı")
        self.assertEqual(sk.alan(metin, "bütçe"), "6,00 USD")
        gelen = json.loads((self.kok / "gelen" / f"{sonuc['soru_id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(gelen["soru"], SORU)
        self.assertEqual(gelen["soran"], UYE)

    def test_kuru_hicbir_sey_yazmaz(self):
        sonuc = self.yeni(kuru=True)
        self.assertEqual(sonuc["sonuc"], "acildi")
        self.assertFalse((self.kok / "sirket-log").exists())
        self.assertFalse((self.kok / "gelen").exists())

    def test_eposta_buyuk_harfle_gelse_de_rol_bulunur(self):
        self.assertEqual(self.yeni(soran="Uye@Nove.Group")["sonuc"], "acildi")


class RolTesti(Kurulum):
    def test_rol_dosyasinda_olmayan_soru_soramaz(self):
        sonuc = self.yeni(soran="yabanci@ornek.com")
        self.assertEqual(sonuc["sonuc"], "reddedildi")
        self.assertFalse((self.kok / "sirket-log").exists())

    def test_kurul_ya_da_yonetici_olmayan_rol_soru_soramaz(self):
        self.assertEqual(self.yeni(soran="eski@nove.group")["sonuc"], "reddedildi")

    def test_rol_dosyasi_yoksa_kimse_soru_soramaz(self):
        (self.kok / "deploy" / "roller.json").unlink()
        sonuc = self.yeni()
        self.assertEqual(sonuc["sonuc"], "reddedildi")
        self.assertIn("roller.json", sonuc["sebep"])


class OnKontrolTesti(Kurulum):
    def test_cok_kisa_soru_kayda_girmez(self):
        for soru in ("", "   ", "bütçe?", "Q3 bütçe"):
            with self.subTest(soru=soru):
                sonuc = self.yeni(soru=soru)
                self.assertEqual(sonuc["sonuc"], "reddedildi")
                self.assertIn("açar mısın", sonuc["sebep"])

    def test_ayni_soru_on_dakika_icinde_ikinci_kayit_acmaz(self):
        ilk = self.yeni()
        ikinci = self.yeni(soru="  q3 Bütçe sapmasının ana   nedenleri neler? ", simdi=OGLEN + timedelta(minutes=9))
        self.assertEqual(ikinci["sonuc"], "var")
        self.assertEqual(ikinci["soru_id"], ilk["soru_id"])
        self.assertEqual(len(list((self.kok / "sirket-log" / "sorular").glob("*.md"))), 1)

    def test_on_dakikadan_sonra_ayni_soru_yeni_kayit(self):
        ilk = self.yeni()
        ikinci = self.yeni(simdi=OGLEN + timedelta(minutes=11))
        self.assertEqual(ikinci["sonuc"], "acildi")
        self.assertNotEqual(ikinci["soru_id"], ilk["soru_id"])

    def test_baskasinin_ayni_sorusu_tekrar_sayilmaz(self):
        self.yeni()
        self.assertEqual(self.yeni(soran="kagan@nove.group")["sonuc"], "acildi")

    def test_gunluk_soru_hakki_dolunca_kayda_girmez(self):
        for i in range(ayar.KURUL_UYESI_GUNLUK_SORU):
            self.assertEqual(self.yeni(soru=f"{SORU} ({i})", simdi=OGLEN + timedelta(minutes=i))["sonuc"], "acildi")
        sonuc = self.yeni(soru=f"{SORU} (son)", simdi=OGLEN + timedelta(minutes=30))
        self.assertEqual(sonuc["sonuc"], "reddedildi")
        self.assertIn("soru hakkın doldu", sonuc["sebep"])

    def test_dunku_sorular_bugunku_hakka_sayilmaz(self):
        for i in range(ayar.KURUL_UYESI_GUNLUK_SORU):
            self.yeni(soru=f"{SORU} ({i})", simdi=OGLEN - timedelta(days=1, minutes=i))
        self.assertEqual(self.yeni()["sonuc"], "acildi")

    def test_mesai_disi_soru_kayda_girer_ve_not_duser(self):
        sonuc = self.yeni(simdi=OGLEN.replace(hour=21))
        self.assertEqual(sonuc["sonuc"], "acildi")
        self.assertIn("mesai dışı", sk.alan(self.kayit(sonuc["soru_id"]), "not"))

    def test_sirket_butcesi_doluysa_soru_kayda_girer_ve_not_duser(self):
        with mock.patch.object(ayar, "gunluk_maliyet", return_value=ayar.GUNLUK_MALIYET_TAVANI_USD):
            sonuc = self.yeni()
        self.assertEqual(sonuc["sonuc"], "acildi")
        self.assertIn("bütçe", sk.alan(self.kayit(sonuc["soru_id"]), "not"))


class MaskelemeTesti(Kurulum):
    def test_kisisel_veri_maskelenir_ve_sayilir(self):
        sonuc = self.yeni(soru="0532 418 27 63 numaralı hastanın şikâyeti, hasta@ornek.com, TC 10000000146 neden kapanmadı?")
        metin = self.kayit(sonuc["soru_id"])
        soru = sk.alan(metin, "soru")
        self.assertEqual(soru, "[telefon] numaralı hastanın şikâyeti, [e-posta], TC [tc-no] neden kapanmadı?")
        self.assertEqual(sk.alan(metin, "maskelendi"), "e-posta (1), telefon (1), tc-no (1)")
        for ham in ("0532", "hasta@ornek.com", "10000000146"):
            self.assertNotIn(ham, metin)
            self.assertNotIn(ham, (self.kok / "gelen" / f"{sonuc['soru_id']}.json").read_text(encoding="utf-8"))

    def test_maskeli_soru_denetci_on_kontrolunden_gecer(self):
        """Maskeleme ve Denetçi aynı desenleri kullanır (QA-DANISMANI.md §3)."""
        import bekci
        maskeli, _ = qa.maskele("hasta 0212 345 67 89, biri@ornek.com, 10000000146")
        self.assertEqual(bekci.on_kontrol(maskeli), [])


class IletTesti(Kurulum):
    def setUp(self):
        super().setUp()
        self.soru_id = self.yeni()["soru_id"]
        self.yol = sk.yol(self.soru_id, self.kok)
        sk.bolum_ekle(self.yol, "## Dağıtım\n- danışman: Finans\n")
        cikti = self.kok / "takimlar" / "finans" / "cikti"
        cikti.mkdir(parents=True)
        (cikti / f"{self.soru_id}-taslak.md").write_text("Sapmanın %70'i pazarlamadan (n=2.140).\n", encoding="utf-8")

    def ekle(self, *bolumler):
        for b in bolumler:
            sk.bolum_ekle(self.yol, b)

    DENETCI_KABUL = "## Denetçi\n- karar: **kabul**\n"
    CEO_ONAY = "## CEO — karar: onay\n- kurula not: Veri 30 Eylül'e kadar.\n"

    def defter(self):
        return (self.kok / "yanitlar" / f"{self.soru_id}.md").read_text(encoding="utf-8")

    def test_iki_imzayla_iletilir(self):
        self.ekle(self.DENETCI_KABUL, self.CEO_ONAY)
        sonuc = qa.ilet(self.kok, self.soru_id, simdi=OGLEN)
        self.assertEqual(sonuc["etiket"], "onaylı")
        defter = self.defter()
        self.assertIn(f"- soru: {SORU}", defter)
        self.assertIn(f"- soran: {UYE}", defter)
        self.assertIn("- danışman: Finans", defter)
        self.assertIn("- Denetçi: ✔ · CEO: ✔", defter)
        self.assertIn("Veri 30 Eylül'e kadar.", defter)
        self.assertIn("Sapmanın %70'i pazarlamadan", defter)
        self.assertEqual(sk.alan(self.kayit(self.soru_id), "durum"), "iletildi")

    def test_ceo_onayi_yoksa_iletilmez(self):
        self.ekle(self.DENETCI_KABUL)
        with self.assertRaises(qa.IletHatasi):
            qa.ilet(self.kok, self.soru_id)
        self.assertFalse((self.kok / "yanitlar").exists())

    def test_denetci_kabulunden_sonra_ceo_onayi_gerekir(self):
        """Eski CEO onayı, sonraki bir Denetçi kararını kapsamaz."""
        self.ekle(self.DENETCI_KABUL, self.CEO_ONAY, self.DENETCI_KABUL)
        with self.assertRaises(qa.IletHatasi):
            qa.ilet(self.kok, self.soru_id)

    def test_denetci_kabulu_yoksa_ceo_onayi_yetmez(self):
        self.ekle("## Denetçi\n- karar: **red**\n", self.CEO_ONAY)
        with self.assertRaises(qa.IletHatasi):
            qa.ilet(self.kok, self.soru_id)

    def test_ceo_kapaliyken_etiketle_iletilir(self):
        self.ekle(self.DENETCI_KABUL, "## CEO — kontrol yapılmadı\n")
        sonuc = qa.ilet(self.kok, self.soru_id)
        self.assertEqual(sonuc["etiket"], "CEO kontrolü yapılmadı")
        self.assertIn("- Denetçi: ✔ · CEO: —", self.defter())

    def test_onaylanamadi_gerekceyle_deftere_girer_yanit_metni_girmez(self):
        self.ekle(self.DENETCI_KABUL, "## CEO — karar: red\n")
        sonuc = qa.ilet(self.kok, self.soru_id, onaylanamadi="CEO: neden kırılımı yok")
        self.assertEqual(sonuc["etiket"], "onaylanamadı")
        defter = self.defter()
        self.assertIn("- etiket: onaylanamadı", defter)
        self.assertIn("CEO: neden kırılımı yok", defter)
        self.assertNotIn("Sapmanın %70'i", defter)
        self.assertEqual(sk.alan(self.kayit(self.soru_id), "durum"), "onaylanamadı")

    def test_defter_kaydi_degistirilmez(self):
        self.ekle(self.DENETCI_KABUL, self.CEO_ONAY)
        qa.ilet(self.kok, self.soru_id)
        with self.assertRaises(qa.IletHatasi):
            qa.ilet(self.kok, self.soru_id)


class MainTesti(Kurulum):
    def test_kullanim_hatasi_2(self):
        self.assertEqual(qa.main([]), 2)
        self.assertEqual(qa.main(["--yeni", SORU]), 2)

    def test_yeni_kuru(self):
        with mock.patch.object(qa, "KOK", self.kok):
            self.assertEqual(qa.main(["--yeni", SORU, "--soran", UYE, "--kuru"]), 0)
        self.assertFalse((self.kok / "sirket-log").exists())

    def test_reddedilen_soru_cikis_1(self):
        with mock.patch.object(qa, "KOK", self.kok):
            self.assertEqual(qa.main(["--yeni", "kısa", "--soran", UYE]), 1)


if __name__ == "__main__":
    unittest.main()
