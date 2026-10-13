"""İş Dağıtımcı — soruyu doğru danışmana götürmek (sirket/IS-DAGITIMCI.md Görev 1, NOVE-KURULUM.md §2 adım 2).

Önce anahtar kelime tablosu (LLM yok); eşleşme yoksa ya da berabere ise Haiku. Haiku sahtelenir: ağ yok, para yok.
python3 -m unittest discover -s tests
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


def _takim(kok, ad, kelimeler, meslek="danışman"):
    dizin = kok / "takimlar" / ad
    dizin.mkdir(parents=True)
    (dizin / "takim.md").write_text(
        f"---\nname: {ad}\ndescription: {meslek}\nanahtar_kelimeler: [{', '.join(kelimeler)}]\n---\n# {ad}\n",
        encoding="utf-8")
    (dizin / "durum.json").write_text(json.dumps({"takim": ad, "kuyruk": []}), encoding="utf-8")


class Kurulum(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp())
        _takim(self.kok, "finans", ["bütçe", "nakit", "maliyet", "sapma"], "Finans danışmanı")
        _takim(self.kok, "okr", ["okr", "hedef", "sapma"], "OKR danışmanı")
        _takim(self.kok, "kalite", ["şikâyet", "kalite", "İade"], "Kalite danışmanı")
        kurulumda = self.kok / "takimlar" / "raporlama"
        kurulumda.mkdir(parents=True)
        (kurulumda / "takim.md").write_text("# Raporlama Danışmanı\n", encoding="utf-8")
        self.haiku = mock.MagicMock(return_value={"danisman": "kalite", "gerekce": "müşteri deneyimi",
                                                  "oneri": None, "maliyet": 0.012})

    def soru(self, metin, soru_id="20261012-1200-abcd", durum="alındı"):
        yol = sk.yol(soru_id, self.kok)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(f"# Soru {soru_id}\n- soran: uye@nove.group (rol: kurul)\n- zaman: {OGLEN.isoformat()}\n"
                       f"- soru: {metin}\n- bütçe: 5,00 USD\n- durum: {durum}\n", encoding="utf-8")
        return soru_id

    def yonlendir(self, soru_id, **kw):
        return dagitici.yonlendir(self.kok, soru_id, haiku=self.haiku, **kw)

    def kayit(self, soru_id):
        return sk.yol(soru_id, self.kok).read_text(encoding="utf-8")

    def kuyruk(self, takim):
        return ayar.durum_oku(takim, self.kok).get("kuyruk") or []


class AnahtarKelimeTesti(Kurulum):
    def test_tek_en_yuksek_skor_llm_cagirmadan_yonlendirir(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        sonuc = self.yonlendir(sid)
        self.haiku.assert_not_called()
        self.assertEqual(sonuc["danisman"], "finans")
        metin = self.kayit(sid)
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "danışman"), "finans")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "yöntem"), "anahtar kelime")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "eşleşen ifadeler"), "bütçe, sapma")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "güven"), "%86")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "öneri"), "okr")
        self.assertEqual(sk.alan(metin, "durum"), "danışmanda")

    def test_kuyruga_s_maddesi_soru_metniyle_yazilir(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        self.yonlendir(sid)
        self.assertEqual(self.kuyruk("finans"), [{"id": f"s-{sid}", "durum": "bekliyor",
                                                  "not": "Q3 bütçe sapmasının ana nedenleri neler?"}])
        self.assertEqual(self.kuyruk("okr"), [], "çoklu danışman yok — öneri yalnız kayda yazılır")

    def test_turkce_buyuk_harf_ve_ek_eslesir(self):
        """'İADE' → 'iade', 'Şikâyetlerin' → 'şikâyet' ile başlar."""
        sid = self.soru("İADE oranı ve Şikâyetlerin dağılımı nasıl?")
        self.assertEqual(self.yonlendir(sid)["danisman"], "kalite")

    def test_kelimenin_ortasi_eslesmez(self):
        """'sokr' içinde 'okr' geçer ama kelime başı değil."""
        sid = self.soru("Bu sokrates meselesini kim çözer acaba?")
        self.yonlendir(sid)
        self.haiku.assert_called_once()

    def test_guven_ust_siniri_96(self):
        sid = self.soru("bütçe nakit maliyet sapma raporu hazır mı?")
        self.yonlendir(sid)
        self.assertEqual(sk.bolum_alani(self.kayit(sid), "## Dağıtım", "güven"), "%96")


class HaikuTesti(Kurulum):
    def test_eslesme_yoksa_haiku_secer(self):
        sid = self.soru("Hastalar randevu sürecinden memnun mu?")
        sonuc = self.yonlendir(sid)
        self.assertEqual(sonuc["danisman"], "kalite")
        metin = self.kayit(sid)
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "yöntem"), "Haiku — tablo eşleşmedi")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "güven"), "Haiku")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "gerekçe"), "müşteri deneyimi")
        self.assertEqual(sk.bolum_alani(metin, "## Dağıtım", "maliyet"), "0.012 USD")

    def test_beraberlikte_haiku_ve_yalniz_aktif_danismanlar_gider(self):
        self.haiku.return_value = {"danisman": "okr", "gerekce": "hedef sapması", "oneri": "finans", "maliyet": 0.01}
        sid = self.soru("Bu çeyrekteki sapma neden büyüdü?")
        self.yonlendir(sid)
        soru, danismanlar = self.haiku.call_args[0]
        self.assertEqual(soru, "Bu çeyrekteki sapma neden büyüdü?")
        self.assertEqual(sorted(d["takim"] for d in danismanlar), ["finans", "kalite", "okr"])
        self.assertEqual(sk.bolum_alani(self.kayit(sid), "## Dağıtım", "yöntem"), "Haiku — beraberlik")
        self.assertEqual(self.kuyruk("okr")[0]["id"], f"s-{sid}")

    def test_haiku_listede_olmayan_ad_donerse_yonlendirilemedi(self):
        for i, yanit in enumerate(({"danisman": "raporlama", "gerekce": "x", "oneri": None, "maliyet": 0.01},
                      {"danisman": "pazarlama", "gerekce": "x", "oneri": None, "maliyet": 0.01},
                      {"hata": "JSON bozuk", "maliyet": 0.01})):
            with self.subTest(yanit=yanit):
                self.haiku.return_value = yanit
                sid = self.soru("Hastalar randevu sürecinden memnun mu?", soru_id=f"20261012-1200-{i}xyz")
                sonuc = self.yonlendir(sid)
                self.assertIsNone(sonuc["danisman"])
                metin = self.kayit(sid)
                self.assertEqual(sk.alan(metin, "durum"), "yönlendirilemedi")
                self.assertTrue(sk.bolum_alani(metin, "## Dağıtım", "sebep"))
                for t in ("finans", "okr", "kalite"):
                    self.assertEqual(self.kuyruk(t), [], "tahminle gönderilmez")

    def test_aktif_danisman_yoksa_haiku_cagrilmaz(self):
        for t in ("finans", "okr", "kalite"):
            (self.kok / "takimlar" / t / "takim.md").write_text(f"# {t}\n", encoding="utf-8")
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        sonuc = self.yonlendir(sid)
        self.haiku.assert_not_called()
        self.assertIsNone(sonuc["danisman"])
        self.assertIn("aktif danışman yok", sk.bolum_alani(self.kayit(sid), "## Dağıtım", "sebep"))


class KuruVeTekrarTesti(Kurulum):
    def test_kuru_hicbir_sey_yazmaz_haikuya_sormaz(self):
        sid = self.soru("Hastalar randevu sürecinden memnun mu?")
        once = self.kayit(sid)
        sonuc = self.yonlendir(sid, kuru=True)
        self.haiku.assert_not_called()
        self.assertEqual(sonuc["yontem"], "Haiku — tablo eşleşmedi")
        self.assertEqual(self.kayit(sid), once)

    def test_yonlendirilmis_soru_yeniden_yonlendirilmez(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        self.yonlendir(sid)
        self.assertIsNone(self.yonlendir(sid))
        self.assertEqual(self.kayit(sid).count("## Dağıtım"), 1)


class BekleyenSorularTesti(Kurulum):
    def test_yalniz_alindi_durumundakiler(self):
        a = self.soru("Q3 bütçe sapmasının ana nedenleri neler?", "20261012-1200-aaaa")
        self.soru("Q3 bütçe sapmasının ana nedenleri neler?", "20261012-1201-bbbb", durum="danışmanda")
        self.assertEqual(dagitici.yonlendirilecek_sorular(self.kok), [a])

    def test_mesai_disinda_yonlendirme_yok(self):
        self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        sonuc = dagitici.sorulari_isle(self.kok, simdi=OGLEN.replace(hour=21), haiku=self.haiku)
        self.assertEqual(sonuc, [])
        self.assertEqual(self.kuyruk("finans"), [])

    def test_mesaide_bekleyenler_yonlendirilir(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        sonuc = dagitici.sorulari_isle(self.kok, simdi=OGLEN, haiku=self.haiku)
        self.assertEqual([(s["soru_id"], s["danisman"]) for s in sonuc], [(sid, "finans")])


class CakismaTesti(Kurulum):
    def test_birden_fazla_danismanda_gecen_kelimeler(self):
        self.assertEqual(dagitici.cakisma(self.kok), {"sapma": ["finans", "okr"]})

    def test_buyuk_kucuk_harf_farki_cakismayi_gizlemez(self):
        _takim(self.kok, "satis-muduru", ["iade", "satış"])
        self.assertEqual(dagitici.cakisma(self.kok)["iade"], ["kalite", "satis-muduru"])


if __name__ == "__main__":
    unittest.main()


class DagitDongusuTesti(Kurulum):
    def test_dagit_once_sorulari_yonlendirir_sonra_danismani_kosturur(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        with mock.patch.object(dagitici, "haiku_sinifla", self.haiku), \
             mock.patch.object(dagitici, "_kostur") as kostur:
            sonuc = dagitici.dagit(self.kok, simdi=OGLEN)
        self.assertEqual([s["soru_id"] for s in sonuc["sorular"]], [sid])
        kostur.assert_called_once_with(self.kok, "finans")

    def test_kuru_dagit_soru_kaydina_dokunmaz(self):
        sid = self.soru("Q3 bütçe sapmasının ana nedenleri neler?")
        once = self.kayit(sid)
        with mock.patch.object(dagitici, "_kostur") as kostur:
            sonuc = dagitici.dagit(self.kok, simdi=OGLEN, kuru=True)
        self.assertEqual(sonuc["sorular"][0]["danisman"], "finans")
        self.assertEqual(self.kayit(sid), once)
        kostur.assert_not_called()


class CakismaKomutuTesti(Kurulum):
    def test_cakisma_komutu_listeler_ve_cakisma_varsa_1_doner(self):
        with mock.patch.object(dagitici, "KOK", self.kok), mock.patch("builtins.print") as yaz:
            kod = dagitici.main(["--cakisma"])
        self.assertEqual(kod, 1)
        self.assertIn("sapma", " ".join(str(c) for c in yaz.call_args_list))
