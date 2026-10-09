"""Defterin kapısı: doğrulama, devralma, kapatma.

Gerçek repo'ya dokunulmaz — her test kendi geçici kökünü kurar.
python3 -m unittest discover -s tests
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import karar_defter  # noqa: E402

TAM = {
    "id": "not-42",
    "kaynak": "telegram",
    "acilis": "2026-09-16T21:04:00+03:00",
    "link": None,
    "baslik": "Meet transkriptlerini Drive'dan al",
    "karar": "Fireflies bırakılıyor, transkript Drive klasöründen çekilecek.",
    "gerekce": None,
    "durum": "acik",
    "kapanis": None,
    "kapanis_zamani": None,
}


def kok_kur():
    """Geçici kök: takimlar/karar-takibi/{cikti,kararlar}."""
    gecici = tempfile.mkdtemp()
    taban = Path(gecici) / "takimlar" / "karar-takibi"
    (taban / "cikti").mkdir(parents=True)
    (taban / "kararlar").mkdir(parents=True)
    return Path(gecici), taban


def cikti_yaz(taban, kayit, ad=None):
    yol = taban / "cikti" / (ad or ("karar-%s.json" % kayit["id"]))
    yol.write_text(json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
    return yol


class DogrulamaTesti(unittest.TestCase):
    def test_tam_kayit_gecer(self):
        tamam, sebep = karar_defter.dogrula(TAM)
        self.assertTrue(tamam, sebep)

    def test_eksik_alan_reddedilir(self):
        for alan in karar_defter.ZORUNLU:
            eksik = {k: v for k, v in TAM.items() if k != alan}
            tamam, sebep = karar_defter.dogrula(eksik)
            self.assertFalse(tamam, "%s eksikken geçti" % alan)
            self.assertIn(alan, sebep)

    def test_acik_olmayan_durum_reddedilir(self):
        """Ajan yalnız açık kayıt üretir; kapatma panelin işi."""
        for durum in ("uygulandi", "vazgecildi", "kapali", ""):
            tamam, sebep = karar_defter.dogrula({**TAM, "durum": durum})
            self.assertFalse(tamam, durum)

    def test_bos_baslik_reddedilir(self):
        tamam, _ = karar_defter.dogrula({**TAM, "baslik": "   "})
        self.assertFalse(tamam)

    def test_onceden_doldurulmus_kapanis_reddedilir(self):
        """M1: `kapanis`/`kapanis_zamani` panele ayrılmış — ajan onları önceden dolduramaz."""
        for alan, deger in (("kapanis", "PR #46"), ("kapanis_zamani", "2026-09-16T10:00:00+03:00")):
            tamam, sebep = karar_defter.dogrula({**TAM, alan: deger})
            self.assertFalse(tamam, alan)
            self.assertIn(alan, sebep)


class HedefAdiTesti(unittest.TestCase):
    def test_ad_acilis_alanindan_kurulur(self):
        kok, _ = kok_kur()
        self.assertEqual(karar_defter.hedef_yolu(kok, TAM).name, "2026-09-16-not-42.json")

    def test_yaniltici_dosya_adi_hedefi_degistirmez(self):
        """Ajan dosyayı 'karar-bambaska.json' diye yazsa bile defterdeki ad
        kaydın kendi `id` ve `acilis` alanlarından kurulur."""
        kok, taban = kok_kur()
        cikti_yaz(taban, TAM, "karar-bambaska-bir-ad.json")
        sonuc = karar_defter.devral(kok)
        self.assertTrue(sonuc[0]["tamam"], sonuc[0]["sebep"])
        self.assertTrue((taban / "kararlar" / "2026-09-16-not-42.json").is_file(),
                        sorted(p.name for p in (taban / "kararlar").iterdir()))


class DevralTesti(unittest.TestCase):
    def test_gecerli_kayit_kararlar_a_tasinir_ciktidan_silinir(self):
        kok, taban = kok_kur()
        kaynak = cikti_yaz(taban, TAM)
        sonuc = karar_defter.devral(kok)
        self.assertEqual(len(sonuc), 1)
        self.assertTrue(sonuc[0]["tamam"], sonuc[0]["sebep"])
        self.assertTrue((taban / "kararlar" / "2026-09-16-not-42.json").is_file())
        self.assertFalse(kaynak.exists(), "cikti'daki kopya kaldı")

    def test_bozuk_kayit_deftere_girmez_ciktida_kalir(self):
        kok, taban = kok_kur()
        kaynak = cikti_yaz(taban, {k: v for k, v in TAM.items() if k != "karar"})
        sonuc = karar_defter.devral(kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertEqual(list((taban / "kararlar").iterdir()), [])
        self.assertTrue(kaynak.exists(), "reddedilen dosya cikti'dan silinmiş")

    def test_var_olan_id_in_uzerine_yazmaz(self):
        """E2'nin çekirdeği: defterdeki kayıt hiçbir koşulda ezilmez."""
        kok, taban = kok_kur()
        hedef = taban / "kararlar" / "2026-09-16-not-42.json"
        eski = {**TAM, "durum": "uygulandi", "kapanis": "PR #46"}
        hedef.write_text(json.dumps(eski, ensure_ascii=False), encoding="utf-8")
        cikti_yaz(taban, TAM)
        sonuc = karar_defter.devral(kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("zaten var", sonuc[0]["sebep"])
        self.assertEqual(json.loads(hedef.read_text(encoding="utf-8")), eski)

    def test_ayni_id_farkli_acilis_reddedilir(self):
        """I1: aynı `id` farklı `acilis` ile farklı bir dosya adına düşer — dosya adı
        denetimi bunu yakalayamaz, `id` deftere iki kez, iki dosya olarak girmemeli."""
        kok, taban = kok_kur()
        cikti_yaz(taban, {**TAM, "acilis": "2026-09-16T09:00:00+03:00"}, "karar-birinci.json")
        sonuc1 = karar_defter.devral(kok)
        self.assertTrue(sonuc1[0]["tamam"], sonuc1[0]["sebep"])
        cikti_yaz(taban, {**TAM, "acilis": "2026-09-17T09:00:00+03:00"}, "karar-ikinci.json")
        sonuc2 = karar_defter.devral(kok)
        self.assertFalse(sonuc2[0]["tamam"])
        self.assertIn("not-42", sonuc2[0]["sebep"])
        self.assertEqual(
            sorted(p.name for p in (taban / "kararlar").iterdir()),
            ["2026-09-16-not-42.json"],
        )

    def test_ayni_id_ayni_acilis_yine_reddedilir(self):
        """Var olan dosya-adı denetimi bozulmadı — aynı id + aynı acilis eskisi gibi düşer."""
        kok, taban = kok_kur()
        cikti_yaz(taban, TAM, "karar-birinci.json")
        karar_defter.devral(kok)
        cikti_yaz(taban, TAM, "karar-ikinci.json")
        sonuc = karar_defter.devral(kok)
        self.assertFalse(sonuc[0]["tamam"])
        self.assertEqual(
            sorted(p.name for p in (taban / "kararlar").iterdir()),
            ["2026-09-16-not-42.json"],
        )

    def test_bozuk_json_devralmayi_dusurmez(self):
        kok, taban = kok_kur()
        (taban / "cikti" / "karar-bozuk.json").write_text("{ bu json değil", encoding="utf-8")
        cikti_yaz(taban, TAM)
        sonuc = karar_defter.devral(kok)
        self.assertEqual(len(sonuc), 2)
        self.assertEqual(sum(1 for s in sonuc if s["tamam"]), 1)

    def test_bos_ciktida_bos_liste(self):
        kok, _ = kok_kur()
        self.assertEqual(karar_defter.devral(kok), [])


class KapatmaTesti(unittest.TestCase):
    def setUp(self):
        self.kok, self.taban = kok_kur()
        cikti_yaz(self.taban, TAM)
        karar_defter.devral(self.kok)
        self.hedef = self.taban / "kararlar" / "2026-09-16-not-42.json"

    def test_kapatma_uc_alani_doldurur(self):
        tamam, sebep = karar_defter.kapat(self.kok, "not-42", "uygulandi", "PR #46")
        self.assertTrue(tamam, sebep)
        kayit = json.loads(self.hedef.read_text(encoding="utf-8"))
        self.assertEqual(kayit["durum"], "uygulandi")
        self.assertEqual(kayit["kapanis"], "PR #46")
        self.assertIsNotNone(kayit["kapanis_zamani"])

    def test_diger_alanlar_degismez(self):
        onceki = json.loads(self.hedef.read_text(encoding="utf-8"))
        karar_defter.kapat(self.kok, "not-42", "vazgecildi", None)
        sonraki = json.loads(self.hedef.read_text(encoding="utf-8"))
        for alan in ("id", "kaynak", "acilis", "link", "baslik", "karar", "gerekce"):
            self.assertEqual(onceki[alan], sonraki[alan], alan)

    def test_zaten_kapali_kayit_ikinci_kez_kapanmaz(self):
        karar_defter.kapat(self.kok, "not-42", "uygulandi", "ilk")
        tamam, sebep = karar_defter.kapat(self.kok, "not-42", "vazgecildi", "ikinci")
        self.assertFalse(tamam)
        self.assertIn("acik", sebep)
        self.assertEqual(json.loads(self.hedef.read_text(encoding="utf-8"))["kapanis"], "ilk")

    def test_bilinmeyen_durum_reddedilir(self):
        tamam, _ = karar_defter.kapat(self.kok, "not-42", "silindi", None)
        self.assertFalse(tamam)

    def test_olmayan_id_reddedilir(self):
        tamam, sebep = karar_defter.kapat(self.kok, "not-999", "uygulandi", None)
        self.assertFalse(tamam)
        self.assertIn("bulunamadı", sebep)

    def test_kapat_yeni_dosya_yaratmaz(self):
        onceki = sorted(p.name for p in (self.taban / "kararlar").iterdir())
        karar_defter.kapat(self.kok, "not-999", "uygulandi", None)
        self.assertEqual(sorted(p.name for p in (self.taban / "kararlar").iterdir()), onceki)


class SorguTesti(unittest.TestCase):
    def test_acik_kararlar_yalniz_acik_olanlari_doner_eskisi_basta(self):
        kok, taban = kok_kur()
        for i, (gun, durum) in enumerate([("10", "acik"), ("12", "uygulandi"), ("11", "acik")]):
            cikti_yaz(taban, {**TAM, "id": "not-%d" % i,
                              "acilis": "2026-09-%sT09:00:00+03:00" % gun}, "karar-not-%d.json" % i)
        karar_defter.devral(kok)
        karar_defter.kapat(kok, "not-1", "uygulandi", None)
        acik = karar_defter.acik_kararlar(kok)
        self.assertEqual([k["id"] for k in acik], ["not-0", "not-2"])


class GuvenlikTesti(unittest.TestCase):
    """Kritik bulgu: bir kayıttaki yol kaçışı ya da geçersiz tarih ne kaydı deftere
    sızdırmalı ne de partideki diğer geçerli kayıtları düşürmeli."""

    def test_id_gecis_denemesi_reddedilir(self):
        tamam, sebep = karar_defter.dogrula({**TAM, "id": "a/../../../tmp/pwn"})
        self.assertFalse(tamam)
        self.assertIn("id", sebep)

    def test_id_icinde_egik_cizgi_reddedilir(self):
        tamam, sebep = karar_defter.dogrula({**TAM, "id": "not/42"})
        self.assertFalse(tamam)
        self.assertIn("id", sebep)

    def test_gecersiz_acilis_reddedilir(self):
        tamam, sebep = karar_defter.dogrula({**TAM, "acilis": "bugün"})
        self.assertFalse(tamam)
        self.assertIn("acilis", sebep)

    def test_bozuk_kayit_partideki_gecerli_kaydi_dusurmez(self):
        """Regresyon: kaçış denemesi içeren kayıt partiyi düşürmemeli — geçerli
        kayıt yine deftere ulaşmalı, bozuk olan cikti'da kalmalı."""
        kok, taban = kok_kur()
        cikti_yaz(taban, {**TAM, "id": "a/../../../tmp/pwn"}, "karar-pwn.json")
        cikti_yaz(taban, {**TAM, "id": "not-1"}, "karar-not-1.json")
        sonuc = karar_defter.devral(kok)
        self.assertEqual(len(sonuc), 2)
        gecti = [s for s in sonuc if s["tamam"]]
        dustu = [s for s in sonuc if not s["tamam"]]
        self.assertEqual(len(gecti), 1)
        self.assertEqual(len(dustu), 1)
        self.assertTrue((taban / "kararlar" / "2026-09-16-not-1.json").is_file())
        self.assertTrue((taban / "cikti" / "karar-pwn.json").is_file())

    def test_hicbir_dosya_kararlar_disina_yaratilmaz(self):
        kok, taban = kok_kur()
        cikti_yaz(taban, {**TAM, "id": "a/../../../tmp/pwn"}, "karar-pwn.json")
        cikti_yaz(taban, {**TAM, "id": "not-1"}, "karar-not-1.json")
        karar_defter.devral(kok)
        self.assertEqual(
            sorted(p.name for p in (taban / "kararlar").iterdir()),
            ["2026-09-16-not-1.json"],
        )
        disari = Path(tempfile.gettempdir()) / "pwn.json"
        self.assertFalse(disari.exists())

    def test_yapisal_denetim_desen_gevsetilse_de_tutar(self):
        """Katman 2 tek başına: KIMLIK_DESENI gevşetilse bile hedef defter dışına çıkamaz.

        İki katman istenmesinin sebebi katman 1'in ileride gevşetilebilmesi. Bu test
        katman 2'yi yalıtarak sınar — silinirse süit kırmızıya döner.
        """
        kok, taban = kok_kur()
        kayit = {**TAM, "id": "a/../../../tmp/pwn"}
        cikti_yaz(taban, kayit, "karar-kotu.json")
        eski = karar_defter.KIMLIK_DESENI
        try:
            karar_defter.KIMLIK_DESENI = re.compile(r"^.{1,64}$")   # katman 1 devre dışı
            sonuc = karar_defter.devral(kok)
        finally:
            karar_defter.KIMLIK_DESENI = eski
        self.assertFalse(sonuc[0]["tamam"])
        self.assertIn("defter dışına", sonuc[0]["sebep"])
        self.assertEqual(list((taban / "kararlar").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
