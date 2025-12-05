#!/bin/bash
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please activate your virtual environment before running tests."
fi
if [ -n "$VIRTUAL_ENV" ]; then
pytest test_unit.py
pytest test_integration.py
fi