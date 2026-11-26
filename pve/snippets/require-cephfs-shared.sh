#!/bin/sh
# Proxmox hookscript for CT 114 (nfs-01): refuse to start unless /pool/ceph-shared is the shared CephFS.
# Without it the container serves the node's own root disk and fills it (2026-11-26).
# One shared copy: cephfs-pve:snippets/require-cephfs-shared.sh. Master: andronics/homelab pve/snippets/.
vmid="$1"; phase="$2"
[ "$phase" = "pre-start" ] || exit 0
MP="${MP:-/pool/ceph-shared}"; WAIT="${WAIT:-60}"
mounted() { findmnt -rn -t ceph --mountpoint "$MP" >/dev/null 2>&1; }
if ! mounted; then
    systemctl reset-failed cephfs-shared.service 2>/dev/null
    systemctl start --no-block cephfs-shared.service
    i=0
    while [ "$i" -lt "$WAIT" ] && ! mounted; do sleep 1; i=$((i + 1)); done
fi
mounted && exit 0
echo "CT $vmid: $MP is not the shared CephFS; refusing to start (see: journalctl -u cephfs-shared)" >&2
exit 1
