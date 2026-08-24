#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare Pages 国内优选 —— 第三方优选域名(CNAME)方案 一键配置
============================================================================
路线（针对 ovorain.com 这种 Cloudflare Pages 静态站、使用 bestcf 优选域名）：

  访客 → www.ovorain.com (CNAME→优选域名, 关代理)
       → 优选域名(cfsaas.080112.xyz) 拿到国内快 IP
       → 优选域名运营方的 Cloudflare for SaaS 凭 SNI=www.ovorain.com
         反代回你的 <project>.pages.dev

  ⚠️ 前置一步（需用户手动，无 API 可代劳）：
     在优选域名提供商后台把 www.ovorain.com 绑到你的 pages.dev 源站。
     本脚本会打印出要填的两个字段。

  本脚本在 Cloudflare 侧只做两件低风险操作：
   1) 把 www.ovorain.com 的 DNS 改成 CNAME → cfsaas.080112.xyz（关代理/小黄云）
   2) （尽力）加一条 Redirect Rule：ovorain.com → https://www.ovorain.com

依赖：仅 Python 标准库。默认 dry-run，加 --apply 才真改。

凭据安全：
  - Token 只从 --token-file 或环境变量 CF_API_TOKEN 读取，绝不打印。
  - 建议把 Token 写进文件（如 cf_token.txt）再 --token-file 传入，避免留在聊天记录。
  - Token 所需权限（在 Cloudflare 控制台创建）：
      Zone → DNS → Edit
      Zone → SSL/TLS → Edit   （用于把 SSL 模式设为 Full，作为兜底）
      Zone → Read
    作用域(Zone Resources)：Include → Specific zone → ovorain.com
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "https://api.cloudflare.com/client/v4"

# ------------------------- 可配置参数 -------------------------
DEFAULT_ZONE = "ovorain.com"
DEFAULT_TARGET = "www.ovorain.com"
DEFAULT_PREFERRED = "cfsaas.080112.xyz"   # VPS789 TOP10 #1，沙箱测到存活
# pages.dev 源站会先尝试用 API 自动探测；失败再用 --pages-origin 指定
# --------------------------------------------------------------


def get_token(args):
    if args.token_file:
        with open(args.token_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    t = os.environ.get("CF_API_TOKEN")
    if not t:
        sys.exit("✗ 未找到 Token。请用 --token-file <path> 传入（推荐，避免留在聊天里），"
                 "或临时设置环境变量 CF_API_TOKEN。")
    return t


def cf_call(token, method, path, body=None):
    url = API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            resp = json.loads(detail)
        except Exception:
            resp = {"success": False, "errors": [{"message": detail[:300]}]}
        resp["_http_status"] = e.code
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}
    return resp


def find_zone(token, zone_name):
    r = cf_call(token, "GET", "/zones?name=" + zone_name)
    if not r.get("success") or not r.get("result"):
        return None, r
    return r["result"][0]["id"], r["result"][0]


def detect_pages_origin(token, zone):
    acct = (zone.get("account") or {}).get("id")
    if not acct:
        return None
    r = cf_call(token, "GET", "/accounts/%s/pages/projects?per_page=100" % acct)
    if not r.get("success"):
        return None
    for p in r.get("result", []):
        domains = p.get("domains", []) or []
        sub = p.get("subdomain")  # 形如 rain-portfolio
        cand = (sub + ".pages.dev") if sub else None
        if any(d == DEFAULT_ZONE or d == DEFAULT_TARGET for d in domains):
            return cand
    # 退化：返回第一个项目的 subdomain
    if r.get("result"):
        sub = r["result"][0].get("subdomain")
        return (sub + ".pages.dev") if sub else None
    return None


def upsert_dns_cname(token, zone_id, name, content):
    lst = cf_call(token, "GET",
                  "/zones/%s/dns_records?name=%s&type=CNAME" % (zone_id, name))
    recs = lst.get("result", [])
    body = {"type": "CNAME", "name": name, "content": content,
            "proxied": False, "ttl": 1}
    if recs:
        rid = recs[0]["id"]
        r = cf_call(token, "PUT", "/zones/%s/dns_records/%s" % (zone_id, rid), body)
        return ("更新", rid, r)
    r = cf_call(token, "POST", "/zones/%s/dns_records" % zone_id, body)
    return ("新建", (r.get("result") or {}).get("id"), r)


def try_redirect_rule(token, zone_id, from_host, to_host):
    # 尽力而为：Cloudflare Redirect Rules 依赖 Rulesets API，权限不够时退化为手动提示
    ruleset_body = {
        "rules": [{
            "expression": 'http.host eq "%s"' % from_host,
            "description": "root-to-www (优选)",
            "action": "redirect",
            "action_parameters": {
                "from_value": {
                    "target_url": {"value": "https://%s" % to_host},
                    "status_code": 301,
                    "preserve_query_string": True,
                }
            },
        }],
    }
    r = cf_call(token, "PUT",
                "/zones/%s/rulesets/phases/http_request_dynamic_redirect/entrypoint" % zone_id,
                ruleset_body)
    return r


def main():
    p = argparse.ArgumentParser(description="Cloudflare Pages 国内优选(CNAME方案)配置")
    p.add_argument("--zone", default=DEFAULT_ZONE)
    p.add_argument("--target", default=DEFAULT_TARGET)
    p.add_argument("--preferred", default=DEFAULT_PREFERRED)
    p.add_argument("--pages-origin", default=None,
                   help="你的 Pages 默认域名，如 rain-portfolio.pages.dev（留空则自动探测）")
    p.add_argument("--token-file", default=None, help="存放 CF API Token 的文件路径")
    p.add_argument("--apply", action="store_true", help="真正执行修改（默认仅 dry-run）")
    args = p.parse_args()
    token = get_token(args)
    apply = args.apply

    print("=" * 64)
    print("Cloudflare Pages 国内优选(CNAME方案)  %s"
          % ("[执行模式]" if apply else "[DRY-RUN 仅预览]"))
    print("  zone        : %s" % args.zone)
    print("  目标主机名   : %s" % args.target)
    print("  优选 CNAME   : %s" % args.preferred)
    print("=" * 64)

    # 1) 校验 token
    v = cf_call(token, "GET", "/user/tokens/verify")
    if not v.get("success"):
        sys.exit("✗ Token 校验失败: %s" % v.get("errors"))
    print("[OK] Token 有效")

    # 2) 定位 zone
    zone_id, zone = find_zone(token, args.zone)
    if not zone_id:
        sys.exit("✗ 找不到 zone %s: %s" % (args.zone, zone.get("errors")))
    print("[OK] zone_id = %s (account=%s)" % (zone_id, (zone.get("account") or {}).get("id")))

    # 3) 探测 pages.dev 源站
    pages_origin = args.pages_origin or detect_pages_origin(token, zone)
    if not pages_origin:
        pages_origin = input("未能自动探测 pages.dev，请手动输入（如 rain-portfolio.pages.dev）：").strip()
    print("[OK] Pages 源站(用于优选域名后台绑定) = %s" % pages_origin)

    # 4) DNS：target -> 优选域名，关代理
    print("\n[步骤] DNS：%s CNAME -> %s (代理关闭)" % (args.target, args.preferred))
    if apply:
        action, rid, r = upsert_dns_cname(token, zone_id, args.target, args.preferred)
        print("   [%s] CNAME id=%s %s" % (action, rid, "成功" if r.get("success") else r.get("errors")))
    else:
        print("   (dry-run) 将 upsert CNAME %s -> %s (proxied=False)" % (args.target, args.preferred))

    # 5) SSL 模式 -> Full（兜底，确保回源 pages.dev 校验证书）
    print("\n[步骤] SSL/TLS 模式 -> Full")
    if apply:
        sr = cf_call(token, "PATCH", "/zones/%s/settings/ssl" % zone_id, {"value": "full"})
        print("   [OK] SSL 模式: %s" % (sr.get("result", {}).get("value")
                                        if sr.get("success") else sr.get("errors")))
    else:
        print("   (dry-run) 将 PATCH /settings/ssl {value:full}")

    # 6) Redirect Rule（尽力）
    print("\n[步骤] Redirect Rule：%s -> https://%s" % (args.zone, args.target))
    if apply:
        rr = try_redirect_rule(token, zone_id, args.zone, args.target)
        if rr.get("success"):
            print("   [OK] 已创建/更新 Redirect Rule")
        else:
            code = rr.get("_http_status")
            print("   ⚠ 自动创建失败(http=%s)：%s" % (code, rr.get("errors")))
            print("   请手动在 CF 控制台 -> Rules -> Redirect Rules 添加：")
            print('     表达式: http.host eq "%s"  → 301 到 https://%s'
                  % (args.zone, args.target))
    else:
        print("   (dry-run) 将 PUT redirect ruleset")

    # 7) 用户需在优选域名后台完成的一次性绑定
    print("\n" + "-" * 64)
    print("⚠ 还需你点一下（优选域名提供商后台，无 API 可代劳）：")
    print("   打开 https://%s 的「添加域名/绑定」页面，填两项：" % args.preferred)
    print("     域名(hostname) : %s" % args.target)
    print("     源站(origin)   : %s" % pages_origin)
    print("   提交后通常秒过，证书由对方自动签发。")
    print("-" * 64)

    print("\n完成后用 https://www.itdog.cn/http/https://www.ovorain.com 或本地")
    print("CloudflareSpeedTest 验证国内是否已走优选 IP。")
    print("=" * 64)


if __name__ == "__main__":
    main()
