@echo off
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process PowerShell -ArgumentList 'Set-ExecutionPolicy RemoteSigned -Force' -Verb RunAs}"
pause

python -m pip install --upgrade pip
pip install virtualenv
virtualenv venv
CALL ".\venv\Scripts\activate"

reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set OS=32BIT || set OS=64BIT

reg Query "HKCU\Software\Python\PythonCore\3.6" | find /i "3.6" > NUL && set py=36 || set py=27
reg Query "HKCU\Software\Python\PythonCore\3.7" | find /i "3.7" > NUL && set py=37 || set py=27

if %OS%==32BIT pip install -r requirements-win32-py36.txt
if %OS%==64BIT (
    if %py%==37 (
        pip install -r requirements-win64-py37.txt
    ) else (
        pip install -r requirements-win64-py36.txt
    )
)
