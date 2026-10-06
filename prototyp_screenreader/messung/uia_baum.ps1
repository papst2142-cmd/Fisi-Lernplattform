# UI-Automation-Baum eines Fensters ausgeben (das, was NVDA unter Windows sieht).
# Aufruf: powershell -File uia_baum.ps1 -Fenster "FISI Screenreader-Prototyp" [-Klick "Farben, eingeklappt"]
param(
    [Parameter(Mandatory = $true)][string]$Fenster,
    [string]$Klick = "",
    [int]$Warten = 40
)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]

function Finde-Fenster {
    for ($i = 0; $i -lt $Warten; $i++) {
        $cond = New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $Fenster)
        $w = $AE::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
        if ($w) { return $w }
        Start-Sleep -Seconds 1
    }
    return $null
}

function Zustand($el) {
    $teile = @()
    try {
        $p = $el.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
        $teile += "Klappzustand=" + $p.Current.ExpandCollapseState
    } catch {}
    try {
        $p = $el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $teile += "Schalter=" + $p.Current.ToggleState
    } catch {}
    try {
        $p = $el.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
        $teile += "ausgewaehlt=" + $p.Current.IsSelected
    } catch {}
    if ($el.Current.IsKeyboardFocusable) { $teile += "Tab-Ziel" }
    if ($el.Current.HasKeyboardFocus) { $teile += "FOKUS" }
    return ($teile -join ", ")
}

$script:Zaehler = @{ alle = 0; leer = 0; benannt = 0; tab = 0 }

function Baum($el, $tiefe) {
    if ($tiefe -gt 40) { return }
    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $kind = $walker.GetFirstChild($el)
    while ($kind) {
        $typ = $kind.Current.ControlType.ProgrammaticName -replace "ControlType\.", ""
        $name = $kind.Current.Name -replace "`r?`n", " / "
        if ($name.Length -gt 90) { $name = $name.Substring(0, 90) + "..." }
        $hilfe = $kind.Current.LocalizedControlType
        $z = Zustand $kind
        $script:Zaehler.alle++
        if ($name) { $script:Zaehler.benannt++ }
        if ($kind.Current.IsKeyboardFocusable) { $script:Zaehler.tab++ }
        # Leere Flaechen ohne Namen und Zustand nur zaehlen, nicht ausgeben
        if (-not $name -and -not $z -and $typ -eq "Pane") { $script:Zaehler.leer++ }
        else { Write-Output ("{0}[{1}] '{2}' ({3}) {{{4}}}" -f ("  " * $tiefe), $typ, $name, $hilfe, $z) }
        Baum $kind ($tiefe + 1)
        $kind = $walker.GetNextSibling($kind)
    }
}

function Finde-Name($el, $name) {
    $cond = New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty, $name)
    return $el.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
}

$w = Finde-Fenster
if (-not $w) { Write-Output "FENSTER NICHT GEFUNDEN: $Fenster"; exit 0 }
# Flutter baut den Baum erst auf, wenn jemand fragt, und ein gebautes
# Flet-Programm entpackt beim ersten Start noch Python: bis zu 120 s warten,
# bis mehr als das Fenster selbst im Baum steht
$alle = [System.Windows.Automation.Condition]::TrueCondition
for ($i = 0; $i -lt 40; $i++) {
    $n = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants, $alle).Count
    if ($n -gt 3) { break }
    Start-Sleep -Seconds 3
}
Write-Output "== Elemente im Baum nach $(3 * $i) s Warten: $n"
Start-Sleep -Seconds 3
Write-Output "== Fenster '$Fenster'"
Baum $w 0
Write-Output ("== Zusammenfassung: {0} Elemente, davon {1} mit Namen, {2} Tab-Ziele, {3} leere Flaechen nicht ausgegeben" -f $script:Zaehler.alle, $script:Zaehler.benannt, $script:Zaehler.tab, $script:Zaehler.leer)

if ($Klick) {
    $ziel = Finde-Name $w $Klick
    if (-not $ziel) { Write-Output "== '$Klick' nicht gefunden"; exit 0 }
    Write-Output "== '$Klick' vorher: $(Zustand $ziel)"
    try {
        $ziel.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Write-Output "== ausgeloest (Invoke)"
    } catch { Write-Output "== kein Invoke moeglich: $_" }
    Start-Sleep -Seconds 3
    Write-Output "== Baum nach dem Klick"
    $script:Zaehler = @{ alle = 0; leer = 0; benannt = 0; tab = 0 }
    Baum $w 0
}
