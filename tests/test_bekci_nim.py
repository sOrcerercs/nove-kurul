"""Bekçinin NVIDIA NIM yolu ve üç yollu sırası. Ağ yok, para harcamaz.

Sıra: NIM → OpenAI → Haiku. Her düşüşte gerekçe hangi yoldan geçildiğini söyler.
Sözleşmeler 2026-09-15 tarihli gerçek ölçüme dayanıyor (bkz. plan Task 3):
`response_format: json_schema` desteklenmiyor ve reasoning modelleri düşük token
bütçesinde `content` alanını BOŞ bırakıyor.

python3 -m unittest discover -s tests
"""
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402


def _yanit(govde):
    return mock.MagicMock(__enter__=mock.MagicMock(
        return_value=mock.MagicMock(read=lambda: json.dumps(govde).encode("utf-8"))),
        __exit__=mock.MagicMock(return_value=False))


def _nim_yaniti(icerik, reasoning=""):
    return _yanit({"choices": [{"message": {"content": icerik, "reasoning_content": reasoning}}]})


def _http(kod):
    return urllib.error.HTTPError("u", kod, "hata", {}, io.BytesIO(b""))


KARAR = json.dumps({"karar": "red", "gerekce": "örneklem yok", "ihlal_edilen_kural": "§2"})


class NimSorTesti(unittest.TestCase):
    def test_karari_ayristirir(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", return_value=_nim_yaniti(KARAR)):
            karar = bekci.nim_sor("nvapi-x", "istem")
        self.assertEqual(karar["karar"], "red")
        self.assertEqual(karar["ihlal_edilen_kural"], "§2")

    def test_istek_ayar_dosyasindaki_adrese_gider(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", return_value=_nim_yaniti(KARAR)) as u:
            bekci.nim_sor("nvapi-x", "istem")
        self.assertEqual(u.call_args[0][0].full_url, f"{ayar.NIM_TABANI}/chat/completions")

    def test_govdede_response_format_yok(self):
        """ÖLÇÜLDÜ: json_schema 404/503 döndürüyor ya da içeriği boşaltıyor."""
        with mock.patch.object(bekci.urllib.request, "urlopen", return_value=_nim_yaniti(KARAR)) as u:
            bekci.nim_sor("nvapi-x", "istem")
        govde = json.loads(u.call_args[0][0].data.decode("utf-8"))
        self.assertNotIn("response_format", govde)
        self.assertGreaterEqual(govde["max_tokens"], 2000, "reasoning modelleri bütçeyi yer")

    def test_anahtar_baslikta_gider_govdede_gecmez(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", return_value=_nim_yaniti(KARAR)) as u:
            bekci.nim_sor("nvapi-gizli", "istem")
        istek = u.call_args[0][0]
        self.assertEqual(istek.get_header("Authorization"), "Bearer nvapi-gizli")
        self.assertNotIn("nvapi-gizli", istek.data.decode("utf-8"))

    def test_bos_content_atlandi_dondurur(self):
        """ÖLÇÜLDÜ: model bütün bütçeyi reasoning'e harcayınca content boş gelir."""
        with mock.patch.object(bekci.urllib.request, "urlopen",
                               return_value=_nim_yaniti("", reasoning="uzun uzun düşündüm")):
            karar = bekci.nim_sor("nvapi-x", "istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertIn("reasoning", karar["gerekce"])

    def test_reasoning_icindeki_json_karar_sayilmaz(self):
        """Karar `content`'ten okunur; reasoning_content'teki taslak JSON kullanılmaz."""
        sahte = json.dumps({"karar": "kabul", "gerekce": "taslak", "ihlal_edilen_kural": None})
        with mock.patch.object(bekci.urllib.request, "urlopen",
                               return_value=_nim_yaniti("", reasoning=sahte)):
            karar = bekci.nim_sor("nvapi-x", "istem")
        self.assertEqual(karar["karar"], "atlandi")

    def test_http_hatasi_atlandi_ve_kodu_soyler(self):
        with mock.patch.object(bekci.urllib.request, "urlopen", side_effect=_http(404)):
            karar = bekci.nim_sor("nvapi-x", "istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertIn("nim 404", karar["gerekce"])


class UcYolluSiraTesti(unittest.TestCase):
    """Sıra mantığı NIM açıkken sınanır; geçici kapatma ayrı sınıfta (NimKapaliTesti)."""
    TEMIZ = {"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None}

    def setUp(self):
        yama = mock.patch.object(bekci, "NIM_ACIK", True)
        yama.start()
        self.addCleanup(yama.stop)

    def test_nim_anahtari_varsa_openai_cagrilmaz(self):
        with mock.patch.object(bekci, "nim_sor", return_value=self.TEMIZ) as n, \
             mock.patch.object(bekci, "openai_sor") as o, \
             mock.patch.object(bekci, "yedek_sor") as h:
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "nvapi-x", "OPENAI_API_KEY": "sk-y"}, "istem")
        n.assert_called_once()
        o.assert_not_called()
        h.assert_not_called()
        self.assertEqual(karar["gerekce"], "temiz")

    def test_nim_atlandi_verirse_openaiye_duser(self):
        atlandi = {"karar": "atlandi", "gerekce": "nim 404", "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "nim_sor", return_value=atlandi), \
             mock.patch.object(bekci, "openai_sor", return_value=self.TEMIZ) as o, \
             mock.patch.object(bekci, "yedek_sor") as h:
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "nvapi-x", "OPENAI_API_KEY": "sk-y"}, "istem")
        o.assert_called_once()
        h.assert_not_called()
        self.assertTrue(karar["gerekce"].startswith("nim 404 → openai yolu · "), karar["gerekce"])

    def test_nim_yoksa_dogrudan_openai(self):
        with mock.patch.object(bekci, "nim_sor") as n, \
             mock.patch.object(bekci, "openai_sor", return_value=self.TEMIZ) as o:
            bekci.llm_karari({"OPENAI_API_KEY": "sk-y"}, "istem")
        n.assert_not_called()
        o.assert_called_once()

    def test_ikisi_de_yoksa_haiku_ve_ayni_aile_uyarisi(self):
        yedek = {"karar": "kabul", "gerekce": "[bekçi aynı aileden — uyarı] temiz",
                 "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "nim_sor") as n, \
             mock.patch.object(bekci, "openai_sor") as o, \
             mock.patch.object(bekci, "yedek_sor", return_value=yedek) as h:
            karar = bekci.llm_karari({}, "istem")
        n.assert_not_called()
        o.assert_not_called()
        h.assert_called_once()
        self.assertIn(bekci.AYNI_AILE_UYARISI, karar["gerekce"])

    def test_nim_ve_openai_ikisi_de_atlarsa_haikuya_duser(self):
        atlandi = lambda g: {"karar": "atlandi", "gerekce": g, "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "nim_sor", return_value=atlandi("nim 404")), \
             mock.patch.object(bekci, "openai_sor", return_value=atlandi("openai 401")), \
             mock.patch.object(bekci, "yedek_sor",
                               return_value={"karar": "red", "gerekce": "boş", "ihlal_edilen_kural": "x"}):
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "n", "OPENAI_API_KEY": "s"}, "istem")
        self.assertEqual(karar["karar"], "red")
        self.assertIn("opus yedeği", karar["gerekce"])


class NimKapaliTesti(unittest.TestCase):
    """11.11.2026: NVIDIA hesabındaki sohbet istekleri yanıt dönmüyor; her denetim 300 sn boşa bekliyordu.
    NIM geçici kapalıyken çağrılmaz, ama düşüş sessiz değildir: gerekçe 'nim kapalı' der."""

    def test_nim_kapaliyken_cagrilmaz_ve_gerekce_soyler(self):
        yedek = {"karar": "kabul", "gerekce": "[bekçi aynı aileden — uyarı] temiz", "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "NIM_ACIK", False), \
             mock.patch.object(bekci, "nim_sor") as n, \
             mock.patch.object(bekci, "yedek_sor", return_value=yedek) as h:
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "nvapi-x"}, "istem")
        n.assert_not_called()
        h.assert_called_once()
        self.assertIn("nim kapalı", karar["gerekce"])
        self.assertIn("opus yedeği", karar["gerekce"])


class YedekZinciriTesti(unittest.TestCase):
    YEDEK = {"karar": "kabul", "gerekce": "[bekçi aynı aileden — uyarı] temiz",
             "ihlal_edilen_kural": None, "maliyet": 0.31}

    def _claude(self, result="{\"karar\":\"kabul\",\"gerekce\":\"temiz\",\"ihlal_edilen_kural\":null}",
                maliyet=0.42):
        return mock.Mock(stdout=json.dumps({"result": result, "total_cost_usd": maliyet}), returncode=0)

    def test_basari_olcutu_gerekcesi(self):
        with mock.patch.object(bekci, "NIM_ACIK", False), \
             mock.patch.object(bekci, "yedek_sor", return_value=self.YEDEK):
            karar = bekci.llm_karari({}, "istem")
        self.assertEqual(karar["gerekce"], "nim kapalı (geçici) → openai anahtarı yok → opus yedeği · "
                                           "[bekçi aynı aileden — uyarı] temiz")
        self.assertEqual(karar["maliyet"], 0.31)

    def test_nim_acik_anahtar_yok_yazilir(self):
        with mock.patch.object(bekci, "NIM_ACIK", True), \
             mock.patch.object(bekci, "yedek_sor", return_value=self.YEDEK):
            karar = bekci.llm_karari({}, "istem")
        self.assertTrue(karar["gerekce"].startswith("nim anahtarı yok → openai anahtarı yok → opus yedeği · "))

    def test_nim_kapali_anahtar_yokken_de_yazilir(self):
        temiz = {"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "NIM_ACIK", False), \
             mock.patch.object(bekci, "nim_sor") as n, \
             mock.patch.object(bekci, "yedek_sor") as y, \
             mock.patch.object(bekci, "openai_sor", return_value=temiz):
            karar = bekci.llm_karari({"OPENAI_API_KEY": "sk-y"}, "istem")
        n.assert_not_called()
        y.assert_not_called()
        self.assertEqual(karar["gerekce"], "nim kapalı (geçici) → openai yolu · temiz")

    def test_openai_401_zinciri(self):
        atlandi = {"karar": "atlandi", "gerekce": "openai 401", "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "NIM_ACIK", False), \
             mock.patch.object(bekci, "openai_sor", return_value=atlandi), \
             mock.patch.object(bekci, "yedek_sor", return_value=self.YEDEK):
            karar = bekci.llm_karari({"OPENAI_API_KEY": "sk-y"}, "istem")
        self.assertTrue(karar["gerekce"].startswith("nim kapalı (geçici) → openai 401 → opus yedeği · "))

    def test_yedek_modeli_butcesi_suresi_ayardan(self):
        with mock.patch.object(bekci.subprocess, "run", return_value=self._claude()) as r:
            karar = bekci.yedek_sor("istem")
        komut = r.call_args.args[0]
        self.assertEqual(komut[komut.index("--model") + 1], "opus")
        self.assertEqual(komut[komut.index("--max-budget-usd") + 1], "0.75")
        self.assertEqual(r.call_args.kwargs["timeout"], 240)
        self.assertEqual(karar["maliyet"], 0.42)
        self.assertIn(bekci.AYNI_AILE_UYARISI, karar["gerekce"])

    def test_model_parametresi_ezer(self):
        with mock.patch.object(bekci.subprocess, "run", return_value=self._claude()) as r:
            bekci.yedek_sor("i", model="haiku")
        komut = r.call_args.args[0]
        self.assertEqual(komut[komut.index("--model") + 1], "haiku")

    def test_yedek_zaman_asimi_atlandi_maliyet_sifir(self):
        with mock.patch.object(bekci.subprocess, "run",
                               side_effect=bekci.subprocess.TimeoutExpired("claude", 240)):
            karar = bekci.yedek_sor("istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertEqual(karar["maliyet"], ayar.BEKCI_YEDEK_BUTCESI_USD)   # kapalı kalır: tavan harcanmış sayılır
        self.assertIn("tavan harcanmış sayıldı", karar["gerekce"])

    def test_yedek_json_nesne_degilse_ya_da_result_null_ise_atlandi(self):
        for stdout in ("null", "[1]", '"x"', json.dumps({"result": None, "total_cost_usd": 0.3})):
            with mock.patch.object(bekci.subprocess, "run",
                                   return_value=mock.Mock(stdout=stdout, stderr="", returncode=0)):
                karar = bekci.yedek_sor("istem")
            self.assertEqual(karar["karar"], "atlandi", stdout)
            self.assertIn("maliyet", karar)

    def test_yedek_json_yoksa_maliyet_korunur(self):
        with mock.patch.object(bekci.subprocess, "run", return_value=self._claude("bütçe aşıldı", 0.75)):
            karar = bekci.yedek_sor("istem")
        self.assertEqual(karar["karar"], "atlandi")
        self.assertEqual(karar["maliyet"], 0.75)

    def test_yedek_reddi_uyari_notu_yuzunden_kabule_donmez(self):
        k = {"karar": "red", "gerekce": "nim kapalı (geçici) → openai anahtarı yok → opus yedeği · "
                                        "[bekçi aynı aileden — uyarı] kaynaksız sayı var",
             "ihlal_edilen_kural": "kaynak", "kontrol": None}
        self.assertEqual(bekci.kontrol_uygula(bekci.gecersiz_gerekceyi_ayikla(k))["karar"], "red")


if __name__ == "__main__":
    unittest.main()
