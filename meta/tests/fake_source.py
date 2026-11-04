#!/usr/bin/env python3
"""Stands in for kubectl, ssh and gh in the tests: answers from recorded fixtures.

The tests link this file as `kubectl`, `ssh` and `gh` in a folder at the front of PATH.
  FAKE_FIXTURES  folder of <source>.json answers (default: ./fixtures beside this file)
  FAKE_FAIL      comma-separated sources that act unreachable (exit 1, a line on stderr)
  FAKE_SLEEP     seconds to wait before answering (to test META_TIMEOUT)
  FAKE_LOG       file each call's argv is appended to, one JSON list per line
"""
import json
import os
import sys
import time


def source(tool, args):
    if tool == "kubectl":
        rest = args[args.index("get") + 1:] if "get" in args else []
        what = rest[0] if rest else ""
        if what == "nodes":
            return "nodes"
        if what.startswith("kustomizations."):
            return "flux"
        if what == "cronjobs,jobs":
            return "backups"
        if what == "deployments":
            return "workloads"
        if what.startswith("ingressroutes."):
            return "routes"
    if tool == "ssh" and args:
        if args[-1].startswith("pvesh get /cluster/status"):
            return "proxmox"
        if args[-1].startswith("ceph status"):
            return "ceph"
    if tool == "gh" and args[:2] == ["api", "graphql"]:
        return "backlog"
    return None


def main():
    tool = os.path.basename(sys.argv[0])
    args = sys.argv[1:]
    log = os.environ.get("FAKE_LOG")
    if log:
        with open(log, "a") as f:
            f.write(json.dumps([tool] + args) + "\n")
    src = source(tool, args)
    if src is None:
        sys.stderr.write(f"fake {tool}: no fixture for {args}\n")
        return 64
    if float(os.environ.get("FAKE_SLEEP", "0") or 0):
        time.sleep(float(os.environ["FAKE_SLEEP"]))
    if src in os.environ.get("FAKE_FAIL", "").split(","):
        sys.stderr.write(f"fake {tool}: connection refused\n")
        return 1
    folder = os.environ.get("FAKE_FIXTURES") or os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures")
    with open(os.path.join(folder, src + ".json")) as f:
        sys.stdout.write(f.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
