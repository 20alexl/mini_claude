@echo off
REM Mini Claude MCP Server launcher for Windows
REM This wrapper handles paths with spaces

setlocal
set "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%venv\Scripts\python.exe" -m mini_claude.server %*
