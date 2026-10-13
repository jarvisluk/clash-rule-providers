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
    const beforeRouting = JSON.stringify([config.rules, config.proxies, config["proxy-providers"]]);
    context.main(config);
    assert.equal(JSON.stringify([config.rules, config.proxies, config["proxy-providers"]]), beforeRouting);
    assert.equal(config.dns.enable, true);
    assert(config.dns.nameserver.every(url => url.endsWith("#Final")));
    assert(config.dns["direct-nameserver"].every(url => url.endsWith("#DIRECT")));
    assert(!config.dns["fake-ip-filter"].some(item => item.includes("quickconnect")));
    assert(!("+.google.com" in config.dns["nameserver-policy"]));
    assert.equal(config.dns.fallback.length, 0);
    assert.equal(config.tun.enable, true);
    assert.equal(config.tun["strict-route"], true);
    assert.equal(config.tun["route-exclude-address"][0], "100.64.0.0/10");
    context.main(config);
    assert.equal(config["proxy-groups"].filter(g => g.name === "DNS-Proxy").length, 0);
    assert.equal(config["proxy-groups"].filter(g => g.name === "Final").length, 1);
  }
}
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../mihomo/dns-override.js"), "utf8"), context);
const original = {
  proxies: [{name: "real", type: "socks5"}, {name: "alias-direct", type: "direct"}],
  "proxy-providers": {subscription: {type: "http"}},
  "proxy-groups": [
    {name: "Final", type: "select", proxies: ["subscription", "DIRECT"]},
    {name: "My Servers", type: "select", proxies: ["DIRECT", "subscription"]},
    {name: "🍎 Apple", type: "select", proxies: ["DIRECT", "subscription"]},
    {name: "subscription", type: "url-test", proxies: ["real"]},
    {name: "🤖 Claude", type: "select", proxies: ["DIRECT", "alias-direct", "Final", "My Servers", "subscription", "real"]},
  ],
  rules: ["DOMAIN,claude.ai,🤖 Claude", "RULE-SET,Personal-Lan,DIRECT", "MATCH,Final"],
};
const othersBefore = JSON.stringify(original["proxy-groups"].filter(g => g.name !== "🤖 Claude"));
const providersBefore = JSON.stringify(original["proxy-providers"]);
context.main(original);
assert.equal(JSON.stringify(original["proxy-groups"].filter(g => g.name !== "🤖 Claude")), othersBefore);
assert.equal(JSON.stringify(original["proxy-providers"]), providersBefore);
assert.deepEqual(Array.from(original["proxy-groups"].find(g => g.name === "🤖 Claude").proxies), ["subscription", "real"]);
assert.deepEqual(Array.from(original.rules), ["DOMAIN,claude.ai,🤖 Claude",
  "AND,((NETWORK,UDP),(DOMAIN,claude.ai)),REJECT", "RULE-SET,Personal-Lan,DIRECT", "MATCH,Final"]);
const first = JSON.stringify(original);
context.main(original);
assert.equal(JSON.stringify(original), first);
const empty = context.main({"proxy-groups": [{name: "🤖 Claude", type: "select", proxies: ["DIRECT"]}]});
assert.deepEqual(Array.from(empty["proxy-groups"][0].proxies), ["REJECT"]);
console.log("DNS and Claude protection preserve every other group's original direct choices");
