# event.json 配置说明

完整示例见 `config/event.example.json`。所有路径相对于你运行命令的目录。

## event
| 键 | 说明 |
|---|---|
| `name` | 活动名，出现在所有页面标题 |
| `emoji` | 标题前的小图标，可空 |
| `timezone` | 页面显示时间用的时区，如 `Europe/London`、`Asia/Shanghai` |
| `currency` | 货币符号，如 `£`、`¥` |

## fields：统一字段
每个人最终都用这些字段表示。键是程序里的名字，`label` 是页面上显示的名字。
- `type: "bool"`：是/否题，自动把「A.是 / 否 / Yes / 需要 / 不需要…」转成 true/false
- `mono: true`：等宽字体显示（学号、邮箱）
- 必有的几个：`name`（姓名）、`id`（唯一编号，如学号/工号/手机号）、`email`、`adult`、`ticket`、`staff`。没有的列可以不映射。

## sources：报名表来源（可以多个）
排在前面的来源优先级更高（合并冲突时用它的值）。
| 键 | 说明 |
|---|---|
| `key` / `label` | 程序名 / 显示名 |
| `file` | CSV 或 xlsx 路径 |
| `format` | `tencent`（腾讯问卷）或 `csv`，目前只影响说明，解析逻辑通用 |
| `export_timezone` | 导出文件里时间所在的时区。**腾讯问卷导出是北京时间 `Asia/Shanghai`**；Google Form 是表格设置的时区 |
| `submission_no` | 提交编号列（腾讯问卷是「编号」）；没有就按行号 |
| `submitted_at` | `{column, format}`，提交时间列和 strptime 格式。腾讯问卷「结束答题时间」是 `%d-%b-%Y %H:%M:%S`；Google Form「时间戳记」常见 `%Y/%m/%d %H:%M:%S` 或 `%m/%d/%Y %H:%M:%S` |
| `columns` | `{统一字段: "表头原文"}`，必须和表头一字不差（含题号，如 `1.您的姓名`） |
| `defaults` | `{字段: 值}`，这个来源没有的列给默认值（例如补录表都算某学校） |
| `attachments` | `{column_prefix, file_pattern}`：上传题的列名前缀（用来数每人传了几个附件），以及附件文件名规则，`{no}` 代表提交编号。腾讯问卷「下载附件」的文件名是 `<编号>_q<题号>_<题目>_<原文件名>`，所以写 `^{no}_q10_` |

## 去重和标记
- `dedupe_by`：按哪些字段认同一个人，按顺序取第一个非空的，默认 `["id", "email"]`
- `ticket_aliases`：把长选项名改短，如 `"早鸟票（截至10月1日）": "早鸟票"`
- `staff_tickets`：选了这些票种就算工作人员
- `checks`：要打的标记
  - `under_18`：未满 18 岁
  - `id_is_email`：学号/ID 填成了邮箱
  - `email_domain_typo`：`expected` 里的邮箱后缀拼错了 1-2 个字母（如 `exmaple`），以及邮箱格式不对
  - `differs`：几个字段值不一样时提示，如去程/返程大巴只选了一个
  - `missing`：某些字段没填
  - `duplicate_image`：不同的人上传了同一张凭证图（需要跑 proofs.py）
  - 重填自动标记，不用配置

## payment：缴费核对
| 键 | 说明 |
|---|---|
| `prices` | `{票种: 价格}`，票种用 alias 之后的短名 |
| `addons` | 附加项列表：`{label, price, when_any: [字段...]}` 任一为真就加；或 `when_all` 全部为真才加 |
| `coupon_discount` | 优惠码减多少（只用于看图时判断，不自动扣） |
| `always_review_tickets` | 这些票种不管凭证如何一律「需要核实」（如工作人员） |
| `payee` | 收款人，看图时核对 |

## master：总表页
- `default_columns`：默认勾选的列。可选的键：所有 fields、`_src`（来源）、`subs`（报名记录）、`checked_in`、`checked_at`、签到页现场字段、`pay_status` / `pay_due` / `pay_paid` / `pay_note`、`flags`、`notes`
- `filter_columns`：除是/否列外，哪些列给筛选按钮，默认 `ticket, _src, checked_in, pay_status`

## checkin：签到 / 手环发放页
| 键 | 说明 |
|---|---|
| `title` | 页面标题，如「入场签到」「手环发放」 |
| `item` | 发的东西，可空 |
| `confirm_label` / `done_label` | 确认按钮文字 / 完成状态文字，如「确认领取手环」/「已领取」 |
| `editable` | 详情里可以现场修改的报名字段（会记录原值和改了什么） |
| `onsite_fields` | 现场登记字段：`{key, label, type, required}`，type 为 `text` / `textarea` / `choice`（配 `options`）/ `scale`（配 `min` `max`）/ `bool` |
| `after_confirm` | 确认后展示的内容：`title`、`qr_image`（图片路径，如活动群二维码）、`caption`、`expires`（有效期文字） |
| `google` | Apps Script 版用：`sheet_id`、`records_tab`、`log_tab` |

## draw：抽奖
`title`、`emoji`、`remove_winner`（默认中奖后移出奖池）。
