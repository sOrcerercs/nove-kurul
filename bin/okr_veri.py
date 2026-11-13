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
import okr_hesap  # noqa: E402,F401
from kalite_veri import baglanti_ac, guvenli_hata, hazirlanamadi  # noqa: E402,F401

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


def _komutlar():
    ap = argparse.ArgumentParser(description="OKR veri okuyucusu — salt okunur")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("sema", help="yapı, sayım ve izin ölçümü (içerik basmaz)")
    return ap


def main(argv, ortam=None, baglan=None, bugun=None):
    args = _komutlar().parse_args(argv)            # kullanım hatası: SystemExit(2)
    if bugun is None:
        bugun = okr_hesap.today_in_istanbul()      # sonraki görevler kullanır
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
