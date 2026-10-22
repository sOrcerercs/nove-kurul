#!/usr/bin/env python3
"""Q&A Danışmanı — kurul sorusunun giriş ve çıkış kapısı (sirket/QA-DANISMANI.md, NOVE-KURULUM.md §2).

LLM çağırmaz, para harcamaz. Sahnede danışman gibi görünür, arkasında bu sürücü vardır.

Giriş (adım 1) — `--yeni "<soru>" --soran <e-posta>`:
  rol (`deploy/roller.json`: kurul | yonetici) → çok kısa soru → aynı soru 10 dk içinde → günlük soru hakkı
  → maskele (e-posta, telefon, TC; Denetçi'yle aynı desenler) → `gelen/<id>.json` + soru kaydı.
  Mesai dışı ya da şirket günlük bütçesi doluysa soru yine kayda girer, `not:` satırı sebebi söyler;
  İş Dağıtımcı onu uygun zamanda yönlendirir. Hiçbir soru sessizce düşmez.

Çıkış (adım 8) — `--ilet <soru-id>`:
  İki imza (son Denetçi `kabul`, ardından CEO `onay`) yoksa iletmez. Yanıtı Yanıt defterine yazar
  (`yanitlar/<id>.md`); onaylanamayan soru da gerekçesiyle deftere girer. Panelde soranın masasına
  düşmesi `panel.py`'nin işidir (Faz 5).

Kullanım:
    python3 bin/soru_kapisi.py --yeni "<soru>" --soran <e-posta> [--kuru]   # 0 açıldı/var · 1 reddedildi
    python3 bin/soru_kapisi.py --ilet <soru-id>                              # 0 iletildi · 1 iletilemez
"""
import json
import random
import re
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import bekci  # noqa: E402
import soru_kaydi  # noqa: E402
import yanit_defteri  # noqa: E402

KOK = ayar.KOK
SORABILEN_ROLLER = ("kurul", "yonetici")


class IletHatasi(Exception):
    """Yanıt kurula iletilemez; sebebi mesajda."""


# --- giriş -----------------------------------------------------------------

def roller(kok):
    """`deploy/roller.json`: {e-posta: rol}. Yoksa ya da bozuksa boş — kimse soru soramaz."""
    try:
        ham = json.loads((Path(kok) / "deploy" / "roller.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(e).strip().lower(): str(r) for e, r in ham.items()} if isinstance(ham, dict) else {}


def maskele(metin):
    """Kişisel veriyi `[e-posta]`, `[tc-no]`, `[telefon]` ile değiştirir. Desenler Denetçi'nin ön kontrolüyle aynı.
    (maskeli metin, {tür: adet}) döner; maskelenen değer hiçbir yere yazılmaz."""
    sayac = {}

    def yerine(tur):
        def degistir(eslesme):
            sayac[tur] = sayac.get(tur, 0) + 1
            return f"[{tur}]"
        return degistir

    metin = bekci.ON_KONTROL["e-posta adresi"].sub(yerine("e-posta"), metin)
    tc = yerine("tc-no")
    metin = bekci._TcDeseni.ADAY.sub(lambda e: tc(e) if bekci.tc_gecerli_mi(e.group()) else e.group(), metin)
    metin = bekci.ON_KONTROL["telefon numarası"].sub(yerine("telefon"), metin)
    return metin, {t: sayac[t] for t in ("e-posta", "telefon", "tc-no") if t in sayac}


def _tr_kucuk(metin):
    return metin.replace("İ", "i").replace("I", "ı").lower()


def _ayni_soru(a, b):
    return " ".join(_tr_kucuk(a).split()) == " ".join(_tr_kucuk(b).split())


def _soran_eposta(metin):
    return (soru_kaydi.alan(metin, "soran") or "").split(" ")[0].lower()


def _kayitlar(kok, onek=""):
    dizin = Path(kok) / "sirket-log" / "sorular"
    return sorted(dizin.glob(f"{onek}*.md")) if dizin.is_dir() else []


def _tekrar_mi(kok, soran, soru, simdi):
    """Aynı kişinin aynı sorusu son SORU_TEKRAR_DK dakikada açıldıysa onun id'si."""
    sinir = simdi - timedelta(minutes=ayar.SORU_TEKRAR_DK)
    for yol in reversed(_kayitlar(kok)):
        metin = yol.read_text(encoding="utf-8")
        try:
            zaman = datetime.fromisoformat(soru_kaydi.alan(metin, "zaman") or "")
        except ValueError:
            continue
        if zaman >= sinir and _soran_eposta(metin) == soran and _ayni_soru(soru_kaydi.alan(metin, "soru") or "", soru):
            return yol.stem
    return None


def _bugunku_soru_sayisi(kok, soran, simdi):
    return sum(1 for yol in _kayitlar(kok, f"{simdi:%Y%m%d}-")
               if _soran_eposta(yol.read_text(encoding="utf-8")) == soran)


def _yeni_id(kok, simdi):
    while True:
        aday = f"{simdi:%Y%m%d-%H%M}-" + "".join(random.choices(string.ascii_lowercase, k=4))
        if not soru_kaydi.yol(aday, kok).exists():
            return aday


def _bekleme_notu(kok, simdi):
    if not ayar.mesaide_mi(simdi):
        return f"mesai dışı ({ayar.MESAI_METNI}) — sabah işlenecek"
    if ayar.gunluk_maliyet(kok, f"{simdi:%Y-%m-%d}") >= ayar.GUNLUK_MALIYET_TAVANI_USD:
        return "şirket günlük bütçesi doldu — ertesi gün işlenecek"
    return None


def _reddet(sebep):
    return {"sonuc": "reddedildi", "soru_id": None, "sebep": sebep}


def yeni(kok, soru, soran, simdi=None, kuru=False):
    """Kurul sorusunu kayda alır. {"sonuc": acildi | var | reddedildi, "soru_id", "sebep"} döner."""
    simdi = simdi or datetime.now().astimezone()
    soran = soran.strip().lower()
    tum_roller = roller(kok)
    if not tum_roller:
        return _reddet("deploy/roller.json yok ya da boş — kimse soru soramaz")
    rol = tum_roller.get(soran)
    if rol not in SORABILEN_ROLLER:
        return _reddet(f"{soran} soru soramaz (rol: {rol or 'yok'})")
    soru, maske = maskele(" ".join(soru.split()))
    if len(re.findall(r"\w+", soru)) < ayar.SORU_EN_AZ_KELIME:
        return _reddet("soru çok kısa — soruyu biraz açar mısın?")
    onceki = _tekrar_mi(kok, soran, soru, simdi)
    if onceki:
        return {"sonuc": "var", "soru_id": onceki,
                "sebep": f"aynı soru {ayar.SORU_TEKRAR_DK} dk içinde soruldu — ilk sorunun durumu gösterilir"}
    if _bugunku_soru_sayisi(kok, soran, simdi) >= ayar.KURUL_UYESI_GUNLUK_SORU:
        return _reddet(f"bugünkü soru hakkın doldu ({ayar.KURUL_UYESI_GUNLUK_SORU} soru)")

    soru_id = _yeni_id(kok, simdi)
    notu = _bekleme_notu(kok, simdi)
    satirlar = [f"# Soru {soru_id}", f"- soran: {soran} (rol: {rol})", f"- zaman: {simdi.isoformat(timespec='seconds')}",
                f"- soru: {soru}", f"- bütçe: {ayar.SORU_BUTCESI_USD:.2f} USD".replace(".", ","), "- durum: alındı"]
    if maske:
        satirlar.append("- maskelendi: " + ", ".join(f"{t} ({n})" for t, n in maske.items()))
    if notu:
        satirlar.append(f"- not: {notu}")
    if not kuru:
        yol = soru_kaydi.yol(soru_id, kok)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        gelen = Path(kok) / "gelen" / f"{soru_id}.json"
        gelen.parent.mkdir(parents=True, exist_ok=True)
        gelen.write_text(json.dumps({"id": soru_id, "soru": soru, "soran": soran,
                                     "zaman": simdi.isoformat(timespec="seconds")}, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    return {"sonuc": "acildi", "soru_id": soru_id, "sebep": notu or "", "kayit": "\n".join(satirlar)}


def sistem_sorusu(kok, danisman, soru, soru_id, aralik, karsilastir, simdi, kuru=False):
    """Zamanlı rapor için sistem sorusu açar: kayıt + `## Dağıtım` (danışman belli) + danışman kuyruğu.

    İş Dağıtımcı onu yeniden yönlendirmez (`## Dağıtım` var → Haiku çağrılmaz). Danışmanın `durum.json`'u yoksa
    kuyruğa yazılamaz; yarım açık kayıt kalmasın diye hiçbir şey yazılmadan `reddedildi` döner.
    Aynı id'li kayıt varsa `var`. `simdi` zaman dilimli olmalı; kayıttaki zaman İstanbul saatidir."""
    yol = soru_kaydi.yol(soru_id, kok)
    if yol.exists():
        return {"sonuc": "var", "soru_id": soru_id, "sebep": "bu gün için rapor zaten açıldı"}
    if not ayar.durum_oku(danisman, kok):
        return _reddet(f"{danisman} kuyruğu yok (durum.json) — rapor açılmadı")
    if not kuru:
        import dagitici   # dagitici bu modülü içe aktarır; döngü olmasın diye burada
        zaman = simdi.astimezone(ZoneInfo("Europe/Istanbul"))
        gun = lambda r: f"{r[0]:%Y-%m-%d}..{r[1]:%Y-%m-%d}"  # noqa: E731
        satirlar = [f"# Soru {soru_id}", "- soran: Zamanlayıcı (kalite günlük raporu)",
                    f"- zaman: {zaman.isoformat(timespec='seconds')}", f"- soru: {soru}",
                    f"- bütçe: {ayar.SORU_BUTCESI_USD:.2f} USD".replace(".", ","),
                    f"- aralik: {gun(aralik)}", f"- karsilastir: {gun(karsilastir)}",
                    "- gorunurluk: kurul", "- durum: danışmanda"]
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        soru_kaydi.bolum_ekle(yol, dagitici._dagitim_bolumu(
            {"danisman": danisman, "yontem": "sistem sorusu", "gerekce": "zamanlı rapor"}))
        dagitici.kuyruga_yaz(kok, danisman, f"s-{soru_id}", soru)
    return {"sonuc": "acildi", "soru_id": soru_id, "sebep": ""}


# --- çıkış -----------------------------------------------------------------

def _imza(metin):
    """İki imza: son karar bölümleri Denetçi kabul + CEO onay (ya da CEO kapalı). Etiket ya da None."""
    son_iki = soru_kaydi.kararlar(metin)[-2:]
    if son_iki == [("denetci", "kabul"), ("ceo", "onay")]:
        return "onaylı"
    if son_iki == [("denetci", "kabul"), ("ceo", "yapilmadi")]:
        return "CEO kontrolü yapılmadı"
    return None


def ilet(kok, soru_id, simdi=None, onaylanamadi=None):
    """Yanıtı Yanıt defterine iletir. `onaylanamadi` verilirse (dağıtıcı) yanıt metni gitmez, gerekçe gider."""
    simdi = simdi or datetime.now().astimezone()
    yol = soru_kaydi.yol(soru_id, kok)
    if not yol.is_file():
        raise IletHatasi(f"soru kaydı yok: {soru_id}")
    metin = yol.read_text(encoding="utf-8")
    if yanit_defteri.yol(soru_id, kok).exists():
        raise IletHatasi(f"{soru_id} Yanıt defterinde zaten var — defter değiştirilmez")
    danisman = soru_kaydi.bolum_alani(metin, "## Dağıtım", "danışman") or "—"
    if onaylanamadi:
        etiket, govde = "onaylanamadı", f"## Gerekçe\n{onaylanamadi}\n"
    else:
        etiket = _imza(metin)
        if not etiket:
            raise IletHatasi("iki imza yok (son karar Denetçi kabulü ve ardından CEO onayı olmalı) — iletilmez")
        import ceo   # döngüsel içe aktarma olmasın diye burada
        taslak = Path(kok) / "takimlar" / ceo.takim_adi(danisman) / "cikti" / f"{soru_id}-taslak.md"
        if not taslak.is_file():
            raise IletHatasi(f"danışman yanıtı yok: {taslak}")
        not_ = soru_kaydi.bolum_alani(metin, "## CEO — karar: onay", "kurula not") or "-"
        govde = (f"## Kurula not\n{not_}\n\n" if not_ != "-" else "") + f"## Yanıt\n{taslak.read_text(encoding='utf-8')}"
    imzalar = {"onaylı": "✔ · CEO: ✔", "CEO kontrolü yapılmadı": "✔ · CEO: —", "onaylanamadı": "— · CEO: —"}[etiket]
    kayit = (f"# Yanıt — {soru_id}\n- soru: {soru_kaydi.alan(metin, 'soru')}\n- soran: {_soran_eposta(metin)}\n"
             f"- tarih: {soru_kaydi.alan(metin, 'zaman')}\n- danışman: {danisman}\n- etiket: {etiket}\n"
             f"- Denetçi: {imzalar}\n- iletildi: {simdi.isoformat(timespec='seconds')}\n\n{govde}")
    try:
        yanit_defteri.yaz(kok, soru_id, kayit)
    except FileExistsError:
        raise IletHatasi(f"{soru_id} Yanıt defterinde zaten var — defter değiştirilmez") from None
    durum = "onaylanamadı" if onaylanamadi else "iletildi"
    soru_kaydi.durum_yaz(yol, durum)
    soru_kaydi.bolum_ekle(yol, f"## İletim\n- etiket: {etiket}\n- zaman: {simdi.isoformat(timespec='seconds')}\n")
    return {"soru_id": soru_id, "etiket": etiket, "durum": durum}


# --- komut satırı ----------------------------------------------------------

def _arguman(argv, ad):
    return argv[argv.index(ad) + 1] if ad in argv and argv.index(ad) + 1 < len(argv) else None


def main(argv):
    if "--yeni" in argv and _arguman(argv, "--yeni") is not None and _arguman(argv, "--soran"):
        kuru = "--kuru" in argv
        sonuc = yeni(KOK, _arguman(argv, "--yeni"), _arguman(argv, "--soran"), kuru=kuru)
        if sonuc["sonuc"] == "reddedildi":
            print(f"soru kayda alınmadı: {sonuc['sebep']}")
            return 1
        if sonuc["sonuc"] == "var":
            print(f"{sonuc['soru_id']}: {sonuc['sebep']}")
            return 0
        print(f"{sonuc['soru_id']}: kayda alındı" + (f" · {sonuc['sebep']}" if sonuc["sebep"] else ""))
        if kuru:
            print("\n" + sonuc["kayit"] + "\n\n  (kuru koşu: soru kaydı ve gelen/ dosyası yazılmadı)")
        return 0
    if "--ilet" in argv and _arguman(argv, "--ilet"):
        try:
            sonuc = ilet(KOK, _arguman(argv, "--ilet"))
        except IletHatasi as exc:
            print(f"iletilmedi: {exc}", file=sys.stderr)
            return 1
        print(f"{sonuc['soru_id']}: {sonuc['etiket']} · Yanıt defterine yazıldı")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
