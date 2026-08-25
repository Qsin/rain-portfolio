# rain-portfolio 项目记忆（长期）

## 项目身份
- 个人作品集网站，作者：陈禹璋（C.Y.Z / Qsin），站点域名 ovorain.com。
- 内容方向：影视解说、信息流买量、口播种草、Vlog、AIGC 短剧、PR/AE 学习。
- 通过 **GitHub Pages** 部署（DNS 经 Cloudflare 代理加速），另有 Cloudflare Worker 项目 rain-portfolio（非站点本身）。git 历史含 cloudflare/workers-autoconfig 分支。

## 文件角色（重要）
- `index.html` = **当前线上运行的新版**（neo-brutal 风格，CSS+JS 全内联单文件）。`old-index.html` 是已冻结的历史版本，勿动。
- 结构为单文件：CSS + JS 全部内联，无外部 .css/.js 文件。
- 媒体资源：根目录放 mp4/jpg/png；AIGC 短剧在 `assets/drama-*/`（含 cover.jpg + video.mp4）；资产图在 `assets/资产/`（AI资产库画廊用，现仅 9 张：角色三视图/宴会大厅/暴风藏身屋/49投影/宴会大厅反打/asset_01~04，已删 02/03/07 并编号重排）。
- 旧版笔记文件 `个人网站播放问题.md` 为历史排障记录（影视解说路径、锚点 id 等问题，已解决）。

## 用户约束（必须遵守）
- **不要修改已写好的现有代码**；后续新增/完善功能时，必须保持原有样式、配色、布局。
- 新版设计系统变量（new-index.html `:root`）：--sky-blue #78B9FF、--sky-deep #5BA0E8、--coral-pink #FF5E4D、--neon-yellow #D4F63D、--klien-blue #1F40E6、--soft-beige #FFF4E6、--text-dark #111、--bg-light #F4F7FB。字体：Playfair Display / Dancing Script / Inter。

## Git 状态（截至 2026-08-25）
- remote: origin = https://github.com/Qsin/rain-portfolio.git（已就绪，无需装 git）。
- 当前在 **`main` 分支**（已合入并推送）。最新提交 `9709fe1`（feat: 全站禁止下载防护 + AI资产库文件夹卡片 + 资产重排）。
- 含多个 20~24MB 的 mp4，仓库体积大，GitHub Pages 构建较慢（约 2~5 分钟）。
- **推送须知（重要）**：本机环境变量 `HTTP_PROXY/HTTPS_PROXY=http://127.0.0.1:8502/` 但该代理不通，导致 git 直连失败。推送时必须先清空代理：`http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY="" ALL_PROXY="" git push ...`；或用 token 注入 URL：`git push https://<PAT>@github.com/Qsin/rain-portfolio.git main`。
- GitHub 凭据管理器（GCM）在本沙箱取不到 Windows 凭据，无法自动认证——推送需用户提供 PAT（repo 权限）。
- **中文路径文件绝不用 `git rm`/`git mv`**（会误删整目录）；改用 Python `os.remove`/`os.rename` + `git add -A`。

## 部署与 HTTPS（2026-08-25 实测）
- GitHub Pages API `GET /repos/Qsin/rain-portfolio/pages` 显示 `status`（building/built）、`cname=ovorain.com`、`https_enforced=false`（GH Pages 本身走 HTTP，HTTPS 由前面 Cloudflare 提供）。
- **线上「不安全」标志 ≠ 页面问题**：已验证 index.html 内无任何 `http://` 明文资源（视频走腾讯云 COS https、lucide 走 unpkg https），无 mixed content。根因在 **Cloudflare SSL/TLS 配置**（模式非 Full/证书异常/DNS 未代理）。需用户在 CF 控制台自查：SSL/TLS→Overview 加密模式设为 Full；DNS 中 ovorain.com 为橙色云（已代理）；开启 Always Use HTTPS。

## 域名与访问规范（2026-08-23 确认）
- **规范域名（canonical）：`ovorain.com`** —— 用户对外统一分享此地址，不主推 www。
- `www.ovorain.com` 仅作兜底：访问时 301 **一步跳回 `https://ovorain.com/`**（2026-08-24 已用 CF Single Redirect 规则实现，省掉原 http→https 多跳）。DNS 仍指向 qsin.github.io。
- 速度：两域名同走 GitHub Pages + Cloudflare 边缘，HTML 速度一致；视频均走腾讯云 COS CDN（同 index.html）。直接给 `ovorain.com` 少一次 301 跳转，体验最快。
- 结论：维持现状（ovorain.com 为主、www 兜底跳转）即最优，无需改动。
