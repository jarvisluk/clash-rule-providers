# Workspace rules

This repository is the single source of rules and DNS for three clients:
Clash Verge (Mihomo), FlClash and Shadowrocket. Clash Verge is the reference:
when clients disagree, follow Clash Verge's rules, order and group defaults.

## Every change must sync all three clients

Any change to `rules/classical/*.yaml`, `policy/*.yaml` or `scripts/*.py` must
update every client in the same commit:

1. Regenerate all outputs:
   ```bash
   python3 scripts/build_dns.py
   python3 scripts/build_shadowrocket.py
   ```
2. Validate:
   ```bash
   python3 scripts/validate.py
   python3 -m unittest discover -s tests
   node tests/dns_override.test.js
   ```
3. Check Shadowrocket still matches Clash Verge:
   - `ORDER` in `scripts/build_shadowrocket.py` follows the `Personal-*` order in
     Clash Verge `profiles/Script.js`.
   - `DIRECT` in the same file matches the DIRECT/proxy choice actually selected
     in each Clash Verge service group (`profiles.yaml` `selected`), not merely
     the group's first entry. Spotify is DIRECT; PayPal and LinkedIn are PROXY.
4. Apply locally to Clash Verge and FlClash (backups go to `.dns-policy-backups`):
   ```bash
   python3 scripts/install_local_dns.py \
     --verge-dir "$HOME/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev" \
     --flclash-dir "$HOME/Library/Application Support/com.follow.clash"
   ```

Never edit DNS directly in local Clash Verge / FlClash scripts. Edit
`policy/dns.yaml` and regenerate, otherwise the next install overwrites it.
Add new site rules to a `rules/classical` provider rather than inline Clash
rules, so Shadowrocket receives them too.
