"""Kitin kendi testleri — ağ yok, claude çağrısı yok, para harcamaz.

python3 -m unittest discover -s tests
"""
import collections
import io
import json
import plistlib
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[1]

# --- sızıntı taramasının kapsamı ---------------------------------------------
# Tarama İZLENEN dosyalarda sır arar. `.env` ve yerel kopyaları kapsam dışıdır:
# sırların durması gereken yer orasıdır ve `.gitignore` onları tutar
# (ayrıca `test_gitignore_env_i_kapsiyor` bunu doğrular). `.env.example` izlenen
# bir dosyadır ve taranmaya devam eder — değerleri boş olmalı.
SIZINTI_ATLA_DIZIN = {".git", "__pycache__", "kosu", "cikti", "gelen", "veri"}
SIZINTI_UZANTILARI = (".py", ".md", ".json", ".sh", ".example", ".gitignore", "")


def sizinti_taranir_mi(yol):
    """Sızıntı taraması bu yolu kapsar mı?"""
    if yol.name == "test_kit.py":
        return False
    if yol.name == ".env" or (yol.name.startswith(".env.") and yol.name != ".env.example"):
        return False
    if set(yol.parts) & SIZINTI_ATLA_DIZIN:
        return False
    return yol.suffix in SIZINTI_UZANTILARI

sys.path.insert(0, str(KOK / "bin"))
import ayar  # noqa: E402
import bekci  # noqa: E402
import dagitici  # noqa: E402
import gunluk  # noqa: E402
import kos  # noqa: E402
import sahne  # noqa: E402
import zamanla  # noqa: E402

TAKIM_MD = """---
name: {ad}
description: {ad} takımı — test.
model: sonnet
tools: [Read, Write]
gerekli_anahtarlar: []
butce_usd: 2
---

# {ad}
"""


def sahte_kok(tmp, takimlar=("kasa-bakimi", "karar-takibi")):
    """Geçici dizinde takimlar/<t>/{takim.md,durum.json,kosu/} olan minik bir repo."""
    kok = Path(tmp) / "kok"
    for ad in takimlar:
        dizin = kok / "takimlar" / ad
        (dizin / "kosu").mkdir(parents=True)
        (dizin / "takim.md").write_text(TAKIM_MD.format(ad=ad), encoding="utf-8")
        (dizin / "durum.json").write_text(json.dumps(
            {"takim": ad, "son_kosu": None, "son_sonuc": None, "kuyruk": [],
             "bekci": {"son_karar": None, "red_sayisi_7g": 0}, "defter_son_ders": None,
             "sayaclar": {}}, ensure_ascii=False), encoding="utf-8")
    return kok


# Kuru koşu ve istem testleri gerçek repoya değil, geçici kökteki örnek bir danışmana bakar:
# Nove'de danışmanlar formdan doldurulana kadar "kurulumda" (frontmatter'sız) duruyor.
DENEME_TAKIM_MD = """---
name: kalite
description: Kalite danışmanı — kurulun kalite sorularını yanıtlar.
model: sonnet
tools: [Read, Write]
gerekli_anahtarlar: []
butce_usd: 2
skills: [kalite-raporu]
---

# Kalite
"""


class deneme_repo:
    """`with deneme_repo() as kok:` — geçici kökte kurulu `kalite` danışmanı; ayar/kos/dagitici KOK'u oraya bakar."""
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        kok = sahte_kok(self._tmp.name, takimlar=("kalite",))
        (kok / "takimlar/kalite/takim.md").write_text(DENEME_TAKIM_MD, encoding="utf-8")
        (kok / "takimlar/kalite/kurallar.md").write_text("# Kalite — kurallar\n", encoding="utf-8")
        self._yamalar = [mock.patch.object(m, "KOK", kok) for m in (ayar, kos, dagitici)]
        for y in self._yamalar:
            y.start()
        return kok

    def __exit__(self, *hata):
        for y in reversed(self._yamalar):
            y.stop()
        self._tmp.cleanup()
        return False


# Zincir mekanizmasının testleri — gerçek ZINCIR tablosundan bağımsız (Nove'de s-/r- kuralları Faz 3'te gelir).
TEST_ZINCIRI = [
    {"ad": "kasa-celiski", "desen": re.compile(r"^kasa-(.+)$"), "takim": "karar-takibi",
     "id": "cel-{0}", "not": "kasa-bakimi çözülmemiş çelişki buldu; sahibini ve yaşını çıkar"},
    {"ad": "qa-haftalik", "desen": re.compile(r"^qa-(.+)$"), "takim": "haftalik-rapor",
     "id": "qa-{0}", "not": "kalite bölümü ekle"},
]
TEST_ZAMANLI = [{"takim": "haftalik-rapor", "gun": 0, "id": "rapor-{hafta}", "not": "haftalık ilerleme raporu"}]


class AyarTesti(unittest.TestCase):
    def test_env_yukle_export_ve_tirnak_tolere_eder(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / ".env"
            yol.write_text("export A=1\nB=\"iki\"\n# yorum\nC='üç'\nBOS=\n", encoding="utf-8")
            self.assertEqual(ayar.env_yukle(yol), {"A": "1", "B": "iki", "C": "üç", "BOS": ""})

    def test_eksik_anahtarlar(self):
        self.assertEqual(ayar.eksik_anahtarlar(["A", "B"], {"A": "1"}), ["B"])
        self.assertEqual(ayar.eksik_anahtarlar([], {}), [])

    def test_mesai_penceresi(self):
        gunduz = datetime(2026, 9, 11, 12, 0)
        gece = datetime(2026, 9, 11, 3, 0)
        self.assertTrue(ayar.mesaide_mi(gunduz))
        self.assertFalse(ayar.mesaide_mi(gece))
        self.assertEqual(ayar.sonraki_mesai(gece).hour, ayar.MESAI_BASLANGIC)

    def test_frontmatter_liste_ayristirir(self):
        fm, govde = ayar.frontmatter(TAKIM_MD.format(ad="kasa-bakimi"))
        self.assertEqual(fm["name"], "kasa-bakimi")
        self.assertEqual(fm["tools"], ["Read", "Write"])
        self.assertEqual(fm["butce_usd"], "2")
        self.assertTrue(govde.startswith("# kasa-bakimi"))

    def test_gercek_takimlarin_frontmatteri_okunur(self):
        for ad in ayar.kurulu_takimlar():
            fm = ayar.takim_bilgisi(ad)
            self.assertIsNotNone(fm, ad)
            self.assertEqual(fm["name"], ad)
            self.assertIsInstance(fm["tools"], list)


class KuruKosuTesti(unittest.TestCase):
    def test_kos_kuru_calisir_ve_hicbir_dosyaya_yazmaz(self):
        with deneme_repo() as kok:
            self._kuru_kos_yazmaz(kok)

    def _kuru_kos_yazmaz(self, KOK):
        for ad in ("kalite",):
            oncesi = json.loads((KOK / "takimlar" / ad / "durum.json").read_text(encoding="utf-8"))
            # Dizinin BOŞ olması değil, DEĞİŞMEMESİ aranır: gerçek koşular buraya kayıt bırakır
            # ve şirket çalışmaya başladıktan sonra "boş" varsayımı kalıcı olarak yanlış olur.
            kosu_oncesi = sorted(p.name for p in (KOK / "takimlar" / ad / "kosu").glob("*.md"))
            yakala = io.StringIO()
            with redirect_stdout(yakala):
                kod = kos.main([ad, "--kuru"])
            self.assertEqual(kod, 0, ad)
            self.assertIn("kuru koşu", yakala.getvalue())
            self.assertIn("claude çağrılmadı", yakala.getvalue())
            sonrasi = json.loads((KOK / "takimlar" / ad / "durum.json").read_text(encoding="utf-8"))
            self.assertEqual(oncesi, sonrasi, f"{ad}: kuru koşu durum.json'u değiştirdi")
            kosu_sonrasi = sorted(p.name for p in (KOK / "takimlar" / ad / "kosu").glob("*.md"))
            self.assertEqual(kosu_oncesi, kosu_sonrasi, f"{ad}: kuru koşu kosu/ altına dosya yazdı")

    def test_istem_anayasayi_ve_kosu_kaydini_soyler(self):
        with deneme_repo() as kok:
            fm = ayar.takim_bilgisi("kalite")
            metin = kos.istem("kalite", fm, kok / "takimlar/kalite/kosu/x.md", "2026-09-11T12:00:00+02:00")
        self.assertIn("ANAYASA.md", metin)
        self.assertIn("kurallar.md", metin)
        self.assertIn("SIRKET_KOSU", metin)
        self.assertIn("<kaynak>", metin)


class KimlikIstemiTesti(unittest.TestCase):
    """Koşu istemi: kimlik → ANAYASA → AJAN-KIMLIGI → kurallar → takim.md sırası."""

    def _istem(self, takim="kalite", fm=None):
        with deneme_repo() as kok:
            return kos.istem(takim, fm if fm is not None else {},
                             kok / f"takimlar/{takim}/kosu/2026-09-11-1200.md", "2026-09-11 12:00")

    def test_istemin_ilk_satiri_kimlik(self):
        metin = self._istem()
        self.assertTrue(metin.startswith("Sen `kalite` ajanısın."), metin[:80])
        self.assertIn("Nove Kurul Ofisi'nde bir çalışansın", metin.splitlines()[0])
        self.assertIn("bir yapay zekâ ajanısın", metin.splitlines()[0])
        self.assertIn("Mesleğin:", metin.splitlines()[0])

    def test_istem_kimlik_dosyasini_okuma_sirasina_koyar(self):
        metin = self._istem()
        self.assertIn("sirket/AJAN-KIMLIGI.md", metin)
        self.assertLess(metin.index("ANAYASA.md"), metin.index("sirket/AJAN-KIMLIGI.md"))
        self.assertLess(metin.index("sirket/AJAN-KIMLIGI.md"), metin.index("takimlar/kalite/kurallar.md"))

    def test_istem_meslegi_takim_md_den_okur(self):
        """fm boş gelse bile description takim.md'den tamamlanır."""
        self.assertIn("Kalite danışmanı", self._istem())

    def test_istem_yetenek_satiri_ekler(self):
        metin = self._istem("deney", {"description": "deneme takımı — test.",
                                      "skills": ["birinci-yetenek", "ikinci-yetenek"]})
        self.assertIn("Yeteneklerin: `skills/birinci-yetenek/SKILL.md`, `skills/ikinci-yetenek/SKILL.md`", metin)
        self.assertIn("ilgili adımda oku ve uygula", metin)

    def test_istem_skillleri_takim_md_den_tamamlar(self):
        self.assertIn("`skills/kalite-raporu/SKILL.md`", self._istem())

    def test_istem_skills_yoksa_yetenek_satiri_yok(self):
        metin = self._istem("yok-boyle-takim", {"description": "x", "skills": []})
        self.assertNotIn("Yeteneklerin:", metin)

    def test_istem_kendini_gelistirme_cumlesi(self):
        metin = self._istem()
        self.assertIn("kendini geliştir", metin)
        self.assertIn("defter.md", metin)

    def test_kuru_kosu_kimlik_satirini_basar(self):
        yakala = io.StringIO()
        with deneme_repo(), redirect_stdout(yakala):
            kos.main(["kalite", "--kuru"])
        cikti = yakala.getvalue()
        self.assertIn("kimlik (istemin ilk satırı): Sen `kalite` ajanısın.", cikti)
        self.assertIn("yetenekler: kalite-raporu", cikti)

    def test_dagitici_kuru_calisir_ve_kuyruga_yazmaz(self):
        with deneme_repo() as kok:
            oncesi = (kok / "takimlar/kalite/durum.json").read_text(encoding="utf-8")
            yakala = io.StringIO()
            with redirect_stdout(yakala):
                kod = dagitici.main(["--kuru"])
            sonrasi = (kok / "takimlar/kalite/durum.json").read_text(encoding="utf-8")
        self.assertEqual(kod, 0)
        self.assertIn("dağıtıcı", yakala.getvalue())
        self.assertIn("kuru koşu", yakala.getvalue())
        self.assertEqual(oncesi, sonrasi)

    def test_kosu_yolu_tarihli(self):
        yol = kos.kosu_yolu("kasa-bakimi", "2026-09-11T12:05:00+02:00", kok="/x")
        self.assertEqual(str(yol), "/x/takimlar/kasa-bakimi/kosu/2026-09-11-1205.md")

    def test_sonucu_cozumle(self):
        iyi = kos.sonucu_cozumle(json.dumps({"result": "bitti", "total_cost_usd": 0.12,
                                             "num_turns": 3, "is_error": False}))
        self.assertEqual(iyi["maliyet"], 0.12)
        self.assertFalse(iyi["hata"])
        self.assertTrue(kos.sonucu_cozumle("json değil")["hata"])


class ZincirTesti(unittest.TestCase):
    def setUp(self):
        yama = mock.patch.object(dagitici, "ZINCIR", TEST_ZINCIRI)
        yama.start()
        self.addCleanup(yama.stop)

    def test_kasa_tamam_olunca_karar_kuyruguna_cel_duser(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-1234", "durum": "tamam", "not": "çözülmemiş çelişki"}]}, kok)
            yazilan = dagitici.zinciri_isle(kok, "kasa-bakimi")
            self.assertEqual([z["id"] for z in yazilan], ["cel-1234"])
            kuyruk = ayar.durum_oku("karar-takibi", kok)["kuyruk"]
            self.assertEqual(kuyruk[0]["id"], "cel-1234")
            self.assertEqual(kuyruk[0]["durum"], "bekliyor")

    def test_zincir_iki_kez_calisinca_tekrar_yazmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [{"id": "kasa-7", "durum": "tamam"}]}, kok)
            dagitici.zinciri_isle(kok, "kasa-bakimi")
            self.assertEqual(dagitici.zinciri_isle(kok, "kasa-bakimi"), [])
            self.assertEqual(len(ayar.durum_oku("karar-takibi", kok)["kuyruk"]), 1)

    def test_bekleyen_madde_zincire_girmez(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [{"id": "kasa-9", "durum": "bekliyor"}]}, kok)
            self.assertEqual(dagitici.zinciri_isle(kok, "kasa-bakimi"), [])

    # --- A: içerik zincirden geçer ------------------------------------------
    def test_kaynak_zincir_notu_yeni_maddeye_gecer(self):
        """Kaynak takım `zincir_not` eklerse alıcı onu görür.

        Eskiden ZINCIR tablosundaki sabit metin yazılıyordu ("çözülmemiş çelişki buldu;
        sahibini ve yaşını çıkar") — alıcı DÖRT çelişkiden hangisi olduğunu bilemiyordu.
        """
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-1234", "durum": "tamam", "not": "günlük denetim",
                 "zincir_not": "4 çelişki, en eskisi 12 gün: koray-brief oranı 15/15 vs 7/16"}]}, kok)
            dagitici.zinciri_isle(kok, "kasa-bakimi")
            madde = ayar.durum_oku("karar-takibi", kok)["kuyruk"][0]
            self.assertIn("koray-brief", madde["not"])
            self.assertNotIn("sahibini ve yaşını", madde["not"])

    def test_zincir_notu_yoksa_tablodaki_varsayilan_kullanilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-1234", "durum": "tamam"}]}, kok)
            dagitici.zinciri_isle(kok, "kasa-bakimi")
            madde = ayar.durum_oku("karar-takibi", kok)["kuyruk"][0]
            self.assertIn("çelişki", madde["not"])

    # --- B: değişmeyen iş her gün yeniden açılmaz ----------------------------
    def test_ayni_zincirden_bekleyen_madde_varken_yenisi_yazilmaz(self):
        """Dört çelişki 12 gündür açık; kasa her sabah koşuyor. Eskiden her sabah yeni bir
        `cel-<tarih>` düşüyordu — değişmeyen iş için günde ~0.28 USD."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("karar-takibi", {"kuyruk": [
                {"id": "cel-eski", "durum": "bekliyor", "not": "önceki çelişki"}]}, kok)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-yeni", "durum": "tamam"}]}, kok)
            self.assertEqual(dagitici.zinciri_isle(kok, "kasa-bakimi"), [])
            self.assertEqual([m["id"] for m in ayar.durum_oku("karar-takibi", kok)["kuyruk"]],
                             ["cel-eski"])

    def test_onceki_zincir_maddesi_kapandiysa_yenisi_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("karar-takibi", {"kuyruk": [
                {"id": "cel-eski", "durum": "tamam", "not": "işlendi"}]}, kok)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-yeni", "durum": "tamam", "zincir_not": "güncel çelişki listesi"}]}, kok)
            yazilan = dagitici.zinciri_isle(kok, "kasa-bakimi")
            self.assertEqual([z["id"] for z in yazilan], ["cel-yeni"])
            madde = ayar.durum_oku("karar-takibi", kok)["kuyruk"][-1]
            self.assertIn("güncel çelişki listesi", madde["not"])

    def test_baska_zincirin_bekleyen_maddesi_engellemez(self):
        """Engelleme zincire özgü: karar-takibi'nde bekleyen bir `not-` maddesi
        kasa zincirini durdurmamalı."""
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            ayar.durum_guncelle("karar-takibi", {"kuyruk": [
                {"id": "not-42", "durum": "bekliyor", "not": "patronun notu"}]}, kok)
            ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [
                {"id": "kasa-7", "durum": "tamam"}]}, kok)
            self.assertEqual([z["id"] for z in dagitici.zinciri_isle(kok, "kasa-bakimi")], ["cel-7"])

    def test_qa_haftalik_zinciri_haftalik_rapora_gider(self):
        istek = dagitici.zincir_esle("qa-2026-W38")
        self.assertIsNotNone(istek, "qa-<hafta> deseni ZINCIR'de tanımlı değil")
        self.assertEqual(istek["takim"], "haftalik-rapor")
        self.assertEqual(istek["id"], "qa-2026-w38")

    def test_kasa_zinciri_bozulmadi(self):
        istek = dagitici.zincir_esle("kasa-2026-09-16")
        self.assertEqual(istek["takim"], "karar-takibi")
        self.assertEqual(istek["id"], "cel-2026-09-16")


class TavanTesti(unittest.TestCase):
    SIMDI = datetime.fromisoformat("2026-09-11T15:00:00+02:00")

    def _bekleyen_kok(self, tmp):
        kok = sahte_kok(tmp)
        ayar.durum_guncelle("kasa-bakimi", {"kuyruk": [{"id": "kasa-1", "durum": "bekliyor"}]}, kok)
        return kok

    def test_bos_kuyruk_kosmaz(self):
        with tempfile.TemporaryDirectory() as tmp:
            kossun, sebep = dagitici.tetik_karari(sahte_kok(tmp), "kasa-bakimi", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("bekleyen madde yok", sebep)

    def test_bekleyen_madde_kosturur(self):
        with tempfile.TemporaryDirectory() as tmp:
            kossun, _ = dagitici.tetik_karari(self._bekleyen_kok(tmp), "kasa-bakimi", self.SIMDI)
            self.assertTrue(kossun)

    def test_mesai_disi_bekletir(self):
        with tempfile.TemporaryDirectory() as tmp:
            gece = self.SIMDI.replace(hour=3)
            kossun, sebep = dagitici.tetik_karari(self._bekleyen_kok(tmp), "kasa-bakimi", gece)
            self.assertFalse(kossun)
            self.assertIn("mesai dışı", sebep)

    def test_kosular_arasi_bekleme_kurali(self):
        # Varsayılan ayar 0 (bekleme yok); kural mantığı ayar 30'a çekilerek sınanır.
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ayar, "KOSULAR_ARASI_DK", 30):
            kok = self._bekleyen_kok(tmp)
            yeni = self.SIMDI - timedelta(minutes=10)
            ayar.durum_guncelle("kasa-bakimi", {"son_kosu": yeni.isoformat()}, kok)
            kossun, sebep = dagitici.tetik_karari(kok, "kasa-bakimi", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("30 dk", sebep)

    def test_bekleme_sifirsa_hemen_kosar(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ayar, "KOSULAR_ARASI_DK", 0):
            kok = self._bekleyen_kok(tmp)
            yeni = self.SIMDI - timedelta(minutes=1)
            ayar.durum_guncelle("kasa-bakimi", {"son_kosu": yeni.isoformat()}, kok)
            kossun, _ = dagitici.tetik_karari(kok, "kasa-bakimi", self.SIMDI)
            self.assertTrue(kossun)

    def test_gunluk_kosu_tavani(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._bekleyen_kok(tmp)
            for saat in range(ayar.GUNLUK_KOSU_TAVANI):
                (kok / "takimlar/kasa-bakimi/kosu" / f"2026-09-11-{saat:02d}00.md").write_text("x")
            kossun, sebep = dagitici.tetik_karari(kok, "kasa-bakimi", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("günlük koşu tavanı", sebep)

    def test_gunluk_maliyet_tavani(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._bekleyen_kok(tmp)
            (kok / "takimlar/karar-takibi/kosu/2026-09-11-0900.md").write_text(
                "- maliyet: %.2f USD · tur: 3\n" % (ayar.GUNLUK_MALIYET_TAVANI_USD + 0.5), encoding="utf-8")
            kossun, sebep = dagitici.tetik_karari(kok, "kasa-bakimi", self.SIMDI)
            self.assertFalse(kossun)
            self.assertIn("günlük bütçe", sebep)


class KosTavanTesti(unittest.TestCase):
    """ANAYASA §4'ün günlük tavanları kos.py'de uygulanır.

    Eskiden yalnız dagitici.tetik_karari'ndaydı, yani panelin "koş" düğmesi ve elle
    çağrı tavanları atlıyordu — kosu_baslat'ın belgesi "tavanları kos.py uygular"
    diyordu ama kos.py saymıyordu.
    """

    def _kok_kosu_ile(self, tmp, adet, maliyet):
        kok = sahte_kok(tmp)
        dizin = kok / "takimlar" / "kasa-bakimi" / "kosu"
        bugun = datetime.now().astimezone().strftime("%Y-%m-%d")
        for i in range(adet):
            (dizin / ("%s-09%02d.md" % (bugun, i))).write_text(
                "- maliyet: %.3f USD\n" % maliyet, encoding="utf-8")
        return kok

    def test_gunluk_kosu_tavani_dolunca_atlanir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._kok_kosu_ile(tmp, ayar.GUNLUK_KOSU_TAVANI, 0.1)
            kossun, sebep = kos.tavan_karari(kok, "kasa-bakimi",
                                             datetime.now().astimezone())
            self.assertFalse(kossun)
            self.assertIn("günlük koşu tavanı", sebep)

    def test_sirket_butcesi_dolunca_atlanir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._kok_kosu_ile(tmp, 1, ayar.GUNLUK_MALIYET_TAVANI_USD)
            kossun, sebep = kos.tavan_karari(kok, "haftalik-rapor",
                                             datetime.now().astimezone())
            self.assertFalse(kossun)
            self.assertIn("bütçe", sebep)

    def test_tavan_altinda_izin_verir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = self._kok_kosu_ile(tmp, 0, 0)
            kossun, sebep = kos.tavan_karari(kok, "kasa-bakimi",
                                             datetime.now().astimezone())
            self.assertTrue(kossun, sebep)


class BekciTesti(unittest.TestCase):
    def test_on_kontrol_anahtar_desenlerini_yakalar(self):
        self.assertEqual(bekci.on_kontrol("anahtar sk-abc123def burada"), ["OpenAI anahtarı"])
        self.assertEqual(bekci.on_kontrol("AIzaSyD-abcdefghij"), ["Google anahtarı"])
        self.assertEqual(bekci.on_kontrol("ghp_abcdef123456"), ["GitHub token"])
        self.assertEqual(bekci.on_kontrol("12345678:AAEabcdefghijklmnopqrstuvwx-yz"),
                         ["Telegram bot token"])
        self.assertIn("e-posta adresi", bekci.on_kontrol("gönderen: biri@marka.com"))

    def test_on_kontrol_temiz_metni_gecirir(self):
        self.assertEqual(bekci.on_kontrol("3 link okundu, 2 tablo yazıldı, 1 ⛔ çıktı"), [])

    def test_bos_kosu_kaydi_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            (kok / "ANAYASA.md").write_text("1. Yayın düğmesi insanın.", encoding="utf-8")
            kosu = kok / "takimlar/kasa-bakimi/kosu/2026-09-11-1200.md"
            kosu.write_text("   \n", encoding="utf-8")
            karar = bekci.denetle(kok, "kasa-bakimi", kosu)
            self.assertEqual(karar["karar"], "red")
            self.assertIn("boş", karar["gerekce"])
            self.assertEqual(ayar.durum_oku("kasa-bakimi", kok)["bekci"]["son_karar"], "red")

    def test_anahtar_sizan_kosu_llm_cagirmadan_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            kosu = kok / "takimlar/kasa-bakimi/kosu/2026-09-11-1200.md"
            kosu.write_text("# Koşu\nAPIFY_TOKEN=sk-gizli123456 ile çektim\n", encoding="utf-8")
            with mock.patch.object(bekci, "openai_sor") as sahte_openai, \
                 mock.patch.object(bekci, "haiku_sor") as sahte_haiku:
                karar = bekci.denetle(kok, "kasa-bakimi", kosu)
            sahte_openai.assert_not_called()
            sahte_haiku.assert_not_called()
            self.assertEqual(karar["karar"], "red")
            self.assertIn("## Bekçi", kosu.read_text(encoding="utf-8"))

    def test_haiku_yedegi_ayni_aile_uyarisi_yazar(self):
        yanit = json.dumps({"result": '{"karar":"kabul","gerekce":"temiz","ihlal_edilen_kural":null}'})
        with mock.patch.object(bekci.subprocess, "run",
                               return_value=mock.Mock(stdout=yanit, returncode=0)):
            karar = bekci.haiku_sor("istem")
        self.assertEqual(karar["karar"], "kabul")
        self.assertIn(bekci.AYNI_AILE_UYARISI, karar["gerekce"])

    def test_madde_3_gerekceli_red_gecersiz(self):
        red = {"karar": "red", "gerekce": "ANAYASA madde 3: denetleyen aynı aileden",
               "ihlal_edilen_kural": "3"}
        self.assertEqual(bekci.gecersiz_gerekceyi_ayikla(red)["karar"], "kabul")

    def test_icerik_gerekceli_red_korunur(self):
        red = {"karar": "red", "gerekce": "kaynaksız sayı: '8 bin abone'", "ihlal_edilen_kural": "2"}
        self.assertEqual(bekci.gecersiz_gerekceyi_ayikla(red)["karar"], "red")


class BelgeTutarliligiTesti(unittest.TestCase):
    def test_env_ornegi_ile_readme_ayni_anahtarlari_sayiyor(self):
        ornek = ayar.env_yukle(KOK / ".env.example")
        self.assertTrue(ornek, ".env.example okunamadı")
        readme = (KOK / "README.md").read_text(encoding="utf-8")
        for anahtar in ornek:
            self.assertIn(anahtar, readme, f"{anahtar} .env.example'da var ama README'de yok")

    def test_env_orneginde_gercek_deger_yok(self):
        for anahtar, deger in ayar.env_yukle(KOK / ".env.example").items():
            if anahtar == "KANAL":
                self.assertEqual(deger, "@ornek-kanal")
            else:
                self.assertEqual(deger, "", f"{anahtar} .env.example'da dolu!")

    def test_sizinti_taramasi_env_i_atlar(self):
        """`.env` sırların DURMASI GEREKEN yer — tarama onu kapsamaz, `.gitignore` tutar."""
        self.assertFalse(sizinti_taranir_mi(KOK / ".env"))
        self.assertFalse(sizinti_taranir_mi(KOK / ".env.local"))

    def test_sizinti_taramasi_env_example_i_kapsar(self):
        """`.env.example` izlenen dosya — içinde gerçek anahtar olmamalı, taranmaya devam eder."""
        self.assertTrue(sizinti_taranir_mi(KOK / ".env.example"))

    def test_sizinti_taramasi_kaynak_dosyalari_kapsar(self):
        self.assertTrue(sizinti_taranir_mi(KOK / "bin" / "kos.py"))
        self.assertTrue(sizinti_taranir_mi(KOK / "ANAYASA.md"))

    def test_sizinti_taramasi_kosu_ciktilarini_atlar(self):
        self.assertFalse(sizinti_taranir_mi(KOK / "takimlar" / "qa-hatti" / "kosu" / "x.md"))

    def test_repoda_sizmis_anahtar_yok(self):
        desenler = [re.compile(p) for p in
                    (r"\bsk-[A-Za-z0-9]{20,}", r"\bAIza[0-9A-Za-z_-]{30,}",
                     r"\bgh[pousr]_[A-Za-z0-9]{30,}", r"\b\d{9,}:[A-Za-z0-9_-]{30,}")]
        for yol in KOK.rglob("*"):
            if not yol.is_file() or not sizinti_taranir_mi(yol):
                continue
            metin = yol.read_text(encoding="utf-8", errors="ignore")
            for desen in desenler:
                self.assertIsNone(desen.search(metin), f"{yol.name}: anahtara benzeyen metin")

    def test_gitignore_env_i_kapsiyor(self):
        satirlar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
        for beklenen in (".env", "takimlar/*/kosu/", "takimlar/*/cikti/", "takimlar/*/gelen/",
                         "takimlar/*/veri/", "__pycache__/", "*.jsonl"):
            self.assertIn(beklenen, satirlar)

    def test_gitignore_nove_gizli_klasorlerini_kapsiyor(self):
        """NOVE-KURULUM.md §3: doldurulmuş formlar ve soru kayıtları git'e girmez."""
        satirlar = (KOK / ".gitignore").read_text(encoding="utf-8").splitlines()
        for beklenen in ("formlar/gelen/", "sirket-log/", "kasa/"):
            self.assertIn(beklenen, satirlar)

    def test_stop_hook_bekciyi_cagiriyor(self):
        ayarlar = json.loads((KOK / ".claude/settings.json").read_text(encoding="utf-8"))
        komutlar = [h["command"] for madde in ayarlar["hooks"]["Stop"] for h in madde["hooks"]]
        self.assertTrue(any("bekci.py" in k for k in komutlar))
        self.assertEqual(list(ayarlar["hooks"]), ["Stop"])


MESAI_ICI = datetime(2026, 9, 11, 10, 0).astimezone()
MESAI_DISI = datetime(2026, 9, 11, 3, 0).astimezone()


GUN = "2026-09-11"
KOSU_METNI = """# Koşu — {takim} — {gun}

- model: sonnet · bütçe: 2 USD

iş yapıldı.

---
- maliyet: {maliyet} USD · tur: 7 · hata: {hata}


## Bekçi
- karar: **{karar}**
- gerekçe: {gerekce}
- ihlal edilen kural: -
"""


def _kosu_yaz(kok, takim, saat, maliyet="0.500", hata="False", karar="kabul", gerekce="temiz"):
    yol = Path(kok) / "takimlar" / takim / "kosu" / f"{GUN}-{saat}.md"
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(KOSU_METNI.format(takim=takim, gun=GUN, maliyet=maliyet, hata=hata,
                                     karar=karar, gerekce=gerekce), encoding="utf-8")
    return yol


class GunlukRaporTesti(unittest.TestCase):
    def test_kosu_oku_ozet_ve_bekci_kararini_ayiklar(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            kosu = gunluk.kosu_oku(_kosu_yaz(kok, "kasa-bakimi", "0930", maliyet="1.250", karar="red"))
        self.assertEqual((kosu["gun"], kosu["saat"]), (GUN, "09:30"))
        self.assertEqual((kosu["maliyet"], kosu["tur"], kosu["hata"]), (1.25, 7, False))
        self.assertEqual((kosu["bekci"], kosu["atlandi"]), ("red", None))

    def test_kosu_oku_atlanan_kosuyu_tanir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            yol = Path(kok) / "takimlar/kasa-bakimi/kosu" / f"{GUN}-0300.md"
            yol.write_text("# Koşu\n\n**Atlandı:** mesai dışı (09:00-23:00); kuyrukta bekler\n",
                           encoding="utf-8")
            kosu = gunluk.kosu_oku(yol)
        self.assertIn("mesai dışı", kosu["atlandi"])
        self.assertEqual((kosu["maliyet"], kosu["bekci"]), (0.0, "-"))

    def test_gunun_kosulari_gune_gore_suzup_saate_gore_sirali_doner(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "kasa-bakimi", "1400")
            _kosu_yaz(kok, "karar-takibi", "0930")
            (Path(kok) / "takimlar/kasa-bakimi/kosu/2026-09-10-1000.md").write_text("dün", encoding="utf-8")
            kosular = gunluk.gunun_kosulari(kok, GUN)
        self.assertEqual([(k["saat"], k["takim"]) for k in kosular],
                         [("09:30", "karar-takibi"), ("14:00", "kasa-bakimi")])

    def test_bekci_telemetrisi_gune_gore_suzulur_bozuk_satir_atlanir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            (Path(kok) / gunluk.TELEMETRI).write_text(
                json.dumps({"zaman": f"{GUN}T09:30:00+03:00", "takim": "kasa-bakimi", "karar": "red"}) + "\n"
                + "{bozuk json\n"
                + json.dumps({"zaman": "2026-09-10T09:30:00+03:00", "takim": "kasa-bakimi", "karar": "kabul"}) + "\n",
                encoding="utf-8")
            kararlar = gunluk.gunun_bekci_kararlari(kok, GUN)
        self.assertEqual([k["karar"] for k in kararlar], ["red"])

    def test_aksam_raporu_kosulari_kararlari_ve_dikkati_yazar(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "kasa-bakimi", "0930", maliyet="1.250", karar="red", gerekce="kaynak yok")
            (Path(kok) / gunluk.TELEMETRI).write_text(
                json.dumps({"zaman": f"{GUN}T09:45:00+03:00", "takim": "kasa-bakimi", "karar": "red",
                            "gerekce": "kaynak yok", "ihlal_edilen_kural": "kaynak"},
                           ensure_ascii=False) + "\n", encoding="utf-8")
            metin = gunluk.aksam_raporu(kok, MESAI_ICI)
        self.assertIn("Akşam denetimi", metin)
        self.assertIn("Bugünün koşuları (1)", metin)
        self.assertIn("**red 1**", metin)
        self.assertIn("⛔ `kasa-bakimi` 09:30 — bekçi **red**", metin)
        self.assertIn(f"/ {ayar.GUNLUK_MALIYET_TAVANI_USD:.0f} USD", metin)

    def test_temiz_gunde_uydurma_uyari_yok(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            _kosu_yaz(kok, "kasa-bakimi", "0930")
            metin = gunluk.aksam_raporu(kok, MESAI_ICI)
        self.assertIn("temiz gün, işaretlenecek bir şey yok", metin)
        self.assertNotIn("⛔", metin)

    def test_sabah_raporu_dagitici_kararlarini_tasir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            dagitici.kuyruga_yaz(kok, "kasa-bakimi", "x-1", "telegram linki")
            dagitim = dagitici.dagit(kok, MESAI_ICI, kuru=True)
            metin = gunluk.sabah_raporu(kok, MESAI_ICI, dagitim)
        self.assertIn("Sabah raporu", metin)
        self.assertIn("| kasa-bakimi | KOŞ |", metin)
        self.assertIn("| karar-takibi | BEKLE |", metin)
        self.assertIn("Dün (2026-09-10)", metin)

    def test_sabah_kuru_kosu_hicbir_takimi_baslatmaz(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            dagitici.kuyruga_yaz(kok, "kasa-bakimi", "x-1", "telegram linki")
            with mock.patch.object(dagitici, "_kostur") as sahte:
                gunluk.sabah(kok, MESAI_ICI, kuru=True)
            sahte.assert_not_called()
            self.assertFalse((Path(kok) / gunluk.RAPOR_DIZINI).exists())

    @mock.patch.object(gunluk, "ZAMANLI", TEST_ZAMANLI)
    def test_haftalik_is_yalniz_pazartesi_kuyruga_duser(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, takimlar=("haftalik-rapor",))
            sali = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 15, 9, 0).astimezone())
            pazartesi = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 14, 9, 0).astimezone())
            tekrar = gunluk.haftalik_kuyruk(kok, datetime(2026, 9, 14, 9, 30).astimezone())
            kuyruk = ayar.durum_oku("haftalik-rapor", kok)["kuyruk"]
        self.assertEqual(sali, [])
        self.assertEqual([h["id"] for h in pazartesi], ["rapor-2026-W38"])
        self.assertEqual(tekrar, [], "aynı haftanın maddesi ikinci kez yazılmamalı")
        self.assertEqual([(o["id"], o["durum"]) for o in kuyruk], [("rapor-2026-W38", "bekliyor")])

    def test_hafta_kimligi_iso_bicimi(self):
        """`rapor-{hafta}` id'si ISO hafta kimliğinden kurulur: YYYY-Www."""
        self.assertEqual(gunluk.hafta_kimligi(datetime(2026, 9, 14, 9, 0)), "2026-W38")
        self.assertRegex(gunluk.hafta_kimligi(datetime(2026, 1, 5, 9, 0)), r"^\d{4}-W\d{2}$")

    @mock.patch.object(gunluk, "ZAMANLI", TEST_ZAMANLI)
    def test_pazartesi_sabahi_haftalik_rapor_gercekten_kosar(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d, takimlar=("haftalik-rapor",))
            with mock.patch.object(dagitici, "_kostur") as sahte:
                metin, _ = gunluk.sabah(kok, datetime(2026, 9, 14, 9, 0).astimezone())
            sahte.assert_called_once_with(kok, "haftalik-rapor")
        self.assertIn("`rapor-2026-W38` düştü", metin)
        self.assertIn("| haftalik-rapor | KOŞ |", metin)

    def test_zamanlanmis_is_olmayan_gunde_rapor_bunu_soyler(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            metin = gunluk.sabah_raporu(kok, MESAI_ICI, {"zincir": [], "kararlar": []})
        self.assertIn("bugün (Cuma) zamanlanmış iş yok", metin)

    def test_rapor_dosyaya_yazilir(self):
        with tempfile.TemporaryDirectory() as d:
            kok = sahte_kok(d)
            yol = gunluk.yaz(kok, "aksam", gunluk.aksam_raporu(kok, MESAI_ICI), MESAI_ICI)
        self.assertEqual(yol.name, f"{GUN}-aksam.md")
        self.assertIn(gunluk.RAPOR_DIZINI, str(yol))


class ZamanlayiciTesti(unittest.TestCase):
    def test_saatler_ayardan_turer(self):
        saatler = {t["ad"]: t["saat"] for t in zamanla.TETIKLER}
        self.assertEqual(saatler["sabah"], ayar.MESAI_BASLANGIC)
        self.assertEqual(saatler["aksam"], ayar.MESAI_BITIS - 1)
        self.assertTrue(ayar.mesaide_mi(datetime(2026, 9, 11, saatler["aksam"], 0)))

    def test_plist_gunluk_py_yi_dogru_bayrakla_cagirir(self):
        for tetik in zamanla.TETIKLER:
            icerik = zamanla.plist_icerigi(tetik, kok="/tmp/kok", python="/usr/bin/python3")
            self.assertEqual(icerik["ProgramArguments"],
                             ["/usr/bin/python3", "/tmp/kok/bin/gunluk.py", tetik["bayrak"]])
            self.assertEqual(icerik["StartCalendarInterval"], {"Hour": tetik["saat"], "Minute": 0})
            self.assertEqual(icerik["WorkingDirectory"], "/tmp/kok")
            self.assertFalse(icerik["RunAtLoad"], "kurulum anında koşu başlatmamalı")
            self.assertIn("/usr/bin", icerik["EnvironmentVariables"]["PATH"])

    def test_plist_yazilabilir_bicimde(self):
        for tetik in zamanla.TETIKLER:
            ham = plistlib.dumps(zamanla.plist_icerigi(tetik))
            self.assertEqual(plistlib.loads(ham)["Label"], zamanla.etiket(tetik["ad"]))


class TasinmaTesti(unittest.TestCase):
    """§4 sayımı ayar.py'ye taşındı; dagitici aynı sonucu vermeye devam eder."""

    def test_ayar_sayim_fonksiyonlarini_tasiyor(self):
        self.assertTrue(hasattr(ayar, "bugunku_kosu_sayisi"))
        self.assertTrue(hasattr(ayar, "gunluk_maliyet"))

    def test_dagitici_ayni_sonucu_verir(self):
        with tempfile.TemporaryDirectory() as tmp:
            kok = sahte_kok(tmp)
            kosu = kok / "takimlar" / "kasa-bakimi" / "kosu"
            (kosu / "2026-09-16-0900.md").write_text("- maliyet: 0.250 USD\n", encoding="utf-8")
            (kosu / "2026-09-16-1000.md").write_text("- maliyet: 1.750 USD\n", encoding="utf-8")
            self.assertEqual(ayar.bugunku_kosu_sayisi(kok, "kasa-bakimi", "2026-09-16"), 2)
            self.assertAlmostEqual(ayar.gunluk_maliyet(kok, "2026-09-16"), 2.0)
            self.assertEqual(dagitici.bugunku_kosu_sayisi(kok, "kasa-bakimi", "2026-09-16"),
                             ayar.bugunku_kosu_sayisi(kok, "kasa-bakimi", "2026-09-16"))

    def test_kisa_adlar_ayarda_ve_panel_onu_kullanir(self):
        """Tek sözlük: panel ve komut kapısı aynı kaynaktan okur."""
        self.assertEqual(sahne.TAKIMLAR, ayar.TAKIM_KISA_ADLARI)
        self.assertEqual(ayar.TAKIM_KISA_ADLARI["satis"], "satis-muduru")


if __name__ == "__main__":
    unittest.main()
