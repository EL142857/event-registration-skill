# 免登录签到：Google Apps Script 版

Claude Artifact 签到页要求每个确认的人都登录并有编辑权限。签到台临时找来的志愿者没有账号时，用这个版本：任何拿到链接的人都能确认，记录写进你自己的 Google 表格。页面和 Artifact 版是同一个模板（`templates/checkin.html`），只是保存方式换成 `google.script.run`。

## 生成
```bash
python3 scripts/build_gas.py event.json out/people.json out/gas --qr 群二维码.png
```
得到 `out/gas/Code.gs`、`out/gas/Index.html`、`out/gas/部署步骤.md`。先把 Google 表格 ID 填进 `checkin.google.sheet_id` 再生成。

## 部署（约 5 分钟，用户自己在浏览器里操作）
1. 打开目标 Google 表格（可以新建一个空的），**扩展程序 → Apps Script**。
2. 默认的 `Code.gs` 全删，粘贴生成的 `Code.gs`。
3. **＋ → HTML**，名字填 `Index`，粘贴 `Index.html`。保存。
4. **部署 → 新建部署 → Web 应用**：执行身份「我」，访问权限「任何人」。第一次要授权（提示未经验证 → 高级 → 继续）。
5. 得到 `https://script.google.com/macros/s/.../exec`，发给签到台。

可以把 `部署步骤.md` 做成一个带「复制」按钮的小页面发给用户，粘贴更方便。

## 数据
- 自动新建两个分页：「签到记录」每人一行（报名原值 / 现场值 / 时间 / 发放人 / 改过的信息，最后一列是程序用 JSON，别手改），「签到操作日志」每次操作一行。表格里其他分页不会被读写。
- 页面顶部有「发放人」输入框（没有登录，靠这个记录是谁确认的），每 15 秒刷新一次别人确认的结果。
- 写入加了锁，多台设备同时确认不会互相覆盖。

## 更新名单
重新跑 `build_gas.py`，把两个文件重新粘贴保存，然后 **部署 → 管理部署 → ✏️ → 版本「新版本」→ 部署**。链接不变，已有记录不受影响。

## 合并
活动后把「签到记录」分页导出 CSV，或直接用 Artifact 版导出的 CSV，交给 `merge.py --checkins`。
