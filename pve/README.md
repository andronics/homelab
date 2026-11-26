# Proxmox node files

Master copies of the hand-installed guards on the Proxmox nodes.

## `snippets/require-cephfs-shared.sh`

Hookscript for CT 114 (`nfs-01`). It refuses a start unless `/pool/ceph-shared` is the shared CephFS, so the
container can never serve, and fill, a node's own root disk. One copy, on the shared `cephfs-pve` storage:

```sh
pvesm set cephfs-pve --content backup,iso,vztmpl,snippets
mkdir -p /mnt/pve/cephfs-pve/snippets
install -m 755 require-cephfs-shared.sh /mnt/pve/cephfs-pve/snippets/
pct set 114 --hookscript cephfs-pve:snippets/require-cephfs-shared.sh
```

* If `cephfs-pve` is not mounted on a node, Proxmox cannot find the script and the start fails.
* If high availability reports `error` after refused starts: fix the mount, then
  `ha-manager set ct:114 --state disabled`, then `--state started`.
* Each node also has `chattr +i` on the empty directory underneath `/pool/ceph-shared`.

## `cephfs-shared.retry.conf`

On every node as `/etc/systemd/system/cephfs-shared.service.d/retry.conf`, then `systemctl daemon-reload`.
It retries the CephFS mount until it succeeds.
