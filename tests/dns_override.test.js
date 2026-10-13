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
console.log("Clash and FlClash overrides replace unsafe vendor DNS and preserve routing");
