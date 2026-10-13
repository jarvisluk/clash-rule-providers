// BEGIN SHARED DNS POLICY (generated; edit policy/dns.yaml)
function applyPersonalDnsPolicy(config, appOwnsTun = false) {
  const shared = {
  "ipv6": true,
  "dns": {
    "enable": true,
    "ipv6": true,
    "listen": "127.0.0.1:1053",
    "enhanced-mode": "fake-ip",
    "fake-ip-range": "198.18.0.1/16",
    "fake-ip-filter-mode": "blacklist",
    "fake-ip-filter": [
      "*.lan",
      "*.local",
      "*.arpa",
      "*.ts.net",
      "time.*.com",
      "ntp.*.com",
      "+.market.xiaomi.com",
      "localhost.ptlogin2.qq.com",
      "*.msftncsi.com",
      "www.msftconnecttest.com"
    ],
    "default-nameserver": [
      "https://223.5.5.5/dns-query",
      "https://223.6.6.6/dns-query"
    ],
    "proxy-server-nameserver": [
      "https://dns.alidns.com/dns-query#DIRECT",
      "https://doh.pub/dns-query#DIRECT"
    ],
    "nameserver": [
      "https://1.1.1.1/dns-query#Final",
      "https://8.8.8.8/dns-query#Final"
    ],
    "direct-nameserver": [
      "https://dns.alidns.com/dns-query#DIRECT",
      "https://doh.pub/dns-query#DIRECT"
    ],
    "direct-nameserver-follow-policy": true,
    "nameserver-policy": {
      "+.lan": "system",
      "+.local": "system",
      "+.home.arpa": "system",
      "+.ts.net": "100.100.100.100#DIRECT"
    },
    "fallback": [],
    "respect-rules": false,
    "prefer-h3": false,
    "use-hosts": true,
    "use-system-hosts": true
  },
  "tun": {
    "enable": true,
    "auto-route": true,
    "auto-detect-interface": true,
    "strict-route": true,
    "dns-hijack": [
      "any:53",
      "tcp://any:53"
    ]
  }
};
  config.ipv6 = shared.ipv6;
  // Replace the DNS object: vendor policies, fallbacks and filters must not survive.
  config.dns = shared.dns;
  config["proxy-groups"] = (config["proxy-groups"] || [])
    .filter((group) => group.name !== "DNS-Proxy");
  // Clash Verge owns these fields in its GUI and discards script overrides.
  if (!appOwnsTun) config.tun = {...(config.tun || {}), ...shared.tun};
  return config;
}
// END SHARED DNS POLICY

function main(config) {
  return applyPersonalDnsPolicy(config);
}
