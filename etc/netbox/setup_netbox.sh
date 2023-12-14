# Setup Netbox
git clone git@github.com:netbox-community/netbox-docker.git
cd netbox-docker
tee docker-compose.override.yml <<EOF
version: '3.4'
services:
  netbox:
    ports:
      - 8000:8080
EOF
docker compose pull
docker compose up


# Dump Database
docker compose exec netbox bash -c "source /opt/netbox/venv/bin/activate && ./manage.py dumpdata -e extras.Script -e extras.Report -e extras.ObjectChange -e django_rq --indent 2 --output /tmp/netbox_dump.json" && \
docker compose cp netbox:/tmp/netbox_dump.json ./netbox_dump.json


# Load Database
docker compose down -v && \
docker compose up -d
docker cp ./netbox_dump.json netbox-docker-netbox-1:/tmp/netbox_dump.json && \
docker compose exec netbox sh -c "/opt/netbox/netbox/manage.py loaddata -v 3 /tmp/netbox_dump.json"


# Misc Notes
curl -X 'GET' \
  'http://localhost:8000/api/ipam/prefixes/2/available-ips/' \
  -H 'accept: application/json' \
  -H 'X-CSRFToken: u9whjnRdEjWf5f9YnCOT91jEJJsCcHhKa0bpUkbmrzh4hYEdrP1ImULGkeFvWAnF'

