@echo off
REM ===========================================================================
REM  Fachinformatiker Lernplattform - Windows-Installer lokal erstellen
REM ===========================================================================
REM  Ergebnis: installer_output\FISI-Lernplattform-Setup-<Version>.exe
REM  Der Installer bringt alles mit und laeuft ohne installiertes Python.
REM
REM  Benoetigt Python 3.8+ und Inno Setup 6 (https://jrsoftware.org/isdl.php).
REM  Die eigentliche Arbeit erledigt build.py. Installer fuer Linux und macOS
REM  entstehen per GitHub Actions (siehe INSTALLER-ANLEITUNG.txt).
REM ===========================================================================

setlocal
cd /d "%~dp0"

echo.
echo ===========================================================
echo   Fachinformatiker Lernplattform - Windows-Installer wird erstellt
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

REM --- 3. Bibliotheken und PyInstaller bereitstellen ---------------------------
echo [..] CustomTkinter, Pillow und PyInstaller werden bereitgestellt ...
python -m pip install --quiet -r requirements-build.txt
if errorlevel 1 (
    echo [FEHLER] Die Bibliotheken konnten nicht installiert werden.
    echo Besteht eine Internetverbindung?
    pause
    exit /b 1
)
echo [OK] Bibliotheken bereit

REM --- 4. Anwendung und Installer bauen ----------------------------------------
echo.
echo [..] Das dauert ein bis zwei Minuten ...
echo.
python build.py
if errorlevel 1 (
    echo.
    echo [FEHLER] Der Build ist fehlgeschlagen. Meldung siehe oben.
    pause
    exit /b 1
)

echo.
echo ===========================================================
echo   Fertig - der Installer liegt im Ordner installer_output
echo ===========================================================
echo.
echo   Die Lernfortschritte werden gespeichert unter:
echo   %%APPDATA%%\FISI-Lernplattform\fisi_lernplattform.db
echo.
pause
endlocal
