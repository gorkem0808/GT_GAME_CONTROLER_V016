# GT GAME CONTROLER V019

Bu sürüm V018'deki iki hatayı düzeltir:

1. **P1/P2 coin GP seçimi kaydedilmiyordu.**  
   Örnek: P1 coin GP17 yerine GP3 seçilince tekrar GP17'ye dönüyordu.  
   V019'da hem program hem controller firmware düzeltildi.

2. **Gri kutucuk / combobox içindeki yazılar görünmüyordu.**  
   V019'da kutu zemini açık, yazı siyah olacak şekilde ayarlandı.

## Varsayılan pinler

- P1 tetik: GP7
- P2 tetik: GP11
- P1 coin: GP17
- P2 coin: GP21
- P1 röle: GP26
- P2 röle: GP27

## Çalışma mantığı

- Coin/kredi gelince ilgili oyuncu aktif olur.
- Tetik basılınca seçilen röle GP aktif olur, silah titreşim motoru çalışır.
- Tetik bırakılınca röle bırakır.
- 3 dakika tetik basılmazsa ilgili oyuncu pasif olur.
- Yeniden çalışması için tekrar coin gerekir.

## GitHub derleme

1. Bu klasörün içindeki tüm dosyaları GitHub deposuna yükle.
2. `.github/workflows/build_uf2.yml` dosyası doğru yerde olmalı.
3. Eylemler / Actions kısmından derlemeyi çalıştır.
4. Yeşil tikten sonra Artifacts/Yapıtlar kısmından ZIP'i indir.
5. Controller Pico'ya yeni `controller.uf2` yükle.

## Not

V019 programı eski V018 controller ile de ayar komutlarını uyumlu göndermeye çalışır. Ama en sağlam kullanım için V019 derlemesinden çıkan yeni `controller.uf2` yüklenmelidir.
