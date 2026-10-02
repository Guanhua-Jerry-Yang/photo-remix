# photo-remix

一个 [Claude Code](https://claude.com/claude-code) Skill：把旅行/生活照片批量做成 AI 二创图，并生成可离线查看、每张一键下载的 HTML 报告。

A Claude Code skill that classifies a photo, picks matching image-to-image prompts, renders them in parallel with Codex CLI's `image_gen`, and builds a self-contained HTML gallery with one-click downloads.

## 它做什么

1. **预处理**：自动裁掉手机相机水印条，读 EXIF
2. **分类筛选**：Claude 看图判断 单人 / 合照 / 风景 / 城市 / 室内 / 美食，以及是否偏色、有路人、天空灰
3. **路由**：按类型只挑适合的 prompt（默认前 6 条）；合照自动跳过只认单人的 prompt；无人物照片跳过人物类
4. **出图**：Codex CLI `image_gen` 4 路并发，失败重试，可断点续跑，区分额度/登录类故障
5. **报告**：图片内嵌的 `report.html`，单张下载、放大下载、全部打包 ZIP
6. **改字**：像素级替换生成图里的名字/短文案，其余像素不变
7. **导入**：从公众号文章抓取新的 prompt 入库

## Prompt 库

| id | 玩法 | 适合 |
|---|---|---|
| 01 | 杂志双区：黑白网点+主色线描 | 人像/合照 |
| 02 | 漫画登机牌 | 单人 |
| 03 | 美式复古潮流贴纸海报 | 人像/合照 |
| 04 | 复古 JRPG NPC + 游戏 UI | 人像/合照 |
| 05 | 3D 城市地图定位界面（参数：城市） | 单人 |
| 06 | 极简独立漫画人物 + 幻想小生物 | 人像/合照 |
| 07 | 上下拼接：原图 × 鼠标乱画 | 人像 |
| 08 | 苹果相册九宫格抓拍 | 单人 |
| 09 | iPhone 主屏幕小组件 | 人像/合照 |
| 10 | 上下海报：原照主体 + 黑线小人 | 通用 |
| 11 | 珐琅冰箱贴 | 人像/合照 |
| 12 | 悬浮手绘画板 UI 涂鸦 | 通用 |
| 13 | 手账热敏小票 | 通用 |
| 14 | 粗蜡笔手绘叠加 | 风景/城市 |
| 15 | ins 风手写文字涂鸦 | 通用 |
| 16 | Photo × Line Art 实景延伸线稿 | 风景/通用 |
| 17 | 剪影编辑设计海报 | 风景/城市 |
| 18 | 复古旅行日志丝网印（参数：城市英文、年份） | 室内/店铺 |
| 19 | 手托微缩折叠绘本 | 美食/通用 |
| 20 | 邮票手账拼贴 | 美食 |
| 21 | Haley Tippmann 画中画 | 美食/通用 |
| R1–R4 | 修复：肤色校正 / 去路人 / 调光线 / 换蓝天 | 检测到问题时 |

实测评分与已知问题见 [`references/test-notes.md`](references/test-notes.md)。

## 依赖

- macOS（用到 `sips` 和系统自带的冬青黑体）
- [Claude Code](https://claude.com/claude-code)
- [Codex CLI](https://github.com/openai/codex) ≥ 0.150，已登录且 `image_generation` 功能可用；默认模型 `gpt-5.5`，可用 `PHOTO_REMIX_MODEL` 覆盖
- Python 3：`pip install pillow numpy beautifulsoup4 lxml`

## 安装

```bash
git clone https://github.com/<you>/photo-remix ~/.claude/skills/photo-remix
```
然后在 Claude Code 里说「把这张照片做成几种玩法 /path/to/photo.jpg」。

## 隐私

照片会经 Codex 发送给 OpenAI 生成图片。报告只写在本地，Skill 不会上传或发布。本仓库不含任何照片或生成结果。

## Prompt 来源

- 01–21：公众号「卡尔的AI沃茨」《国庆相册里舍不得删的废片，我找到了25种新玩法来拯救它们！》（2026-09），文中说明多数来自腾讯元宝 AI 创作内置模板。版权归原作者；本仓库做了少量适配（地点/年份参数化、修正碎片拼接丢失的英文空格、02 无垫图说明）。
- R1–R4：原文只描述效果、未给出 prompt，为本仓库自写。
