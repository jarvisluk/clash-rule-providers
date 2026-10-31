#!/usr/bin/env python3
"""Generate Mihomo YAML and a shared Clash Verge / FlClash script."""

import json
from pathlib import Path

import yaml

from dns_policy import ROOT, load_policy, mihomo_config
from outbound_policy import outbound_script


def override_script(config):
    # No top-level const declarations: this can also be appended to routing scripts.
    return '''// BEGIN SHARED DNS POLICY (generated; edit policy/dns.yaml)
function applyPersonalDnsPolicy(config, appOwnsTun = false) {
  const shared = ''' + json.dumps(config, ensure_ascii=False, indent=2) + ''';
  // Clash Verge owns these fields; its GUI applies them after scripts run.
  // Clash Verge 2.5.6+ counts deleting an app-owned field as an override, so leave them untouched.
  if (!appOwnsTun) config.ipv6 = shared.ipv6;
  // Replace vendor DNS while leaving app-managed values to DNS override settings.
  const appDns = config.dns || {};
  // When Clash Verge DNS settings are on, every value it already set wins over the shared policy.
  config.dns = appOwnsTun ? { ...shared.dns, ...appDns } : { ...shared.dns };
  config["proxy-groups"] = (config["proxy-groups"] || [])
    .filter((group) => group.name !== "DNS-Proxy");
  // Clash Verge owns these fields in its GUI and discards script overrides.
  if (!appOwnsTun) config.tun = {...(config.tun || {}), ...shared.tun};
  return applyPersonalOutboundPolicy(config);
}
''' + outbound_script() + '// END SHARED DNS POLICY\n'


def outputs():
    config = mihomo_config(load_policy())
    yaml_text = "# Generated from policy/dns.yaml. Replace DNS; use the existing Final group.\n"
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
