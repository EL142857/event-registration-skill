"""第 2 步（可选）：把问卷附件（缴费凭证等）对应到每个人，压缩成网页能用的 JPEG。

用法：
    python3 scripts/proofs.py config/event.json out/people.json <附件文件夹或 zip> [来源 key]

  * 附件文件名按配置里的 attachments.file_pattern 认人（腾讯问卷"下载附件"是 "<编号>_q10_原文件名"）
  * 一个人重填过的话，所有提交里的附件都会收进来（同名同大小的只算一次）
  * 图片转正方向、缩到 1600px、存成 out/proof/<来源>_<编号>_<序号>.jpg
  * 不同的人上传了同一张图（内容 md5 相同）→ 两个人都打上标记
  * 结果写回 people.json：每个人多一个 imgs 列表
"""
import hashlib
import os
import re
import sys
import tempfile
import zipfile

from common import dump, load, load_config


def main(cfg_path, people_path, att, src_key=None):
    cfg = load_config(cfg_path)
    src = next((s for s in cfg['sources'] if s.get('attachments') and (src_key in (None, s['key']))), None)
    if not src:
        sys.exit('配置里没有带 attachments 的来源')
    pat = src['attachments'].get('file_pattern', r'^{no}_')
    doc = load(people_path)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(people_path)), 'proof')
    os.makedirs(out_dir, exist_ok=True)

    tmp = None
    if zipfile.is_zipfile(att):
        tmp = tempfile.mkdtemp(prefix='att_')
        with zipfile.ZipFile(att) as z:
            for info in z.infolist():
                name = os.path.basename(info.filename)
                if info.is_dir() or not name:
                    continue
                with z.open(info) as fsrc, open(os.path.join(tmp, name), 'wb') as fdst:
                    fdst.write(fsrc.read())
        att = tmp
    files = []
    for root, _, names in os.walk(att):
        files += [os.path.join(root, n) for n in names]

    from PIL import Image, ImageOps
    hashes = {}
    n_img = 0
    for x in doc['rows']:
        if x['src'] != src['key']:
            continue
        x['imgs'] = []
        seen = set()
        for no in x.get('subs', [x['no']]):
            rx = re.compile(pat.replace('{no}', str(no)))
            for f in sorted(f for f in files if rx.search(os.path.basename(f))):
                sig = (re.sub(r'^\d+_', '', os.path.basename(f)), os.path.getsize(f))
                if sig in seen:
                    continue
                seen.add(sig)
                rel = f"proof/{src['key']}_{no}_{len(x['imgs']) + 1}.jpg"
                try:
                    im = ImageOps.exif_transpose(Image.open(f)).convert('RGB')
                except Exception as e:  # 不是图片（pdf 等）就只记文件名
                    x['imgs'].append({'file': os.path.basename(f), 'sub': no, 'error': f'不是图片：{e.__class__.__name__}'})
                    continue
                im.thumbnail((1600, 1600))
                im.save(os.path.join(out_dir, os.path.basename(rel)), quality=78)
                small = im.copy()
                small.thumbnail((240, 240))
                x['imgs'].append({'src': rel, 'sub': no, 'w': im.width, 'h': im.height,
                                  'tiny': small.width * small.height < 60 * 60})
                n_img += 1
                h = hashlib.md5(open(f, 'rb').read()).hexdigest()
                hashes.setdefault(h, []).append(x)
        if not x['imgs']:
            x['flags'].append('没有上传凭证')
    if any(c['type'] == 'duplicate_image' for c in cfg.get('checks', [])):
        for lst in hashes.values():
            people = {id(p): p for p in lst}
            if len(people) > 1:
                for p in people.values():
                    others = '、'.join(f"#{o['no']} {o['name']}" for o in people.values() if o is not p)
                    p['flags'].append(f'凭证图和 {others} 是同一张')
    dump(doc, people_path)
    print(f'{n_img} 张图 → {out_dir}；没有凭证 {sum(1 for x in doc["rows"] if x["src"] == src["key"] and not x.get("imgs"))} 人')


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:])
