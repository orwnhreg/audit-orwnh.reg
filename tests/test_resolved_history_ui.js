const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const window = { document: { addEventListener() {} }, location: { search: '' } };
vm.runInNewContext(fs.readFileSync('assets/audit_ui.js', 'utf8'), { window });
const ui = window.AuditUI;

const data = {
  fiscal_years: [
    { key: '2570', months: ['2569-10', '2569-11'] },
    { key: '2569', months: ['2568-10'] },
  ],
  resolved_cases: [
    { date: '1/10/2569', hn: '101', dept: 'Eye', missing: ['AN'], month_key: '2569-10' },
    { date: '2/11/2569', hn: '102', dept: 'ODS', missing: ['Address'], month_key: '2569-11' },
    { date: '5/10/2568', hn: '103', dept: 'OR', missing: ['<img src=x>'], month_key: '2568-10' },
  ],
};

assert.deepEqual(
  ui.resolvedCases(data, { fy: '2570', month: '2569-10' }).map((c) => c.hn),
  ['101'],
  'month scope should show only that month'
);
assert.deepEqual(
  ui.resolvedCases(data, { fy: '2570', month: ui.FY_ALL }).map((c) => c.hn),
  ['102', '101'],
  'fiscal-year scope should include its months, newest first'
);
const html = ui.resolvedHistoryHtml(data, { fy: '2569', month: ui.FY_ALL });
assert.match(html, /HN 103/);
assert.match(html, /&lt;img src=x&gt;/);
assert.doesNotMatch(html, /<img src=x>/);
console.log('resolved history UI tests passed');
