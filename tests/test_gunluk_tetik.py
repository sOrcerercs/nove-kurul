"""Zamanlanmış iş kuyruğu: günlük ve haftalık maddeler. Ağ yok, claude çağrısı yok.

`kasa-bakimi` her sabah koşar, `haftalik-rapor` yalnız pazartesi. İkisi de aynı
listeden (`gunluk.ZAMANLI`) beslenir; fark `gun` alanındadır: None = her gün.

python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import gunluk  # noqa: E402

SALI = datetime(2026, 9, 15, 9, 0).astimezone()
CARSAMBA = datetime(2026, 9, 16, 9, 0).astimezone()
PAZARTESI = datetime(2026, 9, 14, 9, 0).astimezone()


def sahte_kok(tmp, *takimlar):
    kok = Path(tmp) / "kok"
    for ad in takimlar:
        (kok / "takimlar" / ad / "kosu").mkdir(parents=True)
        (kok / "takimlar" / ad / "durum.json").write_text(
            json.dumps({"takim": ad, "kuyruk": []}), encoding="utf-8")
    return kok


class GunlukMaddeTesti(unittest.TestCase):
    MADDE = [{"takim": "kasa-bakimi", "gun": None, "id": "kasa-{tarih}", "not": "kasa sağlığı"}]

    def test_gun_none_olan_madde_her_gun_kuyruga_duser(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, "kasa-bakimi")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                sali = gunluk.zamanli_kuyruk(kok, SALI)
                carsamba = gunluk.zamanli_kuyruk(kok, CARSAMBA)
        self.assertEqual([m["id"] for m in sali], ["kasa-2026-09-15"])
        self.assertEqual([m["id"] for m in carsamba], ["kasa-2026-09-16"])

    def test_ayni_gunun_maddesi_ikinci_kez_yazilmaz(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, "kasa-bakimi")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                gunluk.zamanli_kuyruk(kok, SALI)
                tekrar = gunluk.zamanli_kuyruk(kok, SALI)
                kuyruk = ayar.durum_oku("kasa-bakimi", kok)["kuyruk"]
        self.assertEqual(tekrar, [])
        self.assertEqual([(o["id"], o["durum"]) for o in kuyruk], [("kasa-2026-09-15", "bekliyor")])


class HaftalikMaddeTesti(unittest.TestCase):
    MADDE = [{"takim": "haftalik-rapor", "gun": 0, "id": "rapor-{hafta}", "not": "haftalık rapor"}]

    def test_gun_belirtilmis_madde_yalniz_o_gun_duser(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, "haftalik-rapor")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                sali = gunluk.zamanli_kuyruk(kok, SALI)
                pazartesi = gunluk.zamanli_kuyruk(kok, PAZARTESI)
        self.assertEqual(sali, [])
        self.assertEqual([m["id"] for m in pazartesi], ["rapor-2026-W38"])


class SablonAnahtarlariTesti(unittest.TestCase):
    def test_id_sablonu_hem_tarih_hem_hafta_anahtarini_kabul_eder(self):
        """Bir liste iki tempoyu taşıyor; şablon ikisini de tanımalı."""
        madde = [{"takim": "t", "gun": None, "id": "x-{tarih}-{hafta}", "not": "-"}]
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, "t")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                yazilan = gunluk.zamanli_kuyruk(kok, SALI)
        self.assertEqual([m["id"] for m in yazilan], ["x-2026-09-15-2026-W38"])


class AylikMaddeTesti(unittest.TestCase):
    """`ayin` alanı: ayda bir düşer, kaçırılan ay telafi edilir."""

    MADDE = [{"takim": "deneme", "gun": None, "ayin": 1, "id": "okr-{ay}",
              "not": "aylık OKR durumu"}]

    def _kuyruk(self, kok, takim="deneme"):
        return json.loads((Path(kok) / "takimlar" / takim / "durum.json")
                          .read_text(encoding="utf-8")).get("kuyruk") or []

    def test_ayin_birinde_duser(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 1, 9, 0))
            self.assertEqual([y["id"] for y in yazilan], ["okr-2026-10"])

    def test_ayin_yirmisinde_telafi_eder(self):
        """Makine 1'inde kapalıysa rapor hiç üretilmemektense geç üretilir."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 20, 9, 0))
            self.assertEqual([y["id"] for y in yazilan], ["okr-2026-10"])

    def test_ayin_gununden_once_dusmez(self):
        madde = [{**self.MADDE[0], "ayin": 15}]
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 3, 9, 0))
            self.assertEqual(yazilan, [])

    def test_ayni_ay_ikinci_kez_dusmez(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 1, 9, 0))
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 2, 9, 0))
            self.assertEqual(yazilan, [])
            self.assertEqual(len(self._kuyruk(kok)), 1)

    def test_sonraki_ay_yeniden_duser(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", self.MADDE):
                gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 1, 9, 0))
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 11, 1, 9, 0))
            self.assertEqual([y["id"] for y in yazilan], ["okr-2026-11"])

    def test_gunluk_ve_haftalik_davranis_degismez(self):
        """Diğer dört takım bu değişiklikten etkilenmemeli."""
        madde = [{"takim": "deneme", "gun": None, "id": "g-{tarih}", "not": "günlük"},
                 {"takim": "deneme", "gun": 4, "id": "h-{hafta}", "not": "haftalık"}]
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                cuma = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 2, 9, 0))   # cuma
            self.assertEqual(sorted(y["id"] for y in cuma),
                             ["g-2026-10-02", "h-2026-W40"])
            with tempfile.TemporaryDirectory() as tmp2:
                kok2 = sahte_kok(tmp2, "deneme")
                with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                    pzt = gunluk.zamanli_kuyruk(kok2, datetime(2026, 10, 5, 9, 0))  # pazartesi
                self.assertEqual([y["id"] for y in pzt], ["g-2026-10-05"])

    def test_ayin_varsa_gun_yok_sayilir(self):
        """ayin varsa gun yok sayılır — iki alan aynı anda anlamlı olamaz.

        Tarih: 2026-10-05 (pazartesi, ayın 5'i). gun=4 (perşembe) ve ayin=1 (ayın 1'i ve sonrası).
        gun=4 koşulunu sağlamıyor, ama ayin koşulu sağlanıyor → madde DÜŞER.
        """
        madde = [{"takim": "deneme", "gun": 4, "ayin": 1, "id": "okr-{ay}", "not": "aylık OKR"}]
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                yazilan = gunluk.zamanli_kuyruk(kok, datetime(2026, 10, 5, 9, 0))  # pazartesi, ayın 5'i
            self.assertEqual([y["id"] for y in yazilan], ["okr-2026-10"])


class GunAnahtariEksikTesti(unittest.TestCase):
    """`madde.get("gun")` kullanılmalı — köşeli parantez `madde["gun"]` `ayin` kaldırılıp
    `gun` eklenmeyi unutulan bir maddede sabah tetiğini KeyError ile düşürürdü."""

    def test_gun_anahtari_olmayan_madde_keyerror_vermez_her_gun_duser(self):
        madde = [{"takim": "deneme", "id": "x-{tarih}", "not": "-"}]   # "gun" hiç yok
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, "deneme")
            with unittest.mock.patch.object(gunluk, "ZAMANLI", madde):
                yazilan = gunluk.zamanli_kuyruk(kok, SALI)   # KeyError atmamalı
            self.assertEqual([m["id"] for m in yazilan], ["x-2026-09-15"])


class AylikMaddeIdSablonuTesti(unittest.TestCase):
    def test_zamanli_daki_her_ayin_maddesi_id_de_ay_tasir(self):
        """`ayin` taşıyan bir madde `id`'sinde `{ay}` içermezse telafi mantığı bozulur:
        her gün yeni id üretilir ve madde ayın kalan günlerinde her sabah kuyruğa düşer."""
        ayin_maddeleri = [m for m in gunluk.ZAMANLI if m.get("ayin") is not None]
        for madde in ayin_maddeleri:
            self.assertIn("{ay}", madde["id"], madde["id"])


if __name__ == "__main__":
    unittest.main()
