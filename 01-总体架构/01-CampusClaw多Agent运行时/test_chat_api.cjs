const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require(process.env.JSDOM_MODULE || 'jsdom');

const source = fs.readFileSync(path.join(__dirname, 'chat-api-review.html'), 'utf8');
const pause = () => new Promise((resolve) => setTimeout(resolve, 20));
const pretty = (value) => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
const create = (markup, runScripts) => {
  const errors = [];
  let renders = 0;
  const dom = new JSDOM(markup, {
    runScripts,
    virtualConsole: new VirtualConsole(),
    beforeParse(window) {
      window.addEventListener('error', (event) => errors.push(event.message));
      const createElement = window.document.createElement.bind(window.document);
      window.document.createElement = (...args) => {
        if (args[0] === 'article') renders += 1;
        return createElement(...args);
      };
    }
  });
  return { dom, errors, renders: () => renders, document: dom.window.document };
};

(async () => {
  const fallback = create(source);
  assert.equal(fallback.document.querySelectorAll('[data-static-review]').length, 10);
  for (const item of fallback.document.querySelectorAll('.catalog-item')) {
    const text = item.textContent;
    for (const label of ['作用', '调用上下文 Header', '参数与请求体', '响应']) {
      assert.ok(text.includes(label));
    }
    assert.ok(item.querySelector('.auth-section .static-choice'));
    assert.ok(item.querySelector('.response-section .static-response'));
  }
  assert.equal(fallback.errors.length, 0);
  fallback.dom.window.close();

  const enhanced = create(source, 'dangerously');
  const { document, dom } = enhanced;
  const surface = document.getElementById('claw-current-api-catalog');
  const items = Array.from(surface.querySelectorAll('.catalog-item'));
  const models = JSON.parse(document.querySelector('[data-review-models]').textContent);
  const initialNodes = surface.querySelectorAll('*').length;
  assert.equal(items.length, 10);
  assert.equal(enhanced.renders(), 0, 'Closed operations must not be initialized');
  assert.equal(surface.querySelectorAll('[data-api-shell] > *').length, 0);
  assert.ok(initialNodes < 200, `Initial live DOM unexpectedly large: ${initialNodes}`);

  let peakNodes = initialNodes;
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    const operation = models[index].operation;
    item.querySelector('summary').click();
    await pause();
    assert.equal(enhanced.renders(), index + 1, 'Only the selected operation should initialize');
    assert.equal(surface.querySelectorAll('.catalog-item[open]').length, 1);
    assert.equal(surface.querySelectorAll('[data-mounted]').length, 1);
    assert.equal(surface.querySelectorAll('[data-api-shell] > article').length, 1);
    assert.ok(item.textContent.includes(operation.description));
    assert.equal(item.querySelectorAll('.catalog-part').length, 3);
    assert.equal(item.querySelectorAll('.catalog-part[open]').length, 0);

    const auth = item.querySelector('.auth-section');
    for (const mode of operation.requestHeaderExamples) {
      auth.querySelector(`[data-auth-id="${mode.id}"]`).click();
      for (const header of mode.headers) {
        assert.ok(auth.textContent.includes(header.value));
        assert.ok(auth.textContent.includes(header.description));
      }
    }
    const response = item.querySelector('.response-section');
    for (const variant of operation.responses) {
      response.querySelector(`[data-response-id="${variant.id || variant.status}"]`).click();
      for (const [locale, payload] of Object.entries(variant.bodies)) {
        const localeButton = Array.from(response.querySelector('.tabs').children)
          .find((button) => button.textContent === locale);
        assert.ok(localeButton);
        localeButton.click();
        assert.ok(response.querySelector('pre code').textContent.includes(pretty(payload)));
      }
    }
    peakNodes = Math.max(peakNodes, surface.querySelectorAll('*').length);
  }

  // Return to a previous operation without rebuilding it or losing its tab state.
  items[0].querySelector('summary').click();
  await pause();
  assert.equal(enhanced.renders(), 10);
  const lastAuth = models[0].operation.requestHeaderExamples.at(-1);
  assert.equal(items[0].querySelector('.auth-section [aria-pressed="true"]').dataset.authId, lastAuth.id);
  assert.equal(surface.querySelectorAll('[data-mounted]').length, 1);

  // Scrolling should neither mount/unmount content nor change the document.
  const mutations = [];
  const observer = new dom.window.MutationObserver((batch) => mutations.push(...batch));
  observer.observe(surface, { attributes: true, childList: true, subtree: true, characterData: true });
  for (let index = 0; index < 100; index += 1) {
    dom.window.dispatchEvent(new dom.window.Event('scroll'));
    surface.dispatchEvent(new dom.window.Event('scroll', { bubbles: true }));
  }
  await pause();
  observer.disconnect();
  assert.equal(mutations.length, 0, 'Scroll must not change the visualization DOM');
  assert.equal(enhanced.renders(), 10);

  assert.equal(enhanced.errors.length, 0, enhanced.errors.join('\n'));
  items[0].querySelector('summary').click();
  await pause();
  assert.equal(surface.querySelectorAll('[data-mounted]').length, 0);
  assert.equal(surface.querySelectorAll('[data-api-shell] > *').length, 0);
  dom.window.close();

  // A retained deep link opens the exact current operation.
  const linked = create(source, 'dangerously');
  linked.dom.window.location.hash = '#submitSessionEvent';
  await pause();
  assert.equal(linked.document.querySelector('.catalog-item[open]').id, 'submitSessionEvent');
  assert.equal(linked.document.querySelectorAll('[data-mounted]').length, 1);
  linked.dom.window.location.hash = '#listSessionEvents';
  await pause();
  assert.equal(linked.document.querySelector('.catalog-item[open]').id, 'listSessionEvents');
  assert.equal(linked.errors.length, 0);
  linked.dom.window.close();

  // Even a runtime failure during a lazy render must restore the native full content.
  const broken = create(source.replace('renderOperation(staging, slot.model);', 'throw new Error("Injected render failure");'), 'dangerously');
  const brokenItem = broken.document.querySelector('.catalog-item');
  brokenItem.querySelector('summary').click();
  await pause();
  assert.equal(brokenItem.querySelectorAll('[data-static-review]').length, 1);
  assert.ok(brokenItem.textContent.includes('调用上下文 Header'));
  assert.ok(brokenItem.querySelector('.static-response'));
  assert.equal(broken.errors.length, 0);
  broken.dom.window.close();

  console.log(JSON.stringify({
    operationsTested: 10,
    initialLiveElements: initialNodes,
    peakLiveElements: peakNodes,
    initialDynamicRenders: 0,
    simultaneousOperationDetails: 1,
    allAuthResponsesLocales: 'passed',
    reopenPreservesState: 'passed',
    scrollMutations: 0,
    noJavaScriptAndRenderFailureFallbacks: 'passed',
    scope: 'DOM interaction checks only; host scrolling and visual layout not measured'
  }, null, 2));
})().catch((error) => { console.error(error); process.exitCode = 1; });
