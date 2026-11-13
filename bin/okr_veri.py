#!/usr/bin/env python3
"""okr_veri.py — OKR Danışmanı'nın veri okuyucusu. SALT OKUNUR.

Nove PYS Postgres'e `okr_okuyucu` rolüyle bağlanır; yalnız SELECT. Bağlantı yalnız `OKR_READONLY_URL`
(`ayar.ortam_yukle()`); adres hiçbir çıktıya girmez. Kullanıcıdan yalnız `id, name` okunur; e-posta, parola,
not sütunları hiçbir sorguda yoktur. Hesap `okr_hesap.py`'dedir.

Kullanım: python3 bin/okr_veri.py sema
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import okr_hesap  # noqa: E402
from kalite_veri import _tek_satir, baglanti_ac, guvenli_hata, hazirlanamadi  # noqa: E402

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


def aralik_bayraklari_ekle(ap):
    ap.add_argument("--donem", help="dönem kodu (ör. p-2026-fy)")
    ap.add_argument("--baslangic", help="YYYY-MM-DD (--bitis ile birlikte)")
    ap.add_argument("--bitis", help="YYYY-MM-DD (--baslangic ile birlikte)")
    ap.add_argument("--bolum", help="bölüm adı ya da slug")


def aralik_bayraklari_dogrula(ap, args):
    """Kullanım hatası (çıkış 2): `--donem` ile tarih birlikte ya da tarihin tek ucu."""
    if args.donem and (args.baslangic or args.bitis):
        ap.error("--donem ile --baslangic/--bitis birlikte verilmez")
    if bool(args.baslangic) != bool(args.bitis):
        ap.error("--baslangic ve --bitis birlikte verilir")


def aralik_coz(args, rows, baglanti, bugun):
    """Aralık sözlüğü ya da `None` (sebep basılmıştır). Geçersiz girdi sessizce varsayılana düşmez."""
    if args.baslangic:
        if not (okr_hesap.is_valid_iso_date(args.baslangic) and okr_hesap.is_valid_iso_date(args.bitis)):
            print(hazirlanamadi("tarih geçersiz: %s..%s (YYYY-MM-DD, gerçek bir gün)"
                                % (_tek_satir(args.baslangic), _tek_satir(args.bitis))))
            return None
        if args.baslangic > args.bitis:
            print(hazirlanamadi("aralık ters: başlangıç %s bitişten %s sonra" % (args.baslangic, args.bitis)))
            return None
        from_, to, kaynak = args.baslangic, args.bitis, "verilen tarih"            # range.ts:156-158
    elif args.donem:
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
            cikti.append("- Ç%d: %s..%s%s" % (c, r["starts_on"], r["ends_on"], isaret))
    cikti.append("not=dönemler yıllıktır; çeyrek sorusunda --baslangic <mali yıl başı> --bitis <çeyrek sonu> "
                 "kullanılır, sayı birikmiştir")
    print("\n".join(cikti))
    return 0


def _komutlar():
    ap = argparse.ArgumentParser(description="OKR veri okuyucusu — salt okunur")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("sema", help="yapı, sayım ve izin ölçümü (içerik basmaz)")
    alt.add_parser("donemler", help="dönemler ve mali çeyrekler")
    return ap


def main(argv, ortam=None, baglan=None, bugun=None):
    args = _komutlar().parse_args(argv)            # kullanım hatası: SystemExit(2)
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
