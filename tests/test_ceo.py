"""CEO Ajanı — Denetçi'den sonraki ikinci onay kapısı (NOVE-KURULUM.md §5, sirket/CEO-KIMLIGI.md).

Ağ yok, para harcamaz: claude çağrısı `calistir` parametresiyle sahtelenir.
python3 -m unittest discover -s tests
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import ceo  # noqa: E402
import kos  # noqa: E402

SORU_ID = "20261012-1000-abcd"
BASLIK = f"""# Soru {SORU_ID}
- soran: kurul@nove.group (rol: kurul)
- zaman: 2026-10-12 10:00
- soru: Q3 bütçe sapmasının ana nedenleri neler?
- bütçe: 5,00 USD
- durum: alındı

## Dağıtım
- danışman: Finans
- yöntem: anahtar kelime
- eşleşen ifadeler: bütçe, sapma
"""
DENETCI_KABUL = "\n## Denetçi\n- karar: **kabul**\n- gerekçe: temiz\n- kontrol: kaynak gecti · hesap gecti · tutarlilik gecti\n"
DENETCI_RED = "\n## Denetçi\n- karar: **red**\n- gerekçe: hesap tutmuyor\n"
CEO_RED = "\n## CEO — karar: red\n- tur: 1/2\n- gerekçe: neden kırılımı yok\n"
CEO_ONAY = "\n## CEO — karar: onay\n- tur: 1/2\n- gerekçe: tamam\n"

ONAY = {"karar": "onay", "bulgular": [], "gerekce": "Soru yanıtlanmış; sayılar veri/q3.csv'de.",
        "kurula_not": "Veri 30 Eylül'e kadar."}
RED = {"karar": "red", "bulgular": ["Neden kırılımı ekle.", "%18 veri/q3.csv'de yok."],
       "gerekce": "Soru yanıtlanmamış.", "kurula_not": ""}


def _cozum(karar=None, metin=None, hata=False, maliyet=0.31):
    return {"hata": hata, "maliyet": maliyet, "tur": 4,
            "metin": metin if metin is not None else "Kontrol ettim.\n" + json.dumps(karar, ensure_ascii=False)}


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        (self.kok / "sirket").mkdir()
        shutil.copy(KOK / "sirket" / "CEO-KIMLIGI.md", self.kok / "sirket" / "CEO-KIMLIGI.md")
        cikti = self.kok / "takimlar" / "finans" / "cikti"
        cikti.mkdir(parents=True)
        (cikti / f"{SORU_ID}-taslak.md").write_text("# Yanıt\nQ3 sapması %4 (n=412)\n", encoding="utf-8")
        (self.kok / "sirket-log" / "sorular").mkdir(parents=True)
        self.kayit = self.kok / "sirket-log" / "sorular" / f"{SORU_ID}.md"

    def yaz(self, *bolumler):
        self.kayit.write_text(BASLIK + "".join(bolumler), encoding="utf-8")

    def kontrol(self, cozum=None, **kw):
        cagri = mock.MagicMock(return_value=cozum or _cozum(ONAY))
        return ceo.kontrol_et(self.kok, SORU_ID, calistir=cagri, **kw), cagri


class OnSartTesti(Kurulum):
    """`ceo.py` yalnız Denetçi kabulünden sonra çalışır (§5, kabul ölçütü §12)."""

    def test_denetci_kabul_yoksa_hata_ve_claude_cagrilmaz(self):
        self.yaz()
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()

    def test_denetci_red_ise_hata(self):
        self.yaz(DENETCI_RED)
        with self.assertRaises(ceo.OnSartHatasi) as h:
            self.kontrol()
        self.assertIn("Denetçi", str(h.exception))

    def test_red_sonrasi_kabul_gelirse_calisir(self):
        """Denetçi önce reddetti, danışman düzeltti, sonra kabul: son karar sayılır."""
        self.yaz(DENETCI_RED, DENETCI_KABUL)
        karar, cagri = self.kontrol()
        cagri.assert_called_once()
        self.assertEqual(karar["karar"], "onay")

    def test_ceo_reddinden_sonra_denetci_yeniden_kabul_vermeden_calismaz(self):
        """CEO red → danışman düzeltir → Denetçi tekrar → CEO tekrar. Denetçi atlanamaz."""
        self.yaz(DENETCI_KABUL, CEO_RED)
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()

    def test_onaylanmis_soru_yeniden_kontrol_edilmez(self):
        self.yaz(DENETCI_KABUL, CEO_ONAY)
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()

    def test_ikinci_redden_sonra_ucuncu_tur_yok(self):
        """ayar.CEO_MAKS_RED = 1: en fazla bir düzeltme turu → CEO bir soruya en fazla iki kez bakar."""
        self.yaz(DENETCI_KABUL, CEO_RED, DENETCI_KABUL, CEO_RED, DENETCI_KABUL)
        with self.assertRaises(ceo.OnSartHatasi) as h:
            self.kontrol()
        self.assertIn("tur", str(h.exception))

    def test_soru_kaydi_yoksa_hata(self):
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()

    def test_taslak_yoksa_hata(self):
        self.yaz(DENETCI_KABUL)
        (self.kok / "takimlar" / "finans" / "cikti" / f"{SORU_ID}-taslak.md").unlink()
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()

    def test_kimlik_dosyasi_yoksa_hata(self):
        self.yaz(DENETCI_KABUL)
        (self.kok / "sirket" / "CEO-KIMLIGI.md").unlink()
        with self.assertRaises(ceo.OnSartHatasi):
            self.kontrol()


class DanismanAdiTesti(unittest.TestCase):
    def test_gorunen_ad_klasor_adina_cevrilir(self):
        for ad, klasor in (("Finans", "finans"), ("Satış Müdürü", "satis-muduru"), ("OKR", "okr"),
                           ("Raporlama", "raporlama"), ("Kalite", "kalite")):
            with self.subTest(ad=ad):
                self.assertEqual(ceo.takim_adi(ad), klasor)

    def test_klasor_adi_soru_kaydinin_dagitim_bolumunden_okunur(self):
        self.assertEqual(ceo.danisman(BASLIK), "finans")


class KarariAyristirTesti(unittest.TestCase):
    def test_metnin_icindeki_json_okunur(self):
        karar = ceo.karari_ayristir("Bakalım.\n" + json.dumps(ONAY, ensure_ascii=False) + "\nbitti")
        self.assertEqual(karar["karar"], "onay")
        self.assertEqual(karar["kurula_not"], "Veri 30 Eylül'e kadar.")

    def test_json_yoksa_red_okunamadi(self):
        karar = ceo.karari_ayristir("Bence onaylanabilir.")
        self.assertEqual(karar["karar"], "red")
        self.assertIn("CEO yanıtı okunamadı", karar["gerekce"])

    def test_karar_gecersizse_red_asla_onay_sayilmaz(self):
        for bozuk in ({"karar": "kabul", "gerekce": "x"}, {"karar": "ONAY"}, {"gerekce": "iyi"},
                      {"karar": "onay", "bulgular": "liste değil", "gerekce": "x"}, [1, 2]):
            with self.subTest(bozuk=bozuk):
                karar = ceo.karari_ayristir(json.dumps(bozuk))
                self.assertEqual(karar["karar"], "red")
                self.assertIn("okunamadı", karar["gerekce"])

    def test_bulgular_en_fazla_uc_madde(self):
        karar = ceo.karari_ayristir(json.dumps({**RED, "bulgular": ["a", "b", "c", "d", "e"]}))
        self.assertEqual(karar["bulgular"], ["a", "b", "c"])

    def test_red_kararinda_kurula_not_tasinmaz(self):
        karar = ceo.karari_ayristir(json.dumps({**RED, "kurula_not": "kurula gitmesin"}))
        self.assertEqual(karar["kurula_not"], "")


class KontrolTesti(Kurulum):
    def test_onay_soru_kaydina_yazilir(self):
        self.yaz(DENETCI_KABUL)
        karar, _ = self.kontrol(_cozum(ONAY, maliyet=0.312))
        self.assertEqual(karar["karar"], "onay")
        kayit = self.kayit.read_text(encoding="utf-8")
        self.assertIn("## CEO — karar: onay", kayit)
        self.assertIn("- tur: 1/2", kayit)
        self.assertIn("- kurula not: Veri 30 Eylül'e kadar.", kayit)
        self.assertIn("- maliyet: 0.312 USD", kayit)

    def test_red_bulgulariyla_yazilir(self):
        self.yaz(DENETCI_KABUL)
        self.kontrol(_cozum(RED))
        kayit = self.kayit.read_text(encoding="utf-8")
        self.assertIn("## CEO — karar: red", kayit)
        self.assertIn("  1. Neden kırılımı ekle.", kayit)
        self.assertIn("  2. %18 veri/q3.csv'de yok.", kayit)

    def test_ikinci_tur_numaralanir_ve_istemde_ilk_bulgular_hatirlatilir(self):
        self.yaz(DENETCI_KABUL, CEO_RED, DENETCI_KABUL)
        karar, cagri = self.kontrol()
        self.assertEqual(karar["tur"], 2)
        self.assertIn("- tur: 2/2", self.kayit.read_text(encoding="utf-8"))
        self.assertIn("ikinci kontrol", cagri.call_args[0][0])

    def test_claude_hatasi_red_sayilir_onay_sayilmaz(self):
        self.yaz(DENETCI_KABUL)
        karar, _ = self.kontrol(_cozum(metin="süre tavanı aşıldı", hata=True, maliyet=0.0))
        self.assertEqual(karar["karar"], "red")
        self.assertIn("CEO yanıtı okunamadı", karar["gerekce"])
        self.assertIn("süre tavanı aşıldı", karar["gerekce"])

    def test_istem_kimligi_ve_dosya_yollarini_tasir(self):
        self.yaz(DENETCI_KABUL)
        _, cagri = self.kontrol()
        istem = cagri.call_args[0][0]
        self.assertIn("CEO Ajanı", istem)
        self.assertIn(f"sirket-log/sorular/{SORU_ID}.md", istem)
        self.assertIn(f"takimlar/finans/cikti/{SORU_ID}-taslak.md", istem)
        self.assertIn("takimlar/finans/veri/", istem)
        self.assertIn("yanitlar/", istem)

    def test_ceo_kapaliysa_claude_cagrilmaz_ve_kayda_yazilir(self):
        self.yaz(DENETCI_KABUL)
        with mock.patch.object(ayar, "CEO_ACIK", False):
            karar, cagri = self.kontrol()
        cagri.assert_not_called()
        self.assertEqual(karar["karar"], "yapilmadi")
        self.assertIn("## CEO — kontrol yapılmadı", self.kayit.read_text(encoding="utf-8"))


class ClaudeKomutuTesti(unittest.TestCase):
    """Opus · yalnız okuma araçları · 0,50 USD · Denetçi'ye tabi değil (SIRKET_TAKIM yok)."""

    def test_komut(self):
        komut = ceo.claude_komutu("istem")
        self.assertEqual(komut[komut.index("--model") + 1], "opus")
        self.assertEqual(komut[komut.index("--allowedTools") + 1], "Read,Glob,Grep")
        self.assertEqual(komut[komut.index("--max-budget-usd") + 1], str(ayar.CEO_BUTCESI_USD))
        self.assertNotIn("acceptEdits", komut)

    def test_ortamda_sirket_takim_ve_kosu_yok(self):
        with mock.patch.dict("os.environ", {"SIRKET_TAKIM": "finans", "SIRKET_KOSU": "x", "CLAUDECODE": "1"}):
            ortam = ceo.claude_ortami()
        for ad in ("SIRKET_TAKIM", "SIRKET_KOSU", "CLAUDECODE"):
            self.assertNotIn(ad, ortam)

    def test_sure_tavani_ayardan(self):
        with mock.patch.object(ceo.subprocess, "run", side_effect=ceo.subprocess.TimeoutExpired("claude", 1)) as r:
            cozum = ceo.claude_sor("istem")
        self.assertEqual(r.call_args.kwargs["timeout"], ayar.CEO_SURESI_SN)
        self.assertTrue(cozum["hata"])
        self.assertIn("süre tavanı", cozum["metin"])


class MainTesti(Kurulum):
    def test_on_sart_hatasi_cikis_2(self):
        self.yaz()
        with mock.patch.object(ceo, "KOK", self.kok), mock.patch.object(ceo.ayar, "ortam_yukle"):
            self.assertEqual(ceo.main([SORU_ID]), 2)

    def test_arguman_yoksa_cikis_2(self):
        self.assertEqual(ceo.main([]), 2)


if __name__ == "__main__":
    unittest.main()


class TavanTesti(unittest.TestCase):
    """§9 (N27, N31): soru bütçesi en kötü yola ve Denetçi payına yeter; rakam yalnız ayar.py'de (ANAYASA §4)."""

    def test_soru_butcesi_en_kotu_yola_yeter(self):
        en_kotu = 2 * ayar.KOSU_BUTCESI_USD + (1 + ayar.CEO_MAKS_RED) * ayar.CEO_BUTCESI_USD
        self.assertLessEqual(en_kotu + 1.0, ayar.SORU_BUTCESI_USD)

    def test_ceo_tavani_faz4_olcumune_kadar_1_5(self):
        """Kağan, 19.10.2026: Opus 5.5 tahmini tipik ~0,53, ağır ~1,28 USD; Faz 4 beş gerçek soruda ölçülecek."""
        self.assertEqual(ayar.CEO_BUTCESI_USD, 1.5)



class ModelKaydiTesti(Kurulum):
    """N31: Faz 4 maliyet ölçümü için kayıt, koşuyu gerçekte hangi modelin yaptığını söyler (`opus` takma adı varsayım)."""

    def test_cozumleyici_modelleri_maliyete_gore_siralar(self):
        cikti = json.dumps({"result": "x", "total_cost_usd": 0.42, "num_turns": 3, "is_error": False,
                            "modelUsage": {"claude-haiku-5-5": {"costUSD": 0.004},
                                           "claude-opus-5-5": {"costUSD": 0.416}}})
        self.assertEqual(kos.sonucu_cozumle(cikti)["modeller"], ["claude-opus-5-5", "claude-haiku-5-5"])

    def test_model_bilgisi_yoksa_bilinmiyor_der(self):
        cozum = kos.sonucu_cozumle(json.dumps({"result": "x", "total_cost_usd": 0.1}))
        self.assertEqual(cozum["modeller"], [])
        self.assertEqual(kos.model_metni(cozum), "bilinmiyor")
        self.assertEqual(kos.model_metni({"hata": True}), "bilinmiyor")

    def test_ceo_bolumu_modeli_yazar(self):
        self.yaz(DENETCI_KABUL)
        self.kontrol({**_cozum(ONAY), "modeller": ["claude-opus-5-5"]})
        self.assertIn("- model: claude-opus-5-5\n", self.kayit.read_text(encoding="utf-8"))
