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
    TEMIZ = {"karar": "kabul", "gerekce": "temiz", "ihlal_edilen_kural": None}

    def test_nim_anahtari_varsa_openai_cagrilmaz(self):
        with mock.patch.object(bekci, "nim_sor", return_value=self.TEMIZ) as n, \
             mock.patch.object(bekci, "openai_sor") as o, \
             mock.patch.object(bekci, "haiku_sor") as h:
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "nvapi-x", "OPENAI_API_KEY": "sk-y"}, "istem")
        n.assert_called_once()
        o.assert_not_called()
        h.assert_not_called()
        self.assertEqual(karar["gerekce"], "temiz")

    def test_nim_atlandi_verirse_openaiye_duser(self):
        atlandi = {"karar": "atlandi", "gerekce": "nim 404", "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "nim_sor", return_value=atlandi), \
             mock.patch.object(bekci, "openai_sor", return_value=self.TEMIZ) as o, \
             mock.patch.object(bekci, "haiku_sor") as h:
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "nvapi-x", "OPENAI_API_KEY": "sk-y"}, "istem")
        o.assert_called_once()
        h.assert_not_called()
        self.assertIn("nim 404", karar["gerekce"])
        self.assertIn("openai yolu", karar["gerekce"])

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
             mock.patch.object(bekci, "haiku_sor", return_value=yedek) as h:
            karar = bekci.llm_karari({}, "istem")
        n.assert_not_called()
        o.assert_not_called()
        h.assert_called_once()
        self.assertIn(bekci.AYNI_AILE_UYARISI, karar["gerekce"])

    def test_nim_ve_openai_ikisi_de_atlarsa_haikuya_duser(self):
        atlandi = lambda g: {"karar": "atlandi", "gerekce": g, "ihlal_edilen_kural": None}
        with mock.patch.object(bekci, "nim_sor", return_value=atlandi("nim 404")), \
             mock.patch.object(bekci, "openai_sor", return_value=atlandi("openai 401")), \
             mock.patch.object(bekci, "haiku_sor",
                               return_value={"karar": "red", "gerekce": "boş", "ihlal_edilen_kural": "x"}):
            karar = bekci.llm_karari({"NVIDIA_API_KEY": "n", "OPENAI_API_KEY": "s"}, "istem")
        self.assertEqual(karar["karar"], "red")
        self.assertIn("haiku yedeği", karar["gerekce"])


if __name__ == "__main__":
    unittest.main()
