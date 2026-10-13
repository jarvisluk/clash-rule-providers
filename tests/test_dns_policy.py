import copy
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dns_policy import load_policy, mihomo_config, shadowrocket_general
from build_dns import outputs
from build_shadowrocket import build
from install_local_dns import attach_policy, merge_config


class DnsPolicyTests(unittest.TestCase):
    def test_default_uses_final_and_direct_uses_domestic_doh(self):
        config = mihomo_config(load_policy())
        dns = config["dns"]
        self.assertTrue(all(url.endswith("#Final") for url in dns["nameserver"]))
        self.assertEqual(dns["direct-nameserver"],
                         [url + "#DIRECT" for url in load_policy()["direct_resolvers"]])
        self.assertEqual(dns["fallback"], [])
        self.assertTrue(dns["direct-nameserver-follow-policy"])
        self.assertNotIn("proxy-groups", config)
        self.assertFalse(any("quickconnect" in item for item in dns["fake-ip-filter"]))

    def test_bootstrap_does_not_depend_on_the_tunnel(self):
        policy = load_policy()
        dns = mihomo_config(policy)["dns"]
        self.assertEqual(dns["proxy-server-nameserver"],
                         [url + "#DIRECT" for url in policy["direct_resolvers"]])
        general = "\n".join(shadowrocket_general(policy))
        self.assertIn("proxy-dns-server = " + ",".join(policy["bootstrap_resolvers"]), general)
        self.assertIn("dns-direct-system = false", general)
        self.assertIn("dns-fallback-system = false", general)
        self.assertIn("always-ip-address = true", general)

    def test_shadowrocket_uses_the_same_public_resolvers(self):
        policy = load_policy()
        general = dict(line.split(" = ", 1) for line in shadowrocket_general(policy)
                       if " = " in line)
        expected = ",".join(url + "#proxy" for url in policy["public_resolvers"])
        for key in ("dns-server", "fallback-dns-server"):
            self.assertEqual(general[key], expected)
        self.assertEqual(general["direct-dns-server"], ",".join(policy["direct_resolvers"]))
        self.assertIn("DST-PORT,53,REJECT", build())

    def test_public_names_cannot_use_local_exception(self):
        policy = copy.deepcopy(load_policy())
        policy["local_resolvers"]["google.com"] = "system"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.yaml"
            path.write_text(yaml.safe_dump(policy))
            with self.assertRaises(ValueError):
                load_policy(path)

    def test_plaintext_and_preselected_routes_are_rejected(self):
        for endpoint in ("8.8.8.8", "http://8.8.8.8/dns-query",
                         "https://8.8.8.8/dns-query#DIRECT"):
            policy = copy.deepcopy(load_policy())
            policy["public_resolvers"] = [endpoint]
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "policy.yaml"
                path.write_text(yaml.safe_dump(policy))
                with self.assertRaises(ValueError):
                    load_policy(path)

    def test_generated_artifacts_are_current(self):
        for path, expected in outputs().items():
            self.assertEqual(path.read_text(), expected, str(path))
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "shadowrocket/ruleproviders.conf").read_text(), build())

    def test_install_preserves_routing_and_is_repeatable(self):
        from build_dns import override_script
        shared = mihomo_config(load_policy())
        script = 'function main(config) { config.rules = ["MATCH,DIRECT"]; return config; }\n'
        first = attach_policy(script, override_script(shared))
        self.assertEqual(first, attach_policy(first, override_script(shared)))
        verge = attach_policy(script, override_script(shared), app_owns_tun=True)
        self.assertIn("return applyPersonalDnsPolicy(config, true);", verge)
        self.assertEqual(verge, attach_policy(verge, override_script(shared), app_owns_tun=True))
        old = {"rules": ["MATCH,DIRECT"], "dns": {"fallback": ["system"]},
               "proxy-groups": [{"name": "Final", "type": "select", "proxies": ["DIRECT"]},
                                {"name": "DNS-Proxy", "type": "select", "proxies": ["DIRECT"]}],
               "tun": {"route-exclude-address": ["100.64.0.0/10"]}}
        merged = merge_config(old, shared)
        self.assertEqual(merged["rules"], ["MATCH,DIRECT"])
        self.assertEqual(merged["tun"]["route-exclude-address"], ["100.64.0.0/10"])
        self.assertEqual(merged["dns"]["fallback"], [])
        self.assertEqual([g["name"] for g in merged["proxy-groups"]], ["Final"])
        self.assertEqual(merge_config(merged, shared), merged)


if __name__ == "__main__":
    unittest.main()
