# GT GAME CONTROLER V019 - Temiz Kaynak Paket

Bu paket önceki başarısız V010-V014 yamalama yöntemini kullanmaz.
Controller firmware, eski çalışan `keyboard_main.c` mantığı korunarak C kaynak kodundan temiz şekilde derlenmelidir.

## Neden bu paket kaynak olarak verildi?
Bu ortamda Raspberry Pi Pico SDK / ARM GCC toolchain yok. Eski çalışan UF2 içine röle kodu güvenli şekilde eklenemez.
Bu yüzden sahte/yamalı UF2 üretmek yerine gerçek derlenebilir kaynak ve GitHub Actions otomatik derleme sistemi verildi.

## Derlenince çıkacak UF2 dosyaları
- `piko1.uf2`  → Player 1 mouse, GP19 aktif/pasif
- `piko2.uf2`  → Player 2 mouse, GP19 aktif/pasif
- `controller.uf2` → Eski çalışan controller tabanı + röle + coin tipi + tuş atama

## Controller röle pinleri
- P1 röle: GP26
- P2 röle: GP27

## Controller girişleri
- P1 tetik: GP7
- P1 coin: GP17
- P2 tetik: GP11
- P2 coin: GP21

## Röle bağlantısı
P1 röle:
- Controller Pico VBUS → Röle VCC
- Controller Pico GND  → Röle GND
- Controller Pico GP26 → Röle IN

P2 röle:
- Controller Pico VBUS → Röle VCC
- Controller Pico GND  → Röle GND
- Controller Pico GP27 → Röle IN

Motoru Pico VBUS'tan besleme. Motor ayrı 12V adaptörden beslensin.

## GitHub Actions ile UF2 üretme
1. GitHub'da yeni repo aç.
2. Bu paketin içindeki dosyaları aynen yükle.
3. Actions sekmesine gir.
4. `Build GT GAME CONTROLER V019 UF2` işini çalıştır.
5. Yeşil tik bitince Artifacts kısmından `GT_GAME_CONTROLER_3PICO_v019_UF2_READY` dosyasını indir.
6. İçinden `controller.uf2`, `piko1.uf2`, `piko2.uf2` çıkacak.

## Eski controller'a geri dönme
Paket içinde `controller_ESKI_CALISAN_KURTARMA.uf2` var. Bunu yüklersen eski çalışan klavye controller haline döner.

## İlk test
1. Önce sadece Controller Pico'ya derlenen `controller.uf2` yükle.
2. Not Defteri aç.
3. GP6 → GND = 5 yazmalı.
4. GT_GAME_CONTROLER_v019.bat çalıştır.
5. Cihazları Tara / Yenile yap.
6. Röle Testi sekmesinden P1/P2 röleyi test et.

İlk testte motorun 12V beslemesini bağlama; sadece röle LED'i ile dene.


## V019 Yenilikleri

- GT GAME CONTROLER programı daha renkli/canlı arayüzle yenilendi.
- Controller ayarlarına P1 tetik röle GP ve P2 tetik röle GP seçimi eklendi.
- Varsayılan röle pinleri: P1=GP26, P2=GP27.
- Programdan Active High / Active Low, P1/P2 coin tipi ve röle GP pinleri Controller Pico hafızasına kaydedilir.
- Çalışma mantığı: Coin geldikten sonra tetik basılıyken röle çeker; tetik bırakılınca röle bırakır; 180 saniye tetik basılmazsa oyuncu pasif olur.

## Önerilen bağlantı

P1 titreşim rölesi için varsayılan: Controller Pico GP26 -> Röle IN.
P2 titreşim rölesi için varsayılan: Controller Pico GP27 -> Röle IN.
Röle VCC 5V röle modülünde Pico VBUS'a, GND Pico GND'ye bağlanabilir. Motor beslemesi Pico'dan alınmamalıdır.


## V019 Düzeltmeleri
- Açılır seçim kutularında yazılar artık siyah/beyaz kontrastla net görünür.
- Kullanıcı röle/coin GP seçerken program eski ayarı otomatik geri yazmaz.
- P1/P2 coin GP pinleri de seçilebilir hale getirildi. Varsayılan P1 coin GP17, P2 coin GP21.
