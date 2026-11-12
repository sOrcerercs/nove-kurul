#!/usr/bin/env python3
"""Kurul paneli — soketsiz uygulama katmanı (`Uygulama`): giriş, soru, durum ve Yanıt defteri uçları.

Hat kuralları (günlük hak, tekrar, maskeleme, mesai, bütçe, rol) yalnız `soru_kapisi.yeni`'de; burada soru metni
kırpılmaz, sayılmaz, maskelenmez. Soran yalnız oturumdan gelir. Belirteç ve şifre hiçbir yere yazılmaz.
"""
import argparse
import getpass
import json
import os
import sys
import threading
from functools import partial
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import panel_defter  # noqa: E402
import panel_kimlik  # noqa: E402
import soru_kapisi  # noqa: E402

GOVDE_SINIRI = 16 * 1024
KOK = Path(__file__).resolve().parent.parent
PANEL = KOK / "panel"


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


class Ilerletici:
    """Açık soru varken hattı ilerleten tek arka plan iş parçacığı: adımlar yalnız burada koşar."""

    def __init__(self, kok, adim=None, aralik_sn=60, kilit_dolu=ayar.kosu_suruyor, acik=panel_defter.acik_sorular):
        self.kok = kok
        if adim is None:
            import dagitici
            adim = dagitici.dagit
        self._adim, self._aralik, self._kilit_dolu, self._acik = adim, aralik_sn, kilit_dolu, acik
        self._olay = threading.Event()
        self._dur = False
        self._is = None

    def tur(self):
        if not self._acik(self.kok):
            return "bos"
        if self._kilit_dolu(self.kok):
            return "kilit"
        try:
            self._adim(self.kok)
        except Exception as e:  # ayrıntı loga girmez; yalnız tür
            print(f"panel: ilerletici adımı başarısız: {type(e).__name__}", file=sys.stderr)
            return "hata"
        return "adim"

    def _dongu(self):
        while not self._dur:
            self._olay.clear()  # tur sırasında gelen tetik kaybolmaz: clear tur'dan önce
            sonuc = self.tur()
            if self._dur:
                break
            self._olay.wait(None if sonuc == "bos" else self._aralik)

    def baslat(self):
        if self._is is None:
            self._is = threading.Thread(target=self._dongu, name="ilerletici", daemon=True)
            self._is.start()

    def tetikle(self):
        self._olay.set()

    def durdur(self):
        self._dur = True
        self._olay.set()
        if self._is is not None:
            self._is.join(timeout=5)


class Sunucu(SimpleHTTPRequestHandler):
    """İnce HTTP adaptörü: /api/ → Uygulama.istek; geri kalanı panel/ altından statik."""

    def __init__(self, *a, uygulama=None, **kw):
        self.uygulama = uygulama
        super().__init__(*a, directory=str(PANEL), **kw)

    def _api(self, yontem):
        try:
            uzunluk = max(0, int(self.headers.get("Content-Length") or 0))
        except ValueError:
            uzunluk = 0
        govde = self.rfile.read(min(uzunluk, GOVDE_SINIRI + 1)) if yontem == "POST" else b""
        c = cookies.SimpleCookie()
        try:
            c.load(self.headers.get("Cookie") or "")
        except cookies.CookieError:
            pass
        m = c.get(panel_kimlik.CEREZ_ADI)
        kod, d, ek = self.uygulama.istek(yontem, self.path, govde, m.value if m else None, self.client_address[0])
        ham = json.dumps(d, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(ham)))
        self.send_header("Cache-Control", "no-store")
        for ad, deger in ek:
            self.send_header(ad, deger)
        self.end_headers()
        self.wfile.write(ham)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._api("GET")
        if urlsplit(self.path).path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/api/"):
            return self.send_error(405)
        if urlsplit(self.path).path == "/":
            self.path = "/index.html"
        return super().do_HEAD()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._api("POST")
        return self.send_error(405)

    def do_PUT(self):
        self.send_error(405)

    do_DELETE = do_PATCH = do_PUT


def yakala(uygulama):
    """ThreadingHTTPServer'a verilecek, uygulamaya bağlı işleyici sınıfı."""
    return partial(Sunucu, uygulama=uygulama)


def _kullanici_ekle(eposta, ad):
    if os.environ.get("CLAUDECODE"):
        print("panel: bu komutu Kağan kendi terminalinde çalıştırır", file=sys.stderr)
        return 2
    s1 = getpass.getpass("Şifre: ")
    s2 = getpass.getpass("Şifre (tekrar): ")
    if s1 != s2:
        print("panel: şifreler uyuşmuyor", file=sys.stderr)
        return 1
    try:
        panel_kimlik.kullanici_ekle(KOK, eposta, ad, s1)
    except ValueError as e:
        print(f"panel: {e}", file=sys.stderr)
        return 1
    print(f"panel: {eposta} eklendi")
    if eposta.strip().lower() not in soru_kapisi.roller(KOK):
        print("panel: uyarı: rolü yok — `deploy/roller.json`'a eklenene kadar giremez", file=sys.stderr)
    return 0


def main(argv=None):
    a = argparse.ArgumentParser(description="Nove Kurul Ofisi paneli (yalnız 127.0.0.1)")
    a.add_argument("--port", type=int, default=8770)
    a.add_argument("--ilerletme-yok", action="store_true")
    a.add_argument("--https-arkasinda", action="store_true")
    a.add_argument("--kullanici-ekle", metavar="EPOSTA")
    a.add_argument("--ad", default="")
    arg = a.parse_args(argv)
    if arg.kullanici_ekle:
        return _kullanici_ekle(arg.kullanici_ekle, arg.ad or arg.kullanici_ekle)
    il = None if arg.ilerletme_yok else Ilerletici(KOK)
    uyg = Uygulama(KOK, ilerletici=il, https=arg.https_arkasinda)
    try:
        sunucu = ThreadingHTTPServer(("127.0.0.1", arg.port), yakala(uyg))
    except OSError:
        print(f"panel: port {arg.port} dolu (`bin/sahne.py` de 8770 kullanır)", file=sys.stderr)
        return 1
    print(f"panel: http://127.0.0.1:{arg.port} — ilerletme {'kapalı' if il is None else 'açık'}")
    if not (KOK / "deploy" / "kullanicilar.json").exists():
        print('panel: kullanıcı yok; eklemek için: python3 bin/panel.py --kullanici-ekle <eposta> --ad "<ad>"')
    if il is not None:
        il.baslat()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if il is not None:
            il.durdur()
        sunucu.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
