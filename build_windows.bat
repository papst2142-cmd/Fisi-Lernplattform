@echo off
REM ===========================================================================
REM  FISI Lernplattform - Erstellt eine eigenstaendige Windows-Anwendung
REM ===========================================================================
REM  Ergebnis: dist\FISI-Lernplattform.exe
REM  Diese Datei laeuft ohne installiertes Python auf jedem Windows-Rechner.
REM ===========================================================================

setlocal
cd /d "%~dp0"

echo.
echo ===========================================================
echo   FISI Lernplattform - Windows-Paket wird erstellt
echo ===========================================================
echo.

REM --- 1. Python vorhanden? --------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden.
    echo.
    echo Bitte Python von https://www.python.org/downloads/ installieren
    echo und dabei "Add Python to PATH" ankreuzen.
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version') do echo [OK] %%v gefunden

REM --- 2. Tkinter vorhanden? -------------------------------------------------
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Tkinter fehlt in dieser Python-Installation.
    echo Bitte Python neu installieren und "tcl/tk and IDLE" aktiviert lassen.
    echo.
    pause
    exit /b 1
)
echo [OK] Tkinter vorhanden

REM --- 3. PyInstaller bereitstellen ------------------------------------------
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [..] PyInstaller wird installiert ...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [FEHLER] PyInstaller konnte nicht installiert werden.
        echo Besteht eine Internetverbindung?
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller bereit

REM --- 4. Alte Ergebnisse entfernen ------------------------------------------
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist FISI-Lernplattform.spec del /q FISI-Lernplattform.spec

REM --- 5. Anwendung bauen ----------------------------------------------------
echo.
echo [..] Anwendung wird gebaut, das dauert ein bis zwei Minuten ...
echo.
set ICON_OPTION=
if exist icon.ico set ICON_OPTION=--icon icon.ico

python -m PyInstaller ^
    --name "FISI-Lernplattform" ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --clean ^
    %ICON_OPTION% ^
    --add-data "fisi_core.py;." ^
    --add-data "fisi_widgets.py;." ^
    --add-data "app_gui.py;." ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    start.py

if errorlevel 1 (
    echo.
    echo [FEHLER] Der Build ist fehlgeschlagen. Meldung siehe oben.
    pause
    exit /b 1
)

echo.
echo ===========================================================
echo   Fertig
echo ===========================================================
echo.
echo   Die Anwendung liegt hier:
echo   %cd%\dist\FISI-Lernplattform.exe
echo.
echo   Diese Datei laesst sich frei kopieren und braucht kein
echo   installiertes Python mehr.
echo.
echo   Die Lernfortschritte werden gespeichert unter:
echo   %%APPDATA%%\FISI-Lernplattform\fisi_lernplattform.db
echo.
pause
endlocal
