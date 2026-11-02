"""第 1 步：把一份或多份报名表导出（腾讯问卷 / Google Form / 任意 CSV / xlsx）清洗成统一格式。

用法：
    python3 scripts/normalize.py config/event.json out/people.json

做的事：
  * 按配置把各列映射到统一字段（name / id / email / adult / ticket ...），去掉 "A." 选项前缀
  * 是/否 题转成 true/false，票种按 ticket_aliases 统一叫法，工作人员票自动标 staff
  * 提交时间按导出时区换成 UTC
  * 同一来源里同一个人（按 dedupe_by：先学号再邮箱）提交多次：保留最新一份，旧编号记在 prev
  * 按 checks 规则给每个人打标记（未满18岁、邮箱后缀拼错、只坐单程大巴……）
  * 生成拼音搜索词，给名单页 / 签到页 / 抽奖页用

输出 people.json：{meta, rows}。每行是一个人（同一来源内已去重；跨来源合并见 merge.py）。
"""
import re
import sys
from datetime import datetime, timezone

from common import (blank, doc_key, dump, email_key, id_key, load_config, parse_time, read_table,
                    resolve, search_keys, sort_key, strip_option, to_bool)


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def read_source(cfg, src):
    path = resolve(cfg, src['file'])
    head, body = read_table(path)
    col = {h: i for i, h in enumerate(head)}
    missing = [c for c in src.get('columns', {}).values() if c not in col]
    if missing:
        sys.exit(f"[{src['key']}] 表头里找不到这些列：{missing}\n现有列：{head}")
    ftype = {k: v.get('type', 'text') for k, v in cfg['fields'].items()}
    aliases = cfg.get('ticket_aliases', {})
    staff_t = set(cfg.get('staff_tickets', []))
    tz = src.get('export_timezone', cfg['event'].get('timezone', 'UTC'))
    at_cfg = src.get('submitted_at') or {}
    no_col = src.get('submission_no')
    att = src.get('attachments') or {}
    recs = []
    for n, r in enumerate(body, 1):
        g = lambda c: r[col[c]] if c in col else ''
        x = {'src': src['key'], 'no': n, 'at': '', 'flags': []}
        if no_col and no_col in col:
            try:
                x['no'] = int(float(g(no_col)))
            except ValueError:
                pass
        if at_cfg.get('column') in col:
            x['at'] = parse_time(g(at_cfg['column']), at_cfg.get('format'), tz)
        for field, c in src.get('columns', {}).items():
            raw = g(c)
            if ftype.get(field) == 'bool':
                x[field] = to_bool(raw)
            else:
                x[field] = blank(strip_option(raw)) if field not in ('name', 'id', 'email') else strip_option(raw)
        for field, v in (src.get('defaults') or {}).items():
            if x.get(field) in (None, ''):
                x[field] = v
        if x.get('ticket'):
            x['ticket'] = aliases.get(x['ticket'], x['ticket'])
        if 'staff' not in src.get('columns', {}):
            x['staff'] = x.get('ticket') in staff_t
        if att.get('column_prefix'):
            x['proofLinks'] = sum(1 for h, v in zip(head, r) if h.startswith(att['column_prefix']) and 'http' in v)
        if not any(x.get(f) for f in ('name', 'id', 'email')):
            continue  # 空行
        recs.append(x)
    return recs, len(body)


def person_key(x, order):
    for f in order:
        v = id_key(x.get(f)) if f == 'id' else email_key(x.get(f)) if f == 'email' else str(x.get(f) or '').strip().lower()
        if v:
            return f, v
    return 'no', f"{x['src']}-{x['no']}"


def run_checks(cfg, x):
    F = cfg['fields']
    lab = lambda f: F.get(f, {}).get('label', f)
    for c in cfg.get('checks', []):
        t = c['type']
        if t == 'under_18' and x.get('adult') is False:
            x['flags'].append('未满 18 岁')
        elif t == 'id_is_email' and '@' in str(x.get('id') or ''):
            x['flags'].append(f"{lab('id')}填成了邮箱")
        elif t == 'email_domain_typo':
            em = str(x.get('email') or '').strip()
            if em and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', em):
                x['flags'].append('邮箱格式不对')
            elif em:
                dom = em.split('@')[-1].lower()
                for good in c.get('expected', []):
                    if dom != good and edit_distance(dom, good) <= 2:
                        x['flags'].append(f'邮箱后缀可能拼错（应为 {good}？）')
        elif t == 'differs':
            vals = [x.get(f) for f in c['fields']]
            if all(v is not None for v in vals) and len(set(map(str, vals))) > 1:
                x['flags'].append(c.get('message') or '、'.join(map(lab, c['fields'])) + ' 不一致')
        elif t == 'missing':
            for f in c['fields']:
                if f in x and not x.get(f):
                    x['flags'].append(f'没填{lab(f)}')


def main(cfg_path, out_path):
    cfg = load_config(cfg_path)
    order = cfg.get('dedupe_by', ['id', 'email'])
    rows, meta_src = [], []
    for src in cfg['sources']:
        recs, n_lines = read_source(cfg, src)
        groups = {}
        for x in sorted(recs, key=lambda x: (x['at'] or '', x['no'])):
            f, v = person_key(x, order)
            groups.setdefault(v, []).append(x)
        out = []
        for v, lst in groups.items():
            x = dict(lst[-1])
            x['prev'] = [o['no'] for o in lst[:-1]]
            x['subs'] = [o['no'] for o in lst]
            x['k'] = doc_key(v)
            if len(lst) > 1:
                changed = [cfg['fields'].get(f, {}).get('label', f) for f in src.get('columns', {})
                           if len({str(o.get(f)) for o in lst}) > 1]
                x['flags'].append(f"提交了 {len(lst)} 次，以最新一份 #{x['no']} 为准"
                                  + (f"（改过：{'、'.join(changed)}）" if changed else ''))
            run_checks(cfg, x)
            x['py'] = search_keys(x.get('name', ''))
            x['sk'] = sort_key(x.get('name', ''))
            out.append(x)
        out.sort(key=lambda x: x['no'])
        rows += out
        meta_src.append({'key': src['key'], 'label': src.get('label', src['key']), 'submissions': len(recs),
                         'people': len(out), 'exported': max((x['at'] for x in recs), default='')})
        print(f"[{src['key']}] {len(recs)} 份提交 → {len(out)} 人；"
              f"{sum(1 for x in out if x['flags'])} 人有标记")
    # 不同来源之间 key 撞了：给后面的加前缀，避免签到页里两个人共用一个记录（真正合并用 merge.py）
    seen = set()
    for x in rows:
        if x['k'] in seen:
            x['k'] = doc_key(f"{x['src']}-{x['k']}")
        seen.add(x['k'])
    doc = {'meta': {'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'sources': meta_src,
                    'count': len(rows)}, 'rows': rows}
    dump(doc, out_path)
    print('写入', out_path, len(rows), '人')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
