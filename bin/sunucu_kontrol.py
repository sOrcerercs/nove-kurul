#!/usr/bin/env python3
"""Sunucu kurulum kontrolü — Docker konteynerinde kurulumun doğru olduğunu doğrular.

Denetler: `.env` (var, izin 600), zorunlu anahtarlar, posta anahtarları, `claude` (yalnız `--version`),
Denetçi anahtarı, saat dilimi, depo yazılabilirliği, dosya sahipliği, `deploy/roller.json` ve
`deploy/kullanicilar.json`; `--db` ile salt okunur veritabanı bağlantıları (`SELECT 1`).

Yalnız okur, değer basmaz (çıktıda yalnız anahtar adları, sayılar ve sonuçlar; hata iletilerinde yalnız
istisna sınıfı), `claude`'a istek atmaz. Anahtarlar yalnız `.env`'den okunur, `os.environ`'dan değil.

Kullanım:
  docker compose … exec panel python3 bin/sunucu_kontrol.py [--db] [--tasima-oncesi]

Çıkış: 1 en az bir `hata` varsa, yoksa 0; bilinmeyen bayrak 2.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import kalite_veri  # noqa: E402
import rapor_postasi  # noqa: E402

KOK = ayar.KOK
ZORUNLU = ("ANTHROPIC_API_KEY",)
DENETCI_ANAHTARLARI = ("NVIDIA_API_KEY", "OPENAI_API_KEY")
DB_OKUYUCULAR = {"kalite": "QA_READONLY_URL", "okr": "OKR_READONLY_URL"}
DURUM_YOLLARI = ("yanitlar", "sirket-log", "deploy", "formlar/onayli", "takimlar")
YEREL_ADRESLER = ("localhost", "127.0.0.1", "::1")
ETIKETLER = {"tamam": "TAMAM", "uyari": "UYARI", "hata": "HATA ", "bilgi": "BİLGİ"}


def _sonuc(ad, durum, ileti):
    return {"ad": ad, "durum": durum, "ileti": ileti}


def _liste(deger):
    if isinstance(deger, list):
        return [d for d in deger if d]
    return [deger] if deger else []


def _env_dosyasi(kok):
    yol = Path(kok) / ".env"
    try:
        izin = stat.S_IMODE(yol.stat().st_mode)
    except OSError:
        return _sonuc("env-dosyasi", "hata", "yok")
    if izin != 0o600:
        return _sonuc("env-dosyasi", "hata", "izin %s (600 olmalı)" % format(izin, "o"))
    return _sonuc("env-dosyasi", "tamam", "var, izin 600")


def _zorunlu(kok, env):
    gerekli = list(ZORUNLU)
    for takim in ayar.kurulu_takimlar(kok):
        for ad in _liste((ayar.takim_bilgisi(takim, kok) or {}).get("gerekli_anahtarlar")):
            if ad not in gerekli:
                gerekli.append(ad)
    eksik = [a for a in gerekli if not env.get(a)]
    if eksik:
        return _sonuc("zorunlu-anahtarlar", "hata", "eksik: " + ", ".join(eksik))
    return _sonuc("zorunlu-anahtarlar", "tamam", "%d anahtar dolu" % len(gerekli))


def _posta(env):
    eksik = [a for a in rapor_postasi.GEREKLI_ANAHTARLAR if not env.get(a)]
    if eksik:
        return _sonuc("posta-anahtarlari", "bilgi", "isteğe bağlı; eksik: " + ", ".join(eksik))
    return _sonuc("posta-anahtarlari", "tamam", "hepsi dolu")


def _claude(calistir):
    try:
        sonuc = calistir(["claude", "--version"], capture_output=True, text=True, timeout=30)
    except Exception as e:  # noqa: BLE001 — iletiye yalnız sınıf adı
        return _sonuc("claude", "hata", type(e).__name__)
    if sonuc.returncode != 0:
        return _sonuc("claude", "hata", "dönüş kodu %s" % sonuc.returncode)
    return _sonuc("claude", "tamam", "çalışıyor")


def _denetci(env):
    if any(env.get(a) for a in DENETCI_ANAHTARLARI):
        return _sonuc("denetci", "tamam", "ayrı aile anahtarı var")
    return _sonuc("denetci", "uyari", "Denetçi geçici Opus yedeğine düşer (aynı aile)")


def _saat_dilimi(yerel_fark):
    try:
        from zoneinfo import ZoneInfo
        beklenen = datetime.now(ZoneInfo("Europe/Istanbul")).utcoffset()
        yerel = yerel_fark if yerel_fark is not None else datetime.now().astimezone().utcoffset()
    except Exception as e:  # noqa: BLE001
        return _sonuc("saat-dilimi", "hata", type(e).__name__)
    if yerel != beklenen:
        return _sonuc("saat-dilimi", "hata", "yerel saat İstanbul değil (fark %s)" % yerel)
    return _sonuc("saat-dilimi", "tamam", "Europe/Istanbul")


def _var_olan_yollar(kok):
    return [(ad, Path(kok) / ad) for ad in DURUM_YOLLARI if (Path(kok) / ad).exists()]


def _depo_yazilabilir(kok):
    yazilamayan = []
    if not os.access(kok, os.W_OK):
        yazilamayan.append("kök")
    for ad, yol in _var_olan_yollar(kok):
        if not os.access(yol, os.W_OK):
            yazilamayan.append(ad)
    if yazilamayan:
        return _sonuc("depo-yazilabilir", "hata", "yazılamıyor: " + ", ".join(yazilamayan))
    return _sonuc("depo-yazilabilir", "tamam", "yazılabilir")


def _sahiplik(kok, euid):
    euid = os.geteuid() if euid is None else euid
    if euid == 0:
        return _sonuc("sahiplik", "hata", "root olarak koşuyor")
    baskalari = {}

    def bak(yol, etiket):
        try:
            if yol.lstat().st_uid != euid:
                baskalari[etiket] = baskalari.get(etiket, 0) + 1
        except OSError:
            pass

    bak(Path(kok), "kök")
    if (Path(kok) / ".env").exists():
        bak(Path(kok) / ".env", ".env")
    for ad, yol in _var_olan_yollar(kok):
        bak(yol, ad)
        if yol.is_dir():
            try:
                cocuklar = list(yol.iterdir())
            except OSError:
                cocuklar = []
            for c in cocuklar:
                bak(c, ad)
    if baskalari:
        toplam = sum(baskalari.values())
        return _sonuc("sahiplik", "hata", "%d yol başka kullanıcıya ait (%s)" % (toplam, ", ".join(sorted(baskalari))))
    return _sonuc("sahiplik", "tamam", "yollar bu kullanıcıya ait")


def _json_sozluk(kok, ad, tasima_oncesi):
    yol = Path(kok) / "deploy" / (ad + ".json")
    if not yol.is_file():
        if tasima_oncesi:
            return _sonuc(ad, "uyari", "taşımadan sonra gelir")
        return _sonuc(ad, "hata", "deploy/%s.json yok" % ad)
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _sonuc(ad, "hata", "deploy/%s.json okunamadı ya da bozuk" % ad)
    if not isinstance(veri, dict):
        return _sonuc(ad, "hata", "deploy/%s.json sözlük değil" % ad)
    return _sonuc(ad, "tamam", "%d kayıt" % len(veri))


def _db(kok, env, baglan):
    sonuclar = []
    for takim in ayar.kurulu_takimlar(kok):
        anahtar = DB_OKUYUCULAR.get(takim)
        if not anahtar:
            continue
        ad = "db-" + takim
        url = env.get(anahtar)
        if not url:
            sonuclar.append(_sonuc(ad, "bilgi", "atlandı"))
            continue
        try:
            baglanti = kalite_veri.baglanti_ac(url, baglan)
            try:
                with baglanti.cursor() as imlec:
                    imlec.execute("SELECT 1")
            finally:
                baglanti.close()
        except Exception as e:  # noqa: BLE001 — URL ve parola sızmasın: yalnız sınıf adı
            ileti = type(e).__name__
            try:
                makine = urlparse(url).hostname
            except ValueError:
                makine = None
            if makine in YEREL_ADRESLER:
                ileti += "; adres localhost — konteynerden ulaşılmaz"
            sonuclar.append(_sonuc(ad, "hata", ileti))
            continue
        sonuclar.append(_sonuc(ad, "tamam", "bağlandı, SELECT 1"))
    return sonuclar


def kontroller(kok, db=False, tasima_oncesi=False, calistir=subprocess.run, baglan=None, euid=None,
               yerel_fark=None):
    """Kontrol sonuçları: `{"ad", "durum", "ileti"}` listesi. İstisna sızdırmaz, hiçbir şey yazmaz."""
    kok = Path(kok)
    adimlar = []
    try:
        env = ayar.env_yukle(kok / ".env")
    except Exception:  # noqa: BLE001
        env = {}
    adimlar.append(("env-dosyasi", lambda: _env_dosyasi(kok)))
    adimlar.append(("zorunlu-anahtarlar", lambda: _zorunlu(kok, env)))
    adimlar.append(("posta-anahtarlari", lambda: _posta(env)))
    adimlar.append(("claude", lambda: _claude(calistir)))
    adimlar.append(("denetci", lambda: _denetci(env)))
    adimlar.append(("saat-dilimi", lambda: _saat_dilimi(yerel_fark)))
    adimlar.append(("depo-yazilabilir", lambda: _depo_yazilabilir(kok)))
    adimlar.append(("sahiplik", lambda: _sahiplik(kok, euid)))
    adimlar.append(("roller", lambda: _json_sozluk(kok, "roller", tasima_oncesi)))
    adimlar.append(("kullanicilar", lambda: _json_sozluk(kok, "kullanicilar", tasima_oncesi)))
    sonuclar = []
    for ad, adim in adimlar:
        try:
            sonuclar.append(adim())
        except Exception as e:  # noqa: BLE001
            sonuclar.append(_sonuc(ad, "hata", type(e).__name__))
    if db:
        try:
            sonuclar.extend(_db(kok, env, baglan))
        except Exception as e:  # noqa: BLE001
            sonuclar.append(_sonuc("db", "hata", type(e).__name__))
    return sonuclar


def bas(kok, sonuclar):
    print("sunucu kontrolü — %s" % kok)
    for s in sonuclar:
        print("  [%s] %s — %s" % (ETIKETLER[s["durum"]], s["ad"], s["ileti"]))
    hata = sum(1 for s in sonuclar if s["durum"] == "hata")
    uyari = sum(1 for s in sonuclar if s["durum"] == "uyari")
    print("sonuç: %d hata, %d uyarı" % (hata, uyari))


def main(argv=None, kok=None, **enjekte):
    argv = list(sys.argv[1:] if argv is None else argv)
    bilinen = {"--db", "--tasima-oncesi"}
    bilinmeyen = [a for a in argv if a not in bilinen]
    if bilinmeyen:
        print("kullanım: sunucu_kontrol.py [--db] [--tasima-oncesi]", file=sys.stderr)
        return 2
    kok = Path(kok or KOK)
    sonuclar = kontroller(kok, db="--db" in argv, tasima_oncesi="--tasima-oncesi" in argv, **enjekte)
    bas(kok, sonuclar)
    return 1 if any(s["durum"] == "hata" for s in sonuclar) else 0


if __name__ == "__main__":
    sys.exit(main())
