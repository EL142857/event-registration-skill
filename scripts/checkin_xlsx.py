"""签到的 Excel 备份（断网 / 网页出问题时，工作人员直接在单元格里打字）。

用法：
    python3 scripts/checkin_xlsx.py config/event.json out/people.json out/签到备份.xlsx [--blank 20]

一张表：名单信息预先填好（按拼音排序），后面是签到要填的列；是/否、选项、打分都做成下拉框；末尾留空行给现场新增。
"""
import argparse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from common import load, load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config'), ap.add_argument('data'), ap.add_argument('out')
    ap.add_argument('--blank', type=int, default=20)
    a = ap.parse_args()
    cfg = load_config(a.config)
    c = cfg.get('checkin', {})
    F = cfg['fields']
    pre = [f for f in ['name', 'id', 'email', 'adult', 'staff', 'ticket'] if f in F]
    onsite = c.get('onsite_fields', [])
    ok = c.get('done_label', '已签到')
    head = ['编号'] + [F[f]['label'] for f in pre] + [f'是否{ok.replace("已", "")}'] + \
           [o['label'] + ('（必填）' if o.get('required') else '') for o in onsite]
    rows = sorted(load(a.data)['rows'], key=lambda r: r.get('sk') or r.get('name', ''))
    wb = Workbook()
    ws = wb.active
    ws.title = (c.get('title') or '签到')[:30]
    ws.append(head)
    for r in rows:
        ws.append([r.get('no')] + [('是' if r.get(f) else '否') if F[f].get('type') == 'bool' else r.get(f, '') for f in pre]
                  + [''] * (1 + len(onsite)))
    for _ in range(a.blank):
        ws.append(['新'] + [''] * (len(head) - 1))
    n = ws.max_row
    hdr = PatternFill('solid', fgColor='E7E5E4')
    fill_col = PatternFill('solid', fgColor='FFFBEB')
    for i, _ in enumerate(head, 1):
        cell = ws.cell(1, i)
        cell.font, cell.fill, cell.alignment = Font(bold=True), hdr, Alignment(vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = 14 if i > 1 else 7
    ws.freeze_panes = 'C2'

    def dropdown(col, options):
        dv = DataValidation(type='list', formula1='"' + ','.join(map(str, options)) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f'{col}2:{col}{n}')

    for i, f in enumerate(pre, 2):
        if F[f].get('type') == 'bool':
            dropdown(get_column_letter(i), ['是', '否'])
    base = len(pre) + 2
    dropdown(get_column_letter(base), ['是', '否'])
    for j, o in enumerate(onsite, base + 1):
        col = get_column_letter(j)
        if o.get('type') == 'choice':
            dropdown(col, o['options'])
        elif o.get('type') == 'scale':
            dropdown(col, list(range(o.get('min', 1), o.get('max', 5) + 1)))
        elif o.get('type') == 'bool':
            dropdown(col, ['是', '否'])
        if o.get('type') == 'textarea':
            ws.column_dimensions[col].width = 28
    for j in range(base, len(head) + 1):
        for i in range(2, n + 1):
            ws.cell(i, j).fill = fill_col
    wb.save(a.out)
    print(f'{len(rows)} 人 + {a.blank} 空行 → {a.out}')


if __name__ == '__main__':
    main()
