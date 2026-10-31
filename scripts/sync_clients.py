#!/usr/bin/env python3
"""Sync every client from Clash Verge, the reference client, in one run.

1. Snapshot Verge's rule order and current group policies into
   policy/routing.yaml (Shadowrocket is built from it, also in CI), mapping
   blackmatrix7 rule sets to their Shadowrocket lists.
2. Regenerate DNS and Shadowrocket outputs and run all validation.
3. Install FlClash's override script and the shared DNS into Verge and FlClash.
4. Export Clash Mi and Clash.app configurations into Verge's directory.

Local client files are backed up before they change. Shadowrocket only receives
the update after this repository is committed and pushed to main.
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

import yaml

from build_dns import override_script
from build_flclash_override import SERVICE_GROUPS, build as build_flclash
from dns_policy import load_policy, mihomo_config
from install_local_dns import attach_policy, install as install_dns

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "policy/routing.yaml"
VERGE = Path.home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"
FLCLASH = Path.home() / "Library/Application Support/com.follow.clash"
PERSONAL_URL = "/clash-rule-providers@main/rules/classical/"
PORTABLE = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6"}
BLACKMATRIX = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/"


def shadowrocket_rule_set(url):
    """Return the Shadowrocket type and URL of a public blackmatrix7 Clash rule
    set, or None for other sources, which Shadowrocket cannot read."""
    if not url.startswith(BLACKMATRIX + "Clash/"):
        return None
    folder, _, file = url[len(BLACKMATRIX + "Clash/"):].rpartition("/")
    base = f"{BLACKMATRIX}Shadowrocket/{folder}/"
    stem = Path(file).stem
    if stem.endswith("_Domain"):
        return "DOMAIN-SET", f"{base}{stem}.list"
    # X.yaml, X_Classical.yaml and X_IP.yaml are all covered by X.list.
    return "RULE-SET", f"{base}{folder.rpartition('/')[2]}.list"


def resolve(name, groups, selected, seen=()):
    """Return DIRECT, REJECT or PROXY for what a Verge policy currently reaches."""
    if name in ("DIRECT", "REJECT"):
        return name
    group = groups.get(name)
    # Nodes and automatic test groups never reach DIRECT.
    if not group or group["type"] != "select" or name in seen:
        return "PROXY"
    choices = group.get("proxies") or []
    current = selected.get(name)
    if current not in choices:
        current = choices[0] if choices else "REJECT"
    return resolve(current, groups, selected, (*seen, name))


def snapshot(verge):
    config = yaml.safe_load((verge / "clash-verge.yaml").read_text())
    registry = yaml.safe_load((verge / "profiles.yaml").read_text())
    active = next(item for item in registry["items"] if item["uid"] == registry["current"])
    selected = {item["name"]: item["now"] for item in active.get("selected") or []}
    groups = {group["name"]: group for group in config["proxy-groups"]}
    personal = {name: Path(urlsplit(provider["url"]).path).stem
                for name, provider in config["rule-providers"].items()
                if PERSONAL_URL in provider.get("url", "")}
    covered = set()
    for stem in set(personal.values()):
        for rule in yaml.safe_load((ROOT / "rules/classical" / f"{stem}.yaml").read_text())["payload"]:
            covered.add(tuple(rule.split(",")[:2]))

    def entry(group, **extra):
        return {**extra, "group": group, "policy": resolve(group, groups, selected)}

    providers, seen, inline, rule_sets, unmapped = [], set(), [], [], set()
    routing = {}
    for rule in config["rules"]:
        fields = rule.split(",")
        if fields[0] == "RULE-SET" and fields[1] in personal:
            if rule_sets:
                raise SystemExit(f"{rule} follows a third-party rule set; Shadowrocket lists "
                                 "personal providers first, so move it up in Clash Verge")
            stem = personal[fields[1]]
            if stem not in seen:
                seen.add(stem)
                providers.append(entry(fields[2], name=stem))
        elif fields[0] == "RULE-SET":
            mapped = shadowrocket_rule_set(config["rule-providers"][fields[1]].get("url", ""))
            if not mapped:
                unmapped.add(fields[1])
            elif mapped[1] not in (item["url"] for item in rule_sets):
                rule_sets.append(entry(fields[2], type=mapped[0], url=mapped[1]))
        elif fields[0] in PORTABLE and tuple(fields[:2]) not in covered:
            inline.append(rule)
        elif fields[0] == "GEOIP" and fields[1] == "CN":
            routing["geoip-cn"] = entry(fields[2])
        elif fields[0] == "MATCH":
            routing["final"] = entry(fields[1])
    return {"providers": providers, "rule-sets": rule_sets, **routing}, inline, sorted(unmapped)


def write_if_changed(path, content, backup=True):
    if path.exists() and path.read_text() == content:
        return
    if backup and path.exists():
        folder = path.parent / ".dns-policy-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir(parents=True)
        shutil.copy2(path, folder / path.name)
    path.write_text(content)
    print(f"updated {path}")


def share_service_groups(script, merged):
    """Return Merge All's script with Script.js's service-group table before its DNS block."""
    block = re.search(SERVICE_GROUPS, script, re.S)
    if not block:
        raise SystemExit("Script.js has no shared service groups block")
    head, marker, dns = re.sub(SERVICE_GROUPS, "", merged, flags=re.S).partition("// BEGIN SHARED DNS POLICY")
    return head.rstrip() + "\n\n" + block.group(0).rstrip() + "\n" + ("\n" + marker + dns if marker else "")


def run(*command, **kwargs):
    print("$", " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verge-dir", type=Path, default=VERGE)
    parser.add_argument("--flclash-dir", type=Path, default=FLCLASH)
    args = parser.parse_args()

    routing, inline, unmapped = snapshot(args.verge_dir)
    header = ("# Generated by scripts/sync_clients.py from Clash Verge; do not edit.\n"
              "# Personal providers, then Shadowrocket equivalents of third-party rule sets, in Verge\n"
              "# rule order, with the policy each group currently reaches.\n")
    write_if_changed(ROUTING, header + yaml.safe_dump(routing, allow_unicode=True, sort_keys=False),
                     backup=False)

    python = sys.executable
    run(python, "scripts/build_dns.py")
    run(python, "scripts/build_shadowrocket.py")
    run(python, "scripts/validate.py")
    run(python, "-m", "unittest", "discover", "-s", "tests")
    run("node", "tests/dns_override.test.js")

    profiles = args.verge_dir / "profiles"
    write_if_changed(profiles / "sviiDJPlf3BL.js",
                     share_service_groups((profiles / "Script.js").read_text(),
                                          (profiles / "sviiDJPlf3BL.js").read_text()))

    flclash = args.flclash_dir if args.flclash_dir.exists() else None
    if flclash:
        scripts = sorted((flclash / "scripts").glob("*.js"))
        if len(scripts) != 1:
            raise SystemExit(f"expected one FlClash override script, found {len(scripts)}")
        # Attach DNS exactly as install_dns would, so it leaves the script unchanged.
        helper = override_script(mihomo_config(load_policy()))
        write_if_changed(scripts[0], attach_policy(build_flclash(args.verge_dir), helper))
    install_dns(args.verge_dir, flclash)

    env = {**os.environ, "CLASH_VERGE_DIR": str(args.verge_dir)}
    run("ruby", "scripts/build_clash_mi_portable.rb", env=env)
    run("ruby", "scripts/build_clash_mi_subscription_override.rb", env=env)
    run("node", "scripts/build_clash_app_config.js", env=env)

    print(f"\nShadowrocket: {len(routing['providers'])} personal providers and "
          f"{len(routing['rule-sets'])} third-party rule sets synced.")
    if unmapped:
        print("Clash-only rule sets (no Shadowrocket equivalent): " + ", ".join(unmapped))
    if inline:
        print("Inline Clash rules missing from personal providers (Shadowrocket lacks them):")
        print("\n".join(f"  {rule}" for rule in inline))
    print("Reload Clash Verge and restart FlClash. Commit and push to publish Shadowrocket.")


if __name__ == "__main__":
    main()
