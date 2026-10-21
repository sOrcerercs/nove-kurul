import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import tebrik_gorsel as g  # noqa: E402

YAZI = KOK / "tebrik" / "yazi-tipleri"
TR_HARF = "ÇĞİIÖŞÜçğıiöşü"


def _alan(anahtar, kutu, yazi_tipi="Poppins-Bold.ttf", boyut=60, en_kucuk=30,
          satir_max=1, metin=None):
    a = {"anahtar": anahtar, "yazi_tipi": yazi_tipi, "boyut": boyut,
         "en_kucuk": en_kucuk, "renk": "#FFFFFF", "kutu": kutu,
         "hiza": "orta", "satir_max": satir_max}
    if metin is not None:
        a["metin"] = metin
    return a


class GorselTestleri(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = Path(self._t.name)
        self.addCleanup(self._t.cleanup)
        self.sablonlar = self.tmp / "sablonlar"
        self.sablonlar.mkdir()

    def _sablon(self, ad, alanlar):
        Image.new("RGB", (1080, 1350), "#0b1b3f").save(self.sablonlar / f"{ad}.png")
        (self.sablonlar / f"{ad}.json").write_text(json.dumps(
            {"gorsel": f"{ad}.png", "alanlar": alanlar, "logo": [40, 40, 200]}),
            encoding="utf-8")

    def _uret(self, tebrik, cikis=None):
        cikis = cikis or self.tmp / "cikti.png"
        cizilen = []
        gercek = ImageDraw.ImageDraw.text

        def kayit(self_, xy, metin, *a, **k):
            cizilen.append(metin)
            return gercek(self_, xy, metin, *a, **k)

        with mock.patch.object(ImageDraw.ImageDraw, "text", kayit):
            sonuc = g.gorsel_uret(tebrik, self.sablonlar, cikis, YAZI)
        return sonuc, cizilen

    def test_turkce_harfler_basilir(self):
        for dosya in ("GreatVibes-Regular.ttf", "Poppins-Bold.ttf", "Poppins-Regular.ttf"):
            font = ImageFont.truetype(str(YAZI / dosya), 60)
            tofu = bytes(font.getmask("\U0010FFFD"))
            for h in TR_HARF:
                maske = font.getmask(h)
                self.assertIsNotNone(maske.getbbox(), (dosya, h))
                self.assertNotEqual(bytes(maske), tofu, (dosya, h))

    def test_ad_yazildigi_gibi_basilir(self):
        self._sablon("dogum_gunu", [_alan("ad", [90, 600, 900, 150])])
        tebrik = {"tur": "dogum_gunu", "ad": "  ebru   yıldız ", "unvan": "", "bayram": None}
        sonuc, cizilen = self._uret(tebrik)
        self.assertEqual(sonuc, self.tmp / "cikti.png")
        self.assertTrue(sonuc.exists())
        with Image.open(sonuc) as im:
            self.assertEqual(im.size, (1080, 1350))
        self.assertEqual(cizilen, ["ebru yıldız"])

    def test_uzun_ad_iki_satir(self):
        self._sablon("dogum_gunu", [_alan("ad", [90, 600, 500, 200], satir_max=2)])
        ad = "Ayşegül Nur Karaoğlu Büyükşahin Demirtaş"
        _, cizilen = self._uret({"tur": "dogum_gunu", "ad": ad, "unvan": "", "bayram": None})
        self.assertEqual(len(cizilen), 2)
        self.assertEqual(" ".join(cizilen), ad)

    def test_sigmayan_ad_none(self):
        self._sablon("dogum_gunu", [_alan("ad", [90, 600, 500, 200], satir_max=2)])
        cikis = self.tmp / "yok.png"
        sonuc, _ = self._uret({"tur": "dogum_gunu", "ad": "A" * 60, "unvan": "", "bayram": None}, cikis)
        self.assertIsNone(sonuc)
        self.assertFalse(cikis.exists())

    def test_hos_geldin_unvan_basilir(self):
        self._sablon("hos_geldin", [
            _alan("baslik", [90, 200, 900, 120], metin="Welcome to the Team!"),
            _alan("ad", [90, 600, 900, 150]),
            _alan("unvan", [90, 780, 900, 80], yazi_tipi="Poppins-Regular.ttf", boyut=40, en_kucuk=24),
        ])
        _, cizilen = self._uret({"tur": "hos_geldin", "ad": "Ömer Şükrü Güneş",
                                 "unvan": "Kalite Uzmanı", "bayram": None})
        self.assertEqual(cizilen, ["Welcome to the Team!", "Ömer Şükrü Güneş", "Kalite Uzmanı"])

    def test_bayram_ad_tasimaz(self):
        self._sablon("ramazan", [
            _alan("tr", [90, 300, 900, 120], metin="yanlış"),
            _alan("en", [90, 500, 900, 120]),
        ])
        tebrik = {"tur": "bayram", "ad": "Çağla Işıkoğlu", "unvan": "",
                  "bayram": {"ad": "Ramazan Bayramı", "baslangic": "x",
                             "tr": "Bayramınız kutlu olsun.", "en": "Happy holiday.",
                             "sablon": "ramazan"}}
        _, cizilen = self._uret(tebrik)
        self.assertEqual(cizilen, ["Bayramınız kutlu olsun.", "Happy holiday."])
        self.assertNotIn("Çağla Işıkoğlu", cizilen)

    def test_sablon_yoksa_dosya_bulunamadi(self):
        with self.assertRaises(FileNotFoundError):
            g.gorsel_uret({"tur": "hos_geldin", "ad": "A", "unvan": "", "bayram": None},
                          self.sablonlar, self.tmp / "c.png", YAZI)

    def test_logo_dosyasi_yoksa_dosya_bulunamadi(self):
        self._sablon("dogum_gunu", [_alan("ad", [90, 300, 900, 120])])
        tebrik = {"tur": "dogum_gunu", "ad": "Çağla Işıkoğlu", "unvan": "", "bayram": None}
        with mock.patch.object(g, "LOGO_DOSYASI", self.tmp / "yok.png"):
            with self.assertRaises(FileNotFoundError) as c:
                g.gorsel_uret(tebrik, self.sablonlar, self.tmp / "c.png", YAZI)
        self.assertEqual(str(c.exception), "logo yok")
        self.assertFalse((self.tmp / "c.png").exists())

    def test_yazi_sigdir_tek_satir_kucultur(self):
        yol = YAZI / "Poppins-Bold.ttf"
        satirlar, boyut = g.yazi_sigdir("Çağla Işıkoğlu", yol, 120, 30, 400, 100, 1)
        self.assertEqual(satirlar, ["Çağla Işıkoğlu"])
        self.assertLess(boyut, 120)
        self.assertEqual(boyut % 2, 0)

    def test_logo_seffaf(self):
        kaynak = self.tmp / "kaynak.png"
        im = Image.new("RGB", (400, 400), "black")
        ImageDraw.Draw(im).rectangle([150, 150, 249, 249], fill="white")
        im.save(kaynak)
        hedef = self.tmp / "logo.png"
        g.logo_hazirla(kaynak, hedef)
        logo = Image.open(hedef)
        self.assertEqual(logo.mode, "RGBA")
        self.assertEqual(logo.getpixel((0, 0))[3], 0)
        # kare kırpıldıktan sonra ortada opak beyaz
        kare = logo.crop((0, 0, logo.width, int(logo.height * 0.6)))
        self.assertEqual(kare.getpixel((kare.width // 2, kare.height // 2)), (255, 255, 255, 255))


if __name__ == "__main__":
    unittest.main()
