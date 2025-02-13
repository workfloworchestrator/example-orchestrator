# Ensure all pip installed executables are on the path
export PATH=$PATH:~/.local/bin

if [ -f ${CORE_OVERRIDE}/pyproject.toml ]; then
    export DATABASE_URI=${DATABASE_URI}-test
    echo "⏭️ Detected editable core installation, setting DATABASE_URI=$DATABASE_URI to allow running unit tests from $CORE_OVERRIDE"
fi
