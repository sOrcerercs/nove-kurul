"""İş Dağıtımcı soruyu adımdan adıma taşır (NOVE-KURULUM.md §2 adım 5–8, IS-DAGITIMCI.md Görev 2).

Karar soru kaydındaki bölümlerden verilir:
  Denetçi kabul → CEO başlar · Denetçi red/atlandi → onaylanamadı
  CEO onay (ya da kapalı) → kurula iletilir · CEO red → r-<id> (en fazla 1) · ikinci red → onaylanamadı
CEO başlatma ve iletim sahtelenir. python3 -m unittest discover -s tests
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
import dagitici  # noqa: E402
import soru_kaydi as sk  # noqa: E402

TR = timezone(timedelta(hours=3))
OGLEN = datetime(2026, 10, 12, 12, 0, tzinfo=TR)
SID = "20261012-1200-abcd"

DENETCI_KABUL = "## Denetçi\n- karar: **kabul**\n- gerekçe: temiz\n- maliyet: 1.200 USD\n"
DENETCI_RED = "## Denetçi\n- karar: **red**\n- gerekçe: hesap tutmuyor\n- maliyet: 1.000 USD\n"
CEO_ONAY = "## CEO — karar: onay\n- tur: 1/2\n- gerekçe: tamam\n- maliyet: 0.400 USD\n"
CEO_RED = ("## CEO — karar: red\n- tur: 1/2\n- gerekçe: neden kırılımı yok\n- bulgular:\n"
           "  1. Neden kırılımı ekle.\n  2. Aksiyonlara sahip ve tarih yaz.\n- kurula not: -\n- maliyet: 0.400 USD\n")


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        dizin = self.kok / "takimlar" / "finans"
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text("---\nname: finans\ndescription: Finans\n---\n", encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps({"takim": "finans", "kuyruk": [
            {"id": f"s-{SID}", "durum": "tamam", "not": "soru"}]}), encoding="utf-8")
        self.yol = sk.yol(SID, self.kok)
        self.yol.parent.mkdir(parents=True)
        self.yol.write_text(f"# Soru {SID}\n- soran: uye@nove.group (rol: kurul)\n- soru: Q3 sapması neden?\n"
                            "- durum: danışmanda\n\n## Dağıtım\n- danışman: finans\n- maliyet: 0.000 USD\n",
                            encoding="utf-8")
        self.ceo = mock.MagicMock()
        self.ilet = mock.MagicMock(return_value={"etiket": "onaylı"})

    def ekle(self, *bolumler):
        for b in bolumler:
            sk.bolum_ekle(self.yol, b)

    def ilerlet(self, simdi=OGLEN, **kw):
        return dagitici.sorulari_ilerlet(self.kok, simdi=simdi, ceo_baslat=self.ceo, ilet=self.ilet, **kw)

    def durum(self):
        return sk.alan(self.yol.read_text(encoding="utf-8"), "durum")

    def kuyruk(self):
        return ayar.durum_oku("finans", self.kok)["kuyruk"]


class DenetciSonrasiTesti(Kurulum):
    def test_denetci_kabulunde_ceo_baslar(self):
        self.ekle(DENETCI_KABUL)
        adimlar = self.ilerlet()
        self.ceo.assert_called_once_with(self.kok, SID)
        self.assertEqual(adimlar[0]["adim"], "ceo")
        self.assertEqual(self.durum(), "CEO'da")

    def test_ceo_calisirken_ikinci_kez_baslatilmaz(self):
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        self.ilerlet()
        self.ceo.assert_called_once()

    def test_denetci_reddinde_onaylanamadi_ve_ceoya_gitmez(self):
        self.ekle(DENETCI_RED)
        adimlar = self.ilerlet()
        self.ceo.assert_not_called()
        self.ilet.assert_called_once()
        self.assertIn("hesap tutmuyor", self.ilet.call_args.kwargs["onaylanamadi"])
        self.assertEqual(adimlar[0]["adim"], "onaylanamadı")

    def test_denetci_atlandi_de_onaylanamadi(self):
        self.ekle("## Denetçi\n- karar: **atlandi**\n- gerekçe: danışman koşusu hata verdi\n")
        self.ilerlet()
        self.ceo.assert_not_called()
        self.assertIn("atlandi", self.ilet.call_args.kwargs["onaylanamadi"])

    def test_mesai_disinda_ceo_baslamaz_bekler(self):
        self.ekle(DENETCI_KABUL)
        adimlar = self.ilerlet(simdi=OGLEN.replace(hour=21))
        self.ceo.assert_not_called()
        self.assertEqual(adimlar[0]["adim"], "bekle")
        self.assertIn("mesai", adimlar[0]["sebep"])


class CeoSonrasiTesti(Kurulum):
    def test_ceo_onayinda_iletilir(self):
        self.ekle(DENETCI_KABUL, CEO_ONAY)
        adimlar = self.ilerlet()
        self.ilet.assert_called_once_with(self.kok, SID)
        self.assertEqual(adimlar[0]["adim"], "iletildi")

    def test_ceo_kapaliysa_da_iletilir(self):
        self.ekle(DENETCI_KABUL, "## CEO — kontrol yapılmadı\n")
        self.ilerlet()
        self.ilet.assert_called_once_with(self.kok, SID)

    def test_ceo_reddinde_r_maddesi_bulgularla_acilir(self):
        self.ekle(DENETCI_KABUL, CEO_RED)
        adimlar = self.ilerlet()
        self.assertEqual(adimlar[0]["adim"], "düzeltme")
        r = self.kuyruk()[-1]
        self.assertEqual((r["id"], r["durum"]), (f"r-{SID}", "bekliyor"))
        self.assertIn("1. Neden kırılımı ekle.", r["not"])
        self.assertIn("2. Aksiyonlara sahip ve tarih yaz.", r["not"])
        self.assertEqual(self.durum(), "düzeltmede")
        self.ilet.assert_not_called()

    def test_r_maddesi_bir_kez_acilir(self):
        self.ekle(DENETCI_KABUL, CEO_RED)
        self.ilerlet()
        self.ilerlet()
        self.assertEqual(sum(1 for m in self.kuyruk() if m["id"] == f"r-{SID}"), 1)

    def test_duzeltmeden_sonra_denetci_kabulu_ceoyu_yeniden_baslatir(self):
        self.ekle(DENETCI_KABUL, CEO_RED)
        self.ilerlet()
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        self.ceo.assert_called_once_with(self.kok, SID)

    def test_ikinci_ceo_reddinde_onaylanamadi_yeni_r_yok(self):
        self.ekle(DENETCI_KABUL, CEO_RED, DENETCI_KABUL, CEO_RED.replace("1/2", "2/2"))
        adimlar = self.ilerlet()
        self.assertEqual(adimlar[0]["adim"], "onaylanamadı")
        self.assertIn("CEO", self.ilet.call_args.kwargs["onaylanamadi"])
        self.assertIn("neden kırılımı yok", self.ilet.call_args.kwargs["onaylanamadi"])
        self.assertFalse(any(m["id"] == f"r-{SID}" for m in self.kuyruk()))


class SoruButcesiTesti(Kurulum):
    def test_butce_ceoya_yetmiyorsa_onaylanamadi(self):
        self.ekle(DENETCI_KABUL.replace("1.200", "4.700"))
        adimlar = self.ilerlet()
        self.ceo.assert_not_called()
        self.assertEqual(adimlar[0]["adim"], "onaylanamadı")
        self.assertIn("bütçe", self.ilet.call_args.kwargs["onaylanamadi"])

    def test_butce_duzeltmeye_yetmiyorsa_onaylanamadi(self):
        self.ekle(DENETCI_KABUL.replace("1.200", "2.700"), CEO_RED)
        self.ilerlet()
        self.assertFalse(any(m["id"] == f"r-{SID}" for m in self.kuyruk()))
        self.assertIn("bütçe", self.ilet.call_args.kwargs["onaylanamadi"])


class KapsamTesti(Kurulum):
    def test_bitmis_ve_yeni_sorulara_dokunmaz(self):
        for durum in ("alındı", "iletildi", "onaylanamadı", "yönlendirilemedi"):
            with self.subTest(durum=durum):
                sk.durum_yaz(self.yol, durum)
                self.assertEqual(self.ilerlet(), [])

    def test_karar_bolumu_yoksa_danisman_bekleniyor(self):
        self.assertEqual(self.ilerlet(), [])

    def test_kuru_hicbir_sey_yapmaz(self):
        self.ekle(DENETCI_KABUL, CEO_RED)
        once = self.yol.read_text(encoding="utf-8")
        adimlar = self.ilerlet(kuru=True)
        self.assertEqual(adimlar[0]["adim"], "düzeltme")
        self.assertEqual(self.yol.read_text(encoding="utf-8"), once)
        self.assertEqual(len(self.kuyruk()), 1)
        self.ceo.assert_not_called()
        self.ilet.assert_not_called()


class DagitTesti(Kurulum):
    def test_dagit_ilerletir_ve_acilan_r_maddesini_ayni_turda_kosturur(self):
        self.ekle(DENETCI_KABUL, CEO_RED)
        with mock.patch.object(dagitici, "_kostur") as kostur, \
             mock.patch.object(dagitici, "_ceo_baslat", self.ceo), \
             mock.patch.object(dagitici.soru_kapisi, "ilet", self.ilet):
            sonuc = dagitici.dagit(self.kok, simdi=OGLEN)
        self.assertEqual(sonuc["akis"][0]["adim"], "düzeltme")
        kostur.assert_called_once_with(self.kok, "finans")



class CeoTakilmaTesti(Kurulum):
    """ceo.py karar yazmadan düşerse soru 'CEO'da' kalmasın (süre tavanı + 2 dk pay)."""
    GEC = timedelta(seconds=ayar.CEO_SURESI_SN + 121)

    def test_baslatma_zamani_kayda_yazilir(self):
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        self.assertEqual(sk.bolum_alani(self.yol.read_text(encoding="utf-8"), "## CEO başlatıldı", "zaman"),
                         OGLEN.isoformat(timespec="seconds"))

    def test_sure_icinde_beklenir(self):
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        self.assertEqual(self.ilerlet(simdi=OGLEN + timedelta(minutes=6)), [])
        self.ceo.assert_called_once()

    def test_sure_asilinca_bir_kez_yeniden_baslatilir(self):
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        adimlar = self.ilerlet(simdi=OGLEN + self.GEC)
        self.assertEqual(adimlar[0]["adim"], "ceo")
        self.assertIn("yanıt vermedi", adimlar[0]["sebep"])
        self.assertEqual(self.ceo.call_count, 2)

    def test_ikinci_kez_de_yanit_yoksa_onaylanamadi(self):
        self.ekle(DENETCI_KABUL)
        self.ilerlet()
        self.ilerlet(simdi=OGLEN + self.GEC)
        adimlar = self.ilerlet(simdi=OGLEN + 2 * self.GEC)
        self.assertEqual(adimlar[0]["adim"], "onaylanamadı")
        self.assertIn("CEO", self.ilet.call_args.kwargs["onaylanamadi"])
        self.assertEqual(self.ceo.call_count, 2)

    def test_duzeltmeden_sonraki_ceo_turu_sayaci_sifirdan_baslar(self):
        """Önceki turun başlatmaları yeni Denetçi kabulünden sonrakine sayılmaz."""
        self.ekle(DENETCI_KABUL, "## CEO başlatıldı\n- zaman: 2026-10-12T11:00:00+03:00\n",
                  "## CEO başlatıldı\n- zaman: 2026-10-12T11:10:00+03:00\n", CEO_RED, DENETCI_KABUL)
        sk.durum_yaz(self.yol, "Denetçi: kabul")
        self.ilerlet()
        adimlar = self.ilerlet(simdi=OGLEN + self.GEC)
        self.assertEqual(adimlar[0]["adim"], "ceo")


if __name__ == "__main__":
    unittest.main()
