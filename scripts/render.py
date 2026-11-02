"""把数据写进页面模板，生成一个可以直接打开 / 发布成 Claude Artifact 的单文件网页。

用法：
    python3 scripts/render.py <页面> config/event.json <数据.json> <输出.html> [选项]

页面：
    list      报名名单页（数据：people.json）          筛选、搜索、复制邮箱、凭证缩略图点开看大图、标记
    payment   缴费核对页（数据：payment.json）         一人一行，应付 / 实付 / 结论 / 备注 + 凭证图
    master    总表页（数据：master.json）              勾选要的列、筛选、统计、导出 CSV
    checkin   签到 / 手环发放页（数据：people.json 或 master.json）
    draw      抽奖轮盘（数据：people.json 或 master.json）

选项：
    --embed-images     把凭证图直接嵌进 html（单文件，适合几十张图；图多时改用 Artifact 的 files 一起发布 proof/ 文件夹）
    --qr 图片          签到成功后展示的二维码图（覆盖 config.checkin.after_confirm.qr_image）
    --backend claude|gas|local
                       签到页的保存方式：claude = Claude Artifact 数据库（默认）；gas = Google Apps Script（build_gas.py 用）；
                       local = 只存在这台设备的浏览器里
    --view-only        签到页只读（只能搜索查看，不能确认）
"""
import argparse
import html
import base64
import mimetypes
import os

from common import ROOT, inject, load, load_config, public_config, resolve

TPL = os.path.join(ROOT, 'templates')

# 签到页 / 抽奖页只带需要的字段（页面可能分享给工作人员，少带个人信息）
CHECKIN_KEEP = {'k', 'no', 'src', 'name', 'id', 'email', 'adult', 'staff', 'ticket', 'py', 'sk', 'prev', '_src'}
DRAW_KEEP = {'k', 'no', 'name', 'py', 'staff', '_src', 'src'}


def data_uri(path):
    mt = mimetypes.guess_type(path)[0] or 'image/jpeg'
    return f'data:{mt};base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def shape(page, cfg, data, data_path, embed):
    base = os.path.dirname(os.path.abspath(data_path))
    if page in ('list', 'payment') and embed:
        for r in data['rows']:
            for im in r.get('imgs', []):
                if im.get('src') and os.path.exists(os.path.join(base, im['src'])):
                    im['src'] = data_uri(os.path.join(base, im['src']))
    if page == 'checkin':
        extra = set(cfg.get('checkin', {}).get('editable', [])) | {f['key'] for f in cfg.get('checkin', {}).get('onsite_fields', [])}
        rows = [{k: v for k, v in r.items() if k in CHECKIN_KEEP | extra} for r in data['rows']]
        if rows and 'py' not in rows[0]:
            from common import search_keys, sort_key
            for r in rows:
                r['py'], r['sk'] = search_keys(r.get('name', '')), sort_key(r.get('name', ''))
        data = {'meta': data.get('meta', {}), 'rows': rows}
    if page == 'draw':
        from common import search_keys
        rows = []
        for r in data['rows']:
            x = {k: v for k, v in r.items() if k in DRAW_KEEP}
            x.setdefault('py', search_keys(r.get('name', '')))
            rows.append(x)
        data = {'rows': rows}
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page', choices=['list', 'payment', 'master', 'checkin', 'draw'])
    ap.add_argument('config'), ap.add_argument('data'), ap.add_argument('out')
    ap.add_argument('--embed-images', action='store_true')
    ap.add_argument('--qr')
    ap.add_argument('--backend', default='claude', choices=['claude', 'gas', 'local'])
    ap.add_argument('--view-only', action='store_true')
    a = ap.parse_args()
    cfg = load_config(a.config)
    data = shape(a.page, cfg, load(a.data), a.data, a.embed_images)
    pub = public_config(cfg)
    qr = ''
    if a.page == 'checkin':
        q = a.qr or cfg.get('checkin', {}).get('after_confirm', {}).get('qr_image')
        if q:
            qr = data_uri(resolve(cfg, q))
        pub['_backend'] = a.backend
        pub['_viewOnly'] = a.view_only
    if a.page != 'payment':
        pub.pop('payment', None)  # 价格规则只在缴费页用
    n = inject(os.path.join(TPL, f'{a.page}.html'), a.out,
               BASE_CSS=open(os.path.join(TPL, '_base.css'), encoding='utf-8').read(),
               BASE_JS=open(os.path.join(TPL, '_base.js'), encoding='utf-8').read(),
               CONFIG=pub, DATA=data, QR=qr,
               TITLE=html.escape(cfg['event'].get('name', '活动')))
    print(f'{a.out}  {n / 1024:.0f} KB')


if __name__ == '__main__':
    main()
