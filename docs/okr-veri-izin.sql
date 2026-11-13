-- OKR danışmanı — okr_okuyucu için app_settings okuma izni (yalnız `default_range_start` satırı)
--
-- NEDEN: Varsayılan aralığın başlangıcı sitede `app_settings` tablosundaki `default_range_start`
-- anahtarından gelir. `bin/okr_veri.py sema` bu tabloyu okuyamadığını gösterirse betik durmaz,
-- 2025-09-01'e düşer ve düşüşü kapsamda yazar; bu dosya o düşüşü kaldırır.
--
-- İZİN SATIR DÜZEYİNDEDİR: tabloya toptan SELECT verilmez; satır düzeyi güvenlik (RLS) politikası
-- okr_okuyucu'yu yalnız `key = 'default_range_start'` satırına bağlar. Başka ayar satırı görünmez.
--
-- KİM KOŞTURUR: Kağan, SQL editöründe. ANAYASA.md §1: "Prod veritabanına yazma yoktur:
-- `INSERT`/`UPDATE`/`DELETE`, DDL ve migration yasak." CLAUDE.md Yasaklar: "Veri kaynaklarına,
-- prod veritabanına yazma; DDL ya da migration". Ajan bu dosyayı çalıştırmaz; Kağan çalıştırır.
--
-- ===========================================================================
-- NASIL KOŞTURULUR — ADIMLARI TEK TEK ÇALIŞTIR
-- Editör betiği tek işlem sayar; bir ifade patlarsa hepsi geri alınır. Her adımın çıktısını
-- gör, sonra sonrakine geç. Hata olursa HATANIN TAM METNİNİ ver.
-- ===========================================================================


-- ===========================================================================
-- ADIM 1 — ön kontrol (salt okunur). Beklenen: true. false ise DUR, bu dosyayı çalıştırma, Claude'a bildir.
-- (RLS kapalıysa GRANT tüm satırları açardı.)
-- ===========================================================================
SELECT relrowsecurity FROM pg_class WHERE oid = 'public.app_settings'::regclass;


-- ===========================================================================
-- ADIM 2
-- ===========================================================================
GRANT SELECT ON public.app_settings TO okr_okuyucu;


-- ===========================================================================
-- ADIM 3
-- ===========================================================================
CREATE POLICY okr_okuyucu_aralik ON public.app_settings FOR SELECT TO okr_okuyucu USING (key = 'default_range_start');


-- ===========================================================================
-- ADIM 4 — doğrulama (salt okunur). Beklenen: tek satır, okr_okuyucu_aralik, SELECT.
-- ===========================================================================
SELECT policyname, cmd, roles, qual FROM pg_policies WHERE schemaname = 'public' AND tablename = 'app_settings';
