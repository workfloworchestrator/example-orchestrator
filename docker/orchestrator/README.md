# Testing orchestrator-core upgrades

> Note: If you are looking for _development_ on the orchestrator-core, see `./docker/overrides/configuration.md`.
 
The below instructions are for testing changes that require recreating the orchestrator docker compose service, such as:
- updates to the `ghcr.io/workfloworchestrator/orchestrator-core` image
- changes to the entrypoint.sh
- changes to pyproject.toml

## 1. Start clean and up to date

Stop containers and remove all volumes:

```sh
docker compose down --volumes
```

Pull the latest images, ensure all of them are built, and start the containers:

```sh
docker compose pull && docker compose build && docker compose up
```

So far everything should work out of the box, if not then there are pre-existing issues that should be resolved.

## 2. Make your changes

Now you can make your changes, for example temporarily using a pre-release of the orchestrator-core by changing `.env` to:

```
ORCH_BACKEND_TAG=ghcr.io/workfloworchestrator/orchestrator-core:edge
```

You can also make changes to pyproject.toml/uv.lock or entrypoint.sh (in this folder)

## 3. Recreate the container

To test the changes from step 2, run:

```
docker compose up -d --force-recreate orchestrator
```

Inspect the results in your other terminal where `docker compose up` is running.

If needed, make changes or fixes and re-run the above command.
