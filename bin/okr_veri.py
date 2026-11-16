#!/usr/bin/env python3
"""okr_veri.py — OKR Danışmanı'nın veri okuyucusu. SALT OKUNUR.

Nove PYS Postgres'e `okr_okuyucu` rolüyle bağlanır; yalnız SELECT. Bağlantı yalnız `OKR_READONLY_URL`
(`ayar.ortam_yukle()`); adres hiçbir çıktıya girmez. Kullanıcıdan yalnız `id, name` okunur; e-posta, parola,
not sütunları hiçbir sorguda yoktur. Hesap `okr_hesap.py`'dedir.

Kullanım:
  python3 bin/okr_veri.py sema           # yapı, sayım ve izin ölçümü — içerik basmaz
  python3 bin/okr_veri.py donemler       # dönemler ve mali çeyrekler
  python3 bin/okr_veri.py bolumler|objektifler|kr|eksik-veri
        [--donem <kod> | --baslangic YYYY-MM-DD --bitis YYYY-MM-DD] [--bolum <ad|slug>]
  python3 bin/okr_veri.py sirket [--donem <kod> | --baslangic .. --bitis ..]
Aralık verilmezse `app_settings.default_range_start` → bugün (okunamazsa 2025-09-01; kapsamda yazılır).
Çıkış: 0 tamam · 1 durdu (`**Hazırlanamadı:** <sebep>`) · 2 kullanım hatası
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import okr_hesap  # noqa: E402
from kalite_veri import _tek_satir, baglanti_ac, guvenli_hata, hazirlanamadi, js_yuvarla  # noqa: E402

KAYNAK = "Nove PYS Postgres (okr_okuyucu, salt okunur)"

# Sütunlar `okr_hesap.load_tree` satır anahtarlarıyla birebir; sıralama sitedeki gibi
# (Nove Performance lib/queries/tables.ts:94-132). Sayılar double precision, tarihler text: dönüşüm gerekmez.
TABLO_SORGULARI = {
    "periods": ('SELECT id, code, kind::text AS kind, state::text AS state, starts_on, ends_on\n'
                '  FROM public.periods\n ORDER BY starts_on'),
    "departments": ('SELECT id, slug, name_tr\n  FROM public.departments\n ORDER BY sort_order'),
    "users": 'SELECT id, name\n  FROM public.users',
    "objectives": ('SELECT id, code, department_id, period_id, title_tr, owner_user_id, weight\n'
                   '  FROM public.objectives\n ORDER BY code'),
    "key_results": ('SELECT id, objective_id, title_tr, "start", "current", target, unit,\n'
                    '       rollup::text AS rollup, weight, owner_user_id\n'
                    '  FROM public.key_results\n ORDER BY id'),
    "monthly": ('SELECT key_result_id, month, value\n  FROM public.kr_monthly_values'),
}

_SAYIM_TABLOLARI = ("periods", "departments", "users", "objectives", "key_results",
                    "kr_monthly_values", "checkins")


def tablolari_oku(baglanti):
    """`okr_hesap.load_tree`'nin beklediği `rows` sözlüğü: tablo → satır sözlükleri."""
    rows = {}
    for ad, sql in TABLO_SORGULARI.items():
        with baglanti.cursor() as imlec:
            imlec.execute(sql)
            ham = imlec.fetchall()
            sutunlar = [d[0] for d in imlec.description]
        rows[ad] = [dict(zip(sutunlar, satir)) for satir in ham]
    return rows


def checkin_sayisi(baglanti):
    with baglanti.cursor() as imlec:
        imlec.execute("SELECT count(*) FROM public.checkins")
        return int(imlec.fetchall()[0][0])


def sema_sorgulari():
    """(ad, SQL) listesi — yalnız yapı ve sayım; hiçbir satır içeriği okunmaz."""
    sayim = "\nUNION ALL\n".join(
        "SELECT '%s' AS tablo, count(*) AS satir FROM public.%s" % (t, t) for t in _SAYIM_TABLOLARI)
    return [
        ("satir_sayilari", sayim),
        ("users_sutun_izinleri", """
SELECT column_name, privilege_type
  FROM information_schema.column_privileges
 WHERE grantee = current_user
   AND table_schema = 'public'
   AND table_name = 'users'
 ORDER BY column_name
"""),
        ("eposta_izni",
         "SELECT has_column_privilege(current_user, 'public.users', 'email', 'SELECT') AS eposta_okunur"),
        ("app_settings_okunur", "SELECT count(*) FROM public.app_settings"),
        ("oturum", "SELECT current_setting('default_transaction_read_only') AS salt_okunur, "
                   "current_setting('statement_timeout') AS zaman_asimi"),
    ]


def sema_bas(baglanti):
    """Her sorguyu ayrı dener; izin hatası satırı basılır, betik durmaz."""
    for ad, sql in sema_sorgulari():
        try:
            with baglanti.cursor() as imlec:
                imlec.execute(sql)
                satirlar = imlec.fetchall()
        except Exception as hata:            # noqa: BLE001 — sebep görünür olmalı (ANAYASA §2)
            print("- %s: okunamadı (%s)" % (ad, type(hata).__name__))
            try:
                baglanti.rollback()          # hatalı işlem sonraki sorguları bozmasın
            except Exception:                # noqa: BLE001
                pass
            continue
        print("- %s: %d satır" % (ad, len(satirlar)))
        for satir in satirlar:
            print("    " + " | ".join(str(d) for d in satir))


# KAYNAK: Nove Performance lib/queries/settings.ts:14 @ d5d0e5d
VARSAYILAN_BASLANGIC = "2025-09-01"

ORAN_NOTU = "aylık oranların ortalaması; ayların hacmi farklıysa gerçek orandan sapabilir"


def varsayilan_baslangic(baglanti):
    """`(tarih, kaynak)`. Okunamayan/yok/geçersiz ayar yerleşik varsayılana düşer ve düşüş `kaynak`ta yazılır."""
    # KAYNAK: Nove Performance lib/queries/settings.ts:6,24-28 @ d5d0e5d
    try:
        with baglanti.cursor() as imlec:
            imlec.execute("SELECT value FROM public.app_settings WHERE key = 'default_range_start'")
            satirlar = imlec.fetchall()
    except Exception as hata:                        # noqa: BLE001 — düşüş kapsamda görünür
        try:
            baglanti.rollback()                      # hatalı işlem sonraki sorguyu bozmasın
        except Exception:                            # noqa: BLE001
            pass
        return VARSAYILAN_BASLANGIC, "yerleşik varsayılan — app_settings okunamadı (%s)" % type(hata).__name__
    if not satirlar:
        return VARSAYILAN_BASLANGIC, "yerleşik varsayılan — app_settings satırı yok"
    deger = satirlar[0][0]
    if isinstance(deger, str) and okr_hesap.is_valid_iso_date(deger):
        return deger, "app_settings.default_range_start"
    return VARSAYILAN_BASLANGIC, "yerleşik varsayılan — app_settings değeri geçersiz"


def aralik_bayraklari_ekle(ap, bolum=True):
    ap.add_argument("--donem", help="dönem kodu (ör. 2026-FY; liste: donemler)")
    ap.add_argument("--baslangic", help="YYYY-MM-DD (--bitis ile birlikte)")
    ap.add_argument("--bitis", help="YYYY-MM-DD (--baslangic ile birlikte)")
    if bolum:
        ap.add_argument("--bolum", help="bölüm adı ya da slug")
    else:
        ap.set_defaults(bolum=None)


def aralik_bayraklari_dogrula(ap, args):
    """Kullanım hatası (çıkış 2): `--donem` ile tarih birlikte ya da tarihin tek ucu."""
    if args.donem is not None and (args.baslangic is not None or args.bitis is not None):
        ap.error("--donem ile --baslangic/--bitis birlikte verilmez")
    if (args.baslangic is None) != (args.bitis is None):
        ap.error("--baslangic ve --bitis birlikte verilir")


def aralik_coz(args, rows, baglanti, bugun):
    """Aralık sözlüğü ya da `None` (sebep basılmıştır). Geçersiz girdi sessizce varsayılana düşmez."""
    if args.baslangic is not None:
        if not (okr_hesap.is_valid_iso_date(args.baslangic) and okr_hesap.is_valid_iso_date(args.bitis)):
            print(hazirlanamadi("tarih geçersiz: %s..%s (YYYY-MM-DD, gerçek bir gün)"
                                % (_tek_satir(args.baslangic), _tek_satir(args.bitis))))
            return None
        if args.baslangic > args.bitis:
            print(hazirlanamadi("aralık ters: başlangıç %s bitişten %s sonra" % (args.baslangic, args.bitis)))
            return None
        from_, to, kaynak = args.baslangic, args.bitis, "verilen tarih"            # range.ts:156-158
    elif args.donem is not None:
        donem = next((p for p in rows["periods"] if p["code"] == args.donem), None)  # range.ts:160-162
        if donem is None:
            gecerli = ", ".join(p["code"] for p in rows["periods"])
            print(hazirlanamadi("dönem bulunamadı: %s (geçerli: %s)" % (_tek_satir(args.donem), gecerli)))
            return None
        from_, to, kaynak = donem["starts_on"], donem["ends_on"], "dönem %s" % donem["code"]
    else:                                                                         # range.ts:97-110
        from_, ayar_kaynagi = varsayilan_baslangic(baglanti)
        to, kaynak = bugun, "varsayılan (%s)" % ayar_kaynagi
        if from_ > to:
            print(hazirlanamadi("varsayılan başlangıç %s bugünden (%s) sonra" % (from_, bugun)))
            return None
    donemler = okr_hesap.periods_in_range(rows["periods"], from_, to)
    if not donemler:
        print(hazirlanamadi("%s..%s aralığına düşen dönem yok" % (from_, to)))
        return None
    return {"from_": from_, "to": to, "kaynak": kaynak,
            "as_of": okr_hesap.as_of_cutoff(to, bugun), "donemler": donemler}


def kapsam_bolumu(komut, aralik, ek, kayit):
    """Çıktının başındaki `## kapsam`; satır sırası sabit, her değer tek satıra indirilir."""
    n = len(aralik["donemler"])
    satirlar = ["## kapsam",
                "kaynak=%s" % KAYNAK,
                "komut=%s" % _tek_satir(komut),
                "aralik=%s..%s" % (_tek_satir(aralik["from_"]), _tek_satir(aralik["to"])),
                "aralik_kaynagi=%s" % _tek_satir(aralik["kaynak"]),
                "kesim=%s (aralık sonu ile bugünün küçüğü; Europe/Istanbul)" % _tek_satir(aralik["as_of"]),
                "donemler=%s" % ",".join(_tek_satir(p["code"]) for p in aralik["donemler"])]
    if n > 1 and aralik.get("birlesik", True):
        satirlar.append("birlesik=evet — aralık %d dönemi kapsıyor; site gibi birleştirildi" % n)
    satirlar += ["son_tamamlanan_ay=%s" % okr_hesap.last_completed_month(aralik["as_of"]),
                 "birikim=değerler her KR'ın kendi döneminin ilk ayından kesime kadar birikir; ara dilim hesaplanmaz",
                 "ana_yuzde=StD varsa StD, yoksa yıllık (sitenin rozet yüzdesi)",
                 "hesap=Nove Performance d5d0e5d"]
    for anahtar, deger in (ek or {}).items():
        satirlar.append("%s=%s" % (_tek_satir(anahtar), _tek_satir(deger)))
    satirlar.append("kayit=%d" % kayit)
    return "\n".join(satirlar)


def agac_hazirla(baglanti, args, bugun):
    """Komutların ortak girişi: `(aralik, periods, depts, checkin)`; durduysa `None` (sebep basılmıştır)."""
    rows = tablolari_oku(baglanti)
    aralik = aralik_coz(args, rows, baglanti, bugun)
    if aralik is None:
        return None
    periods, depts = okr_hesap.load_tree(rows, [p["id"] for p in aralik["donemler"]], aralik["as_of"])
    return aralik, periods, depts, checkin_sayisi(baglanti)


def donemler_bas(baglanti, bugun):
    rows = tablolari_oku(baglanti)
    donemler = sorted(rows["periods"], key=lambda p: p["starts_on"])
    if not donemler:
        print(hazirlanamadi("dönem yok"))
        return 1
    obj_sayisi = {}
    for o in rows["objectives"]:
        obj_sayisi[o["period_id"]] = obj_sayisi.get(o["period_id"], 0) + 1
    aralik = {"from_": donemler[0]["starts_on"], "to": max(p["ends_on"] for p in donemler),
              "kaynak": "tüm dönemler", "donemler": donemler, "birlesik": False}
    aralik["as_of"] = okr_hesap.as_of_cutoff(aralik["to"], bugun)
    cikti = [kapsam_bolumu("donemler", aralik, None, len(donemler))]
    for p in donemler:
        cikti.append("- %s: tur=%s durum=%s aralik=%s..%s objective=%d" % (
            _tek_satir(p["code"]), p["kind"], p["state"], p["starts_on"], p["ends_on"],
            obj_sayisi.get(p["id"], 0)))
    cikti.append("## mali ceyrekler")
    yillar = []
    for p in donemler:
        if p["state"] == "active":
            fy = okr_hesap.fiscal_year_of(p["starts_on"])
            if fy not in yillar:
                yillar.append(fy)
    for fy in yillar:
        for c in range(1, 5):
            r = okr_hesap.fiscal_quarter_range(fy, c)
            isaret = " (bugün)" if r["starts_on"] <= bugun <= r["ends_on"] else ""
            cikti.append("- %d-FY Ç%d: %s..%s%s" % (fy, c, r["starts_on"], r["ends_on"], isaret))
    cikti.append("not=dönemler yıllıktır; çeyrek sorusunda --baslangic <mali yıl başı> --bitis <çeyrek sonu> "
                 "kullanılır, sayı birikmiştir")
    print("\n".join(cikti))
    return 0


def _turkce_kucuk(metin):
    return metin.replace("İ", "i").replace("I", "ı").lower()


def bolum_bul(depts, ad):
    """`name_tr` ya da `slug` ile (Türkçe küçük harf); bulunamazsa sebep basılır, `None` döner."""
    aranan = _turkce_kucuk(ad)
    for d in depts:
        if aranan in (_turkce_kucuk(d["name_tr"]), _turkce_kucuk(d["slug"])):
            return d
    gecerli = ", ".join(_tek_satir(d["name_tr"]) for d in depts)
    print(hazirlanamadi("bölüm bulunamadı: %s (geçerli: %s)" % (_tek_satir(ad), gecerli)))
    return None


OLCULEBILIR_YOK = "ölçülebilir KR yok"
VERI_YOK = "kesime kadar aylık veri yok"


def sayi_yaz(x):
    metin = ("%.2f" % x).rstrip("0").rstrip(".")
    return "0" if metin == "-0" else metin


def _agirlik_yaz(w):
    return sayi_yaz(w) if okr_hesap.is_set(w) else "yok"


def cift_yaz(cift, olculebilir, sebep=OLCULEBILIR_YOK):
    """O7: ana yüzde `status_pct` (StD varsa StD), yıllık yanında. Ölçülmüş ölçülebilir KR yoksa `—` ve sebep (B7)."""
    if not olculebilir:
        return "yuzde=— std=yok yillik=— durum=— sebep=%s" % sebep
    return "yuzde=%s std=%s yillik=%s durum=%s std_kapsam=%d/%d" % (
        sayi_yaz(cift["status_pct"]), "yok" if cift["std"] is None else sayi_yaz(cift["std"]),
        sayi_yaz(cift["annual"]), okr_hesap.DURUM_ADLARI[okr_hesap.status_of(cift["status_pct"])],
        cift["with_std"], cift["measurable"])


def _olcumlu_olculebilir(krs):
    """Ölçülmüş ağaçta ölçülebilir KR'lar (`progress.ts:73` + `tree.ts:331-333`)."""
    return [k for k in okr_hesap.measured_krs_of(krs) if okr_hesap.is_measurable(k)]


def _sebep(krs):
    """`None`: ölçülmüş ölçülebilir KR var. Yoksa B7 sebebi: ölçülebilir KR var ama hiçbiri kesime kadar ölçülmemiş
    → `kesime kadar aylık veri yok`; hiç ölçülebilir KR yok → `ölçülebilir KR yok`."""
    if _olcumlu_olculebilir(krs):
        return None
    if any(okr_hesap.is_measurable(k) for k in krs):
        return VERI_YOK
    return OLCULEBILIR_YOK


def _cift_kapsamli(cift, krs):
    sebep = _sebep(krs)
    return cift_yaz(cift, sebep is None, sebep or OLCULEBILIR_YOK)


def _kr_sayimi(krs):
    """`(olculmeyen, olculemeyen)` — ayrık: ölçülemeyen KR ölçülmeyen sayılmaz."""
    olculemeyen = len([k for k in krs if not okr_hesap.is_measurable(k)])
    olculmeyen = len([k for k in krs if okr_hesap.is_measurable(k) and not k["measured_by_cutoff"]])
    return olculmeyen, olculemeyen


def en_dusuk_kr(obj):
    """Planın kuralı (sitede karşılığı yok; Kağan 13.11 teyit): ölçülmüş ve ölçülebilir KR'lar içinde en küçük
    `status_pct`; eşitlikte ağırlığı büyük olan (ağırlıksız en sonda), sonra `id`. Aday yoksa `None`."""
    adaylar = _olcumlu_olculebilir(obj["krs"])
    if not adaylar:
        return None

    def anahtar(k):
        w = k.get("weight")
        agirlikli = okr_hesap.is_set(w)
        return (okr_hesap.kr_pair(k)["status_pct"], 0 if agirlikli else 1, -w if agirlikli else 0, str(k["id"]))
    return min(adaylar, key=anahtar)


def _bolum_ek(args, depts):
    """`--bolum` verildiyse tek bölüm ve kapsam `ek`i; bulunamazsa `None` (sebep basılmıştır)."""
    if args.bolum is None:
        return depts, {}
    d = bolum_bul(depts, args.bolum)
    if d is None:
        return None
    return [d], {"bolum": d["name_tr"]}


def bolumler_bas(baglanti, args, bugun):
    hazir = agac_hazirla(baglanti, args, bugun)
    if hazir is None:
        return 1
    aralik, _, depts, _ = hazir
    secim = _bolum_ek(args, depts)
    if secim is None:
        return 1
    secilen, ek = secim
    cikti = [kapsam_bolumu("bolumler", aralik, ek, len(secilen))]
    for d in secilen:
        kr_sayisi = 0
        for o in d["objectives"]:
            kr_sayisi = kr_sayisi + len(o["krs"])
        cikti.append("- %s: %s objective=%d kr=%d" % (
            _tek_satir(d["name_tr"]), _cift_kapsamli(okr_hesap.dept_pair(d), [k for o in d["objectives"] for k in o["krs"]]),
            len(d["objectives"]), kr_sayisi))
    print("\n".join(cikti))
    return 0


def objektifler_bas(baglanti, args, bugun):
    hazir = agac_hazirla(baglanti, args, bugun)
    if hazir is None:
        return 1
    aralik, periods, depts, _ = hazir
    secim = _bolum_ek(args, depts)
    if secim is None:
        return 1
    secilen, ek = secim
    kod_by_period = {p["id"]: p["code"] for p in periods}
    satirlar = []
    for d in secilen:
        for o in d["objectives"]:
            olculmeyen, olculemeyen = _kr_sayimi(o["krs"])
            dusuk = en_dusuk_kr(o)
            if dusuk is None:
                dusuk_yazi = "yok"
            else:
                dusuk_yazi = "%s (%%%s, agirlik=%s%s)" % (
                    _tek_satir(dusuk["title_tr"]), sayi_yaz(okr_hesap.kr_pair(dusuk)["status_pct"]),
                    _agirlik_yaz(dusuk.get("weight")), ", özetten" if dusuk["bridge"] else "")
            satirlar.append(
                "- %s / %s %s: donem=%s agirlik=%s %s kr=%d olculmeyen=%d olculemeyen=%d sorumlu=%s en_dusuk_kr=%s"
                % (_tek_satir(d["name_tr"]), _tek_satir(o["code"]), _tek_satir(o["title_tr"]),
                   _tek_satir(kod_by_period.get(o["period_id"], "yok")), _agirlik_yaz(o.get("weight")),
                   _cift_kapsamli(okr_hesap.obj_pair(o), o["krs"]),
                   len(o["krs"]), olculmeyen, olculemeyen, _tek_satir(o["owner_name"]) or "yok", dusuk_yazi))
    print("\n".join([kapsam_bolumu("objektifler", aralik, ek, len(satirlar))] + (satirlar or ["- objective yok"])))
    return 0


_DURUM_SIRASI = ("above", "expected", "below", "open", "none")


def _dagilim_yaz(ad, yuzdeler):
    """Beş bant (`status.ts:3-24`); pay `js_yuvarla(100 * n / N)` betik hesabıdır, `N == 0` ise `—`."""
    sayim = {k: 0 for k in _DURUM_SIRASI}
    for pct in yuzdeler:
        sayim[okr_hesap.status_of(pct)] += 1
    n_top = len(yuzdeler)
    parcalar = []
    for k in _DURUM_SIRASI:
        pay = "—" if n_top == 0 else "%%%d" % js_yuvarla(100 * sayim[k] / n_top)
        parcalar.append("%s=%d (%s)" % (okr_hesap.DURUM_ADLARI[k], sayim[k], pay))
    return "- %s (n=%d): %s" % (ad, n_top, " · ".join(parcalar))


def sirket_bas(baglanti, args, bugun):
    hazir = agac_hazirla(baglanti, args, bugun)
    if hazir is None:
        return 1
    aralik, _, depts, checkin = hazir
    objektifler = [o for d in depts for o in d["objectives"]]
    krlar = [k for o in objektifler for k in o["krs"]]
    olculmeyen, olculemeyen = _kr_sayimi(krlar)
    # Halka kümesi: ölçülmüş ve ölçülebilir KR'lar, KR'ın status_pct'si (overview.ts:202-215,253-257)
    halka = _olcumlu_olculebilir(krlar)
    kr_yuzdeleri = [okr_hesap.kr_pair(k)["status_pct"] for k in halka]
    obj_yuzdeleri = [okr_hesap.obj_pair(o)["status_pct"] for o in objektifler if _olcumlu_olculebilir(o["krs"])]
    gelisime_acik = len([p for p in kr_yuzdeleri if okr_hesap.is_open_to_development(p)])  # overview.ts:231-234
    ek = {"paylar": "betik hesabı; sitede sayım var, pay yok"}
    if checkin == 0:
        ek["checkin_notu"] = "Nove PYS'de check-in kaydı yok"
    cikti = [kapsam_bolumu("sirket", aralik, ek, len(krlar)),
             "- sirket: %s" % _cift_kapsamli(okr_hesap.company_pair(depts), krlar),
             "- sayim: bolum=%d objective=%d kr=%d olculebilir=%d olculmeyen=%d olculemeyen=%d ozetten=%d" % (
                 len(depts), len(objektifler), len(krlar), len(krlar) - olculemeyen, olculmeyen, olculemeyen,
                 len([k for k in krlar if k["bridge"]])),
             _dagilim_yaz("kr_dagilimi", kr_yuzdeleri),
             _dagilim_yaz("objective_dagilimi", obj_yuzdeleri),
             "- gelisime_acik_kr=%d (%%59 ve altı; Başlamadı dahil)" % gelisime_acik,
             "- checkin=%d" % checkin]
    print("\n".join(cikti))
    return 0


def oran_kr_mi(kr):
    """O3: aylık oranların ortalaması alınan KR (`avg` ve birim `%`)."""
    return kr["rollup"] == "avg" and (kr["unit"] or "").strip() == "%"


OLCULEMIYOR = "ölçülemiyor (hedef = başlangıç)"
KOPRU_NOTU = "aylık satır yok; saklı özet değer"


def _kr_listesi(secilen):
    """`(bölüm, objective, KR)` üçlüleri; bölüm → objective → KR sırası ağaçtaki gibi."""
    return [(d, o, k) for d in secilen for o in d["objectives"] for k in o["krs"]]


def _kr_adi(d, o, k):
    return "%s / %s / %s" % (_tek_satir(d["name_tr"]), _tek_satir(o["code"]), _tek_satir(k["title_tr"]))


def _kr_sebebi(k):
    """`—` taşıyan KR'ın sebebi (B7), yoksa `None`. Ölçülemeyen KR ölçülmeyen sayılmaz (`_kr_sayimi` gibi)."""
    if not okr_hesap.is_measurable(k):
        return OLCULEMIYOR
    if not k["measured_by_cutoff"]:
        return VERI_YOK
    return None


GERIDE_NOTU = "şu an başlangıcın gerisinde; yüzde 0'a kırpılır"


def kr_satiri(d, o, k):
    """Tek KR satırı. Dört durum ayrı (B7): ölçülemiyor · kesime kadar veri yok · saklı özet (not) · gerçek değer."""
    olculmus = k["measured_by_cutoff"]
    sebep = _kr_sebebi(k)
    su_an = sayi_yaz(k["current"]) if olculmus else "—"
    kalan = sayi_yaz(k["target"] - k["current"]) if olculmus else "—"
    if sebep is None:
        cift = okr_hesap.kr_pair(k)
        yuzde = "yuzde=%s std=%s yillik=%s durum=%s" % (
            sayi_yaz(cift["status_pct"]), "yok" if cift["std"] is None else sayi_yaz(cift["std"]),
            sayi_yaz(cift["annual"]), okr_hesap.DURUM_ADLARI[okr_hesap.status_of(cift["status_pct"])])
    else:
        yuzde = "yuzde=— std=yok yillik=— durum=— sebep=%s" % sebep
    satir = ("- %s: hedef=%s baslangic=%s su_an=%s kalan=%s birim=%s kural=%s %s son_dolu_ay=%s agirlik=%s "
             "sorumlu=%s") % (
        _kr_adi(d, o, k), sayi_yaz(k["target"]), sayi_yaz(okr_hesap.effective_start(k)), su_an, kalan, _tek_satir(k["unit"] or "") or "yok",
        _tek_satir(k["rollup"]), yuzde, _tek_satir(k["latest_month"] or "yok"), _agirlik_yaz(k.get("weight")),
        _tek_satir(k["owner_name"]) or "yok")
    if k["bridge"]:
        satir += " not=%s" % KOPRU_NOTU
    if oran_kr_mi(k):
        satir += " oran_notu=evet"
    if sebep is None and _baslangicin_gerisinde(k):
        satir += " ilerleme_notu=%s" % GERIDE_NOTU
    return satir


def _baslangicin_gerisinde(k):
    """Şu an, başlangıçtan hedefin ters yönünde mi? Site bu ilerlemeyi 0'a kırpar (progress.ts:25-31)."""
    bas = okr_hesap.effective_start(k)
    return (k["current"] - bas) * (k["target"] - bas) < 0


def kr_bas(baglanti, args, bugun):
    hazir = agac_hazirla(baglanti, args, bugun)
    if hazir is None:
        return 1
    aralik, _, depts, _ = hazir
    secim = _bolum_ek(args, depts)
    if secim is None:
        return 1
    secilen, ek = secim
    krlar = _kr_listesi(secilen)
    aylar = [k["latest_month"] for _, _, k in krlar if k["latest_month"]]
    ek["son_dolu_ay"] = max(aylar) if aylar else "yok"
    ek["kalan"] = "hedef − şu an (betik hesabı)"
    if any(oran_kr_mi(k) for _, _, k in krlar):
        ek["oran_notu"] = ORAN_NOTU
    cikti = [kapsam_bolumu("kr", aralik, ek, len(krlar))]
    cikti += [kr_satiri(d, o, k) for d, o, k in krlar] or ["- kr yok"]
    cikti.append("## olculemeyenler")
    olculemeyen = ["- %s: %s" % (_kr_adi(d, o, k), _kr_sebebi(k)) for d, o, k in krlar if _kr_sebebi(k)]
    cikti += olculemeyen or ["- yok"]
    print("\n".join(cikti))
    return 0


def eksik_veri_bas(baglanti, args, bugun):
    hazir = agac_hazirla(baglanti, args, bugun)
    if hazir is None:
        return 1
    aralik, _, depts, _ = hazir
    secim = _bolum_ek(args, depts)
    if secim is None:
        return 1
    secilen, ek = secim
    son_ay = okr_hesap.last_completed_month(aralik["as_of"])
    gruplar = {"hic": [], "kesime_kadar": [], "son_ay": []}
    for d, o, k in _kr_listesi(secilen):
        if k["bridge"]:
            grup = "hic"
        elif not k["measured_by_cutoff"]:
            grup = "kesime_kadar"
        elif son_ay in k["period_months"] and son_ay not in k["filled_months"]:
            grup = "son_ay"
        else:
            continue
        gruplar[grup].append("- %s: kural=%s son_dolu_ay=%s sorumlu=%s" % (
            _kr_adi(d, o, k), _tek_satir(k["rollup"]), _tek_satir(k["latest_month"] or "yok"),
            _tek_satir(k["owner_name"]) or "yok"))
    for ad, satirlar in gruplar.items():
        ek[ad] = str(len(satirlar))
    cikti = [kapsam_bolumu("eksik-veri", aralik, ek, sum(len(v) for v in gruplar.values()))]
    for ad, baslik in (("hic", "## hic aylik verisi yok"), ("kesime_kadar", "## kesime kadar verisi yok"),
                       ("son_ay", "## son tamamlanan ayda verisi yok")):
        cikti.append(baslik)
        cikti += gruplar[ad] or ["- yok"]
    print("\n".join(cikti))
    return 0


_ARALIKLI_KOMUTLAR = {
    "bolumler": ("bölüm yüzdeleri", bolumler_bas),
    "objektifler": ("objective yüzdeleri ve en düşük KR", objektifler_bas),
    "sirket": ("şirket yüzdesi, sayım ve durum dağılımı", sirket_bas),
    "kr": ("KR başına hedef, şu an, yüzde ve ölçülemeyenler", kr_bas),
    "eksik-veri": ("aylık verisi eksik KR'lar", eksik_veri_bas),
}


def _komutlar():
    ap = argparse.ArgumentParser(description="OKR veri okuyucusu — salt okunur")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("sema", help="yapı, sayım ve izin ölçümü (içerik basmaz)")
    alt.add_parser("donemler", help="dönemler ve mali çeyrekler")
    aralikli = {}
    for ad, (yardim, _) in _ARALIKLI_KOMUTLAR.items():
        aralikli[ad] = alt.add_parser(ad, help=yardim)
        aralik_bayraklari_ekle(aralikli[ad], bolum=(ad != "sirket"))
    return ap, aralikli


def main(argv, ortam=None, baglan=None, bugun=None):
    ap, aralikli = _komutlar()
    args = ap.parse_args(argv)                     # kullanım hatası: SystemExit(2)
    if args.komut in aralikli:
        aralik_bayraklari_dogrula(aralikli[args.komut], args)
    if bugun is None:
        bugun = okr_hesap.today_in_istanbul()
    elif not (isinstance(bugun, str) and okr_hesap.is_valid_iso_date(bugun)):
        print(hazirlanamadi("bugün geçersiz: %s" % _tek_satir(bugun)))
        return 1
    if ortam is None:
        ortam = ayar.ortam_yukle()
    url = (ortam.get("OKR_READONLY_URL") or "").strip()
    if not url:
        print(hazirlanamadi("OKR_READONLY_URL yok"))
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
        if args.komut == "donemler":
            return donemler_bas(baglanti, bugun)
        if args.komut in _ARALIKLI_KOMUTLAR:
            return _ARALIKLI_KOMUTLAR[args.komut][1](baglanti, args, bugun)
        return 0
    except Exception as hata:                      # noqa: BLE001
        print(hazirlanamadi("sorgu başarısız (%s)" % guvenli_hata(hata, url)))
        return 1
    finally:
        try:
            baglanti.close()
        except Exception:                          # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
