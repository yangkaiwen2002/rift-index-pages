# RIFT INDEX · GitHub Pages

[公开网站](https://yangkaiwen2002.github.io/rift-index-pages/)

英雄联盟选手查询与统计网站：历史档案、真实头像、六维雷达图、选手对比与赛事记录。索引覆盖 2011—2026，包含 2026 世界赛决赛。

本仓库包含公开网站的发布文件、数据同步脚本与自动部署流程；完整开发项目单独维护。网站无需登录，也不收集账号信息。

数据来源：[RiftWise](https://riftwise.gg/stats/data)，整合 Leaguepedia、Oracle’s Elixir。人物与战队图片来自原始资料和 Riot 官方赛事页面，英雄图标来自 Riot Data Dragon。具体来源与缺失数据说明见网站“数据说明”。

应用代码采用 MIT 许可，第三方图片及数据保留各自权利。本网站不隶属于 Riot Games、HLTV 或数据提供方。

## 比赛中心

- 2011—2026 年，26,894 场历史系列赛、725 项赛事；覆盖 LPL、LCK、LEC（含 EU LCS）、MSI、Worlds，以及 First Stand、LCS、LCP、PCS 等 16 个赛事体系。
- 可组合筛选年份、联赛、具体赛事和比赛状态，搜索战队，分页查看赛果；有逐局数据的比赛可进入计分板。
- 每天单独刷新 Riot LoL Esports 的已公布赛程（经 RiftWise 公开缓存），即使统计快照版本未变化也会抓取。赛程和历史赛果去重，保留比赛详情入口。
- 时间统一按北京时间 / 香港时间显示。未公布的赛程不编造；过期而未确认的比赛不冒充正在直播。历史记录可能缺少逐局统计或头像。

## 每日自动更新

- GitHub Actions 每天 **08:17（北京时间 / 香港时间，UTC 00:17）** 检查上游最新快照；GitHub 调度可能延迟。
- 新快照同步全历史索引、常用选手完整档案与逐局记录，并保留完整 2026 世界赛档案。上游版本未改变时核验现有完整数据并更新时间清单。
- 同步多赛事比赛归档与最新已公布赛程，按年份分片并校验摘要；页面显示赛程源的更新时间。
- 校验通过后提交数据，**同一次工作流直接部署到 GitHub Pages**，并以未登录请求核对公开数据的 SHA-256。无需个人访问令牌，也不依赖本地电脑。
- 抓取或校验失败时，不发布不完整数据。每日检查记录会提交到仓库；超过 48 小时无成功核验，页面显示更新延迟。
- 页面每次打开请求带唯一查询参数的更新清单，核对数据摘要；历史日志带版本号，打开中的页面每 5 分钟及重新聚焦时检查发布版本。
- 每日更新代表同步上游最新**已发布**数据，不代表比赛结束后实时更新。

[查看运行记录 / 手动更新](https://github.com/yangkaiwen2002/rift-index-pages/actions/workflows/daily-refresh.yml)。手动勾选 `force` 可重拉完整快照；普通日更自动跳过未变化的源版本。

GitHub Pages 的 Source 使用 **GitHub Actions**。新增或修改前端后推送到 `main` 也会先校验再发布。日更任务使用 GitHub 自带的仓库令牌提交数据后直接部署，避免机器人提交不触发下一次构建的问题。

## 用量与费用

日更只运行 Python、Node.js 校验与 GitHub Pages 部署，没有模型调用、ChatGPT 任务或付费数据 API，AI token 消耗为 **0**。不需要个人 API Key；提交使用 GitHub 自动提供且限于当前工作流的 `GITHUB_TOKEN`。

使用公开仓库的标准 `ubuntu-latest` 运行器（[GitHub 当前规则下免费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)），不使用收费的大型运行器。产物只保留 1 天；抓取任务最多 15 分钟，无变化的历史快照跳过重新下载。数据源可用性和 GitHub 调度时间仍受第三方服务影响。
