@echo off
setlocal

title IT Toolkit

set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%\src"
set "IT_TOOLKIT_LAUNCHER_SHELL=cmd"

echo.
echo ==========================================
echo              IT TOOLKIT
echo ==========================================
echo.

set "PYTHON_CMD="

where py >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    py -3.10 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1

    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.10"
        goto :RUN
    )
)

where python >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1

    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        goto :RUN
    )
)

echo ERROR: Python 3.10 or newer is required.
echo.
echo Please use an approved offline Python installation.
echo.

goto :END

:RUN

echo Starting detection engine...
echo.

%PYTHON_CMD% -m it_toolkit.main

if errorlevel 1 (
    echo.
    echo Toolkit exited with an error.
)

:END

echo.
pause

endlocal