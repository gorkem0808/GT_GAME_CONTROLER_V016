@echo off
cd /d "%~dp0"
py -3 gt_game_controler_v023.py
if errorlevel 1 python gt_game_controler_v023.py
pause
