"""Tebrik Danışmanı — sürücü: günde tek posta, geç/kaçan notu, adsız özet, kuru koşu.

Yapay zekâ yok; kurallı betik. Her gün 08:55 Europe/Istanbul (launchd, uyanınca geç de koşabilir).
Sıra: bugün gönderildiyse dur → ANAYASA + alıcı kapısı → tablo → tebrikler ve görseller → notlar →
gönder, **sonra** kaydı yaz → adsız özet. Kayıtlar `sirket-log/tebrik/` altında (git dışı, ad içerir);
ekrana ad, adres, anahtar basılmaz. Kuru koşunun kaydı `<gun>.kuru.json`'dır; gerçek koşunun kararları
(bugün gönderildi mi, dün kaçan, ilk koşu) yalnız `<gun>.json`'a bakar.

Ortam anahtarları (yalnız adlar; değerler `.env`'de): TEBRIK_SMTP_SUNUCU, TEBRIK_SMTP_PORT,
TEBRIK_SMTP_KULLANICI, TEBRIK_SMTP_SIFRE, TEBRIK_ALICI, TEBRIK_DRIVE_DOSYA, TEBRIK_DRIVE_ANAHTAR.

Kullanım: python3 bin/tebrik_postasi.py [--kuru [--gun YYYY-MM-DD]]
Çıkış: 0 tamam · 1 hata (Drive, SMTP, kayıt) · 2 kullanım · 3 ANAYASA kapısı kapalı ya da alıcı geçersiz
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import tebrik_drive  # noqa: E402
import tebrik_gorsel  # noqa: E402
import tebrik_posta  # noqa: E402
import tebrik_takvim  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
KAYIT_KLASORU = KOK / "sirket-log" / "tebrik"
IST = ZoneInfo("Europe/Istanbul")
GEC_SAAT = time(9, 15)
KURU_SAAT = time(8, 55)
KILIT_ADI = ".kilit"
KILIT_BAYAT_SN = 30 * 60
KOSTU_DURUMLARI = ("gonderildi", "bos")  # dün bu durumdaysa kaçan yok; hata/kuru kaçırmış sayılır
_GUN_KAYDI = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")  # *.kuru.json eşleşmez


def istanbul_gunu(simdi: datetime) -> date:
    return simdi.astimezone(IST).date()


def ayin_ilk_is_gunu_mu(gun: date) -> bool:
    """Ayın ilk Pazartesi–Cuma günü mü (resmî tatil hesaba katılmaz)."""
    if gun.weekday() >= 5:
        return False
    return all(date(gun.year, gun.month, g).weekday() >= 5 for g in range(1, gun.day))


def _onceki_kayit_var_mi(klasor: Path, gun: date) -> bool:
    """`gun`den önceki herhangi bir gün kaydı var mı (ilk koşuda kaçan notu yazılmaz — R11)."""
    if not klasor.is_dir():
        return False
    return any(_GUN_KAYDI.match(y.name) and y.stem < gun.isoformat() for y in klasor.iterdir())


def _kilit_al(yol: Path) -> bool:
    """O_EXCL kilit; 30 dakikadan eski kilit bayat sayılıp devralınır."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            os.close(os.open(str(yol), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            return True
        except FileExistsError:
            try:
                bayat = datetime.now().timestamp() - yol.stat().st_mtime > KILIT_BAYAT_SN
            except FileNotFoundError:
                continue  # bu arada bırakıldı; yeniden dene
            if not bayat:
                return False
            try:
                yol.unlink()
            except FileNotFoundError:
                pass
    return False


def _kayit_oku(yol: Path):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _yaz_json(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gecici.replace(yol)


def _kapi_acik_mi(ortam: dict, kok: Path):
    """(açık mı, sebep). ANAYASA metni NFC'ye çevrilir (R8)."""
    try:
        metin = (kok / "ANAYASA.md").read_text(encoding="utf-8")
    except OSError:
        return False, "ANAYASA.md okunamadı"
    if not tebrik_posta.istisna_var(unicodedata.normalize("NFC", metin)):
        return False, f"ANAYASA'da '{tebrik_posta.ISTISNA_BASLIGI}' başlığı yok"
    try:
        tebrik_posta.alici_dogrula(ortam.get("TEBRIK_ALICI", ""))
    except ValueError as hata:
        return False, str(hata)
    return True, ""


def _bayramlar(kok: Path) -> list:
    yol = kok / "tebrik" / "bayramlar.json"
    if not yol.exists():
        return []
    return json.loads(yol.read_text(encoding="utf-8"))


def _tebrik_adi(t: dict) -> str:
    return t["ad"] if t["tur"] != "bayram" else t["bayram"]["ad"]


def _sablon_adi(t: dict) -> str:
    return t["bayram"]["sablon"] if t["tur"] == "bayram" else t["tur"]


def _gorseller(tebrikler: list, gun: date, kok: Path, klasor: Path):
    """(görsel yolları, bugünü etkileyen eksikler) — R1, R2, R3."""
    yollar, eksik, sayac = [], [], {}
    sablonlar, yazilar = kok / "tebrik" / "sablonlar", kok / "tebrik" / "yazi-tipleri"
    for t in tebrikler:
        ad = tebrik_posta.ek_adi(gun, t)
        sayac[ad] = sayac.get(ad, 0) + 1
        if sayac[ad] > 1:  # aynı gün aynı ad (ya da aynı ASCII kısaltması): -2, -3 eki
            ad = f"{ad[:-len('.png')]}-{sayac[ad]}.png"
        try:
            yol = tebrik_gorsel.gorsel_uret(t, sablonlar, klasor / ad, yazilar)
        except FileNotFoundError:
            not_ = f"şablon yok: {_sablon_adi(t)}"
            if not_ not in eksik:
                eksik.append(not_)
            continue
        if yol is None:
            eksik.append(f"{_tebrik_adi(t)} — görsel üretilemedi: ad kutuya sığmadı")
        else:
            yollar.append(yol)
        if t["tur"] == "hos_geldin" and not t.get("unvan"):
            eksik.append(f"{t['ad']} — ünvan yok")
    return yollar, eksik


def _kayit(gun, durum, simdi, tebrikler, eksik_sayisi, gec):
    return {"gun": gun.isoformat(), "durum": durum, "zaman": simdi.astimezone(IST).isoformat(timespec="seconds"),
            "tebrik_sayisi": len(tebrikler), "eksik_sayisi": eksik_sayisi, "gec": gec,
            "adlar": [_tebrik_adi(t) for t in tebrikler]}


def _sonlandir(kayit: dict, kok: Path, kuru: bool, rc: int) -> int:
    """Günün kaydını, kuru değilse adsız özeti yazar. Kayıt yazılamazsa rc 1."""
    klasor = kok / "sirket-log" / "tebrik"
    try:
        _yaz_json(klasor / f"{kayit['gun']}{'.kuru' if kuru else ''}.json", kayit)
        if not kuru:
            onceki = _kayit_oku(klasor / "ozet.json") or {}
            ozet = {k: v for k, v in kayit.items() if k != "adlar"}
            ozet["son_gonderim"] = (kayit["gun"] if kayit["durum"] == "gonderildi"
                                    else onceki.get("son_gonderim"))
            _yaz_json(klasor / "ozet.json", ozet)
    except OSError as hata:
        print(f"tebrik: kayıt yazılamadı ({type(hata).__name__})", file=sys.stderr)
        return 1
    print(f"tebrik: {kayit['gun']} durum={kayit['durum']} tebrik={kayit['tebrik_sayisi']} "
          f"eksik={kayit['eksik_sayisi']}")
    return rc


def _yolla(mesaj, ortam: dict, gonder, kuru: bool, klasor: Path, gun: date) -> None:
    if kuru:
        klasor.mkdir(parents=True, exist_ok=True)
        (klasor / f"{gun.isoformat()}.eml").write_bytes(mesaj.as_bytes())
    else:
        gonder(mesaj, ortam)


def _hazirla(satirlar, gun, yerel, gec, kok, klasor, gun_klasoru):
    """(tebrikler, görseller, notlar, eksik sayısı)."""
    # (4) tebrikler ve görseller
    kisiler, tablo_eksikleri = tebrik_takvim.dogrula(satirlar)
    bayramlar = _bayramlar(kok)
    tebrikler = tebrik_takvim.bugunun_tebrikleri(kisiler, bayramlar, gun)
    gorseller, bugun_eksikleri = _gorseller(tebrikler, gun, kok, gun_klasoru)

    # (5) notlar
    notlar = []
    dun = gun - timedelta(days=1)
    dun_kaydi = _kayit_oku(klasor / f"{dun.isoformat()}.json") or {}
    if dun_kaydi.get("durum") not in KOSTU_DURUMLARI and _onceki_kayit_var_mi(klasor, gun):
        kacan = tebrik_takvim.bugunun_tebrikleri(kisiler, bayramlar, dun)
        if kacan:
            notlar.append("Dün kaçan tebrikler: " + ", ".join(_tebrik_adi(t) for t in kacan))
    ilk_is_gunu = ayin_ilk_is_gunu_mu(gun)
    if (gun.month == 12 and ilk_is_gunu  # R10: yalnız aralığın ilk iş günü
            and not any(str(b.get("baslangic", "")).startswith(f"{gun.year + 1}-") for b in bayramlar)):
        notlar.append("Gelecek yılın bayram tarihleri takvimde yok")
    notlar.extend(tablo_eksikleri + bugun_eksikleri if ilk_is_gunu else bugun_eksikleri)
    if gec and (tebrikler or notlar):
        notlar.insert(0, f"Geç gönderildi ({yerel.strftime('%H:%M')})")
    return tebrikler, gorseller, notlar, len(tablo_eksikleri) + len(bugun_eksikleri)


def kos(simdi: datetime, ortam: dict, kok: Path, kuru=False,
        indir=tebrik_drive.tablo_indir, gonder=tebrik_posta.gonder) -> int:
    """Aynı anda iki koşuyu kilitle önler; kilit doluysa gönderim yok, rc 0."""
    kok = Path(kok)
    kilit = kok / "sirket-log" / "tebrik" / KILIT_ADI
    if not _kilit_al(kilit):
        print("tebrik: başka bir koşu sürüyor (kilit dolu); bu koşu bir şey yapmadı")
        return 0
    try:
        return _kos(simdi, ortam, kok, kuru, indir, gonder)
    finally:
        try:
            kilit.unlink()
        except FileNotFoundError:
            pass


def _kos(simdi, ortam, kok, kuru, indir, gonder) -> int:
    gun = istanbul_gunu(simdi)
    yerel = simdi.astimezone(IST)
    klasor = kok / "sirket-log" / "tebrik"
    gun_klasoru = klasor / gun.isoformat()

    # (1) bugün gönderildiyse ikinci gönderim yok
    bugun = _kayit_oku(klasor / f"{gun.isoformat()}.json")
    if bugun and bugun.get("durum") == "gonderildi":
        print(f"tebrik: {gun.isoformat()} zaten gönderildi")
        return 0

    # (2) ANAYASA + alıcı kapısı (kuru koşu bağımsız)
    if not kuru:
        acik, sebep = _kapi_acik_mi(ortam, kok)
        if not acik:  # kapı kapalıyken kayıt yazılmaz: kapı açılınca o gün "dün kaçan" olarak bildirilir (R12)
            print(f"tebrik: gönderim yok — {sebep}", file=sys.stderr)
            return 3

    gonderen = ortam.get("TEBRIK_SMTP_KULLANICI", "")  # R4
    alici = ortam.get("TEBRIK_ALICI", "")
    gec = yerel.time() >= GEC_SAAT

    # (3) tablo
    try:
        tablo = indir(ortam, klasor / "tablo.xlsx")
        satirlar = tebrik_takvim.xlsx_oku(tablo)
    except Exception as hata:
        # RuntimeError (Drive) ve eksik sütun mesajı veri taşımaz; diğerlerinde yalnız tür adı
        sebep = (str(hata) if isinstance(hata, (RuntimeError, tebrik_takvim.EksikSutun))
                 else type(hata).__name__)
        print(f"tebrik: tablo okunamadı — {sebep}", file=sys.stderr)
        kayit = _kayit(gun, "kuru" if kuru else "hata", simdi, [], 0, gec)
        mesaj = tebrik_posta.mail_kur([], [], [f"Tebrik tablosu okunamadı ({sebep}); bugünün tebrikleri "
                                              "hazırlanamadı."], gonderen, alici, gun)
        try:
            _yolla(mesaj, ortam, gonder, kuru, gun_klasoru, gun)
        except Exception as hata2:
            print(f"tebrik: bildirim gönderilemedi — {hata2}", file=sys.stderr)
        return _sonlandir(kayit, kok, kuru, 1)

    # (4)–(5) beklenmeyen hata: yalnız tür adı yazılır (veri sızmaz), kayıt hata, rc 1 (R13c)
    try:
        tebrikler, gorseller, notlar, eksik_sayisi = _hazirla(satirlar, gun, yerel, gec, kok, klasor, gun_klasoru)
    except Exception as hata:
        tur = type(hata).__name__
        print(f"tebrik: hazırlanamadı — {tur}", file=sys.stderr)
        if not kuru:  # hiçbir tebrik sessizce kaybolmaz: alıcıya bildirim (ek yok)
            mesaj = tebrik_posta.mail_kur([], [], [f"Tebrikler hazırlanamadı ({tur}); bugünün tebrikleri "
                                                   "gönderilemedi."], gonderen, alici, gun)
            try:
                gonder(mesaj, ortam)
            except Exception as hata2:
                print(f"tebrik: bildirim gönderilemedi — {hata2}", file=sys.stderr)
        return _sonlandir(_kayit(gun, "kuru" if kuru else "hata", simdi, [], 0, gec), kok, kuru, 1)

    # (6) gönderilecek bir şey yoksa mail yok
    if not tebrikler and not notlar:
        return _sonlandir(_kayit(gun, "kuru" if kuru else "bos", simdi, [], eksik_sayisi, gec), kok, kuru, 0)

    # (7) gönder, sonra kaydı yaz
    mesaj = tebrik_posta.mail_kur(tebrikler, gorseller, notlar, gonderen, alici, gun)
    try:
        _yolla(mesaj, ortam, gonder, kuru, gun_klasoru, gun)
    except Exception as hata:
        print(f"tebrik: gönderilemedi — {hata}", file=sys.stderr)
        return _sonlandir(_kayit(gun, "kuru" if kuru else "hata", simdi, tebrikler, eksik_sayisi, gec), kok, kuru, 1)
    durum = "kuru" if kuru else "gonderildi"
    # (8) özet _sonlandir'da
    return _sonlandir(_kayit(gun, durum, simdi, tebrikler, eksik_sayisi, gec), kok, kuru, 0)


def main(argv=None) -> int:
    ayrac = argparse.ArgumentParser(description="Tebrik Danışmanı — günlük özel gün postası")
    ayrac.add_argument("--kuru", action="store_true", help="mail atmadan .eml ve PNG'leri klasöre yazar")
    ayrac.add_argument("--gun", help="YYYY-MM-DD (yalnız --kuru ile)")
    try:
        args = ayrac.parse_args(argv)
    except SystemExit as cikis:
        return 2 if cikis.code else 0
    if args.gun and not args.kuru:
        print("tebrik: --gun yalnız --kuru ile kullanılır", file=sys.stderr)
        return 2
    if args.gun:
        try:
            simdi = datetime.combine(date.fromisoformat(args.gun), KURU_SAAT, tzinfo=IST)
        except ValueError:
            print("tebrik: --gun YYYY-MM-DD olmalı", file=sys.stderr)
            return 2
    else:
        simdi = datetime.now(IST)
    ortam = ayar.ortam_yukle()
    return kos(simdi, ortam, KOK, kuru=args.kuru)


if __name__ == "__main__":
    sys.exit(main())
