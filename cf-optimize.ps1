<#
.SYNOPSIS  Cloudflare Pages 国内优选(CNAME方案) 一键配置 (PowerShell 版, Windows 原生)
.DESCRIPTION
  路线: 把 www.<zone> 的 DNS 改成 CNAME -> 优选域名(关代理), SSL 设 Full, 并尝试加根域->www 跳转。
  优选域名运营方会凭 SNI 反代回你的 <project>.pages.dev (需在对方后台把 www 绑到 pages.dev 一次)。
  默认 dry-run 预览; 加 -Apply 才真正修改。
  凭据: 优先读同目录 cf_token.txt; 没有则交互提示粘贴 (不会回显到文件)。
#>
[CmdletBinding()]
param(
    [string]$Zone       = "ovorain.com",
    [string]$Target     = "www.ovorain.com",
    [string]$Preferred  = "cfsaas.080112.xyz",
    [string]$PagesOrigin = "",
    [string]$TokenFile  = "cf_token.txt",
    [switch]$Apply
)

$API = "https://api.cloudflare.com/client/v4"
$ErrorActionPreference = "Stop"

function CF {
    param($Method, $Path, $BodyObj)
    $headers = @{ Authorization = "Bearer $script:token"; "Content-Type" = "application/json" }
    $url = $API + $Path
    $body = $null
    if ($BodyObj) { $body = ($BodyObj | ConvertTo-Json -Compress -Depth 10) }
    try {
        if ($BodyObj) {
            $r = Invoke-RestMethod -Method $Method -Uri $url -Headers $headers -Body $body -TimeoutSec 30
        } else {
            $r = Invoke-RestMethod -Method $Method -Uri $url -Headers $headers -TimeoutSec 30
        }
        return $r
    } catch {
        $status = $null
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        $msg = $_.ErrorDetails.Message
        if (-not $msg) { $msg = $_.Exception.Message }
        try { $o = $msg | ConvertFrom-Json; if ($status) { $o._http_status = $status }; return $o }
        catch { return @{ success = $false; errors = @(@{ code = $status; message = $msg }) } }
    }
}

Write-Host ("=" * 64)
Write-Host ("Cloudflare Pages 国内优选(CNAME方案)  " + $(if ($Apply) { "[执行模式]" } else { "[DRY-RUN 仅预览]" }))
Write-Host ("  zone        : " + $Zone)
Write-Host ("  目标主机名   : " + $Target)
Write-Host ("  优选 CNAME   : " + $Preferred)
Write-Host ("=" * 64)

# 1) 读 token
if (Test-Path $TokenFile) {
    $script:token = (Get-Content $TokenFile -Raw).Trim()
    Write-Host ("[OK] 已从 $TokenFile 读取 Token")
} else {
    $script:token = Read-Host -Prompt "请粘贴 Cloudflare API Token (cfat_...) "
    $script:token = $script:token.Trim()
}
if (-not $script:token) { Write-Error "未获取到 Token, 中止。"; exit 1 }

# 2) 探针校验 token
#    注意: /user/tokens/verify 是公开滥用防护端点, 对沙箱/云 IP 经常返 1000; 用 /zones 做真实能力兜底
$v = CF GET "/user/tokens/verify"
if ($v.success) {
    Write-Host "[OK] Token 有效 (verify 端点 OK)"
} else {
    Write-Host ("[WARN] /user/tokens/verify 被拒: " + ($v.errors | ConvertTo-Json -Compress))
    Write-Host "        通常是 Cloudflare 的滥用防护, 不代表 Token 无效, 继续 (用 /zones 做真实能力校验) ..."
}

# 3) 定位 zone
$zr = CF GET ("/zones?name=" + $Zone)
if (-not $zr.success -or -not $zr.result) { Write-Error ("✗ 找不到 zone $Zone : " + ($zr.errors | ConvertTo-Json -Compress)); exit 1 }
$zoneId = $zr.result[0].id
$acctId = $zr.result[0].account.id
Write-Host ("[OK] zone_id = $zoneId  account_id = $acctId")

# 4) 探测 pages.dev 源站
#    优先: 调用 Account Pages API 列出项目 (需要 Account:Pages:Read, 本 Token 大概率没有)
#    兜底: 用默认 PagesOrigin 参数 (默认 rain-portfolio.pages.dev), 也可用户用 -PagesOrigin 指定
$pages = $PagesOrigin
if (-not $pages) {
    try {
        $pp = CF GET ("/accounts/" + $acctId + "/pages/projects?per_page=100")
        if ($pp.success -and $pp.result -and $pp.result.Count -gt 0) {
            foreach ($p in $pp.result) {
                if ($p.subdomain) { $pages = $p.subdomain + ".pages.dev"; break }
            }
        } else {
            Write-Host ("[WARN] Pages 项目探测失败: " + ($pp.errors | ConvertTo-Json -Compress))
            Write-Host "        用默认 'rain-portfolio.pages.dev' (若不对, 用 -PagesOrigin 指定)"
        }
    } catch {
        Write-Host ("[WARN] Pages 项目探测异常: " + $_.Exception.Message)
    }
}
if (-not $pages) { $pages = "rain-portfolio.pages.dev" }
Write-Host ("[OK] Pages 源站(用于优选域名后台绑定) = $pages")

# 5) DNS: target -> 优选域名, 关代理
Write-Host ("`n[步骤] DNS: $Target CNAME -> $Preferred (代理关闭)")
if ($Apply) {
    $lst = CF GET ("/zones/$zoneId/dns_records?name=$Target&type=CNAME")
    $dnsBody = @{ type = "CNAME"; name = $Target; content = $Preferred; proxied = $false; ttl = 1 }
    if ($lst.result -and $lst.result.Count -gt 0) {
        $rid = $lst.result[0].id
        $r = CF PUT ("/zones/$zoneId/dns_records/$rid") $dnsBody
        Write-Host ("   [更新] CNAME id=$rid " + $(if ($r.success) { "成功" } else { ($r.errors | ConvertTo-Json -Compress) }))
    } else {
        $r = CF POST ("/zones/$zoneId/dns_records") $dnsBody
        Write-Host ("   [新建] CNAME " + $(if ($r.success) { "成功" } else { ($r.errors | ConvertTo-Json -Compress) }))
    }
} else {
    Write-Host ("   (dry-run) 将 upsert CNAME $Target -> $Preferred (proxied=False)")
}

# 6) SSL 模式 -> Full (探测式, Token 无 SSL:Edit 时跳过, Pages 默认 Full 已足够)
Write-Host ("`n[步骤] SSL/TLS 模式 -> Full (探测式, 无权限则跳过)")
if (-not $Apply) {
    Write-Host "   (dry-run) 将先 GET /zones/<id>/ssl 检测端点, 存在则 PATCH; Pages 项目通常跳过"
} else {
    $probe = CF GET "/zones/$zoneId/ssl"
    if ($probe.success) {
        $sr = CF PATCH "/zones/$zoneId/settings/ssl" @{ value = "full" }
        Write-Host ("   " + $(if ($sr.success) { "[OK] SSL 模式 = " + $sr.result.value } else { "[SKIP] " + ($sr.errors | ConvertTo-Json -Compress) }))
    } else {
        Write-Host "   [SKIP] 此 zone 不暴露 /ssl 路由 (典型 Pages 项目), 跳过 (Pages 默认 Full 已足够)"
    }
}

# 7) Redirect Rule (尽力)
Write-Host ("`n[步骤] Redirect Rule: $Zone -> https://$Target")
if ($Apply) {
    $rrBody = @{ rules = @(@{
        expression = "http.host eq ""$Zone"""
        description = "root-to-www (优选)"
        action = "redirect"
        action_parameters = @{ from_value = @{
            target_url = @{ value = "https://$Target" }
            status_code = 301
            preserve_query_string = $true
        } }
    }) }
    $rr = CF PUT ("/zones/$zoneId/rulesets/phases/http_request_dynamic_redirect/entrypoint") $rrBody
    if ($rr.success) { Write-Host "   [OK] 已创建/更新 Redirect Rule" }
    else {
        Write-Host ("   ⚠ 自动创建失败: " + ($rr.errors | ConvertTo-Json -Compress))
        Write-Host "   请手动在 CF 控制台 -> Rules -> Redirect Rules 添加:"
        Write-Host ("     表达式: http.host eq ""$Zone""  -> 301 到 https://$Target")
    }
} else {
    Write-Host "   (dry-run) 将 PUT redirect ruleset"
}

# 8) 第三方后台一次性绑定
Write-Host ("`n" + ("-" * 64))
Write-Host "⚠ 还需你点一下 (优选域名提供商后台, 无 API 可代劳):"
Write-Host ("   打开 https://$Preferred 的「添加域名/绑定」页, 填两项:")
Write-Host ("     域名(hostname) : $Target")
Write-Host ("     源站(origin)   : $pages")
Write-Host ("   提交后通常秒过, 证书由对方自动签发。")
Write-Host ("-" * 64)

Write-Host "`n完成后用 https://www.itdog.cn/http/https://$Target 验证国内是否已走优选 IP。"
Write-Host ("=" * 64)


