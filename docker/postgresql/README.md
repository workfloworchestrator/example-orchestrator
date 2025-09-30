# Postgres init files

All `.sql` files in this directory are mounted into the postgres container and executed on startup.


## Netbox database snapshot

`01-netbox.sql` contains a Netbox database snapshot that helps reduce startup time.


### Update snapshot

To update the snapshot, i.e. when Netbox is updated, perform the following steps.
The `pg_dump` utility is required.

1. Destroy your local docker compose volume (or temporarily use a new docker compose project name)
2. Set the database snapshot to empty:
```sh
echo "CREATE DATABASE netbox;" > 01-netbox.sql
```
3. Start docker compose as normal and wait for Netbox migrations to complete
4. Generate a new database snapshot:
```sh
pg_dump -d postgresql://nwa:nwa@127.0.0.1:5432/netbox --create -f 01-netbox.sql
```
