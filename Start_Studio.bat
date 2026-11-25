@echo off
cd /d "%~dp0"
echo Starting Producer Reborn Studio GUI...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" ".agents\plugins\producer-reborn\studio_gui.py"
) else (
    python ".agents\plugins\producer-reborn\studio_gui.py"
)
pause
