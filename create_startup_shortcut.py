import os
import subprocess

startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
target = os.path.abspath("run_cctv_silent.bat")
vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{startup_dir}\\CCTV_Store_AI.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "{os.path.abspath('.')}"
oLink.WindowStyle = 7
oLink.Save
'''
with open("create_lnk.vbs", "w", encoding="utf-8") as f:
    f.write(vbs_content)

subprocess.run(["cscript", "//nologo", "create_lnk.vbs"], check=True)
os.remove("create_lnk.vbs")
print(f"🎉 Created permanent Windows Startup shortcut:\n{startup_dir}\\CCTV_Store_AI.lnk")
