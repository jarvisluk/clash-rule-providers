#!/usr/bin/env python3
"""Build a Shadowrocket config from this repository's classical providers."""

from pathlib import Path

import yaml

from dns_policy import load_policy, shadowrocket_general, shadowrocket_hosts


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "rules" / "classical"
OUTPUT = ROOT / "shadowrocket" / "ruleproviders.conf"
UPDATE_URL = "https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/shadowrocket/ruleproviders.conf"

# Match the current selections in the user's Clash Verge service groups.
DIRECT = {
    "servers", "lan", "chinamax", "bilibili", "apple", "onedrive",
    "microsoft", "learning", "gamedownload", "gamedownloadcn",
    "hoyoverse", "steam", "steamcn", "emby", "spotify", "hijacking",
}
# Clash Verge Script.js order. Only private-network lan moves up, so LAN DNS
# precedes the plaintext DNS rejection; it does not overlap other providers.
ORDER = [
    "servers", "lan", "spotify", "openai", "claude", "gemini", "cursor", "github",
    "telegram", "youtube", "onedrive", "paypal", "cryptocurrency", "microsoft",
    "google", "apple", "linkedin", "learning", "twitter", "bilibili", "tiktok",
    "netflix", "disney", "gamedownload", "gamedownloadcn", "hoyoverse", "steam",
    "steamcn", "emby", "globalmedia", "chinamax", "hijacking",
]
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6"}


def build() -> str:
    policy = load_policy()
    actual = {path.stem for path in PROVIDERS.glob("*.yaml")}
    if actual != set(ORDER):
        raise ValueError(f"Provider mismatch: missing={actual - set(ORDER)}, extra={set(ORDER) - actual}")
    lines = [
        "# Generated from jarvisluk/clash-rule-providers rules/classical/*.yaml.",
        "# Node subscription is configured separately in Shadowrocket.",
        "[General]",
        f"update-url = {UPDATE_URL}",
        *shadowrocket_general(policy),
        "",
        "[Rule]",
    ]
    for name in ORDER:
        if name == "spotify":
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
            fields.insert(2, "DIRECT" if name in DIRECT else "PROXY")
            lines.append(",".join(fields))
    lines.extend(["GEOIP,CN,DIRECT", "FINAL,PROXY", "", *shadowrocket_hosts(policy), ""])
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build())
    print(OUTPUT)
