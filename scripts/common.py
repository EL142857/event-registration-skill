"""共用工具：读配置、读问卷导出、字段清洗、拼音搜索词。

只用标准库；拼音（pypinyin）、Excel（openpyxl）、图片（Pillow）都是可选依赖，
没装时对应功能自动降级。
"""
import csv
import itertools
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TRUE = {'是', '有', '需要', '要', '会', '愿意', 'yes', 'y', 'true', '1', '√', '✓'}
FALSE = {'否', '无', '没有', '不需要', '不要', '不会', '不愿意', 'no', 'n', 'false', '0', '×'}
BLANK = {'', '无', '没有', '/', '-', '—', 'n/a', 'na', 'none', 'null', '暂无', '无。', '0'}


# ---------- 配置 ----------
def load_config(path):
    cfg = json.load(open(path, encoding='utf-8'))
    cfg['_dir'] = os.path.dirname(os.path.abspath(path))
    cfg.setdefault('fields', {})
    for k, label in (('name', '姓名'), ('id', 'ID'), ('email', '邮箱'), ('adult', '已满18岁'),
                     ('ticket', '票种'), ('staff', '工作人员')):
        cfg['fields'].setdefault(k, {'label': label})
    cfg['fields']['adult'].setdefault('type', 'bool')
    cfg['fields']['staff'].setdefault('type', 'bool')
    return cfg


def resolve(cfg, p):
    """配置里的相对路径相对于项目根目录（config 文件所在目录的上一级，或当前目录）。"""
    if not p or os.path.isabs(p):
        return p
    for base in (os.getcwd(), os.path.dirname(cfg['_dir']), cfg['_dir']):
        q = os.path.join(base, p)
        if os.path.exists(q):
            return q
    return os.path.join(os.getcwd(), p)


def public_config(cfg):
    """写进网页的配置：去掉文件路径等内部信息。"""
    out = {k: v for k, v in cfg.items() if not k.startswith('_') and k != 'sources'}
    out['sources'] = [{'key': s['key'], 'label': s.get('label', s['key'])} for s in cfg.get('sources', [])]
    return out


# ---------- 读表 ----------
def read_table(path):
    """读 CSV（自动去 BOM）或 xlsx，返回 (表头, 行列表)。"""
    if path.lower().endswith(('.xlsx', '.xlsm')):
        import openpyxl
        ws = openpyxl.load_workbook(path, data_only=True).active
        rows = [['' if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)]
    else:
        with open(path, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    head = [h.strip() for h in rows[0]]
    body = [r + [''] * (len(head) - len(r)) for r in rows[1:]]
    return head, body


# ---------- 单元格清洗 ----------
def strip_option(v):
    """腾讯问卷选项会带 'A.' 前缀；'其他〖xxx〗' 取括号里的填空。"""
    v = str(v or '').strip().strip('\t').strip()
    v = re.sub(r'^[A-Z][.．、]\s*', '', v)
    m = re.match(r'^其他[〖\[(（](.*)[〗\])）]$', v)
    return m.group(1).strip() if m else v


def to_bool(v):
    s = strip_option(v).lower().rstrip('。.!！')
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    if s.startswith(('是', '需要', 'yes')):
        return True
    if s.startswith(('否', '不', 'no')):
        return False
    return None


def blank(v):
    s = str(v or '').strip()
    return '' if s.lower() in BLANK else s


def norm_key(v):
    """去重用的 key：小写、去空白、邮箱去掉 @ 后面（学号常被填成邮箱）。"""
    s = re.sub(r'\s', '', str(v or '')).lower()
    return s


def id_key(v):
    s = norm_key(v)
    return s.split('@')[0] if s else ''


def email_key(v):
    return norm_key(v)


def doc_key(v):
    """数据库文档 id 只允许安全字符。"""
    return re.sub(r'[^a-z0-9_\-.~:@+]', '_', str(v).strip().lower()) or 'x'


def parse_time(s, fmt=None, tz='UTC'):
    """返回 UTC ISO 字符串；解析不了返回空。"""
    s = str(s or '').strip()
    if not s:
        return ''
    fmts = [fmt] if fmt else []
    fmts += ['%d-%b-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%m/%d/%Y %H:%M:%S',
             '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M']
    for f in fmts:
        try:
            t = datetime.strptime(s, f)
            break
        except (ValueError, TypeError):
            continue
    else:
        try:
            t = datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            return ''
    if t.tzinfo is None:
        t = t.replace(tzinfo=ZoneInfo(tz))
    return t.astimezone(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')


def local_time(iso, tz, fmt='%m-%d %H:%M'):
    if not iso:
        return ''
    t = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    return t.astimezone(ZoneInfo(tz)).strftime(fmt)


# ---------- 拼音 ----------
def search_keys(name):
    """姓名的拼音全拼、首字母、名在前写法；英文名的各种拼法。搜索框用。"""
    keys = set()
    han = ''.join(re.findall(r'[一-鿿]', name or ''))
    latin = [w.lower() for w in re.findall(r'[A-Za-z]+', name or '')]
    if han:
        try:
            from pypinyin import pinyin, Style
            opts = [list(dict.fromkeys(p))[:3] for p in pinyin(han, style=Style.NORMAL, heteronym=True)]
            for combo in itertools.islice(itertools.product(*opts), 12):
                keys |= {''.join(combo), ''.join(s[0] for s in combo), ''.join(combo[1:]) + combo[0]}
        except ImportError:
            pass
    if latin:
        keys |= {''.join(latin), ''.join(reversed(latin)), ''.join(w[0] for w in latin)} | set(latin)
    keys |= {k.replace('v', 'u') for k in keys if 'v' in k}
    return ' '.join(sorted(k for k in keys if k))


def sort_key(name):
    try:
        from pypinyin import lazy_pinyin
        return ''.join(lazy_pinyin(name or '')).lower().replace(' ', '')
    except ImportError:
        return (name or '').lower()


# ---------- 输出 ----------
def dump(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def load(path):
    return json.load(open(path, encoding='utf-8'))


def inject(template_path, out_path, **parts):
    """把 /*__NAME__*/null 或 __NAME__ 占位符换成 JSON / 文本。"""
    s = open(template_path, encoding='utf-8').read()
    for name, value in parts.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False).replace('</', '<\\/')
        s = s.replace(f'/*__{name}__*/null', text).replace(f'/*__{name}__*/', text).replace(f'__{name}__', text)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    open(out_path, 'w', encoding='utf-8').write(s)
    return len(s.encode())
