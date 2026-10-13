"""Keep original routing choices; only Claude is protected from direct bypass."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_outbound_policy():
    policy = yaml.safe_load((ROOT / "policy/outbound.yaml").read_text())
    if policy.get("version") != 1 or not isinstance(policy.get("enabled"), bool):
        raise ValueError("unsupported outbound policy")
    if not isinstance(policy.get("protected_groups"), list):
        raise ValueError("protected_groups must be a list")
    return policy


def outbound_script():
    policy = load_outbound_policy()
    return "\n// Only the explicitly protected groups disallow direct outbounds.\n" + """function applyPersonalOutboundPolicy(config) {
  const policy = """ + json.dumps(policy, ensure_ascii=False) + """;
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
"""
