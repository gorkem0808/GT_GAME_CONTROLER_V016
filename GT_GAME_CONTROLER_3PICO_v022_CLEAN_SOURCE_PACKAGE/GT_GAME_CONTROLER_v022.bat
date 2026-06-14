@echo off
chcp 65001 >nul
title GT GAME CONTROLER v022
cd /d "%~dp0"
if not exist gt_game_controler_v022.py (
  echo HATA: gt_game_controler_v022.py bu klasorde yok.
  echo ZIP icinden direkt calistirma. Once klasore tamamen cikar.
  pause
  exit /b 1
)
python --version >nul 2>nul
if errorlevel 1 (
  py -3 -m pip install -r requirements.txt
  py -3 gt_game_controler_v022.py
) else (
  python -m pip install -r requirements.txt
  python gt_game_controler_v022.py
)
pause
