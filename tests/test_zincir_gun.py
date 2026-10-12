"""Zincirin gün koşulu — `qa-haftalik` yalnız cuma koşusundan tetiklenmeli.

Neden var: Faz 6'da qa-hatti günlüğe geçince kuyruk id'si `qa-{hafta}`'dan
`qa-{tarih}`'e döndü. `ZINCIR`'deki `^qa-(.+)$` deseni ikisini de yakalıyor,
dolayısıyla `haftalik-rapor` her gün kuyruğa giriyor ve günde ~1 USD'lik
gereksiz koşu açılıyordu. Kalite bölümü yalnız cuma koşusunda (KR 2.2'nin
üretildiği koşu) anlamlı.

python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import dagitici  # noqa: E402

CUMA = datetime(2026, 9, 18, 9, 0)
PAZARTESI = datetime(2026, 9, 21, 9, 0)

TAKIM_MD = "---\nname: {ad}\ndescription: {ad} — test.\ntools: [Read]\nbutce_usd: 1\n---\n\n# {ad}\n"


def sahte_kok(tmp, kuyruklar):
    kok = Path(tmp) / "kok"
    for ad, kuyruk in kuyruklar.items():
        dizin = kok / "takimlar" / ad
        dizin.mkdir(parents=True)
        (dizin / "takim.md").write_text(TAKIM_MD.format(ad=ad), encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps(
            {"takim": ad, "kuyruk": kuyruk}, ensure_ascii=False), encoding="utf-8")
    return kok


def hedef_kuyruk(kok, takim):
    return json.loads((kok / "takimlar" / takim / "durum.json").read_text(
        encoding="utf-8")).get("kuyruk") or []


# Gün koşulu ve koşulsuz zincirin davranışı — gerçek ZINCIR tablosundan bağımsız, testin kendi kuralları.
KURALLAR = [
    {"ad": "kasa-celiski", "desen": __import__("re").compile(r"^kasa-(.+)$"), "takim": "karar-takibi",
     "id": "cel-{0}", "not": "çözülmemiş çelişki"},
    {"ad": "qa-haftalik", "desen": __import__("re").compile(r"^qa-(.+)$"), "takim": "haftalik-rapor", "gun": 4,
     "id": "qa-{0}", "not": "cuma koşusu bitti; kalite bölümü ekle"},
]


class ZincirGunKosuluTesti(unittest.TestCase):

    def setUp(self):
        yama = unittest.mock.patch.object(dagitici, "ZINCIR", KURALLAR)
        yama.start()
        self.addCleanup(yama.stop)

    def _kos(self, simdi, qa_id="qa-2026-09-18"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kok = sahte_kok(tmp.name, {
            "qa-hatti": [{"id": qa_id, "durum": "tamam", "not": "günlük rapor"}],
            "haftalik-rapor": [],
        })
        yazilan = dagitici.zinciri_isle(kok, "qa-hatti", simdi=simdi)
        return yazilan, hedef_kuyruk(kok, "haftalik-rapor")

    def test_cuma_zinciri_kurar(self):
        yazilan, kuyruk = self._kos(CUMA)
        self.assertEqual(len(yazilan), 1, "cuma koşusu kalite bölümünü tetiklemeli")
        self.assertEqual(len(kuyruk), 1)

    def test_pazartesi_zincir_kurmaz(self):
        yazilan, kuyruk = self._kos(PAZARTESI)
        self.assertEqual(yazilan, [], "cuma dışı günlük koşu zincir kurmamalı")
        self.assertEqual(kuyruk, [], "haftalik-rapor kuyruğuna madde düşmemeli")

    def test_gun_kosulu_olmayan_zincir_her_gun_calisir(self):
        """`kasa-celiski` gün koşulu taşımıyor — davranışı değişmemeli."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kok = sahte_kok(tmp.name, {
            "kasa-bakimi": [{"id": "kasa-2026-09-21", "durum": "tamam", "not": "çelişki"}],
            "karar-takibi": [],
        })
        yazilan = dagitici.zinciri_isle(kok, "kasa-bakimi", simdi=PAZARTESI)
        self.assertEqual(len(yazilan), 1)
        self.assertEqual(len(hedef_kuyruk(kok, "karar-takibi")), 1)

    def test_simdi_verilmezse_bugun_kullanilir(self):
        """Çağıranlar `simdi` geçirmeyebilir; imza geriye dönük uyumlu kalmalı."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kok = sahte_kok(tmp.name, {"qa-hatti": [], "haftalik-rapor": []})
        self.assertEqual(dagitici.zinciri_isle(kok, "qa-hatti"), [])


class NotZorunluTesti(unittest.TestCase):
    """`not_zorunlu`: kaynak `zincir_not` bırakmadıysa zincir kurulmaz."""

    KURAL = [{"ad": "deneme-zinciri", "desen": __import__("re").compile(r"^okr-(.+)$"),
              "takim": "hedef", "id": "okr-{0}", "not_zorunlu": True,
              "not": "genel metin"}]

    def _kos(self, zincir_not):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        oge = {"id": "okr-2026-10", "durum": "tamam", "not": "aylık"}
        if zincir_not is not None:
            oge["zincir_not"] = zincir_not
        kok = sahte_kok(tmp.name, {"kaynak": [oge], "hedef": []})
        with unittest.mock.patch.object(dagitici, "ZINCIR", self.KURAL):
            yazilan = dagitici.zinciri_isle(kok, "kaynak", simdi=CUMA)
        return yazilan, hedef_kuyruk(kok, "hedef")

    def test_not_varsa_kurar_ve_notu_tasir(self):
        yazilan, kuyruk = self._kos("KR 2.1 skor tanımı, KR 2.3 baz rakam")
        self.assertEqual(len(yazilan), 1)
        self.assertEqual(kuyruk[0]["not"], "KR 2.1 skor tanımı, KR 2.3 baz rakam")

    def test_not_yoksa_kurmaz(self):
        yazilan, kuyruk = self._kos(None)
        self.assertEqual(yazilan, [], "içeriksiz madde açılmamalı")
        self.assertEqual(kuyruk, [])

    def test_not_yoksa_atlama_stderre_loglanir(self):
        """Sessiz `continue` ajanın notu UNUTMASI ile kasıtlı susmayı ayırt edilemez
        kılıyordu — atlandığında en az bir satır stderr çıktısı olmalı."""
        import io
        buf = io.StringIO()
        with unittest.mock.patch("sys.stderr", buf):
            self._kos(None)
        self.assertIn("okr-2026-10", buf.getvalue())

    def test_bos_not_da_kurmaz(self):
        yazilan, kuyruk = self._kos("   ")
        self.assertEqual(yazilan, [])
        self.assertEqual(kuyruk, [])

    def test_not_zorunlu_olmayan_kural_etkilenmez(self):
        """Mevcut iki ZINCIR maddesi `not_zorunlu` taşımıyor; davranışları aynı kalmalı."""
        kural = [{**self.KURAL[0]}]
        del kural[0]["not_zorunlu"]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kok = sahte_kok(tmp.name, {
            "kaynak": [{"id": "okr-2026-10", "durum": "tamam", "not": "aylık"}],
            "hedef": []})
        with unittest.mock.patch.object(dagitici, "ZINCIR", kural):
            yazilan = dagitici.zinciri_isle(kok, "kaynak", simdi=CUMA)
        self.assertEqual(len(yazilan), 1)
        self.assertEqual(hedef_kuyruk(kok, "hedef")[0]["not"], "genel metin")


if __name__ == "__main__":
    unittest.main()
