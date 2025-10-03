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
echo (اگر خطا دیدی، همین پنجره رو نبند؛ اسکرین‌شات بگیر)
pause
