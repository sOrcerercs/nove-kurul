#!/usr/bin/env python3
"""Ajan Sahnesi — yerel panel sunucusu.

Şirketin o anki hâlini repodan okuyup `sahne/` altındaki sahneye verir.
SALT OKUNURDUR: hiçbir dosyaya yazmaz, hiçbir takımı başlatmaz, ağa çıkmaz.
Yalnız 127.0.0.1'e bağlanır — dışarıya açılmaz.

    python3 bin/sahne.py            # http://127.0.0.1:8770
    python3 bin/sahne.py --port 9000
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402 — kuyruk yazımı reponun kendi yardımcısıyla yapılır
import karar_defter  # noqa: E402 — karar kapatma iş mantığı burada, panel yalnız kapı

KOK = Path(__file__).resolve().parent.parent
SAHNE = KOK / "sahne"
TZ = timezone(timedelta(hours=3))

# Kuyruğa giren metin tek satır, 200 karakter.
NOT_SINIRI = 200

# Kısa adlar ayar.py'de — panel aynı sözlüğü okur.
TAKIMLAR = ayar.TAKIM_KISA_ADLARI

# Nove danışmanları soru geldiğinde koşar; formda "Tempo" (§6) istenirse buraya yazılır.
TEMPO = {anahtar: "soru geldiğinde" for anahtar in TAKIMLAR}


def _oku_json(yol):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _saat(iso):
    """2026-09-15T23:06:22+03:00 -> 2026-09-15 23:06"""
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso).astimezone(TZ).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(iso)[:16].replace("T", " ")


def _son_dosya(klasor):
    if not klasor.is_dir():
        return None
    adaylar = sorted(p for p in klasor.iterdir() if p.is_file() and not p.name.startswith("."))
    return adaylar[-1] if adaylar else None


def _kuyruk_ozeti(durum):
    kuyruk = durum.get("kuyruk") or []
    bekleyen = [m for m in kuyruk if m.get("durum") == "bekliyor"]
    if not kuyruk:
        return "kuyruk boş", 0
    if not bekleyen:
        son = kuyruk[-1]
        return "%s · %s" % (son.get("id", "—"), son.get("durum", "—")), 0
    ilk = bekleyen[0]
    metin = "%s · bekliyor" % ilk.get("id", "—")
    if ilk.get("not"):
        metin += " — %s" % ilk["not"]
    if len(bekleyen) > 1:
        metin += "  (+%d bekleyen)" % (len(bekleyen) - 1)
    return metin, len(bekleyen)


def _kosu_ayristir(metin):
    """Koşu kaydını yapıya göre ayrıştırır — başlık adlarına güvenmez, ajan onları serbest yazar.

    Sabit çapalar: `kos.py`'ın yazdığı `- maliyet: … · tur: … · hata: …` satırı
    ve `bekci.py`'ın yazdığı `## Bekçi` bölümü.
    """
    ozet, maliyet, tur, hata = [], None, None, None
    bolum = None
    for ham in metin.splitlines():
        satir = ham.strip()
        if satir.startswith("- maliyet:"):
            m = re.search(r"maliyet:\s*([\d.]+)\s*USD.*?tur:\s*(\d+).*?hata:\s*(\w+)", satir)
            if m:
                maliyet, tur, hata = m.group(1), int(m.group(2)), m.group(3).lower() == "true"
            continue
        if satir.startswith("## "):
            bolum = satir[3:].strip()
            continue
        if bolum and satir and not satir.startswith(("```", "|", "---")):
            # her bölümden yalnız ilk dolu satır — koşu kaydı uzun, panel kısa
            if not any(o["bolum"] == bolum for o in ozet):
                temiz = re.sub(r"[*`]", "", satir).lstrip("- ").strip()
                if len(temiz) > 3:
                    ozet.append({"bolum": bolum, "satir": temiz[:190]})
    return {"ozet": ozet[:7], "maliyet": maliyet, "tur": tur, "hata": hata}


def _bugun_ozeti(takim, simdi):
    """`takimlar/<takim>/kosu/<bugün>-*.md` → panelin 'Bugün' bölümü. Yoksa koşmadı der."""
    gun = simdi.strftime("%Y-%m-%d")
    klasor = KOK / "takimlar" / takim / "kosu"
    if not klasor.is_dir():
        return {"kosdu": False, "not": "takım kurulu değil"}
    kayitlar = sorted(p for p in klasor.glob(gun + "-*.md") if p.is_file())
    if not kayitlar:
        return {"kosdu": False, "not": "bugün koşmadı"}
    son = kayitlar[-1]
    try:
        metin = son.read_text(encoding="utf-8")
    except OSError as hata:
        return {"kosdu": False, "not": "koşu kaydı okunamadı: %s" % hata}
    cozum = _kosu_ayristir(metin)
    saat = son.stem.split("-")[-1]
    return {
        "kosdu": True,
        "saat": "%s:%s" % (saat[:2], saat[2:]) if len(saat) == 4 else saat,
        "kayit": "takimlar/%s/kosu/%s" % (takim, son.name),
        "kosu_sayisi": len(kayitlar),
        **cozum,
    }


def _bugun_cikti(takim, simdi):
    """Bugün üretilmiş çıktı dosyası varsa adı."""
    klasor = KOK / "takimlar" / takim / "cikti"
    if not klasor.is_dir():
        return None
    gun = simdi.strftime("%Y-%m-%d")
    bugunku = sorted(p.name for p in klasor.iterdir() if p.is_file() and p.name.startswith(gun))
    return bugunku[-1] if bugunku else None


def _bugun_bekci(simdi):
    """Bugünkü bekçi kararları — telemetriden."""
    yol = KOK / "takimlar" / "bekci-telemetri.jsonl"
    gun = simdi.strftime("%Y-%m-%d")
    kararlar = []
    if not yol.is_file():
        return kararlar
    try:
        for satir in yol.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if not satir or gun not in satir:
                continue
            try:
                k = json.loads(satir)
            except ValueError:
                continue
            if str(k.get("zaman", "")).startswith(gun):
                kararlar.append(k)
    except OSError:
        pass
    return kararlar


def _son_bekci_karari():
    yol = KOK / "takimlar" / "bekci-telemetri.jsonl"
    if not yol.is_file():
        return None
    son = None
    try:
        for satir in yol.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                son = json.loads(satir)
            except ValueError:
                continue
    except OSError:
        return None
    return son


def _sayac_satiri(sayaclar):
    """durum.json'daki sayaçları okunur tek satıra çevirir — uydurma yok."""
    if not sayaclar:
        return None
    atla = {"cikti_dosyasi"}
    parcalar = []
    for k, v in sayaclar.items():
        if k in atla:
            continue
        parcalar.append("%s: %s" % (k.replace("_", " "), v))
    return " · ".join(parcalar) if parcalar else None


def _takim_verisi(anahtar):
    klasor = KOK / "takimlar" / TAKIMLAR[anahtar]
    tempo = TEMPO[anahtar]
    if not klasor.is_dir():
        return {
            "durum": "planda",
            "detay": "takım klasörü henüz açılmadı\ntempo: %s" % tempo,
            "olcum": "— takım kurulu değil",
            "kuyruk": "—",
            "cikti": "— henüz çıktı yok",
            "kaynak": "takimlar/%s/ — yok" % TAKIMLAR[anahtar],
            "bugun": {"kosdu": False, "not": "takım kurulu değil"},
            "kurulu": False,
        }

    durum = _oku_json(klasor / "durum.json") or {}
    satir = []
    son_kosu = _saat(durum.get("son_kosu"))
    son_sonuc = durum.get("son_sonuc")
    if son_kosu:
        satir.append("son koşu: %s → %s" % (son_kosu, son_sonuc or "?"))
    else:
        satir.append("kurulu, henüz koşmadı")
    satir.append("tempo: %s" % tempo)

    bekci = durum.get("bekci") or {}
    if bekci.get("son_karar"):
        satir.append("bekçi: %s (%s)" % (bekci["son_karar"], _saat(bekci.get("zaman")) or "—"))
    red7 = bekci.get("red_sayisi_7g")
    if red7 is not None:
        satir.append("7 günde red: %s" % red7)
    if durum.get("defter_son_ders"):
        satir.append("son ders: %s" % durum["defter_son_ders"])

    kuyruk_metni, bekleyen = _kuyruk_ozeti(durum)

    cikti_klasor = klasor / "cikti"
    son_cikti = _son_dosya(cikti_klasor)
    cikti = (
        "takimlar/%s/cikti/%s" % (TAKIMLAR[anahtar], son_cikti.name)
        if son_cikti
        else "— henüz çıktı yok"
    )

    kosu_klasor = klasor / "kosu"
    kosu_sayisi = len([p for p in kosu_klasor.iterdir() if p.is_file()]) if kosu_klasor.is_dir() else 0

    olcum = _sayac_satiri(durum.get("sayaclar")) or (
        "koşu kaydı: %d" % kosu_sayisi if kosu_sayisi else "— koşu yok, ölçüm yok"
    )

    return {
        "durum": son_sonuc or ("kuyrukta" if bekleyen else "hazır"),
        "detay": "\n".join(satir),
        "olcum": olcum,
        "kuyruk": kuyruk_metni,
        "cikti": cikti,
        "kaynak": "takimlar/%s/durum.json" % TAKIMLAR[anahtar],
        "bugun": _bugun_ozeti(TAKIMLAR[anahtar], datetime.now(TZ)),
        "kurulu": True,
    }


def veri():
    simdi = datetime.now(TZ)
    aktorler = {}
    kurulu = 0
    for anahtar in TAKIMLAR:
        a = _takim_verisi(anahtar)
        if a.pop("kurulu", False):
            kurulu += 1
        aktorler[anahtar] = a

    acik_kararlar = karar_defter.acik_kararlar(KOK)

    bugunku_kararlar = _bugun_bekci(simdi)
    bugun_kosanlar = [(TAKIMLAR[k], "%s · %s" % (a["bugun"].get("saat", "—"), a.get("durum", "?")))
                      for k, a in aktorler.items() if a.get("bugun", {}).get("kosdu")]
    bugun_ciktilar = [(TAKIMLAR[k], _bugun_cikti(TAKIMLAR[k], simdi))
                      for k in TAKIMLAR if _bugun_cikti(TAKIMLAR[k], simdi)]
    _sr = _son_dosya(KOK / "sirket-log" / "rapor")
    bugun_rapor = _sr.name if _sr and _sr.name.startswith(simdi.strftime("%Y-%m-%d")) else None

    # --- bekçi
    son = _son_bekci_karari()
    if son:
        gerekce = (son.get("gerekce") or "").strip()
        if len(gerekce) > 150:
            gerekce = gerekce[:147].rsplit(" ", 1)[0] + "…"
        aktorler["bekci"] = {
            "durum": "nöbette",
            "detay": "bin/bekci.py — Stop hook'ta, ayrı süreçte\n"
            "düşüş sırası: NVIDIA NIM → OpenAI → Haiku\n"
            "son karar: %s · %s (%s)\n%s"
            % (son.get("karar", "—"), son.get("takim", "—"), _saat(son.get("zaman")) or "—", gerekce),
            "olcum": "son karar: %s · ihlal: %s"
            % (son.get("karar", "—"), son.get("ihlal_edilen_kural") or "yok"),
            "kuyruk": "denetim kuyruğu boş",
            "cikti": "takimlar/bekci-telemetri.jsonl",
            "kaynak": "takimlar/bekci-telemetri.jsonl",
            "bugun": {
                "kosdu": bool(bugunku_kararlar),
                "not": "bugün karar yok" if not bugunku_kararlar else None,
                "ozet": [{"bolum": k.get("takim", "?"), "satir": "%s — %s" % (
                    k.get("karar", "?"), (k.get("gerekce") or "")[:150])} for k in bugunku_kararlar],
                "kayit": "takimlar/bekci-telemetri.jsonl",
            },
        }

    # --- dağıtıcı: zincir kurulu takımlardan türetilir
    zincir = ["günlük"] + [TAKIMLAR[k] for k in TAKIMLAR if (KOK / "takimlar" / TAKIMLAR[k]).is_dir()]
    aktorler["dagitici"] = {
        "durum": "hazır",
        "detay": "bin/dagitici.py — düz Python, LLM çağırmaz\n"
        "kurulu halkalar: %s → bekçi\n"
        "takımlar birbirine yazmaz, zinciri dağıtıcı kurar" % " → ".join(zincir),
        "olcum": "%d kurulu takım · %d planda" % (kurulu, len(TAKIMLAR) - kurulu),
        "kuyruk": "—",
        "cikti": "takimlar/<takim>/durum.json",
        "kaynak": "takimlar/ — klasör taraması",
        "bugun": {
            "kosdu": bool(bugun_kosanlar),
            "not": "bugün hiçbir takım koşmadı" if not bugun_kosanlar else None,
            "ozet": [{"bolum": t, "satir": d} for t, d in bugun_kosanlar],
            "kayit": "takimlar/*/kosu/",
        },
    }

    # --- günlük: sıradaki tetik saatten türetilir
    sonraki = "09:00 — sabah dağıtıcı" if simdi.hour >= 22 or simdi.hour < 9 else (
        "22:00 — akşam denetimi" if simdi.hour < 22 else "09:00 — sabah dağıtıcı"
    )
    rapor_klasor = KOK / "sirket-log" / "rapor"
    son_rapor = _son_dosya(rapor_klasor)
    mesaide = 9 <= simdi.hour < 23
    aktorler["gunluk"] = {
        "durum": "mesaide" if mesaide else "mesai dışı",
        "detay": "bin/gunluk.py — launchd, düz Python\n"
        "sabah 09:00 → dağıtıcı + sabah raporu\n"
        "akşam 22:00 → gün denetimi (yalnız okur)\n"
        "sıradaki tetik: %s" % sonraki,
        "olcum": "şu an %s · mesai 09:00–23:00 → %s"
        % (simdi.strftime("%H:%M"), "açık" if mesaide else "kapalı"),
        "kuyruk": "sıradaki tetik: %s" % sonraki.split(" —")[0],
        "cikti": "sirket-log/rapor/%s" % son_rapor.name if son_rapor else "— henüz rapor yok",
        "kaynak": "bin/gunluk.py · sistem saati",
        "bugun": {
            "kosdu": bool(bugun_rapor),
            "not": "bugün sabah raporu yazılmadı" if not bugun_rapor else None,
            "ozet": ([{"bolum": "sabah raporu", "satir": bugun_rapor}] if bugun_rapor else []),
            "kayit": "sirket-log/rapor/",
        },
    }

    # --- patron masası: bekleyen taslaklar ve patron notları
    taslaklar = []
    patron_notu = 0
    for anahtar, ad in TAKIMLAR.items():
        cikti_klasor = KOK / "takimlar" / ad / "cikti"
        if cikti_klasor.is_dir():
            taslaklar += [p.name for p in cikti_klasor.iterdir() if p.is_file()]
        d = _oku_json(KOK / "takimlar" / ad / "durum.json") or {}
        patron_notu += len(
            [
                m
                for m in (d.get("kuyruk") or [])
                if m.get("durum") == "bekliyor" and str(m.get("id", "")).startswith("not-")
            ]
        )
    aktorler["masa"] = {
        "durum": "yayın düğmesi burada",
        "detay": "bekleyen taslak: %d\npatron notu (kuyrukta 'not-'): %d\n"
        "takımlar buraya teslim eder, birbirine değil\nyayın kararı insanın"
        % (len(taslaklar), patron_notu),
        "olcum": "%d taslak · %d patron notu" % (len(taslaklar), patron_notu),
        "kuyruk": (taslaklar[-1] + " — okunmayı bekliyor") if taslaklar else "masa boş",
        "cikti": "takimlar/<takim>/cikti/",
        "kaynak": "takimlar/*/cikti/ · durum.json kuyrukları",
        "bugun": {
            "kosdu": bool(bugun_ciktilar),
            "not": "bugün masaya taslak düşmedi" if not bugun_ciktilar else None,
            "ozet": [{"bolum": t, "satir": c} for t, c in bugun_ciktilar],
            "kayit": "takimlar/*/cikti/",
        },
    }

    return {
        "zaman_cizgisi": zaman_cizgisi(simdi=simdi),
        "uretildi": simdi.isoformat(timespec="seconds"),
        "okundu": simdi.strftime("%H:%M"),
        "canli": True,
        "kurulu_takim": kurulu,
        "planda_takim": len(TAKIMLAR) - kurulu,
        "aktorler": aktorler,
        "acik_kararlar": acik_kararlar,
    }


# Panelin okumasına izin verilen kökler. Dışına çıkan her istek reddedilir.
# `.env` hem bu köklerin dışında hem de izinli uzantı listesinde değil — iki kat kapalı.
OKUNABILIR_KOKLER = ("takimlar", "sirket-log")
OKUNABILIR_UZANTILAR = (".md", ".txt", ".jsonl")
DOSYA_TAVANI_BAYT = 512 * 1024


def okunabilir_yol(goreli):
    """Repo köküne göreli yolu doğrular. Geçersizse (None, sebep) döner.

    `..` ile yukarı çıkma, sembolik bağla dışarı sızma ve izinsiz uzantı burada durur:
    yol çözülerek (resolve) karşılaştırılır, yani `takimlar/../.env` de elenir.
    """
    if not goreli or not isinstance(goreli, str):
        return None, "yol yok"
    try:
        aday = (KOK / goreli).resolve()
    except (OSError, ValueError):
        return None, "yol çözülemedi"
    if aday.suffix.lower() not in OKUNABILIR_UZANTILAR:
        return None, "bu uzantı okunmuyor (%s)" % ", ".join(OKUNABILIR_UZANTILAR)
    izinli = False
    for ad in OKUNABILIR_KOKLER:
        try:
            if aday.is_relative_to((KOK / ad).resolve()):
                izinli = True
                break
        except (OSError, ValueError):
            continue
    if not izinli:
        return None, "bu klasör panelden okunmuyor"
    if not aday.is_file():
        return None, "dosya yok"
    if aday.stat().st_size > DOSYA_TAVANI_BAYT:
        return None, "dosya çok büyük (>%d KB)" % (DOSYA_TAVANI_BAYT // 1024)
    return aday, None


def dosya_oku(goreli):
    yol, sebep = okunabilir_yol(goreli)
    if yol is None:
        return False, sebep
    try:
        icerik = yol.read_text(encoding="utf-8", errors="replace")
    except OSError as hata:
        return False, "okunamadı: %s" % hata
    return True, {
        "yol": str(yol.relative_to(KOK)),
        "bayt": yol.stat().st_size,
        "degisti": _saat(datetime.fromtimestamp(yol.stat().st_mtime, TZ).isoformat()),
        "icerik": icerik,
    }


def zaman_cizgisi(gun=7, simdi=None):
    """"Ben yokken ne oldu" — son N günün olayları, yeniden eskiye, güne göre gruplu.

    Olaylar dosyaların KENDİ zaman damgalarından çıkar, uydurulmaz:
      koşu    → `kosu/YYYY-MM-DD-HHMM.md` dosya adı + kaydın `hata:` satırı
      bekçi   → `bekci-telemetri.jsonl` içindeki `zaman` alanı
      çıktı   → `cikti/` dosyasının değişme zamanı
      rapor   → `sirket-log/rapor/` dosyasının değişme zamanı
    Her olay kaynağını taşır (ANAYASA §2: kaynaksız satır yok).
    """
    simdi = simdi or datetime.now(TZ)
    sinir = simdi - timedelta(days=gun)
    olaylar = []

    def ekle(zaman, aktor, tur, metin, kaynak):
        if zaman >= sinir:
            olaylar.append({"zaman": zaman, "aktor": aktor, "tur": tur,
                            "metin": metin, "kaynak": kaynak})

    for anahtar, takim in TAKIMLAR.items():
        kosu_klasor = KOK / "takimlar" / takim / "kosu"
        if kosu_klasor.is_dir():
            for yol in kosu_klasor.glob("*.md"):
                damga = yol.stem                      # YYYY-MM-DD-HHMM
                try:
                    zaman = datetime.strptime(damga[:16], "%Y-%m-%d-%H%M").replace(tzinfo=TZ)
                except ValueError:
                    continue
                try:
                    cozum = _kosu_ayristir(yol.read_text(encoding="utf-8"))
                except OSError:
                    cozum = {}
                if cozum.get("hata") is True:
                    ne = "koşu düştü"
                elif cozum.get("maliyet"):
                    ne = "koştu · %s USD · %s tur" % (cozum["maliyet"], cozum.get("tur", "?"))
                else:
                    ne = "koştu"
                ekle(zaman, takim, "kosu", ne, "takimlar/%s/kosu/%s" % (takim, yol.name))

        cikti_klasor = KOK / "takimlar" / takim / "cikti"
        if cikti_klasor.is_dir():
            for yol in cikti_klasor.iterdir():
                if yol.is_file() and not yol.name.startswith("."):
                    ekle(datetime.fromtimestamp(yol.stat().st_mtime, TZ), takim, "cikti",
                         "çıktı üretti: %s" % yol.name,
                         "takimlar/%s/cikti/%s" % (takim, yol.name))

    for k in _bugun_bekci_hepsi():
        try:
            zaman = datetime.fromisoformat(k["zaman"]).astimezone(TZ)
        except (ValueError, KeyError, TypeError):
            continue
        gerekce = " ".join((k.get("gerekce") or "").split())[:120]
        ekle(zaman, "bekçi", "bekci",
             "%s → %s%s" % (k.get("takim", "?"), k.get("karar", "?"),
                            (" — " + gerekce) if gerekce else ""),
             "takimlar/bekci-telemetri.jsonl")

    rapor_klasor = KOK / "sirket-log" / "rapor"
    if rapor_klasor.is_dir():
        for yol in rapor_klasor.iterdir():
            if yol.is_file() and yol.suffix == ".md":
                ne = "akşam denetimi" if "aksam" in yol.name else "sabah raporu"
                ekle(datetime.fromtimestamp(yol.stat().st_mtime, TZ), "günlük", "rapor",
                     "%s yazıldı" % ne, "sirket-log/rapor/%s" % yol.name)

    olaylar.sort(key=lambda o: o["zaman"], reverse=True)

    gunler, sirali = [], {}
    for o in olaylar:
        etiket = o["zaman"].strftime("%Y-%m-%d")
        if etiket not in sirali:
            sirali[etiket] = {
                "gun": etiket,
                "baslik": _gun_basligi(o["zaman"], simdi),
                "olaylar": [],
            }
            gunler.append(sirali[etiket])
        sirali[etiket]["olaylar"].append({
            "saat": o["zaman"].strftime("%H:%M"),
            "aktor": o["aktor"], "tur": o["tur"],
            "metin": o["metin"], "kaynak": o["kaynak"],
        })
    return {"gun": gun, "toplam": len(olaylar), "gunler": gunler}


GUN_ADI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def _gun_basligi(zaman, simdi):
    fark = (simdi.date() - zaman.date()).days
    if fark == 0:
        return "Bugün"
    if fark == 1:
        return "Dün"
    return "%s · %s" % (GUN_ADI[zaman.weekday()], zaman.strftime("%d.%m"))


def _bugun_bekci_hepsi():
    """Telemetrinin tamamı — zaman çizgisi kendi penceresini uygular."""
    yol = KOK / "takimlar" / "bekci-telemetri.jsonl"
    if not yol.is_file():
        return []
    kayitlar = []
    try:
        for satir in yol.read_text(encoding="utf-8").splitlines():
            satir = satir.strip()
            if not satir:
                continue
            try:
                kayitlar.append(json.loads(satir))
            except ValueError:
                continue
    except OSError:
        return []
    return kayitlar


def _temiz(metin, sinir=NOT_SINIRI):
    """Kuyruğa giren metin tek satıra iner ve kırpılır."""
    tek_satir = " ".join(str(metin or "").split())
    return tek_satir[:sinir] + ("…" if len(tek_satir) > sinir else "")


def not_birak(anahtar, metin):
    """Patronun notunu takımın kuyruğuna `not-` maddesi olarak ekler (AJAN-KIMLIGI: 'not-' patrondan gelir).

    Panelin yazdığı iki yerden biri. Sınırın tamamı:
    (a) bir takımın kuyruğuna `not-` maddesi ekler,
    (b) var olan bir karar kaydının `durum` · `kapanis` · `kapanis_zamani` alanlarını
        değiştirir (bkz. `karar_kapat`).
    Başka hiçbir dosyaya, hiçbir alana dokunmaz.
    """
    if anahtar not in TAKIMLAR:
        return False, "bilinmeyen takım"
    takim = TAKIMLAR[anahtar]
    if not (KOK / "takimlar" / takim).is_dir():
        return False, "%s takımı henüz kurulu değil — kuyruğu yok" % takim
    notu = _temiz(metin)
    if not notu:
        return False, "not boş"

    durum = ayar.durum_oku(takim, KOK)
    kuyruk = durum.get("kuyruk") or []
    id_ = "not-p%d" % int(datetime.now(TZ).timestamp())
    if any(isinstance(o, dict) and o.get("id") == id_ for o in kuyruk):
        return False, "aynı id zaten kuyrukta"
    madde = {"id": id_, "durum": "bekliyor", "not": notu}
    ayar.durum_guncelle(takim, {"kuyruk": [*kuyruk, madde]}, KOK)
    return True, {"takim": takim, "madde": madde, "kuyruk_uzunlugu": len(kuyruk) + 1}


def karar_kapat(id_, durum, kapanis=None):
    """Var olan bir karar kaydını kapatır. İş mantığı `karar_defter.kapat`'ta —
    panel yalnız kapıdır, böylece defter HTTP kaldırmadan sınanabilir."""
    if not id_:
        return False, "karar id'si yok"
    return karar_defter.kapat(KOK, id_, durum, kapanis)


def kosu_baslat(anahtar, kuru=False):
    """`python3 bin/kos.py <takim>` — ayrı süreçte, kabuk yok, takım adı beyaz listeden.

    Tavanları, mesai kontrolünü ve kilidi kos.py uygular (ANAYASA §4); panel saymaz.
    """
    if anahtar not in TAKIMLAR:
        return False, "bilinmeyen takım"
    takim = TAKIMLAR[anahtar]
    if not (KOK / "takimlar" / takim).is_dir():
        return False, "%s takımı henüz kurulu değil" % takim
    komut = [sys.executable, str(KOK / "bin" / "kos.py"), takim] + (["--kuru"] if kuru else [])
    try:
        subprocess.Popen(komut, cwd=str(KOK), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as hata:
        return False, "başlatılamadı: %s" % hata
    mesaide = ayar.mesaide_mi()
    return True, {
        "takim": takim,
        "kuru": kuru,
        "mesaide": mesaide,
        "not": "koşu başlatıldı" if (kuru or mesaide) else
               "başlatıldı ama mesai dışı (%s) — kos.py atlayıp kuyrukta bırakır" % ayar.MESAI_METNI,
    }


class Sunucu(SimpleHTTPRequestHandler):
    def _govde(self):
        try:
            uzunluk = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None
        if uzunluk <= 0 or uzunluk > 64 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(uzunluk).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None

    def _yanit(self, kod, govde):
        ham = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(ham)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(ham)

    def do_POST(self):  # noqa: N802
        # CSRF emniyeti: tarayıcıdaki başka bir sayfa bu uca form gönderemesin.
        # Basit cross-origin POST bu başlığı koyamaz (preflight gerekir).
        if self.headers.get("X-Sahne") != "1":
            return self._yanit(403, {"tamam": False, "hata": "X-Sahne başlığı yok"})
        kaynak = self.headers.get("Origin")
        if kaynak and "127.0.0.1" not in kaynak and "localhost" not in kaynak:
            return self._yanit(403, {"tamam": False, "hata": "dış kaynak"})

        yol = self.path.split("?", 1)[0]
        govde = self._govde() or {}
        if not isinstance(govde, dict):
            return self._yanit(400, {"tamam": False, "hata": "gövde bir JSON nesnesi olmalı"})
        if yol == "/not":
            tamam, sonuc = not_birak(govde.get("takim"), govde.get("not"))
        elif yol == "/kos":
            tamam, sonuc = kosu_baslat(govde.get("takim"), kuru=bool(govde.get("kuru")))
        elif yol == "/karar":
            tamam, sonuc = karar_kapat(govde.get("id"), govde.get("durum"), govde.get("kapanis"))
        else:
            return self._yanit(404, {"tamam": False, "hata": "bilinmeyen uç"})
        return self._yanit(200 if tamam else 400,
                           {"tamam": tamam, **({"sonuc": sonuc} if tamam else {"hata": sonuc})})

    def do_PUT(self):  # noqa: N802
        self.send_error(405, "Bu panel yalnız not bırakır, koşu başlatır ve karar kapatır")

    do_DELETE = do_PATCH = do_PUT

    def do_GET(self):  # noqa: N802
        yol = self.path.split("?", 1)[0]
        if yol == "/dosya":
            from urllib.parse import parse_qs, urlparse
            istek = parse_qs(urlparse(self.path).query).get("yol", [""])[0]
            tamam, sonuc = dosya_oku(istek)
            return self._yanit(200 if tamam else 400,
                               {"tamam": tamam, **({"sonuc": sonuc} if tamam else {"hata": sonuc})})
        if yol in ("/veri.json", "/veri"):
            try:
                govde = json.dumps(veri(), ensure_ascii=False).encode("utf-8")
            except Exception as hata:  # panel çökmesin, sebebi görünsün
                govde = json.dumps(
                    {"canli": False, "hata": str(hata)}, ensure_ascii=False
                ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)
            return
        if yol == "/":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, bicim, *args):
        # /veri.json 60 saniyede bir çağrılıyor — günlüğü boğmasın.
        if "veri.json" not in " ".join(str(a) for a in args):
            super().log_message(bicim, *args)


def main():
    ap = argparse.ArgumentParser(description="Ajan Sahnesi — yerel panel (salt okunur)")
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    if not SAHNE.is_dir():
        raise SystemExit("sahne/ klasörü yok: %s" % SAHNE)

    handler = partial(Sunucu, directory=str(SAHNE))
    with ThreadingHTTPServer((args.host, args.port), handler) as sunucu:
        print("Ajan Sahnesi · salt okunur · http://%s:%d" % (args.host, args.port))
        print("Anayasa: http://%s:%d/anayasa.html" % (args.host, args.port))
        print("Durdurmak için Ctrl+C")
        try:
            sunucu.serve_forever()
        except KeyboardInterrupt:
            print("\nkapandı")


if __name__ == "__main__":
    main()
