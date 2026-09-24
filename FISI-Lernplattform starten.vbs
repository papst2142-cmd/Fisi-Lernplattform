' ===========================================================================
'  FISI-Lernplattform starten.vbs
'  Startet die Lernplattform direkt aus dem Quellcode - OHNE exe-Build.
'  Zeigt kein Konsolenfenster an (nutzt pythonw statt python).
'
'  Diese Datei kann per Rechtsklick -> "Senden an" -> "Desktop (Verknuepfung
'  erstellen)" auf den Desktop gelegt werden. Ein Doppelklick startet danach
'  immer die aktuellste Version aus diesem Ordner.
' ===========================================================================

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Ordner ermitteln, in dem dieses Skript liegt (funktioniert auch, wenn der
' gesamte Programmordner spaeter verschoben oder umbenannt wird).
skriptordner = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = skriptordner

' Zuerst pythonw (kein Konsolenfenster) versuchen, sonst mit python starten.
On Error Resume Next
WshShell.Run "pythonw start.py", 0, False
If Err.Number <> 0 Then
    Err.Clear
    WshShell.Run "python start.py", 0, False
    If Err.Number <> 0 Then
        MsgBox "Python wurde nicht gefunden." & vbCrLf & vbCrLf & _
               "Bitte pruefen, ob Python installiert ist und beim" & vbCrLf & _
               "Installieren ""Add Python to PATH"" angehakt wurde.", _
               vbExclamation, "FISI Lernplattform"
    End If
End If
On Error Goto 0
