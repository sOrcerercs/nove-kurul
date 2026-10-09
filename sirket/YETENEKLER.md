# YETENEKLER — Nove Kurul Ofisi

> Danışmanların kullandığı yeteneklerin kataloğu.
> Bir yetenek, o işin nasıl yapılacağını adım adım, şablonuyla ve kontrol listesiyle anlatan tek dosyadır:
> `skills/<ad>/SKILL.md`. Ajan koşu adımında **yalnızca ilgili yeteneği** okur.

## Neden bu dosyalar var — üç gerekçe

1. **Token sorununu çözmek.** Bir işin nasıl yapılacağını her koşuda baştan anlatmak pahalıdır ve her
   seferinde biraz farklı çıkar. Yetenek dosyası bir kez yazılır, ajan koşuda sadece ilgili adımda okur.
2. **Ajanın hatırlaması.** Ajanın hafızası yok; oturum kapanınca her şey gider. `defter.md` dünü,
   `skills/` ise **nasıl yapıldığını** hatırlar. Yazmadığın şey olmamıştır.
3. **Ajanın gelişmesi.** Her yetenek dosyasının sonunda `## Öğrenilenler` bölümü var. Ajan koşuda aldığı
   veriyle kendini geliştirir: dersi `defter.md`'ye yazar, aynı ders üç koşuda tekrar ederse yeteneğin
   `## Öğrenilenler` bölümüne öneri bırakır. Kararı Kağan verir.

## Katalog

| Danışman | Yetenek | Ne işe yarar | Kaynak | Lisans |
|---|---|---|---|---|

**Toplam 0 yetenek.** Danışmanlar formdan doldurulup kuruldukça (NOVE-KURULUM.md Faz 4 ve 6) eklenir.

## Planlanan

| Danışman | Yetenek | Ne zaman | Not |
|---|---|---|---|
| `kalite` | `qa-koclugu-kurgusu` | Faz 4 | kagan-sirketi'deki yetenek Kalite danışmanına uyarlanarak taşınır |

## Nasıl çalışır (teknik)

- Kaynak: `takimlar/<danisman>/takim.md` frontmatter'ındaki `skills: [ad1, ad2]` alanı.
- `bin/agents_uret.py` bu alanı **şirket alanı** sayar (agent frontmatter'ına sızmaz) ve önsöze
  `Yeteneklerin: ...` satırını ekler.
- `bin/kos.py` `istem()` aynı satırı koşu istemine koyar — `python3 bin/kos.py <danisman> --kuru` ile görülür.
- Bağın bütünlüğünü `tests/test_skills.py` denetler: bildirilen her yetenek diskte var mı, her yetenek
  hangi takımı bildiriyorsa o takım da onu bildiriyor mu, her dosya `## Öğrenilenler` taşıyor mu,
  bu katalog güncel mi.
