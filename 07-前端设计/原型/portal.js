(() => {
  'use strict';
  const $ = id => document.getElementById(id), scenes = window.frontendScenes;
  let active, state, fidelity = 'high', frameKey = '';
  function params() { return new URLSearchParams(location.hash.slice(1)); }
  function updateHash() {
    const value = new URLSearchParams({ scene: active.id, fidelity, state: state.id });
    history.replaceState(null, '', '#' + value);
  }
  function applyFidelity() {
    $('high').setAttribute('aria-pressed', String(fidelity === 'high'));
    $('low').setAttribute('aria-pressed', String(fidelity === 'low'));
    try { $('preview').contentWindow.designPreview?.setFidelity(fidelity); } catch (_) { /* Local file policies may isolate iframe origins. */ }
    $('standalone').href = previewUrl();
  }
  function previewUrl() {
    const query = new URLSearchParams({ view: state.view || active.view, state: state.id, fidelity });
    return (state.frame || active.frame) + '?' + query;
  }
  function openFrame(force = false) {
    const key = active.id + ':' + state.id;
    if (key === frameKey && !force) { applyFidelity(); return; }
    frameKey = key;
    $('load-status').hidden = false;
    $('preview').src = previewUrl();
    $('preview').title = active.title + ' · ' + state.label;
    $('standalone').href = previewUrl();
  }
  function choose(id, selectedState, force = false) {
    active = scenes.find(scene => scene.id === id) || scenes[5];
    state = active.states.find(item => item.id === selectedState) || active.states[0];
    for (const button of $('scenes').children) button.setAttribute('aria-current', button.dataset.scene === active.id ? 'page' : 'false');
    $('state').replaceChildren(...active.states.map(item => new Option(item.label, item.id)));
    $('state').value = state.id;
    $('goal').textContent = active.goal + (fidelity === 'low' ? ' · 低保真：区域与顺序' : '');
    $('document').href = active.doc;
    $('detail-title').textContent = active.title;
    $('coverage').textContent = active.coverage;
    $('tradeoff').textContent = ''; $('steps').replaceChildren();
    applyFidelity(); openFrame(force); updateHash();
  }
  for (const [i, scene] of scenes.entries()) {
    const button = document.createElement('button');
    button.textContent = String(i + 1).padStart(2, '0') + ' ' + scene.title;
    button.dataset.scene = scene.id;
    button.onclick = () => choose(scene.id);
    $('scenes').append(button);
  }
  for (const level of ['high', 'low']) $(level).onclick = () => {
    fidelity = level; applyFidelity(); updateHash();
    $('goal').textContent = active.goal + (fidelity === 'low' ? ' · 低保真：区域与顺序' : '');
  };
  $('state').onchange = () => choose(active.id, $('state').value);
  $('reset').onclick = () => choose(active.id, state.id, true);
  $('preview').onload = () => { $('load-status').hidden = true; applyFidelity(); };
  $('behavior').onclick = async () => {
    const scene = active;
    $('details').showModal();
    $('tradeoff').textContent = '正在读取场景说明…';
    try {
      const response = await fetch(scene.doc);
      if (!response.ok) throw Error('Scene document unavailable');
      const markdown = await response.text();
      if (active !== scene) return;
      const interaction = markdown.split('## 交互行为')[1]?.split('## ')[0] || '';
      const rows = interaction.split('\n').filter(line => line.startsWith('|')).slice(2);
      $('steps').replaceChildren(...rows.map(line => {
        const tr = document.createElement('tr');
        for (const value of line.split('|').slice(1, -1)) { const td = document.createElement('td'); td.textContent = value.trim(); tr.append(td); }
        return tr;
      }));
      $('tradeoff').textContent = markdown.split('## 取舍')[1]?.split('## ')[0].trim() || '详见场景说明。';
    } catch (_) {
      $('tradeoff').textContent = '请通过“场景说明”查看完整行为；本地文件模式可改用本地 HTTP 预览。';
    }
  };
  $('close').onclick = () => $('details').close();
  function loadHash() {
    const query = params(); fidelity = query.get('fidelity') === 'low' ? 'low' : 'high';
    choose(query.get('scene'), query.get('state'));
  }
  window.addEventListener('hashchange', loadHash);
  loadHash();
})();
