#!/bin/bash

CD ..

VENV="venv"
PATH="$PWD/$VENV/bin/activate"

if [ -e "$PATH" ]; then
    source "$PATH"
else
    python3 -m venv "$VENV"
    source "$PATH"
    pip install -r requirements.txt
fi

python3 main.py
