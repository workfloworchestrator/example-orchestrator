FROM netboxcommunity/netbox:v4.0-2.9.1


# Patch strawberry schema to enable federation
RUN sed -i 's/= strawberry.Schema(/= strawberry.federation.Schema(enable_federation_2=True,/g' /opt/netbox/netbox/netbox/graphql/schema.py

# Patch strawberry types to allow joins
ADD patch_federation.py .
RUN python patch_federation.py
