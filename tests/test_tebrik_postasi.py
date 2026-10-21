"""Tebrik sürücüsünün testleri — geçici kök, sahte indirme ve gönderim, gerçek modüller.

Adlar uydurmadır. python3 -m unittest discover -s tests
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl
from PIL import Image

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import tebrik_postasi as tp  # noqa: E402

IST = ZoneInfo("Europe/Istanbul")
BASLIK = ("Ad Soyad", "Ünvan", "Doğum günü", "İşe giriş tarihi")
ISTISNALI = "# ANAYASA\n\n## İstisna — tebrik postası\nİç alıcıya günlük tebrik.\n"
ISTISNASIZ = "# ANAYASA\n\n## Madde 1\nDış iletişim yok.\n"
ORTAM = {"TEBRIK_ALICI": "alici@nove.group", "TEBRIK_SMTP_KULLANICI": "gonderen@nove.group"}

# 20.10.2026 Salı: Çağla'nın doğum günü; Ömer'inki dün (19.10).
SATIRLAR = [
    ("Çağla Işıkoğlu", "Uzman", "20.10", None),
    ("Ömer Şükrü Güneş", "Müdür", "19.10", None),
    ("İpek Yağmur Öztürk", "Şef", "05.03", None),
]
TUM_ADLAR = [s[0] for s in SATIRLAR] + ["Deniz Ağaoğlu", "Gökay Çelik", "Ilgın Şen"]


def _an(y, a, g, s=8, d=55):
    return datetime(y, a, g, s, d, tzinfo=IST)


def _sablon(klasor, ad):
    Image.new("RGB", (540, 675), "#0b1b3f").save(klasor / f"{ad}.png")
    alan = {"anahtar": "ad", "yazi_tipi": "Poppins-Bold.ttf", "boyut": 40, "en_kucuk": 20,
            "renk": "#FFFFFF", "kutu": [40, 300, 460, 100], "hiza": "orta", "satir_max": 2}
    (klasor / f"{ad}.json").write_text(json.dumps({"gorsel": f"{ad}.png", "alanlar": [alan]}),
                                       encoding="utf-8")


def _sessiz(fn, *a, **k):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def _govde(mesaj):
    return mesaj.get_body(("plain",)).get_content()


def _ekler(mesaj):
    return [p.get_filename() for p in mesaj.iter_attachments()]


class SurucuTestleri(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.kok = Path(self._t.name)
        sablonlar = self.kok / "tebrik" / "sablonlar"
        sablonlar.mkdir(parents=True)
        for ad in ("dogum_gunu", "hos_geldin"):
            _sablon(sablonlar, ad)
        (self.kok / "tebrik" / "yazi-tipleri").symlink_to(KOK / "tebrik" / "yazi-tipleri")
        (self.kok / "tebrik" / "bayramlar.json").write_text("[]", encoding="utf-8")
        self.anayasa(ISTISNALI)
        self.satirlar = list(SATIRLAR)
        self.gonderilen = []
        self.gonder_hatasi = None

    def anayasa(self, metin):
        (self.kok / "ANAYASA.md").write_text(metin, encoding="utf-8")

    def indir(self, ortam, hedef):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(BASLIK)
        for s in self.satirlar:
            ws.append(s)
        hedef.parent.mkdir(parents=True, exist_ok=True)
        wb.save(hedef)
        return hedef

    def gonder(self, mesaj, ortam):
        if self.gonder_hatasi:
            hata, self.gonder_hatasi = self.gonder_hatasi, None
            raise hata
        self.gonderilen.append(mesaj)

    def kos(self, simdi=None, kuru=False, indir=None):
        return _sessiz(tp.kos, simdi or _an(2026, 10, 20), dict(ORTAM), self.kok, kuru=kuru,
                      indir=indir or self.indir, gonder=self.gonder)

    def kayit(self, gun="2026-10-20"):
        return json.loads((self.kok / "sirket-log" / "tebrik" / f"{gun}.json").read_text(encoding="utf-8"))

    def dun_kosuldu(self, gun="2026-10-19", durum="bos"):
        klasor = self.kok / "sirket-log" / "tebrik"
        klasor.mkdir(parents=True, exist_ok=True)
        (klasor / f"{gun}.json").write_text(json.dumps({"gun": gun, "durum": durum}), encoding="utf-8")

    # --- gün ---------------------------------------------------------------

    def test_istanbul_gunu_utc_gecesi(self):
        self.assertEqual(tp.istanbul_gunu(datetime(2026, 10, 19, 21, 30, tzinfo=timezone.utc)),
                         date(2026, 10, 20))

    # --- tek gönderim -------------------------------------------------------

    def test_ayni_gun_ikinci_kosu_gondermez(self):
        self.assertEqual(self.kos(), 0)
        self.assertEqual(self.kos(_an(2026, 10, 20, 10, 0)), 0)
        self.assertEqual(len(self.gonderilen), 1)
        k = self.kayit()
        self.assertEqual(k["durum"], "gonderildi")
        self.assertEqual(k["tebrik_sayisi"], 1)
        self.assertEqual(k["adlar"], ["Çağla Işıkoğlu"])
        self.assertEqual(_ekler(self.gonderilen[0]), ["2026-10-20-dogum-gunu-cagla-isikoglu.png"])

    def test_smtp_hatasi_sonra_yeniden_dener(self):
        self.gonder_hatasi = RuntimeError("SMTP: OSError")
        self.assertEqual(self.kos(), 1)
        self.assertEqual(self.kayit()["durum"], "hata")
        self.assertEqual(self.gonderilen, [])
        self.assertEqual(self.kos(_an(2026, 10, 20, 9, 5)), 0)
        self.assertEqual(len(self.gonderilen), 1)
        self.assertEqual(self.kayit()["durum"], "gonderildi")

    def test_kuru_kaydi_gonderimi_engellemez(self):
        self.assertEqual(self.kos(kuru=True), 0)
        self.assertEqual(self.kayit("2026-10-20.kuru")["durum"], "kuru")
        self.assertFalse((self.kok / "sirket-log" / "tebrik" / "2026-10-20.json").exists())
        self.assertEqual(self.kos(), 0)
        self.assertEqual(len(self.gonderilen), 1)

    # --- ANAYASA kapısı ve kuru koşu ----------------------------------------

    def test_istisna_yoksa_rc3_gonderim_yok(self):
        self.anayasa(ISTISNASIZ)
        self.assertEqual(self.kos(), 3)
        self.assertEqual(self.gonderilen, [])

    def test_alici_gecersizse_rc3(self):
        rc = _sessiz(tp.kos, _an(2026, 10, 20), {"TEBRIK_ALICI": "biri@ornek.com"}, self.kok,
                    indir=self.indir, gonder=self.gonder)
        self.assertEqual(rc, 3)
        self.assertEqual(self.gonderilen, [])

    def test_kuru_istisnasiz_calisir(self):
        self.anayasa(ISTISNASIZ)
        self.assertEqual(self.kos(kuru=True), 0)
        self.assertEqual(self.gonderilen, [])
        klasor = self.kok / "sirket-log" / "tebrik" / "2026-10-20"
        self.assertTrue((klasor / "2026-10-20-dogum-gunu-cagla-isikoglu.png").exists())
        eml = list(klasor.glob("*.eml"))
        self.assertEqual(len(eml), 1)
        self.assertIn("Çağla Işıkoğlu", self._eml_metni(eml[0]))
        self.assertEqual(self.kayit("2026-10-20.kuru")["durum"], "kuru")

    def test_kuru_gercek_kaydi_ezmez(self):
        self.dun_kosuldu("2026-10-20", durum="hata")
        self.assertEqual(self.kos(kuru=True), 0)
        self.assertEqual(self.kayit()["durum"], "hata")
        self.assertFalse((self.kok / "sirket-log" / "tebrik" / "ozet.json").exists())

    def test_kuru_kaydi_onceki_kayit_sayilmaz(self):
        # Yalnız kuru koşulmuş geçmiş → gerçek ilk koşu (R11): kaçan notu yok.
        self.assertEqual(self.kos(_an(2026, 10, 18), kuru=True), 0)
        self.assertEqual(self.kos(_an(2026, 10, 19), kuru=True), 0)
        self.assertEqual(self.kos(), 0)
        self.assertNotIn("Dün kaçan", _govde(self.gonderilen[0]))

    def test_dunun_kuru_kaydi_dunu_kosulmus_saymaz(self):
        self.dun_kosuldu("2026-10-18")
        self.assertEqual(self.kos(_an(2026, 10, 19), kuru=True), 0)
        self.kos()
        self.assertIn("Dün kaçan tebrikler: Ömer Şükrü Güneş", _govde(self.gonderilen[0]))

    def _eml_metni(self, yol):
        from email import policy
        from email.parser import BytesParser
        with yol.open("rb") as f:
            return _govde(BytesParser(policy=policy.default).parse(f))

    # --- boş gün -------------------------------------------------------------

    def test_bos_gun_mail_yok_kayit_bos(self):
        self.satirlar = [("İpek Yağmur Öztürk", "Şef", "05.03", None)]
        self.assertEqual(self.kos(), 0)
        self.assertEqual(self.gonderilen, [])
        self.assertEqual(self.kayit()["durum"], "bos")

    # --- notlar --------------------------------------------------------------

    def test_dun_kacan_not(self):
        self.dun_kosuldu("2026-10-18")  # önceki bir koşu var, dünün kaydı yok
        self.assertEqual(self.kos(), 0)
        govde = _govde(self.gonderilen[0])
        self.assertIn("Dün kaçan tebrikler: Ömer Şükrü Güneş", govde)
        self.assertEqual(len(_ekler(self.gonderilen[0])), 1)
        self.assertNotIn("omer", " ".join(_ekler(self.gonderilen[0])))

    def test_dun_hata_ya_da_kuru_ise_kacan_sayilir(self):
        for durum in ("hata", "kuru"):
            with self.subTest(durum=durum):
                self.gonderilen = []
                (self.kok / "sirket-log" / "tebrik" / "2026-10-20.json").unlink(missing_ok=True)
                self.dun_kosuldu(durum=durum)
                self.kos()
                self.assertIn("Dün kaçan tebrikler: Ömer Şükrü Güneş", _govde(self.gonderilen[0]))

    def test_ilk_kosuda_kacan_notu_yok(self):
        self.kos()
        self.assertNotIn("Dün kaçan", _govde(self.gonderilen[0]))

    def test_dun_kosulduysa_kacan_notu_yok(self):
        self.dun_kosuldu()
        self.kos()
        self.assertNotIn("Dün kaçan", _govde(self.gonderilen[0]))

    def test_gec_gonderim_notu(self):
        self.dun_kosuldu()
        self.kos(_an(2026, 10, 20, 14, 0))
        self.assertIn("Geç gönderildi (14:00)", _govde(self.gonderilen[0]))
        self.assertTrue(self.kayit()["gec"])

    def test_zamaninda_gec_notu_yok(self):
        self.dun_kosuldu()
        self.kos(_an(2026, 10, 20, 9, 14))
        self.assertNotIn("Geç gönderildi", _govde(self.gonderilen[0]))
        self.assertFalse(self.kayit()["gec"])

    def test_ayin_ilk_is_gunu_tum_eksikler(self):
        # 1 Kasım 2026 Pazar → 2 Kasım Pazartesi ayın ilk iş günü.
        self.satirlar = [
            ("Deniz Ağaoğlu", "Analist", "31.02", None),          # tarih okunamaz
            ("Gökay Çelik", "", "07.07", date(2026, 11, 2)),      # 2 Kasım hoş geldin, ünvan yok
            ("Ilgın Şen", "", "08.08", date(2026, 11, 3)),        # 3 Kasım hoş geldin, ünvan yok
        ]
        self.dun_kosuldu("2026-11-01")
        self.kos(_an(2026, 11, 2))
        govde = _govde(self.gonderilen[0])
        self.assertIn("Deniz Ağaoğlu — doğum günü okunamadı", govde)
        self.assertIn("Gökay Çelik — ünvan yok", govde)

        self.kos(_an(2026, 11, 3))
        govde = _govde(self.gonderilen[1])
        self.assertNotIn("Deniz Ağaoğlu", govde)
        self.assertIn("Ilgın Şen — ünvan yok", govde)

    def test_sablon_yoksa_not_ve_metinli_tebrik(self):
        (self.kok / "tebrik" / "sablonlar" / "dogum_gunu.json").unlink()
        self.dun_kosuldu()
        self.assertEqual(self.kos(), 0)
        govde = _govde(self.gonderilen[0])
        self.assertIn("şablon yok: dogum_gunu", govde)
        self.assertIn("Çağla Işıkoğlu", govde)
        self.assertEqual(_ekler(self.gonderilen[0]), [])

    def test_aralikta_gelecek_yil_bayram_yoksa_hatirlatma(self):
        self.satirlar = [("İpek Yağmur Öztürk", "Şef", "05.03", None)]
        # 1 Aralık 2026 Salı: aralığın ilk iş günü → hatırlatma; 2 Aralık → yok.
        self.dun_kosuldu("2026-11-30")
        self.kos(_an(2026, 12, 1))
        self.assertIn("Gelecek yılın bayram tarihleri takvimde yok", _govde(self.gonderilen[0]))
        self.assertEqual(self.kos(_an(2026, 12, 2)), 0)
        self.assertEqual(len(self.gonderilen), 1)
        self.assertEqual(self.kayit("2026-12-02")["durum"], "bos")

    def test_aralik_ilk_is_gunu_bayram_varsa_hatirlatma_yok(self):
        self.satirlar = [("İpek Yağmur Öztürk", "Şef", "05.03", None)]
        (self.kok / "tebrik" / "bayramlar.json").write_text(json.dumps([
            {"ad": "Yılbaşı", "baslangic": "2027-01-01", "sablon": "yilbasi", "tr": "a", "en": "b"}]),
            encoding="utf-8")
        self.dun_kosuldu("2026-11-30")
        self.assertEqual(self.kos(_an(2026, 12, 1)), 0)
        self.assertEqual(self.gonderilen, [])
        self.assertEqual(self.kayit("2026-12-01")["durum"], "bos")

    def test_bozuk_bayramlar_rc1_kayit_hata(self):
        (self.kok / "tebrik" / "bayramlar.json").write_text("[{bozuk", encoding="utf-8")
        hata = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(hata):
            rc = tp.kos(_an(2026, 10, 20), dict(ORTAM), self.kok, indir=self.indir, gonder=self.gonder)
        self.assertEqual(rc, 1)
        self.assertEqual(len(self.gonderilen), 1)  # hiçbir tebrik sessizce kaybolmaz
        self.assertIn("Tebrikler hazırlanamadı (JSONDecodeError)", _govde(self.gonderilen[0]))
        self.assertEqual(_ekler(self.gonderilen[0]), [])
        self.assertEqual(self.kayit()["durum"], "hata")
        self.assertIn("JSONDecodeError", hata.getvalue())
        self.assertNotIn("Traceback", hata.getvalue())

    def test_bayram_alani_eksik_bildirim(self):
        (self.kok / "tebrik" / "bayramlar.json").write_text(json.dumps([
            {"ad": "Cumhuriyet Bayramı", "baslangic": "2026-10-20"}]), encoding="utf-8")
        self.assertEqual(self.kos(), 1)
        self.assertEqual(len(self.gonderilen), 1)
        self.assertIn("Tebrikler hazırlanamadı (KeyError)", _govde(self.gonderilen[0]))
        self.assertEqual(self.kayit()["durum"], "hata")

    def test_bozuk_bayramlar_kuru_mail_yok(self):
        (self.kok / "tebrik" / "bayramlar.json").write_text("[{bozuk", encoding="utf-8")
        self.assertEqual(self.kos(kuru=True), 1)
        self.assertEqual(self.gonderilen, [])
        self.assertEqual(list((self.kok / "sirket-log" / "tebrik").glob("**/*.eml")), [])

    # --- aynı ad ------------------------------------------------------------

    def test_ayni_adli_iki_kisi_iki_ek(self):
        self.satirlar = [("Çağla Işıkoğlu", "Uzman", "20.10", None),
                         ("Çağla Işıkoğlu", "Şef", "20.10", date(2020, 3, 2))]  # farklı kişi
        self.dun_kosuldu()
        self.assertEqual(self.kos(), 0)
        self.assertEqual(_ekler(self.gonderilen[0]), ["2026-10-20-dogum-gunu-cagla-isikoglu.png",
                                                      "2026-10-20-dogum-gunu-cagla-isikoglu-2.png"])
        self.assertEqual(self.kayit()["tebrik_sayisi"], 2)

    # --- kilit -------------------------------------------------------------

    def _kilit(self):
        yol = self.kok / "sirket-log" / "tebrik" / ".kilit"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("", encoding="utf-8")
        return yol

    def test_kilit_doluysa_gondermez(self):
        yol = self._kilit()
        self.assertEqual(self.kos(), 0)
        self.assertEqual(self.gonderilen, [])
        self.assertTrue(yol.exists())  # başkasının kilidine dokunmaz

    def test_bayat_kilit_devralinir_ve_birakilir(self):
        yol = self._kilit()
        eski = yol.stat().st_mtime - 31 * 60
        os.utime(yol, (eski, eski))
        self.assertEqual(self.kos(), 0)
        self.assertEqual(len(self.gonderilen), 1)
        self.assertFalse(yol.exists())

    # --- özet --------------------------------------------------------------

    def test_ozet_ad_tasimaz(self):
        self.kos()
        metin = (self.kok / "sirket-log" / "tebrik" / "ozet.json").read_text(encoding="utf-8")
        for ad in TUM_ADLAR:
            self.assertNotIn(ad, metin)
        ozet = json.loads(metin)
        self.assertNotIn("adlar", ozet)
        self.assertEqual(ozet["son_gonderim"], "2026-10-20")
        self.assertEqual(ozet["tebrik_sayisi"], 1)

    # --- Drive hatası ------------------------------------------------------

    def test_drive_hatasi_rc1_ve_bildirim(self):
        def bozuk(ortam, hedef):
            raise RuntimeError("Drive okunamadı: HttpError")
        self.assertEqual(self.kos(indir=bozuk), 1)
        self.assertEqual(len(self.gonderilen), 1)
        self.assertIn("okunamadı", _govde(self.gonderilen[0]))
        self.assertEqual(_ekler(self.gonderilen[0]), [])
        self.assertEqual(self.kayit()["durum"], "hata")

    def test_eksik_sutun_mesaji_gosterilir(self):
        def eksik(ortam, hedef):
            wb = openpyxl.Workbook()
            wb.active.append(("Ad Soyad", "Doğum günü", "İşe giriş tarihi"))
            hedef.parent.mkdir(parents=True, exist_ok=True)
            wb.save(hedef)
            return hedef
        self.assertEqual(self.kos(indir=eksik), 1)
        self.assertIn("eksik sütun: Ünvan", _govde(self.gonderilen[0]))

    def test_diger_hata_yalniz_tur_adi(self):
        def bozuk(ortam, hedef):
            raise ValueError("gizli ayrıntı")
        self.assertEqual(self.kos(indir=bozuk), 1)
        govde = _govde(self.gonderilen[0])
        self.assertIn("(ValueError)", govde)
        self.assertNotIn("gizli", govde)

    # --- komut satırı -------------------------------------------------------

    def test_gun_kurusuz_rc2(self):
        self.assertEqual(_sessiz(tp.main, ["--gun", "2026-10-20"]), 2)


if __name__ == "__main__":
    unittest.main()
