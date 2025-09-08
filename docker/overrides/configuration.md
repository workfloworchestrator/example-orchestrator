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

## Orchestrator UI & backend docker image overrides

In [docker-compose.yml](../../docker-compose.yml), the `orchestrator` and
`orchestrator-ui` services use pre-built images to spin up their respective
applications (i.e., there is no `build:` directive specified). The docker image
tag defaults to use the artifacts built in the workfloworchestrator project's
Github Container Registry, but can be overridden by setting environment
variables.

### For Example

```bash
ORCH_UI_IMAGE=my-local-image:tag docker compose up -d --force-recreate
```
