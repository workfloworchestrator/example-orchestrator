FROM netboxcommunity/netbox:v4.4.1

# NOTE: when updating the Netbox version, remember to update the database snapshot. See docker/postgresql/README.md for details

# Patch strawberry schema to enable federation
RUN sed -i 's/= strawberry.Schema(/= strawberry.federation.Schema(enable_federation_2=True,/g' /opt/netbox/netbox/netbox/graphql/schema.py

# Patch strawberry types to allow joins
ADD patch_federation.py .
RUN python patch_federation.py
