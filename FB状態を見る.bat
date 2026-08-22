@echo off
REM ---------------------------------------------------------
REM  Show the health of the ClaudeFB auto-update system.
REM  Double-click this when the FB column looks stale.
REM ---------------------------------------------------------
cd /d "%~dp0"
chcp 65001 > nul

echo.
echo ==========================================
echo   ClaudeFB auto-update : health check
echo ==========================================
echo.

echo --- [1] scheduled task ---
schtasks /Query /TN ClaudeFB_Update30min /FO LIST /V 2>nul | findstr /C:"Status" /C:"Last Run Time" /C:"Last Result" /C:"Next Run Time" /C:"Scheduled Task State"
if errorlevel 1 echo   [NG] task not found - it may have been deleted
echo.
echo   Last Result 0 = OK / not 0 = failed
echo.

echo --- [2] current branch (must be main) ---
git rev-parse --abbrev-ref HEAD
echo.

echo --- [3] unpushed commits (should be empty) ---
git log --oneline origin/main..HEAD
echo.

echo --- [4] last lines of the log ---
if exist "_fb_update.log" (
  powershell -NoProfile -Command "Get-Content '_fb_update.log' -Tail 12 -Encoding UTF8"
) else (
  echo   no log yet
)
echo.

echo --- [5] what the sheet is actually reading ---
powershell -NoProfile -Command "try { $r = Invoke-WebRequest 'https://ruirui135.github.io/us-trip-2026-oct-9k2x/fb.csv' -UseBasicParsing -TimeoutSec 20; $first = ($r.Content -split \"`n\")[0]; Write-Host ('  HTTP ' + $r.StatusCode + '  ' + $first) } catch { Write-Host '  [NG] could not fetch the published CSV' }"
echo.

echo ==========================================
pause
