@echo off

if not exist "%ProgramFiles%\Git\git.exe" (
  echo "Git is not installed."
  exit /b 1
)

for /f "delims=" %%i in ('git rev-parse --is-inside-work-tree') do (
  if not "%%i"=="true" (
    echo "The current directory is not a git repository."
    exit /b 1
  )
)

git pull
