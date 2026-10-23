"""Danışman koşusunun yazma kapsamı — ağ yok, claude çağrısı yok, para harcamaz.

Son inceleme, Kritik 1 (19.10.2026): danışman çıplak `Write` ve `--permission-mode acceptEdits` ile koşunca
`bin/kalite_veri.py`'yi değiştirip izinli komutla çalıştırabiliyordu — `.env`'deki her anahtara erişim. Karar (Kağan,
20.10.2026, A): her danışman yalnız kendi klasörüne yazar; izin listesinde olmayan her araç sorulmadan reddedilir
(`dontAsk`). 20.10.2026 canlı deneme: `acceptEdits` + `Write` → `bin/` dosyası değişti; `dontAsk` +
`Write(…)` + `Edit(./takimlar/deneme/**)` → klasör içi yazıldı, `bin/` reddedildi. Aynı gün ikinci deneme: yol kuralı
yalnız `Edit(…)` olarak işliyor (Write dahil her yazma aracını kapsar); tek başına `Write(…)` alt klasöre yazmayı da reddetti.

python3 -m unittest discover -s tests
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import kos  # noqa: E402


class YazmaKapsamiTesti(unittest.TestCase):
    def test_ciplak_yazma_araclari_kendi_klasorune_daralir(self):
        self.assertEqual(kos.yazma_kapsami(["Read", "Write", "Edit", "Glob"], "kalite"),
                         ["Read", "Edit(./takimlar/kalite/**)", "Glob"])

    def test_baska_klasore_acilan_yazma_kendi_klasorune_cevrilir(self):
        self.assertEqual(kos.yazma_kapsami(["Write(./bin/**)", "Edit(//etc/**)"], "kalite"),
                         ["Edit(./takimlar/kalite/**)"])

    def test_diger_duzenleme_araclari_de_daralir(self):
        self.assertEqual(kos.yazma_kapsami(["MultiEdit", "NotebookEdit"], "okr"),
                         ["Edit(./takimlar/okr/**)"])

    def test_izinli_komut_ve_okuma_araclari_dokunulmaz(self):
        araclar = ["Read", "Glob", "Grep", "Bash(python3 bin/kalite_veri.py:*)"]
        self.assertEqual(kos.yazma_kapsami(araclar, "kalite"), araclar)


class KomutTesti(unittest.TestCase):
    def test_izin_listesi_disindaki_arac_sorulmadan_reddedilir(self):
        komut = kos.claude_komutu("istem", ["Read"], 2)
        self.assertEqual(komut[komut.index("--permission-mode") + 1], "dontAsk")
        self.assertNotIn("acceptEdits", komut)

    def test_cikti_kesen_komutlar_yasak(self):
        """23.10.2026 uçtan uca deneme: danışman betik çıktısını `| head -14` ile kesip görmediği satır hakkında
        iddia kurdu (AJAN-KIMLIGI "Veriyi kesmeden oku"). Canlı deneme: --disallowedTools ile `| head` reddedildi."""
        komut = kos.claude_komutu("istem", ["Read"], 2)
        yasak = komut[komut.index("--disallowedTools") + 1].split(",")
        for arac in ("Bash(head:*)", "Bash(tail:*)", "Bash(grep:*)", "Bash(cut:*)", "Bash(sed:*)", "Bash(awk:*)"):
            self.assertIn(arac, yasak)

    def test_alt_surece_daraltilmis_araclar_gider(self):
        fm = {"model": "sonnet", "tools": ["Read", "Write", "Bash(python3 bin/kalite_veri.py:*)"]}
        sahte = mock.Mock(stdout=json.dumps({"is_error": False, "result": "ok"}), stderr="", returncode=0)
        with mock.patch.object(kos.subprocess, "run", return_value=sahte) as calisti:
            kos._claude_kos("istem", fm, "kalite", Path("/tmp/yok.md"))
        komut = calisti.call_args.args[0]
        self.assertEqual(komut[komut.index("--allowedTools") + 1],
                         "Read,Edit(./takimlar/kalite/**),Bash(python3 bin/kalite_veri.py:*)")

    def test_tools_yoksa_varsayilan_da_daralir(self):
        sahte = mock.Mock(stdout=json.dumps({"is_error": False, "result": "ok"}), stderr="", returncode=0)
        with mock.patch.object(kos.subprocess, "run", return_value=sahte) as calisti:
            kos._claude_kos("istem", {"model": "sonnet"}, "finans", Path("/tmp/yok.md"))
        komut = calisti.call_args.args[0]
        self.assertEqual(komut[komut.index("--allowedTools") + 1], "Read,Edit(./takimlar/finans/**),Glob,Grep")


if __name__ == "__main__":
    unittest.main()
