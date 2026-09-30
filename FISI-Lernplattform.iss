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
  #define MyAppVersion "0.43"
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
