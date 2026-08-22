# rain-portfolio 项目记忆（长期）

## 项目身份
- 个人作品集网站，作者：陈禹璋（C.Y.Z / Qsin），站点域名 ovorain.com。
- 内容方向：影视解说、信息流买量、口播种草、Vlog、AIGC 短剧、PR/AE 学习。
- 通过 **Cloudflare Pages** 部署（git 历史含 cloudflare/workers-autoconfig 分支）。

## 文件角色（重要）
- `index.html` = 旧版网站（靛蓝/青色渐变风格，已完成）。
- `new-index.html` = 新版（开发中，neo-brutal 风格），**做好后替换掉旧版**。
- 结构为单文件：CSS + JS 全部内联，无外部 .css/.js 文件。
- 媒体资源：根目录放 mp4/jpg/png；AIGC 短剧在 `assets/drama-*/`（含 cover.jpg + video.mp4）；资产图在 `assets/资产/`。
- 旧版笔记文件 `个人网站播放问题.md` 为历史排障记录（影视解说路径、锚点 id 等问题，已解决）。

## 用户约束（必须遵守）
- **不要修改已写好的现有代码**；后续新增/完善功能时，必须保持原有样式、配色、布局。
- 新版设计系统变量（new-index.html `:root`）：--sky-blue #78B9FF、--sky-deep #5BA0E8、--coral-pink #FF5E4D、--neon-yellow #D4F63D、--klien-blue #1F40E6、--soft-beige #FFF4E6、--text-dark #111、--bg-light #F4F7FB。字体：Playfair Display / Dancing Script / Inter。

## Git 状态（截至 2026-08-21）
- remote: origin = https://github.com/Qsin/rain-portfolio.git（已就绪，无需装 git）。
- 当前 HEAD **detached** 于 tag `v1.0-current`（commit 9db4aaf，含完整 new-index.html 工作），**未合入 main、也未推送**。
- `main` == `origin/main` == 43122fe（同步，0 ahead/0 behind）。
- 另有 tag `v2.0-portfolio`。
- 已跟踪 29 个文件，含多个 20~24MB 的 mp4（仓库体积较大，首次推送会上传较多数据）。
- 推送前需先归位到 main（或新建分支）再把 9db4aaf 的工作并入，再 `git push`。
