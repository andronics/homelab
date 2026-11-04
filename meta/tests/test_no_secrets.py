"""Brain record 0019 §6: the homelab module never reads Kubernetes Secrets, never calls `pass`
to show anything, and never asks for YAML (where Secret data would come back). This greps the
module's source and fails on any of it."""

import os
import re
import unittest

MODULE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "homelab")

FORBIDDEN = {
    "kubectl get secret": re.compile(r"get\W+secrets?\b", re.I),
    "the secrets resource, in any form": re.compile(r"\bsecrets?\b", re.I),
    "pass show": re.compile(r"pass\W+show", re.I),
    "pass as a command": re.compile(r"""["']pass["']"""),
    "-o yaml": re.compile(r"-o\W*yaml|output\W*yaml", re.I),
    "yaml output at all": re.compile(r"\byaml\b", re.I),
    "kubectl config view": re.compile(r"config\W+view", re.I),
    "a shell between the module and a source": re.compile(r"shell\s*=\s*True"),
}


class NoSecrets(unittest.TestCase):
    def test_module_source_has_no_secret_access(self):
        with open(MODULE) as f:
            lines = f.read().splitlines()
        found = [
            f"line {n}: {why}: {line.strip()}"
            for n, line in enumerate(lines, 1)
            for why, pattern in FORBIDDEN.items()
            if pattern.search(line)
        ]
        self.assertEqual(found, [], "\n".join(found))

    def test_the_grep_catches_what_it_should(self):
        bad = ['["kubectl", "get", "secret", "x"]', "kubectl get secrets -A", "pass show services/x",
               '["kubectl", "get", "pods", "-o", "yaml"]', 'subprocess.run(c, shell=True)']
        for line in bad:
            self.assertTrue(any(p.search(line) for p in FORBIDDEN.values()), line)


if __name__ == "__main__":
    unittest.main()
