# Untersuchung Fix 0.55.1: Update 0.54 -> 0.55 am echten Windows-Rechner
$ErrorActionPreference = "Continue"
$Ziel = Join-Path $env:USERPROFILE "Desktop\Claude\Fisi Lernplattform Test"
$Out = Join-Path $PWD "protokolle"
New-Item -ItemType Directory -Force $Out | Out-Null
$Daten = Join-Path $env:APPDATA "FISI-Lernplattform"

function Version {
  (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue |
    Where-Object DisplayName -like "FISI*").DisplayVersion
}
function Prozesse($titel) {
  Write-Host "--- Prozessliste ($titel):"
  $p = Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue
  if ($p) { $p | Format-Table Id, StartTime, @{n="Fenster";e={$_.MainWindowTitle}} -AutoSize | Out-String | Write-Host }
  else { Write-Host "    (kein FISI-Lernplattform-Prozess)" }
}
function Setup($exe, $log, [switch]$MitDir) {
  # genau die Optionen, die fisi_update.install() uebergibt, plus /LOG
  $args = @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$log`"")
  if ($MitDir) { $args += "/DIR=`"$Ziel`"" }
  $t = Get-Date
  $p = Start-Process $exe -ArgumentList $args -Wait -PassThru
  Write-Host ("    Rueckgabewert Installer: {0}  (Dauer {1:n1} s)" -f $p.ExitCode, ((Get-Date) - $t).TotalSeconds)
  return $p.ExitCode
}

Write-Host "=== 1. Ausgangslage: 0.54 nach '$Ziel' installieren"
Setup "dl\Setup-0.54.exe" "$Out\0_install_054.log" -MitDir | Out-Null
Start-Sleep 20
Write-Host "    installierte Version: $(Version)"
if (-not (Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue)) {
  Start-Process (Join-Path $Ziel "FISI-Lernplattform.exe"); Start-Sleep 20 }
Prozesse "0.54 laeuft (steht fuer den haengenden Prozess)"

Write-Host "=== 2. Szenario A: Update auf 0.55, waehrend 0.54 noch laeuft"
$codeA = Setup "dl\Setup-0.55.exe" "$Out\A_update_mit_laufendem_prozess.log"
Write-Host "    installierte Version danach: $(Version)"
Prozesse "nach Szenario A"

Write-Host "=== 3. Szenario B: Prozess beendet, Update auf 0.55"
Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 3
Prozesse "vor Szenario B"
$codeB = Setup "dl\Setup-0.55.exe" "$Out\B_update_ohne_prozess.log"
Start-Sleep 5
Write-Host "    installierte Version danach: $(Version)"
Prozesse "nach Szenario B (Installer startet das Programm neu)"
Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "=== 4. Szenario C: Schliessen fuer das Update mit dem Code von 0.55 (Quellcode, Windows)"
$env:REPO = (Get-Location).Path
$env:FISI_DB_PATH = Join-Path $Out "c_daten\lernfortschritt.db"
New-Item -ItemType Directory -Force (Split-Path $env:FISI_DB_PATH) | Out-Null
python untersuchung\repro_close.py dashboard update 2>&1 | Select-String "ERGEBNIS|TclError" | Write-Host
Write-Host "--- fehler.log (Szenario C):"
Get-Content (Join-Path $Out "c_daten\fehler.log") -ErrorAction SilentlyContinue | Select-Object -Last 6 | Write-Host

Write-Host "=== Zusammenfassung: A=$codeA B=$codeB"
Write-Host "=== Auszug Installer-Protokoll A (Fehler/Rollback):"
Select-String -Path "$Out\A_update_mit_laufendem_prozess.log" -Pattern "error|fehler|roll|restart manager|in use|Benutzung|Exit|close|DeleteFile|Retry|Abort|succeeded" | ForEach-Object { Write-Host $_.Line }
