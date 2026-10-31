#!/usr/bin/env ruby

require "fileutils"
require "yaml"

ROOT = ENV.fetch("CLASH_VERGE_DIR", File.join(Dir.home, "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev"))
SOURCE = File.join(ROOT, "clash-verge.yaml")
OUTPUT = ARGV.fetch(0, File.join(ROOT, "overrides", "Clash-Mi-My-Rules.yaml"))

config = YAML.load_file(SOURCE)
provider_group_names = config.fetch("proxy-providers", {}).map do |name, provider|
  prefix = provider.dig("override", "additional-prefix").to_s.strip
  prefix.empty? ? name : "#{prefix} #{name}"
end

groups = config.fetch("proxy-groups", []).reject do |group|
  provider_group_names.include?(group["name"])
end

groups.each do |group|
  group.delete("use")
  if %w[自动选择 🇭🇰\ 香港 🇯🇵\ 日本 🇺🇸\ 美国 🇸🇬\ 新加坡 🇹🇼\ 台湾 🌍\ 其他地区 🤖\ AI\ 支持地区].include?(group["name"])
    group["include-all"] = true
  end
  if group["proxies"].is_a?(Array)
    group["proxies"] = group["proxies"].reject { |name| provider_group_names.include?(name) }
  end
end

regions = ["自动选择", "🇭🇰 香港", "🇯🇵 日本", "🇺🇸 美国", "🇸🇬 新加坡", "🇹🇼 台湾", "🌍 其他地区", "🤖 AI 支持地区", "DIRECT"]
first = groups.find { |group| group["name"] == "🌍一级代理" }
second = groups.find { |group| group["name"] == "🌐二级代理" }
third = groups.find { |group| group["name"] == "🛡️三级代理" }

first["proxies"] = regions
first["include-all"] = true
second["proxies"] = (["🌍一级代理"] + regions).uniq
second["include-all"] = true
third["proxies"] = (["🌐二级代理", "🌍一级代理"] + regions).uniq
third["include-all"] = true

rule_providers = Marshal.load(Marshal.dump(config.fetch("rule-providers", {})))
rule_providers.each_value do |provider|
  provider["proxy"] = "Final" if provider["type"] == "http"
  next unless provider["type"] == "file"

  provider["payload"] = YAML.load_file(File.expand_path(provider.fetch("path"), ROOT)).fetch("payload")
  provider["type"] = "inline"
  provider.delete("path")
end
rule_providers["CN_IP"] = {
  "type" => "http",
  "behavior" => "ipcidr",
  "format" => "mrs",
  "interval" => 86_400,
  "url" => "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/cn.mrs",
  "path" => "./ruleset/cn_ip.mrs",
  "proxy" => "Final"
}

rules = config.fetch("rules", []).map do |rule|
  if rule.start_with?("GEOIP,CN,")
    "RULE-SET,CN_IP,#{rule.split(",", 3).fetch(2)},no-resolve"
  else
    rule
  end
end

dns = YAML.load_file(File.expand_path("../mihomo/dns.yaml", __dir__)).fetch("dns")
dns["listen"] = "127.0.0.1:1053"
dns.delete("fallback-filter") if Array(dns["fallback"]).empty?

override = {
  "ipv6" => YAML.load_file(File.join(ROOT, "config.yaml")).fetch("ipv6", false),
  "dns" => dns,
  "proxy-groups" => groups,
  "rule-providers" => rule_providers,
  "rules" => rules
}

FileUtils.mkdir_p(File.dirname(OUTPUT))
File.write(OUTPUT, YAML.dump(override))

puts "output=#{OUTPUT}"
puts "groups=#{groups.length}"
puts "rule_providers=#{rule_providers.length}"
puts "rules=#{rules.length}"
