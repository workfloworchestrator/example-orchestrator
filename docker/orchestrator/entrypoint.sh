#!/bin/bash

# Ensure all pip installed executables are on the path
PATH=$PATH:~/.local/bin

# Install extra requirements for orchestrator
pip install uv
uv sync
source .venv/bin/activate

if [ -f ${CORE_OVERRIDE}/pyproject.toml ]; then
    echo "⏭️ Use editable install of orchestrator-core"

    extras=""
    [ "${AGENT_ENABLED,,}" = "true" ] && extras+="agent,"
    [ "${SEARCH_ENABLED,,}" = "true" ] && extras+="search,"

    install_spec="$CORE_OVERRIDE"
    if [ -n "$extras" ]; then
        # Example: '/path/to/core[agent,search]'
        install_spec="$CORE_OVERRIDE"'['"${extras%,}"']'
    fi

    echo "Installing with spec: '$install_spec'"
    uv pip install -e "$install_spec"

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