import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import tebrik_posta  # noqa: E402

GUN = date(2026, 10, 20)
DOGUM = {"tur": "dogum_gunu", "ad": "Çağla Işıkoğlu", "unvan": "Uzman", "bayram": None}
HOS = {"tur": "hos_geldin", "ad": "Ömer Şükrü Güneş", "unvan": "Mühendis", "bayram": None}
BAYRAM = {"tur": "bayram", "ad": "", "unvan": "", "bayram": {
    "ad": "Cumhuriyet Bayramı", "baslangic": "29.10", "tr": "Cumhuriyet Bayramımız kutlu olsun.",
    "en": "Happy Republic Day.", "sablon": "bayram.png"}}
ORTAM = {"TEBRIK_SMTP_SUNUCU": "smtp.ornek.test", "TEBRIK_SMTP_PORT": "587",
         "TEBRIK_SMTP_KULLANICI": "gonderen@nove.group", "TEBRIK_SMTP_SIFRE": "cok-gizli-sifre",
         "TEBRIK_ALICI": "alici@nove.group"}


class AliciTest(unittest.TestCase):
    def test_alici_tek_adres(self):
        self.assertEqual(tebrik_posta.alici_dogrula("  a@nove.group "), "a@nove.group")
        for kotu in ("a@nove.group,b@nove.group", "a@nove.group;b@nove.group", "a@nove.group b@x.com",
                     "a@gmail.com", "a@nove.group.evil.com", "", "@nove.group", "x@y@nove.group"):
            with self.assertRaises(ValueError) as c:
                tebrik_posta.alici_dogrula(kotu)
            if "@" in kotu:
                self.assertNotIn(kotu, str(c.exception))


class IstisnaTest(unittest.TestCase):
    def test_istisna_basligi(self):
        var = "# ANAYASA\n\n## İstisna — tebrik postası\n\nMetin.\n"
        self.assertTrue(tebrik_posta.istisna_var(var))
        self.assertFalse(tebrik_posta.istisna_var("# ANAYASA\n\n## Madde 1\n"))
        self.assertTrue(tebrik_posta.istisna_var(
            "Önceki.\n\n**İstisna — tebrik postası (revize 21.10.2026):** Tebrik danışmanının hazırladığı görsel.\n"))
        self.assertTrue(tebrik_posta.istisna_var("__İstisna — tebrik postası__ metin\n"))
        self.assertFalse(tebrik_posta.istisna_var("## İstisna — tebrik postasıX\n"))
        self.assertFalse(tebrik_posta.istisna_var("## İstisna — tebrik\n"))
        self.assertFalse(tebrik_posta.istisna_var("Metinde İstisna — tebrik postası geçiyor ama başlık değil\n"))


class MailTest(unittest.TestCase):
    def test_ek_adi_ascii(self):
        self.assertEqual(tebrik_posta.ek_adi(GUN, DOGUM), "2026-10-20-dogum-gunu-cagla-isikoglu.png")
        self.assertEqual(tebrik_posta.ek_adi(GUN, HOS), "2026-10-20-hos-geldin-omer-sukru-gunes.png")
        self.assertEqual(tebrik_posta.ek_adi(GUN, BAYRAM), "2026-10-20-bayram-cumhuriyet-bayrami.png")
        self.assertEqual(tebrik_posta.ek_adi(GUN, {**DOGUM, "ad": "İlker  Çelik"}),
                         "2026-10-20-dogum-gunu-ilker-celik.png")

    def test_mail_ekleri_ve_govde(self):
        with tempfile.TemporaryDirectory() as d:
            yollar = []
            for t in (DOGUM, HOS, BAYRAM):
                p = Path(d) / tebrik_posta.ek_adi(GUN, t)
                p.write_bytes(b"\x89PNG\r\n")
                yollar.append(p)
            m = tebrik_posta.mail_kur([DOGUM, HOS, BAYRAM], yollar, ["Geç gönderim notu"],
                                      "gonderen@nove.group", "alici@nove.group", GUN)
        self.assertEqual(m["Subject"], "Tebrikler — 20.10.2026")
        self.assertEqual(m["To"], "alici@nove.group")
        self.assertEqual(m["From"], "gonderen@nove.group")
        ekler = [e.get_filename() for e in m.iter_attachments()]
        self.assertEqual(ekler, [p.name for p in yollar])
        govde = m.get_body(("plain",)).get_content()
        for beklenen in ("Çağla Işıkoğlu", "Ömer Şükrü Güneş",
                         "Yeni yaşınızda, tüm hayallerinizin gerçeğe dönüşmesini dileriz.",
                         "In your new age, we wish all your dreams come true.",
                         "Welcome to the Team!", "Cumhuriyet Bayramımız kutlu olsun.",
                         "Happy Republic Day.", "Geç gönderim notu"):
            self.assertIn(beklenen, govde)

    def test_tebrik_yoksa_konu(self):
        m = tebrik_posta.mail_kur([], [], ["Eksik var"], "g@nove.group", "a@nove.group", GUN)
        self.assertEqual(m["Subject"], "Tebrik tablosu — 20.10.2026")
        self.assertIn("Eksik var", m.get_content())


class _SahteSMTP:
    ornekler = []

    def __init__(self, sunucu, port, **kw):
        self.cagrilar = []
        self.sunucu, self.port = sunucu, port
        _SahteSMTP.ornekler.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, **kw):
        self.cagrilar.append("starttls")

    def login(self, k, s):
        self.cagrilar.append(("login", k, s))

    def send_message(self, mesaj, to_addrs=None, **kw):
        self.cagrilar.append(("send", to_addrs))


class _Patlayan(_SahteSMTP):
    def login(self, k, s):
        raise OSError("giriş reddedildi cok-gizli-sifre alici@nove.group")


class _KapanirkenPatlayan(_SahteSMTP):
    def __exit__(self, *a):
        raise OSError("quit sırasında bağlantı koptu")


class GonderTest(unittest.TestCase):
    def setUp(self):
        _SahteSMTP.ornekler = []
        self.mesaj = tebrik_posta.mail_kur([DOGUM], [], [], "gonderen@nove.group", "alici@nove.group", GUN)

    def test_gonder_tek_alici_ve_tls(self):
        tebrik_posta.gonder(self.mesaj, ORTAM, smtp_kur=_SahteSMTP)
        c = _SahteSMTP.ornekler[0].cagrilar
        self.assertEqual(c[0], "starttls")
        self.assertIn(("send", ["alici@nove.group"]), c)

    def test_ssl_portu(self):
        ssl_kul = []

        class SSL(_SahteSMTP):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                ssl_kul.append(1)

        o = {**ORTAM, "TEBRIK_SMTP_PORT": "465"}
        orijinal = tebrik_posta.smtplib.SMTP_SSL
        tebrik_posta.smtplib.SMTP_SSL = SSL
        try:
            tebrik_posta.gonder(self.mesaj, o)
        finally:
            tebrik_posta.smtplib.SMTP_SSL = orijinal
        self.assertEqual(ssl_kul, [1])
        self.assertNotIn("starttls", SSL.ornekler[-1].cagrilar)

    def test_gecersiz_alici_gondermez(self):
        o = {**ORTAM, "TEBRIK_ALICI": "x@gmail.com"}
        with self.assertRaises(ValueError):
            tebrik_posta.gonder(self.mesaj, o, smtp_kur=_SahteSMTP)
        self.assertEqual(_SahteSMTP.ornekler, [])

    def test_smtp_hatasi_sifre_sizdirmaz(self):
        with self.assertRaises(RuntimeError) as c:
            tebrik_posta.gonder(self.mesaj, ORTAM, smtp_kur=_Patlayan)
        s = str(c.exception)
        self.assertEqual(s, "SMTP: OSError")
        self.assertNotIn("cok-gizli-sifre", s)
        self.assertNotIn("alici@nove.group", s)

    def test_gonderimden_sonra_kapanis_hatasi_yutulur(self):
        tebrik_posta.gonder(self.mesaj, ORTAM, smtp_kur=_KapanirkenPatlayan)
        self.assertIn(("send", ["alici@nove.group"]), _SahteSMTP.ornekler[0].cagrilar)


if __name__ == "__main__":
    unittest.main()
