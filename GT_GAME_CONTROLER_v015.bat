@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "gt_game_controler_v015.py" (
  echo HATA: gt_game_controler_v015.py bu klasorde yok.
  echo ZIP icinden direkt calistirma. Klasore tamamen cikar.
  pause
  exit /b 1
)
python --version >nul 2>&1
if errorlevel 1 (
  py -3 "%~dp0gt_game_controler_v015.py"
) else (
  python "%~dp0gt_game_controler_v015.py"
)
pause
