#!/usr/bin/env python3
"""Kalite danışmanının veri okuyucusu — SDR Analyzer Postgres'inden SALT OKUNUR sorgular.

Bağlantı `QA_READONLY_URL` ile `.env`'den gelir (`ayar.ortam_yukle`); rol `qa_okuyucu`'dur.
Yalnız SELECT; her bağlantı `read_only`, `statement_timeout = 15s` (bağlantı seçeneği), `connect_timeout = 20`.
Bağlantı adresi hiçbir çıktıya, loga ya da hata iletisine girmez. Çağrı transkripti, rapor
gövdesi, müşteri adı, kanıt ve tıbbi işaret alanları hiçbir sorguda yoktur.

Kullanım:
  python3 bin/kalite_veri.py sema     # yapı ve izin ölçümü — içerik basmaz
Çıkış: 0 tamam · 1 durdu (`**Hazırlanamadı:** <sebep>`) · 2 kullanım hatası
"""
import argparse
import math
import re
import sys
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
SAAT_DILIMI = "sunucu saati (varsayılan UTC)"


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
    return 0 if sonuc == 0 else sonuc


def kapsam_bolumu(komut, baslangic, bitis, filtre, kayit):
    """Çıktının başındaki `## kapsam` bölümü: hangi veri, hangi kuralla, kaç kayıt."""
    satirlar = ["## kapsam",
                "kaynak=SDR Analyzer Postgres (qa_okuyucu, salt okunur)",
                "komut=%s" % komut,
                "aralik=%s..%s" % (baslangic, bitis),
                "saat_dilimi=%s" % SAAT_DILIMI,
                "kural=AGENT/TEAM_LEADER, aktif, callClassification NULL ya da CONNECTED_QUALIFIED"]
    for anahtar, deger in (filtre or {}).items():
        satirlar.append("%s=%s" % (anahtar, deger))
    satirlar.append("kayit=%d" % kayit)
    return "\n".join(satirlar)


def guvenli_hata(hata, url):
    """Tür adı + mesaj; adres, `://` sonrası kimlik ve parola parçaları `***`."""
    mesaj = str(hata)
    if url:
        mesaj = mesaj.replace(url, "***")
    mesaj = re.sub(r"://[^@/\s\"']*@", "://***@", mesaj)
    mesaj = re.sub(r"(?i)password\s*=\s*\S+", "password=***", mesaj)
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
    except Exception as hata:                      # noqa: BLE001 — iletiyi maskele, URL sızmasın
        print(hazirlanamadi("bağlanılamadı (%s)" % guvenli_hata(hata, url)))
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
