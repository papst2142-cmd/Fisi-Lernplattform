; ============================================================================
;  FISI Lernplattform - Inno Setup Installer-Skript
; ============================================================================
;  Baut aus der fertigen dist\FISI-Lernplattform.exe (siehe build_windows.bat)
;  einen richtigen Windows-Installer mit Start-Menue-Eintrag, optionaler
;  Desktop-Verknuepfung und sauberer Deinstallation ueber die
;  Windows-Einstellungen ("Apps & Features").
;
;  Bedienung:
;    1. Zuerst build_windows.bat ausfuehren, damit dist\FISI-Lernplattform.exe
;       aktuell ist.
;    2. Diese Datei (FISI-Lernplattform.iss) in Inno Setup oeffnen.
;    3. Oben auf "Compile" klicken (oder Strg+F9).
;    4. Das fertige Setup liegt danach in installer_output\.
;
;  WICHTIG: AppVersion unten muss zu APP_VERSION in app_gui.py passen und bei
;  jedem Update mit hochgezaehlt werden (siehe Projektvorgabe: Version bei
;  jedem Update um 1 erhoehen).
; ============================================================================

#define MyAppName "FISI Lernplattform"
#define MyAppVersion "0.19"
#define MyAppExeName "FISI-Lernplattform.exe"

[Setup]
AppId={{6B2E7B7B-6C1E-4E59-9C55-FISI-LERNPLATTFORM}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
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
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent
