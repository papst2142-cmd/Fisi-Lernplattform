# ============================================================================
#  Fachinformatiker Lernplattform - automatischer Update-Test (ab 0.56)
# ============================================================================
#  Laeuft in "Installer bauen" (build.yml) auf einem Windows-Rechner von
#  GitHub, bevor ein Release veroeffentlicht wird:
#    1. Alte Version (letztes normales Release) aus dem Release installieren
#    2. Alte Version starten
#    3. Neuen Installer so starten, wie es die alte Version beim Update tut
#       (/WAITPID, /UPDATELOG, /FISIEXE, /LOG), Programm schliesst sich
#    4. Pruefen: Rueckgabewert 0, neue Version installiert, alter Prozess
#       weg, update.log ohne Fehler, neue Version startet und endet sauber
#  Ab 0.61 (Umbenennung, 19 Pruefungen): Version ueber den Registry-Schluessel
#  der AppId statt ueber den Anzeigenamen; nach dem Update genau eine
#  Verknuepfung im Startmenue und auf dem Desktop mit neuem Namen, kein alter
#  Startmenue-Ordner, genau ein Eintrag in "Apps & Features", Lernstand im
#  selben Ordner. Pruefungen 14 und 16 nur, wenn die alte Version noch den
#  alten Namen hat (kleiner als 0.61).
#  Ab 0.62 (21 Pruefungen): LICENSE.txt und THIRD_PARTY_NOTICES.txt im
#  Programmordner (20), Dateieigenschaft LegalCopyright der Exe (21).
#  Grenze: Auf dem GitHub-Rechner laeuft kein Schutzprogramm (Norton o.ae.).
#  Ein gruener Test beweist also nicht, dass das Update auf jedem PC klappt.
# ============================================================================
param(
  [Parameter(Mandatory = $true)] [string] $AltVersion,
  [Parameter(Mandatory = $true)] [string] $NeuVersion,
  [Parameter(Mandatory = $true)] [string] $NeuSetup
)
$ErrorActionPreference = "Continue"
$Out = Join-Path $PWD "update_test_protokolle"
New-Item -ItemType Directory -Force $Out | Out-Null
Start-Transcript -Path "$Out\konsole.txt" -Force | Out-Null

$Ziel = Join-Path $env:LOCALAPPDATA "Programs\FISI-Lernplattform"
$Exe = Join-Path $Ziel "FISI-Lernplattform.exe"
$Daten = Join-Path $env:APPDATA "FISI-Lernplattform"
$Ergebnisse = New-Object System.Collections.ArrayList

function Pruefung($name, [bool]$ok, $detail) {
  $null = $Ergebnisse.Add([pscustomobject]@{ Name = $name; Ok = $ok; Detail = "$detail" })
  Write-Host ("[{0}] {1}: {2}" -f $(if ($ok) { "OK" } else { "FEHLER" }), $name, $detail)
}
# Ab 0.61: Inno legt den Schluessel als AppId + "_is1" an - unabhaengig vom
# Anzeigenamen. Gefunden wird der Eintrag ueber den Namen (alt "FISI*", neu
# "Fachinformatiker*"); geprueft wird, dass der Schluessel (= AppId) nach dem
# Update derselbe ist wie bei der alten Version.
$Uninstall = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
function Eintraege {
  @(Get-ItemProperty "$Uninstall\*" -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like "FISI*" -or $_.DisplayName -like "Fachinformatiker*" })
}
function Version { (Eintraege | Select-Object -First 1).DisplayVersion }
# Verknuepfungen auf die Exe (Ziel gelesen, nicht nur der Dateiname)
$StartMenue = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell
function Verknuepfungen($ordner) {
  @(Get-ChildItem $ordner -Recurse -Filter *.lnk -ErrorAction SilentlyContinue |
    Where-Object { $Shell.CreateShortcut($_.FullName).TargetPath -ieq $Exe })
}
function Namen($liste) { ($liste | ForEach-Object { $_.FullName.Replace($StartMenue, "Startmenue").Replace($Desktop, "Desktop") }) -join ", " }
$AlterName = ([version]($AltVersion + ".0" * (3 - $AltVersion.Split(".").Count))) -lt [version]"0.61.0"
function Prozesse { @(Get-Process FISI-Lernplattform -ErrorAction SilentlyContinue) }
function Liste($titel) {
  Write-Host "--- Prozesse ($titel):"
  $p = Prozesse
  if ($p.Count) { $p | Format-Table Id, StartTime, Path -AutoSize | Out-String | Write-Host }
  else { Write-Host "    (kein FISI-Lernplattform-Prozess)" }
}

Write-Host "=== 1. Alte Version $AltVersion herunterladen und installieren"
$AltSetup = Join-Path $env:RUNNER_TEMP "FISI-Lernplattform-Setup-$AltVersion.exe"
$url = "https://github.com/papst2142-cmd/Fisi-Lernplattform/releases/download/v$AltVersion/FISI-Lernplattform-Setup-$AltVersion.exe"
Invoke-WebRequest $url -OutFile $AltSetup
$p = Start-Process $AltSetup -ArgumentList @("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=`"$Out\0_installation_alt.log`"") -PassThru
$null = $p.WaitForExit(300000)
Pruefung "Alte Version installiert" (($p.ExitCode -eq 0) -and ((Version) -eq $AltVersion)) "Rueckgabewert $($p.ExitCode), Version $(Version)"
Start-Sleep 5
# Der Installer startet das Programm nach einer stillen Installation selbst - beenden
# und unten gezielt neu starten
Prozesse | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# 14: Gegenprobe - die alte Version hat die alten Verknuepfungen angelegt
$sv = @(Verknuepfungen $StartMenue); $dv = @(Verknuepfungen $Desktop)
$AppKeyAlt = @(Eintraege | ForEach-Object { $_.PSChildName })
if ($AlterName) {
  Pruefung "Vorher: alte Verknuepfungen vorhanden" (($sv.Count -eq 1) -and ($sv[0].Name -eq "FISI Lernplattform.lnk") -and ($dv.Count -eq 1)) "$(Namen ($sv + $dv))"
} else {
  Pruefung "Vorher: alte Verknuepfungen (entfaellt, alte Version hat schon den neuen Namen)" $true "$(Namen ($sv + $dv))"
}

Write-Host "=== 2. Alte Version starten"
Start-Process $Exe | Out-Null
Start-Sleep 25
$alt = Prozesse | Sort-Object StartTime | Select-Object -Last 1
Pruefung "Alte Version laeuft" ($null -ne $alt) "Prozess $($alt.Id)"
Liste "alte Version laeuft"
$DB = Join-Path $Daten "fisi_lernplattform.db"
$dbVorher = Get-Item $DB -ErrorAction SilentlyContinue

Write-Host "=== 3. Update auf $NeuVersion wie aus dem Programm heraus"
$UpdDir = Join-Path $env:TEMP "FISI-Lernplattform-Update"
New-Item -ItemType Directory -Force $UpdDir | Out-Null
$Setup = Join-Path $UpdDir (Split-Path $NeuSetup -Leaf)
Copy-Item $NeuSetup $Setup -Force
Remove-Item "$Daten\update.log", "$Daten\update_installer.log", "$Daten\fehler.log" -ErrorAction SilentlyContinue
$t = Get-Date
$h = Start-Process python -ArgumentList @(".github\update-test\starte_update.py", "`"$Setup`"", $alt.Id, "`"$Exe`"", $NeuVersion) `
     -RedirectStandardOutput "$Out\starter.txt" -PassThru -NoNewWindow
Start-Sleep 3
Write-Host "    Programm schliesst sich (wie nach 'Jetzt aktualisieren': WM_CLOSE)"
$null = $alt.CloseMainWindow()
$fertig = $h.WaitForExit(300000)
if (-not $fertig) { $h.Kill() }
$dauer = ((Get-Date) - $t).TotalSeconds
Get-Content "$Out\starter.txt" | Write-Host
$rc = (Select-String -Path "$Out\starter.txt" -Pattern "^RUECKGABEWERT (-?\d+)").Matches.Groups[1].Value
Pruefung "Installer beendet" $fertig ("nach {0:n1} s" -f $dauer)
Pruefung "Rueckgabewert des Installers 0" ($rc -eq "0") "Rueckgabewert $rc"
Pruefung "Alter Prozess beendet" ($null -eq (Get-Process -Id $alt.Id -ErrorAction SilentlyContinue)) "Prozess $($alt.Id)"

Write-Host "=== 4. Neue Version startet (der Installer startet sie nach dem Update)"
Start-Sleep 25
Liste "nach dem Update"
$v = Version
Pruefung "Installierte Version" ($v -eq $NeuVersion) "erwartet $NeuVersion, gefunden $v"
# 15-19 (ab 0.61): Namen nach dem Update
$sn = @(Verknuepfungen $StartMenue)
Pruefung "Startmenue: genau eine Verknuepfung, neuer Name" (($sn.Count -eq 1) -and ($sn[0].Name -eq "Fachinformatiker Lernplattform.lnk") -and ($sn[0].Directory.Name -eq "Fachinformatiker Lernplattform")) "$($sn.Count): $(Namen $sn)"
$altOrdner = Join-Path $StartMenue "FISI Lernplattform"
if ($AlterName) {
  Pruefung "Alter Startmenue-Ordner entfernt" (-not (Test-Path $altOrdner)) $(if (Test-Path $altOrdner) { "noch da: " + ((Get-ChildItem $altOrdner).Name -join ", ") } else { "nicht mehr vorhanden" })
} else {
  Pruefung "Alter Startmenue-Ordner (entfaellt, alte Version hat schon den neuen Namen)" $true "-"
}
$dn = @(Verknuepfungen $Desktop)
Pruefung "Desktop: genau eine Verknuepfung, neuer Name" (($dn.Count -eq 1) -and ($dn[0].Name -eq "Fachinformatiker Lernplattform.lnk")) "$($dn.Count): $(Namen $dn)"
$en = @(Eintraege)
Pruefung "Apps und Features: genau ein Eintrag" (($en.Count -eq 1) -and ($en[0].DisplayName -like "Fachinformatiker Lernplattform*") -and ($en[0].Publisher -eq "Nico H") -and ($en[0].DisplayVersion -eq $NeuVersion) -and ($AppKeyAlt.Count -eq 1) -and ($en[0].PSChildName -eq $AppKeyAlt[0])) "$($en.Count): $(($en | ForEach-Object { '{0} / {1} / {2} / Schluessel {3}' -f $_.DisplayName, $_.Publisher, $_.DisplayVersion, $_.PSChildName }) -join '; ') (vorher $($AppKeyAlt -join ', '))"
$dbNachher = Get-Item $DB -ErrorAction SilentlyContinue
$neuOrdner = @(Get-ChildItem $env:APPDATA -Directory -Filter "Fachinformatiker*" -ErrorAction SilentlyContinue)
Pruefung "Lernstand im selben Ordner" (($null -ne $dbVorher) -and ($null -ne $dbNachher) -and ($dbNachher.LastWriteTime -ge $dbVorher.LastWriteTime) -and ($neuOrdner.Count -eq 0)) "$DB, vorher $(if ($dbVorher) { $dbVorher.Length } else { 'fehlt' }) Byte, nachher $(if ($dbNachher) { $dbNachher.Length } else { 'fehlt' }) Byte, neue Ordner: $($neuOrdner.Count)"
Copy-Item "$Daten\update.log" "$Out\update.log" -ErrorAction SilentlyContinue
Copy-Item "$Daten\update_installer.log" "$Out\update_installer.log" -ErrorAction SilentlyContinue
$log = Get-Content "$Daten\update.log" -Encoding utf8 -ErrorAction SilentlyContinue
$log | Write-Host
$inst = Get-Content "$Out\update_installer.log" -ErrorAction SilentlyContinue
Pruefung "Installation vollstaendig" (($log -match "Installation erfolgreich, Version $([regex]::Escape($NeuVersion))").Count -gt 0) "Zeile 'Installation erfolgreich' in update.log"
Pruefung "Kein Zurueckrollen" (($inst -match "Rolling back changes").Count -eq 0) "Installer-Protokoll"
Pruefung "update.log ohne Fehler" ((($log -match "NICHT abgeschlossen|fehlgeschlagen|nicht starten|unvollst").Count) -eq 0) "keine Fehlerzeile"
Pruefung "Neue Version meldet Abschluss" (($log -match "abgeschlossen, Programm l.uft als").Count -gt 0) "Zeile von finish_pending_update"
$neu = @(Prozesse)
Pruefung "Genau ein Programm laeuft (die neue Version)" ($neu.Count -eq 1) "$($neu.Count) Prozess(e)"

Write-Host "=== 5. Neue Version schliessen: bleibt ein Prozess uebrig?"
foreach ($n in $neu) { $null = $n.CloseMainWindow() }
$ende = $true
foreach ($n in $neu) { if (-not $n.WaitForExit(20000)) { $ende = $false } }
Start-Sleep 2
Liste "nach dem Schliessen"
Pruefung "Kein Prozess bleibt uebrig" (((Prozesse).Count -eq 0) -and $ende) "$((Prozesse).Count) Prozess(e) nach 20 s"
$fehler = ""
if (Test-Path "$Daten\fehler.log") { $fehler = (Get-Content "$Daten\fehler.log" -Raw -Encoding utf8); Copy-Item "$Daten\fehler.log" "$Out\fehler.log" }
Pruefung "fehler.log leer" ([string]::IsNullOrWhiteSpace($fehler)) $(if ($fehler) { "Eintraege vorhanden" } else { "keine Eintraege" })
# 20-21 (ab 0.62): Lizenzdateien im Programmordner, Copyright der Exe
$lic = Get-Item (Join-Path $Ziel "LICENSE.txt") -ErrorAction SilentlyContinue
$tpn = Get-Item (Join-Path $Ziel "THIRD_PARTY_NOTICES.txt") -ErrorAction SilentlyContinue
Pruefung "Lizenzdateien im Programmordner" (($null -ne $lic) -and ($null -ne $tpn) -and ($lic.Length -gt 0) -and ($tpn.Length -gt 0)) "LICENSE.txt $(if ($lic) { $lic.Length } else { 'fehlt' }) Byte, THIRD_PARTY_NOTICES.txt $(if ($tpn) { $tpn.Length } else { 'fehlt' }) Byte"
$copy = (Get-Item $Exe -ErrorAction SilentlyContinue).VersionInfo.LegalCopyright
Pruefung "Copyright der Exe" ($copy -ceq "Copyright (c) 2026 Nico H") "LegalCopyright '$copy'"
Prozesse | Stop-Process -Force -ErrorAction SilentlyContinue

# Zusammenfassung fuer die Seite des Laufs und das Protokoll
$ok = -not ($Ergebnisse | Where-Object { -not $_.Ok })
$md = @("## Update-Test $AltVersion -> ${NeuVersion}: $(if ($ok) { 'bestanden' } else { 'FEHLGESCHLAGEN' })", "",
        "| Pruefung | Ergebnis | Angabe |", "|---|---|---|")
foreach ($e in $Ergebnisse) { $md += "| $($e.Name) | $(if ($e.Ok) { 'OK' } else { '**FEHLER**' }) | $($e.Detail) |" }
$md += ""
$md += "Grenze: Auf dem GitHub-Rechner (Windows Server, $([Environment]::OSVersion.VersionString)) laeuft kein Schutzprogramm. Der Test zeigt, dass der Update-Ablauf selbst funktioniert, nicht, dass er auf jedem PC funktioniert."
$md | Set-Content "$Out\ergebnis.md" -Encoding utf8
if ($env:GITHUB_STEP_SUMMARY) { $md | Add-Content $env:GITHUB_STEP_SUMMARY -Encoding utf8 }
Stop-Transcript | Out-Null
if (-not $ok) { exit 1 }
exit 0
