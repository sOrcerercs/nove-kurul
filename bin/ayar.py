#!/usr/bin/env python3
"""Şirketin tek ayar dosyası — mesai, tavanlar, yollar, anahtarlar.

Bütün betikler buradan okur; hiçbir sayı ikinci bir yerde yazılmaz.
Anahtarlar repo kökündeki `.env` dosyasındadır (`.env.example` kopyası) ve git'e girmez.
"""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
TAKIMLAR = KOK / "takimlar"
ENV_DOSYASI = KOK / ".env"

# --- mesai (ANAYASA 4) -----------------------------------------------------
MESAI_BASLANGIC = 8   # dahil — NOVE-KURULUM.md §9
MESAI_BITIS = 20      # hariç
MESAI_METNI = f"{MESAI_BASLANGIC:02d}:00-{MESAI_BITIS:02d}:00"

# --- tavanlar (ANAYASA 4) --------------------------------------------------
KOSU_BUTCESI_USD = 2.0          # tek koşunun para tavanı
KOSU_SURESI_SN = 15 * 60        # tek koşunun süre tavanı
KOSULAR_ARASI_DK = 0            # aynı takımın iki koşusu arası — 0: bekleme yok
GUNLUK_KOSU_TAVANI = 15         # danışman başına gün — soru akışı olaylı, takvimli değil (§9)
GUNLUK_MALIYET_TAVANI_USD = 40.0  # tüm şirket, gün — ilk ay ölçülür, sonra yeniden ayarlanır (§9)
ES_ZAMANLI_TAVAN = 3            # dağıtıcının aynı anda başlattığı takım sayısı (§9)

# --- soru akışı (NOVE-KURULUM.md §2, §5, §9) — Faz 2/3'te kullanılır ------------
SORU_BUTCESI_USD = 5.0          # soru başına toplam: danışman + düzeltme + Denetçi + CEO
KURUL_UYESI_GUNLUK_SORU = 10    # kurul üyesi başına gün — kötüye kullanım freni
BEKCI_MAKS_RED = 2              # Denetçi reddinde aynı oturumda en fazla düzeltme
CEO_ACIK = True                 # tasarımdaki `ceoSorgular`; üretimde açık ve kilitli
CEO_MAKS_RED = 1                # CEO reddinden sonra en fazla bir düzeltme turu
CEO_BUTCESI_USD = 0.50          # CEO kontrolü başına
CEO_SURESI_SN = 5 * 60

TAKIM_KISA_ADLARI = {          # telefonda ve panelde kısa yazılsın diye; tek sözlük (Nove danışmanları)
    "finans": "finans",
    "kalite": "kalite",
    "okr": "okr",
    "rapor": "raporlama",
    "satis": "satis-muduru",
}

KOSU_DOSYA_ADI = re.compile(r"^(\d{4}-\d{2}-\d{2})-\d{4}\.md$")   # grup birebir korunur
MALIYET_DESENI = re.compile(r"maliyet:\s*([\d.]+)\s*USD", re.IGNORECASE)


def bugunku_kosu_sayisi(kok, takim, bugun):
    """Takımın bugün kaç koşu kaydı yazdığı (ANAYASA §4 — günde 2)."""
    dizin = Path(kok) / "takimlar" / takim / "kosu"
    if not dizin.is_dir():
        return 0
    return sum(1 for p in dizin.glob("*.md")
               if KOSU_DOSYA_ADI.match(p.name) and p.name.startswith(bugun))


def gunluk_maliyet(kok, bugun):
    """Bugünkü bütün koşu kayıtlarındaki `maliyet: N USD` toplamı (ANAYASA §4 — 5 USD)."""
    toplam = 0.0
    for kosu in sorted((Path(kok) / "takimlar").glob("*/kosu/%s*.md" % bugun)):
        for ham in MALIYET_DESENI.findall(kosu.read_text(encoding="utf-8", errors="ignore")):
            try:
                toplam += float(ham)
            except ValueError:
                continue
    return toplam

# --- model köprüsü (docs/07-farkli-model.md) -------------------------------
# Varsayılan sağlayıcı Anthropic'tir. `takim.md`'de `saglayici: nim` yazan takım
# `bin/model_proxy.py`'nin ayağa kaldırdığı yerel LiteLLM proxy'sine yönlendirilir.
NIM_TABANI = "https://integrate.api.nvidia.com/v1"   # NVIDIA NIM uç adresi — bekçi ve köprü aynı yerden okur
NIM_PROXY_URL = "http://127.0.0.1:4000"   # yalnız yerel — dışarı açık değil
NIM_YEREL_TOKEN = "sk-nove-kurul-yerel"    # yerel proxy'nin bearer token'ı (gizli değil)
LITELLM_SURUM = "1.101.0"                 # uvx ile sabitlenir; bkz. model_proxy.YASAKLI_SURUMLER

ENV_SATIRI = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def simdi_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


# --- anahtarlar ------------------------------------------------------------

def env_yukle(yol=None):
    """`.env` dosyasını sözlük olarak okur; `export` ve tırnak toleranslı. Yoksa boş sözlük."""
    try:
        satirlar = Path(yol or ENV_DOSYASI).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    sonuc = {}
    for satir in satirlar:
        if satir.lstrip().startswith("#"):
            continue
        eslesme = ENV_SATIRI.match(satir)
        if eslesme:
            sonuc[eslesme.group(1)] = eslesme.group(2).strip("'\"")
    return sonuc


def ortam_yukle(yol=None):
    """`.env` içeriğini ortama yazar. **Proje `.env`'i kazanır**: kabukta aynı adla tanımlı bir
    değişken varsa üzerine yazılır — izleyici `.env`'e ne yazdıysa onu görür. `.env`'de geçmeyen
    değişkenlere dokunulmaz. Ortamın kopyasını döner."""
    for anahtar, deger in env_yukle(yol).items():
        os.environ[anahtar] = deger
    return dict(os.environ)


def eksik_anahtarlar(gerekli, ortam=None):
    ortam = ortam if ortam is not None else os.environ
    return [a for a in gerekli if not ortam.get(a)]


# --- mesai -----------------------------------------------------------------

def mesaide_mi(simdi=None):
    an = simdi or datetime.now()
    return MESAI_BASLANGIC <= an.hour < MESAI_BITIS


def sonraki_mesai(simdi=None):
    an = simdi or datetime.now()
    aday = an.replace(hour=MESAI_BASLANGIC, minute=0, second=0, microsecond=0)
    return aday if aday > an else aday + timedelta(days=1)


# --- takim.md frontmatter --------------------------------------------------

def _deger(ham):
    ham = ham.strip()
    if ham.startswith("[") and ham.endswith("]"):
        ic = ham[1:-1].strip()
        return [p.strip().strip("'\"") for p in ic.split(",")] if ic else []
    return ham.strip("'\"")


def frontmatter(metin):
    """Basit YAML frontmatter: `anahtar: değer` ve `[a, b]` listeleri. (fm, gövde) döner."""
    if not metin.startswith("---"):
        return {}, metin
    parcalar = metin.split("---", 2)
    if len(parcalar) < 3:
        return {}, metin
    fm = {}
    for satir in parcalar[1].splitlines():
        if ":" not in satir or satir.lstrip().startswith("#"):
            continue
        anahtar, ham = satir.split(":", 1)
        fm[anahtar.strip()] = _deger(ham)
    return fm, parcalar[2].lstrip("\n")


def takim_bilgisi(takim, kok=None):
    """`takimlar/<takim>/takim.md` frontmatter'ı; dosya yoksa None."""
    yol = Path(kok or KOK) / "takimlar" / takim / "takim.md"
    if not yol.is_file():
        return None
    fm, _ = frontmatter(yol.read_text(encoding="utf-8"))
    return fm


def kurulumda_mi(takim, kok=None):
    """`takim.md` var ama tanımı (frontmatter) yok → danışman kurulumda.

    NOVE-KURULUM.md Faz 6: verisi bağlanmamış danışman sahnede "kurulumda" görünür; sürücü onu
    koşturmaz, ajan dosyası üretmez. Danışman formu `takim.md`'ye işlenince kendiliğinden kurulu olur."""
    return takim_bilgisi(takim, kok) == {}


def kurulu_takimlar(kok=None):
    """`takim.md`'si tanımlı (frontmatter'lı) takımlar; `_` ile başlayan iskelet ve kurulumdakiler hariç."""
    dizin = Path(kok or KOK) / "takimlar"
    if not dizin.is_dir():
        return []
    return sorted(p.parent.name for p in dizin.glob("*/takim.md")
                  if not p.parent.name.startswith("_") and takim_bilgisi(p.parent.name, kok))


# --- durum.json ------------------------------------------------------------

def durum_yolu(takim, kok=None):
    return Path(kok or KOK) / "takimlar" / takim / "durum.json"


def durum_oku(takim, kok=None):
    try:
        return json.loads(durum_yolu(takim, kok).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def durum_guncelle(takim, yama, kok=None):
    """Yeni sözlük yazar (immutable birleştirme); yazılan durumu döner."""
    yol = durum_yolu(takim, kok)
    yeni = {**durum_oku(takim, kok), **yama}
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return yeni


def ozet(simdi=None):
    """`python3 bin/ayar.py` çıktısı — üç satır. Önce `.env` yüklenir."""
    ortam_yukle()
    an = simdi or datetime.now().astimezone()
    durum = "içinde" if mesaide_mi(an) else "dışında"
    return "\n".join([
        f"{an:%Y-%m-%d %H:%M} — mesai {durum} ({MESAI_METNI}), sonraki açılış {sonraki_mesai(an):%a %H:%M}",
        f"tavanlar: koşu {KOSU_BUTCESI_USD} USD / {KOSU_SURESI_SN // 60} dk · "
        f"takım günde {GUNLUK_KOSU_TAVANI} koşu · arası {KOSULAR_ARASI_DK} dk · "
        f"şirket günde {GUNLUK_MALIYET_TAVANI_USD} USD",
        f".env: {'var' if Path(ENV_DOSYASI).exists() else 'yok'}",
    ])


if __name__ == "__main__":
    print(ozet())
