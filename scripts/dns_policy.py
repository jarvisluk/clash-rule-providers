"""Translate the shared policy into client settings without system fallback."""

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
GROUP = "DNS-Proxy"


def load_policy(path=None):
    policy = yaml.safe_load((path or ROOT / "policy/dns.yaml").read_text())
    if policy.get("version") != 1 or not isinstance(policy.get("ipv6"), bool):
        raise ValueError("unsupported DNS policy version or invalid ipv6")
    for key in ("public_resolvers", "bootstrap_resolvers"):
        values = policy.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"{key} must be a nonempty resolver list")
        for value in values:
            url = urlsplit(value)
            if url.scheme != "https" or url.path != "/dns-query" or url.fragment or url.query:
                raise ValueError(f"only plain, certificate-verified DoH endpoints allowed: {value}")
            # IP endpoints avoid bootstrap DNS queries about the resolver itself.
            ipaddress.ip_address(url.hostname)
    for suffix, resolver in policy.get("local_resolvers", {}).items():
        if suffix not in {"lan", "local", "home.arpa", "ts.net"}:
            raise ValueError(f"public namespace cannot bypass proxy DNS: {suffix}")
        if resolver != "system" and not ipaddress.ip_address(resolver).is_private and resolver != "100.100.100.100":
            raise ValueError(f"local resolver must be private: {resolver}")
    for address in policy["shadowrocket_hijack"]:
        ipaddress.ip_address(address)
    return policy


def mihomo_config(policy):
    public = [f"{url}#{GROUP}" for url in policy["public_resolvers"]]
    bootstrap = [f"{url}#DIRECT" for url in policy["bootstrap_resolvers"]]
    dns = {
        "enable": True,
        "ipv6": policy["ipv6"],
        "listen": "127.0.0.1:1053",
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "fake-ip-filter-mode": "blacklist",
        "fake-ip-filter": policy["fake_ip_filter"],
        "default-nameserver": policy["bootstrap_resolvers"],
        "proxy-server-nameserver": bootstrap,
        "nameserver": public,
        "direct-nameserver": public,
        "direct-nameserver-follow-policy": True,
        "nameserver-policy": {
            f"+.{suffix}": resolver if resolver == "system" else f"{resolver}#DIRECT"
            for suffix, resolver in policy["local_resolvers"].items()
        },
        "fallback": [],
        "respect-rules": False,
        "prefer-h3": False,
        "use-hosts": True,
        "use-system-hosts": True,
    }
    group = {
        "name": GROUP,
        "type": "select",
        "include-all": True,
        "exclude-type": "Direct|Reject|Compatible|Pass|Dns",
        "exclude-filter": "(?i)剩余流量|套餐到期|距离下次|最新网址|remain:|used:|reset in:",
        # Mihomo otherwise uses COMPATIBLE (which can become DIRECT) for empty groups.
        "empty-fallback": "REJECT",
    }
    return {
        "ipv6": policy["ipv6"],
        "dns": dns,
        "proxy-groups": [group],
        "tun": {
            "enable": True,
            "auto-route": True,
            "auto-detect-interface": True,
            "strict-route": True,
            "dns-hijack": ["any:53", "tcp://any:53"],
        },
    }


def shadowrocket_general(policy):
    public = ",".join(f"{url}#proxy" for url in policy["public_resolvers"])
    return [
        "# Generated from policy/dns.yaml; public queries require a working proxy.",
        f"dns-server = {public}",
        f"direct-dns-server = {public}",
        f"fallback-dns-server = {public}",
        "proxy-dns-server = " + ",".join(policy["bootstrap_resolvers"]),
        "dns-direct-system = false",
        "dns-fallback-system = false",
        "dns-direct-fallback-proxy = true",
        # Resolve proxy destinations through the same DoH endpoints, not node DNS.
        "always-ip-address = true",
        "use-local-host-item-for-proxy = true",
        "private-ip-answer = true",
        "udp-policy-not-supported-behaviour = REJECT",
        f"ipv6 = {str(policy['ipv6']).lower()}",
        "prefer-ipv6 = false",
        "hijack-dns = " + ",".join(f"{ip}:53" for ip in policy["shadowrocket_hijack"]),
    ]


def shadowrocket_hosts(policy):
    lines = ["[Host]", "localhost = 127.0.0.1"]
    for suffix, resolver in policy["local_resolvers"].items():
        lines.extend([f"{suffix} = server:{resolver}", f"*.{suffix} = server:{resolver}"])
    return lines
