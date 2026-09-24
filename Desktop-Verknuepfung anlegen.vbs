' ===========================================================================
'  Desktop-Verknuepfung anlegen.vbs
'  Legt auf dem Desktop eine Verknuepfung "FISI Lernplattform" an, die
'  direkt mit dem eigenen Programm-Icon (icon.ico) verknuepft ist und beim
'  Start automatisch den aktuellsten Code aus diesem Ordner verwendet.
'
'  Einfach EINMAL per Doppelklick ausfuehren. Nach einem Update von Claude
'  muss das nicht erneut gemacht werden - die Verknuepfung zeigt weiterhin
'  auf diesen Ordner.
' ===========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

skriptordner = FSO.GetParentFolderName(WScript.ScriptFullName)
zielSkript = skriptordner & "\FISI-Lernplattform starten.vbs"
iconDatei = skriptordner & "\icon.ico"
desktop = WshShell.SpecialFolders("Desktop")
linkPfad = desktop & "\FISI Lernplattform.lnk"

If Not FSO.FileExists(zielSkript) Then
    MsgBox "Die Datei 'FISI-Lernplattform starten.vbs' wurde in diesem " & _
           "Ordner nicht gefunden." & vbCrLf & vbCrLf & _
           "Bitte sicherstellen, dass dieses Skript im selben Ordner wie " & _
           "die Programmdateien liegt.", vbExclamation, "FISI Lernplattform"
    WScript.Quit
End If

Set link = WshShell.CreateShortcut(linkPfad)
link.TargetPath = zielSkript
link.WorkingDirectory = skriptordner
link.Description = "FISI Lernplattform starten"
If FSO.FileExists(iconDatei) Then
    link.IconLocation = iconDatei & ",0"
End If
link.Save

MsgBox "Fertig! Auf dem Desktop liegt jetzt die Verknuepfung " & _
       "'FISI Lernplattform' mit eigenem Icon.", vbInformation, "FISI Lernplattform"
