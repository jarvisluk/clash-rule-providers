# Clash Rule Providers

Personal Mihomo/Clash rule-provider library.

This repository stores small, explicit rule sets that can be subscribed from
Mihomo/Clash with `rule-providers`. The files use `behavior: classical`, so
each payload item is a normal route rule without the final policy target.

## Provider URL

Use jsDelivr URLs. They avoid bootstrapping rule updates through the GitHub
route itself.

```yaml
https://cdn.jsdelivr.net/gh/jarvisluk/clash-rule-providers@main/rules/classical/spotify.yaml
```

## Example

See [examples/mihomo.yaml](examples/mihomo.yaml) for a minimal ready-to-copy
snippet.

Put these `RULE-SET` rules near the top of your Clash rules list. Mihomo
matches rules from top to bottom, so earlier custom providers override broad
third-party providers.

## Validate

```bash
python3 scripts/validate.py
```

The validator checks that every rule file has a `payload` list and that each
classical rule omits the final policy target.
