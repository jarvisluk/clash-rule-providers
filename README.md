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

## Shadowrocket

Import [shadowrocket/ruleproviders.conf](shadowrocket/ruleproviders.conf) as a
separate Shadowrocket configuration. It contains the current rules from all
31 classical providers with their Clash default policies, and does not contain
proxy nodes. Keep the existing node subscription in Shadowrocket.

### Automatic sync

After changes to `rules/classical/*.yaml` are pushed to `main`, the
[Sync Shadowrocket workflow](.github/workflows/sync-shadowrocket.yml) validates
the providers, regenerates the configuration, and commits it automatically.
No generated commit is created when the output is unchanged. Pull requests
are validated without publishing. The workflow can also be run manually
from GitHub Actions.

Clash and Shadowrocket share the repository's personal rules as their source.
Local-only Clash edits, runtime policy selections, and third-party rule
providers are not synchronized by this workflow. Unsupported Shadowrocket
rule types or new provider categories fail validation and must be added to
the generator explicitly.

On the phone, add or update this URL as a remote configuration and select it:

```text
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/shadowrocket/ruleproviders.conf
```

The generated `[General]` section includes this address as `update-url`.
In Shadowrocket's Settings, enable automatic background updates for
**Configuration** and set the interval to **1 day**. In iOS Settings > General
> Background App Refresh, allow Shadowrocket to refresh. Updating the old
remote configuration once installs the new `update-url`; if it was imported
as a local file, add it from the URL above instead.

Publication happens after the GitHub workflow completes; the phone fetches
updates on its next scheduled refresh, not immediately. iOS may delay or
prevent background tasks, especially after force-quitting the app or rebooting.
To fetch immediately, use the configuration's **Update Configuration** action.
Remote configuration updates replace local edits to that configuration.
Keep node subscriptions separate as before.

See the [Shadowrocket manual's automatic update instructions](https://github.com/LOWERTOP/Shadowrocket#自动更新).
For local generation, install `PyYAML==6.0.3` and run
`python3 scripts/build_shadowrocket.py`.
