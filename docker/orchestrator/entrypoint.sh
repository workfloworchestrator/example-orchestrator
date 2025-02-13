#!/bin/bash

# Ensure all pip installed executables are on the path
PATH=$PATH:~/.local/bin

# Install extra requirements for orchestrator
pip install -r requirements.txt

if [ -f ${CORE_OVERRIDE}/pyproject.toml ]; then
    echo "⏭️ Use editable install of orchestrator-core with dev and test dependencies"
    pip install -e $CORE_OVERRIDE[dev,test]

    # Run any missing migrations on the database
    python main.py db upgrade heads

    uvicorn --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app --reload --proxy-headers --reload-dir $CORE_OVERRIDE
else
    # Run any missing migrations on the database
    python main.py db upgrade heads

    echo "⏭️ Use pip installed orchestrator-core $(pip freeze | grep orchestrator-core)"
    uvicorn --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app --reload --proxy-headers
fi
