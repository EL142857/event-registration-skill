"""生成一套完全虚构的示例数据，用来试跑整条流程（不含任何真实个人信息）。

用法：python3 scripts/make_sample.py examples
生成：
  examples/sample_main.csv         腾讯问卷格式的主报名表（30 份提交，含重填、未成年、邮箱拼错等情况）
  examples/sample_late.csv         普通 CSV 格式的补录表（6 人，其中 2 人和主表重复）
  examples/sample_attachments/     问卷"下载附件"解压后的样子：<编号>_q10_<原文件名>.png（假转账截图）
  examples/sample_qr.png           占位二维码图（不是真的二维码）
"""
import csv
import os
import random
import shutil
import sys
from datetime import datetime, timedelta

SURNAMES = list('赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦许何吕施张孔曹严华金魏陶姜')
GIVEN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '甲', '乙', '丙', '丁', '小明', '小红', '小刚', '小美']
LATIN = ['Alex Sample', 'Sam Example', 'Jamie Demo', 'Robin Test']


def fake_people(rng, n):
    used, out = set(), []
    while len(out) < n:
        name = '示例' + rng.choice(SURNAMES) + rng.choice(GIVEN)
        if name in used:
            continue
        used.add(name)
        i = len(out) + 1
        out.append({'name': name, 'id': f'ex{100 + i}', 'email': f'ex{100 + i}@example.ac.uk'})
    for j, nm in enumerate(LATIN):
        out[j * 7]['name'] = nm
    return out


def fmt_tencent(t):
    return t.strftime('%d-%b-%Y %H:%M:%S')


def proof_image(path, amount, kind, rng):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 600, 1000
    im = Image.new('RGB', (W, H), (246, 246, 248))
    d = ImageDraw.Draw(im)
    font = None
    for f in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
              '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', '/System/Library/Fonts/PingFang.ttc',
              'C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(f):
            font = f
            break
    F = (lambda s: ImageFont.truetype(font, s)) if font else (lambda s: ImageFont.load_default(size=s))
    d.rectangle([0, 0, W, 120], fill=(30, 110, 90))
    d.text((40, 40), 'SAMPLE BANK  示例银行', fill='white', font=F(34))
    if kind == 'blank':
        return im.save(path)
    if kind == 'review':
        d.text((40, 200), 'Review payment', fill=(40, 40, 40), font=F(40))
        d.text((40, 280), f'£{amount}.00', fill=(40, 40, 40), font=F(72))
        d.rounded_rectangle([40, 820, W - 40, 900], 20, fill=(30, 110, 90))
        d.text((200, 840), 'Confirm', fill='white', font=F(36))
    else:
        d.ellipse([W // 2 - 60, 180, W // 2 + 60, 300], fill=(52, 180, 120))
        d.line([(W // 2 - 30, 242), (W // 2 - 8, 264), (W // 2 + 32, 218)], fill='white', width=12)
        d.text((40, 340), '转账成功 Payment sent', fill=(40, 40, 40), font=F(36))
        d.text((40, 420), f'£{amount}.00', fill=(20, 20, 20), font=F(80))
        d.text((40, 560), 'To: 示例收款人', fill=(90, 90, 90), font=F(30))
        d.text((40, 610), f'Ref: SAMPLE{rng.randint(1000, 9999)}', fill=(90, 90, 90), font=F(30))
    d.text((40, H - 60), '虚构示例图 · not a real payment', fill=(170, 170, 170), font=F(24))
    im.save(path)


def main(outdir):
    rng = random.Random(2026)
    os.makedirs(os.path.join(outdir, 'sample_attachments'), exist_ok=True)
    P = fake_people(rng, 26)
    tickets = ['A.早鸟票（截至10月1日）', 'B.普通票（10月2日起）', 'C.工作人员']
    price = {'A': 60, 'B': 70, 'C': 0}
    head = ['编号', '开始答题时间', '结束答题时间', '答题时长', '1.您的姓名', '2.您的学校', '3.您的学号', '4.您的年级', '5.您的邮箱',
            '6.您是否已满18岁', '7.是否需要乘坐去程大巴', '8.是否需要乘坐返程大巴', '9.您的购票种类',
            '10.请上传您的缴费凭证_附件1', '10.请上传您的缴费凭证_附件2', '11.您的食物过敏源', '12.其它说明', 'IP', 'UA']
    rows, no = [], 0
    verdicts = {}
    t = datetime(2026, 9, 20, 18, 0)
    plan = list(range(len(P))) + [3, 11, 18]  # 3 人重填
    for idx in plan:
        p = dict(P[idx])
        no += 1
        t += timedelta(hours=rng.randint(1, 30), minutes=rng.randint(0, 59))
        tk = tickets[0] if no < 18 else tickets[1]
        if idx in (5, 13, 21):
            tk = tickets[2]
        to = rng.random() < 0.7
        back = to if rng.random() < 0.85 else not to
        adult = 'B.否' if idx == 9 else 'A.是'
        email = p['email']
        if idx == 15:
            email = email.replace('example.ac.uk', 'exmaple.ac.uk')
        sid = p['id']
        if idx == 17:
            sid = p['email']  # 学号填成邮箱
        if idx in (3, 11) and no > len(P):
            to = not to  # 重填时改了大巴
        due = price[tk[0]] + (20 if (to or back) else 0)
        kind, amount = 'ok', due
        if idx == 7:
            amount = due - 20  # 少付车费
        if idx == 12:
            kind = 'review'
        if idx == 5:
            kind = 'blank'
        n_img = 0 if idx == 20 else 1
        links = []
        for k in range(n_img):
            fn = f'{no}_q10_请上传您的缴费凭证__IMG_{1000 + no * 3 + k}.png'
            src_no = 4 if idx == 22 else no  # idx 22 和 #4 上传了同一张图
            same = os.path.join(outdir, 'sample_attachments', '4_q10_请上传您的缴费凭证__IMG_1012.png')
            if idx == 22 and os.path.exists(same):
                shutil.copy(same, os.path.join(outdir, 'sample_attachments', fn))
            else:
                proof_image(os.path.join(outdir, 'sample_attachments', fn), amount, kind, rng)
            links.append(f'=Hyperlink("https://example.com/files/{src_no}-{k}","附件{k + 1}")')
        links += [''] * (2 - len(links))
        k = sid.split('@')[0]
        if idx % 4 != 1:  # 留一部分不写结论，演示「待看图」
            if not n_img:
                pass
            elif kind == 'blank':
                verdicts[k] = {'status': 'check', 'paid': '无', 'note': f'凭证是空白图，没有转账记录；应付 £{due}'}
            elif kind == 'review':
                verdicts[k] = {'status': 'check', 'paid': f'£{amount}（未确认）', 'note': '截图是转账前的确认页，还没点 Confirm，证明不了已付款'}
            elif amount < due:
                verdicts[k] = {'status': 'check', 'paid': f'£{amount}', 'note': f'应付 £{due}，只看到 £{amount}，差 £{due - amount}'}
            else:
                verdicts[k] = {'status': 'ok', 'paid': f'£{amount}', 'note': ''}
        start = t - timedelta(minutes=rng.randint(2, 9))
        rows.append([no, fmt_tencent(start), fmt_tencent(t), rng.randint(100, 600), p['name'], 'A.示例大学', sid,
                     rng.choice(['A.本科一年级', 'B.本科二年级', 'E.研究生']), email, adult,
                     'A.是' if to else 'B.否', 'A.是' if back else 'B.否', tk, *links,
                     rng.choice(['无', '花生', '', '/', '海鲜']), rng.choice(['', '', '和朋友一起来', '可能晚到 10 分钟']),
                     '0.0.0.*', 'Mozilla/5.0 (sample)'])
    with open(os.path.join(outdir, 'sample_main.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerows([head] + rows)

    late_head = ['序号', '提交时间', '姓名', '邮箱', '微信号', '是否满18岁', '身份']
    late = []
    for i, p in enumerate([P[2], P[8]] + fake_people(random.Random(7), 30)[26:30]):
        email = p['email'] if i < 2 else f'late{i}@example.com'
        if i == 5:
            p = {'name': P[14]['name']}  # 和主表里某人同名、邮箱不同 → 合并时会列成问题
        late.append([i + 1, (t + timedelta(days=1, minutes=i * 7)).strftime('%Y/%m/%d %H:%M:%S'), p['name'] if i else p['name'] + ' ',
                     email, f'wx_sample_{i + 1}', '是', '摊主' if i in (0, 3) else '志愿者'])
    with open(os.path.join(outdir, 'sample_late.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows([late_head] + late)

    import json
    json.dump(verdicts, open(os.path.join(outdir, 'sample_verdicts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # 签到页导出的记录（格式同签到页数据库里的 checkins 文档）
    now = '2026-10-31T18:{:02d}:00Z'
    checkins = []
    for i, p in enumerate(P[:12]):
        cur = {'name': p['name'], 'id': p['id'], 'email': p['email'], 'adult': i != 9, 'staff': i in (2, 5, 8),
               'wechat': f'wx_demo_{i}', 'costume': '有' if i % 2 else '没有', 'walk': (i % 5) + 1, 'remark': ''}
        if i == 4:
            cur['email'] = 'new.address@example.com'
        checkins.append({'k': p['id'], 'claimed': i != 6, 'claimedAt': now.format(i * 3), 'current': cur,
                         'original': {kk: cur[kk] for kk in ('name', 'id', 'email')}, 'manual': False})
    checkins.append({'k': 'm-demo1', 'manual': True, 'claimed': True, 'claimedAt': now.format(50),
                     'current': {'name': '示例现场新增', 'id': '', 'email': 'walkin@example.com', 'adult': True, 'staff': False,
                                 'wechat': 'wx_walkin', 'costume': '没有', 'walk': 3, 'remark': '现场买票'}})
    json.dump(checkins, open(os.path.join(outdir, 'sample_checkins.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # 占位"二维码"：只是个方格图案，不能扫
    from PIL import Image, ImageDraw
    q = Image.new('RGB', (290, 290), 'white')
    d = ImageDraw.Draw(q)
    r = random.Random(1)
    for y in range(29):
        for x in range(29):
            if r.random() < 0.45:
                d.rectangle([x * 10, y * 10, x * 10 + 9, y * 10 + 9], fill='black')
    for ox, oy in ((0, 0), (220, 0), (0, 220)):
        d.rectangle([ox, oy, ox + 69, oy + 69], fill='black')
        d.rectangle([ox + 10, oy + 10, ox + 59, oy + 59], fill='white')
        d.rectangle([ox + 20, oy + 20, ox + 49, oy + 49], fill='black')
    q.save(os.path.join(outdir, 'sample_qr.png'))
    print(f'{len(rows)} 份主表提交、{len(late)} 份补录、{len(os.listdir(os.path.join(outdir, "sample_attachments")))} 张示例凭证图 → {outdir}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'examples')
