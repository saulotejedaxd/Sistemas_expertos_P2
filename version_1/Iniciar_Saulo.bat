@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 saulo_sistema_experto.py
) else (
  python saulo_sistema_experto.py
)
pause
