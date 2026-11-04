# meta homelab

The homelab centre's module for `meta`, the front door to every knowledge centre (the brain's
design record 0019). One executable, `meta/homelab`, Python 3 standard library only, read-only.

## What it shows

| Verb | Shows | Reads | Cache |
|---|---|---|---|
| `status` | Proxmox quorum and nodes online; Kubernetes (Talos) nodes Ready; Flux Kustomizations and HelmReleases ready or failing; Ceph health and raw usage; the newest backup per job and its age. A summary line, then one line per check | `ssh pve-01 pvesh get /cluster/status`, `ssh pve-01 ceph status`, `kubectl get nodes`, Flux Kustomizations and HelmReleases, CronJobs and Jobs labelled `app.kubernetes.io/component=backup` | 60 s |
| `list services\|nodes\|backups` | One name per line, sorted. *Services* are the Deployments the Flux Kustomization `apps` manages | the same sources | 300 s |
| `show <service>` | `key: value` lines: namespace, ready replicas, image tags, the `apps` Kustomization's state, ingress host, last backup. Exit 5 if there is no such service | Deployments, Traefik IngressRoutes, Flux, the backup CronJobs | 60 s |
| `backlog` | Open issues and pull requests across the eight homelab repos, numbers and titles | `gh api graphql` | 600 s |

Every verb takes `--json` (one JSON value on stdout) and `--help`. The core does the caching;
the module calls its sources in parallel, and stops each before `META_TIMEOUT` runs out.

Thresholds: a backup warns after 26 hours and fails after 50 hours or when its newest run failed;
Ceph usage warns at 75% and fails at 85%.

Exit codes are the record's: 0 all well, 1 a problem found, 2 usage, 4 a live source
unreachable, 5 not found, 6 the module broke.

It never reads a Kubernetes Secret, never asks a source for YAML, and prints no key, token or
password; `meta/tests/test_no_secrets.py` greps the source to keep it so.

## Running it

```sh
meta homelab status            # through the core, once registered
meta/homelab status            # straight from a checkout on the desktop
meta/homelab show <service> --json
meta/homelab --meta-manifest   # what the core reads to learn the verbs
```

It needs, on the desktop, the access the homelab coordinator already uses read-only: `kubectl`
with the cluster's kubeconfig, `ssh pve-01`, and `gh`.

## How the core finds it

The homelab coordinator's actor note in the brain carries a `meta_module` property with the
absolute path of this executable on the desktop. The core runs `<path> --meta-manifest`, caches
the answer, and then runs `<path> <verb> [args]` with `META=1`, `META_CENTRE`, `META_VERB`,
`META_JSON` and `META_TIMEOUT` set and stdin closed.

## Tests

```sh
python3 -m unittest discover -s meta/tests -v
```

A fake core (`meta/tests/test_contract.py`) checks the manifest, the output conventions and the
exit codes. `kubectl`, `ssh` and `gh` are replaced by `meta/tests/fake_source.py`, answering from
trimmed, hand-checked recordings in `meta/tests/fixtures/` (names and hosts made generic), so
CI never needs the live system.
