"""Stop hook süresi, bekçinin en kötü durumdaki süresinden uzun olmalı.

NIM zaman aşımına uğrarsa bekçi Haiku yedeğine düşer; hook bundan önce öldürülürse koşu denetimsiz kalır.
"""
import json
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "bin"))
import bekci  # noqa: E402


class StopHookSuresi(unittest.TestCase):
    def test_hook_nim_ve_yedekten_uzun(self):
        ayarlar = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))
        sureler = [h["timeout"] for grup in ayarlar["hooks"]["Stop"] for h in grup["hooks"]
                   if "bekci.py" in h["command"]]
        self.assertTrue(sureler)
        for sure in sureler:
            self.assertGreater(sure, bekci.NIM_ZAMAN_ASIMI_SN + bekci.ZAMAN_ASIMI_SN)


if __name__ == "__main__":
    unittest.main()
