# Kurallar — OKR Danışmanı

> Bekçi bu dosyayı okur ve koşu kaydını buna göre denetler. Yalnızca insan değiştirir.
> Formdan üretildi: `formlar/onayli/okr.md` → `bin/formdan_takim.py`.

## Neye göre çalışır
- ANAYASA'nın tamamı geçerlidir; aşağıdakiler ona ektir.

## Asla yapmaz
- Hedef tanımını değiştirmek ya da yorumla yeniden yazmak
- Tanımsız ölçüm uydurmak; `—` ile `0`'ı karıştırmak
- okr_veri.py'nin vermediği bir sayıyı türetmek ya da yüzdeyi kendisi hesaplamak (betiğin sayısı sitenin sayısıdır)
- Veritabanına okr_okuyucu dışında bağlanmak ya da okr_veri.py dışında komut çalıştırmak
- Oran KR'ını (oran_notu=evet) notsuz vermek
- Yalnız bir çeyreğin dilimini hesaplamak (sayı mali yıl başından birikir)
- Check-in kaydı yokken check-in'e dayanan soruya tahminle yanıt vermek
- Kişiye puan ya da başarı skalası vermek

## Çıktı kalite ölçütleri
- Her iddia etiketli (✅/🟡/⛔) ve kaynaklı.
- Çıktı Türkçe; teknik terimler orijinal hâliyle kalır.
- dönem kodu (mali yıl Eylül'de başlar), son dolu ay, her `—` için sebep · ana yüzde StD'dir, yıllık yanında · aralık birden çok dönemi kapsıyorsa bunun söylenmesi

## Teyit ve hassas veri
- Personel adı ve unvanı yazılabilir. Hasta ve müşterinin adı soyadı yazılabilir; telefon, e-posta, TC kimlik no yazılmaz (ANAYASA §2).
- Sayıyı kim teyit eder:
  - Tüm yüzdeler: Kağan
  - Site hesabı (Nove Performance lib/domain ve lib/queries/{tree,std,range}.ts) değişirse bin/okr_hesap.py güncellenir ve üç sayılık karşılaştırma yinelenir: Kağan
- Hassas alanlar (KVKK) — bilgi amaçlı, kural koymaz; ne yazılacağını yukarıdaki satır belirler:
  - kullanıcı tablosu (e-posta, parola özeti — betik okumaz), objective/KR sorumlularının adları
- Formülü teyitsiz göstergeler — hesaplanmaz, `—` gösterilir ve teyit sahibi yazılır:
  - Marketing Score, Lead Score — tanımlı değil, `—` gösterilir
