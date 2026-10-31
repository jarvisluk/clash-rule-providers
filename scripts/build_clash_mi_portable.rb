#!/usr/bin/env ruby

require "fileutils"
require "yaml"

ROOT = ENV.fetch("CLASH_VERGE_DIR", File.join(Dir.home, "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"))
SOURCE = File.join(ROOT, "clash-verge.yaml")
PROFILE_REGISTRY = File.join(ROOT, "profiles.yaml")
dns_only = ARGV.delete("--dns-only")
OUTPUT = ARGV.fetch(0, File.join(ROOT, "exports", "Clash-Mi-iPhone-20260916.yaml"))

def sync_dns(config)
  dns = YAML.load_file(File.expand_path("../mihomo/dns.yaml", __dir__)).fetch("dns")
  dns["listen"] = "127.0.0.1:1053"
  dns.delete("fallback-filter") if Array(dns["fallback"]).empty?
  config["dns"] = dns
  config["ipv6"] = YAML.load_file(File.join(ROOT, "config.yaml")).fetch("ipv6", false)
end

if dns_only
  config = YAML.load_file(OUTPUT)
  sync_dns(config)
  File.write(OUTPUT, YAML.dump(config))
  puts "output=#{OUTPUT}"
  puts "dns_only=true"
  exit
end

config = YAML.load_file(SOURCE)
provider_names = {}
all_proxies = []

config.fetch("proxy-providers", {}).each do |provider_name, provider|
  source_path = File.expand_path(provider.fetch("path"), ROOT)
  source = YAML.load_file(source_path)
  prefix = provider.dig("override", "additional-prefix").to_s
  exclude = provider["exclude-filter"] && Regexp.new(provider["exclude-filter"])
  rename_map = source.fetch("proxies", []).to_h do |proxy|
    old_name = proxy.fetch("name").to_s
    [old_name, "#{prefix}#{old_name}"]
  end

  names = []
  source.fetch("proxies", []).each do |raw_proxy|
    old_name = raw_proxy.fetch("name").to_s
    next if exclude&.match?(old_name)

    proxy = Marshal.load(Marshal.dump(raw_proxy))
    proxy["name"] = rename_map.fetch(old_name)
    %w[dialer-proxy detour].each do |key|
      proxy[key] = rename_map.fetch(proxy[key], proxy[key]) if proxy[key]
    end
    if proxy["proxies"].is_a?(Array)
      proxy["proxies"] = proxy["proxies"].map { |name| rename_map.fetch(name, name) }
    end
    names << proxy["name"]
    all_proxies << proxy
  end
  provider_names[provider_name] = names
end

config["proxies"] = all_proxies
config.fetch("proxy-groups", []).each do |group|
  uses = group.delete("use")
  next unless uses

  include_pattern = group.delete("filter")
  exclude_pattern = group.delete("exclude-filter")
  include_regex = include_pattern && Regexp.new(include_pattern)
  exclude_regex = exclude_pattern && Regexp.new(exclude_pattern)
  expanded = uses.flat_map { |provider_name| provider_names.fetch(provider_name, []) }
  expanded.select! { |name| include_regex.match?(name) } if include_regex
  expanded.reject! { |name| exclude_regex.match?(name) } if exclude_regex
  group["proxies"] = (Array(group["proxies"]) + expanded).uniq
end
config.delete("proxy-providers")

config.fetch("rule-providers", {}).each_value do |provider|
  provider["proxy"] = "Final" if provider["type"] == "http"
end
config.fetch("rule-providers", {})["CN_IP"] = {
  "type" => "http",
  "behavior" => "ipcidr",
  "format" => "mrs",
  "interval" => 86_400,
  "url" => "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/cn.mrs",
  "path" => "./ruleset/cn_ip.mrs",
  "proxy" => "Final"
}
config["rules"] = config.fetch("rules", []).map do |rule|
  if rule.start_with?("GEOIP,CN,")
    "RULE-SET,CN_IP,#{rule.split(",", 3).fetch(2)},no-resolve"
  else
    rule
  end
end

registry = YAML.load_file(PROFILE_REGISTRY)
active_profile = registry.fetch("items", []).find { |item| item["uid"] == registry["current"] }
selections = Array(active_profile && active_profile["selected"]).to_h do |selection|
  [selection["name"], selection["now"]]
end
config.fetch("proxy-groups", []).each do |group|
  selected = selections[group["name"]]
  choices = group["proxies"]
  next unless selected && choices.is_a?(Array) && choices.include?(selected)

  group["proxies"] = [selected] + choices.reject { |choice| choice == selected }
end

%w[external-controller external-controller-unix secret port socks-port redir-port tproxy-port].each do |key|
  config.delete(key)
end
config["mixed-port"] = 7890
config["allow-lan"] = false
sync_dns(config)

FileUtils.mkdir_p(File.dirname(OUTPUT))
File.write(OUTPUT, YAML.dump(config))

puts "output=#{OUTPUT}"
puts "nodes=#{all_proxies.length}"
puts "groups=#{config.fetch("proxy-groups", []).length}"
puts "rule_providers=#{config.fetch("rule-providers", {}).length}"
puts "rules=#{config.fetch("rules", []).length}"
