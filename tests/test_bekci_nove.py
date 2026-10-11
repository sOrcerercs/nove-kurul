"""Bekçinin Nove değişiklikleri (NOVE-KURULUM.md §4, sirket/DENETCI.md). Ağ yok, para harcamaz.

- Ön kontrole telefon ve TC kimlik no desenleri (KVKK)
- Yönerge: Nove Group Yönetim Kurulu'nun bağımsız denetçisi
- Üçlü kontrol: kaynak · hesap · tutarlılık → gecti | kaldi | uygulanmaz

python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import bekci  # noqa: E402

FIKSTUR = KOK / "tests" / "fikstur" / "bekci"
GECTI = {"kaynak": "gecti", "hesap": "gecti", "tutarlilik": "gecti"}


def _cikti(karar):
    return {"output": [{"content": [{"text": json.dumps(karar)}]}]}


class TelefonTesti(unittest.TestCase):
    def test_turk_cep_telefonu_bicimleri_yakalanir(self):
        for metin in ("0532 123 45 67", "+90 532 123 45 67", "05321234567", "(0532) 123-45-67",
                      "532 123 45 67", "0090 532 123 4567"):
            with self.subTest(metin=metin):
                self.assertIn("telefon numarası", bekci.on_kontrol(f"hasta: {metin} aradı"))

    def test_sabit_hat_yakalanir(self):
        for metin in ("0212 345 67 89", "(0312) 345 67 89", "+90 216 345 67 89"):
            with self.subTest(metin=metin):
                self.assertIn("telefon numarası", bekci.on_kontrol(f"klinik: {metin}"))

    def test_rapor_sayilari_telefon_sayilmaz(self):
        for metin in ("146/146 sayfa", "1227 cross-reference", "2026-09-15T09:00:00+03:00",
                      "412 + 388 = 800", "gelir 5.320.000 TL", "maliyet: 0.412 USD · tur: 9",
                      "Q3: 1.250.000 TL, n=412"):
            with self.subTest(metin=metin):
                self.assertEqual(bekci.on_kontrol(metin), [])


class TcKimlikTesti(unittest.TestCase):
    def test_on_bir_haneli_tc_yakalanir(self):
        self.assertIn("TC kimlik numarası", bekci.on_kontrol("TC: 12345678950 olan hasta"))

    def test_sifirla_baslayan_on_bir_hane_tc_sayilmaz(self):
        """TC sıfırla başlamaz; 05321234567 telefondur."""
        self.assertNotIn("TC kimlik numarası", bekci.on_kontrol("05321234567"))

    def test_daha_uzun_sayinin_parcasi_tc_sayilmaz(self):
        self.assertEqual(bekci.on_kontrol("sipariş no 1234567890123"), [])


class FiksturTesti(unittest.TestCase):
    def test_telefon_sizmis_on_kontrolde_yakalanir(self):
        metin = (FIKSTUR / "telefon-sizmis.md").read_text(encoding="utf-8")
        self.assertIn("telefon numarası", bekci.on_kontrol(metin))

    def test_hesap_tutmuyor_on_kontrolden_gecer_llmye_gider(self):
        """Hesap hatası desenle yakalanmaz; Denetçi'nin LLM katmanının işi."""
        metin = (FIKSTUR / "hesap-tutmuyor.md").read_text(encoding="utf-8")
        self.assertTrue(metin.strip())
        self.assertEqual(bekci.on_kontrol(metin), [])

    def test_temiz_fikstur_hala_temiz(self):
        self.assertEqual(bekci.on_kontrol((FIKSTUR / "temiz.md").read_text(encoding="utf-8")), [])


class YonergeTesti(unittest.TestCase):
    def test_nove_kurulu_denetcisi_ve_uclu_kontrol(self):
        istem = bekci._istem("anayasa", "kurallar", "kayıt")
        self.assertIn("Nove Group Yönetim Kurulu'nun bağımsız denetçisi", istem)
        self.assertNotIn("içerik şirketi", istem)
        for ad in ("kaynak", "hesap", "tutarlilik"):
            self.assertIn(ad, istem)

    def test_sema_kontrol_alanini_ister(self):
        self.assertIn("kontrol", bekci.YANIT_SEMASI["required"])
        kontrol = bekci.YANIT_SEMASI["properties"]["kontrol"]
        self.assertEqual(sorted(kontrol["required"]), ["hesap", "kaynak", "tutarlilik"])
        self.assertEqual(kontrol["properties"]["hesap"]["enum"], ["gecti", "kaldi", "uygulanmaz"])

    def test_sema_disi_yollara_giden_json_talimati_kontrolu_soyler(self):
        self.assertIn("kontrol", bekci.JSON_TALIMATI)


class UcluKontrolTesti(unittest.TestCase):
    def test_kontrol_ayristirilir(self):
        karar = bekci.yaniti_ayristir(_cikti({"karar": "kabul", "gerekce": "temiz",
                                              "ihlal_edilen_kural": None, "kontrol": GECTI}))
        self.assertEqual(karar["kontrol"], GECTI)

    def test_kontrol_yoksa_karar_kalir_kontrol_none(self):
        karar = bekci.yaniti_ayristir(_cikti({"karar": "kabul", "gerekce": "temiz",
                                              "ihlal_edilen_kural": None}))
        self.assertEqual(karar["karar"], "kabul")
        self.assertIsNone(karar["kontrol"])

    def test_gecersiz_kontrol_degeri_none_sayilir(self):
        karar = bekci.yaniti_ayristir(_cikti({"karar": "kabul", "gerekce": "x", "ihlal_edilen_kural": None,
                                              "kontrol": {**GECTI, "hesap": "belki"}}))
        self.assertIsNone(karar["kontrol"])

    def test_bir_kontrol_kaldiysa_kabul_red_olur(self):
        karar = bekci.kontrol_uygula({"karar": "kabul", "gerekce": "genel olarak iyi",
                                      "ihlal_edilen_kural": None, "kontrol": {**GECTI, "hesap": "kaldi"}})
        self.assertEqual(karar["karar"], "red")
        self.assertIn("hesap", karar["gerekce"])
        self.assertEqual(karar["ihlal_edilen_kural"], "üçlü kontrol: hesap")

    def test_hepsi_gectiyse_kabul_kalir(self):
        karar = {"karar": "kabul", "gerekce": "ok", "ihlal_edilen_kural": None, "kontrol": GECTI}
        self.assertEqual(bekci.kontrol_uygula(karar), karar)

    def test_kontrolu_kalan_red_madde34_ayiklamasiyla_kabule_donmez(self):
        """Gerekçe 'tavan' dese bile kaldi varsa red kalır: ayıklama önce, kontrol sonra."""
        red = {"karar": "red", "gerekce": "tavan aşıldı; hesap tutmuyor", "ihlal_edilen_kural": "4",
               "kontrol": {**GECTI, "hesap": "kaldi"}}
        sonuc = bekci.kontrol_uygula(bekci.gecersiz_gerekceyi_ayikla(red))
        self.assertEqual(sonuc["karar"], "red")


class DenetleKayitTesti(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "takimlar" / "finans" / "kosu").mkdir(parents=True)
        self.kosu = self.kok / "takimlar" / "finans" / "kosu" / "2026-10-12-1000.md"

    def test_kontrol_kosu_kaydina_ve_telemetriye_yazilir(self):
        self.kosu.write_text("# Koşu\nQ3 sapması %4 (n=412, veri/q3.csv)\n", encoding="utf-8")
        llm = {"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None,
               "kontrol": {**GECTI, "tutarlilik": "uygulanmaz"}}
        with mock.patch.object(bekci, "llm_karari", return_value=llm):
            bekci.denetle(self.kok, "finans", self.kosu)
        kayit = self.kosu.read_text(encoding="utf-8")
        self.assertIn("- kontrol: kaynak gecti · hesap gecti · tutarlilik uygulanmaz", kayit)
        satir = json.loads((self.kok / "takimlar" / "bekci-telemetri.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(satir["kontrol"]["tutarlilik"], "uygulanmaz")

    def test_llm_kabul_ama_kontrol_kaldi_ise_denetle_red_doner(self):
        self.kosu.write_text("# Koşu\n412 + 388 = 900\n", encoding="utf-8")
        llm = {"karar": "kabul", "gerekce": "iyi", "ihlal_edilen_kural": None,
               "kontrol": {**GECTI, "hesap": "kaldi"}}
        with mock.patch.object(bekci, "llm_karari", return_value=llm):
            karar = bekci.denetle(self.kok, "finans", self.kosu)
        self.assertEqual(karar["karar"], "red")

    def test_on_kontrol_redinde_kontrol_yapilmadi(self):
        self.kosu.write_text("# Koşu\nhasta 0532 123 45 67 aradı\n", encoding="utf-8")
        with mock.patch.object(bekci, "llm_karari") as llm:
            karar = bekci.denetle(self.kok, "finans", self.kosu)
        llm.assert_not_called()
        self.assertEqual(karar["karar"], "red")
        self.assertIsNone(karar["kontrol"])
        self.assertIn("- kontrol: yapılmadı", self.kosu.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
