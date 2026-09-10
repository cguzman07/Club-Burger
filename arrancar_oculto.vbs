Set sh = CreateObject("Wscript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
script = root & "\inicio_silencioso.py"
pyw = sh.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Launcher\pyw.exe"
If fso.FileExists(pyw) Then
  sh.Run """" & pyw & """ -3 """ & script & """", 0, False
Else
  sh.Run "pyw -3 """ & script & """", 0, False
End If
