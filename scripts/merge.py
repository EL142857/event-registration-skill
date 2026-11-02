"""第 4 步：把所有来源合并成一人一行的总表，冲突和拿不准的地方列成问题清单。

用法：
    python3 scripts/merge.py config/event.json out/people.json out/master.json \
        [--payment out/payment.json] [--checkins 签到导出.json ...] [--resolve resolutions.json]

合并规则：
  * 来源按 config.sources 的顺序定优先级（排前面的更可信）
  * 学号相同或邮箱相同 → 自动合并成一个人；只有名字相同 → 不合并，写进问题清单问主办方
  * 同一个人在不同来源里某个字段不一样 → 用优先级高的，另一份写进备注
  * 签到记录（签到页导出的 JSON / CSV）：按 k → 学号 → 邮箱 → 姓名 对上人；现场改过的信息以现场为准；
    名单外的现场新增变成新的一行
  * 主办方回答过的问题写进 resolutions.json，再跑一次就会生效：
      {"same": [["k1","k2"]], "different": [["k1","k2"]], "exclude": ["k"],
       "override": {"k": {"ticket": "工作人员"}}}
输出 master.json：{meta, columns, rows, questions}；同时在旁边写一份 questions.md 方便直接发给主办方。
"""
import argparse
import csv
import json
import os

from common import dump, email_key, id_key, load, load_config, local_time, search_keys

def show(v):
    return '是' if v is True else '否' if v is False else str(v)


SKIP = {'flags', 'prev', 'subs', 'py', 'sk', 'imgs', 'proofLinks', 'at', 'no', 'src', 'k'}


def load_checkins(paths, cfg):
    """签到记录，支持三种：签到页数据库导出（一组 {k, current, claimed,...} 的 JSON）、一个文件夹的单条 JSON、
    签到页「导出 CSV」或 Google 表格「签到记录」分页导出的 CSV（按列名对回字段）。"""
    c = cfg.get('checkin', {})
    ok = c.get('done_label', '已签到')
    label2key = {v.get('label', k): k for k, v in cfg['fields'].items()}
    label2key.update({o['label']: o['key'] for o in c.get('onsite_fields', [])})
    out = []
    for p in paths:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.endswith('.json'):
                    out.append(json.load(open(os.path.join(p, f), encoding='utf-8')))
        elif p.endswith('.json'):
            d = json.load(open(p, encoding='utf-8'))
            out += d if isinstance(d, list) else [d] if 'k' in d else list(d.values())
        else:
            with open(p, encoding='utf-8-sig', newline='') as f:
                for r in csv.DictReader(f):
                    cur = {}
                    for col, v in r.items():
                        key = label2key.get(col)
                        if key and v != '':
                            cur[key] = True if v == '是' else False if v == '否' else v
                    out.append({'k': r.get('key', ''), 'claimed': r.get(ok) == '是', 'claimedAt': r.get('时间', ''),
                                'current': cur, 'manual': r.get('现场新增') == '是' or r.get('来源', '').startswith('现场')})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config'), ap.add_argument('people'), ap.add_argument('out')
    ap.add_argument('--payment'), ap.add_argument('--checkins', nargs='*', default=[]), ap.add_argument('--resolve')
    a = ap.parse_args()
    cfg = load_config(a.config)
    F = cfg['fields']
    lab = lambda f: F.get(f, {}).get('label', f)
    tz = cfg['event'].get('timezone', 'UTC')
    prio = {s['key']: i for i, s in enumerate(cfg['sources'])}
    label_of = {s['key']: s.get('label', s['key']) for s in cfg['sources']}
    res = load(a.resolve) if a.resolve and os.path.exists(a.resolve) else {}
    same = [set(p) for p in res.get('same', [])]
    different = {frozenset(p) for p in res.get('different', [])}
    excluded = set(res.get('exclude', []))

    recs = sorted([x for x in load(a.people)['rows'] if x['k'] not in excluded], key=lambda x: (prio.get(x['src'], 99), x['no']))
    people, questions = [], []

    def find(x):
        for p in people:
            if any(x['k'] in s and (s & p['_keys']) for s in same):
                return p, '主办方确认是同一人'
        for p in people:
            if frozenset((x['k'], p['k'])) in different or any(frozenset((x['k'], k)) in different for k in p['_keys']):
                continue
            if x.get('id') and id_key(x['id']) in p['_ids']:
                return p, '学号相同'
            if x.get('email') and email_key(x['email']) in p['_emails']:
                return p, '邮箱相同'
        return None, ''

    for x in recs:
        p, why = find(x)
        if p is None:
            p = {'k': x['k'], '_keys': {x['k']}, '_ids': set(), '_emails': set(), '_src': [], '_subs': [], 'notes': [], 'flags': []}
            people.append(p)
        p['_keys'].add(x['k'])
        if x.get('id'):
            p['_ids'].add(id_key(x['id']))
        if x.get('email'):
            p['_emails'].add(email_key(x['email']))
        p['_src'].append(x['src'])
        p['_subs'].append(f"{label_of.get(x['src'], x['src'])}#{x['no']}")
        p['flags'] += x.get('flags', [])
        for f, v in x.items():
            if f in SKIP or f == 'staff' or v in (None, ''):
                continue
            if p.get(f) in (None, ''):
                p[f] = v
            elif str(p[f]).strip() != str(v).strip():
                p['notes'].append(f"{lab(f)}：{label_of.get(x['src'], x['src'])}里填的是「{show(v)}」，按「{show(p[f])}」")
        if x.get('staff') and not p.get('staff'):
            if 'staff' in p:
                p['notes'].append(f"{label_of.get(x['src'], x['src'])}里是{lab('staff')}（{x.get('ticket') or ''}），算{lab('staff')}")
            p['staff'] = True
        p.setdefault('staff', x.get('staff'))

    # 只有名字相同的 → 问主办方
    by_name = {}
    for p in people:
        n = str(p.get('name', '')).replace(' ', '').lower()
        if n:
            by_name.setdefault(n, []).append(p)
    for n, lst in by_name.items():
        if len(lst) > 1:
            pairs = [frozenset((x['k'], y['k'])) for i, x in enumerate(lst) for y in lst[i + 1:]]
            if all(pr in different for pr in pairs):
                continue
            questions.append({'type': 'same_name', 'keys': [p['k'] for p in lst],
                              'text': f"「{lst[0].get('name')}」出现了 {len(lst)} 次（" + '；'.join(
                                  f"{'、'.join(p['_subs'])} {p.get('id') or p.get('email') or ''}" for p in lst) + '），是同一个人吗？'})

    # 缴费
    if a.payment and os.path.exists(a.payment):
        pay = {r['k']: r for r in load(a.payment)['rows']}
        for p in people:
            hits = [pay[k] for k in p['_keys'] if k in pay]
            if hits:
                h = hits[0]
                p.update(pay_status=h['statusLabel'], pay_due=h['due'], pay_paid=h['paid'], pay_note=h['note'])

    # 签到
    onsite = [f['key'] for f in cfg.get('checkin', {}).get('onsite_fields', [])]
    for d in load_checkins(a.checkins, cfg):
        cur = d.get('current') or {}
        if str(cur.get('name', '')).startswith('测试'):
            continue
        p = next((p for p in people if d.get('k') in p['_keys']), None)
        if not p and cur.get('id'):
            p = next((p for p in people if id_key(cur['id']) in p['_ids']), None)
        if not p and cur.get('email'):
            p = next((p for p in people if email_key(cur['email']) in p['_emails']), None)
        if not p and cur.get('name'):
            hit = [p for p in people if p.get('name') == cur['name']]
            if len(hit) == 1:
                p = hit[0]
                p['notes'].append('签到记录按姓名对上')
        if not p:
            p = {'k': d.get('k') or f"onsite-{len(people)}", '_keys': {d.get('k')}, '_ids': set(), '_emails': set(),
                 '_src': ['onsite'], '_subs': ['现场新增'], 'notes': ['名单外，现场登记'], 'flags': []}
            people.append(p)
            questions.append({'type': 'walk_in', 'keys': [p['k']], 'text': f"「{cur.get('name', '?')}」是现场新增的，不在任何报名表里，要收费/核实吗？"})
        if p.get('checked_in') == '是' and d.get('claimed'):
            p['notes'].append('签到了两次，已合并')
        if d.get('claimed'):
            p['checked_in'] = '是'
            p['checked_at'] = local_time(d.get('claimedAt'), tz) if 'T' in str(d.get('claimedAt', '')) else d.get('claimedAt', '')
        else:
            p.setdefault('checked_in', '否')
        for f, v in cur.items():
            if f in onsite and v not in (None, ''):
                p[f] = v
            elif f in F and v not in (None, '') and p.get(f) not in (None, '') and str(p[f]) != str(v):
                p['notes'].append(f"{lab(f)}：现场改成了「{show(v)}」（报名时是「{show(p[f])}」）")
                p[f] = v
            elif f in F and v not in (None, '') and p.get(f) in (None, ''):
                p[f] = v

    for k, ov in res.get('override', {}).items():
        for p in people:
            if k in p['_keys']:
                p.update(ov)
                p['notes'].append('主办方手动修改：' + '、'.join(f'{lab(f)}={v}' for f, v in ov.items()))

    rows = []
    for i, p in enumerate(people, 1):
        r = {k: v for k, v in p.items() if not k.startswith('_')}
        r.update(no=i, _src='、'.join(dict.fromkeys(label_of.get(s, '现场新增') for s in p['_src'])), subs='、'.join(p['_subs']),
                 flags='；'.join(dict.fromkeys(p['flags'])), notes='；'.join(dict.fromkeys(p['notes'])))
        r.setdefault('checked_in', '否' if a.checkins else '')
        r['py'] = search_keys(r.get('name', ''))
        rows.append(r)

    cols = [{'key': 'no', 'label': '序号'}] + [{'key': k, 'label': v.get('label', k), 'type': v.get('type', 'text')} for k, v in F.items()]
    cols += [{'key': '_src', 'label': '来源'}, {'key': 'subs', 'label': '报名记录'}]
    if a.checkins:
        cols += [{'key': 'checked_in', 'label': '已签到'}, {'key': 'checked_at', 'label': '签到时间'}]
        cols += [{'key': f['key'], 'label': f['label']} for f in cfg.get('checkin', {}).get('onsite_fields', []) if f['key'] not in F]
    if a.payment:
        cols += [{'key': 'pay_status', 'label': '缴费核对'}, {'key': 'pay_due', 'label': '应付'}, {'key': 'pay_paid', 'label': '实付'},
                 {'key': 'pay_note', 'label': '缴费备注'}]
    cols += [{'key': 'flags', 'label': '标记'}, {'key': 'notes', 'label': '合并备注'}]
    present = {k for r in rows for k, v in r.items() if v not in (None, '')}
    cols = [c for c in cols if c['key'] in present or c['key'] in ('no', 'name')]
    meta = {'count': len(rows), 'sources': {label_of.get(s, s): sum(1 for r in rows if label_of.get(s, s) in r['_src'])
                                           for s in list(prio) + ['onsite']}}
    dump({'meta': meta, 'columns': cols, 'rows': rows, 'questions': questions}, a.out)
    qpath = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'questions.md')
    with open(qpath, 'w', encoding='utf-8') as f:
        f.write('# 需要主办方确认的问题\n\n' + ('\n'.join(f'{i}. {q["text"]}' for i, q in enumerate(questions, 1)) or '没有问题 🎉') + '\n')
    print(f"{len(recs)} 条记录 → {len(rows)} 人；{len(questions)} 个问题 → {qpath}")


if __name__ == '__main__':
    main()
