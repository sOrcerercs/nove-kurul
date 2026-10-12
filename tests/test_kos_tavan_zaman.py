"""`kos()` bir çalışırken tek bir zaman damgası kullanmalı — `zaman` (dosya adı, üstbilgi,
`durum.json`) ile `tavan_karari`'ye giden gün AYRI okunursa gece yarısını geçen bir koşu
günlük sayımı yanlış güne yazabilir.

python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import kos  # noqa: E402


def sahte_kok(tmp, ad="deneme"):
    kok = Path(tmp) / "kok"
    dizin = kok / "takimlar" / ad
    (dizin / "kosu").mkdir(parents=True)
    (dizin / "takim.md").write_text("---\nname: %s\n---\n" % ad, encoding="utf-8")
    (dizin / "durum.json").write_text(json.dumps(
        {"takim": ad, "son_kosu": None, "son_sonuc": None, "kuyruk": []},
        ensure_ascii=False), encoding="utf-8")
    return kok


class TavanKarariTekZamanTesti(unittest.TestCase):
    def test_tavan_karari_kosunun_kendi_zamanini_alir_ikinci_saat_okumaz(self):
        """`ayar.simdi_iso()` sabitlenir; `tavan_karari`'ye giden `simdi` ondan türemeli,
        gerçek `datetime.now()`'dan DEĞİL. Eski kod bu testi kırardı: ikinci bir saat
        okuması yapıp gerçek 'şimdi'yi geçirirdi."""
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            sabit_zaman = "2026-09-17T23:59:59+03:00"
            cagrilar = []

            def sahte_tavan(kok_, takim, simdi):
                cagrilar.append(simdi)
                return False, "test durdurma"

            with mock.patch.object(kos.ayar, "KOK", kok), mock.patch.object(kos, "KOK", kok), \
                    mock.patch.object(kos.ayar, "simdi_iso", return_value=sabit_zaman), \
                    mock.patch.object(kos.ayar, "mesaide_mi", return_value=True), \
                    mock.patch.object(kos, "tavan_karari", sahte_tavan):
                kos.kos("deneme", zorla=False)

            self.assertEqual(len(cagrilar), 1, "tavan_karari tam olarak bir kez çağrılmalı")
            self.assertEqual(cagrilar[0], datetime.fromisoformat(sabit_zaman),
                             "tavan_karari, kos()'un kendi 'zaman'ından türeyen saati almalı")


if __name__ == "__main__":
    unittest.main()
