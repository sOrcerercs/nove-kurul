# Nove Kurul Ofisi

> Nove Group yöneticileri için ajan ekosistemi. Kurul üyesi soru sorar; danışman ajanlar analiz eder,
> Denetçi kuralları denetler, CEO Ajanı ikinci kez kontrol edip onaylar. **Yayın düğmesi insanda.**
> Veri kaynakları salt okunur. Ayrıntılı tasarım: `NOVE-KURULUM.md`.

## Danışmanlar

| Danışman | Klasör | Durum |
|---|---|---|
| Finans Danışmanı | `takimlar/finans/` | kurulumda — form bekliyor (Faz 6) |
| Kalite Danışmanı | `takimlar/kalite/` | kurulumda — ilk danışman (Faz 4) |
| OKR Danışmanı | `takimlar/okr/` | kurulumda — form bekliyor (Faz 6) |
| Raporlama Danışmanı | `takimlar/raporlama/` | kurulumda — form bekliyor (Faz 6) |
| Satış Müdürü | `takimlar/satis-muduru/` | kurulumda — form bekliyor (Faz 6) |

"Kurulumda": `takim.md`'nin tanımı (frontmatter) henüz yok. Sürücü bu danışmanı koşturmaz, ajan dosyası üretmez,
İş Dağıtımcı ona soru göndermez (`ayar.kurulumda_mi`). Form `takim.md`'ye işlenince danışman kendiliğinden kurulu olur.

## Sistem rolleri

| Rol | Tanım | Sürücü |
|---|---|---|
| Q&A Danışmanı — giriş/çıkış kapısı, LLM'siz | `sirket/QA-DANISMANI.md` | `bin/soru_kapisi.py` (Faz 3) |
| İş Dağıtımcı — yönlendirme, zincir, koşu başlatma | `sirket/IS-DAGITIMCI.md` | `bin/dagitici.py` |
| Denetçi — birinci onay, ayrı model ailesi | `sirket/DENETCI.md` | `bin/bekci.py` (Stop hook) |
| CEO Ajanı — ikinci onay, karar kalitesi | `sirket/CEO-KIMLIGI.md` | `bin/ceo.py` (Faz 2) |

## Okuma sırası (her danışman, her koşuda)
1. `ANAYASA.md` — değişmez çerçeve
2. `sirket/AJAN-KIMLIGI.md` — kimsin, nasıl çalışırsın
3. `takimlar/<danisman>/kurallar.md` — danışmanın sınırları
4. `takimlar/<danisman>/takim.md` — koşu adımları ve çıktı sözleşmesi
5. `skills/` — işi karşılayan yetenek varsa

## Klasör yapısı
```
NOVE-KURULUM.md       kurulum belgesi — kararlar (N1–N11), akış, fazlar, açık sorular
ANAYASA.md            beş madde — İNSANIN dosyası, ajan değiştirmez
bin/                  kos.py · bekci.py · dagitici.py · gunluk.py · ayar.py · agents_uret.py · sahne.py · …
sirket/               AJAN-KIMLIGI.md · DENETCI.md · CEO-KIMLIGI.md · QA-DANISMANI.md · IS-DAGITIMCI.md · YETENEKLER.md
takimlar/<danisman>/  takim.md · kurallar.md · defter.md · durum.json · kosu/ · cikti/ · veri/
takimlar/_iskelet/    yeni danışmanın dört dosyalık iskeleti (bin/takim-olustur.sh)
skills/<ad>/SKILL.md  yetenekler
panel/                kurul üyelerinin arayüzü: giriş + Kurul Ofisi (demo verisiyle)
tests/                python3 -m unittest discover -s tests
sirket-log/           soru kayıtları, rapor, telemetri — git'e girmez
kasa/                 bilgi kasası (kendi git deposu) — git'e girmez
.env                  anahtarlar — asla commit'e girmez
```

## Yasaklar
- `.env` okuma, açma, ekrana basma — **kuralla değil, `.claude/settings.json`'daki `permissions.deny` ile kapalı**.
  Yanıt defteri (`yanitlar/`) ve onaylı formlar (`formlar/onayli/`) de aynı şekilde yazmaya kapalı; Yanıt defterine
  yalnız sürücü yazar.
- Veri kaynaklarına, prod veritabanına yazma; DDL ya da migration
- Mail, mesaj, yayın; kişiye ya da departmana talimat; tarayıcıyla panele giriş
- `ANAYASA.md`, `kurallar.md`, `formlar/onayli/`, `sirket/CEO-KIMLIGI.md` değiştirme — insanın
- Hasta ve müşteri adı, telefon, e-posta, TC kimlik numarası — hiçbir dosyaya

## Lisans
`LICENSE` dosyası olduğu gibi kalır; telif satırı silinmez ve değiştirilmez.
