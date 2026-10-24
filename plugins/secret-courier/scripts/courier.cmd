@echo off
rem courier.cmd - the CLI: `courier <command> ...` (exists, copy, prompt, test, inject, run, remove, sweep,
rem sinks, scan, doctor). Same interpreter search as the guard; a missing interpreter exits 1 with the fix.
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYCMD="
if defined COURIER_PYTHON if exist "%COURIER_PYTHON%" set "PYCMD="%COURIER_PYTHON%""
if not defined PYCMD call :probe py -3
if not defined PYCMD call :probe python
if not defined PYCMD call :probe python3
if not defined PYCMD (
  1>&2 echo secret-courier: no Python 3.11 or newer was found. Fix: winget install Python.Python.3.13
  exit /b 1
)
%PYCMD% -I -X utf8 -B "%ROOT%\scripts\courier_entry.py" --cli %*
exit /b %ERRORLEVEL%

:probe
%* -c "import sys;raise SystemExit(sys.version_info < (3,11))" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYCMD=%*"
exit /b 0
