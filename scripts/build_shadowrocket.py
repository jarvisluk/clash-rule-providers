#!/usr/bin/env python3
"""Build a Shadowrocket config from this repository's classical providers."""

from pathlib import Path

import yaml

from dns_policy import load_policy, shadowrocket_general, shadowrocket_hosts


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "rules" / "classical"
OUTPUT = ROOT / "shadowrocket" / "ruleproviders.conf"
UPDATE_URL = "https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/shadowrocket/ruleproviders.conf"

ROUTING = ROOT / "policy" / "routing.yaml"
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6"}


def load_routing():
    """Clash Verge order and policies, snapshotted by scripts/sync_clients.py."""
    routing = yaml.safe_load(ROUTING.read_text())
    providers = routing["providers"]
    policies = {item["name"]: item["policy"] for item in providers}
    policies["geoip-cn"] = routing["geoip-cn"]["policy"]
    policies["final"] = routing["final"]["policy"]
    if any(policy not in {"DIRECT", "PROXY", "REJECT"} for policy in policies.values()):
        raise ValueError(f"Unsupported policy in {ROUTING}")
    # Private-network lan moves first, so LAN DNS precedes the plaintext DNS
    # rejection; it does not overlap other providers.
    order = ["lan"] + [item["name"] for item in providers if item["name"] != "lan"]
    if len(order) != len(providers):
        raise ValueError(f"Duplicate or missing lan provider in {ROUTING}")
    return order, policies


def build() -> str:
    policy = load_policy()
    order, policies = load_routing()
    actual = {path.stem for path in PROVIDERS.glob("*.yaml")}
    if actual != set(order):
        raise ValueError(f"Provider mismatch: missing={actual - set(order)}, extra={set(order) - actual}; "
                         "add the provider to Clash Verge and run scripts/sync_clients.py")
    lines = [
        "# Generated from jarvisluk/clash-rule-providers rules/classical/*.yaml.",
        "# Node subscription is configured separately in Shadowrocket.",
        "[General]",
        f"update-url = {UPDATE_URL}",
        *shadowrocket_general(policy),
        "",
        "[Rule]",
    ]
    for index, name in enumerate(order):
        if index == 1:
            # Known public DNS endpoints are hijacked above; reject any other
            # plaintext DNS that remains. Private LAN destinations precede this.
            lines.append("DST-PORT,53,REJECT")
        lines.append(f"# {name}")
        source = yaml.safe_load((PROVIDERS / f"{name}.yaml").read_text())
        payload = source.get("payload") if isinstance(source, dict) else None
        if not isinstance(payload, list):
            raise ValueError(f"Missing payload list in {name}")
        for raw in payload:
            if not isinstance(raw, str):
                raise ValueError(f"Invalid rule in {name}: {raw!r}")
            fields = [field.strip() for field in raw.split(",")]
            cidr = fields[0] in {"IP-CIDR", "IP-CIDR6"}
            valid_options = len(fields) == 2 or (
                cidr and len(fields) == 3 and fields[2] == "no-resolve"
            )
            if fields[0] not in SUPPORTED or not valid_options or not fields[1]:
                raise ValueError(f"Unsupported rule in {name}: {raw}")
            fields.insert(2, policies[name])
            lines.append(",".join(fields))
    lines.extend([f"GEOIP,CN,{policies['geoip-cn']}", f"FINAL,{policies['final']}",
                  "", *shadowrocket_hosts(policy), ""])
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build())
    print(OUTPUT)
