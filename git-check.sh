#!/bin/bash

if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null; then
  git pull
fi
