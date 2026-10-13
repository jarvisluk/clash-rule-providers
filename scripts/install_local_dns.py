#!/usr/bin/env python3
"""Install generated DNS into existing local clients with timestamped backups.

Run after pulling repository updates. Never modifies subscriptions or node secrets.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

import yaml

from build_dns import override_script
from dns_policy import load_policy, mihomo_config

START = "// BEGIN SHARED DNS POLICY"
END = "// END SHARED DNS POLICY"


def attach_policy(script, helper):
    script = re.sub(r"// BEGIN SHARED DNS POLICY.*?// END SHARED DNS POLICY\n?",
                    "", script, flags=re.S)
    script = script.replace("return applyPersonalDnsPolicy(config);", "return config;")
    if "return config;" not in script:
        raise ValueError("routing script has no known return point; refusing to overwrite")
    return script.replace("return config;", "return applyPersonalDnsPolicy(config);").rstrip() + "\n\n" + helper


def merge_config(config, shared):
    config["dns"] = shared["dns"]
    config["ipv6"] = shared["ipv6"]
    config["proxy-groups"] = [g for g in config.get("proxy-groups", [])
                              if g["name"] != "DNS-Proxy"] + shared["proxy-groups"]
    config["tun"] = {**config.get("tun", {}), **shared["tun"]}
    return config


def install(verge, flclash=None):
    shared = mihomo_config(load_policy())
    helper = override_script(shared)
    writes = {}
    if verge:
        for name in ("Script.js", "sviiDJPlf3BL.js"):
            path = verge / "profiles" / name
            if path.exists():
                writes[path] = attach_policy(path.read_text(), helper)
        path = verge / "dns_config.yaml"
        if path.exists():
            data = yaml.safe_load(path.read_text())
            data["dns"] = shared["dns"]
            writes[path] = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        for name in ("config.yaml", "clash-verge.yaml"):
            path = verge / name
            if path.exists():
                data = merge_config(yaml.safe_load(path.read_text()), shared)
                writes[path] = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    if flclash:
        # Update existing scripts, preserving the user's service groups and providers.
        for path in sorted((flclash / "scripts").glob("*.js")):
            writes[path] = attach_policy(path.read_text(), helper)
        path = flclash / "config.yaml"
        if path.exists():
            data = merge_config(yaml.safe_load(path.read_text()), shared)
            writes[path] = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    for path, content in writes.items():
        if path.read_text() == content:
            continue
        # Back up before each mutation, retaining all subscription and node data locally.
        backup = path.parent / ".dns-policy-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup.mkdir(parents=True)
        shutil.copy2(path, backup / path.name)
        path.write_text(content)
        print(f"updated {path}")
    if flclash and sys.platform == "darwin":
        # FlClash patches TUN and IPv6 after running the profile script.
        # Its own persistent settings therefore have to agree with the policy.
        prefs = Path.home() / "Library/Preferences/com.follow.clash.plist"
        if prefs.exists() and flclash.name == "com.follow.clash":
            saved = plistlib.loads(prefs.read_bytes())
            settings = json.loads(saved["flutter.config"])
            before = json.dumps(settings, ensure_ascii=False)
            settings["overrideDns"] = False
            patch = settings.setdefault("patchClashConfig", {})
            patch["ipv6"] = shared["ipv6"]
            patch["dns"] = shared["dns"]
            tun = patch.setdefault("tun", {})
            tun.update(shared["tun"])
            vpn = settings.setdefault("vpnProps", {})
            vpn.update({"enable": True, "ipv6": shared["ipv6"],
                        "dnsHijacking": True, "allowBypass": False})
            after = json.dumps(settings, ensure_ascii=False)
            if before != after:
                backup = flclash / ".dns-policy-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup.mkdir(parents=True)
                shutil.copy2(prefs, backup / prefs.name)
                # Use CFPreferences through defaults, avoiding its cached plist being overwritten.
                subprocess.run(["defaults", "write", "com.follow.clash", "flutter.config",
                                "-string", after], check=True)
                print("updated FlClash DNS/TUN preferences; restart FlClash to apply")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verge-dir", type=Path)
    parser.add_argument("--flclash-dir", type=Path)
    args = parser.parse_args()
    if not args.verge_dir and not args.flclash_dir:
        parser.error("specify at least one client directory")
    install(args.verge_dir, args.flclash_dir)
