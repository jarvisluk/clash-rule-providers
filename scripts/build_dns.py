#!/usr/bin/env python3
"""Generate Mihomo YAML and a shared Clash Verge / FlClash script."""

import json
from pathlib import Path

import yaml

from dns_policy import ROOT, GROUP, load_policy, mihomo_config


def override_script(config):
    # No top-level const declarations: this can also be appended to routing scripts.
    return '''// BEGIN SHARED DNS POLICY (generated; edit policy/dns.yaml)
function applyPersonalDnsPolicy(config) {
  const shared = ''' + json.dumps(config, ensure_ascii=False, indent=2) + ''';
  config.ipv6 = shared.ipv6;
  // Replace the DNS object: vendor policies, fallbacks and filters must not survive.
  config.dns = shared.dns;
  config["proxy-groups"] = (config["proxy-groups"] || [])
    .filter((group) => group.name !== "''' + GROUP + '''")
    .concat(shared["proxy-groups"]);
  config.tun = {...(config.tun || {}), ...shared.tun};
  return config;
}
// END SHARED DNS POLICY
'''


def outputs():
    config = mihomo_config(load_policy())
    yaml_text = "# Generated from policy/dns.yaml. Merge DNS by replacement and append DNS-Proxy.\n"
    yaml_text += yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    script = override_script(config)
    entry = "\nfunction main(config) {\n  return applyPersonalDnsPolicy(config);\n}\n"
    return {
        ROOT / "mihomo/dns.yaml": yaml_text,
        ROOT / "mihomo/dns-override.js": script + entry,
        ROOT / "flclash/dns-override.js": script + entry,
    }


if __name__ == "__main__":
    for path, content in outputs().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        print(path.relative_to(ROOT))
