@echo off
setlocal
set "JEEVES_PYTHON=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
if not exist "%JEEVES_PYTHON%" (
    echo BLOCKED: reviewed native Jeeves Python was not found.
    exit /b 2
)
"%JEEVES_PYTHON%" "%~dp0kanban-control.py" %*
exit /b %errorlevel%
