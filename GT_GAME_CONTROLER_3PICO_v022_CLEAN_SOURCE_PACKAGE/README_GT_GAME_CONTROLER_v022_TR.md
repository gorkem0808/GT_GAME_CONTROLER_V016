# GT GAME CONTROLER V022

Bu paket, 3 Pico sistemini yeniden temiz şekilde kurmak için hazırlandı.

## Yapı

- `piko1.uf2`  → P1 absolute mouse, GP19 aktif/pasif
- `piko2.uf2`  → P2 absolute mouse, GP19 aktif/pasif
- `controller.uf2` → Controller Pico, keyboard + coin/tetik/röle timer
- `GT_GAME_CONTROLER_v022.bat` → Test / kalibrasyon / ayar programı
- `gt_game_controler_v022.py` → Programın Python dosyası

## Controller ayarları programdan değişir

Program içinde şu pinler seçilebilir ve Controller Pico hafızasına kaydedilir:

- P1 coin GP
- P2 coin GP
- P1 tetik GP
- P2 tetik GP
- P1 röle GP
- P2 röle GP
- Röle tipi: ACTIVE HIGH / ACTIVE LOW
- Coin tipi: DRY kuru kontak / HIGH 3.3V pulse

Varsayılanlar:

```text
P1 coin  = GP17
P2 coin  = GP21
P1 tetik = GP7
P2 tetik = GP11
P1 röle  = GP26
P2 röle  = GP27
```

## Röle çalışma mantığı

```text
Coin geldi → oyuncu aktif olur
Tetik basıldı → seçilen röle GP çeker
Tetik bırakıldı → röle bırakır
3 dakika tetik basılmazsa → oyuncu pasif olur, tekrar coin gerekir
```

## Önemli bağlantılar

Röle modülü 5V ise:

```text
Controller Pico VBUS → Röle VCC
Controller Pico GND  → Röle GND
Seçilen röle GP      → Röle IN
```

Motoru Pico'dan besleme. Motor ayrı 12V adaptörden beslensin:

```text
12V +   → Röle COM
Röle NO → Motor +
Motor - → 12V -
```

Pico GPIO pinlerine direkt 5V verme. Para mekanizması 5V pulse veriyorsa optokuplör veya seviye düşürücü kullan.

## GitHub derleme

Bu kaynak paketi GitHub deposuna yükle. Sonra:

```text
Eylemler → Build GT GAME CONTROLER V022 UF2 → Run workflow / İş akışını çalıştır
```

Derleme bitince Yapıtlar / Artifacts bölümündeki ZIP içinde şunlar çıkacak:

```text
piko1.uf2
piko2.uf2
controller.uf2
GT_GAME_CONTROLER_v022.bat
gt_game_controler_v022.py
```

Önce Controller Pico'ya `controller.uf2` yükle. Sonra programdan cihaz tara ve röle testi yap.
