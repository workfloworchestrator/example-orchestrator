# Configuration

Some configuration options for the docker compose services can be overriden.

## Environment variables

For each service you can create a `.env` file to override certain variables, see `docker-compose.yml` for the expected filenames.

For example to set/change orchestrator variables, create the file in `docker/overrides/orchestrator/orchestrator.env`.

## Custom orchestrator-core

The example orchestrator can be started with a custom version of the orchestrator-core, i.e. to perform tests.

This can be done by either:

1. Cloning the orchestrator-core codebase into `docker/overrides/orchestrator-core`
2. Setting the `CORE_DIR` environment variable to an external orchestrator-core directory

The second option can be made semi-persistent by adding it to the `.env` file, for example:

```
CORE_DIR=/path/to/my/orchestrator-core
```

This orchestrator-core version is then installed into the container with hot reloading enabled.

**Note**: before changing CORE_DIR, any new database migrations should be manually reverted.
