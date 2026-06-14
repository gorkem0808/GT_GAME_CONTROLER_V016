# GT GAME CONTROLER V023 - V021 Arayüzlü Temiz Paket

Bu paket V021 program arayüzü temel alınarak hazırlandı. V022’deki farklı görünüm kaldırıldı.

## Amaç
- Program V021 gibi görünsün ve çalışsın.
- Controller firmware içinde coin GP, tetik GP ve röle GP seçimi çalışsın.
- Kaydedilen ayarlar Controller Pico hafızasında kalsın.

## Varsayılan pinler
- P1 coin: GP17
- P2 coin: GP21
- P1 tetik: GP7
- P2 tetik: GP11
- P1 röle: GP26
- P2 röle: GP27

## Çalışma mantığı
Coin geldikten sonra oyuncu aktif olur. Tetik basılınca seçilen röle GP pini aktif olur. Tetik bırakılınca röle bırakır. 180 saniye tetik basılmazsa oyuncu pasif olur.

## GitHub derleme
Bu paketi GitHub deposuna yükle. Actions / Eylemler kısmında build_uf2 iş akışını çalıştır. Çıkan artifact ZIP içinde piko1.uf2, piko2.uf2 ve controller.uf2 olur.
