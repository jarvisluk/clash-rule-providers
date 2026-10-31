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
    "fake-ip-range6": "fdfe:dcba:9876::1/64",
    "fake-ip-filter-mode": "blacklist",
    "fake-ip-filter": [
      "*.lan",
      "*.local",
      "*.arpa",
      "+.ts.net",
      "time.*.com",
      "ntp.*.com",
      "+.market.xiaomi.com",
      "localhost.ptlogin2.qq.com",
      "+.msftncsi.com",
      "+.msftconnecttest.com",
      "localhost",
      "+.stun.*.*",
      "+.stun.*.*.*"
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
      "+.ts.net": "100.100.100.100#DIRECT",
      "geosite:cn": [
        "https://dns.alidns.com/dns-query#DIRECT",
        "https://doh.pub/dns-query#DIRECT"
      ]
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

// Only the explicitly protected groups disallow direct outbounds.
function applyPersonalOutboundPolicy(config) {
  const policy = {"version": 1, "enabled": true, "protected_groups": ["🤖 Claude"]};
  if (!policy.enabled) return config;
  const protectedGroups = new Set(policy.protected_groups);
  const unsafe = new Set(["DIRECT", "COMPATIBLE", "PASS"]);
  for (const node of config.proxies || []) {
    if (["direct", "compatible", "pass"].includes((node.type || "").toLowerCase())) unsafe.add(node.name);
  }
  const groups = new Map((config["proxy-groups"] || []).map(group => [group.name, group]));
  function canBypass(name, seen = new Set()) {
    if (unsafe.has(name)) return true;
    if (!groups.has(name) || seen.has(name)) return false;
    const next = new Set(seen); next.add(name);
    return (groups.get(name).proxies || []).some(candidate => canBypass(candidate, next));
  }
  for (const name of protectedGroups) {
    const group = groups.get(name);
    if (!group) continue;
    group.proxies = (group.proxies || []).filter(candidate => !canBypass(candidate));
    group["exclude-type"] = Array.from(new Set([
      ...(group["exclude-type"] || "").split("|").filter(Boolean), "direct", "compatible", "pass"
    ])).join("|");
    if (!group.proxies.length && !(group.use || []).length) group.proxies = ["REJECT"];
  }
  const rules = [];
  for (const raw of config.rules || []) {
    if (raw.startsWith("AND,((NETWORK,UDP),(") && raw.endsWith(")),REJECT")) continue;
    rules.push(raw);
    const fields = raw.split(",");
    const targetIndex = fields.length - (fields[fields.length - 1] === "no-resolve" ? 2 : 1);
    if (targetIndex > 0 && protectedGroups.has(fields[targetIndex]) && fields[0] !== "MATCH") {
      // Reject a Claude match if its selected node lacks UDP, before a later
      // domestic/direct rule can accept it. Other services retain their rules.
      rules.push(`AND,((NETWORK,UDP),(${fields.slice(0, targetIndex).join(",")})),REJECT`);
    }
  }
  config.rules = rules;
  return config;
}
// END SHARED DNS POLICY

function main(config) {
  return applyPersonalDnsPolicy(config);
}
