// 所有页面共用的小工具（render.py 会把它直接写进页面）
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = (s) => String(s ?? '').toLowerCase().replace(/[\s·'’._-]/g, '');
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
}
function fmtTime(iso, tz) {
  if (!iso) return '';
  try {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: tz || undefined, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
    return `${p.month}-${p.day} ${p.hour}:${p.minute}`;
  } catch (_) { return iso; }
}
const yn = (v) => (v === true ? '是' : v === false ? '否' : '');
function fieldText(cfg, f, v) {
  const t = cfg.fields?.[f]?.type;
  if (t === 'bool' || typeof v === 'boolean') return yn(v);
  return v ?? '';
}
let _toastT;
function toast(msg) {
  let t = $('#toast');
  if (!t) { t = h('div', { id: 'toast', class: 'toast' }); document.body.append(t); }
  t.textContent = msg; t.hidden = false; clearTimeout(_toastT); _toastT = setTimeout(() => { t.hidden = true; }, 2200);
}
// 关键词匹配：姓名 / 拼音 / 首字母 / 学号 / 邮箱 / 编号
function matchScore(q, hay, nos) {
  q = norm(q);
  if (!q) return 0;
  if (/^#?\d+$/.test(q) && (nos || []).includes(+q.replace('#', ''))) return 0;
  let best = 9;
  for (const raw of hay) {
    const s = norm(raw);
    if (!s) continue;
    if (s === q) return 0;
    if (s.startsWith(q)) best = Math.min(best, 1);
    else if (s.includes(q)) best = Math.min(best, 2);
  }
  return best;
}
// 导出：在 Claude Artifact 里用 downloads 能力，普通浏览器里直接下载
async function saveFile(filename, text, type = 'text/csv') {
  const blob = new Blob([text], { type });
  try {
    const dl = await window.claude?.use?.('downloads');
    if (dl) { await dl.save({ filename, data: blob }); return; }
  } catch (e) { if (e?.code === 'declined') return; }
  const a = h('a', { href: URL.createObjectURL(blob), download: filename });
  document.body.append(a); a.click(); a.remove();
}
function toCsv(lines) {
  return '﻿' + lines.map((r) => r.map((x) => { const s = String(x ?? ''); return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }).join(',')).join('\r\n');
}
const stamp = () => new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
// 看大图：点缩略图打开，左右键切换
const Viewer = (() => {
  let list = [], i = 0, el;
  function ensure() {
    if (el) return;
    el = h('div', { class: 'viewer', onclick: (e) => { if (e.target === el) close(); } },
      h('img', { alt: '' }), h('div', { class: 'cap' }),
      h('div', { class: 'nav' },
        h('button', { class: 'btn', type: 'button', text: '← 上一张', onclick: () => go(-1) }),
        h('button', { class: 'btn', type: 'button', text: '关闭', onclick: () => close() }),
        h('button', { class: 'btn', type: 'button', text: '下一张 →', onclick: () => go(1) })));
    document.body.append(el);
    document.addEventListener('keydown', (e) => {
      if (!el.classList.contains('on')) return;
      if (e.key === 'Escape') close(); else if (e.key === 'ArrowLeft') go(-1); else if (e.key === 'ArrowRight') go(1);
    });
  }
  function show() { $('img', el).src = list[i].src; $('.cap', el).textContent = `${list[i].cap || ''}（${i + 1}/${list.length}）`; }
  function go(d) { i = (i + d + list.length) % list.length; show(); }
  function open(items, start) { ensure(); list = items; i = start || 0; show(); el.classList.add('on'); }
  function close() { el?.classList.remove('on'); }
  return { open };
})();
