"""Ön hazırlık testleri — ağ yok, claude çağrısı yok, para harcamaz.

Neden var: 2026-09-16 09:00 koşusunda `haftalik-rapor` düştü. Ajan
`python3 bin/repo_ozet.py --gun 7` çağırdı, komut Claude Code'un 120 sn'lik ön
plan Bash sınırını aştı, arka plana alındı ("bittiğinde haber verilecek") ve
başsız `claude -p` oturumu 12 dakika bekleyip 15 dk tavanına çarptı. Komut
aslında 09:03'te bitmişti; ajan sonucu hiç alamadı.

Çözüm: yavaş komutu sürücü ajan çağrılmadan önce kendisi koşturur, çıktıyı
`takimlar/<takim>/veri/<ad>.txt` dosyasına yazar, ajan yalnız `Read` eder.

python3 -m unittest discover -s tests
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "bin"))
import kos  # noqa: E402

TAKIM_MD = """---
name: {ad}
description: {ad} takımı — test.
tools: [Read, Write]
gerekli_anahtarlar: []
onhazirlik: [{onhazirlik}]
butce_usd: 2
---

# {ad}
"""


def sahte_kok(tmp, ad="deneme", onhazirlik=""):
    kok = Path(tmp) / "kok"
    dizin = kok / "takimlar" / ad
    (dizin / "kosu").mkdir(parents=True)
    (dizin / "takim.md").write_text(
        TAKIM_MD.format(ad=ad, onhazirlik=onhazirlik), encoding="utf-8")
    (dizin / "durum.json").write_text(json.dumps(
        {"takim": ad, "son_kosu": None, "son_sonuc": None, "kuyruk": []},
        ensure_ascii=False), encoding="utf-8")
    return kok


class DosyaAdiTesti(unittest.TestCase):
    """Komuttan türetilen dosya adı okunur ve çakışmasız olmalı."""

    def test_python_scriptinin_adi_kullanilir(self):
        self.assertEqual(kos.onhazirlik_adi("python3 bin/repo_ozet.py --gun 7", 0), "repo_ozet")
        self.assertEqual(kos.onhazirlik_adi("python3 bin/claude_gecmis.py --gun 7", 1), "claude_gecmis")

    def test_script_yoksa_sirali_ada_duser(self):
        self.assertEqual(kos.onhazirlik_adi("gh pr list --limit 5", 2), "onhazirlik-3")


class AcikAdTesti(unittest.TestCase):
    """`ad = komut` biçimi: aynı script'ten iki farklı çıktı üretilebilsin.

    Neden var: `qa-hatti` hem günlük (`qa_ozet.py --gun`) hem haftalık
    (`qa_ozet.py`) çıktıya dayanıyor. Ad `.py` kökünden türeyince ikisi de
    `qa_ozet.txt`'e yazıyor ve günlük koşu, cuma KR 2.2 dalının okuduğu
    haftalık dosyayı eziyordu. `veri/` gitignore'da — ezilen geri gelmez.
    """

    def test_acik_ad_script_adinin_onune_gecer(self):
        self.assertEqual(
            kos.onhazirlik_adi("qa_gun = python3 bin/qa_ozet.py --gun", 0), "qa_gun")

    def test_acik_ad_yoksa_davranis_degismez(self):
        """Diğer üç takım bu değişiklikten etkilenmemeli."""
        self.assertEqual(kos.onhazirlik_adi("python3 bin/qa_ozet.py --gun", 0), "qa_ozet")
        self.assertEqual(kos.onhazirlik_adi("python3 bin/repo_ozet.py --gun 7", 0), "repo_ozet")
        self.assertEqual(kos.onhazirlik_adi("gh pr list --limit 5", 2), "onhazirlik-3")

    def test_ortam_degiskeni_oneki_ad_sayilmaz(self):
        """`FOO=bar komut` bir ad ataması değil; boşluklu `=` şart."""
        self.assertEqual(
            kos.onhazirlik_adi("TZ=UTC python3 bin/repo_ozet.py", 0), "repo_ozet")

    def test_guvensiz_ad_reddedilir(self):
        """Ad dosya adına giriyor — yol ayracı ve nokta kabul edilmez."""
        for kotu in ("../kacis = python3 bin/qa_ozet.py",
                     "a/b = python3 bin/qa_ozet.py",
                     "qa.gun = python3 bin/qa_ozet.py"):
            self.assertEqual(kos.onhazirlik_adi(kotu, 0), "qa_ozet", kotu)

    def test_acik_adla_komut_calisir_ve_dosya_o_ada_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            sonuc = kos.onhazirlik_kos("deneme", ["gunluk = echo merhaba-gun"], kok=kok)
            self.assertTrue(sonuc[0]["tamam"], sonuc[0].get("neden"))
            yol = kok / "takimlar" / "deneme" / "veri" / "gunluk.txt"
            self.assertTrue(yol.is_file(), "veri/gunluk.txt yazılmalıydı")
            metin = yol.read_text(encoding="utf-8")
            self.assertIn("merhaba-gun", metin)
            self.assertNotIn("gunluk =", metin.splitlines()[1],
                             "başlıktaki komut satırı ad önekinden arınmalı")

    def test_ayni_script_iki_farkli_dosyaya_yazar(self):
        """Asıl kusur buydu: iki kip aynı dosyayı eziyordu."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            kos.onhazirlik_kos("deneme", ["gun = echo gunluk-icerik",
                                          "hafta = echo haftalik-icerik"], kok=kok)
            veri = kok / "takimlar" / "deneme" / "veri"
            self.assertIn("gunluk-icerik", (veri / "gun.txt").read_text(encoding="utf-8"))
            self.assertIn("haftalik-icerik", (veri / "hafta.txt").read_text(encoding="utf-8"))


class OnHazirlikKosumuTesti(unittest.TestCase):
    """Komut sürücüde koşar, çıktı veri/ altına düşer, ajanın Bash'ine hiç gitmez."""

    def test_cikti_veri_klasorune_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, onhazirlik="echo merhaba-sahne")
            sonuc = kos.onhazirlik_kos("deneme", ["echo merhaba-sahne"], kok=kok)
            yol = kok / "takimlar" / "deneme" / "veri" / "onhazirlik-1.txt"
            self.assertTrue(yol.is_file(), "veri/ altına dosya yazılmadı")
            self.assertIn("merhaba-sahne", yol.read_text(encoding="utf-8"))
            self.assertEqual(len(sonuc), 1)
            self.assertTrue(sonuc[0]["tamam"])

    def test_bos_liste_hicbir_sey_yapmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            self.assertEqual(kos.onhazirlik_kos("deneme", [], kok=kok), [])
            self.assertFalse((kok / "takimlar" / "deneme" / "veri").exists())

    def test_hata_veren_komut_kosuyu_dusurmez_sebep_dosyaya_yazilir(self):
        """ANAYASA §2: sessiz düşme yok — sebep görünür olur, koşu devam eder."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            sonuc = kos.onhazirlik_kos("deneme", ["ls /yok-boyle-bir-klasor-9z8x"], kok=kok)
            self.assertFalse(sonuc[0]["tamam"])
            metin = (kok / "takimlar" / "deneme" / "veri" / "onhazirlik-1.txt").read_text(encoding="utf-8")
            self.assertIn("çıkış", metin)

    def test_takilan_komut_tavana_carpar_ve_isaretlenir(self):
        """120 sn'lik ajan sınırından bağımsız: sürücü kendi tavanını uygular."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            sonuc = kos.onhazirlik_kos(
                "deneme", ["sleep 30"], kok=kok, tavan_sn=1)
            self.assertFalse(sonuc[0]["tamam"])
            metin = (kok / "takimlar" / "deneme" / "veri" / "onhazirlik-1.txt").read_text(encoding="utf-8")
            self.assertIn("süre tavanı", metin)


class IstemTesti(unittest.TestCase):
    """Ajan komutu çağırmasın diye istem hazır dosyayı adıyla söylemeli."""

    def test_hazir_dosyalar_isteme_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp, onhazirlik="python3 bin/repo_ozet.py --gun 7")
            fm = {"name": "deneme", "onhazirlik": ["python3 bin/repo_ozet.py --gun 7"]}
            metin = kos.istem("deneme", fm, kok / "takimlar/deneme/kosu/x.md", "2026-09-16T09:00:00", kok=kok)
            self.assertIn("takimlar/deneme/veri/repo_ozet.txt", metin)
            self.assertIn("komutu tekrar çalıştırma", metin)


if __name__ == "__main__":
    unittest.main()
