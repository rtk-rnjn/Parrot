#!/bin/bash

VENV="venv"
PATH="$PWD/$VENV/bin/activate"

# check if the virtual environment exists
if [ -e "$PATH" ]; then
    # activate the virtual environment
    echo "VIRTUAL ENVIRONMENT EXISTS"
    source "$PATH"
else
    # create the virtual environment
    echo "CREATING VIRTUAL ENVIRONMENT"
    python -m venv "$VENV"
    source "$PATH"
fi

# # install the requirements
# pip install -r requirements.txt
# # run the app
python3 main.py
