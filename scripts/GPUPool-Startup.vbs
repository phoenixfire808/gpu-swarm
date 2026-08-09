Option Explicit

' GPU Pool no-admin logon launcher.
' Task Scheduler registration is unavailable from a non-elevated session, so
' this hidden Startup-folder entry starts the same persistent service runners.

Dim sh, root, py, ps
Set sh = CreateObject("WScript.Shell")
root = "C:\Users\Drew\Projects\gpu-swarm"
py = "C:\Python313\pythonw.exe"
ps = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
sh.CurrentDirectory = root

' Start in dependency order; task_service.py keeps each child alive/restarting.
sh.Run Q(py) & " " & Q(root & "\scripts\task_service.py") & " scheduler", 0, False
WScript.Sleep 10000
sh.Run Q(py) & " " & Q(root & "\scripts\task_service.py") & " portal", 0, False
WScript.Sleep 10000
sh.Run Q(py) & " " & Q(root & "\scripts\task_service.py") & " worker", 0, False
WScript.Sleep 15000
sh.Run Q(ps) & " -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File " & Q(root & "\scripts\start_public_tunnel.ps1"), 0, False

Function Q(value)
    Q = Chr(34) & value & Chr(34)
End Function
