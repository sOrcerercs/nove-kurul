#!/usr/bin/env python3
"""Bekçi karşılaştırma — aynı koşu kaydını birden çok yola verip kararları yan yana koyar.

ANAYASA §3 bekçinin ayrı aileden olmasını ister, ama **ayrı olması iyi olduğunu kanıtlamaz.**
Bu araç onu ölçer: elde tutulan beş fikstürden biri temiz, dördü kasıtlı bozuk. Her yolun
her fikstüre ne dediği tabloya düşer; beklenenden sapan satır işaretlenir.

Araç hiçbir dosyaya YAZMAZ — `bekci.denetle` bilerek çağrılmaz (o `durum.json`'a ve koşu
kaydına yazar). Yalnız `on_kontrol` ve yol fonksiyonları kullanılır.

Kullanım:
    python3 bin/bekci_karsilastir.py                  # .env'deki anahtarlara göre uygun yollar
    python3 bin/bekci_karsilastir.py --yol nim,haiku  # yolları elle seç
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar  # noqa: E402
import bekci  # noqa: E402

KOK = ayar.KOK
FIKSTUR_DIZINI = KOK / "tests" / "fikstur" / "bekci"

FIKSTURLER = [
    {"ad": "temiz", "dosya": "temiz.md", "beklenen": "kabul"},
    {"ad": "kaynaksiz-sayi", "dosya": "kaynaksiz-sayi.md", "beklenen": "red"},
    {"ad": "orneklemsiz-yuzde", "dosya": "orneklemsiz-yuzde.md", "beklenen": "red"},
    {"ad": "eposta-sizmis", "dosya": "eposta-sizmis.md", "beklenen": "red"},
    {"ad": "bos", "dosya": "bos.md", "beklenen": "red"},
]

YOLLAR = {
    "nim": ("NVIDIA_API_KEY", lambda anahtar, istem: bekci.nim_sor(anahtar, istem)),
    "openai": ("OPENAI_API_KEY", lambda anahtar, istem: bekci.openai_sor(anahtar, istem)),
    "haiku": (None, lambda anahtar, istem: bekci.haiku_sor(istem)),
}


def _istem(metin):
    return bekci._istem(
        (KOK / "ANAYASA.md").read_text(encoding="utf-8"),
        (KOK / "takimlar" / "_iskelet" / "kurallar.md").read_text(encoding="utf-8"),
        metin)


def calistir(yollar, ortam):
    """Her fikstürü her yola verir. Ön kontrolün yakaladığı kayıt modele HİÇ gitmez."""
    satirlar = []
    for f in FIKSTURLER:
        metin = (FIKSTUR_DIZINI / f["dosya"]).read_text(encoding="utf-8")
        bos = not metin.strip()
        ihlaller = bekci.on_kontrol(metin)
        on_kontrol = bos or bool(ihlaller)
        if on_kontrol:
            sonuclar = {y: "red" for y in yollar}
            sebep = "boş kayıt" if bos else ", ".join(ihlaller)
        else:
            istem = _istem(metin)
            sonuclar, sebep = {}, ""
            for y in yollar:
                anahtar_adi, cagir = YOLLAR[y]
                anahtar = str(ortam.get(anahtar_adi) or "").strip() if anahtar_adi else ""
                sonuclar[y] = (cagir(anahtar, istem) or {}).get("karar", "?")
        satirlar.append({"ad": f["ad"], "beklenen": f["beklenen"], "sonuclar": sonuclar,
                         "on_kontrol": on_kontrol, "sebep": sebep,
                         "sapma": any(k != f["beklenen"] for k in sonuclar.values())})
    return satirlar


def tablo(satirlar, yollar):
    basliklar = ["fikstür", "beklenen", *yollar, ""]
    cizgi = "| " + " | ".join(basliklar) + " |\n| " + " | ".join("---" for _ in basliklar) + " |\n"
    for s in satirlar:
        hucreler = [s["ad"], s["beklenen"], *[s["sonuclar"].get(y, "-") for y in yollar],
                    "SAPMA" if s["sapma"] else ("ön kontrol" if s["on_kontrol"] else "ok")]
        cizgi += "| " + " | ".join(hucreler) + " |\n"
    sapan = sum(1 for s in satirlar if s["sapma"])
    return cizgi + f"\n{len(satirlar) - sapan}/{len(satirlar)} beklenen sonuç" + (
        f" · {sapan} sapma" if sapan else "")


def uygun_yollar(ortam):
    secili = [y for y, (anahtar_adi, _) in YOLLAR.items()
              if anahtar_adi and str(ortam.get(anahtar_adi) or "").strip()]
    return secili + ["haiku"]


def main(argv):
    ortam = ayar.ortam_yukle()
    yollar = None
    if "--yol" in argv:
        yollar = [y.strip() for y in argv[argv.index("--yol") + 1].split(",") if y.strip() in YOLLAR]
    yollar = yollar or uygun_yollar(ortam)
    print(f"bekçi karşılaştırma — yollar: {', '.join(yollar)}\n")
    print(tablo(calistir(yollar, ortam), yollar))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
