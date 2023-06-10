@ECHO OFF

CD ..
SET "VENV=venv"
SET "PATH=%CD%\%venv%\Scripts\activate.bat"

IF EXIST "%PATH%" (
    CALL "%PATH%"
) ELSE (
    python -m venv %VENV%
    CALL "%PATH%"
    pip install -r requirements.txt
)

:RUN_APP
python main.py