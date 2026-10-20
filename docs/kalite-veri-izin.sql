-- Kalite danışmanı — qa_okuyucu için ek SÜTUN izinleri
--
-- NEDEN: `bin/kalite_veri.py sema` ölçümü (qa_okuyucu, UTC) iki sütunun kapalı olduğunu gösterdi:
--     Evaluation."callClassification"  — sayım koşulu (SAYIM_KOSULU) bunsuz kurulamaz
--     Evaluation."coachingSeenAt"      — koçluk görüldü bilgisi (kocluk alt komutu)
-- Haftanın çağrısı tablosu (WeeklyBestCall) da hiç okunamıyor.
--
-- İZİN SÜTUN DÜZEYİNDEDİR: tabloya toptan SELECT verilmez. `qa_degerlendirme` ve `qa_kriter`
-- görünümlerine DOKUNULMAZ. Serbest metin sütunları (`note`, `approachNote`) bilerek
-- DIŞARIDA bırakıldı; transcript · report · reportData · customerName · evidence ·
-- medicalFlags zaten kapalıdır ve kapalı kalır.
--
-- KİM KOŞTURUR: Kağan, Supabase SQL editöründe. ANAYASA — "Şema/yetki değişikliğini insan
-- kendi çalıştırır." Ajan bu dosyayı çalıştırmaz.
--
-- ===========================================================================
-- NASIL KOŞTURULUR — ADIMLARI TEK TEK ÇALIŞTIR
-- Editör betiği tek işlem sayar; bir ifade patlarsa hepsi geri alınır. Her adımın çıktısını
-- gör, sonra sonrakine geç. Hata olursa HATANIN TAM METNİNİ ver.
-- ===========================================================================


-- ===========================================================================
-- ADIM 1 (ZORUNLU) — sınıflandırma ve koçluk-görüldü sütunları
-- ===========================================================================
GRANT SELECT ("callClassification", "coachingSeenAt") ON public."Evaluation" TO qa_okuyucu;


-- ===========================================================================
-- ADIM 2 (İSTEĞE BAĞLI) — haftanın çağrısı
-- Yalnız yapısal sütunlar; serbest metin `note` ve `approachNote` verilmez.
-- ===========================================================================
GRANT SELECT (id, "teamId", "isoWeek", "evaluationId", "sharedAt", approach, origin) ON public."WeeklyBestCall" TO qa_okuyucu;


-- ===========================================================================
-- ADIM 3 — doğrulama (salt okunur)
-- Beklenen: Adım 1 için iki satır (callClassification, coachingSeenAt; SELECT);
-- Adım 2'yi koşturduysan WeeklyBestCall için yedi satır daha.
-- ===========================================================================
SELECT table_name, column_name, privilege_type
  FROM information_schema.column_privileges
 WHERE grantee = 'qa_okuyucu'
   AND table_schema = 'public'
   AND ((table_name = 'Evaluation' AND column_name IN ('callClassification', 'coachingSeenAt'))
        OR table_name = 'WeeklyBestCall')
 ORDER BY table_name, column_name;
