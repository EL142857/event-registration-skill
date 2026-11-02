# 发布页面（Claude Artifact）

`render.py` 生成的都是单文件 html，可以直接用浏览器打开，也可以用 Claude 的 Artifact 工具发布成 claude.ai 上的私有页面。

## 各页面需要什么
| 页面 | capabilities | 附带文件 |
|---|---|---|
| list 名单 | 不需要（导出 CSV 想走确认弹窗可加 `"downloads": true`） | 凭证图：`--embed-images` 打进 html；或发布时 `files: {"proof/xxx.jpg": "out/proof/xxx.jpg", ...}` |
| payment 缴费核对 | 同上 | 同上 |
| master 总表 | `{"downloads": true}` | 无 |
| checkin 签到 | 见下 | 无（二维码已内嵌） |
| draw 抽奖 | 不需要 | 无 |

图片超过几十张时，不要嵌进 html（页面会很大），用 `files` 一起发布 `proof/` 文件夹。

## 签到页（数据库）
```json
"capabilities": {
  "db": {"rules": [{"path": "checkins", "read": "view", "write": "interact"}]},
  "user": {"scopes": ["profile"]},
  "downloads": true
}
```
- 每个人一条文档 `checkins/<k>`：`original`（报名时的信息）、`current`（现场确认后的信息）、`changed`、`claimed`、`claimedAt`、`claimedBy`（用户 id）、`history`（每次确认/修改/撤销）。现场新增的人 key 是 `m-xxxx`，`manual: true`。
- 名单直接写在 html 里，所以没登录的人也能搜索查看（只读，看不到谁签过）。名单更新：重新 `render.py checkin` 再发布到同一个 artifact，已有签到记录按 key 保留。
- **谁能确认**：必须登录 claude.ai，且在这个 artifact 上至少是 Contributor / Editor。用公开链接打开的访客永远只能看。签到台人多、不方便都登录时，用 Google Apps Script 版。
- 活动结束后：用 ArtifactData 的 `list` 读出 `checkins` 整个集合，存成 JSON，交给 `merge.py --checkins`。

## 发布后检查
- 用 ArtifactData `list` 看一下 `checkins` 集合能读到（空集合也算正常）。
- 用手机宽度打开一次签到页：搜索、点人、必填提示、确认、二维码、下一位。

## 分享
页面默认私有。名单、缴费、总表页含个人信息，只分享给需要的工作人员；签到页只带姓名、ID、邮箱、票种等必要字段。
