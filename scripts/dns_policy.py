"""Translate the shared policy into client settings without system fallback."""

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_policy(path=None):
    policy = yaml.safe_load((path or ROOT / "policy/dns.yaml").read_text())
    if policy.get("version") != 1 or not isinstance(policy.get("ipv6"), bool):
        raise ValueError("unsupported DNS policy version or invalid ipv6")
    if policy.get("proxy_group") != "Final":
        raise ValueError("the simple policy uses the existing Final group")
    for key in ("public_resolvers", "direct_resolvers", "bootstrap_resolvers"):
        values = policy.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"{key} must be a nonempty resolver list")
        for value in values:
            url = urlsplit(value)
            if url.scheme != "https" or url.path != "/dns-query" or url.fragment or url.query:
                raise ValueError(f"only plain, certificate-verified DoH endpoints allowed: {value}")
            if not url.hostname:
                raise ValueError(f"missing DoH hostname: {value}")
            # Direct DoH hostnames are bootstrapped through encrypted IP endpoints.
            if key != "direct_resolvers":
                ipaddress.ip_address(url.hostname)
    for suffix, resolver in policy.get("local_resolvers", {}).items():
        if suffix not in {"lan", "local", "home.arpa", "ts.net"}:
            raise ValueError(f"public namespace cannot bypass proxy DNS: {suffix}")
        if resolver != "system" and not ipaddress.ip_address(resolver).is_private and resolver != "100.100.100.100":
            raise ValueError(f"local resolver must be private: {resolver}")
    for name in policy.get("direct_domains", []):
        if not isinstance(name, str) or not name.startswith("geosite:"):
            raise ValueError(f"direct_domains only accepts geosite categories: {name}")
    if ipaddress.ip_network(policy["fake_ip_range6"], strict=False).version != 6:
        raise ValueError("fake_ip_range6 must be an IPv6 network")
    for address in policy["shadowrocket_hijack"]:
        ipaddress.ip_address(address)
    return policy


def mihomo_config(policy):
    public = [f"{url}#{policy['proxy_group']}" for url in policy["public_resolvers"]]
    direct = [f"{url}#DIRECT" for url in policy["direct_resolvers"]]
    dns = {
        "enable": True,
        "ipv6": policy["ipv6"],
        "listen": "127.0.0.1:1053",
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "fake-ip-range6": policy["fake_ip_range6"],
        "fake-ip-filter-mode": "blacklist",
        "fake-ip-filter": policy["fake_ip_filter"],
        "default-nameserver": policy["bootstrap_resolvers"],
        "proxy-server-nameserver": direct.copy(),
        "nameserver": public,
        "direct-nameserver": direct,
        "direct-nameserver-follow-policy": True,
        "nameserver-policy": {
            **{f"+.{suffix}": resolver if resolver == "system" else f"{resolver}#DIRECT"
               for suffix, resolver in policy["local_resolvers"].items()},
            **{name: direct.copy() for name in policy.get("direct_domains", [])},
        },
        "fallback": [],
        "respect-rules": False,
        "prefer-h3": False,
        "use-hosts": True,
        "use-system-hosts": True,
    }
    return {
        "ipv6": policy["ipv6"],
        "dns": dns,
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
    direct = ",".join(policy["direct_resolvers"])
    return [
        "# Generated from policy/dns.yaml; default DNS uses the selected proxy, DIRECT uses domestic DoH.",
        f"dns-server = {public}",
        f"direct-dns-server = {direct}",
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
        # Shadowrocket's equivalent of fake-ip-filter; it has no "+." wildcard.
        "always-real-ip = " + ",".join(
            name for item in policy["fake_ip_filter"]
            for name in ((item[2:], "*." + item[2:]) if item.startswith("+.") else (item,))
        ),
    ]


def shadowrocket_hosts(policy):
    lines = ["[Host]", "localhost = 127.0.0.1"]
    for suffix, resolver in policy["local_resolvers"].items():
        lines.extend([f"{suffix} = server:{resolver}", f"*.{suffix} = server:{resolver}"])
    return lines
