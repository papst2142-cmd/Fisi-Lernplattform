# ============================================================================
#  NVDA automatisch pruefen (Erkundung, nur Zweig proto-screenreader)
# ============================================================================
#  1. NVDA-Starter von NV Access holen (Update-Auskunft api.nvaccess.org,
#     sonst download.nvaccess.org), SHA1/SHA256 und Signatur protokollieren
#  2. Tragbare Kopie anlegen (--create-portable-silent)
#  3. NVDA ohne Ton starten: Sprachausgabe "silence", Protokollstufe 12
#     (Ein-/Ausgabe) -> jede Sprachausgabe steht als "Speaking [...]" im Log
#  4. Prototyp starten, UIA-Baum MIT laufendem NVDA messen (Frage 3)
#  5. Tasten wie in NVDA-Testanleitung 4.1 und 4.2 senden, nach jedem
#     Schritt mitschreiben, was NVDA gesagt hat (Frage 2)
#  6. Gegenprobe: Editor (Notepad) und reines Flutter-Programm (Frage 4)
#
#  Aufruf (Windows PowerShell 5.1):
#    powershell -File nvda_lauf.ps1 -Prototyp <exe> -Gegenprobe <exe> -Aus <ordner>
#  Datei bewusst nur ASCII (Windows PowerShell liest Skripte ohne BOM als ANSI).
# ============================================================================
param(
    [Parameter(Mandatory = $true)][string]$Prototyp,
    [string]$Gegenprobe = "",
    [string]$GegenprobeTitel = "gegenprobe",
    [Parameter(Mandatory = $true)][string]$Aus
)
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
New-Item -ItemType Directory -Force $Aus | Out-Null
$Aus = (Resolve-Path $Aus).Path
$HIER = Split-Path -Parent $MyInvocation.MyCommand.Path
$UIA_BAUM = Join-Path (Split-Path -Parent $HIER) "uia_baum.ps1"
$PROTO_TITEL = "FISI Screenreader-Prototyp"

function Log([string]$t) {
    Write-Output $t
    Add-Content -Path (Join-Path $Aus "ablauf.txt") -Value $t -Encoding UTF8
}

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Threading;
using System.Runtime.InteropServices;
public static class H {
    [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool SystemParametersInfo(uint a, uint b, ref bool c, uint d);
    public static void Runter(byte vk, bool ext) { keybd_event(vk, 0, ext ? 1u : 0u, UIntPtr.Zero); Thread.Sleep(40); }
    public static void Hoch(byte vk, bool ext) { keybd_event(vk, 0, (ext ? 1u : 0u) | 2u, UIntPtr.Zero); Thread.Sleep(40); }
    public static void Taste(byte vk) { Runter(vk, false); Hoch(vk, false); }
    public static string Vorne() {
        StringBuilder s = new StringBuilder(512);
        GetWindowText(GetForegroundWindow(), s, 512);
        return s.ToString();
    }
    public static bool Screenreader() { bool b = false; SystemParametersInfo(0x0046, 0, ref b, 0); return b; }
    // Fenster nach vorne holen: eigener (unbenutzter) Tastendruck F24 hebt die
    // Vordergrund-Sperre von Windows auf, ohne Menues zu oeffnen
    public static bool Hole(IntPtr h) {
        ShowWindow(h, 9);
        Runter(0x87, false); Hoch(0x87, false);
        return SetForegroundWindow(h);
    }
}
"@

# ---------------------------------------------------------------------------
# 1. NVDA holen
# ---------------------------------------------------------------------------
Log "== 1. NVDA holen"
$starter = Join-Path $env:RUNNER_TEMP "nvda_starter.exe"
$url = $null; $sha1Soll = $null
try {
    $q = "https://api.nvaccess.org/nvdaUpdateCheck?autoCheck=False&allowUsageStats=False&version=2025.1&versionType=stable&osVersion=10.0.26100%20workstation&x64=True&osArchitecture=AMD64"
    $r = Invoke-WebRequest -UseBasicParsing -Uri $q -TimeoutSec 60
    $txt = if ($r.Content -is [byte[]]) { [System.Text.Encoding]::UTF8.GetString($r.Content) } else { [string]$r.Content }
    Log "Update-Auskunft von api.nvaccess.org (gleiche Quelle wie NVDAs eigene Update-Pruefung):"
    foreach ($z in $txt -split "`n") {
        $z = $z.Trim()
        if ($z) { Log "   $z" }
        if ($z -like "launcherUrl: *") { $url = ($z.Substring(13) -split " ")[0] }
        if ($z -like "launcherHash: *") { $sha1Soll = $z.Substring(14).Trim().ToLower() }
    }
} catch { Log "Update-Auskunft fehlgeschlagen: $_" }
if (-not $url) { $url = "https://download.nvaccess.org/releases/2026.2/nvda_2026.2.exe"; Log "Ersatzadresse: $url" }
try {
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $starter -TimeoutSec 600
} catch { Log "DOWNLOAD FEHLGESCHLAGEN: $_"; exit 0 }
$sha1 = (Get-FileHash $starter -Algorithm SHA1).Hash.ToLower()
$sha256 = (Get-FileHash $starter -Algorithm SHA256).Hash.ToLower()
$sig = Get-AuthenticodeSignature $starter
Log "Datei:   $url"
Log "Groesse: $((Get-Item $starter).Length) Bytes"
Log "SHA1:    $sha1  (Soll laut NV Access: $sha1Soll)"
Log "SHA256:  $sha256"
Log "Signatur: $($sig.Status) / $($sig.SignerCertificate.Subject)"
Log "Dateiversion: $((Get-Item $starter).VersionInfo.ProductVersion)"
if ($sha1Soll -and $sha1 -ne $sha1Soll) { Log "PRUEFSUMME PASST NICHT - Abbruch"; exit 0 }
if ($sig.Status -ne "Valid") { Log "SIGNATUR NICHT GUELTIG - Abbruch"; exit 0 }

# ---------------------------------------------------------------------------
# 2. Tragbare Kopie
# ---------------------------------------------------------------------------
Log "== 2. Tragbare Kopie anlegen"
$port = Join-Path $env:RUNNER_TEMP "nvda_portabel"
$p = Start-Process $starter -ArgumentList "--create-portable-silent", "--portable-path=$port" -PassThru
if (-not $p.WaitForExit(300000)) { Log "Anlegen dauert ueber 5 Minuten - Abbruch"; exit 0 }
Log "Starter beendet mit Code $($p.ExitCode)"
$nvda = Join-Path $port "nvda.exe"
for ($i = 0; $i -lt 60 -and -not (Test-Path $nvda); $i++) { Start-Sleep -Seconds 2 }
if (-not (Test-Path $nvda)) { Log "nvda.exe NICHT ENTSTANDEN - Abbruch"; Get-ChildItem $port -ErrorAction SilentlyContinue | ForEach-Object { Log "   $($_.Name)" }; exit 0 }
Log "nvda.exe vorhanden: $nvda"

# ---------------------------------------------------------------------------
# 3. NVDA ohne Ton starten
# ---------------------------------------------------------------------------
Log "== 3. NVDA starten (Sprachausgabe 'silence', Protokollstufe 12, Sprache Deutsch)"
$cfg = Join-Path $env:RUNNER_TEMP "nvda_konfig"
New-Item -ItemType Directory -Force $cfg | Out-Null
@"
[general]
language = de
showWelcomeDialogAtStartup = False
playStartAndExitSounds = False
askToExit = False
saveConfigurationOnExit = False
[speech]
synth = silence
[update]
autoCheck = False
startupNotification = False
askedAllowUsageStats = True
allowUsageStats = False
"@ | Set-Content -Path (Join-Path $cfg "nvda.ini") -Encoding ASCII
$nvdaLog = Join-Path $Aus "nvda.log"
Log "Screenreader-Kennzeichen vor NVDA-Start: $([H]::Screenreader())"
$np = Start-Process $nvda -ArgumentList "-m", "--lang=de", "--log-level=12", "-f", "`"$nvdaLog`"", "-c", "`"$cfg`"", "--disable-addons" -PassThru
Start-Sleep -Seconds 15
$k = Start-Process $nvda -ArgumentList "-k" -PassThru -Wait
Log "NVDA laeuft (nvda -k, 0 = ja): $($k.ExitCode)"
Log "Screenreader-Kennzeichen mit NVDA: $([H]::Screenreader())"
if (-not (Test-Path $nvdaLog)) { Log "KEIN NVDA-PROTOKOLL ENTSTANDEN" }

# ---------------------------------------------------------------------------
# Hilfen: Protokoll lesen, Tasten senden, Fokus abfragen
# ---------------------------------------------------------------------------
function Logstand {
    if (-not (Test-Path $nvdaLog)) { return 0 }
    return (Get-Item $nvdaLog).Length
}
function Gesprochen-seit([long]$ab) {
    if (-not (Test-Path $nvdaLog)) { return @() }
    $fs = [System.IO.File]::Open($nvdaLog, "Open", "Read", "ReadWrite")
    try {
        $fs.Seek($ab, "Begin") | Out-Null
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
        $text = $sr.ReadToEnd()
    } finally { $fs.Close() }
    $raus = @()
    foreach ($z in $text -split "`r?`n") {
        if ($z -like "Speaking *") {
            # Steuerbefehle (Sprache, Pause, Abbruch) entfernen, nur Woerter behalten
            $s = $z.Substring(9) -replace "\w+Command\([^)]*\)", "" -replace "CancellableSpeech \([^)]*\)", "" -replace "CallbackCommand[^,\]]*", ""
            $teile = [regex]::Matches($s, "'((?:[^'\\]|\\.)*)'|`"((?:[^`"\\]|\\.)*)`"") | ForEach-Object { if ($_.Groups[1].Success) { $_.Groups[1].Value } else { $_.Groups[2].Value } }
            $raus += ("SPRICHT: " + (($teile | Where-Object { $_.Trim() }) -join " | "))
        }
    }
    return $raus
}
function Fokus {
    try {
        $f = [System.Windows.Automation.AutomationElement]::FocusedElement
        return "$($f.Current.ControlType.ProgrammaticName -replace 'ControlType\.', '') '$($f.Current.Name)'"
    } catch { return "(kein Fokus lesbar)" }
}
$VK = @{ "Tab" = 0x09; "Enter" = 0x0D; "Leertaste" = 0x20; "Pfeil runter" = 0x28; "Pfeil hoch" = 0x26; "Escape" = 0x1B }
function Sende([string]$taste) {
    switch ($taste) {
        "Umschalt+Tab" { [H]::Runter(0x10, $false); [H]::Taste(0x09); [H]::Hoch(0x10, $false) }
        # NVDA-Taste = Einfg (erweiterte Taste); NVDA wertet eingespeiste Tasten aus (handleInjectedKeys)
        "NVDA+Tab" { [H]::Runter(0x2D, $true); [H]::Taste(0x09); [H]::Hoch(0x2D, $true) }
        default { [H]::Taste([byte]$VK[$taste]) }
    }
}
$script:Protokoll = @()
function Schritt([string]$nr, [string]$taste, [int]$warten = 1500) {
    $ab = Logstand
    if ($taste) { Sende $taste }
    Start-Sleep -Milliseconds $warten
    $sp = Gesprochen-seit $ab
    $zeile = "[$nr] Taste: $(if ($taste) { $taste } else { '-' }) | Fokus (UIA): $(Fokus) | Vordergrund: $([H]::Vorne())"
    Log $zeile
    if ($sp.Count -eq 0) { Log "      SPRICHT: (nichts)" } else { foreach ($s in $sp) { Log "      $s" } }
}
function Starte-Fenster([string]$exe, [string]$titel, [string]$arbeitsordner) {
    $ab = Logstand
    $pr = if ($arbeitsordner) { Start-Process $exe -WorkingDirectory $arbeitsordner -PassThru } else { Start-Process $exe -PassThru }
    $h = [IntPtr]::Zero
    for ($i = 0; $i -lt 120; $i++) {
        $pr.Refresh()
        $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $titel)
        $w = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
        if ($w) { $h = [IntPtr]$w.Current.NativeWindowHandle; break }
        Start-Sleep -Seconds 1
    }
    Log "Fenster '$titel' nach $i s: $(if ($h -ne [IntPtr]::Zero) { 'gefunden' } else { 'NICHT gefunden' })"
    return @{ Prozess = $pr; Handle = $h; Ab = $ab }
}

# ---------------------------------------------------------------------------
# 4. Prototyp starten, UIA-Baum mit laufendem NVDA (Frage 3)
# ---------------------------------------------------------------------------
Log "== 4. Prototyp starten"
$f = Starte-Fenster $Prototyp $PROTO_TITEL (Split-Path -Parent $Prototyp)
if ($f.Handle -ne [IntPtr]::Zero) {
    # Python entpackt beim ersten Start; Inhalt abwarten
    Start-Sleep -Seconds 20
    Log "Nach vorne geholt: $([H]::Hole($f.Handle)) / Vordergrund: $([H]::Vorne())"
    Start-Sleep -Seconds 3
    $sp = Gesprochen-seit $f.Ab
    Log "[1] Programmstart | Fokus (UIA): $(Fokus)"
    if ($sp.Count -eq 0) { Log "      SPRICHT: (nichts)" } else { foreach ($s in $sp) { Log "      $s" } }

    Log "== UIA-Baum des Prototyps MIT laufendem NVDA"
    powershell -NoProfile -File $UIA_BAUM -Fenster $PROTO_TITEL -Warten 10 | Tee-Object -FilePath (Join-Path $Aus "uia_prototyp_mit_nvda.txt") | ForEach-Object { Write-Output "   $_" }
    [H]::Hole($f.Handle) | Out-Null
    Start-Sleep -Seconds 2

    # -----------------------------------------------------------------------
    # 5. Tasten nach NVDA-Testanleitung 4.1 und 4.2
    # -----------------------------------------------------------------------
    Log "== 5. Abschnitt 4.1 (Tab-Reihenfolge Optionen)"
    for ($n = 2; $n -le 13; $n++) { Schritt "$n" "Tab" }
    Schritt "14" "Umschalt+Tab"
    Log "== 5. Abschnitt 4.2 (Auf- und Zuklappen)"
    Schritt "15a" "Umschalt+Tab"
    Schritt "15b" "Umschalt+Tab"
    Schritt "15c" "Umschalt+Tab"
    Schritt "15" "Enter" 2500
    Schritt "16" "NVDA+Tab"
    Schritt "17" "Tab"
    Schritt "18" "Pfeil runter"
    Schritt "19" "Tab"
    Schritt "20" "Leertaste" 2500
    Schritt "21a" "Tab"
    Schritt "21b" "Tab"
    Schritt "21c" "Tab"
    Schritt "22" "Enter" 2500
    Schritt "23a" "Umschalt+Tab"
    Schritt "23b" "Umschalt+Tab"
    Schritt "23c" "Umschalt+Tab"
    Schritt "23" "Enter" 2500
    Schritt "24" "Tab"
    Schritt "25a" "Umschalt+Tab"
    Schritt "25b" "Umschalt+Tab"
    Schritt "25c" "Umschalt+Tab"
    Schritt "25" "Enter" 2500
    Schritt "26a" "Umschalt+Tab"
    Schritt "26b" "Umschalt+Tab"
    Schritt "26c" "Umschalt+Tab"
    Schritt "26d" "Umschalt+Tab"
    Schritt "26" "Enter" 2500
    Stop-Process -Id $f.Prozess.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# ---------------------------------------------------------------------------
# 6. Gegenprobe (Frage 4)
# ---------------------------------------------------------------------------
Log "== 6a. Gegenprobe Editor (Notepad)"
$ab = Logstand
$np2 = Start-Process notepad.exe -PassThru
Start-Sleep -Seconds 4
$np2.Refresh()
if ($np2.MainWindowHandle -ne [IntPtr]::Zero) { [H]::Hole($np2.MainWindowHandle) | Out-Null }
Start-Sleep -Seconds 2
$sp = Gesprochen-seit $ab
Log "[G1] Editor gestartet | Fokus (UIA): $(Fokus) | Vordergrund: $([H]::Vorne())"
if ($sp.Count -eq 0) { Log "      SPRICHT: (nichts)" } else { foreach ($s in $sp) { Log "      $s" } }
Schritt "G2" "Enter"
Get-Process notepad -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

if ($Gegenprobe -and (Test-Path $Gegenprobe)) {
    Log "== 6b. Gegenprobe reines Flutter-Programm (Zaehler-Vorlage)"
    $g = Starte-Fenster $Gegenprobe $GegenprobeTitel (Split-Path -Parent $Gegenprobe)
    if ($g.Handle -ne [IntPtr]::Zero) {
        Start-Sleep -Seconds 5
        Log "Nach vorne geholt: $([H]::Hole($g.Handle)) / Vordergrund: $([H]::Vorne())"
        Start-Sleep -Seconds 2
        $sp = Gesprochen-seit $g.Ab
        Log "[F1] Flutter-Programm gestartet | Fokus (UIA): $(Fokus)"
        if ($sp.Count -eq 0) { Log "      SPRICHT: (nichts)" } else { foreach ($s in $sp) { Log "      $s" } }
        Log "== UIA-Baum Flutter-Gegenprobe MIT laufendem NVDA"
        powershell -NoProfile -File $UIA_BAUM -Fenster $GegenprobeTitel -Warten 10 | Tee-Object -FilePath (Join-Path $Aus "uia_flutter_gegenprobe_mit_nvda.txt") | ForEach-Object { Write-Output "   $_" }
        [H]::Hole($g.Handle) | Out-Null
        Start-Sleep -Seconds 1
        Schritt "F2" "Tab"
        Schritt "F3" "Enter"
        Schritt "F4" "NVDA+Tab"
        Stop-Process -Id $g.Prozess.Id -Force -ErrorAction SilentlyContinue
    }
} else { Log "== 6b. Flutter-Gegenprobe nicht vorhanden ($Gegenprobe)" }

# ---------------------------------------------------------------------------
# Ende: NVDA beenden, Protokoll auswerten
# ---------------------------------------------------------------------------
Start-Process $nvda -ArgumentList "-q" -Wait
Start-Sleep -Seconds 3
Log "== NVDA-Protokoll: Fehler und Warnungen"
if (Test-Path $nvdaLog) {
    $alles = Get-Content $nvdaLog -Encoding UTF8
    Log "Zeilen im Protokoll: $($alles.Count), davon 'Speaking': $(($alles | Where-Object { $_ -like 'Speaking *' }).Count)"
    $alles | Select-Object -First 25 | ForEach-Object { Log "   $_" }
    $alles | Select-String -Pattern "^(ERROR|WARNING|CRITICAL)" -Context 0, 3 | Select-Object -First 15 | ForEach-Object { Log "   $($_.ToString())" }
}
Log "== Ende"
