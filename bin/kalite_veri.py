#!/usr/bin/env python3
"""Kalite danışmanının veri okuyucusu — SDR Analyzer Postgres'inden SALT OKUNUR sorgular.

Bağlantı `QA_READONLY_URL` ile `.env`'den gelir (`ayar.ortam_yukle`); rol `qa_okuyucu`'dur.
Yalnız SELECT; her bağlantı `read_only`, `statement_timeout = 15s` (bağlantı seçeneği), `connect_timeout = 20`.
Bağlantı adresi hiçbir çıktıya, loga ya da hata iletisine girmez. Çağrı transkripti, rapor
gövdesi, müşteri adı, kanıt ve tıbbi işaret alanları hiçbir sorguda yoktur.

Kullanım:
  python3 bin/kalite_veri.py sema     # yapı ve izin ölçümü — içerik basmaz
  python3 bin/kalite_veri.py ekipler
  python3 bin/kalite_veri.py ekip-ozet --baslangic YYYY-MM-DD --bitis YYYY-MM-DD
        [--karsilastir-baslangic .. --karsilastir-bitis ..] [--tip first|second] [--ekip <ad>]
  python3 bin/kalite_veri.py temsilci-ozet|kriterler|kocluk --baslangic .. --bitis .. [--ekip <ad>] [--tip ..]
Çıkış: 0 tamam · 1 durdu (`**Hazırlanamadı:** <sebep>`) · 2 kullanım hatası
"""
import argparse
import math
import re
import sys
from urllib.parse import urlsplit
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

BAGLANTI_ZAMAN_ASIMI = 20
SORGU_ZAMAN_ASIMI_MS = 15000        # 15s — bağlantı seçeneği olarak verilir, rollback'ten etkilenmez


# Raporlarım kuralı (sdr-analyzer reports/auto + callVisibility.ts:90).
# Sorgu kuruculardaki takma adlar: Evaluation = e, kayıt sahibi User = u.
UYE_KOSULU = "u.\"role\" IN ('AGENT', 'TEAM_LEADER') AND u.\"isActive\" = true"
SAYIM_KOSULU = ("(e.\"callClassification\" IS NULL OR e.\"callClassification\" = 'CONNECTED_QUALIFIED')"
                " AND " + UYE_KOSULU)
SAAT_DILIMI = "UTC gün sınırı (TR 03:00)"      # DB timezone UTC; panel (Vercel) de UTC günleri kullanır
PUANLAMA_DEGISIM_TARIHI = datetime(2026, 9, 1)  # öncesinde puanlama farklı; karşılaştırma geçersiz


def gun_siniri(baslangic, bitis):
    """`YYYY-MM-DD` → (başlangıç 00:00:00, bitiş 23:59:59), sunucu saatinde (naive)."""
    bas = datetime.strptime(baslangic, "%Y-%m-%d")
    bit = datetime.strptime(bitis, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    if bit < bas:
        raise ValueError("bitiş başlangıçtan önce: %s > %s" % (baslangic, bitis))
    return bas, bit


def js_yuvarla(x, hane=0):
    """JS `Math.round(x*10^h)/10^h` — yarımlar yukarı; Python round() değil."""
    kat = 10 ** hane
    sonuc = math.floor(x * kat + 0.5) / kat
    if hane == 0:
        return int(sonuc)                        # Math.round tam sayı verir (73, 73.0 değil)
    return 0 if sonuc == 0 else sonuc


def _tek_satir(deger):
    return " ".join(str(deger).split())


def kapsam_bolumu(komut, baslangic, bitis, filtre, kayit):
    """Çıktının başındaki `## kapsam` bölümü: hangi veri, hangi kuralla, kaç kayıt."""
    satirlar = ["## kapsam",
                "kaynak=SDR Analyzer Postgres (qa_okuyucu, salt okunur)",
                "komut=%s" % _tek_satir(komut),
                "aralik=%s..%s" % (_tek_satir(baslangic), _tek_satir(bitis)),
                "saat_dilimi=%s" % SAAT_DILIMI,
                "kural=AGENT/TEAM_LEADER, aktif, callClassification NULL ya da CONNECTED_QUALIFIED"]
    for anahtar, deger in (filtre or {}).items():
        satirlar.append("%s=%s" % (_tek_satir(anahtar), _tek_satir(deger)))
    satirlar.append("kayit=%d" % kayit)
    return "\n".join(satirlar)


def guvenli_hata(hata, url):
    """Tür adı + mesaj; adres parçaları (url, ana makine, port, rol, parola) `***`."""
    mesaj = str(hata)
    parcalar = []
    if url:
        parcalar.append(url)
        try:
            u = urlsplit(url)
            parcalar += [u.hostname, str(u.port) if u.port else None, u.username, u.password]
        except ValueError:
            pass
        if "://" in url:                         # parola `@` ya da `/` içerebilir: son `@`'ten böl
            kalan = url.split("://", 1)[1]
            kimlik, ayrac, makine = kalan.rpartition("@")
            if ayrac:
                kullanici, _, parola = kimlik.partition(":")
                parcalar += [kullanici, parola]
                parcalar += [f for f in re.split(r"[/:@]", kimlik) if len(f) >= 2]   # `Abc/123` → `Abc`, `123`
            ad_port = makine.split("/", 1)[0].split("?", 1)[0]
            parcalar += [ad_port.rsplit(":", 1)[0], ad_port.rsplit(":", 1)[-1]]
    for parca in sorted({p for p in parcalar if p}, key=len, reverse=True):
        mesaj = mesaj.replace(parca, "***")
    mesaj = re.sub(r"://[^@/\s\"']*@", "://***@", mesaj)
    mesaj = re.sub(r"(?i)password\s*=\s*\S+", "password=***", mesaj)
    mesaj = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "***", mesaj)      # çözülmüş IPv4
    mesaj = re.sub(r"([(\[])[0-9a-fA-F:.]*:[0-9a-fA-F:.]*([)\]])", r"\1***\2", mesaj)   # IPv6
    return "%s: %s" % (type(hata).__name__, mesaj)


def hazirlanamadi(sebep):
    """Durma satırı. Sessiz düşme yok (ANAYASA §2)."""
    return "**Hazırlanamadı:** %s" % sebep


def sema_sorgulari():
    """(ad, SQL) listesi — yalnız yapı ve sayım; hiçbir satır içeriği okunmaz."""
    return [
        ("izinler", """
SELECT table_name, column_name, privilege_type
  FROM information_schema.column_privileges
 WHERE grantee = current_user
   AND table_schema = 'public'
   AND (table_name IN ('Evaluation', 'User', 'Team')
        OR table_name ILIKE '%weekly%' OR table_name ILIKE '%nomination%')
 ORDER BY table_name, column_name
"""),
        ("sinif_farki", """
SELECT count(*) AS fark_sayisi
  FROM public."Evaluation"
 WHERE "callClassification"::text IS DISTINCT FROM "reportData"->>'callClassification'
"""),
        ("saat_dilimi", "SELECT current_setting('timezone') AS timezone"),
    ]


def baglan_varsayilan(url):
    import psycopg
    return psycopg.connect(url, connect_timeout=BAGLANTI_ZAMAN_ASIMI,
                           options="-c statement_timeout=%d" % SORGU_ZAMAN_ASIMI_MS)


def baglanti_ac(url, baglan=None):
    """Salt okunur, zaman aşımlı bağlantı. Hata iletisi çağırana URL taşımaz."""
    baglanti = (baglan or baglan_varsayilan)(url)
    try:
        baglanti.read_only = True            # oturum özelliği: rollback'ten sonra da geçerli
    except Exception:
        baglanti.close()
        raise
    return baglanti


def sema_bas(baglanti):
    """Her sorguyu ayrı dener; izin hatası satırı basılır, betik durmaz."""
    for ad, sql in sema_sorgulari():
        try:
            with baglanti.cursor() as imlec:
                imlec.execute(sql)
                satirlar = imlec.fetchall()
        except Exception as hata:            # noqa: BLE001 — sebep görünür olmalı (§2)
            print("- %s: okunamadı (%s)" % (ad, type(hata).__name__))
            try:
                baglanti.rollback()          # hatalı işlem sonraki sorguları bozmasın
            except Exception:                # noqa: BLE001
                pass
            continue
        print("- %s: %d satır" % (ad, len(satirlar)))
        for satir in satirlar:
            print("    " + " | ".join(str(d) for d in satir))


def ekipler_sorgusu():
    """(sql, params) — ekip adı ve aktif AGENT/TEAM_LEADER üye sayısı."""
    sql = ("SELECT t.name, count(u.id) AS temsilci\n"
           "  FROM public.\"Team\" t\n"
           "  LEFT JOIN public.\"User\" u ON u.\"teamId\" = t.id AND " + UYE_KOSULU + "\n"
           " GROUP BY t.name\n ORDER BY t.name")
    return sql, {}


AZ_ORNEK_ESIGI = 3                  # kurallar: 3'ten az değerlendirmeli temsilci "en iyi" seçilmez
TIP_ESLEME = {"first": "FIRST_CALL", "second": "SECOND_CALL"}


def _filtre_kosullari(bas, bit, tip, ekip):
    kosul = ["e.\"callDate\" >= %(bas)s", "e.\"callDate\" <= %(bit)s", SAYIM_KOSULU]
    param = {"bas": bas, "bit": bit}
    if tip:
        kosul.append("e.\"callType\"::text = %(tip)s")
        param["tip"] = TIP_ESLEME[tip]
    if ekip:
        kosul.append("t.name = %(ekip)s")
        param["ekip"] = ekip
    return "\n   AND ".join(kosul), param


def ekip_ozet_sorgusu(bas, bit, tip, ekip=None):
    """(sql, params) — ekip başına (ekip, toplam puan, kayıt, temsilci sayısı). Parametreli."""
    kosul, param = _filtre_kosullari(bas, bit, tip, ekip)
    sql = ("SELECT t.name, sum(e.score) AS toplam, count(*) AS adet,"
           " count(DISTINCT e.\"agentId\") AS temsilci\n"
           "  FROM public.\"Evaluation\" e\n"
           "  JOIN public.\"User\" u ON e.\"agentId\" = u.id\n"
           "  JOIN public.\"Team\" t ON u.\"teamId\" = t.id\n"
           " WHERE " + kosul + "\n"
           " GROUP BY t.id, t.name\n ORDER BY t.name")
    return sql, param


def ekip_tablosu(satirlar):
    """(ekip, toplam, adet, temsilci) → ortalama kayıt başına, JS yuvarlamasıyla tam sayı."""
    tablo = []
    for ekip, toplam, adet, temsilci in satirlar:
        if not adet:
            continue
        tablo.append({"ekip": ekip, "ortalama": js_yuvarla(float(toplam) / adet),
                      "kayit": int(adet), "temsilci": int(temsilci)})
    return tablo


def temsilci_ozet_sorgusu(bas, bit, tip, ekip=None):
    """(sql, params) — temsilci başına (temsilci, ekip, toplam puan, kayıt). Parametreli."""
    kosul, param = _filtre_kosullari(bas, bit, tip, ekip)
    sql = ("SELECT u.name, t.name, sum(e.score) AS toplam, count(*) AS adet\n"
           "  FROM public.\"Evaluation\" e\n"
           "  JOIN public.\"User\" u ON e.\"agentId\" = u.id\n"
           "  JOIN public.\"Team\" t ON u.\"teamId\" = t.id\n"
           " WHERE " + kosul + "\n"
           " GROUP BY u.id, u.name, t.name\n ORDER BY t.name, u.name")
    return sql, param


def temsilci_tablosu(satirlar):
    """(temsilci, ekip, toplam, adet) → ortalama kayıt başına, bir haneye; 3'ten az kayıt işaretli."""
    tablo = []
    for temsilci, ekip, toplam, adet in satirlar:
        if not adet:
            continue
        tablo.append({"temsilci": temsilci, "ekip": ekip,
                      "ortalama": js_yuvarla(float(toplam) / adet, 1),
                      "kayit": int(adet), "az_ornek": adet < AZ_ORNEK_ESIGI})
    tablo.sort(key=lambda t: (-t["ortalama"], t["temsilci"]))
    return tablo


# Okunmamış koçluk: SDR Analyzer paneli kuralı (app/lib/coachingInbox.ts, isCoachingUnseen) — agentRead DEĞİL.
OKUNMAYAN_KOSULU = ("(e.\"coachingSeenAt\" IS NULL OR (e.\"coachingDoneAt\" IS NOT NULL"
                    " AND e.\"coachingSeenAt\" < e.\"coachingDoneAt\"))")


def kocluk_sorgusu(bas, bit, tip, ekip=None):
    """(sql, params) — temsilci başına (temsilci, ekip, kayıt, koçluk yapılan, okunmayan). Parametreli."""
    kosul, param = _filtre_kosullari(bas, bit, tip, ekip)
    sql = ("SELECT u.name, t.name, count(*) AS adet,\n"
           "       count(*) FILTER (WHERE e.\"coachingDone\") AS kocluk_yapilan,\n"
           "       count(*) FILTER (WHERE e.\"coachingDone\" AND " + OKUNMAYAN_KOSULU + ") AS okunmayan\n"
           "  FROM public.\"Evaluation\" e\n"
           "  JOIN public.\"User\" u ON u.id = e.\"agentId\"\n"
           "  JOIN public.\"Team\" t ON t.id = u.\"teamId\"\n"
           " WHERE " + kosul + "\n"
           " GROUP BY u.id, u.name, t.name\n ORDER BY t.name, u.name")
    return sql, param


def kocluk_tablosu(satirlar):
    """(temsilci, ekip, kayıt, koçluk yapılan, okunmayan) → okunan = yapılan - okunmayan."""
    tablo = []
    for temsilci, ekip, adet, yapilan, okunmayan in satirlar:
        if not adet:
            continue
        tablo.append({"temsilci": temsilci, "ekip": ekip, "kayit": int(adet),
                      "kocluk_yapilan": int(yapilan), "okunan": int(yapilan) - int(okunmayan),
                      "okunmayan": int(okunmayan)})
    tablo.sort(key=lambda t: (-t["okunmayan"], t["ekip"], t["temsilci"]))
    return tablo


def kriter_sorgusu(bas, bit, tip, ekip=None):
    """(sql, params) — ekip ve kriter başına (ekip, kriter_id, etiket, kaldı, kısmi, geçti). NA sayılmaz."""
    kosul, param = _filtre_kosullari(bas, bit, tip, ekip)
    sql = ("SELECT t.name, k.kriter_id, k.kriter_label,\n"
           "       count(*) FILTER (WHERE k.verdict = 'FAIL') AS kaldi,\n"
           "       count(*) FILTER (WHERE k.verdict = 'PARTIAL') AS kismi,\n"
           "       count(*) FILTER (WHERE k.verdict = 'PASS') AS gecti\n"
           "  FROM public.qa_kriter k\n"
           "  JOIN public.\"Evaluation\" e ON e.id = k.eval_id\n"
           "  JOIN public.\"User\" u ON e.\"agentId\" = u.id\n"
           "  JOIN public.\"Team\" t ON u.\"teamId\" = t.id\n"
           " WHERE " + kosul + "\n"
           "   AND k.verdict IN ('FAIL', 'PARTIAL', 'PASS')\n"
           " GROUP BY t.name, k.kriter_id, k.kriter_label\n ORDER BY k.kriter_id, t.name")
    return sql, param


def kriter_kayit_sorgusu(bas, bit, tip, ekip=None):
    """(sql, params) — kriter satırı olan DEĞERLENDİRME sayısı (kriterli kayıt; First Call'lar dışarıda kalabilir)."""
    kosul, param = _filtre_kosullari(bas, bit, tip, ekip)
    sql = ("SELECT count(DISTINCT e.id) AS kriter_kayit\n"
           "  FROM public.qa_kriter k\n"
           "  JOIN public.\"Evaluation\" e ON e.id = k.eval_id\n"
           "  JOIN public.\"User\" u ON e.\"agentId\" = u.id\n"
           "  JOIN public.\"Team\" t ON u.\"teamId\" = t.id\n"
           " WHERE " + kosul + "\n"
           "   AND k.verdict IN ('FAIL', 'PARTIAL', 'PASS')")
    return sql, param


def kriter_tablosu(satirlar, ekipler_tum):
    """Ekipler üstünden toplanır; kaldıya göre sıralı. İkinci dönüş: sayılan kaydı olup kriter satırı
    olmayan ekipler (\"0 kaçırma\" diye gösterilmez)."""
    toplam = {}
    gorunen = set()
    for ekip, kid, etiket, kaldi, kismi, gecti in satirlar:
        if not (kaldi + kismi + gecti):
            continue
        gorunen.add(ekip)
        k = toplam.setdefault(kid, {"kriter_id": kid, "kriter": etiket, "kaldi": 0, "kismi": 0, "gecti": 0})
        k["kaldi"] += int(kaldi)
        k["kismi"] += int(kismi)
        k["gecti"] += int(gecti)
    tablo = []
    for k in toplam.values():
        k["oran_kaldi"] = js_yuvarla(k["kaldi"] / (k["kaldi"] + k["kismi"] + k["gecti"]), 2)
        tablo.append(k)
    tablo.sort(key=lambda k: (-k["kaldi"], k["kriter_id"]))
    return tablo, [e for e in ekipler_tum if e not in gorunen]


def karsilastir(simdi, onceki):
    """Önceki dönemle yan yana; düşüşe göre sıralı (en büyük düşüş ilk, karşılaştırması olmayan sonda)."""
    eski = {s["ekip"]: s for s in onceki}
    sonuc = []
    for s in simdi:
        o = eski.get(s["ekip"])
        satir = dict(s)
        satir["onceki_ortalama"] = o["ortalama"] if o else None
        satir["onceki_kayit"] = o["kayit"] if o else None
        satir["fark"] = (s["ortalama"] - o["ortalama"]) if o else None
        sonuc.append(satir)
    for ad, o in eski.items():                   # önceki dönemde kaydı olup şimdi hiç kaydı kalmayan ekip
        if ad not in {s["ekip"] for s in simdi}:
            sonuc.append({"ekip": ad, "ortalama": None, "kayit": 0, "temsilci": 0,
                          "onceki_ortalama": o["ortalama"], "onceki_kayit": o["kayit"], "fark": None})
    # sıra: şimdi kaydı kalmayanlar (en ağır), sonra düşüşe göre, önceki dönemi olmayanlar sonda
    sonuc.sort(key=lambda r: (r["ortalama"] is not None, r["onceki_ortalama"] is None,
                              r["fark"] if r["fark"] is not None else 0, r["ekip"]))
    return sonuc


def _sorgula(baglanti, sorgu):
    sql, param = sorgu
    with baglanti.cursor() as imlec:
        imlec.execute(sql, param)
        return imlec.fetchall()


def ekipler_bas(baglanti):
    satirlar = _sorgula(baglanti, ekipler_sorgusu())
    if not satirlar:
        print(hazirlanamadi("ekip bulunamadı"))
        return 1
    print(kapsam_bolumu("ekipler", "-", "-", {}, len(satirlar)))
    for ad, temsilci in satirlar:
        print("- %s: temsilci=%d" % (_tek_satir(ad), temsilci))
    return 0


def ekip_ozet_bas(baglanti, args):
    try:
        bas, bit = gun_siniri(args.baslangic, args.bitis)
        onc = None
        if args.karsilastir_baslangic:
            onc = gun_siniri(args.karsilastir_baslangic, args.karsilastir_bitis)
    except ValueError as hata:
        print(hazirlanamadi("tarih geçersiz (%s)" % hata))
        return 1
    aralik = "%s..%s" % (args.baslangic, args.bitis)
    if args.ekip:
        adlar = [r[0] for r in _sorgula(baglanti, ekipler_sorgusu())]
        if args.ekip not in adlar:
            print(hazirlanamadi("ekip bulunamadı: %s; mevcut ekipler: %s"
                                % (_tek_satir(args.ekip), ", ".join(_tek_satir(a) for a in adlar) or "yok")))
            return 1
    tablo = ekip_tablosu(_sorgula(baglanti, ekip_ozet_sorgusu(bas, bit, args.tip, args.ekip)))
    if not tablo:
        print(hazirlanamadi("%s için sayılabilir kayıt yok" % aralik))
        return 1
    filtre = {}
    if args.tip:
        filtre["tip"] = args.tip
    if args.ekip:
        filtre["ekip"] = args.ekip
    if onc:
        filtre["karsilastirma"] = "%s..%s" % (args.karsilastir_baslangic, args.karsilastir_bitis)
        tablo = karsilastir(tablo, ekip_tablosu(
            _sorgula(baglanti, ekip_ozet_sorgusu(onc[0], onc[1], args.tip, args.ekip))))
    if bas < PUANLAMA_DEGISIM_TARIHI or (onc and onc[0] < PUANLAMA_DEGISIM_TARIHI):
        filtre["uyari"] = "1 Eylül 2026 öncesi puanlama farklı; karşılaştırma geçersiz"
    if args.tip != "first":
        filtre["not"] = "canlı Second Call formülü deploy bekliyor"
    print(kapsam_bolumu("ekip-ozet", args.baslangic, args.bitis, filtre, sum(t["kayit"] for t in tablo)))
    for t in tablo:
        ort = "yok" if t["ortalama"] is None else t["ortalama"]
        satir = "- %s: ortalama=%s kayit=%d temsilci=%d" % (_tek_satir(t["ekip"]), ort,
                                                           t["kayit"], t["temsilci"])
        if onc:
            if t["onceki_ortalama"] is None:
                satir += " onceki=yok fark=yok"
            elif t["fark"] is None:
                satir += " onceki=%s onceki_kayit=%d fark=yok" % (t["onceki_ortalama"], t["onceki_kayit"])
            else:
                satir += " onceki=%s onceki_kayit=%d fark=%+d" % (t["onceki_ortalama"], t["onceki_kayit"],
                                                                   t["fark"])
                satir = satir.replace("fark=+0", "fark=0")
        print(satir)
    return 0


def _hazirla(baglanti, args):
    """Ortak: tarih + ekip doğrulama. (bas, bit) ya da None (sebep yazıldı)."""
    try:
        bas, bit = gun_siniri(args.baslangic, args.bitis)
    except ValueError as hata:
        print(hazirlanamadi("tarih geçersiz (%s)" % hata))
        return None
    if args.ekip:
        adlar = [r[0] for r in _sorgula(baglanti, ekipler_sorgusu())]
        if args.ekip not in adlar:
            print(hazirlanamadi("ekip bulunamadı: %s; mevcut ekipler: %s"
                                % (_tek_satir(args.ekip), ", ".join(_tek_satir(a) for a in adlar) or "yok")))
            return None
    return bas, bit


def _filtre_ozeti(args):
    filtre = {}
    if args.tip:
        filtre["tip"] = args.tip
    if args.ekip:
        filtre["ekip"] = args.ekip
    return filtre


def temsilci_ozet_bas(baglanti, args):
    sinir = _hazirla(baglanti, args)
    if not sinir:
        return 1
    tablo = temsilci_tablosu(_sorgula(baglanti, temsilci_ozet_sorgusu(sinir[0], sinir[1], args.tip, args.ekip)))
    if not tablo:
        print(hazirlanamadi("%s için sayılabilir kayıt yok" % ("%s..%s" % (args.baslangic, args.bitis))))
        return 1
    print(kapsam_bolumu("temsilci-ozet", args.baslangic, args.bitis, _filtre_ozeti(args),
                        sum(t["kayit"] for t in tablo)))
    for t in tablo:
        print("- %s: ekip=%s ortalama=%s kayit=%d az_ornek=%s"
              % (_tek_satir(t["temsilci"]), _tek_satir(t["ekip"]), "%g" % t["ortalama"], t["kayit"],
                 "evet" if t["az_ornek"] else "hayir"))
    return 0


def kocluk_bas(baglanti, args):
    sinir = _hazirla(baglanti, args)
    if not sinir:
        return 1
    tablo = kocluk_tablosu(_sorgula(baglanti, kocluk_sorgusu(sinir[0], sinir[1], args.tip, args.ekip)))
    if not tablo:
        print(hazirlanamadi("%s için sayılabilir kayıt yok" % ("%s..%s" % (args.baslangic, args.bitis))))
        return 1
    filtre = _filtre_ozeti(args)
    filtre["kocluk_sonrasi_gelisme"] = "— (ölçütü tanımlı değil; teyit: Quality Supervisor)"
    print(kapsam_bolumu("kocluk", args.baslangic, args.bitis, filtre, sum(t["kayit"] for t in tablo)))
    for t in tablo:
        print("- %s: ekip=%s kayit=%d kocluk_yapilan=%d okunan=%d okunmayan=%d"
              % (_tek_satir(t["temsilci"]), _tek_satir(t["ekip"]), t["kayit"], t["kocluk_yapilan"],
                 t["okunan"], t["okunmayan"]))
    return 0


def kriterler_bas(baglanti, args):
    sinir = _hazirla(baglanti, args)
    if not sinir:
        return 1
    bas, bit = sinir
    ekipler = ekip_tablosu(_sorgula(baglanti, ekip_ozet_sorgusu(bas, bit, args.tip, args.ekip)))
    if not ekipler:
        print(hazirlanamadi("%s için sayılabilir kayıt yok" % ("%s..%s" % (args.baslangic, args.bitis))))
        return 1
    tablo, disi = kriter_tablosu(_sorgula(baglanti, kriter_sorgusu(bas, bit, args.tip, args.ekip)),
                                 [e["ekip"] for e in ekipler])
    filtre = _filtre_ozeti(args)
    kk = _sorgula(baglanti, kriter_kayit_sorgusu(bas, bit, args.tip, args.ekip))
    filtre["kriter_kayit"] = int(kk[0][0]) if kk else 0
    if disi:
        filtre["kapsam_disi"] = ",".join(_tek_satir(e) for e in disi)
    print(kapsam_bolumu("kriterler", args.baslangic, args.bitis, filtre, sum(e["kayit"] for e in ekipler)))
    for k in tablo:
        print("- %s: kaldi=%d kismi=%d gecti=%d oran_kaldi=%.2f"
              % (_tek_satir(k["kriter"]), k["kaldi"], k["kismi"], k["gecti"], k["oran_kaldi"]))
    return 0


def _komutlar():
    ap = argparse.ArgumentParser(description="Kalite veri okuyucusu — salt okunur")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("sema", help="yapı ve izin ölçümü (içerik basmaz)")
    alt.add_parser("ekipler", help="ekip adları ve aktif temsilci sayısı")
    oz = alt.add_parser("ekip-ozet", help="ekip başına kayıt ağırlıklı ortalama")
    oz.add_argument("--baslangic", required=True)
    oz.add_argument("--bitis", required=True)
    oz.add_argument("--karsilastir-baslangic")
    oz.add_argument("--karsilastir-bitis")
    oz.add_argument("--tip", choices=sorted(TIP_ESLEME))
    oz.add_argument("--ekip")
    for ad, yardim in (("temsilci-ozet", "temsilci başına ortalama"),
                       ("kriterler", "kriter başına kaldı/kısmi/geçti"),
                       ("kocluk", "temsilci başına koçluk yapılan / okunan / okunmayan")):
        k = alt.add_parser(ad, help=yardim)
        k.add_argument("--baslangic", required=True)
        k.add_argument("--bitis", required=True)
        k.add_argument("--ekip")
        k.add_argument("--tip", choices=sorted(TIP_ESLEME))
    return ap


def main(argv, ortam=None, baglan=None):
    ap = _komutlar()
    args = ap.parse_args(argv)                     # kullanım hatası: SystemExit(2)
    if args.komut == "ekip-ozet" and bool(args.karsilastir_baslangic) != bool(args.karsilastir_bitis):
        ap.error("--karsilastir-baslangic ve --karsilastir-bitis birlikte verilmeli")
    if ortam is None:
        ortam = ayar.ortam_yukle()
    url = (ortam.get("QA_READONLY_URL") or "").strip()
    if not url:
        print(hazirlanamadi("QA_READONLY_URL yok"))
        return 1
    try:
        baglanti = baglanti_ac(url, baglan)
    except Exception as hata:                      # noqa: BLE001 — iletiyi maskele, URL sızmasın
        print(hazirlanamadi("bağlanılamadı (%s)" % guvenli_hata(hata, url)))
        return 1
    try:
        if args.komut == "sema":
            sema_bas(baglanti)
            return 0
        islev = {"ekipler": lambda: ekipler_bas(baglanti),
                 "ekip-ozet": lambda: ekip_ozet_bas(baglanti, args),
                 "temsilci-ozet": lambda: temsilci_ozet_bas(baglanti, args),
                 "kriterler": lambda: kriterler_bas(baglanti, args),
                 "kocluk": lambda: kocluk_bas(baglanti, args)}.get(args.komut)
        return islev() if islev else 0
    except Exception as hata:                      # noqa: BLE001 — zaman aşımı, izin, kopan bağlantı
        print(hazirlanamadi("sorgu başarısız (%s)" % guvenli_hata(hata, url)))
        return 1
    finally:
        try:
            baglanti.close()
        except Exception:                          # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
