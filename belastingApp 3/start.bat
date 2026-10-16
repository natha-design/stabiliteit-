@echo off
title Gebouwbelasting
cd /d "%~dp0"

set PY=
where py >nul 2>nul && set PY=py
if "%PY%"=="" where python >nul 2>nul && set PY=python

if "%PY%"=="" (
    echo Python is niet gevonden.
    echo Installeer Python via https://www.python.org/downloads/
    echo en vink "Add python.exe to PATH" aan tijdens de installatie.
    echo.
    pause
    exit /b 1
)

echo Pakketten controleren / installeren (eerste keer kan even duren)...
%PY% -m pip install --quiet streamlit pandas openpyxl
if errorlevel 1 (
    echo.
    echo Installatie van de pakketten is mislukt. Controleer je internetverbinding.
    pause
    exit /b 1
)

echo.
echo App wordt gestart. Je browser opent automatisch.
echo Sluit dit venster of druk Ctrl+C om te stoppen.
echo.
%PY% -m streamlit run gebouwbelasting_frontend.py
pause
