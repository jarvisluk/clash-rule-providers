#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
RULE_DIR = ROOT / "rules" / "classical"
RULE_TYPES_WITH_ONE_ARG = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "GEOIP"}
RULE_TYPES_WITH_CIDR = {"IP-CIDR", "IP-CIDR6", "SRC-IP-CIDR"}


def validate_rule(path: Path, rule: str) -> list[str]:
    errors: list[str] = []
    parts = [p.strip() for p in rule.split(",")]
    rule_type = parts[0] if parts else ""
    if not rule_type:
        return [f"{path}: empty rule"]
    if rule_type in RULE_TYPES_WITH_ONE_ARG and len(parts) != 2:
        errors.append(f"{path}: {rule!r} should have exactly 2 fields")
    elif rule_type in RULE_TYPES_WITH_CIDR and len(parts) not in (2, 3):
        errors.append(f"{path}: {rule!r} should have 2 or 3 fields")
    elif rule_type not in RULE_TYPES_WITH_ONE_ARG | RULE_TYPES_WITH_CIDR:
        if len(parts) < 2:
            errors.append(f"{path}: {rule!r} is too short")

    if len(parts) >= 3 and parts[-1] in {
        "DIRECT",
        "REJECT",
        "PROXY",
        "Final",
    }:
        errors.append(f"{path}: provider rule must not include policy target: {rule!r}")
    return errors


def main() -> int:
    errors: list[str] = []
    files = sorted(RULE_DIR.glob("*.yaml"))
    if not files:
        errors.append(f"no rule files found under {RULE_DIR}")

    for path in files:
        data = yaml.safe_load(path.read_text()) or {}
        payload = data.get("payload")
        if not isinstance(payload, list):
            errors.append(f"{path}: missing payload list")
            continue
        for item in payload:
            if not isinstance(item, str):
                errors.append(f"{path}: payload item is not a string: {item!r}")
                continue
            errors.extend(validate_rule(path, item))

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"validated {len(files)} rule files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
