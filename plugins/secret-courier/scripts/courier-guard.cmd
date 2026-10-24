@echo off
rem courier-guard.cmd - run one Claude Code guard hook (--bash-hook | --read-hook | --write-hook | --prompt-hook)
rem with whatever Python 3.11+ the machine has and no venv (the guard is stdlib only). FAILS CLOSED: no
rem interpreter, or any exit other than 0 and 2, refuses the tool call (exit 2). The prompt hook is the one
rem exception (exit 0): the developer's message must survive. Order: %COURIER_PYTHON%, py -3, python, python3.
rem Never print "No such file or directory" here: Claude Code downgrades a plugin prompt hook that says so.
setlocal
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "FAILRC=2"
if "%~1"=="--prompt-hook" set "FAILRC=0"
set "PYCMD="
if defined COURIER_PYTHON if exist "%COURIER_PYTHON%" set "PYCMD="%COURIER_PYTHON%""
if not defined PYCMD call :probe py -3
if not defined PYCMD call :probe python
if not defined PYCMD call :probe python3
if not defined PYCMD (
  1>&2 echo secret-courier guard: no Python 3.11 or newer was found, so this tool call is refused. Fix: winget install Python.Python.3.13 then restart Claude Code.
  exit /b %FAILRC%
)
%PYCMD% -I -X utf8 -B "%ROOT%\scripts\courier_entry.py" %*
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" exit /b 0
if "%RC%"=="2" exit /b 2
1>&2 echo secret-courier guard: the guard exited with code %RC%, so this tool call is refused.
exit /b %FAILRC%

:probe
%* -c "import sys;raise SystemExit(sys.version_info < (3,11))" >nul 2>&1
if errorlevel 1 exit /b 0
set "PYCMD=%*"
exit /b 0
