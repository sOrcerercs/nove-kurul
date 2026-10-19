---
name: kurul-yaniti
description: Kurula giden taslağın düzeni — Kısa yanıt, Dayanak, Bilinmeyenler, Not. Her danışmanın her taslağında.
kaynak: Nove Kurul Ofisi (yerli yetenek, 19.10.2026)
lisans: MIT (LICENSE)
uyarlayan: Nove Kurul Ofisi
takimlar: [kalite]
---

# kurul-yaniti — taslağın düzeni

Bu yetenek kural koymaz. Kurallar `ANAYASA.md` §2'de ve `sirket/AJAN-KIMLIGI.md`'de (etiket, kaynak, `n`, `—`,
kişisel veri). Burada yalnız **düzen** var: kurul üyesi her danışmanın yanıtını aynı yerden okur.

## Ne zaman

Her koşuda, `takimlar/<danisman>/cikti/<soru-id>-taslak.md` yazarken. `r-` (CEO reddinden sonra düzeltme)
maddesinde de aynı düzen korunur; yalnız CEO'nun bulduğu yer düzeltilir.

## Düzen

Taslak bu dört başlığı bu sırayla taşır. İlk üçü her zaman vardır; `Not` yalnız söylenecek bir şey varsa.

```
# <soru-id> — <sorunun kısa adı>

## Kısa yanıt
## Dayanak
## Bilinmeyenler
## Not
```

## Kısa yanıt

- 2–3 cümle. **İlk cümle sorunun cevabıdır** — soru "hangisi" diyorsa ilk cümle hangisi olduğunu söyler.
- Soru belirsizse hangi yorumla yanıtladığın burada, ilk cümleden hemen sonra yazar.
- Cevap verilemiyorsa ilk cümle bunu söyler ve sebebini verir ("veri bağlı değil", "formül teyit bekliyor").

Örnek (yer tutucular `<…>`; sayı uydurulmaz):

> <Ekip adı>, <dönem> içinde kalite puanı en çok düşen ekip. Düşüş <puan> puan ✅; ölçülen çağrı sayısı küçük
> (n=<n>), bu yüzden eğilim değil işaret olarak okunmalı.

## Dayanak

- Cevabı taşıyan iddialar, madde madde. Her iddianın yanında etiketi (✅ birincil · 🟡 ikincil · ⛔ doğrulanamadı),
  kaynağı ve örneklemden geliyorsa `n`'i.
- Sayılar tabloya girebilir; tablonun her satırı da kaynaklıdır.
- Bağlam ve yöntem cümleleri etiketsiz kalabilir (ANAYASA §2).

Örnek:

> - <dönem> kalite puanı <puan> ✅ — `veri/<dosya>`, n=<n>
> - Önceki dönem <puan> ✅ — aynı kaynak, n=<n>
> - Düşüşün en çok görüldüğü bölüm: <bölüm> 🟡 — bölüm skorları, ağırlıklar teyit bekliyor

## Bilinmeyenler

- Doğrulanamayanlar (⛔), formülü teyitsiz için `—` gösterilen göstergeler ve **teyidi kimin vereceği**.
- Bilinmeyen yoksa tek satır: `yok`.

Örnek:

> - Bölüm ağırlıklı skor: `—` — ağırlıkları <unvan> teyit edecek.

## Not

- İsteğe bağlı. Başka bir danışmanı ilgilendiren nokta (`öneri: <danışman>`), verideki bir hata, kurulun
  bilmesi gereken bir sınır.
- Koşu kaydındaki `öneri:` satırı ayrıca yazılır; bu bölüm onun yerine geçmez.

## Öğrenilenler

Ajan koşuda aldığı veriyle kendini geliştirir: düzenle ilgili tekrarlayan ders önce `defter.md`'ye yazılır;
aynı ders üç koşuda tekrar ederse buraya öneri olarak bırakılır. Kararı Kağan verir.

- (henüz yok)
