@echo off
REM ---------------------------------------------------------
REM  Update ClaudeFB column (docs/fb.csv) and push to GitHub.
REM  ASCII only: cmd.exe reads .bat in the system codepage.
REM  All output goes to _fb_update.log so failures are visible.
REM ---------------------------------------------------------
setlocal
cd /d "%~dp0"
set "LOG=%~dp0_fb_update.log"

REM rotate the log so it cannot grow forever
if exist "%LOG%" for %%A in ("%LOG%") do if %%~zA GTR 300000 del "%LOG%"

call :run >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo [%date% %time%] FAILED rc=%RC% >> "%LOG%"
exit /b %RC%


:run
echo.
echo ===== %date% %time% =====

REM --- guard: GitHub Pages serves main/docs, so any other branch is a silent no-op
set "BRANCH="
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%B"
if not "%BRANCH%"=="main" (
  echo [ERROR] on branch "%BRANCH%" but Pages serves "main" - aborting
  exit /b 2
)

REM --- build
uv run python build_fb.py
if errorlevel 1 (
  echo [ERROR] build_fb.py failed
  exit /b 3
)

REM --- nothing changed on disk? then there is nothing to send
git diff --quiet -- docs/fb.csv
if not errorlevel 1 (
  echo OK: no change
  exit /b 0
)

git add docs/fb.csv
if errorlevel 1 (
  echo [ERROR] git add failed
  exit /b 4
)

git -c user.name="Okazaki" -c user.email="komugigoma0805@gmail.com" commit -m "Update ClaudeFB" -q
if errorlevel 1 (
  echo [ERROR] git commit failed
  exit /b 5
)

git push -q
if errorlevel 1 (
  echo [ERROR] git push failed - GitHub is now BEHIND the local commit
  exit /b 6
)

echo OK: updated and pushed
exit /b 0
