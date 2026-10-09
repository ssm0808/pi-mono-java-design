// Local DOM regression for the design fixture; no service or product verification.
// JSDOM_MODULE=/path/to/jsdom node 07-前端设计/原型/test_schedule_review.cjs
const {JSDOM} = require(process.env.JSDOM_MODULE || 'jsdom');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, 'schedule-review.html'), 'utf8');
const code = fs.readFileSync(path.join(__dirname, 'schedule-review.js'), 'utf8');
function fixture(state) {
  const dom = new JSDOM(html, {url: 'http://fixture.local/schedule-review.html' + (state ? '?state='+state : ''), runScripts:'outside-only'});
  const w = dom.window, $ = id => w.document.getElementById(id);
  w.eval(code);
  function input(id, value) {$(id).value=value;$(id).dispatchEvent(new w.Event('input',{bubbles:true}));}
  function mode(value) {const e=w.document.querySelector(`input[value=${value}]`); e.checked=true;e.dispatchEvent(new w.Event('change',{bubbles:true}));}
  return {dom,w,$,input,mode,get snapshot(){return w.scheduleDemo.snapshot;}};
}
let count=0;
function check(state, run) {const f=fixture(state);try{run(f);count++;}finally{f.dom.window.close();}}
check(undefined,f=>{
  assert.equal(f.snapshot.trigger,'manual','New tasks must not register an automatic schedule implicitly');
  f.input('task-name','手动巡检');f.input('instructions','读取工单');
  f.$('save').click();assert.equal(f.snapshot.saved.schedule,null);assert.equal(f.snapshot.writeCount,1);
  assert.equal(f.$('run-result').hidden,true,'Saving must not run the task');
});
check('custom',f=>{
  f.input('expression','30 17 8 * * MON-FRI');f.input('instructions','草稿内容');
  f.mode('manual');f.mode('schedule');
  assert.equal(f.$('expression').value,'30 17 8 * * MON-FRI');
  f.w.designPreview.setFidelity('low');f.w.designPreview.setFidelity('high');
  assert.equal(f.$('instructions').value,'草稿内容');assert.equal(f.$('expression').value,'30 17 8 * * MON-FRI');
  f.input('expression','0 8 * * 1-5');f.$('save').click();
  assert.equal(f.snapshot.writeCount,0,'Five-field Cron must not be silently accepted');
  assert.match(f.$('feedback').textContent,/6 项/);
});
check('paused',f=>{
  f.mode('manual');f.$('save').click();assert.equal(f.snapshot.saved.schedule,null);
  assert.equal(f.snapshot.saved.status,'paused','Trigger changes must not unpause the task');
  assert.equal(f.$('pause').hidden,true);assert.equal(f.$('run').disabled,false);
  f.$('run').click();f.$('run').click();assert.equal(f.snapshot.writeCount,2,'Repeated run clicks while pending must not dispatch twice');
  assert.match(f.$('run-result').textContent,/运行请求已提交/);
});
check('schedule',f=>{
  f.$('unknown-save').checked=true;f.$('save').click();
  assert.equal(f.snapshot.uncertain,true);assert.equal(f.snapshot.writeCount,1);
  f.w.designPreview.setFidelity('low');f.$('save').click();assert.equal(f.snapshot.writeCount,1);
  assert.equal(f.$('instructions').value.length>0,true);assert.equal(f.$('saved-panel').hidden,true);
  f.$('check').click();assert.equal(f.snapshot.uncertain,false);assert.equal(f.snapshot.writeCount,1,'Read-only reconciliation must not write');
  assert.equal(f.$('saved-panel').hidden,false);
});
check('schedule',f=>{
  f.$('save').click();assert.equal(f.$('saved-future').querySelectorAll('time').length,5);
  f.$('edit').click();f.input('at','09:00');assert.equal(f.$('future-times').hidden,true);
  f.$('save').click();assert.equal(f.$('saved-future').querySelectorAll('time').length,0,'A changed rule must not reuse stale fixture times');
  assert.match(f.$('saved-future').textContent,/暂无/);
});
console.log(`${count} schedule fixture scenarios passed: explicit mode, lossless drafts, paused edits, unknown writes and stale times.`);
