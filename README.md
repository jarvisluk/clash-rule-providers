# Personal rules and DNS policy

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
32 classical providers with their Clash default policies, and does not contain
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

## Shared DNS policy: Clash Verge, Shadowrocket and FlClash

Edit **[policy/dns.yaml](policy/dns.yaml)** to change DNS for all clients.
The workflow generates the following files and validates them together:

| Client | Generated configuration |
| --- | --- |
| Shadowrocket | [shadowrocket/ruleproviders.conf](shadowrocket/ruleproviders.conf), DNS plus personal rules |
| Clash Verge / Mihomo | [mihomo/dns-override.js](mihomo/dns-override.js), DNS-only script |
| FlClash | [flclash/dns-override.js](flclash/dns-override.js), identical DNS-only script |
| Other Mihomo clients | [mihomo/dns.yaml](mihomo/dns.yaml), DNS fragment |

The simple policy is:

- Default lookup: Cloudflare / Google DoH through the existing **Final** group.
- DIRECT destination lookup: AliDNS / DNSPod DoH directly.
- Proxy node lookup: domestic DoH directly, avoiding a tunnel bootstrap loop.
- No public system/plaintext fallback and no QuickConnect Fake-IP exclusions.
- No separate DNS proxy group. Existing website rules and node groups are preserved.

Choose a working **proxy** in Final on Clash/FlClash. Selecting DIRECT in Final
also sends default DNS directly; there is no independent DNS selector guarding
that choice. Direct website queries reaching domestic DNS are intentional under
this policy. Local LAN / mDNS / Tailscale namespaces retain their private DNS
exceptions. IPv6 remains enabled and should be captured alongside IPv4.

Shadowrocket uses its selected default node (`#proxy`) as the equivalent of
Clash's Final for default DNS, and domestic DoH for `direct-dns-server`.
`always-ip-address` requests client-side resolution so proxy destinations use
the specified DNS. Encrypted fallback uses the selected proxy; system fallback
is disabled. Node names have a separate encrypted bootstrap resolver. Resolver
policy is shared; runtime node selections are independent on each device.

### Install and update

Shadowrocket: update and select the existing remote configuration:

```text
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/shadowrocket/ruleproviders.conf
```

Clash Verge / FlClash: apply the DNS helper after any service routing script.
The helper replaces vendor DNS settings and removes the old DNS proxy group.
Use a profile that already defines Final. The YAML fragment is not a complete
subscription: replace the DNS object without replacing node/service groups.
If an existing profile uses a routing script, append `applyPersonalDnsPolicy`
to that script and call it on the final config rather than discarding routing.

```text
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/mihomo/dns-override.js
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/flclash/dns-override.js
```

The workflow publishes files; clients must fetch/reimport them. For existing
local macOS routing scripts, pull the repository and run the installer:

```bash
git pull --ff-only
python3 scripts/install_local_dns.py \
  --verge-dir "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev" \
  --flclash-dir "$HOME/Library/Application Support/com.follow.clash"
```

Changed files are backed up in `.dns-policy-backups`. Reload Clash Verge and
restart FlClash afterwards. Keep FlClash's independent Override DNS disabled;
the macOS installer also synchronizes its persistent DNS/TUN/IPv6 settings.
Clash Verge owns TUN fields in its GUI: enable Strict Route and DNS Hijacking
(`any:53,tcp://any:53`) there. The installed Verge routing helper leaves TUN
fields to the application to avoid discarded-setting notifications.

TUN/VPN capture must remain enabled. OS permissions cannot be granted by a
configuration file. App-owned encrypted DNS and OS VPN exclusions require
verification on each device; a browser test cannot prove every app is covered.

### Verify and regenerate locally

Install PyYAML==6.0.3, then run:

```bash
python3 scripts/build_dns.py
python3 scripts/build_shadowrocket.py
python3 scripts/validate.py
python3 -m unittest discover -s tests
node tests/dns_override.test.js
```

After refreshing each client, run an extended test at
<https://www.dnsleaktest.com/>. Test Wi-Fi/cellular where applicable and check
physical-interface packets for unexpected plaintext DNS. QuickConnect can use
Fake-IP; public entry-point success does not verify NAS login or relay sessions.

References: [Mihomo DNS](https://wiki.metacubex.one/config/dns/),
[Shadowrocket settings](https://github.com/LOWERTOP/Shadowrocket/wiki).

## Claude-only direct restriction

[policy/outbound.yaml](policy/outbound.yaml) protects only **🤖 Claude**.
All other groups retain their original choices, including DIRECT in **My Servers**,
**Final** and the other service groups. Existing subscription and region groups
retain their original construction; DIRECT is not added to automatic test groups.

The generated helper removes direct nodes/aliases and groups that can reach DIRECT
from Claude's choices, without modifying those shared groups. A matching UDP
rejection follows each Claude rule so an unsupported UDP node cannot fall through
to a later direct rule. Website rules for other services and LAN are preserved.

Default DNS still uses Final. Choosing DIRECT in Final therefore also makes the
default DoH connection direct; this is an intentional available selection under
the restored policy. No system firewall has been installed or enabled here.
