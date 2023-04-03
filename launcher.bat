@ECHO OFF

SET "VENV=venv"
SET "PATH=%CD%\%venv%\Scripts\activate.bat"

:: check if the virtual environment exists
IF EXIST "%PATH%" (
    :: create the virtual environment
    CALL "%PATH%"
) ELSE (
    :: create the virtual environment
    python -m venv %VENV%
    CALL "%PATH%"
    pip install -r requirements.txt
)

:RUN_APP
python main.py