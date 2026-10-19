"""Danışman formu hattı (docs/superpowers/specs/2026-10-19-advisor-form-pipeline-design.md).

Ağ yok, para harcamaz; betik geçici bir kökte koşar, gerçek `takimlar/`'a dokunmaz.
python3 -m unittest discover -s tests
"""
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))


class KilitTesti(unittest.TestCase):
    """K6: insanın dosyaları kuralla değil yetkiyle kapalı; eski altı kilit de yerinde (12'nin 12'si)."""

    def test_insan_dosyalari_yetkiyle_kilitli(self):
        deny = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]["deny"]
        beklenen = ["Read(./.env)", "Read(./.env.*)"]
        for yol in ("./yanitlar/**", "./formlar/onayli/**", "./takimlar/*/kurallar.md",
                    "./ANAYASA.md", "./sirket/CEO-KIMLIGI.md"):
            beklenen += [f"Write({yol})", f"Edit({yol})"]
        self.assertEqual(len(beklenen), 12)
        for satir in beklenen:
            with self.subTest(satir=satir):
                self.assertIn(satir, deny)


if __name__ == "__main__":
    unittest.main()
