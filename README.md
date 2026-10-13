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

## Shared DNS policy: Clash Verge, Shadowrocket and FlClash

Edit **[policy/dns.yaml](policy/dns.yaml)** to change DNS for all clients. The
existing workflow generates these artifacts together:

| Client | Generated configuration |
| --- | --- |
| Shadowrocket | [shadowrocket/ruleproviders.conf](shadowrocket/ruleproviders.conf), rules plus DNS |
| Clash Verge / Mihomo | [mihomo/dns-override.js](mihomo/dns-override.js), DNS-only script |
| FlClash | [flclash/dns-override.js](flclash/dns-override.js), same DNS-only script |
| Other Mihomo clients | [mihomo/dns.yaml](mihomo/dns.yaml), configuration fragment |

All public destination lookups, including DIRECT websites, use Cloudflare and
Google **DoH through a proxy**. No plaintext or system DNS is configured as a
public fallback. If the DNS proxy is unavailable, public resolution fails
instead of switching to direct DNS. Website routing rules still decide whether
the subsequent website connection is direct or proxied.

Mihomo clients use a separate `DNS-Proxy` selector containing subscription
nodes, excluding Direct/Compatible adapters. Its empty fallback is `REJECT`;
it never references `Final` or another service group that can select DIRECT.
Choose a working node in `DNS-Proxy` after installing. Shadowrocket uses its
selected default node (`#proxy`) and `always-ip-address` to resolve proxy
destinations through the configured DoH instead of leaving resolution to the
proxy server. This matches the resolver policy; node choices are local and
are not synchronized between clients.

Only proxy node names use AliDNS DoH directly before a tunnel is available.
DoH resolver URLs use IP addresses with normal TLS verification, avoiding
system bootstrap resolution. This is an explicit exception: AliDNS can see
node names and the device's source IP. It does not resolve public website names.
Never add public namespaces to `local_resolvers`. Only `lan`, `local`,
`home.arpa` and Tailscale `ts.net` may use private/system resolvers. Tailscale
MagicDNS requires Tailscale to be connected; `.local` discovery can also use
mDNS. These private namespace queries are intentionally local.

Clash/FlClash overrides replace the entire subscription DNS object to remove
vendor fallbacks and domain policies, append the dedicated DNS group and enable
TUN with TCP/UDP port 53 interception and strict routing. They retain existing
TUN route exclusions for private networks. Shadowrocket explicitly configures
encrypted backup DNS, disables system fallback, intercepts common public DNS
addresses and rejects remaining plaintext port 53 traffic after LAN rules.

### Install and update

Clash Verge: apply the generated DNS script **after** service routing/group
scripts. If using the YAML fragment, replace the entire `dns` object and append
`DNS-Proxy` to existing groups; importing the fragment as a complete subscription
would omit your nodes and website rules. Disable independent GUI DNS overrides
or give them the identical generated settings.

FlClash: use the generated script as a profile override. If your profile already
uses a routing script, append the `applyPersonalDnsPolicy` helper to that script
and call it on the final config; don't replace your routing script with the
DNS-only script. Disable FlClash's independent **Override DNS** setting so its
GUI settings cannot overwrite the script. Keep VPN/TUN capture enabled in the
client; operating-system VPN permissions cannot be granted by a config file.
FlClash applies its GUI TUN/IPv6 settings after profile scripts: enable DNS
Hijacking and IPv6 in VPN settings, disable Allow Bypass, and enable TUN and
Auto Route on desktop. The macOS installer updates these preferences too.

Remote script download URLs:

```text
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/mihomo/dns-override.js
https://raw.githubusercontent.com/jarvisluk/clash-rule-providers/main/flclash/dns-override.js
```

The workflow publishes changes; it cannot force a client to fetch them.
Shadowrocket refreshes its existing remote configuration. Clash/FlClash local
scripts must be refreshed/reimported, or updated using the installer below.
It preserves existing routing scripts, replaces DNS, and backs up each changed
file in a `.dns-policy-backups` directory. Reload the client afterwards.

```bash
git pull --ff-only
python3 scripts/build_dns.py
python3 scripts/build_shadowrocket.py
python3 scripts/install_local_dns.py \
  --verge-dir "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev" \
  --flclash-dir "$HOME/Library/Application Support/com.follow.clash"
```

### Verification and limits

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests
node tests/dns_override.test.js
```

Reconnect and run an extended test at <https://www.dnsleaktest.com/> on each
device, on Wi-Fi and cellular networks where applicable. Check that public test
queries reach the configured resolvers, then temporarily choose an unavailable
DNS proxy: a new uncached public lookup should fail, with no ISP fallback.
Use a packet capture on the physical interface for stronger verification.

This policy governs DNS handled by the client. Application-owned DoH/DoT,
OS VPN exclusions, disabled VPN/TUN capture, and overlapping VPNs must be
checked on each device. A successful browser test does not prove every app is
covered. IPv6 remains enabled and must be captured alongside IPv4.

References: [Mihomo DNS](https://wiki.metacubex.one/config/dns/),
[Mihomo proxy groups](https://wiki.metacubex.one/config/proxy-groups/),
[Shadowrocket settings](https://github.com/LOWERTOP/Shadowrocket/wiki).
