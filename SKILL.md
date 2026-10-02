---
name: photo-remix
description: 把旅行/生活照片批量做成 AI 二创图（杂志拼贴、复古贴纸海报、JRPG 游戏画面、iPhone 桌面、热敏小票、手账、绘本、剪影海报等 21 种玩法 + 肤色/去路人/调光/换蓝天 4 种修复）。先看图分类（单人/合照/风景/城市/室内/美食），只挑适合的 prompt，用 Codex CLI 的图像生成并发出图，最后生成一个可离线查看、每张一键下载的 report.html。触发场景：「把这张照片做成几种玩法」「照片二创」「AI 修图试一下这些 prompt」「photo remix」「朋友圈出片」「给照片套模板」；也用于「把这篇公众号里的修图 prompt 导入库」和「把生成图里的名字/文字改成 X」。不负责：视频、纯文生图（无原图）、商业修图精修。
---

# photo-remix

照片 → 看图分类 → 按路由挑 prompt → Codex `image_gen` 并发出图 → 逐张点评 → 自包含 report.html。

## 目录约定

- Skill：`prompts/`（每条一个 .txt + `index.json` 元数据与路由）、`scripts/`、`references/`
- 每次运行一个 run 目录：`~/Pictures/photo-remix/<YYYYMMDD-HHMM>_<简短标签>/`
  - `photos/pNN/{source.jpg, strip.jpg, meta.json, notes.json, outputs/<id>.png, outputs/<id>.recaption.txt}`
  - `plan.json`、`jobs/`、`jobs.txt`、`logs/`、`report.html`
- run 目录是交付物，不自动清理；`jobs/`、`logs/` 是中间产物

## 隐私

照片多半有本人和家人：**report.html 只在本地打开，不发 Artifact、不上传云盘或图床**，除非用户明确要求。Codex 出图会把照片发给 OpenAI，这是本 skill 的固有前提，首次使用时告诉用户一句。

## 流程

### 1. 预处理
```bash
python3 ~/.claude/skills/photo-remix/scripts/preprocess.py --run <run> <照片1> [<照片2> ...]
```
自动裁掉底部相机水印条（存成 `strip.jpg`）。**Read 一下每张 `strip.jpg`**：确认确实是水印条（截图/白底文档会误判，误判就加 `--no-crop` 重跑该张）；水印里常有地点和时间，记下来作为参数。

### 2. 分类筛选（Claude 自己看 `source.jpg`）
对每张照片判断并写入 `<run>/plan.json`：

| 字段 | 取值 |
|---|---|
| `type` | `person_single` 单人像 · `group` 合照 2+ 人 · `scenery` 自然风景 · `city` 城市远景/建筑 · `interior` 室内/店铺 · `food` 美食 |
| `persons` | 画面主体人数（路人不算）；0 表示没有人物 |
| `repairs` | 只在看到问题时加：`R1` 肤色被灯光染色 · `R2` 有明显路人 · `R3` 阴天/逆光发灰 · `R4` 天空灰白或过曝 |
| `mode` | `top`（默认，路由前 6 条）· `all`（用户说「全跑」）· `ids`（用户点名，配 `"ids": [...]`）；加 `"no_filter": true` 可绕过下方硬规则（仅限用户明确要全量对比时） |
| `params` | `location_cn` / `location_en` / `year`（05 地图、18 日志需要；从水印、EXIF 或用户那里来，拿不到就问） |
| `reason` | 一句话分类依据，会显示在报告里 |

判定要点：人和风景都有时，看谁是视觉主体；美食照里有人入镜但主体是菜，仍按 `food`。

```json
{"photos": [{"key": "p01", "type": "group", "persons": 2, "repairs": [], "mode": "top",
  "params": {"location_cn": "青岛", "location_en": "Qingdao", "year": "2026"},
  "reason": "两人坐秋千、面向镜头，背景是海滩酒吧"}]}
```

路由与排序在 `prompts/index.json` 的 `routes`，硬规则由脚本执行：
- 合照一律跳过 02/05/08（它们只保留一个人物身份，实测会丢掉其他人）
- `persons: 0` 跳过所有需要人物的 prompt
- 每条的实测评分和已知问题见 `references/test-notes.md`

### 3. 生成任务并出图
```bash
python3 ~/.claude/skills/photo-remix/scripts/make_jobs.py --run <run>        # 打印每张照片选中/跳过的 prompt
zsh ~/.claude/skills/photo-remix/scripts/run_jobs.sh <run> 4                 # 用 Bash run_in_background 跑
```
- 每条约 2–3 分钟、约 6 万 Codex token；4 路并发，6 条约 5 分钟
- 已有输出自动跳过，中断后重跑同一命令即可续跑
- 最后一行 `RESULT:` 区分「基础设施失败」（额度/登录/模型不可用）和「其他失败」。基础设施失败要如实报告，不要写成"prompt 不行"
- 模型默认 `gpt-5.5`（Codex 默认模型可能对 ChatGPT 账号不可用）；可用环境变量 `PHOTO_REMIX_MODEL` 覆盖

### 4. 逐张点评
出图后用 `sips -Z 900 <png> --out <tmp>` 缩略后 Read 每一张，对照 prompt 要求写 `photos/pNN/notes.json`：
```json
{"01": {"score": "★★★★★", "note": "一句话：哪里好、哪里偏离 prompt（丢人、编造信息、文字错误）"}}
```
重点检查：人物是否都在、脸是否保真、文字有无乱码/拼写错误、是否编造了照片里没有的东西。

### 5. 报告
```bash
python3 ~/.claude/skills/photo-remix/scripts/build_report.py --run <run> --title "标题"
open <run>/report.html
```
图片全部内嵌，可离线打开、转发；每张有「⬇ 下载」，点图放大后也能下载，顶部「全部下载（ZIP）」（需联网加载 JSZip，离线时自动改为逐张下载）。

## 子功能

### 改字（不重新生成）
用户说「把图里的 X 改成 Y」时，只改那几块像素：
```bash
S=~/.claude/skills/photo-remix/scripts
python3 $S/text_replace.py find <img> x0,y0,x1,y1            # 在大致区域里找文字精确外框（暗字加 --dark）
python3 $S/text_replace.py put <img> --out <id>_renamed.png \
  --box 154,76,206,99 --text 新名字A --box 99,1174,178,1208 --text 新名字A --center
```
先把区域裁出来放大 Read 确认位置，改完再放大检查（字重、是否断笔、底色有无色块）。输出命名为 `outputs/<id>_<后缀>.png`，报告会作为变体卡片显示；可在 notes.json 用 `"<id>_<后缀>": {"label": "改名版", ...}` 写标签。

### 导入新文章的 prompt
```bash
python3 $S/import_article.py fetch <公众号URL> --out <tmp目录>   # 输出 article.txt 并提示可能的长 prompt 行
```
Read `article.txt` 确定每条 prompt 的起止行（公众号会把一段 prompt 切成很多碎片行），再逐条：
```bash
python3 $S/import_article.py add <tmp目录> --lines 15-57 --id 22 --slug xxx --title "标题" \
  [--needs-person] [--single-person-only] [--types group,person_single] [--keep-newlines]
```
地点、年份等可变内容改成 `{{location_cn}}` / `{{location_en}}` / `{{year}}`。入库前把清单给用户确认。

## 已知限制
- 本机只有 Codex 一个出图通道；额度用尽就停下报告
- GPT 图像模型画不出「故意画烂」的效果（07），会自编航班号等信息（02），装饰元素可能来自 prompt 而不是照片（20 的柠檬）
