#!/usr/bin/env python3
"""Kurul paneli — soketsiz uygulama katmanı (`Uygulama`): giriş, soru, durum ve Yanıt defteri uçları.

Hat kuralları (günlük hak, tekrar, maskeleme, mesai, bütçe, rol) yalnız `soru_kapisi.yeni`'de; burada soru metni
kırpılmaz, sayılmaz, maskelenmez. Soran yalnız oturumdan gelir. Belirteç ve şifre hiçbir yere yazılmaz.
"""
import json
import sys
import threading
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel_defter  # noqa: E402
import panel_kimlik  # noqa: E402
import soru_kapisi  # noqa: E402

GOVDE_SINIRI = 16 * 1024


class _Hata(Exception):
    def __init__(self, kod, govde):
        super().__init__(kod)
        self.kod, self.govde = kod, govde


class Uygulama:
    def __init__(self, kok, oturumlar=None, fren=None, ilerletici=None, yeni=soru_kapisi.yeni, https=False):
        self.kok = Path(kok)
        self.oturumlar = oturumlar if oturumlar is not None else panel_kimlik.Oturumlar()
        self.fren = fren if fren is not None else panel_kimlik.DenemeFreni()
        self.ilerletici = ilerletici
        self._yeni = yeni
        self.https = https
        self._soru_kilidi = threading.Lock()

    # --- yardımcılar -------------------------------------------------------

    def _cerez(self, deger, bitis_sn):
        c = f"{panel_kimlik.CEREZ_ADI}={deger}; HttpOnly; SameSite=Strict; Path=/; Max-Age={bitis_sn}"
        return ("Set-Cookie", c + ("; Secure" if self.https else ""))

    @staticmethod
    def _json(govde):
        try:
            d = json.loads(govde.decode("utf-8")) if govde else {}
        except (ValueError, UnicodeDecodeError):
            raise _Hata(400, {"hata": "geçersiz istek"})
        if not isinstance(d, dict):
            raise _Hata(400, {"hata": "geçersiz istek"})
        return d

    def _oturum(self, cerez):
        """{"eposta", "ad", "rol"}; yoksa ya da rol artık sorabilen değilse 401. Rol her istekte okunur."""
        o = self.oturumlar.bul(cerez) if cerez else None
        rol = soru_kapisi.roller(self.kok).get(o["eposta"]) if o else None
        if o is None or rol not in soru_kapisi.SORABILEN_ROLLER:
            raise _Hata(401, {"hata": "oturum yok"})
        return {"eposta": o["eposta"], "ad": o["ad"], "rol": rol}

    @staticmethod
    def _kimlik(ad, rol):
        return {"ad": ad, "basHarf": panel_kimlik.bas_harf(ad), "rol": rol}

    # --- giriş noktası -----------------------------------------------------

    def istek(self, yontem, yol, govde=b"", cerez=None, ip="127.0.0.1"):
        try:
            return self._yonlendir(yontem, urlsplit(yol).path, govde, cerez, ip)
        except _Hata as h:
            return h.kod, h.govde, []
        except Exception as e:  # ayrıntı gövdeye girmez; stderr'e yalnız tür
            print(f"panel: beklenmeyen hata: {type(e).__name__}", file=sys.stderr)
            return 500, {"hata": "sunucu hatası"}, []

    def _yonlendir(self, yontem, yol, govde, cerez, ip):
        if len(govde) > GOVDE_SINIRI:
            raise _Hata(413, {"hata": "gövde çok büyük"})
        if not yol.startswith("/api/"):
            raise _Hata(404, {"hata": "bulunamadı"})
        parca = yol[len("/api/"):]
        sabit = {"giris": "POST", "cikis": "POST", "ben": "GET", "soru": "POST", "yanitlar": "GET"}
        if parca in sabit:
            if yontem != sabit[parca]:
                raise _Hata(405, {"hata": "yöntem desteklenmiyor"})
            if parca == "giris":
                return self._giris(govde, ip)
            o = self._oturum(cerez)
            if parca == "ben":
                return 200, self._kimlik(o["ad"], o["rol"]), []
            if parca == "cikis":
                self.oturumlar.kapat(cerez)
                return 200, {}, [self._cerez("", 0)]
            if parca == "soru":
                return self._soru(o, govde)
            return 200, panel_defter.liste(self.kok, o["eposta"], o["rol"]), []
        if parca.startswith("sorular/"):
            if yontem != "GET":
                raise _Hata(405, {"hata": "yöntem desteklenmiyor"})
            o = self._oturum(cerez)
            d = panel_defter.durum(self.kok, unquote(parca[len("sorular/"):]), o["eposta"], o["rol"])
            if d is None:
                raise _Hata(404, {"hata": "bulunamadı"})
            return 200, d, []
        raise _Hata(404, {"hata": "bulunamadı"})

    # --- uçlar -------------------------------------------------------------

    def _giris(self, govde, ip):
        d = self._json(govde)
        eposta, sifre = d.get("eposta"), d.get("sifre")
        if not isinstance(eposta, str) or not isinstance(sifre, str):
            raise _Hata(400, {"hata": "e-posta ve şifre gerekli"})
        if self.fren.engelli_mi(eposta, ip):
            raise _Hata(429, {"hata": "çok fazla deneme — biraz sonra tekrar deneyin"})
        k = panel_kimlik.dogrula(self.kok, eposta, sifre)
        if k is None:
            self.fren.basarisiz(eposta, ip)
            raise _Hata(401, {"hata": "e-posta ya da şifre yanlış"})
        self.fren.basarili(eposta)
        belirtec = self.oturumlar.ac(k["eposta"], k["ad"])
        return 200, self._kimlik(k["ad"], k["rol"]), [self._cerez(belirtec, panel_kimlik.OTURUM_SURESI_SN)]

    def _soru(self, o, govde):
        soru = self._json(govde).get("soru")
        if not isinstance(soru, str) or not soru.strip():
            raise _Hata(400, {"hata": "soru gerekli"})
        try:
            soru.encode("utf-8")
        except UnicodeEncodeError:  # geçerlilik denetimi; metin yine olduğu gibi geçer
            raise _Hata(400, {"hata": "soru geçersiz karakter içeriyor"})
        with self._soru_kilidi:
            s = self._yeni(self.kok, soru, o["eposta"])
        if s["sonuc"] == "reddedildi":
            return 200, {"durum": "reddedildi", "sebep": s["sebep"]}, []
        d = panel_defter.durum(self.kok, s["soru_id"], o["eposta"], o["rol"])
        if d is None:
            d = {"soru_id": s["soru_id"], "durum": "arastiriliyor"}
        if s["sonuc"] == "var":
            d = dict(d, bilgi=s["sebep"])
        elif self.ilerletici is not None:
            self.ilerletici.tetikle()
        return 200, d, []
