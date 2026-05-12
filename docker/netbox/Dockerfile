FROM netboxcommunity/netbox:v4.5-4.0.2

# NOTE: when updating the Netbox version, remember to update the database snapshot. See docker/postgresql/README.md for details

# Patch strawberry schema to enable federation
RUN sed -i 's/= strawberry.Schema(/= strawberry.federation.Schema(/g' /opt/netbox/netbox/netbox/graphql/schema.py

# Patch strawberry types to allow joins
ADD patch_federation.py .
RUN python patch_federation.py
