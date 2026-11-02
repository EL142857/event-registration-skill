"""第 3 步（可选）：缴费凭证核对。

用法：
    python3 scripts/payment.py config/event.json out/people.json out/verdicts.json out/payment.json

  * 按 config.payment 算每个人应付多少：票价 + 附加项（如大巴）
  * 读人工/Claude 看图后写下的结论 verdicts.json：{ "<k>": {"status": "ok|coupon|check|free", "paid": "£80", "note": "..."} }
  * 没有结论的人先给一个自动建议：
      - 没有凭证图                  → check「没有凭证」
      - 票种在 always_review_tickets → check「按规则一律核实」
      - 应付 0                      → free
      - 其余                         → pending（待看图）
  * 把还要看图的人写进 verdicts.todo.json（含应付金额和图片路径），看完图后把结论抄进 verdicts.json 再跑一次
"""
import os
import sys

from common import dump, load, load_config

LABEL = {'ok': '无误', 'coupon': '用了优惠码（待验证）', 'check': '需要核实', 'free': '免费', 'pending': '待看图'}


def due_of(pay, x):
    price = pay.get('prices', {}).get(x.get('ticket'))
    items = []
    if price is None:
        items.append(('票价未知：' + str(x.get('ticket') or '未填票种'), 0))
    else:
        items.append((x.get('ticket') or '票', price))
    for a in pay.get('addons', []):
        hit_any = any(x.get(f) for f in a.get('when_any', []))
        hit_all = bool(a.get('when_all')) and all(x.get(f) for f in a['when_all'])
        if hit_any or hit_all:
            items.append((a['label'], a['price']))
    return sum(p for _, p in items), items, price is None


def main(cfg_path, people_path, verdict_path, out_path):
    cfg = load_config(cfg_path)
    pay = cfg.get('payment') or sys.exit('配置里没有 payment')
    cur = cfg['event'].get('currency', '')
    doc = load(people_path)
    V = load(verdict_path) if os.path.exists(verdict_path) else {}
    review = set(pay.get('always_review_tickets', []))
    rows, todo = [], {}
    for x in doc['rows']:
        due, items, unknown = due_of(pay, x)
        v = V.get(x['k'])
        if v:
            st, paid, note = v.get('status', 'check'), v.get('paid', ''), v.get('note', '')
        else:
            paid = ''
            if x.get('ticket') in review:
                st, note = 'check', f"{x.get('ticket')}按规则一律核实"
            elif unknown:
                st, note = 'check', '票种不在价格表里'
            elif 'imgs' in x and not x['imgs'] and due > 0:
                st, note = 'check', '没有凭证'
            elif due == 0:
                st, note = 'free', '应付 0'
            else:
                st, note = 'pending', ''
            if st in ('pending',) or (st == 'check' and x.get('imgs')):
                todo[x['k']] = {'name': x.get('name'), 'ticket': x.get('ticket'), 'due': f'{cur}{due}',
                                'items': [f'{a} {cur}{b}' for a, b in items], 'imgs': [i.get('src') for i in x.get('imgs', [])],
                                'status': '', 'paid': '', 'note': ''}
        rows.append({'k': x['k'], 'src': x['src'], 'no': x['no'], 'subs': x.get('subs', [x['no']]), 'name': x.get('name', ''),
                     'id': x.get('id', ''), 'ticket': x.get('ticket', ''), 'staff': x.get('staff'), 'py': x.get('py', ''),
                     'items': [f'{a} {cur}{b}' for a, b in items], 'due': due, 'status': st, 'statusLabel': LABEL.get(st, st),
                     'paid': paid, 'note': note, 'imgs': x.get('imgs', []), 'flags': x.get('flags', [])})
    missing = set(V) - {r['k'] for r in rows}
    if missing:
        print('注意：verdicts.json 里有这些 key 在名单里找不到：', sorted(missing))
    from collections import Counter
    c = Counter(r['status'] for r in rows)
    dump({'meta': {**doc['meta'], 'currency': cur, 'payee': pay.get('payee', ''), 'counts': dict(c)}, 'rows': rows}, out_path)
    todo_path = os.path.join(os.path.dirname(os.path.abspath(verdict_path)), 'verdicts.todo.json')
    dump(todo, todo_path)
    print('结果：', ', '.join(f'{LABEL.get(k, k)} {n}' for k, n in c.items()), f'→ {out_path}')
    print(f'{len(todo)} 人需要看图下结论 → {todo_path}')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
