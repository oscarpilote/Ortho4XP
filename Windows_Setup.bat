@echo off
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process PowerShell -ArgumentList 'Set-ExecutionPolicy RemoteSigned -Force' -Verb RunAs}"
pause

python -m pip install --upgrade pip
pip install virtualenv
virtualenv venv
CALL ".\venv\Scripts\activate"

reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT

if %OS%==32BIT pip install -r requirements-win32-py36.txt
if %OS%==64BIT pip install -r requirements-win64-py36.txt
