# Danışman Formu — <Bölüm adı>

> Bu formu bölüm yöneticisi doldurur. Son hâlini Kağan verir. Bilmediğin alanı boş bırak ya da "?" yaz — uydurma.
> Telefon, e-posta, TC kimlik no YAZMA: betik formda bunları bulursa durur.
> Biçim: her alan `- Etiket: değer` satırıdır. Birden çok madde varsa alt satırlara iki boşluk girintiyle yaz.
> Başlık numaralarını (`## 1.` … `## 7.`) değiştirme; betik bölümleri numarasından bulur.

## 1. Kimlik
- Danışman adı (odada görünecek):
- Yöneticinin adı soyadı (yalnız formda kalır):
- Yöneticinin unvanı:
- Tek cümleyle mesleği:
- Sahnedeki rengi (isteğe bağlı):

> ör. Danışman adı: Finans · Yöneticinin unvanı: Finans Müdürü · Renk: yeşil
> ör. Mesleği: "Finans danışmanı olarak kurulun bütçe, nakit ve maliyet sorularını muhasebe verisiyle yanıtlamak."

## 2. Hangi soruları alır
- Bu danışmana gelmesi gereken 5 örnek soru:
  1.
  2.
  3.
  4.
  5.
- Anahtar kelimeler (virgülle; İş Dağıtımcı bunlarla yönlendirir):
- Bu danışmana GELMEMESİ gereken, karışabilecek sorular:

> ör. anahtar kelimeler: bütçe, nakit, maliyet, sapma

## 3. Veri
| Kaynak | Ne var içinde | Nerede (sistem/dosya) | Kim erişim verir | Ne sıklıkta güncellenir |
|---|---|---|---|---|
|  |  |  |  |  |

- Bu verideki hassas alanlar (KVKK):
- Formülü/tanımı herkesçe bilinmeyen göstergeler:

> ör. gösterge: "upsell oranı nasıl hesaplanır" — formülü teyit edilene kadar `—` gösterilir.

## 4. Kurallar (kurallar.md'ye gidecek)
- Bu danışman ASLA şunu yapmamalı:
- Her yanıtta mutlaka olması gereken:
- Hangi sayıyı kim teyit eder:

## 5. İyi yanıt nasıl görünür
- Kurula giden ideal yanıtın bir örneği (yarım sayfa yeter):

## 6. Tempo (isteğe bağlı)
- Soru beklemeden düzenli üretmesini istediğin bir rapor:

> ör. "her pazartesi bütçe sapması"

## 7. Revize (Kağan doldurur)
- Model (boşsa sonnet):
- Ek yetenekler (virgülle; kurul-yaniti kendiliğinden eklenir):
- Gerekli anahtarlar (virgülle, ör. QA_READONLY_URL):
- Personel adı (boşsa evet; kapatmak için hayır):

## Kağan'ın revize kontrol listesi

`formlar/onayli/`'ye almadan önce. İşaretli olanları betik ayrıca denetler.

- [ ] Mesleği tek cümle ve bir fiille bitiyor (`description` alanı bu cümle olur)
- [ ] Anahtar kelimeler diğer danışmanlarla çakışmıyor — betik uyarır
- [ ] Her veri kaynağı **salt okunur** bir yolla bağlanabiliyor (SELECT rolü, dışa aktarım, paylaşılan klasör)
- [ ] Formülü teyitsiz gösterge `—` olarak işaretli ve teyit sahibi yazılı
- [ ] Formda kişisel veri yok — betik durur
- [ ] Ek yetenekler `skills/` altında var — betik durur
