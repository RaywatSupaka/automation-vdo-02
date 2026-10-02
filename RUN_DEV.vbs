Option Explicit
Dim shell, files, root, python, entry, arguments
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
python = files.BuildPath(root, ".venv\Scripts\pythonw.exe")
entry = files.BuildPath(root, "desktop_entry.py")
If Not files.FileExists(python) Then
    MsgBox "Run SETUP.bat in the project folder first.", 16, "SmartFlow Next"
    WScript.Quit 1
End If
shell.CurrentDirectory = root
shell.Environment("Process")("SMARTFLOW_MODE") = "dev"
arguments = " desktop"
If WScript.Arguments.Count = 1 Then
    If WScript.Arguments(0) = "--desktop-smoke" Then arguments = arguments & " --desktop-smoke"
End If
shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & entry & Chr(34) & arguments, 0, False
