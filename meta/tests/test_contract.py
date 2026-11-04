"""A fake `meta` core: runs meta/homelab as the real core would (brain record 0019 §2, §3, §5)
and checks the manifest, the output conventions and the exit codes against recorded fixtures.

kubectl, ssh and gh are replaced by fake_source.py at the front of PATH, so nothing live runs.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(os.path.dirname(HERE), "homelab")
FIXTURES = os.path.join(HERE, "fixtures")
FAKE = os.path.join(HERE, "fake_source.py")

NOW = "2026-11-04T04:10:00+00:00"
ANSI = re.compile(r"\x1b\[")
STATES = {"ok", "warn", "fail", "unknown"}
MANIFEST_KEYS = {"meta", "centre", "owner", "summary", "verbs", "results", "menu"}
VERB_KEYS = {"summary", "args", "complete", "cache", "writes", "interactive", "timeout"}


class FakeCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="meta-homelab-test-")
        cls.bin = os.path.join(cls.tmp, "bin")
        os.mkdir(cls.bin)
        for tool in ("kubectl", "ssh", "gh"):
            os.symlink(FAKE, os.path.join(cls.bin, tool))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    # ------------------------------------------------------------ running the module

    def run_module(self, *args, verb=None, json_flag=False, env=None, timeout=25):
        e = {
            "PATH": os.pathsep.join([self.bin, os.path.dirname(sys.executable), "/usr/bin", "/bin"]),
            "HOME": self.tmp,
            "TZ": "UTC",
            "META_HOMELAB_NOW": NOW,
            "META": "1",
            "META_CENTRE": "homelab",
            "META_TIMEOUT": "20",
            "META_CACHE_DIR": os.path.join(self.tmp, "cache"),
            "FAKE_FIXTURES": FIXTURES,
            "FAKE_LOG": os.path.join(self.tmp, "calls.log"),
        }
        argv = list(args)
        if verb is None and argv and not argv[0].startswith("-"):
            verb = argv[0]
        if verb:
            e["META_VERB"] = verb
        if json_flag:
            e["META_JSON"] = "1"
            argv.append("--json")
        e.update(env or {})
        start = time.monotonic()
        p = subprocess.run(
            [MODULE, *argv], stdin=subprocess.DEVNULL, capture_output=True, text=True,
            env=e, timeout=timeout,
        )
        p.elapsed = time.monotonic() - start
        return p

    def assert_conventions(self, p, is_json=False):
        self.assertNotRegex(p.stdout, ANSI, "colour on a pipe")
        self.assertNotRegex(p.stderr, ANSI)
        for line in p.stderr.splitlines():
            self.assertTrue(line.startswith("meta homelab:"), f"stderr line {line!r}")
            self.assertLessEqual(len(line), 100)
        self.assertNotIn("Traceback", p.stderr)
        if is_json:
            return json.loads(p.stdout)  # exactly one JSON value, or this raises
        for line in p.stdout.splitlines():
            self.assertLessEqual(len(line), 100, f"line wider than 100: {line!r}")
        return None

    def fixtures_with(self, name, change):
        """A copy of the fixtures with one file changed by change(obj) -> obj."""
        folder = tempfile.mkdtemp(dir=self.tmp)
        for f in os.listdir(FIXTURES):
            shutil.copy(os.path.join(FIXTURES, f), folder)
        path = os.path.join(folder, name + ".json")
        with open(path) as f:
            obj = json.load(f)
        with open(path, "w") as f:
            json.dump(change(obj), f)
        return folder

    # ------------------------------------------------------------ the manifest

    def manifest(self):
        p = self.run_module("--meta-manifest", timeout=2)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertLess(p.elapsed, 2.0)
        return json.loads(p.stdout)

    def test_manifest_is_valid(self):
        m = self.manifest()
        self.assertLessEqual(set(m), MANIFEST_KEYS)
        self.assertEqual(m["meta"], 1)
        self.assertEqual(m["centre"], "homelab")
        self.assertEqual(m["owner"], "homelab-coordinator")
        self.assertIsInstance(m["summary"], str)
        self.assertIn("status", m["verbs"])
        self.assertEqual(set(m["verbs"]), {"status", "list", "show", "backlog"})
        for name, v in m["verbs"].items():
            self.assertLessEqual(set(v), VERB_KEYS, name)
            self.assertIsInstance(v["summary"], str)
            cache = v.get("cache", 0)
            self.assertTrue(isinstance(cache, int) and not isinstance(cache, bool) and cache >= 0, name)
            self.assertNotIn("writes", v, f"{name}: no module verb writes in v1")
            self.assertNotIn("interactive", v, name)
            c = v.get("complete")
            if c is not None:
                self.assertIn("args", v)
                if isinstance(c, list):
                    self.assertTrue(all(isinstance(x, str) for x in c))
                else:
                    self.assertIsInstance(c, str)
                    words = c.split()
                    self.assertEqual(words[0], "list")
                    self.assertIn("list", m["verbs"])
                    self.assertIn(words[1], m["verbs"]["list"]["complete"])
        self.assertEqual(m["verbs"]["status"]["cache"], 60)
        self.assertEqual(m["verbs"]["list"]["cache"], 300)
        self.assertEqual(m["verbs"]["list"]["complete"], ["services", "nodes", "backups"])
        self.assertEqual(m["verbs"]["show"]["complete"], "list services")
        self.assertEqual(m["verbs"]["show"]["cache"], 60)
        self.assertEqual(m["verbs"]["backlog"]["cache"], 600)
        self.assertEqual(m["results"], [1, 5])

    # ------------------------------------------------------------ status

    def test_status_plain(self):
        p = self.run_module("status")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assert_conventions(p)
        lines = p.stdout.splitlines()
        self.assertTrue(lines[0].startswith("ok"), lines[0])
        self.assertIn("homelab:", lines[0])
        names = " ".join(lines)
        for want in ("proxmox quorum", "proxmox pve-01", "k8s talos-01", "flux ks apps",
                     "flux hr kube-system/cilium", "ceph health", "ceph usage",
                     "backup media/backup-photos"):
            self.assertIn(want, names)
        for line in lines:
            self.assertIn(line.split()[0], STATES)

    def test_status_json(self):
        p = self.run_module("status", json_flag=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = self.assert_conventions(p, is_json=True)
        self.assertEqual(set(data), {"summary", "state", "checks"})
        self.assertEqual(data["state"], "ok")
        self.assertTrue(data["checks"])
        for c in data["checks"]:
            self.assertLessEqual(set(c), {"name", "state", "detail", "since"})
            self.assertIn(c["state"], STATES)
            if "since" in c:
                self.assertRegex(c["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        plain = self.run_module("status").stdout.splitlines()
        self.assertEqual(len(plain), len(data["checks"]) + 1)

    def test_status_json_from_env_alone(self):
        p = self.run_module("status", env={"META_JSON": "1"})
        self.assertEqual(json.loads(p.stdout)["state"], "ok")

    def test_status_finds_problems(self):
        def ceph_warn(o):
            o["health"] = {"status": "HEALTH_WARN", "checks": {"OSD_DOWN": {"summary": {"message": "1 osds down"}}}}
            return o
        p = self.run_module("status", json_flag=True, env={"FAKE_FIXTURES": self.fixtures_with("ceph", ceph_warn)})
        self.assertEqual(p.returncode, 1)
        data = json.loads(p.stdout)
        self.assertEqual(data["state"], "warn")
        ceph = next(c for c in data["checks"] if c["name"] == "ceph health")
        self.assertEqual(ceph["state"], "warn")
        self.assertIn("OSD_DOWN", ceph["detail"])

    def test_status_old_and_failed_backups(self):
        def stale(o):
            for i in o["items"]:
                if i["kind"] == "CronJob" and i["metadata"]["name"] == "backup-photos":
                    i["status"]["lastSuccessfulTime"] = "2026-11-03T00:00:00Z"
                if i["kind"] == "Job" and i["metadata"]["name"].startswith("backup-music-"):
                    i["status"]["conditions"] = [{"type": "Failed", "status": "True"}]
            return o
        p = self.run_module("status", json_flag=True, env={"FAKE_FIXTURES": self.fixtures_with("backups", stale)})
        self.assertEqual(p.returncode, 1)
        checks = {c["name"]: c for c in json.loads(p.stdout)["checks"]}
        self.assertEqual(checks["backup media/backup-photos"]["state"], "warn")
        self.assertEqual(checks["backup media/backup-music"]["state"], "fail")
        self.assertEqual(json.loads(p.stdout)["state"], "fail")

    def test_status_node_not_ready(self):
        def down(o):
            for c in o["items"][0]["status"]["conditions"]:
                if c["type"] == "Ready":
                    c["status"], c["reason"] = "Unknown", "NodeStatusUnknown"
            return o
        p = self.run_module("status", env={"FAKE_FIXTURES": self.fixtures_with("nodes", down)})
        self.assertEqual(p.returncode, 1)
        self.assertTrue(p.stdout.startswith("fail"))
        self.assertRegex(p.stdout, r"(?m)^fail\s+k8s talos-01\s+not Ready")

    def test_status_source_unreachable_is_exit_4(self):
        p = self.run_module("status", json_flag=True, env={"FAKE_FAIL": "ceph"})
        self.assertEqual(p.returncode, 4)
        data = self.assert_conventions(p, is_json=True)
        self.assertEqual(next(c for c in data["checks"] if c["name"] == "ceph")["state"], "unknown")
        self.assertIn("unreachable", p.stderr)
        self.assertTrue(p.stderr.startswith("meta homelab:"))

    def test_status_honours_meta_timeout(self):
        p = self.run_module("status", env={"FAKE_SLEEP": "10", "META_TIMEOUT": "2"}, timeout=8)
        self.assertEqual(p.returncode, 4)
        self.assertLess(p.elapsed, 4.0, "a source call outlived META_TIMEOUT")

    def test_status_parallel_well_under_20s(self):
        p = self.run_module("status", env={"FAKE_SLEEP": "1"})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertLess(p.elapsed, 3.5, "sources not run in parallel")

    # ------------------------------------------------------------ list and show

    def test_list_each_kind(self):
        want = {
            "services": ["music", "photos", "photos-db", "tracker", "whoami"],
            "nodes": ["pve-01", "pve-02", "pve-03", "talos-01", "talos-02", "talos-03"],
            "backups": ["backup-music", "backup-photos", "backup-tracker"],
        }
        for what, names in want.items():
            with self.subTest(what=what):
                p = self.run_module("list", what)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assert_conventions(p)
                lines = p.stdout.splitlines()
                self.assertEqual(lines, sorted(set(lines)))
                self.assertEqual(lines, names)
                j = self.run_module("list", what, json_flag=True)
                data = self.assert_conventions(j, is_json=True)
                self.assertIsInstance(data, list)
                self.assertEqual([r["name"] for r in data], names)

    def test_completion_source(self):
        """show's complete is "list services": its plain output is one value per line."""
        p = self.run_module("list", "services", env={"TOOL_STATS": "skip"})
        self.assertTrue(all(line and " " not in line for line in p.stdout.splitlines()))

    def test_show(self):
        p = self.run_module("show", "photos")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assert_conventions(p)
        kv = dict(line.split(": ", 1) for line in p.stdout.splitlines())
        self.assertEqual(kv["namespace"], "media")
        self.assertEqual(kv["ready"], "1/1")
        self.assertEqual(kv["image"], "photos=v3.3.5")
        self.assertTrue(kv["kustomization"].startswith("apps: ok"))
        self.assertEqual(kv["ingress"], "photos.example.org")
        self.assertIn("backup-photos", kv["backup"])
        j = self.run_module("show", "photos", json_flag=True)
        data = self.assert_conventions(j, is_json=True)
        self.assertEqual(data["name"], "photos")
        self.assertEqual(data["ingress_hosts"], ["photos.example.org"])
        self.assertEqual(data["last_backup"], "2026-11-04T01:00:08+00:00")

    def test_show_without_ingress_or_backup(self):
        p = self.run_module("show", "web/whoami")
        self.assertEqual(p.returncode, 0, p.stderr)
        kv = dict(line.split(": ", 1) for line in p.stdout.splitlines())
        self.assertEqual(kv["ready"], "2/2")
        self.assertEqual(kv["backup"], "none")

    def test_show_not_found_is_exit_5(self):
        for j in (False, True):
            p = self.run_module("show", "nosuch", json_flag=j)
            self.assertEqual(p.returncode, 5)
            self.assertEqual(p.stdout, "")
            self.assert_conventions(p)

    def test_list_and_show_unreachable_is_exit_4(self):
        for args in (("list", "services"), ("list", "nodes"), ("show", "photos")):
            with self.subTest(args=args):
                p = self.run_module(*args, env={"FAKE_FAIL": "workloads,proxmox"})
                self.assertEqual(p.returncode, 4)
                self.assertEqual(p.stdout, "")
                self.assert_conventions(p)

    # ------------------------------------------------------------ backlog

    def test_backlog(self):
        p = self.run_module("backlog")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assert_conventions(p)
        self.assertIn("1 open issues, 1 open PRs across 8 repos", p.stdout.splitlines()[0])
        self.assertIn("andronics/homelab-k8s", p.stdout)
        data = self.assert_conventions(self.run_module("backlog", json_flag=True), is_json=True)
        self.assertEqual(len(data["repos"]), 8)
        self.assertEqual({(i["kind"], i["number"]) for i in data["items"]}, {("issue", 3), ("pr", 12)})
        self.assertEqual(self.run_module("backlog", env={"FAKE_FAIL": "backlog"}).returncode, 4)

    # ------------------------------------------------------------ usage, help, faults

    def test_usage_errors_are_exit_2(self):
        for args in (("shwo",), ("list",), ("list", "foo"), ("show",), ("status", "extra"),
                     ("status", "--bogus"), ()):
            with self.subTest(args=args):
                p = self.run_module(*args, verb=args[0] if args else None)
                self.assertEqual(p.returncode, 2)
                self.assertEqual(p.stdout, "")
                self.assertTrue(p.stderr.startswith("meta homelab:"), p.stderr)

    def test_help(self):
        for verb in ("status", "list", "show", "backlog"):
            p = self.run_module(verb, "--help")
            self.assertEqual(p.returncode, 0)
            self.assertTrue(p.stdout.startswith(f"usage: meta homelab {verb}"))
        self.assertEqual(self.run_module("help").returncode, 0)

    def test_broken_module_is_exit_6(self):
        p = self.run_module("list", "services",
                            env={"FAKE_FIXTURES": self.fixtures_with("workloads", lambda o: {"items": ["x"]})})
        self.assertEqual(p.returncode, 6)
        self.assertNotIn("Traceback", p.stderr)
        self.assertTrue(p.stderr.startswith("meta homelab: internal error"))

    def test_sources_called_are_read_only(self):
        log = os.path.join(self.tmp, "calls.log")
        if os.path.exists(log):
            os.remove(log)
        for args in (("status",), ("list", "services"), ("list", "nodes"), ("list", "backups"),
                     ("show", "photos"), ("backlog",)):
            self.run_module(*args)
        with open(log) as f:
            calls = [json.loads(line) for line in f]
        self.assertTrue(calls)
        for c in calls:
            text = " ".join(c).lower()
            self.assertNotIn("secret", text)
            self.assertNotIn("yaml", text)
            self.assertNotIn("pass ", text)
            if c[0] == "kubectl":
                self.assertIn("get", c)
                self.assertEqual(c[-2:], ["-o", "json"])
            if c[0] == "ssh":
                self.assertRegex(c[-1], r"^(pvesh get |ceph status )")
            if c[0] == "gh":
                self.assertEqual(c[1:3], ["api", "graphql"])
                self.assertNotIn("mutation", text)


if __name__ == "__main__":
    unittest.main()
