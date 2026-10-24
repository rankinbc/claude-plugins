@echo off
rem courier-session.cmd - the SessionStart hook: one line for the person saying whether the guard is live.
rem Always exits 0 (a failing SessionStart hook hides its own message). With no Python 3.11+ it says so
rem itself, because in that state every guarded tool call is refused until one is installed.
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYCMD="
if defined COURIER_PYTHON if exist "%COURIER_PYTHON%" set "PYCMD="%COURIER_PYTHON%""
if not defined PYCMD call :probe py -3
if not defined PYCMD call :probe python
if not defined PYCMD call :probe python3
if not defined PYCMD (
  echo {"systemMessage": "secret-courier: no Python 3.11 or newer was found, so every Bash, PowerShell, Read, Grep, Glob, Write and Edit call is refused until one is installed (winget install Python.Python.3.13), then restart Claude Code."}
  exit /b 0
)
%PYCMD% -I -X utf8 -B "%ROOT%\scripts\courier_entry.py" --session-start
exit /b 0

:probe
%* -c "import sys;raise SystemExit(sys.version_info < (3,11))" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYCMD=%*"
exit /b 0
