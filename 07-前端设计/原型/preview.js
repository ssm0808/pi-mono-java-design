(() => {
  'use strict';
  const query = new URLSearchParams(location.search), $ = id => document.getElementById(id);
  const view = query.get('view') || (window.planDemo ? 'plan' : $('conversation-scenario') ? 'chat' : 'slash');
  document.documentElement.dataset.view = view;
  const setFidelity = value => { document.documentElement.dataset.fidelity = value === 'low' ? 'low' : 'high'; };
  window.designPreview = Object.freeze({ setFidelity });
  setFidelity(query.get('fidelity'));
  const state = query.get('state');
  if (window.planDemo) {
    if (state === 'new') $('new-chat').click();
    else if ([...$('scenario').options].some(option => option.value === state)) {
      $('scenario').value = state; window.planDemo.reset(state);
    }
    document.querySelector('.demo-panel').open = false;
  } else if ($('conversation-scenario')) {
    const select = $('conversation-scenario');
    if ([...select.options].some(option => option.value === state)) {
      select.value = state; select.dispatchEvent(new Event('change', { bubbles: true }));
    }
    const rail = document.querySelector('.chat-rail'), toggle = document.createElement('button');
    toggle.id = 'chat-nav-toggle'; toggle.type = 'button'; toggle.textContent = '会话';
    toggle.setAttribute('aria-label', '打开或关闭会话导航'); toggle.setAttribute('aria-expanded', 'false');
    function close() { rail.dataset.open = 'false'; toggle.setAttribute('aria-expanded', 'false'); }
    toggle.onclick = () => { const open = rail.dataset.open !== 'true'; rail.dataset.open = String(open); toggle.setAttribute('aria-expanded', String(open)); };
    document.querySelector('.chat-header').prepend(toggle);
    rail.addEventListener('click', event => { if (event.target.closest('[data-chat-select]')) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && rail.dataset.open === 'true') { close(); toggle.focus(); } });
    document.addEventListener('click', event => { if (!rail.contains(event.target) && event.target !== toggle) close(); });
  } else if (view === 'slash' && ['catalog', 'argument', 'options', 'newChat', 'running', 'help', 'unmatched'].includes(state)) {
    location.hash = state;
  }
})();
