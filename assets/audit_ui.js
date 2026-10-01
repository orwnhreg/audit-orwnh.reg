/* audit_ui.js — shared interactive engine for the register audit pages.
 *
 * Contract with the build scripts:
 *   window.AUDIT_DATA = {current:{fy,month}, fiscal_years:[{key,label,months,has_data}],
 *                        periods:{key:{label,finished,missing,completeness_pct,dept_breakdown,
 *                                     top_missing_cols,progress,unfinished,daily,elapsed}},
 *                        fy_totals:{fy:{...same shape + monthly,trend_vs_prev}}, ...}
 *   AuditUI.init(AUDIT_DATA, {onSelection, tableBody, emptyRowMsg}) -> selection
 *
 * Selection = {fy:"2570", month:"__fy__"|"2569-10", dept:"", col:"", day:"", q:"", sort:null, page:1}
 * كلหน้าใช้ engine เดียวกัน: เลือกปีงบ → เดือน/ทั้งปีงบ แล้วทุก panel ของหน้านั้นวาดใหม่จาก
 * ข้อมูลชุดเดียวกัน (periods / fy_totals) — ไม่มี panel ไหนค้างตัวเลขเก่า.
 */
(function (global) {
  'use strict';
  var FY_ALL = '__fy__';
  var TH_MONTH_SHORT = {1:'ม.ค.',2:'ก.พ.',3:'มี.ค.',4:'เม.ย.',5:'พ.ค.',6:'มิ.ย.',7:'ก.ค.',8:'ส.ค.',9:'ก.ย.',10:'ต.ค.',11:'พ.ย.',12:'ธ.ค.'};

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function qs() {
    var out = {}, raw = global.location.search.replace(/^\?/, '');
    if (!raw) return out;
    raw.split('&').forEach(function (part) {
      var kv = part.split('=');
      if (kv[0]) out[decodeURIComponent(kv[0])] = decodeURIComponent((kv[1] || '').replace(/\+/g, ' '));
    });
    return out;
  }

  function queryOf(sel) {
    var parts = [];
    function add(k, v) { if (v !== '' && v != null) parts.push(k + '=' + encodeURIComponent(v)); }
    add('fy', sel.fy);
    add('month', sel.month);
    add('dept', sel.dept);
    add('col', sel.col);
    add('day', sel.day);
    add('q', sel.q);
    return parts.join('&');
  }

  // ให้สลับแท็บ Dashboard <-> ข้อมูล แล้วตัวเลือก (ปีงบ/เดือน/ตัวกรอง) คงอยู่
  function syncTabLinks(query) {
    Array.prototype.forEach.call(global.document.querySelectorAll('a.tab'), function (a) {
      var base = (a.getAttribute('href') || '').split('?')[0];
      if (base) a.setAttribute('href', base + (query ? '?' + query : ''));
    });
  }

  function setUrl(sel) {
    var query = queryOf(sel);
    syncTabLinks(query);
    if (!global.history || !global.history.replaceState) return;
    global.history.replaceState(null, '', global.location.pathname + (query ? '?' + query : ''));
  }

  // ---- data access -------------------------------------------------------
  function fysOf(data) { return (data.fiscal_years || []).map(function (f) { return f; }); }

  function fyEntry(data, fy) {
    var list = fysOf(data);
    for (var i = 0; i < list.length; i++) if (String(list[i].key) === String(fy)) return list[i];
    return null;
  }

  function block(data, sel) {
    if (sel.month === FY_ALL) return (data.fy_totals || {})[sel.fy] || null;
    return (data.periods || {})[sel.month] || null;
  }

  function isFyScope(sel) { return sel.month === FY_ALL; }

  function scopeLabel(data, sel) {
    if (isFyScope(sel)) {
      var f = fyEntry(data, sel.fy);
      return f ? f.label : 'ปีงบ ' + sel.fy;
    }
    var p = (data.periods || {})[sel.month];
    return p ? p.label : sel.month;
  }

  // ---- cases -------------------------------------------------------------
  function visibleCases(data, sel) {
    var cases = data.all_cases || [];
    var months = null;
    if (isFyScope(sel)) {
      var f = fyEntry(data, sel.fy);
      months = f ? f.months : [];
    }
    return cases.filter(function (c) {
      if (months ? months.indexOf(c.month_key) === -1 : c.month_key !== sel.month) return false;
      if (sel.dept && (c.dept || '') !== sel.dept) return false;
      if (sel.day && String(dayOf(c.date)) !== String(sel.day)) return false;
      if (sel.col && (c.missing || []).indexOf(sel.col) === -1) return false;
      if (sel.q) {
        var hay = [c.hn, c.name, c.dept, c.op, (c.circ || '')].join(' ').toLowerCase();
        if (hay.indexOf(sel.q.toLowerCase()) === -1) return false;
      }
      return true;
    });
  }

  function dayOf(date) { var p = String(date || '').split('/'); return p.length ? parseInt(p[0], 10) : 0; }

  function sortCases(cases, sort) {
    if (!sort || !sort.key) return cases;
    var dir = sort.dir === 'desc' ? -1 : 1;
    var copy = cases.slice();
    copy.sort(function (a, b) {
      var av, bv;
      if (sort.key === 'date') { av = [dayOf(a.date), a.date]; bv = [dayOf(b.date), b.date]; }
      else if (sort.key === 'days') { av = a.days_pending == null ? -1 : a.days_pending; bv = b.days_pending == null ? -1 : b.days_pending; }
      else { av = String(a[sort.key] || ''); bv = String(b[sort.key] || ''); }
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return copy;
  }

  // ---- charts ------------------------------------------------------------
  function dailyBars(daily) {
    if (!daily || !daily.length) return '<p class="all-clear">ไม่มีข้อมูล</p>';
    var max = 0;
    daily.forEach(function (d) { if (d.total > max) max = d.total; });
    if (!max) max = 1;
    var bars = daily.map(function (d) {
      var total = d.total || 0, missing = d.missing || 0;
      var ok = Math.max(total - missing, 0);
      var h = total ? (total / max * 100) : 0;
      var title = 'วันที่ ' + d.day + ': ทั้งหมด ' + total + ', ไม่ครบ ' + missing;
      return '<div class="bar-col" data-day="' + d.day + '" data-drill="day" data-value="' + d.day + '" title="' + esc(title) + '">' +
        '<div class="bar-stack" style="height:' + h + '%">' +
          '<div class="bar-seg bar-missing" style="height:' + (total ? missing / total * 100 : 0) + '%"></div>' +
          '<div class="bar-seg bar-ok" style="height:' + (total ? ok / total * 100 : 0) + '%"></div>' +
        '</div><span class="bar-label">' + d.day + '</span></div>';
    }).join('');
    return '<div class="chart-wrap"><div class="chart-legend">' +
      '<span class="legend-item"><i class="legend-dot legend-ok"></i>ครบ</span>' +
      '<span class="legend-item"><i class="legend-dot legend-missing"></i>ไม่ครบ</span>' +
      '</div><div class="bar-chart">' + bars + '</div></div>';
  }

  function monthBars(monthly) {
    if (!monthly || !monthly.length) return '<p class="all-clear">ไม่มีข้อมูล</p>';
    var max = 0;
    monthly.forEach(function (m) { if (m.total > max) max = m.total; });
    if (!max) max = 1;
    var bars = monthly.map(function (m) {
      var total = m.total || 0, missing = m.missing || 0;
      var ok = Math.max(total - missing, 0);
      var h = total ? (total / max * 100) : 0;
      return '<div class="bar-col" data-month="' + esc(m.key) + '" data-drill="month" data-value="' + esc(m.key) + '" title="' + esc(m.label + ': ทั้งหมด ' + total + ', ไม่ครบ ' + missing) + '">' +
        '<div class="bar-stack" style="height:' + h + '%">' +
          '<div class="bar-seg bar-missing" style="height:' + (total ? missing / total * 100 : 0) + '%"></div>' +
          '<div class="bar-seg bar-ok" style="height:' + (total ? ok / total * 100 : 0) + '%"></div>' +
        '</div><span class="bar-label">' + esc(m.label) + '</span></div>';
    }).join('');
    return '<div class="chart-wrap"><div class="chart-legend">' +
      '<span class="legend-item"><i class="legend-dot legend-ok"></i>ครบ</span>' +
      '<span class="legend-item"><i class="legend-dot legend-missing"></i>ไม่ครบ</span>' +
      '</div><div class="bar-chart">' + bars + '</div></div>';
  }

  function chartHtml(data, sel) {
    if (isFyScope(sel)) {
      var fy = block(data, sel);
      return monthBars(fy ? fy.monthly : []);
    }
    var p = block(data, sel);
    return dailyBars(p ? p.daily : []);
  }

  // ---- progress ----------------------------------------------------------
  function progressHtml(data, sel) {
    var b = block(data, sel) || {};
    var prog = b.progress || { total: 0, pending: 0, resolved: 0, ever: 0 };
    var total = prog.total || 0;
    var resolvedPct = total ? prog.resolved / total * 100 : 0;
    var pendingPct = total ? prog.pending / total * 100 : 0;
    var restPct = Math.max(100 - resolvedPct - pendingPct, 0);
    return { prog: prog, resolvedPct: resolvedPct, pendingPct: pendingPct, restPct: restPct };
  }

  function completenessText(data, sel) {
    var b = block(data, sel);
    if (!b || b.completeness_pct == null) return { text: '—', cls: 'pct-none', empty: true };
    var pct = b.completeness_pct;
    var cls = pct >= 97 ? 'pct-good' : (pct >= 90 ? 'pct-warn' : 'pct-bad');
    return { text: pct + '%', cls: cls, empty: false };
  }

  // ---- init --------------------------------------------------------------
  function init(data, opts) {
    opts = opts || {};
    var q = qs();
    var cur = data.current || { fy: null, month: null };
    var fy = String(q.fy || cur.fy || '');
    if (!fyEntry(data, fy)) fy = String(cur.fy || (fysOf(data)[0] || {}).key || '');
    var entry = fyEntry(data, fy) || { months: [] };
    var month = q.month || cur.month || FY_ALL;
    if (month !== FY_ALL && entry.months.indexOf(month) === -1) month = FY_ALL;
    if (month === FY_ALL && entry.months.indexOf(cur.month) !== -1 && !q.month && cur.fy === fy) {
      month = cur.month;   // เดือนปัจจุบันของปีงบปัจจุบัน = ค่าเริ่มต้น
    }
    var sel = {
      fy: fy,
      month: month,
      dept: q.dept || '',
      col: q.col || '',
      day: q.day || '',
      q: q.q || '',
      sort: null,
      page: 1
    };

    var fySel = global.document.getElementById('fySelect');
    var monthSel = global.document.getElementById('monthSelect');
    var searchInput = global.document.getElementById('caseSearch');
    var pageSel = global.document.getElementById('pageSize');
    var chipHost = global.document.getElementById('activeFilters');
    var tableBody = opts.tableBody ? global.document.getElementById(opts.tableBody) : null;
    if (tableBody) tableBody = tableBody.querySelector('tbody') || tableBody;

    function fyOptions() {
      return fysOf(data).map(function (f) {
        return '<option value="' + esc(f.key) + '"' + (String(f.key) === String(sel.fy) ? ' selected' : '') + '>' +
          esc(f.label) + (f.has_data ? '' : ' · ยังไม่มีข้อมูล') + '</option>';
      }).join('');
    }

    function monthOptions() {
      var e = fyEntry(data, sel.fy) || { months: [] };
      var out = ['<option value="' + FY_ALL + '"' + (sel.month === FY_ALL ? ' selected' : '') + '>ทั้งปีงบ (รวมทุกเดือน)</option>'];
      e.months.forEach(function (k) {
        var p = (data.periods || {})[k] || {};
        var suffix = p.finished ? ' — ' + p.finished + ' เคส' : ' — ยังไม่มีข้อมูล';
        out.push('<option value="' + esc(k) + '"' + (k === sel.month ? ' selected' : '') + '>' +
          esc(p.label || k) + esc(suffix) + '</option>');
      });
      return out.join('');
    }

    function renderChips() {
      if (!chipHost) return;
      var chips = [];
      function chip(k, label) {
        chips.push('<button class="filter-chip" data-clear="' + esc(k) + '">' + esc(label) + ' ✕</button>');
      }
      if (sel.dept) chip('dept', 'แผนก: ' + sel.dept);
      if (sel.col) chip('col', 'ช่องที่ขาด: ' + sel.col);
      if (sel.day) chip('day', 'วันที่ ' + sel.day);
      if (sel.q) chip('q', 'ค้นหา: ' + sel.q);
      chipHost.innerHTML = chips.length
        ? '<span class="chip-label">กรองอยู่:</span>' + chips.join('') + '<button class="filter-chip filter-chip-clear" data-clear="__all__">ล้างทั้งหมด</button>'
        : '';
    }

    function renderTable() {
      if (!tableBody) return { shown: 0, total: 0 };
      var cases = sortCases(visibleCases(data, sel), sel.sort);
      var pageSize = pageSel ? parseInt(pageSel.value, 10) || 0 : 0;
      var maxPage = pageSize ? Math.max(Math.ceil(cases.length / pageSize), 1) : 1;
      if (sel.page > maxPage) sel.page = maxPage;
      var slice = pageSize ? cases.slice((sel.page - 1) * pageSize, sel.page * pageSize) : cases;
      var wanted = {};
      slice.forEach(function (c) { wanted[c.hn + '|' + c.date] = true; });
      var shown = 0;
      Array.prototype.forEach.call(tableBody.children, function (tr) {
        var key = tr.getAttribute('data-key');
        var show = !!wanted[key];
        tr.style.display = show ? '' : 'none';
        if (show) shown++;
      });
      var pager = global.document.getElementById('pager');
      if (pager) {
        if (pageSize && cases.length > pageSize) {
          var btns = '';
          for (var i = 1; i <= maxPage; i++) {
            btns += '<button class="page-btn' + (i === sel.page ? ' active' : '') + '" data-page="' + i + '">' + i + '</button>';
          }
          pager.innerHTML = '<span class="page-info">แสดง ' + slice.length + ' จาก ' + cases.length + ' เคส</span>' + btns;
          pager.style.display = '';
        } else {
          pager.innerHTML = '<span class="page-info">ทั้งหมด ' + cases.length + ' เคส</span>';
          pager.style.display = cases.length ? '' : 'none';
        }
      }
      var noMsg = global.document.getElementById('noCasesMsg');
      if (noMsg) noMsg.style.display = cases.length ? 'none' : '';
      return { shown: shown, total: cases.length };
    }

    function apply(reason) {
      sel.fy = String(sel.fy);
      if (fySel) fySel.innerHTML = fyOptions();
      if (monthSel) monthSel.innerHTML = monthOptions();
      if (searchInput && searchInput.value !== sel.q) searchInput.value = sel.q;
      renderChips();
      var res = renderTable();
      if (opts.onSelection) opts.onSelection(sel, data, res);
      setUrl(sel);
    }

    if (fySel) fySel.addEventListener('change', function () {
      sel.fy = fySel.value; sel.month = FY_ALL; sel.dept = sel.col = sel.day = ''; sel.page = 1;
      var cur2 = data.current || {};
      var e2 = fyEntry(data, sel.fy);
      if (e2 && String(cur2.fy) === String(sel.fy) && e2.months.indexOf(cur2.month) !== -1) sel.month = cur2.month;
      apply('fy');
    });
    if (monthSel) monthSel.addEventListener('change', function () {
      sel.month = monthSel.value; sel.page = 1;
      apply('month');
    });
    if (searchInput) {
      var t = null;
      searchInput.addEventListener('input', function () {
        global.clearTimeout(t);
        t = global.setTimeout(function () { sel.q = searchInput.value.trim(); sel.page = 1; apply('q'); }, 180);
      });
    }
    if (pageSel) pageSel.addEventListener('change', function () { sel.page = 1; apply('page'); });

    if (chipHost) chipHost.addEventListener('click', function (ev) {
      var btn = ev.target.closest ? ev.target.closest('[data-clear]') : null;
      if (!btn) return;
      var k = btn.getAttribute('data-clear');
      if (k === '__all__') { sel.dept = sel.col = sel.day = sel.q = ''; if (searchInput) searchInput.value = ''; }
      else sel[k] = '';
      sel.page = 1;
      apply('chip');
    });

    // drill-down: chart bars / department bars / missing-column rows
    var page = global.document.body;
    page.addEventListener('click', function (ev) {
      var el = ev.target.closest ? ev.target.closest('[data-drill]') : null;
      if (!el) return;
      var kind = el.getAttribute('data-drill');
      var value = el.getAttribute('data-value') || '';
      if (kind === 'day') { sel.day = (sel.day === value ? '' : value); }
      else if (kind === 'dept') { sel.dept = (sel.dept === value ? '' : value); }
      else if (kind === 'col') { sel.col = (sel.col === value ? '' : value); }
      else if (kind === 'month') {
        sel.month = value; sel.page = 1; apply('drill'); return;
      }
      sel.page = 1;
      apply('drill');
    });

    // sortable headers
    if (tableBody && tableBody.parentElement) {
      var thead = tableBody.parentElement.querySelector('thead');
      if (thead) thead.addEventListener('click', function (ev) {
        var th = ev.target.closest ? ev.target.closest('th[data-sort]') : null;
        if (!th) return;
        var key = th.getAttribute('data-sort');
        if (sel.sort && sel.sort.key === key) sel.sort = { key: key, dir: sel.sort.dir === 'asc' ? 'desc' : 'asc' };
        else sel.sort = { key: key, dir: 'asc' };
        Array.prototype.forEach.call(thead.querySelectorAll('th[data-sort]'), function (h) {
          h.classList.remove('sorted-asc', 'sorted-desc');
        });
        th.classList.add(sel.sort.dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
        apply('sort');
      });
    }

    if (global.document.getElementById('pager')) {
      global.document.getElementById('pager').addEventListener('click', function (ev) {
        var b = ev.target.closest ? ev.target.closest('[data-page]') : null;
        if (!b) return;
        sel.page = parseInt(b.getAttribute('data-page'), 10);
        apply('pager');
      });
    }

    apply('init');
    return sel;
  }

  global.AuditUI = {
    init: init,
    visibleCases: visibleCases,
    sortCases: sortCases,
    block: block,
    scopeLabel: scopeLabel,
    isFyScope: isFyScope,
    chartHtml: chartHtml,
    dailyBars: dailyBars,
    monthBars: monthBars,
    progressHtml: progressHtml,
    completenessText: completenessText,
    FY_ALL: FY_ALL,
    esc: esc
  };

  // กดป้ายแจ้งเตือน (chip) แล้วอธิบายเกณฑ์ — ใช้ได้ทั้งสองหน้า
  var RULE_EXPLAIN = {
    'HN ซ้ำต่างคน': 'HN เดียวกัน ผ่าตัดวันเดียวกัน แต่คนละชื่อ — ตรวจ HN จากเอกสารต้นฉบับ',
    'AN ซ้ำข้ามคน': 'AN เดียวกันอยู่คนละ HN ภายใน 3 วัน — เช็ก AN ว่าตัวใดตัวหนึ่งผิด',
    'ห้องซ้อนเวลา': 'วันเดียวกันห้องเดียวกัน ช่วงเวลาคาบกัน — ส่วนใหญ่เวลาลงผิด เช็กเวลาก่อนสรุป',
    'ห้องผ่าตัดซ้ำกัน': 'ห้องเดียวกันแต่คนละแพทย์ — ลงเลขห้องผิด ตรวจว่าอีกเคสอยู่ห้องไหน',
    'เวลาผ่าตัดไม่สัมพันธ์กัน': 'ลำดับเวลา เข้าห้อง→เริ่ม→เสร็จ→ออก ไม่สัมพันธ์กัน หรือห่างกันเกิน 12 ชั่วโมง — แก้เวลาให้ถูกต้อง',
    'รูปแบบเวลาเพี้ยน': 'รูปแบบเวลาไม่ใช่ ชั่วโมง:นาที:วินาที — แก้ให้เป็นรูปแบบเวลา',
    'ชื่อซ้ำในทีม': 'ชื่อเดียวกันอยู่ 2 บทบาทในทีมชุดเดียวกัน — แก้ชื่อให้ถูกคน',
    'AN': 'AN ว่าง — ODS และตึกผู้ป่วยในต้องมี AN (ยกเว้น OPD)',
    'Address': 'ที่อยู่ว่าง — กรอกที่อยู่ หรือโน้ตเหตุผลไว้ในหมายเหตุ',
    'ค่าหัตถการ': 'ราคาหัตถการว่าง — ต้องมีทุกเคส',
    'เวร': 'เคสนอกเวลาแต่ไม่ลงเวร — ลงรหัสเวร',
    'Team': 'เคสนอกเวลาแต่ไม่ลงทีม — ลงรหัสทีม',
    'HN': 'HN ว่าง — กรอก HN ให้ครบทุกเคส',
    'Aneasthesia': 'วิธีระงับความรู้สึกว่าง — กรอกข้อมูลให้ครบ'
  };
  function ruleExplain(label) {
    if (RULE_EXPLAIN[label]) return RULE_EXPLAIN[label];
    if (label.indexOf('หมายเหตุเรื่องที่อยู่') === 0) return 'โน้ตประกอบจากช่องหมายเหตุ ไม่ใช่ค่าที่อยู่จริง';
    if (label.indexOf('ทีมเวร') >= 0 || label === 'Assistant' || label === 'Scrub' ||
        label === 'Circulating' || label === 'Nurse Aid') return 'บทบาททีมนี้ว่าง — กรอกชื่อทีมให้ครบ (Eye ยกเว้น Assistant)';
    return 'ป้ายนี้บอกสาเหตุที่เคสถูกแจ้ง — แก้ข้อมูลในทะเบียนแล้วรายงานจะหายเอง';
  }
  function showRuleToast(text) {
    var doc = global.document;
    var t = doc.getElementById('ruleToast');
    if (!t) {
      t = doc.createElement('div');
      t.id = 'ruleToast';
      t.addEventListener('click', function () { t.className = ''; });
      doc.body.appendChild(t);
    }
    t.textContent = text;
    t.className = 'show';
    if (showRuleToast._t) global.clearTimeout(showRuleToast._t);
    showRuleToast._t = global.setTimeout(function () { t.className = ''; }, 5000);
  }
  if (global.document && global.document.addEventListener) {
    global.document.addEventListener('click', function (ev) {
      var chip = ev.target.closest ? ev.target.closest('.chip[data-rule]') : null;
      if (!chip) return;
      showRuleToast(ruleExplain(chip.getAttribute('data-rule')));
    });
  }
})(window);
