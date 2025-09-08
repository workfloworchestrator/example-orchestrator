#!/bin/bash

# Ensure all pip installed executables are on the path
PATH=$PATH:~/.local/bin

# Install extra requirements for orchestrator
pip install uv
uv sync
source .venv/bin/activate

if [ -f ${CORE_OVERRIDE}/pyproject.toml ]; then
    echo "⏭️ Use editable install of orchestrator-core with dev and test dependencies"
    uv pip install -e $CORE_OVERRIDE[dev,test]

    # Run any missing migrations on the database
    python main.py db upgrade heads

    uvicorn --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app --reload --proxy-headers \
        --reload-dir $CORE_OVERRIDE \
        --reload-dir products \
        --reload-dir services \
        --reload-dir translations \
        --reload-dir utils \
        --reload-dir workflows
else
    # Run any missing migrations on the database
    python main.py db upgrade heads

    echo "⏭️ Use orchestrator-core as specified in pyproject.toml $(uv pip freeze | grep orchestrator-core)"
    uvicorn --host 0.0.0.0 --port 8080 $UVICORN_ARGS main:app --reload --proxy-headers
fi
