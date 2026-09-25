# T-1002 — [monitoring] interface oper-state down: clab-orch-demo-par-p ethernet-1/2

From: monitoring (auto-created from alert)

## Alert payload

```json
{
  "alertname": "InterfaceOperDown",
  "device": "clab-orch-demo-par-p",
  "interface": "ethernet-1/2",
  "oper_state": "down",
  "for": "60s",
  "severity": "warning"
}
```

## Description

Automatically created. Determine whether this interface is supposed to carry
a service, whether the state is expected (maintenance, decommissioned port)
or a fault, and what the impact is.
