"""生成签到页的 Google Apps Script 版（不用登录 Claude，任何拿到链接的工作人员都能确认，数据写进你的 Google 表格）。

用法：
    python3 scripts/build_gas.py config/event.json out/people.json out/gas/ [--qr 二维码.png]

生成 out/gas/Code.gs 和 out/gas/Index.html，部署步骤见 out/gas/部署步骤.md（也在 references/google-apps-script.md）。
名单是写死在 Index.html 里的；名单更新后重新跑本脚本，再把两个文件粘回去，「管理部署 → 编辑 → 新版本」。
"""
import argparse
import json
import os
import subprocess
import sys

from common import HERE, ROOT, load_config

STEPS = """# 部署步骤（约 5 分钟）

1. 打开要存签到记录的 Google 表格（可以新建一个空表格），网址里 `/d/` 和 `/edit` 之间那串就是表格 ID，填进 config 的 `checkin.google.sheet_id`，重新运行 build_gas.py。
2. 表格菜单 **扩展程序 → Apps Script**。
3. 把左侧默认的 `Code.gs` 内容全部删掉，粘贴本文件夹里 `Code.gs` 的全部内容。
4. 左侧 **＋ → HTML**，文件名填 `Index`（不要加 .html），粘贴 `Index.html` 的全部内容。
5. 点 💾 保存。
6. 右上角 **部署 → 新建部署** → 类型选「Web 应用」：
   - 执行身份：**我**
   - 谁可以访问：**任何人**
   然后点「部署」，第一次会要求授权，点「允许」（会提示应用未经验证，点 高级 → 继续）。
7. 复制得到的 `https://script.google.com/macros/s/.../exec` 链接，发给签到台的工作人员。

记录会写进表格里自动创建的两个分页：「{records}」（每人一行）和「{log}」（每次操作一行），表格里其他分页不会被动。

**更新名单**：重新生成后，把两个文件重新粘贴保存，然后 **部署 → 管理部署 → ✏️ 编辑 → 版本选「新版本」→ 部署**，链接不变。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config'), ap.add_argument('data'), ap.add_argument('outdir')
    ap.add_argument('--qr')
    a = ap.parse_args()
    cfg = load_config(a.config)
    c = cfg.get('checkin', {})
    g = c.get('google', {})
    if not g.get('sheet_id'):
        print('提醒：config.checkin.google.sheet_id 还没填，生成的 Code.gs 先用占位符，部署前要填好再生成一次。')
    os.makedirs(a.outdir, exist_ok=True)
    cmd = [sys.executable, os.path.join(HERE, 'render.py'), 'checkin', a.config, a.data, os.path.join(a.outdir, 'Index.html'), '--backend', 'gas']
    if a.qr:
        cmd += ['--qr', a.qr]
    subprocess.run(cmd, check=True)
    F = cfg['fields']
    editable = [f for f in c.get('editable', ['name', 'id', 'email', 'adult', 'staff']) if f in F]
    onsite = [o['key'] for o in c.get('onsite_fields', [])]
    labels = {k: v.get('label', k) for k, v in F.items()}
    labels.update({o['key']: o['label'] for o in c.get('onsite_fields', [])})
    conf = {
        'title': f"{cfg['event']['name']} · {c.get('title', '签到')}",
        'sheetId': g.get('sheet_id') or 'PASTE_SHEET_ID_HERE',
        'recordsTab': g.get('records_tab', '签到记录'), 'logTab': g.get('log_tab', '签到操作日志'),
        'timezone': cfg['event'].get('timezone', 'UTC'), 'okLabel': c.get('done_label', '已签到'),
        'editable': editable, 'onsite': onsite, 'labels': labels,
        'required': [o['key'] for o in c.get('onsite_fields', []) if o.get('required')],
    }
    code = open(os.path.join(ROOT, 'templates', 'gas', 'Code.gs'), encoding='utf-8').read()
    code = code.replace('__GAS_CONFIG__', json.dumps(conf, ensure_ascii=False, indent=2))
    open(os.path.join(a.outdir, 'Code.gs'), 'w', encoding='utf-8').write(code)
    open(os.path.join(a.outdir, '部署步骤.md'), 'w', encoding='utf-8').write(
        STEPS.replace('{records}', conf['recordsTab']).replace('{log}', conf['logTab']))
    print('Code.gs / Index.html / 部署步骤.md →', a.outdir)


if __name__ == '__main__':
    main()
