# Network demo over HTTPS

This runs the [network demo](README.md) on a public server behind
[Traefik](https://traefik.io/) with Let's Encrypt certificates:

| URL                                | Service                         |
| ---------------------------------- | ------------------------------- |
| `https://gui.networkdemo.virge.io`     | orchestrator UI                 |
| `https://api.networkdemo.virge.io`     | orchestrator API (REST, GraphQL, websocket, `/mcp`) |
| `https://chat.networkdemo.virge.io`    | LibreChat with the agents       |
| `https://netbox.networkdemo.virge.io`  | NetBox                          |
| `https://traefik.networkdemo.virge.io` | Traefik dashboard               |

Everything lives in two files next to this one: the compose overlay
[`docker-compose.traefik.yml`](docker-compose.traefik.yml) and its settings
`networkdemo.env` (from [`networkdemo.env.example`](networkdemo.env.example)).
The tracked configuration in `docker/` is not modified.

> [!WARNING]
> None of these services has real authentication here (the orchestrator runs
> with `OAUTH2_ACTIVE=False`, and LibreChat allows anyone to register). The **IP allowlist** in
> `ALLOWED_IPS` is the only protection: every request from an address outside
> it gets a `403`. Keep the list short and tear the stack down after the demo.

## 1. DNS and firewall

- Create DNS A records for `gui`, `api`, `chat`, `netbox` and `traefik` under
  `networkdemo.virge.io`, or one wildcard `*.networkdemo.virge.io`, pointing to
  the server's public IP. On AWS, use an Elastic IP so the address survives a
  stop/start.
- Open inbound TCP **80 and 443 from `0.0.0.0/0`** in the security group.
  Let's Encrypt validates over port 80 from unpublished addresses, so port 80
  must be open to the world. The allowlist does not apply to the ACME challenge,
  and plain HTTP only redirects to HTTPS.

Check with `getent hosts gui.networkdemo.virge.io` (repeat for each name).

## 2. Prerequisites on the server

- Docker with compose v2, [uv](https://docs.astral.sh/uv/), and
  [containerlab](https://containerlab.dev/install/)
  (`bash -c "$(curl -sL https://get.containerlab.dev)"`).
- A root `.env` with the LLM credentials, as described in the
  [AI agents](../README.md#ai-agents) section:

  ```
  AGENT_MODEL=openai:gpt-5-mini
  AGENT_API_KEY=sk-...
  ```

## 3. Build `demo/networkdemo.env`

```bash
cp demo/networkdemo.env.example demo/networkdemo.env
```

Then fill it in:

- `ACME_EMAIL`: your address for the Let's Encrypt account.
- `ALLOWED_IPS`: replace `203.0.113.10/32` with the addresses you (and the
  audience's network, if needed) browse from. `curl -s https://checkip.amazonaws.com` on
  your laptop tells you yours. Keep the server's own public IP and
  `172.16.0.0/12` (the docker networks).
- The secrets: generate them in one go:

  ```bash
  sed -i \
    -e "s/^NEXTAUTH_SECRET=.*/NEXTAUTH_SECRET=$(openssl rand -hex 32)/" \
    -e "s/^LIBRECHAT_JWT_SECRET=.*/LIBRECHAT_JWT_SECRET=$(openssl rand -hex 32)/" \
    -e "s/^LIBRECHAT_JWT_REFRESH_SECRET=.*/LIBRECHAT_JWT_REFRESH_SECRET=$(openssl rand -hex 32)/" \
    -e "s/^LIBRECHAT_CREDS_KEY=.*/LIBRECHAT_CREDS_KEY=$(openssl rand -hex 32)/" \
    -e "s/^LIBRECHAT_CREDS_IV=.*/LIBRECHAT_CREDS_IV=$(openssl rand -hex 16)/" \
    -e "s/^NETBOX_ADMIN_PASSWORD=.*/NETBOX_ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')/" \
    demo/networkdemo.env
  ```

`NETBOX_ADMIN_PASSWORD` only takes effect when NetBox creates its superuser,
which happens on the first start against an empty database. On an existing
stack, change the password in NetBox itself.

To be safe with Let's Encrypt rate limits, you can uncomment `ACME_CA_SERVER`
for a first run against the staging CA.

## 4. Bring it up

Set these once per shell. After that, every `docker compose` command in
the [demo README](README.md) works as written, without the `--env-file` flags:

```bash
export COMPOSE_FILE=docker-compose.yml:demo/docker-compose.traefik.yml
export COMPOSE_ENV_FILES=.env,demo/demo.env,demo/networkdemo.env
```

```bash
docker compose config --quiet                 # catches a missing setting early
docker compose up -d --wait                   # first run builds a2a-proxy, LSO and NetBox; NetBox takes a few minutes
(cd clab && sudo containerlab deploy)         # three SR Linux nodes on the compose network
uv run python demo/scripts/demo.py seed       # bootstrap NetBox, 3 nodes, 2 core links
uv run python demo/scripts/demo.py verify
```

Then open `https://gui.networkdemo.virge.io` and `https://chat.networkdemo.virge.io`
(register a local account, pick the **planner** model). From here on the
[use cases](README.md#the-use-cases) run as described in the demo README.

## Troubleshooting

- **403 Forbidden**: your address is not in `ALLOWED_IPS`. `docker compose
  logs traefik` shows the client IP for each request. After editing the file,
  `docker compose up -d traefik` applies it.
- **Certificate warnings**: `docker compose logs traefik | grep -i acme`.
  Usually DNS doesn't point here yet, or port 80 is closed. After a staging run,
  comment out `ACME_CA_SERVER` and run `docker compose down traefik && docker volume
  rm example-orchestrator_traefik-acme && docker compose up -d traefik`.
- **UI loads but shows no data**: check the browser console. The UI
  talks to `https://api.networkdemo.virge.io` directly, so that hostname must
  resolve and be allowlisted for the browser too.
- **`up` fails with "container orchestrator is unhealthy" on a first start**:
  the orchestrator installs dependencies and reloads a few times before it
  answers, which can outlast its health check. Check that `docker logs
  orchestrator` ends with "Application startup complete", then run `docker compose up -d --wait` again.
- **Port 5432 already in use**: the overlay deliberately does not publish
  postgres on the host, so a local PostgreSQL server does not clash with it.
- **Agent answers are stale or fail after a restart**: after restarting
  `inventory-agent` or `network-agent`, also restart `planner-agent` (see the
  [AI agents](../README.md#ai-agents) note).
- **Tear down**: `docker compose down` (add `-v` for a full wipe, including
  the certificates) and `(cd clab && sudo containerlab destroy --cleanup)`.
