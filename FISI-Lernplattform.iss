; ============================================================================
;  FISI Lernplattform - Inno Setup Installer-Skript
; ============================================================================
;  Baut aus dem fertigen Programmordner dist\FISI-Lernplattform\ einen
;  richtigen Windows-Installer mit Start-Menue-Eintrag, optionaler
;  Desktop-Verknuepfung und sauberer Deinstallation ueber die
;  Windows-Einstellungen ("Apps & Features").
;
;  Normalerweise wird dieses Skript automatisch von build.py aufgerufen
;  (lokal oder per GitHub Actions). build.py uebergibt dabei die Version aus
;  APP_VERSION in app_gui.py. Der Ersatzwert unten wird mit
;  "python build.py --setze-version <Version>" automatisch mitgepflegt.
;
;  Manuell: zuerst "python build.py --nur-app" ausfuehren, dann diese Datei in
;  Inno Setup oeffnen und auf "Compile" klicken. Das fertige Setup liegt
;  danach in installer_output\.
; ============================================================================

#define MyAppName "FISI Lernplattform"
#ifndef MyAppVersion
  #define MyAppVersion "0.55.1"
#endif
#define MyAppExeName "FISI-Lernplattform.exe"

[Setup]
AppId={{6B2E7B7B-6C1E-4E59-9C55-FISI-LERNPLATTFORM}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}
AppPublisher=FISI Lernplattform Projekt
DefaultDirName={localappdata}\Programs\FISI-Lernplattform
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer_output
OutputBaseFilename=FISI-Lernplattform-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Installation nur fuer den aktuellen Benutzer, keine Admin-Rechte noetig.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "dist\FISI-Lernplattform\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
; Nach einem Update aus dem Programm heraus (stille Installation) automatisch neu starten
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[Code]
// ============================================================================
//  Ab 0.55.1: Update aus dem Programm heraus absichern
// ============================================================================
//  Das Programm startet den Installer mit
//    /WAITPID=<Prozessnummer>  /UPDATELOG=<Datenordner\update.log>
//    /FISIEXE=<Pfad der laufenden FISI-Lernplattform.exe>  /LOG=<...>
//  1. Bevor irgendeine Datei ersetzt wird, wartet der Installer, bis das
//     Programm wirklich beendet ist (hoechstens WAIT_SECONDS). Laeuft es
//     dann noch, wird es beendet - der Lernstand ist zu diesem Zeitpunkt
//     schon gesichert. Vorher lief der Installer sofort los; blieb das
//     Programm haengen, waren seine Dateien in Benutzung und der Installer
//     machte am Ende alles rueckgaengig.
//  2. Jeder Schritt und das Ergebnis stehen in update.log.
//  3. Scheitert die Installation, startet die alte Version wieder und
//     meldet den Fehlschlag (fisi_update.finish_pending_update).
//  Ohne /WAITPID (Installer per Doppelklick) aendert sich nichts.

const
  SYNCHRONIZE = $00100000;
  PROCESS_TERMINATE = $0001;
  WAIT_OBJECT_0 = 0;
  WAIT_SECONDS = 30;

var
  InstallDone: Boolean;

function OpenProcess(dwDesiredAccess: DWORD; bInheritHandle: BOOL; dwProcessId: DWORD): THandle;
  external 'OpenProcess@kernel32.dll stdcall';
function WaitForSingleObject(hHandle: THandle; dwMilliseconds: DWORD): DWORD;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function TerminateProcess(hProcess: THandle; uExitCode: UINT): BOOL;
  external 'TerminateProcess@kernel32.dll stdcall';
function CloseHandle(hObject: THandle): BOOL;
  external 'CloseHandle@kernel32.dll stdcall';

function FromApp(): Boolean;
begin
  Result := ExpandConstant('{param:WAITPID|}') <> '';
end;

procedure UpdateLog(Text: String);
var
  Path: String;
  Lines: TArrayOfString;
begin
  Log(Text);
  Path := ExpandConstant('{param:UPDATELOG|}');
  if Path = '' then
    exit;
  SetArrayLength(Lines, 1);
  Lines[0] := GetDateTimeString('yyyy/mm/dd hh:nn:ss', '-', ':') +
    ' | Installer {#MyAppVersion} | ' + Text;
  SaveStringsToUTF8FileWithoutBOM(Path, Lines, True);
end;

function InitializeSetup(): Boolean;
var
  Pid: Integer;
  Process: THandle;
begin
  Result := True;
  InstallDone := False;
  if not FromApp() then
    exit;
  Pid := StrToIntDef(ExpandConstant('{param:WAITPID|0}'), 0);
  UpdateLog('gestartet, wartet auf das Ende des Programms (Prozess ' + IntToStr(Pid) + ')');
  Process := OpenProcess(SYNCHRONIZE or PROCESS_TERMINATE, False, Pid);
  if Process = 0 then
  begin
    UpdateLog('Programm ist bereits beendet');
    exit;
  end;
  if WaitForSingleObject(Process, WAIT_SECONDS * 1000) = WAIT_OBJECT_0 then
    UpdateLog('Programm hat sich beendet')
  else
  begin
    UpdateLog('Programm l' + #$00E4 + 'uft nach ' + IntToStr(WAIT_SECONDS) +
      ' s noch und wird beendet (Lernstand ist schon gesichert)');
    TerminateProcess(Process, 1);
    if WaitForSingleObject(Process, 10000) = WAIT_OBJECT_0 then
      UpdateLog('Programm beendet')
    else
      UpdateLog('Programm lie' + #$00DF + ' sich nicht beenden');
  end;
  CloseHandle(Process);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if not FromApp() then
    exit;
  if CurStep = ssInstall then
    UpdateLog('ersetzt die Programmdateien in ' + ExpandConstant('{app}'))
  else if CurStep = ssPostInstall then
  begin
    InstallDone := True;
    UpdateLog('Installation erfolgreich, Version {#MyAppVersion} ist installiert');
  end;
end;

procedure DeinitializeSetup();
var
  Exe: String;
  Code: Integer;
begin
  if (not FromApp()) or InstallDone then
    exit;
  UpdateLog('Installation NICHT abgeschlossen, die bisherige Version bleibt unver' + #$00E4 + 'ndert. ' +
    'Details: ' + ExpandConstant('{param:LOG|update_installer.log}'));
  Exe := ExpandConstant('{param:FISIEXE|}');
  if (Exe <> '') and FileExists(Exe) then
  begin
    UpdateLog('startet die bisherige Version wieder');
    Exec(Exe, '', '', SW_SHOWNORMAL, ewNoWait, Code);
  end;
end;
