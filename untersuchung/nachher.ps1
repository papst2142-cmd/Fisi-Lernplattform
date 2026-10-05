# Untersuchung Fix 0.55.1: der reparierte Stand am echten Windows-Rechner
$ErrorActionPreference = "Continue"
$Out = Join-Path $PWD "protokolle_nachher"
New-Item -ItemType Directory -Force $Out | Out-Null
Start-Transcript -Path "$Out\konsole.txt" -Force | Out-Null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$Ziel = Join-Path $env:USERPROFILE "Desktop\Claude\Fisi Lernplattform Test Ä"
$Exe = Join-Path $Ziel "FISI-Lernplattform.exe"
$Daten = Join-Path $env:APPDATA "FISI-Lernplattform"
$UpdDir = Join-Path $env:TEMP "FISI Update Ü"
New-Item -ItemType Directory -Force $UpdDir | Out-Null
$Gebaut = (Get-ChildItem "fix\installer_output\*Setup*.exe")[0].FullName
$Setup = Join-Path $UpdDir "FISI-Lernplattform-Setup-0.55.exe"
Copy-Item $Gebaut $Setup

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
function Bild($name) {
  $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
  $bmp.Save("$Out\$name.png"); $g.Dispose(); $bmp.Dispose()
}
function Alle-Beenden { Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2 }
function Starte-App {
  Start-Process $Exe | Out-Null
  Start-Sleep 25
  return (Get-Process FISI-Lernplattform | Sort-Object StartTime | Select-Object -Last 1)
}
function Update($app, $target, [switch]$Schliessen, $name) {
  Remove-Item "$Daten\update.log", "$Daten\update_installer.log" -ErrorAction SilentlyContinue
  $t = Get-Date
  $h = Start-Process python -ArgumentList @("untersuchung\starte_update.py", "`"$Setup`"", $app.Id, "`"$Exe`"", $target) `
       -RedirectStandardOutput "$Out\$name.harness.txt" -PassThru -NoNewWindow
  if ($Schliessen) {
    Start-Sleep 3
    Write-Host "    Programm wird geschlossen (wie Klick aufs X, WM_CLOSE) ..."
    $null = $app.CloseMainWindow()
  }
  if (-not $h.WaitForExit(240000)) { Write-Host "    Installer haengt nach 240 s"; $h.Kill() }
  Write-Host ("    Dauer bis Installer-Ende: {0:n1} s" -f ((Get-Date) - $t).TotalSeconds)
  Get-Content "$Out\$name.harness.txt" | Write-Host
  Start-Sleep 20
  Write-Host "    installierte Version: $(Version)"
  Prozesse "nach $name"
  Copy-Item "$Daten\update.log" "$Out\$name.update.log" -ErrorAction SilentlyContinue
  Copy-Item "$Daten\update_installer.log" "$Out\$name.installer.log" -ErrorAction SilentlyContinue
  Write-Host "--- update.log ($name):"
  Get-Content "$Daten\update.log" -Encoding utf8 -ErrorAction SilentlyContinue | Write-Host
}

Write-Host "=== 0. Reparierte Version nach '$Ziel' installieren (Leerzeichen + Umlaut)"
Write-Host "    Installer: $Setup"
$p = Start-Process $Setup -ArgumentList @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/DIR=`"$Ziel`"", "/LOG=`"$Out\0_install.log`"") -PassThru
$null = $p.WaitForExit(300000); Write-Host "    Rueckgabewert: $($p.ExitCode)"
Start-Sleep 25
Write-Host "    installierte Version: $(Version)"
Alle-Beenden

Write-Host "=== 1. Schliessen am X (WM_CLOSE): endet der Prozess, bleibt fehler.log leer?"
Remove-Item "$Daten\fehler.log" -ErrorAction SilentlyContinue
$app = Starte-App
Prozesse "laeuft"
$t = Get-Date; $null = $app.CloseMainWindow()
$ende = $app.WaitForExit(20000)
Write-Host ("    beendet: {0}  nach {1:n1} s" -f $ende, ((Get-Date) - $t).TotalSeconds)
Prozesse "nach dem Schliessen"
Write-Host "    fehler.log vorhanden: $(Test-Path "$Daten\fehler.log")"

Write-Host "=== 2. Szenario N1: Update, Programm schliesst sich normal"
$app = Starte-App
Update $app "0.55" -Schliessen "N1_normal"
Alle-Beenden

Write-Host "=== 3. Szenario N2: Update, Programm haengt (schliesst sich nicht)"
$app = Starte-App
Update $app "0.55" "N2_programm_haengt"
Alle-Beenden

Write-Host "=== 4. Szenario N3: Update scheitert (Programmdatei von anderem Prozess gesperrt)"
$app = Starte-App
$lock = Start-Process python -ArgumentList @("-c", "`"import time; f=open(r'$Ziel\FISI-Lernplattform.exe','rb'); time.sleep(150)`"") -PassThru -NoNewWindow
Start-Sleep 2
Update $app "0.56" -Schliessen "N3_datei_in_benutzung"
Bild "N3_meldung_nach_fehlschlag"
Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    Fenstertitel: $($_.MainWindowTitle)" }
$lock | Stop-Process -Force -ErrorAction SilentlyContinue
Alle-Beenden
Write-Host "    Lernstand-Datenbank noch da: $(Test-Path "$Daten\fisi_lernplattform.db") $((Get-ChildItem $Daten -Filter *.db | Select-Object -ExpandProperty Name) -join ', ')"

Write-Host "=== 5. Tests aus dem Quellcode unter Windows"
Push-Location fix
python test_update.py 2>&1 | Select-String "Ran |OK|FAIL|ERROR|skipped" | Write-Host
python test_beenden.py 2>&1 | Select-String "Ran |OK|FAIL|ERROR|skipped|\.\.\." | Write-Host
Pop-Location

Copy-Item "$Daten\fehler.log" "$Out\fehler_installiert.log" -ErrorAction SilentlyContinue
Stop-Transcript | Out-Null
