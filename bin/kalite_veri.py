#!/usr/bin/env python3
"""Kalite danışmanının veri okuyucusu — SDR Analyzer Postgres'inden SALT OKUNUR sorgular.

Bağlantı `QA_READONLY_URL` ile `.env`'den gelir (`ayar.ortam_yukle`); rol `qa_okuyucu`'dur.
Yalnız SELECT; her bağlantı `read_only`, `statement_timeout = 15s`, `connect_timeout = 20`.
Bağlantı adresi hiçbir çıktıya, loga ya da hata iletisine girmez. Çağrı transkripti, rapor
gövdesi, müşteri adı, kanıt ve tıbbi işaret alanları hiçbir sorguda yoktur.

Kullanım:
  python3 bin/kalite_veri.py sema     # yapı ve izin ölçümü — içerik basmaz
Çıkış: 0 tamam · 1 durdu (`**Hazırlanamadı:** <sebep>`) · 2 kullanım hatası
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402

BAGLANTI_ZAMAN_ASIMI = 20
SORGU_ZAMAN_ASIMI = "15s"


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
 WHERE "callClassification" IS DISTINCT FROM "reportData"->>'callClassification'
"""),
        ("saat_dilimi", "SELECT current_setting('timezone') AS timezone"),
    ]


def baglan_varsayilan(url):
    import psycopg
    return psycopg.connect(url, connect_timeout=BAGLANTI_ZAMAN_ASIMI)


def baglanti_ac(url, baglan=None):
    """Salt okunur, zaman aşımlı bağlantı. Hata iletisi çağırana URL taşımaz."""
    baglanti = (baglan or baglan_varsayilan)(url)
    baglanti.read_only = True
    with baglanti.cursor() as imlec:
        imlec.execute("SET statement_timeout = '%s'" % SORGU_ZAMAN_ASIMI)
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


def _komutlar():
    ap = argparse.ArgumentParser(description="Kalite veri okuyucusu — salt okunur")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("sema", help="yapı ve izin ölçümü (içerik basmaz)")
    return ap


def main(argv, ortam=None, baglan=None):
    args = _komutlar().parse_args(argv)            # kullanım hatası: SystemExit(2)
    if ortam is None:
        ortam = ayar.ortam_yukle()
    url = (ortam.get("QA_READONLY_URL") or "").strip()
    if not url:
        print(hazirlanamadi("QA_READONLY_URL yok"))
        return 1
    try:
        baglanti = baglanti_ac(url, baglan)
    except Exception as hata:                      # noqa: BLE001 — URL sızmasın: yalnız tür
        print(hazirlanamadi("bağlanılamadı (%s)" % type(hata).__name__))
        return 1
    try:
        if args.komut == "sema":
            sema_bas(baglanti)
        return 0
    finally:
        try:
            baglanti.close()
        except Exception:                          # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
