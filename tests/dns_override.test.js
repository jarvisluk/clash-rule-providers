const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

for (const client of ["mihomo", "flclash"]) {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(path.join(__dirname, "..", client, "dns-override.js"), "utf8"), context);
  for (const providerOnly of [false, true]) {
    const config = {
      proxies: providerOnly ? [] : [{name: "node", type: "socks5"}],
      "proxy-providers": providerOnly ? {subscription: {type: "http"}} : {},
      "proxy-groups": [{name: "Final", type: "select", proxies: ["DIRECT"]},
                       {name: "DNS-Proxy", type: "select", proxies: ["DIRECT"]}],
      dns: {enable: false, nameserver: ["system"], fallback: ["223.5.5.5"],
            "nameserver-policy": {"+.google.com": "system"}},
      tun: {"route-exclude-address": ["100.64.0.0/10"]},
      rules: ["MATCH,Final"],
    };
    const beforeNodes = JSON.stringify(config.proxies);
    context.main(config);
    assert.equal(JSON.stringify(config.proxies), beforeNodes);
    assert(config.rules.includes("MATCH,Final"));
    assert.equal(config.rules[config.rules.length - 1], "MATCH,REJECT");
    assert(!config["proxy-groups"].find(g => g.name === "Final").proxies.includes("DIRECT"));
    assert.equal(config.dns.enable, true);
    assert(config.dns.nameserver.every(url => url.endsWith("#Final")));
    assert(config.dns["direct-nameserver"].every(url => url.endsWith("#DIRECT")));
    assert(!config.dns["fake-ip-filter"].some(item => item.includes("quickconnect")));
    assert(!("+.google.com" in config.dns["nameserver-policy"]));
    assert.equal(config.dns.fallback.length, 0);
    assert.equal(config.tun.enable, true);
    assert.equal(config.tun["strict-route"], true);
    assert.equal(config.tun["route-exclude-address"][0], "100.64.0.0/10");
    const first = JSON.stringify(config);
    context.main(config);
    assert.equal(JSON.stringify(config), first, "overrides must be idempotent");
    assert.equal(config["proxy-groups"].filter(g => g.name === "DNS-Proxy").length, 0);
    assert.equal(config["proxy-groups"].filter(g => g.name === "Final").length, 1);
  }
}

const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../mihomo/dns-override.js"), "utf8"), context);
const unsafe = {
  proxies: [{name: "real", type: "socks5"}, {name: "bypass", type: "direct"}],
  "proxy-providers": {sub: {type: "http", "exclude-type": "ss"}},
  "proxy-groups": [
    {name: "Final", type: "select", proxies: ["nested", "🇨🇳 ChinaWebsites", "bypass", "DIRECT"]},
    {name: "nested", type: "fallback", proxies: ["DIRECT", "real"]},
    {name: "empty", type: "select", proxies: ["DIRECT"]},
    {name: "🇨🇳 ChinaWebsites", type: "select", proxies: ["DIRECT", "real"]},
  ],
  rules: ["DOMAIN,foreign.example,nested", "RULE-SET,Personal-Lan,DIRECT", "GEOIP,CN,DIRECT", "MATCH,DIRECT"],
};
context.main(unsafe);
assert.deepEqual(Array.from(unsafe["proxy-groups"].find(g => g.name === "Final").proxies), ["nested", "REJECT"]);
assert.deepEqual(Array.from(unsafe["proxy-groups"].find(g => g.name === "empty").proxies), ["REJECT"]);
assert(unsafe["proxy-groups"].find(g => g.name === "🇨🇳 ChinaWebsites").proxies.includes("DIRECT"));
assert.equal(unsafe["proxy-providers"].sub["exclude-type"], "ss|direct|compatible|pass");
const guard = "AND,((NETWORK,UDP),(DOMAIN,foreign.example)),REJECT";
assert.equal(unsafe.rules[unsafe.rules.indexOf("DOMAIN,foreign.example,nested") + 1], guard);
assert(unsafe.rules.indexOf(guard) < unsafe.rules.indexOf("GEOIP,CN,DIRECT"));
assert(unsafe.rules.includes("RULE-SET,Personal-Lan,Final"), "a LAN-named provider can contain public hosts");
assert(unsafe.rules.includes("MATCH,Final"));
assert(!unsafe.rules.includes("MATCH,DIRECT"));
assert(!unsafe.rules.some(rule => rule.includes("198.18.0.0/16,DIRECT")), "fake IPs are not LAN destinations");
const blank = context.main({});
assert.deepEqual(Array.from(blank["proxy-groups"][0].proxies), ["REJECT"]);
assert.equal(blank.rules[blank.rules.length - 1], "MATCH,REJECT");
console.log("DNS, nested direct bypasses, empty groups and unsupported UDP fail closed");
