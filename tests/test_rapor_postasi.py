import contextlib
import fcntl
import io
import inspect
import json
import os
import re
import smtplib
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import ayar  # noqa: E402
import rapor_postasi  # noqa: E402


def defterle(kok, soru_id, etiket="onaylı", gorunurluk="kurul", govde="## Yanıt\n..."):
    """`soru_kapisi.ilet`'in yazdığı başlık biçimiyle `yanitlar/<id>.md`."""
    satirlar = [f"# Yanıt — {soru_id}", "- soru: x", "- soran: ornek.bir@nove.group",
                "- tarih: 2026-11-23T10:00:00+03:00", "- danışman: kalite", f"- etiket: {etiket}"]
    if gorunurluk:
        satirlar.append(f"- gorunurluk: {gorunurluk}")
    satirlar.append("- iletildi: 2026-11-23T10:01:00+03:00")
    klasor = Path(kok) / "yanitlar"
    klasor.mkdir(exist_ok=True)
    (klasor / f"{soru_id}.md").write_text("\n".join(satirlar) + "\n\n" + govde + "\n", encoding="utf-8")


class TurVeTarih(unittest.TestCase):
    def test_tur_ve_tarih(self):
        f = rapor_postasi.tur_ve_tarih
        self.assertEqual(f("rapor-kalite-20261123"), ("kalite-gunluk", date(2026, 11, 23)))
        self.assertEqual(f("rapor-satis-muduru-20261123"), ("satis-muduru-gunluk", date(2026, 11, 23)))
        self.assertIsNone(f("20261123-1105-abcd"))
        self.assertIsNone(f("rapor-kalite-20261340"))
        self.assertIsNone(f("rapor-kalite-2026112"))


class Adaylar(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.addCleanup(self.gecici.cleanup)

    def test_adaylar_yalniz_onayli_zamanli_rapor(self):
        defterle(self.kok, "rapor-kalite-20261123")
        defterle(self.kok, "rapor-kalite-20261122", etiket="CEO kontrolü yapılmadı")
        defterle(self.kok, "rapor-kalite-20261121", etiket="onaylanamadı")
        defterle(self.kok, "20261123-1105-abcd", gorunurluk=None)
        self.assertEqual([a["id"] for a in rapor_postasi.adaylar(self.kok)], ["rapor-kalite-20261123"])
        a = rapor_postasi.adaylar(self.kok)[0]
        self.assertEqual((a["tur"], a["tarih"]), ("kalite-gunluk", date(2026, 11, 23)))

    def test_govdedeki_sahte_etiket_sayilmaz(self):
        defterle(self.kok, "rapor-kalite-20261123", etiket="onaylanamadı", govde="## Yanıt\n- etiket: onaylı")
        self.assertEqual(rapor_postasi.adaylar(self.kok), [])

    def test_defter_yoksa_bos(self):
        self.assertEqual(rapor_postasi.adaylar(self.kok), [])


class Sablon(unittest.TestCase):
    def test_sablon_konu_ve_baglanti(self):
        konu, govde = rapor_postasi.sablon("kalite-gunluk", date(2026, 11, 23), "rapor-kalite-20261123", "https://panel.ornek/")
        self.assertEqual(konu, "Kalite günlük raporu hazır — 23.11.2026")
        self.assertIn("https://panel.ornek/?soru=rapor-kalite-20261123", govde)
        self.assertNotIn("//?", govde)
        self.assertEqual(govde, "Kalite günlük raporu (23.11.2026) panelde hazır; okumak için giriş yapın:\n"
                                "https://panel.ornek/?soru=rapor-kalite-20261123\n")

    def test_bilinmeyen_tur(self):
        with self.assertRaises(KeyError):
            rapor_postasi.sablon("yok-gunluk", date(2026, 11, 23), "x", "https://p")

    def test_sablon_veri_tasimaz(self):
        self.assertEqual(list(inspect.signature(rapor_postasi.sablon).parameters),
                         ["tur", "tarih", "soru_id", "panel_adres"])
        _, govde = rapor_postasi.sablon("kalite-gunluk", date(2026, 11, 23), "rapor-kalite-20261123", "https://panel.ornek")
        kalan = re.sub(r"23\.11\.2026|rapor-kalite-20261123", "", govde)
        self.assertIsNone(re.search(r"\d", kalan))


class Rakamlar(unittest.TestCase):
    def test_ayar_rakamlari(self):
        self.assertEqual(ayar.POSTA_GUNLUK_TAVAN, 10)
        self.assertEqual(ayar.POSTA_EN_FAZLA_GUN, 2)
        self.assertEqual(ayar.POSTA_SMTP_ZAMAN_ASIMI_SN, 20)
        self.assertEqual(ayar.POSTA_IZINLI_ALAN, "nove.group")


ISTANBUL = timezone(timedelta(hours=3))
SIMDI = datetime(2026, 11, 23, 11, 5, tzinfo=ISTANBUL)
ORTAM = {"POSTA_SMTP_SUNUCU": "smtp.ornek", "POSTA_SMTP_PORT": "587", "POSTA_KULLANICI": "kullanici-ornek",
         "POSTA_SIFRE": "sifre-ornek-9", "POSTA_GONDEREN": "rapor@nove.group", "PANEL_ADRES": "https://panel.ornek"}
ALICILAR = ["ornek.bir@nove.group", "ornek.iki@nove.group"]


class SahteSMTP:
    ornekler = []
    hata_ver = {}  # adım adı → istisna

    def __init__(self, host, port, timeout=None):
        self._hata("init")
        self.host, self.port, self.timeout = host, port, timeout
        self.starttls_cagrildi = False
        self.gonderilen = []  # (msg, to_addrs)
        type(self).ornekler.append(self)

    @classmethod
    def _hata(cls, adim):
        if adim in cls.hata_ver:
            raise cls.hata_ver[adim]

    def starttls(self):
        self._hata("starttls")
        self.starttls_cagrildi = True

    def login(self, k, s):
        self._hata("login")

    def send_message(self, msg, to_addrs=None):
        self._hata("send")
        self.gonderilen.append((msg, to_addrs))

    def quit(self):
        pass


class SahteSSL(SahteSMTP):
    ornekler = []
    hata_ver = {}


class Gonderim(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self.gecici.name)
        self.addCleanup(self.gecici.cleanup)
        (self.kok / "ANAYASA.md").write_text(f"x\n{rapor_postasi.ISTISNA_ISARETI}\n", encoding="utf-8")
        (self.kok / "deploy").mkdir()
        self.alicilari_yaz({"kalite-gunluk": ALICILAR})
        SahteSMTP.ornekler = []
        SahteSMTP.hata_ver = {}
        SahteSSL.ornekler = []
        SahteSSL.hata_ver = {}
        for ad, sinif in (("SMTP", SahteSMTP), ("SMTP_SSL", SahteSSL)):
            y = mock.patch.object(rapor_postasi.smtplib, ad, sinif)
            y.start()
            self.addCleanup(y.stop)
        defterle(self.kok, "rapor-kalite-20261123")

    def alicilari_yaz(self, veri):
        (self.kok / "deploy" / "posta-alicilari.json").write_text(
            veri if isinstance(veri, str) else json.dumps(veri), encoding="utf-8")

    def cagir(self, **kw):
        kw.setdefault("ortam", dict(ORTAM))
        kw.setdefault("simdi", SIMDI)
        return rapor_postasi.calistir(self.kok, **kw)

    def mesajlar(self):
        return [m for o in SahteSMTP.ornekler + SahteSSL.ornekler for m in o.gonderilen]

    def test_gonderir_ve_kaydeder(self):
        r = self.cagir()
        self.assertEqual(len(SahteSMTP.ornekler), 1)
        (msg, to_addrs), = self.mesajlar()
        self.assertEqual(msg["Subject"], "Kalite günlük raporu hazır — 23.11.2026")
        self.assertEqual(msg["From"], ORTAM["POSTA_GONDEREN"])
        self.assertEqual(msg["To"], ORTAM["POSTA_GONDEREN"])
        self.assertNotIn("Bcc", msg)
        self.assertNotIn("Cc", msg)
        self.assertEqual(to_addrs, ALICILAR)
        for a in ALICILAR:
            self.assertNotIn(a, msg.as_string())
        k = rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")
        self.assertEqual((k["durum"], k["alici_sayisi"]), ("gonderildi", 2))
        self.assertTrue(SahteSMTP.ornekler[0].starttls_cagrildi)
        self.assertEqual(SahteSSL.ornekler, [])
        self.assertEqual(SahteSMTP.ornekler[0].timeout, ayar.POSTA_SMTP_ZAMAN_ASIMI_SN)
        self.assertEqual(r["sonuclar"][0]["sonuc"], "gonderildi")

    def test_port_465_ssl(self):
        self.cagir(ortam={**ORTAM, "POSTA_SMTP_PORT": "465"})
        self.assertEqual(SahteSMTP.ornekler, [])
        self.assertEqual(len(SahteSSL.ornekler), 1)
        self.assertFalse(SahteSSL.ornekler[0].starttls_cagrildi)

    def test_govdeye_rapor_metni_girmez(self):
        defterle(self.kok, "rapor-kalite-20261123", govde="## Kurula not\nGizli not 4711\n\n## Yanıt\nAyşe Örnek 87,5 puan\n")
        p = self.kok / "yanitlar" / "rapor-kalite-20261123.md"
        p.write_text(p.read_text(encoding="utf-8").replace("- soru: x", "- soru: Günlük kalite raporu 31 görüşme"),
                     encoding="utf-8")
        self.cagir()
        (msg, _), = self.mesajlar()
        ham = msg.as_string() + msg.get_content()
        for yasak in ("4711", "87,5", "Ayşe", "Örnek", "31 görüşme", "Gizli"):
            self.assertNotIn(yasak, ham)
        self.assertFalse(msg.is_multipart())

    def test_idempotent(self):
        self.cagir()
        r = self.cagir()
        self.assertEqual(len(self.mesajlar()), 1)
        self.assertEqual(r["sonuclar"], [])

    def test_kilit_anayasa(self):
        (self.kok / "ANAYASA.md").write_text("istisna yok\n", encoding="utf-8")
        r = self.cagir()
        self.assertEqual(self.mesajlar(), [])
        self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123"))
        self.assertEqual(len(r["kilitler"]), 1)
        self.assertIn("ANAYASA", r["kilitler"][0])
        self.assertEqual(r["sonuclar"][0]["sonuc"], "kilitli")

    def test_kilit_env_eksik(self):
        ortam = {k: v for k, v in ORTAM.items() if k not in ("POSTA_SIFRE", "PANEL_ADRES")}
        r = self.cagir(ortam=ortam)
        self.assertEqual(self.mesajlar(), [])
        metin = " ".join(r["kilitler"])
        self.assertIn("POSTA_SIFRE", metin)
        self.assertIn("PANEL_ADRES", metin)
        for deger in ORTAM.values():
            self.assertNotIn(deger, metin)

    def test_kilit_env_bicim(self):
        r = self.cagir(ortam={**ORTAM, "POSTA_SMTP_PORT": "abc"})
        self.assertTrue(r["kilitler"])
        r = self.cagir(ortam={**ORTAM, "PANEL_ADRES": "panel.ornek"})
        self.assertTrue(r["kilitler"])
        self.assertEqual(self.mesajlar(), [])
        self.assertNotIn("panel.ornek", " ".join(r["kilitler"]))

    def test_kilit_ajan_ortami(self):
        ortam = {**ORTAM, rapor_postasi.AJAN_ISARETI: "1"}
        r = self.cagir(ortam=ortam)
        self.assertEqual(self.mesajlar(), [])
        self.assertTrue(r["kilitler"])
        self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123"))
        r = self.cagir(ortam=ortam, kuru=True)
        self.assertEqual(r["sonuclar"][0]["sonuc"], "gonderilecek")
        self.assertEqual(SahteSMTP.ornekler, [])
        self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123"))

    def test_alici_yok(self):
        self.alicilari_yaz({"okr-gunluk": ALICILAR})
        r = self.cagir()
        self.assertEqual(self.mesajlar(), [])
        self.assertEqual(r["sonuclar"][0]["sonuc"], "alici-yok")
        k = rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")
        self.assertEqual((k["durum"], k["alici_sayisi"]), ("alici-yok", 0))
        (self.kok / "deploy" / "posta-alicilari.json").unlink()
        self.cagir()
        self.assertEqual(self.mesajlar(), [])
        self.assertEqual(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")["durum"], "alici-yok")
        self.alicilari_yaz({"kalite-gunluk": ALICILAR})
        self.cagir()
        self.assertEqual(len(self.mesajlar()), 1)
        self.assertEqual(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")["durum"], "gonderildi")

    def test_alici_dosyasi_bozuk(self):
        for icerik in ({"kalite-gunluk": "ornek.bir@nove.group"},
                       "{bozuk json",
                       {"kalite-gunluk": ["ornek.bir@nove.group\nBcc: x@disari.ornek"]},
                       {"kalite-gunluk": ["ornek.bir@nove.group", "biri@disari.ornek"]},
                       {"kalite-gunluk": ["biri@nove.group.disari.ornek"]}):
            with self.subTest(icerik=icerik):
                r = self._bozuk(icerik)
                self.assertEqual(self.mesajlar(), [])
                metin = " ".join(r["kilitler"])
                self.assertIn("alıcı dosyası bozuk", metin)
                self.assertNotIn("@", metin)
                self.assertEqual(r["sonuclar"][0]["sonuc"], "kilitli")

    def _bozuk(self, icerik):
        self.alicilari_yaz(icerik)
        return self.cagir()

    def test_alici_alan_buyuk_kucuk_harf_ve_yinelenen(self):
        self.alicilari_yaz({"kalite-gunluk": [" Ornek.Bir@Nove.Group ", "ornek.bir@nove.group"]})
        self.assertEqual(rapor_postasi.alicilari_oku(self.kok), {"kalite-gunluk": ["ornek.bir@nove.group"]})

    def test_tavan(self):
        defterle(self.kok, "rapor-okr-20261123")
        self.alicilari_yaz({"kalite-gunluk": ALICILAR, "okr-gunluk": ALICILAR})
        with mock.patch.object(ayar, "POSTA_GUNLUK_TAVAN", 1), \
                mock.patch.dict(rapor_postasi.RAPOR_ADLARI, {"okr-gunluk": "OKR günlük raporu"}):
            r = self.cagir()
            self.assertEqual(len(self.mesajlar()), 1)
            self.assertEqual([x["sonuc"] for x in r["sonuclar"]], ["gonderildi", "tavan"])
            self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-okr-20261123"))
            self.cagir(simdi=SIMDI + timedelta(days=1))
            self.assertEqual(len(self.mesajlar()), 2)

    def test_eski_rapor_gitmez(self):
        for g in ("20261023", "20261120", "20261121"):
            defterle(self.kok, f"rapor-kalite-{g}")
        r = self.cagir()
        sonuc = {x["id"]: x["sonuc"] for x in r["sonuclar"]}
        self.assertEqual(sonuc["rapor-kalite-20261023"], "eski")
        self.assertEqual(sonuc["rapor-kalite-20261120"], "eski")
        self.assertEqual(sonuc["rapor-kalite-20261121"], "gonderildi")
        self.assertEqual(sonuc["rapor-kalite-20261123"], "gonderildi")
        self.assertEqual(len(self.mesajlar()), 2)
        for g in ("20261023", "20261120"):
            self.assertIsNone(rapor_postasi.kayit_oku(self.kok, f"rapor-kalite-{g}"))

    def test_ad_yok(self):
        defterle(self.kok, "rapor-okr-20261123")
        r = self.cagir()
        sonuc = {x["id"]: x["sonuc"] for x in r["sonuclar"]}
        self.assertEqual(sonuc["rapor-okr-20261123"], "ad-yok")
        self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-okr-20261123"))

    def test_hata_yeniden_denenir(self):
        SahteSMTP.hata_ver = {"send": smtplib.SMTPRecipientsRefused({ALICILAR[0]: (550, b"x")})}
        r = self.cagir()
        k = rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")
        self.assertEqual((k["durum"], k["hata"], k["deneme"]), ("hata", "SMTPRecipientsRefused", 1))
        self.assertNotIn("@", rapor_postasi.kayit_yolu(self.kok, "rapor-kalite-20261123").read_text(encoding="utf-8"))
        self.assertNotIn("@", json.dumps(r, ensure_ascii=False, default=str))
        SahteSMTP.hata_ver = {}
        self.cagir()
        k = rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123")
        self.assertEqual(k["durum"], "gonderildi")

    def test_send_hatasi_donguyu_surdurur(self):
        defterle(self.kok, "rapor-kalite-20261122")
        sayac = []

        def bir_kez_hata(self, msg, to_addrs=None):
            sayac.append(1)
            if len(sayac) == 1:
                raise smtplib.SMTPServerDisconnected("x")
            self.gonderilen.append((msg, to_addrs))
        SahteSMTP.hata_ver = {}
        with mock.patch.object(SahteSMTP, "send_message", bir_kez_hata):
            r = self.cagir()
        self.assertEqual([x["sonuc"] for x in r["sonuclar"]], ["hata", "gonderildi"])
        self.assertEqual(len(SahteSMTP.ornekler), 1)

    def test_baglanti_hatasi_donguyu_bitirir(self):
        defterle(self.kok, "rapor-kalite-20261122")
        SahteSMTP.hata_ver = {"init": OSError("x")}
        with mock.patch.object(SahteSMTP, "_hata", wraps=SahteSMTP._hata) as m:
            r = self.cagir()
        self.assertEqual(m.call_count, 1)
        k = rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261122")
        self.assertEqual((k["durum"], k["hata"]), ("hata", "OSError"))
        self.assertIsNone(rapor_postasi.kayit_oku(self.kok, "rapor-kalite-20261123"))
        self.assertEqual([x["sonuc"] for x in r["sonuclar"]], ["hata"])

    def test_ayni_anda_iki_cagri(self):
        klasor = self.kok / "sirket-log" / "posta"
        klasor.mkdir(parents=True)
        with open(klasor / ".kilit", "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r = self.cagir()
            self.assertEqual(self.mesajlar(), [])
            self.assertEqual(r["kilitler"], ["başka bir gönderim sürüyor"])
            self.assertEqual(r["sonuclar"], [])
            k = self.cagir(kuru=True)
            self.assertEqual(k["sonuclar"][0]["sonuc"], "gonderilecek")
        self.cagir()
        self.assertEqual(len(self.mesajlar()), 1)

    def test_kayitta_adres_yok(self):
        self.cagir()
        dosyalar = [p for p in (self.kok / "sirket-log" / "posta").rglob("*") if p.is_file()]
        self.assertTrue(dosyalar)
        for p in dosyalar:
            self.assertNotIn("@", p.read_text(encoding="utf-8"))

    def test_kuru_yazmaz(self):
        r = self.cagir(kuru=True)
        self.assertEqual(r["sonuclar"][0]["sonuc"], "gonderilecek")
        self.assertEqual(r["sonuclar"][0]["alici_sayisi"], 2)
        self.assertEqual(SahteSMTP.ornekler, [])
        self.assertFalse((self.kok / "sirket-log").exists())

    def test_kuru_kilitleri_raporlar_ama_listeler(self):
        (self.kok / "ANAYASA.md").write_text("yok\n", encoding="utf-8")
        r = self.cagir(kuru=True)
        self.assertEqual(len(r["kilitler"]), 1)
        self.assertEqual(r["sonuclar"][0]["sonuc"], "gonderilecek")

    def test_kuru_panel_adresi_yokken_dusmez(self):
        r = self.cagir(kuru=True, ortam={rapor_postasi.AJAN_ISARETI: "1"})
        self.assertEqual(r["sonuclar"][0]["sonuc"], "gonderilecek")
        self.assertIn("PANEL_ADRES", " ".join(r["kilitler"]))
        self.assertEqual(SahteSMTP.ornekler, [])

    def test_ortam_varsayilani_kok_env(self):
        onceki = dict(os.environ)
        with mock.patch.dict(os.environ, {}, clear=True):
            r = rapor_postasi.calistir(self.kok, simdi=SIMDI)
            self.assertEqual(os.environ, {})
        self.assertEqual(os.environ, onceki)
        metin = " ".join(r["kilitler"])
        for ad in rapor_postasi.GEREKLI_ANAHTARLAR:
            self.assertIn(ad, metin)

    def test_okunamayan_kayit_calistirmayi_bozmaz(self):
        defterle(self.kok, "rapor-kalite-20261122")
        (self.kok / "yanitlar" / "rapor-kalite-20261122.md").write_bytes(b"\xff\xfe\x00bozuk")
        self.assertEqual([a["id"] for a in rapor_postasi.adaylar(self.kok)], ["rapor-kalite-20261123"])

    def test_ornek_dosya_gecerli(self):
        depo = Path(__file__).resolve().parent.parent
        veri = json.loads((depo / "deploy" / "posta-alicilari.json.example").read_text(encoding="utf-8"))
        gecici = tempfile.TemporaryDirectory()
        self.addCleanup(gecici.cleanup)
        (Path(gecici.name) / "deploy").mkdir()
        (Path(gecici.name) / "deploy" / "posta-alicilari.json").write_text(json.dumps(veri), encoding="utf-8")
        self.assertEqual(rapor_postasi.alicilari_oku(gecici.name), {k: v for k, v in veri.items()})
        self.assertIn("deploy/posta-alicilari.json", (depo / ".gitignore").read_text(encoding="utf-8").splitlines())


class KomutSatiri(unittest.TestCase):
    AJAN = {**ORTAM, "CLAUDECODE": "1"}
    setUp = Gonderim.setUp
    alicilari_yaz = Gonderim.alicilari_yaz

    def main(self, argv, ortam):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            kod = rapor_postasi.main(argv, kok=self.kok, ortam=ortam, simdi=SIMDI)
        return kod, cikti.getvalue()

    def kayit_dosyalari(self):
        return list((self.kok / "sirket-log" / "posta").glob("*.json"))

    def test_kuru_ajan_ortaminda_listeler(self):
        kod, cikti = self.main(["--kuru"], self.AJAN)
        self.assertEqual(kod, 0)
        for parca in ("rapor-kalite-20261123", "2 alıcı", "kuru koşu", "rapor postası — 2026-11-23 11:05 (kuru)"):
            self.assertIn(parca, cikti)
        self.assertNotIn("@", cikti)
        self.assertEqual(SahteSMTP.ornekler + SahteSSL.ornekler, [])
        self.assertEqual(self.kayit_dosyalari(), [])

    def test_ajan_ortaminda_yazan_kosu_durur(self):
        kod, cikti = self.main([], self.AJAN)
        self.assertEqual(kod, 1)
        self.assertIn("yalnız --kuru", cikti)
        self.assertEqual(SahteSMTP.ornekler + SahteSSL.ornekler, [])
        self.assertEqual(self.kayit_dosyalari(), [])

    def test_kilitler_kuruda_gorunur(self):
        (self.kok / "ANAYASA.md").write_text("istisna yok\n", encoding="utf-8")
        kod, cikti = self.main(["--kuru"], {})
        self.assertEqual(kod, 0)
        self.assertEqual(sum(1 for s in cikti.splitlines() if s.startswith("  KİLİT ")), 2)
        self.assertIn("GÖNDER", cikti)

    def test_gercek_kosu_cikis_kodlari(self):
        kod, cikti = self.main([], dict(ORTAM))
        self.assertEqual(kod, 0)
        self.assertIn("GİTTİ", cikti)
        self.assertNotIn("(kuru)", cikti)
        # kilit tutmuyor
        (self.kok / "ANAYASA.md").write_text("istisna yok\n", encoding="utf-8")
        kod, cikti = self.main([], dict(ORTAM))
        self.assertEqual(kod, 1)
        self.assertIn("KİLİT", cikti)

    def test_gonderim_hatasi_cikis_1(self):
        SahteSMTP.hata_ver = {"send": smtplib.SMTPRecipientsRefused({ALICILAR[0]: (550, b"x")})}
        kod, cikti = self.main([], dict(ORTAM))
        self.assertEqual(kod, 1)
        self.assertIn("HATA SMTPRecipientsRefused", cikti)
        self.assertNotIn("@", cikti)

    def test_kullanim_hatasi(self):
        self.assertEqual(self.main(["--gonder"], dict(ORTAM))[0], 2)
        self.assertEqual(self.main(["x"], dict(ORTAM))[0], 2)

    def test_alt_surec_kuru(self):
        kok = Path(__file__).resolve().parent.parent
        r = subprocess.run([sys.executable, "bin/rapor_postasi.py", "--kuru"], cwd=kok,
                           env={**os.environ, "CLAUDECODE": "1"}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("rapor postası —"), r.stdout)
        self.assertNotIn("@", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
