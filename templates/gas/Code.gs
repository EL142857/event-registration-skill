/**
 * 签到页的 Google 表格后台（Apps Script）。由 scripts/build_gas.py 生成，不需要手改。
 *
 * 网页每次确认都写进下面这个 Google 表格的两个分页（不存在会自动创建，其他分页不会被读写）：
 *   「记录」每人一行，是当前状态：报名时的信息、现场改过的信息、时间、确认人；最后一列是程序用的 JSON
 *   「日志」每次确认 / 修改 / 撤销都追加一行
 */
const CONF = __GAS_CONFIG__;

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle(CONF.title)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover');
}

// ---------- 给网页调用的接口 ----------
/** 所有人的当前状态 { k: record }（去掉操作历史，轮询用） */
function getChecks() {
  const out = {};
  readAll_().forEach(function (x) { const r = x.rec; delete r.history; out[r.k] = r; });
  return out;
}

/** 保存一条记录（网页已经算好整条记录，这里加锁写入，并补上历史） */
function saveRecord(json) {
  const rec = JSON.parse(json);
  if (!rec || !rec.k) throw new Error('记录格式不对');
  if (rec.claimed) {
    const missing = CONF.required.filter(function (f) { const v = rec.current && rec.current[f]; return v === null || v === undefined || v === ''; });
    if (missing.length) throw new Error('请先填写：' + missing.map(function (f) { return CONF.labels[f] || f; }).join('、'));
  }
  return withLock_(function () {
    const sh = sheet_(CONF.recordsTab, head_());
    const found = find_(rec.k);
    const prevHist = found && found.rec.history ? found.rec.history : [];
    const last = (rec.history || []).slice(-1)[0];
    rec.history = prevHist.concat(last ? [last] : []).slice(-50);
    write_(sh, found ? found.row : null, rec);
    if (last) log_(rec, last);
    return JSON.stringify(rec);
  });
}

// ---------- 表格读写 ----------
function head_() {
  const h = ['key', '编号', '来源', CONF.okLabel, '时间', '确认人'];
  CONF.editable.forEach(function (f) { h.push(CONF.labels[f] + '(报名)', CONF.labels[f]); });
  CONF.onsite.forEach(function (f) { h.push(CONF.labels[f]); });
  return h.concat(['改过的信息', '最后保存', '保存次数', 'data（程序用，请勿修改）']);
}
function sheet_(name, head) {
  const ss = SpreadsheetApp.openById(CONF.sheetId);
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, head.length).setValues([head]).setFontWeight('bold').setBackground('#e7e5e4');
    sh.setFrozenRows(1);
  }
  return sh;
}
function readAll_() {
  const head = head_();
  const sh = sheet_(CONF.recordsTab, head);
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  const vals = sh.getRange(2, head.length, n, 1).getValues();
  const out = [];
  vals.forEach(function (v, i) {
    if (!v[0]) return;
    try { out.push({ row: i + 2, rec: JSON.parse(v[0]) }); } catch (e) { /* 被手动改坏的行跳过 */ }
  });
  return out;
}
function find_(k) { return readAll_().filter(function (x) { return x.rec.k === k; })[0] || null; }
function show_(f, v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'boolean') return v ? '是' : '否';
  return v;
}
function write_(sh, row, r) {
  const o = r.original || {}, c = r.current || {};
  const line = [r.k, r.no === null ? '' : r.no, r.source || '', r.claimed ? '是' : '否', time_(r.claimedAt), r.claimedBy || ''];
  CONF.editable.forEach(function (f) { line.push(show_(f, o[f]), show_(f, c[f])); });
  CONF.onsite.forEach(function (f) { line.push(show_(f, c[f])); });
  line.push((r.changed || []).map(function (f) { return CONF.labels[f] || f; }).join('、'), time_(r.updatedAt), r.saves || 0, JSON.stringify(r));
  if (row) sh.getRange(row, 1, 1, line.length).setValues([line]);
  else sh.appendRow(line);
}
function log_(r, e) {
  const sh = sheet_(CONF.logTab, ['时间', '操作', '编号', '姓名', '操作人', '改动']);
  const diff = Object.keys(e.diff || {}).map(function (f) {
    return (CONF.labels[f] || f) + '：' + (show_(f, e.diff[f][0]) || '未填') + ' → ' + (show_(f, e.diff[f][1]) || '未填');
  }).join('；');
  sh.appendRow([time_(e.at, true), e.action, r.no === null ? '现场新增' : r.no, (r.current && r.current.name) || '', e.by || '', diff]);
}
function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try { return fn(); } finally { lock.releaseLock(); }
}
function time_(iso, sec) { return iso ? Utilities.formatDate(new Date(iso), CONF.timezone, sec ? 'MM-dd HH:mm:ss' : 'MM-dd HH:mm') : ''; }
