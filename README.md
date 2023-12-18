# Example Workflow Orchestrator

Example workflow orchestrator
(https://workfloworchestrator.org/orchestrator-core/) implementation.

## Quickstart

Make sure you have docker installed and run:

```
docker compose up
```

This will start the `orchestrator`, `orchestrator-gui`, `netbox`, `postgres`
and `redis`.

To access the `orchestrator-gui`, point your browser to:

```
http://localhost:3000/
```

And to access `netbox` (admin/admin), point your browser to:

```
http://localhost:8000/
```

## Using the example orchestrator

Use the following steps to see the example orchestrator in action:

1. bootstrap Netbox
   1. from the `Tasks` tab click `New Task`
   2. select `Bootstrap Netbox` and click `Submit` (twice)
2. create a network node (need at least two to create a core link)
   1. in the right-above corner, click on the `New Process` button
   2. select either the `Node Cisco` or `Node Nokia` and click `Next`
   3. fill in the needed fields, click `Submit` and view the summary form
   4. click `Submit` again to start the workflow, or click `Previous` to modify fields
3. add interfaces to a node (needed by the other products)
   1. on the `Subscriptions` tab, click on the subscription for the node to show the details
   2. on the `Actions` tab, click on the `Sync ports with IMS` action and confirm to start the workflow
4. create a core link
   1. in the right-above corner, click on the `New Process` button
   2. select either the `core link 10G` or `core link 100G` and click `Next`
   3. fill in de forms and finally click on `Submit` to start the workflow
5. create a customer port (need at least two **tagged** ports to create a l2vpn)
   1. start a `New Process` for either a `port 10G` or a `port 100G`
   3. fill in de forms and finally click on `Submit` to start the workflow
6. create a l2vpn
   1. start a `New Process` for a `l2vpn`, fill in the forms, and `Submit` to start the workflow

While running the different workflows, have a look at the following netbox
pages to see the orchestrator interact with netbox:

- Devices
  - Devices
  - Interfaces
- Connections
  - Cables
  - Interface Connections
- IPAM
  - IP Addresses
  - Prefixes
  - VLANs
- Overlay
  - L2VPNs
  - Terminations
