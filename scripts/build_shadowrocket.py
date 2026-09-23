#!/usr/bin/env python3
"""Build a Shadowrocket config from this repository's classical providers."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "rules" / "classical"
OUTPUT = ROOT / "shadowrocket" / "ruleproviders.conf"

# Match the initial selections in the user's Clash service groups.
DIRECT = {
    "lan", "chinamax", "bilibili", "apple", "onedrive", "paypal",
    "microsoft", "linkedin", "learning", "gamedownload", "gamedownloadcn",
    "hoyoverse", "steam", "steamcn", "emby", "spotify", "hijacking",
}
ORDER = [
    "lan", "openai", "claude", "gemini", "cursor", "github", "telegram",
    "youtube", "cryptocurrency", "google", "tiktok", "netflix", "disney",
    "globalmedia", "twitter", "spotify", "onedrive", "paypal", "microsoft",
    "apple", "linkedin", "learning", "bilibili", "gamedownload",
    "gamedownloadcn", "hoyoverse", "steam", "steamcn", "emby", "chinamax",
    "hijacking",
]
SUPPORTED = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6"}


def build() -> str:
    actual = {path.stem for path in PROVIDERS.glob("*.yaml")}
    if actual != set(ORDER):
        raise ValueError(f"Provider mismatch: missing={actual - set(ORDER)}, extra={set(ORDER) - actual}")
    lines = [
        "# Generated from jarvisluk/clash-rule-providers rules/classical/*.yaml.",
        "# Node subscription is configured separately in Shadowrocket.",
        "[General]",
        "",
        "[Rule]",
    ]
    for name in ORDER:
        lines.append(f"# {name}")
        source = (PROVIDERS / f"{name}.yaml").read_text()
        for raw in source.splitlines():
            if not raw.startswith("  - "):
                continue
            fields = raw[4:].split(",")
            if fields[0] not in SUPPORTED or len(fields) < 2:
                raise ValueError(f"Unsupported rule in {name}: {raw}")
            fields.insert(2, "DIRECT" if name in DIRECT else "PROXY")
            lines.append(",".join(fields))
    lines.extend(["GEOIP,CN,DIRECT", "FINAL,PROXY", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(build())
    print(OUTPUT)
