# GT GAME CONTROLER V020

V020, V019 tabanını korur. Sadece Controller Ayar ekranındaki kaydetme davranışı düzeltildi.

## Düzeltilen hata

- P1 coin GP17 yerine GP3 seçilip kaydedildiğinde ekranda tekrar GP17 görünmesi engellendi.
- Kaydet sonrası eski STATUS satırı gelirse combobox değerleri geri çevrilmez.
- Program, Controller Pico yeni ayarı gerçekten geri bildirdi mi diye kontrol eder.
- Eğer Controller eski değeri geri bildirirse uyarı verir: Bu durumda Controller Pico'da eski UF2 yüklüdür.

## Mantık aynı kaldı

- P1 coin varsayılan: GP17
- P2 coin varsayılan: GP21
- P1 röle varsayılan: GP26
- P2 röle varsayılan: GP27
- Coin/kredi sonrası tetik basınca röle çeker.
- Tetik bırakılınca röle bırakır.
- 180 saniye tetik yoksa oyuncu pasif olur.

## Derleme

GitHub Actions ile derleme yapılır. Çıkan artifact içinde piko1.uf2, piko2.uf2 ve controller.uf2 bulunur.

Önce controller.uf2 dosyasını Controller Pico'ya yükleyin.


## V021 Notu

Bu sürümde P1/P2 tetik GP seçimi eklendi. Controller Ayarları bölümünden P1 coin GP, P2 coin GP, P1 tetik GP, P2 tetik GP, P1 röle GP ve P2 röle GP ayrı ayrı seçilip Controller'a kaydedilebilir. Varsayılanlar: P1 coin GP17, P2 coin GP21, P1 tetik GP7, P2 tetik GP11, P1 röle GP26, P2 röle GP27.
