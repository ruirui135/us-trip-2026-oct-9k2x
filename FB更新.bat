@echo off
REM ---------------------------------------------------------
REM  Update ClaudeFB column (docs/fb.csv) and push to GitHub.
REM  ASCII only: cmd.exe reads .bat in the system codepage.
REM ---------------------------------------------------------
cd /d "%~dp0"

echo [%date% %time%] start

uv run python build_fb.py
if errorlevel 1 (
  echo [ERROR] build_fb.py failed
  exit /b 1
)

git diff --quiet -- docs/fb.csv
if errorlevel 1 (
  git add docs/fb.csv
  git -c user.name="Okazaki" -c user.email="komugigoma0805@gmail.com" commit -m "Update ClaudeFB" -q
  git push -q
  echo [%date% %time%] pushed
) else (
  echo [%date% %time%] no change
)

exit /b 0
