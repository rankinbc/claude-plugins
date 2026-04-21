@echo off
REM Windows double-click launcher for Claude Code.
REM Requires `claude` to be on your PATH (default after installing Claude Code).
cd /d "%~dp0"
echo Starting Claude Code in %CD%...
echo.
claude
REM If Claude Code exits, pause so the window doesn't close immediately.
if errorlevel 1 pause
