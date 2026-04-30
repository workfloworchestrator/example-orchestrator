#!/bin/bash

# Exit on errors or unset variables
set -eu

# Tell uv not to ever download python, but use whatever version is set in https://github.com/workfloworchestrator/orchestrator-core/blob/main/Dockerfile
# This version should match with pyproject.toml
export UV_PYTHON_DOWNLOADS=never

# Install extra requirements for example-orchestrator
uv sync
source .venv/bin/activate

setup() {
    echo "▶ db upgrade heads"
    python main.py db upgrade heads

    echo "▶ index subscriptions"
    python main.py index subscriptions

    echo "▶ index products"
    python main.py index products

    echo "▶ index processes"
    python main.py index processes

    echo "▶ index workflows"
    python main.py index workflows
}

if [ -f ${CORE_OVERRIDE}/pyproject.toml ]; then
    echo "⏭️ Use editable install of orchestrator-core"

    extras=""  # comma delimited list of extras

    install_spec="$CORE_OVERRIDE"
    if [ -n "$extras" ]; then
        # Example: '/path/to/core[agent,search]'
        install_spec="$CORE_OVERRIDE"'['"${extras%,}"']'
    fi

    echo "Installing with spec: '$install_spec'"
    uv pip install -e "$install_spec"

    setup

    uvicorn --host 0.0.0.0 --port 8080 ${UVICORN_ARGS:-} wsgi:app --reload --proxy-headers \
        --reload-dir $CORE_OVERRIDE \
        --reload-dir products \
        --reload-dir services \
        --reload-dir translations \
        --reload-dir utils \
        --reload-dir workflows
else
    setup

    echo "⏭️ Use orchestrator-core as specified in pyproject.toml $(uv pip freeze | grep orchestrator-core)"
    uvicorn --host 0.0.0.0 --port 8080 ${UVICORN_ARGS:-} wsgi:app --reload --proxy-headers
fi
