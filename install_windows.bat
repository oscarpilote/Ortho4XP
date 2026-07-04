@echo off
echo Setting up Ortho4XP...
echo:

echo Setting up a Python virtual environment
python -m venv venv
echo:

echo Activating the Python virtual environment
call venv\Scripts\activate.bat
echo:

echo Installing Python dependency: gdal
pip install Utils\win\gdal-3.11.1-cp313-cp313-win_amd64.whl
echo:

echo Installing Python dependency: scikit-fmm
pip install Utils\win\scikit_fmm-2025.6.23-cp313-cp313-win_amd64.whl
echo:

echo Installing remaining Python dependencies
pip install -r requirements.txt
echo:

echo Ortho4XP setup complete!
echo:

echo Use start_windows.bat to start Ortho4XP
echo:

call deactivate
pause