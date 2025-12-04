#!/bin/bash
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please activate your virtual environment before running tests."
    exit 1
fi
pytest test_unit.py
pytest test_integration.py