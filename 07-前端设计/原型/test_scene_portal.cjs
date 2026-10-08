// Start the repository's local HTTP preview first; tests cover design fixtures only.
// JSDOM_MODULE=/path/to/jsdom node 07-前端设计/原型/test_scene_portal.cjs
const {JSDOM, VirtualConsole} = require(process.env.JSDOM_MODULE || 'jsdom');
const assert = require('node:assert/strict');
const base = process.env.FRONTEND_PREVIEW_URL || 'http://127.0.0.1:8765/07-前端设计/原型/index.html';
const errors = [], consoleSink = new VirtualConsole();
consoleSink.on('jsdomError', error => errors.push(error.message));
(async () => {
  const dom = await JSDOM.fromURL(base, {resources:'usable', runScripts:'dangerously', virtualConsole:consoleSink});
  try {
    const w = dom.window, d = w.document;
    if (d.readyState !== 'complete') await new Promise(resolve => w.addEventListener('load', resolve, {once:true}));
    const frame = d.getElementById('preview'), $ = id => d.getElementById(id);
    function loaded(action) {
      return new Promise((resolve,reject) => {
        const timer = setTimeout(() => reject(Error('Prototype frame did not load')), 5000);
        frame.addEventListener('load', () => {clearTimeout(timer); resolve();}, {once:true});
        action();
      });
    }
    let states = 0;
    for (const scene of w.frontendScenes) {
      await loaded(() => d.querySelector(`[data-scene="${scene.id}"]`).click());
      for (const [index, state] of scene.states.entries()) {
        if (index) await loaded(() => {$('state').value=state.id; $('state').dispatchEvent(new w.Event('change'));});
        const fw = frame.contentWindow, fd = fw.document;
        assert.equal(fd.documentElement.dataset.view, state.view || scene.view);
        if (fw.tokenDemo) assert.equal(fw.tokenDemo.snapshot.phase, {'token-ready':'ready','token-refreshing':'refreshing','token-failed':'failed'}[state.id]);
        else if (fw.planDemo) assert.equal(fw.planDemo.snapshot.phase, {new:'idle',slash:'planIdle',buildQuestion:'question'}[state.id] || state.id);
        else if ((state.view || scene.view) === 'chat') assert.equal(fd.querySelector('.chat-prototype').dataset.phase, state.id);
        assert.equal(fd.documentElement.dataset.fidelity, 'high');
        const input = fd.querySelector('#draft, #chat-draft, #composer-input');
        if (input && !input.disabled) {input.value = '保真度切换保留草稿'; input.dispatchEvent(new fw.Event('input', {bubbles:true}));}
        const phase = fd.querySelector('[data-phase]')?.dataset.phase;
        $('low').click();
        assert.equal(frame.contentWindow, fw, 'Changing fidelity must not reload the frame');
        assert.equal(fd.documentElement.dataset.fidelity, 'low');
        if (input && !input.disabled) assert.equal(input.value, '保真度切换保留草稿');
        assert.equal(fd.querySelector('[data-phase]')?.dataset.phase, phase);
        $('high').click();
        assert.equal(fd.documentElement.dataset.fidelity, 'high');
        assert.equal(frame.contentWindow, fw);
        assert.match($('document').getAttribute('href'), /场景\//);
        states++;
      }
    }
    // A pending irreversible decision remains pending across fidelity changes.
    await loaded(() => d.querySelector('[data-scene="plan"]').click());
    const fw=frame.contentWindow;fw.document.getElementById('approve').click();
    assert.equal(fw.planDemo.snapshot.phase, 'decisionPending');
    $('low').click();$('high').click();
    assert.equal(fw.planDemo.snapshot.phase, 'decisionPending');
    assert.equal(fw.planDemo.snapshot.writes, 1);
    fw.document.getElementById('receipt').click();
    assert.equal(fw.planDemo.snapshot.phase, 'executing');
    assert.deepEqual(errors, []);
    console.log(`${w.frontendScenes.length} scenes / ${states} entry states passed; fidelity preserves drafts and pending decisions. DOM checks only.`);
  } finally {dom.window.close();}
})().catch(error => {console.error(error);process.exitCode=1;});
