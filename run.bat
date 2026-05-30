@echo off
REM This batch file starts the Flask backend server
REM @echo off = don't print each command to screen

echo Starting Doom Scrolling Stop backend...
echo.

REM Change directory to the backend folder
cd /d "%~dp0backend"

REM Start the Flask server
python app.py

REM If server crashes, pause so you can read the error
pause