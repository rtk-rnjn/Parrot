#!/bin/bash

VENV="venv"
PATH="$PWD/$VENV/Scripts/activate"

# check if the virtual environment exists
if [ -e "$PATH" ]; then
    # activate the virtual environment
    echo "VIRTUAL ENVIRONMENT EXISTS"
    source "$PATH"
    goto RUN_APP
else
    # create the virtual environment
    echo "CREATING VIRTUAL ENVIRONMENT"
    python -m venv "$VENV"
    source "$PATH"
    goto RUN_APP
fi

# # install the requirements
# pip install -r requirements.txt

:RUN_APP

# # run the app
# python main.py
