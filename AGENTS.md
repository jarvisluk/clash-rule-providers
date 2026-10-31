# Workspace rules

This repository holds the personal rule providers and every client sync script.
Clash Verge (Mihomo) is the reference client: its rule order, group selections
and scripts decide what FlClash, Shadowrocket, Clash Mi and Clash.app receive.
Only DNS has its own source, `policy/dns.yaml`.

## Every change must sync all clients

After changing rules, policies, scripts here, or Clash Verge's routing or group
selections, run the single sync entry point:

```bash
python3 scripts/sync_clients.py
```

It snapshots Verge into `policy/routing.yaml`, regenerates Shadowrocket and DNS
outputs, runs every validation, installs FlClash and Verge files with backups,
and exports Clash Mi / Clash.app. Commit the result, including
`policy/routing.yaml`, in the same commit as the change; Shadowrocket receives
it only after pushing to `main`.

- Do not hand-edit `policy/routing.yaml` or generated outputs. Change Clash
  Verge (for example, select DIRECT in a service group) and re-run the sync.
- Do not edit DNS in local Verge / FlClash scripts. Edit `policy/dns.yaml`.
- Service groups are defined once, in the shared block of Verge's
  `profiles/Script.js`; the sync copies it into Merge All's script and FlClash.
- Add new site rules to a `rules/classical` provider rather than inline Clash
  rules; the sync lists any inline rule Shadowrocket would miss.
- A new provider must be referenced from Clash Verge before syncing; the
  Shadowrocket build fails if the two sets differ.
- Generated Clash Mi / Clash.app exports contain nodes and stay in the Verge
  directory. Never copy them into this public repository.
