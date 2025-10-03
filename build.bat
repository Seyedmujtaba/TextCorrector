@echo off
setlocal
cd /d "%~dp0"

echo === Using Python ===
where python
echo.

echo === Running build.py ===
python "%~dp0build.py"
set EC=%ERRORLEVEL%
echo.
echo ExitCode: %EC%

echo.
echo === Dist listing ===
dir /-c "%~dp0dist"

echo.
echo Press any key to exit...
pause >nul
