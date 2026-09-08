// DOM-only regression for the local design fixture, not a production API/E2E test.
// Run: JSDOM_MODULE=/absolute/path/to/jsdom node test_frontend_review.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_MODULE || 'jsdom');
const html = fs.readFileSync(path.join(__dirname, 'frontend-review.html'), 'utf8');
const cases = [];

function fixture() {
  const errors = [];
  let networkCalls = 0;
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', (error) => errors.push(error));
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    virtualConsole,
    beforeParse(window) {
      const blocked = () => { networkCalls += 1; throw Error('Fixture must not call a network API'); };
      window.fetch = blocked;
      window.XMLHttpRequest = blocked;
      window.WebSocket = blocked;
      window.EventSource = blocked;
    }
  });
  const { window } = dom;
  const document = window.document;
  const get = (id) => document.getElementById(id);
  const change = (element, value, type = 'input') => {
    element.value = value;
    element.dispatchEvent(new window.Event(type, { bubbles: true }));
  };
  return {
    window, document, get, change,
    click: (id) => get(id).click(),
    draft: (value) => change(get('chat-draft'), value),
    scenario: (value) => change(get('conversation-scenario'), value, 'change'),
    phase: () => document.querySelector('.chat-prototype').dataset.phase,
    finish() {
      assert.deepEqual(errors, [], 'Inline scripts must not raise errors');
      assert.equal(networkCalls, 0);
      dom.window.close();
    }
  };
}

function test(name, run) {
  const f = fixture();
  try {
    run(f);
    // Opaque-origin localStorage is intentionally inaccessible; fixture has no persistence API calls.
    assert.doesNotMatch(html.slice(html.lastIndexOf('<script>')), /localStorage|sessionStorage|indexedDB/);
    f.finish();
    cases.push(name);
  } catch (error) {
    f.window.close();
    throw new Error(name, { cause: error });
  }
}

test('running keeps a draft without queuing', (f) => {
  f.draft('下一步检查');
  assert.equal(f.get('chat-send').disabled, true);
  f.click('chat-send');
  assert.equal(f.phase(), 'running');
  f.click('simulate-terminal');
  assert.equal(f.phase(), 'ready');
  assert.equal(f.get('chat-draft').value, '下一步检查');
  assert.equal(f.get('chat-send').disabled, false);
});

test('2048 Unicode code points and optional files', (f) => {
  f.scenario('ready');
  assert.equal(f.get('chat-send').disabled, true);
  f.draft('😀'.repeat(2048));
  assert.equal(f.get('chat-send').disabled, false);
  f.draft('😀'.repeat(2049));
  assert.equal(f.get('chat-send').disabled, true);
  f.draft('');
  for (let i = 0; i < 5; i += 1) f.click('chat-add-file');
  assert.equal(f.get('chat-attachments').children.length, 4);
  assert.equal(f.get('chat-add-file').disabled, true);
  assert.equal(f.get('chat-send').disabled, false);
  f.click('chat-send');
  f.click('simulate-receipt');
  assert.equal(f.get('chat-attachments').children.length, 0);
  assert.match(f.get('chat-user').textContent, /4 个示例附件/);
});

test('IME and Shift+Enter never submit', (f) => {
  f.scenario('ready'); f.draft('选字');
  const input = f.get('chat-draft');
  input.dispatchEvent(new f.window.Event('compositionstart'));
  input.dispatchEvent(new f.window.KeyboardEvent('keydown', { key: 'Enter' }));
  f.click('chat-send');
  assert.equal(f.phase(), 'ready');
  input.dispatchEvent(new f.window.Event('compositionend'));
  input.dispatchEvent(new f.window.KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
  assert.equal(f.phase(), 'ready');
  input.dispatchEvent(new f.window.KeyboardEvent('keydown', { key: 'Enter' }));
  assert.equal(f.phase(), 'submitting');
});

test('complete receipt preserves edits made after submission', (f) => {
  f.scenario('ready'); f.draft('原消息'); f.click('chat-add-file'); f.click('chat-send');
  assert.equal(f.get('chat-draft').value, '原消息');
  f.draft('新草稿'); f.click('chat-add-file'); f.click('simulate-receipt');
  assert.equal(f.get('chat-user').textContent, '原消息\n已提交 1 个示例附件');
  assert.equal(f.get('chat-draft').value, '新草稿');
  assert.equal(f.get('chat-attachments').children.length, 1);
  assert.equal(f.phase(), 'running');
  assert.equal(f.get('chat-send').disabled, true);
});

test('allow receipt is not tool completion', (f) => {
  f.scenario('confirming'); f.draft('保留草稿'); f.click('chat-allow');
  assert.equal(f.phase(), 'confirmingSubmit');
  assert.equal(f.get('chat-allow').disabled, true);
  assert.equal(f.get('chat-deny').disabled, true);
  f.click('simulate-receipt');
  assert.equal(f.phase(), 'running');
  assert.match(f.get('chat-tool-output').textContent, /尚未收到结果/);
  assert.equal(f.get('chat-send').disabled, true);
});

test('deny reason validation, optional reason and no whole-turn failure', (f) => {
  f.scenario('confirming'); f.click('chat-deny');
  f.change(f.get('chat-deny-reason'), '   '); f.click('chat-deny-submit');
  assert.equal(f.phase(), 'confirming');
  f.change(f.get('chat-deny-reason'), '😀'.repeat(2049)); f.click('chat-deny-submit');
  assert.equal(f.phase(), 'confirming');
  f.change(f.get('chat-deny-reason'), ''); f.click('chat-deny-submit'); f.click('simulate-receipt');
  assert.equal(f.phase(), 'running');
  assert.match(f.get('chat-notice').textContent, /拒绝决定已接受/);
  f.click('simulate-terminal');
  assert.equal(f.phase(), 'ready');
  assert.match(f.get('chat-tool-output').textContent, /未执行/);
  assert.match(f.get('chat-answer').textContent, /任务已完成/);
});

test('stop request, receipt and actual termination stay separate', (f) => {
  f.draft('停止后再发'); f.click('chat-stop');
  assert.equal(f.phase(), 'stopRequested');
  assert.equal(f.get('chat-stop').disabled, true);
  f.click('simulate-receipt');
  assert.equal(f.phase(), 'stopAccepted');
  assert.equal(f.get('chat-send').disabled, true);
  f.click('simulate-terminal');
  assert.equal(f.phase(), 'ready');
  assert.match(f.get('chat-tool-output').textContent, /尚未收到结果/);
  assert.match(f.get('chat-answer').textContent, /实际停止记录/);
});

test('unknown submission stays unknown after history without a receipt', (f) => {
  f.scenario('uncertain'); f.draft('待核实草稿'); f.click('chat-check');
  assert.equal(f.phase(), 'recovering');
  f.click('simulate-history');
  assert.equal(f.phase(), 'uncertain');
  assert.equal(f.get('chat-draft').value, '待核实草稿');
  assert.equal(f.get('chat-send').disabled, true);
});

test('last history page is not execution completion', (f) => {
  f.scenario('offline'); f.draft('断线草稿'); f.click('chat-check'); f.click('simulate-history');
  assert.equal(f.phase(), 'running');
  assert.equal(f.get('chat-send').disabled, true);
  assert.match(f.get('chat-history-note').textContent, /末页/);
});

test('configuration refresh requires a separate explicit modification', (f) => {
  f.scenario('conflict'); f.draft('配置不影响草稿'); f.click('chat-config-reload');
  assert.equal(f.phase(), 'conflict');
  assert.match(f.get('chat-config-label').textContent, /模型 B/);
  assert.match(f.get('chat-notice').textContent, /尚未发起写入/);
  f.click('chat-config-confirm');
  assert.equal(f.phase(), 'ready');
  assert.match(f.get('chat-config-label').textContent, /模型 A · 深度思考关闭/);
  assert.equal(f.get('chat-draft').value, '配置不影响草稿');
});

test('existing Headers validation remains independent', (f) => {
  const row = f.document.querySelector('[data-header-row]');
  f.change(row.querySelector('.header-key'), 'X-Test');
  assert.match(row.querySelector('.header-error').textContent, /同时填写/);
  f.change(row.querySelector('.header-value'), 'fixture');
  assert.equal(row.querySelector('.header-error').textContent, '');
  assert.ok(f.document.querySelectorAll('[data-header-row]').length >= 2);
  f.change(row.querySelector('.header-key'), 'Host');
  assert.match(row.querySelector('.header-error').textContent, /禁止/);
});

// No DOM geometry assertions: jsdom is not a layout engine.
assert.match(html, /color-scheme:\s*light\s*;/);
assert.doesNotMatch(html, /class="(?:follow-up-mode|command-glyph)"/);
console.log(`${cases.length} prototype state scenarios passed; no browser layout or backend integration claim.`);
