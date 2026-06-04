@echo off
REM ============================================================================
REM  Tunify - one-click launcher for Windows
REM
REM  What this does:
REM    1. Checks Python is installed (and >= 3.10)
REM    2. Creates a virtual environment in .venv\ on first run
REM    3. Installs dependencies (only if requirements.txt changed)
REM    4. Starts the Flask server and opens your browser
REM
REM  Just double-click this file.
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  ============================================================
echo   Tunify - Same-artist music recommendation system
echo  ============================================================
echo.

REM ---- Step 1: Check Python ------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo  ERROR: Python is not installed or not in your PATH.
    echo.
    echo  Please install Python 3.10 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo  During install, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo  Found %PYVER%
echo.

REM ---- Step 2: Create venv if missing --------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo  First-time setup: creating virtual environment in .venv\ ...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo  ERROR: Could not create virtual environment.
        pause
        exit /b 1
    )
    REM Force install on first run.
    if exist ".venv\.last_install" del ".venv\.last_install" >nul 2>nul
)

REM ---- Step 3: Install / update dependencies -------------------------------
REM Only re-install when requirements.txt has changed.
set "REQ_HASH_FILE=.venv\.last_install"
set "NEED_INSTALL=1"
if exist "%REQ_HASH_FILE%" (
    for /f "delims=" %%h in ('certutil -hashfile requirements.txt SHA256 ^| findstr /v ":"') do set "REQ_NOW=%%h"
    set /p REQ_OLD=<"%REQ_HASH_FILE%"
    if "!REQ_NOW!"=="!REQ_OLD!" set "NEED_INSTALL=0"
)

if "%NEED_INSTALL%"=="1" (
    echo  Installing/updating dependencies ^(this may take a minute^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo  ERROR: Dependency install failed. See messages above.
        pause
        exit /b 1
    )
    for /f "delims=" %%h in ('certutil -hashfile requirements.txt SHA256 ^| findstr /v ":"') do echo %%h>"%REQ_HASH_FILE%"
    echo  Dependencies ready.
    echo.
) else (
    echo  Dependencies up to date.
    echo.
)

REM ---- Step 4: Launch ------------------------------------------------------
".venv\Scripts\python.exe" launch.py

REM Keep window open if launch.py exits with an error.
if errorlevel 1 pause
endlocal
