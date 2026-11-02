# event-registration-skill

**活动报名 · 数据整理 · 名单 · 签到 · 抽奖 —— 一套给 Claude 用的一键工具（Claude Skill）**

办过一次活动就知道：问卷导出一堆 `A.是`、同一个人填三遍、学号填成邮箱、付款截图对不上、几张表要合成一张、现场签到手忙脚乱……
这个 skill 把这些活全部做成了「改配置 + 一条命令」，从一次 100+ 人的真实活动里打磨出来，换任何活动只需要改一个 `event.json`。

> English: A Claude Skill for event registration workflows — clean form exports (Tencent Wenjuan / Google Forms / any CSV), dedupe & flag issues, review payment screenshots, merge multiple sources into one master list, and generate single-file pages for the roster, payment check, master table, on-site check-in (Claude Artifact or no-login Google Apps Script, plus an Excel backup) and a lucky-draw wheel. Config-driven; no code changes per event.

## 能做什么

| | 功能 | 产出 |
|---|---|---|
| 📝 | 报名表设计：题目清单、开头文案、导出注意事项 | `references/form-design.md` |
| 🧹 | 清洗问卷导出：字段映射、去 `A.` 前缀、是/否转换、时区换算、按学号/邮箱去重保留最新、自动标记问题 | `people.json` |
| 🖼️ | 附件处理：问卷附件 zip 自动对应到人、压缩、发现「不同人同一张图」 | `proof/*.jpg` |
| 💷 | 缴费核对：按配置算应付（票价 + 大巴等附加项），看图下结论，一人一行 | `payment.json` + 页面 |
| 🔗 | 多来源合并：多张报名表 + 补录 + 现场签到 → 一人一行总表，冲突列成问题清单 | `master.json` + `questions.md` |
| 📋 | 报名名单页：筛选、拼音搜索、复制邮箱、凭证大图翻页 | `list` 页面 |
| 🎟️ | 现场签到 / 发手环页：拼音搜索、改信息留痕、现场新增、必填项、确认后弹群二维码、撤销、导出 | `checkin` 页面 |
| ☁️ | 免登录签到：同一个页面的 Google Apps Script 版，记录写进 Google 表格 | `Code.gs` + `Index.html` |
| 📊 | 签到 Excel 备份：断网时直接在表格里填，带下拉框 | `.xlsx` |
| 🎰 | 抽奖轮盘：点名加入奖池、转盘抽取、不在场重抽 | `draw` 页面 |

## 截图（虚构示例数据）

| 报名名单 | 缴费核对 |
|---|---|
| ![](docs/list.png) | ![](docs/payment.png) |
| **报名总表** | **签到（手机）** |
| ![](docs/master.png) | ![](docs/checkin.png) |

## 安装

**作为 Claude Code skill**
```bash
git clone https://github.com/EL142857/event-registration-skill ~/.claude/skills/event-registration
pip install -r ~/.claude/skills/event-registration/requirements.txt
```
之后直接对 Claude 说「帮我整理这份报名表导出」「做一个签到页」，它会按 `SKILL.md` 的流程来。

**在 claude.ai 上用**：把仓库打包成 zip，在 设置 → Capabilities → Skills 上传。

**不用 Claude，直接跑脚本**也完全可以（纯 Python，标准库 + 三个可选依赖）。

## 快速试一下

```bash
bash scripts/run_example.sh     # 生成虚构数据，跑完整条流程
open out/名单.html out/签到.html # 或者用浏览器打开 out/ 里的任意页面
```

## 用在自己的活动上

```bash
cp config/event.example.json config/event.json   # 改活动名、列名、价格、签到字段
python3 scripts/normalize.py config/event.json out/people.json
python3 scripts/proofs.py    config/event.json out/people.json 附件.zip
python3 scripts/payment.py   config/event.json out/people.json out/verdicts.json out/payment.json
python3 scripts/merge.py     config/event.json out/people.json out/master.json --payment out/payment.json
python3 scripts/render.py list    config/event.json out/people.json  out/名单.html --embed-images
python3 scripts/render.py checkin config/event.json out/people.json  out/签到.html --qr 群二维码.png
python3 scripts/render.py draw    config/event.json out/master.json  out/抽奖.html
```
配置说明见 [`references/config.md`](references/config.md)。

## 目录

```
SKILL.md                 Claude 读的说明（流程、规则、发布方法）
config/                  配置示例
scripts/                 normalize / proofs / payment / merge / render / checkin_xlsx / build_gas / make_sample
templates/               页面模板（单文件 html，自动适配深色模式和手机）+ Apps Script 后台
references/              报名表设计、配置、凭证核对、发布、Apps Script、隐私
examples/                虚构示例数据（make_sample.py 生成）
```

## 隐私

仓库里没有任何真实个人信息；示例数据全部是脚本生成的虚构内容。`.gitignore` 已排除 `out/`、`data/`、`*.zip` 和 `config/event.json`，请不要把真实报名数据提交进来。详见 [`references/privacy.md`](references/privacy.md)。

## License

MIT
