@echo off
setlocal
echo === Using Python ===
where python || echo (python not in PATH)
echo.
echo === Running build.py ===
REM اگر python کار نکرد، این خط رو فعال کن و بالایی رو کامنت کن:
REM py -3 "%~dp0build.py" & echo ExitCode: %ERRORLEVEL% & pause & exit /b

python "%~dp0build.py"
echo.
echo ExitCode: %ERRORLEVEL%
echo (اگر خطا دیدی، همین پنجره رو عکس بگیر و بفرست)
pause
