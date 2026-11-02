---
name: event-registration
description: 活动报名与名单整理一条龙：设计报名表、清洗问卷导出（腾讯问卷/Google Form/任意 CSV/Excel）和附件、去重标记、缴费凭证核对、多来源合并总表、现场签到/手环发放页（Claude Artifact 或 Google Apps Script 免登录版 + Excel 备份）、抽奖轮盘。用户提到活动报名、报名表、问卷导出、名单整理、去重、缴费核对、签到、发手环、总表、抽奖时使用。
---

# 活动报名 / 名单整理 / 签到 一条龙

一套从「报名表设计」到「现场签到、抽奖」的一键工具。所有脚本只读一个配置文件 `event.json`，换活动只改配置，不改代码。
脚本在 `scripts/`，页面模板在 `templates/`，细节文档在 `references/`。

## 先做什么

1. **问清楚再动手**：活动名称、时区、报名表从哪导出、学号/邮箱哪个是唯一标识、票种和价格、签到时要现场补登哪些信息、签到后要不要展示群二维码。拿不准就问用户，不要猜价格和规则。
2. 复制 `config/event.example.json` 为用户的 `event.json`，按 `references/config.md` 填。**列名必须和导出文件表头一字不差**——先读一下表头再填。
3. 依赖：Python 3.9+；`pip install -r requirements.txt`（pypinyin 拼音搜索、openpyxl Excel、Pillow 图片），缺了也能跑，只是对应功能降级。
4. 想先看效果：`bash scripts/run_example.sh` 用虚构数据跑完整条流程，结果在 `out/`。

## 流程（按需选用，每步都是一条命令）

| 步骤 | 命令 | 产出 |
|---|---|---|
| 0 设计报名表 | 读 `references/form-design.md` | 题目清单、开头文案、导出注意事项 |
| 1 清洗导出 | `python3 scripts/normalize.py event.json out/people.json` | 一人一行、去重、标记（未成年、邮箱拼错、重填…） |
| 2 附件/凭证图 | `python3 scripts/proofs.py event.json out/people.json 附件.zip` | `out/proof/*.jpg`，同图不同人标记 |
| 3 缴费核对 | `python3 scripts/payment.py event.json out/people.json out/verdicts.json out/payment.json` | 应付金额 + 结论；`verdicts.todo.json` 是待看图清单 |
| 4 合并总表 | `python3 scripts/merge.py event.json out/people.json out/master.json --payment out/payment.json --checkins 签到导出.json --resolve resolutions.json` | 一人一行总表 + `questions.md` |
| 5 页面 | `python3 scripts/render.py <list\|payment\|master\|checkin\|draw> event.json <数据.json> out/页面.html` | 单文件网页 |
| 6 签到备份 | `python3 scripts/checkin_xlsx.py event.json out/people.json out/签到备份.xlsx` | 带下拉框的 Excel |
| 7 免登录签到 | `python3 scripts/build_gas.py event.json out/people.json out/gas --qr 群二维码.png` | Google Apps Script 两个文件 + 部署步骤 |

页面说明：
- `list` 报名名单：筛选（来源/票种/每个是否题/有标记）、搜索（姓名、拼音全拼、首字母、学号、邮箱、编号）、复制邮箱、凭证缩略图点开放大左右翻页、导出 CSV。
- `payment` 缴费核对：一人一行，应付明细 / 实付 / 结论 / 备注 / 凭证图，按结论筛选。
- `master` 总表：勾选要的列（记在本机）、按取值少的列筛选、统计跟着筛选变、导出 CSV；顶部列出要主办方确认的问题。
- `checkin` 签到 / 发手环：搜索后**必须点列表**才打开某人（回车只收键盘）；可改报名信息（会记录原值）；现场登记字段可设必填；列表末尾永远有「现场新增（名单外）」；确认后全屏展示群二维码；撤销；所有者可导出 CSV；屏幕常亮。
- `draw` 抽奖：点名字加入奖池，轮盘抽取，中奖可移出奖池，「不在场，重抽」。状态存在本机浏览器。

## 关键做法（从真实活动里总结的）

- **去重**：同一来源里按 `dedupe_by`（默认先学号后邮箱，学号会去掉 `@` 后面）保留最新一份，旧编号记在 `prev`，并标出前后改了哪些题。不同来源之间只在 `merge.py` 里合并。
- **只有名字相同绝不自动合并**，写进 `questions.md` 问主办方；主办方回答后写进 `resolutions.json`（`same` / `different` / `exclude` / `override`）再跑一次。
- **缴费核对要看图**：`payment.py` 只算应付金额和给出自动建议。对 `verdicts.todo.json` 里的每个人，用 Read 工具逐张打开 `out/proof/` 里的图，按 `references/payment-review.md` 判断（金额对不对、是不是转账成功页而不是确认页、收款人、空白图/无关图、多人共用一张图），把结论写进 `verdicts.json`，再跑 `payment.py`。拿不准一律 `check` 并写清原因，不要替用户认定「已付」。
- **规则写进配置，不写进代码**：价格、附加项（如大巴）、优惠券减免、哪些票种一律核实，都在 `config.payment`。
- **时间**：问卷导出时间按 `export_timezone` 解析（腾讯问卷是北京时间），页面统一按 `event.timezone` 显示，并注明时区。

## 发布页面（Claude Artifact）

读 `references/publishing.md`。要点：
- `list` / `payment` 带凭证图：图少用 `--embed-images` 打成单文件；图多则发布时把 `out/proof/` 作为 `files` 一起发布。
- `checkin` 需要声明 `capabilities: {"db": {"rules": [{"path": "checkins", "read": "view", "write": "interact"}]}, "user": {"scopes": ["profile"]}, "downloads": true}`；记录写在 `checkins/<k>`，可用 ArtifactData 读回来交给 `merge.py`。
- 只有登录且是编辑者/贡献者的工作人员能确认；需要「拿链接就能用、不用登录」时，用 Google Apps Script 版（`references/google-apps-script.md`）。
- `master` / `list` / `draw` 不需要任何 capability（`master` 导出可加 `downloads: true`）。

## 隐私

名单页面含个人信息：默认私有发布，分享前提醒用户。签到页和抽奖页只带必要字段（`render.py` 已裁剪）。不要把真实报名数据、凭证图提交进任何代码仓库。详见 `references/privacy.md`。
