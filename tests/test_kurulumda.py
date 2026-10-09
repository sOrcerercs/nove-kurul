"""Kurulumdaki danışman — `takim.md`'si var ama tanımı (frontmatter) henüz yok.

NOVE-KURULUM.md Faz 6: "Bir danışman ancak verisi bağlıysa devreye girer. Verisi olmayan danışman sahnede
'kurulumda' olarak görünür." Danışman klasörleri formdan doldurulmadan önce yalnız başlıklı bir `takim.md`
ile açılıyor; sürücü bunları kurulu takım sanıp koşturmamalı, ajan dosyası üretmemeli.
"""
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))
import agents_uret  # noqa: E402
import ayar  # noqa: E402
import dagitici  # noqa: E402
import kos  # noqa: E402
import io  # noqa: E402
from contextlib import redirect_stdout  # noqa: E402
from unittest import mock  # noqa: E402

KURULU = """---
name: kalite
description: Kalite danışmanı olarak kurulun kalite sorularını yanıtlamak.
skills: []
---

# Kalite Danışmanı
"""
KURULUMDA = "# Finans Danışmanı\n"


class KurulumdaTesti(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.kok = Path(self._gecici.name)
        for ad, metin in (("kalite", KURULU), ("finans", KURULUMDA)):
            (self.kok / "takimlar" / ad).mkdir(parents=True)
            (self.kok / "takimlar" / ad / "takim.md").write_text(metin, encoding="utf-8")
        (self.kok / "takimlar" / "_iskelet").mkdir(parents=True)
        (self.kok / "takimlar" / "_iskelet" / "takim.md").write_text(KURULU, encoding="utf-8")

    def tearDown(self):
        self._gecici.cleanup()

    def test_frontmattersiz_takim_kurulumda_sayilir(self):
        self.assertTrue(ayar.kurulumda_mi("finans", self.kok))
        self.assertFalse(ayar.kurulumda_mi("kalite", self.kok))

    def test_olmayan_takim_kurulumda_degildir(self):
        self.assertFalse(ayar.kurulumda_mi("yok", self.kok))

    def test_kurulu_takimlar_kurulumdakileri_ve_iskeleti_disarida_birakir(self):
        self.assertEqual(ayar.kurulu_takimlar(self.kok), ["kalite"])

    def test_dagitici_yalniz_kurulu_takimlari_gorur(self):
        self.assertEqual(dagitici.takimlar(self.kok), ["kalite"])

    def test_dagitici_kurulumdaki_takimi_sebebiyle_kosturmaz(self):
        simdi = datetime(2026, 10, 9, 10, 0).astimezone()
        kossun, sebep = dagitici.tetik_karari(self.kok, "finans", simdi)
        self.assertFalse(kossun)
        self.assertIn("kurulumda", sebep)

    def test_kurulumdaki_takim_icin_ajan_dosyasi_uretilmez(self):
        agents_uret.uret(self.kok)
        uretilen = sorted(p.stem for p in (self.kok / ".claude" / "agents").glob("*.md"))
        self.assertEqual(uretilen, ["kalite"])

    def test_kos_kurulumdaki_danismani_kuru_bile_kosturmaz(self):
        """Elle `python3 bin/kos.py finans --kuru` çağrılsa bile kurulumdaki danışman koşmaz ve sebebi söylenir."""
        cikti = io.StringIO()
        with mock.patch.object(ayar, "KOK", self.kok), mock.patch.object(kos, "KOK", self.kok), \
                redirect_stdout(cikti):
            kod = kos.main(["finans", "--kuru"])
        self.assertEqual(kod, 0)
        self.assertIn("kurulumda", cikti.getvalue())
        self.assertNotIn("kuru koşu —", cikti.getvalue())


if __name__ == "__main__":
    unittest.main()
