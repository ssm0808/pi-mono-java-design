(() => {
  'use strict';
  const $ = id => document.getElementById(id), q = new URLSearchParams(location.search);
  let saved = null, editing = q.get('state') === 'paused', uncertain = false, writeCount = 0, runPending = false;
  const textFields = ['task-name','instructions','description','credentials','metadata','timezone','expression','at'];
  const fixtureTimes = ['2026-10-09T00:00:00Z','2026-10-12T00:00:00Z','2026-10-13T00:00:00Z','2026-10-14T00:00:00Z','2026-10-15T00:00:00Z'];
  function trigger() { return document.querySelector('input[name=trigger]:checked').value; }
  function expression() {
    if ($('frequency').value === 'custom') return $('expression').value.trim();
    const [hour,minute] = $('at').value.split(':').map(Number);
    const day = $('frequency').value === 'weekly' ? $('weekday').value : $('frequency').value === 'weekdays' ? 'MON-FRI' : '*';
    return `0 ${minute} ${hour} * * ${day}`;
  }
  function tell(value,error = false) { $('feedback').hidden = false; $('feedback').textContent = value; $('feedback').dataset.error = String(error); }
  function mode() {
    const scheduled = trigger() === 'schedule', custom = $('frequency').value === 'custom';
    $('schedule-fields').hidden = !scheduled; $('manual-note').hidden = scheduled;
    $('custom-field').hidden = !custom; $('preset-fields').hidden = custom;
    $('weekday-field').hidden = $('frequency').value !== 'weekly'; $('rule-summary').hidden = custom;
    $('rule').textContent = expression();
    $('save-note').textContent = saved?.status === 'paused' ? '保存修改保持暂停，不会恢复自动运行。' : scheduled ? '保存后按计划自动运行，不会立即执行。' : '保存为手动任务，不会立即执行。';
    $('paused-note').hidden = saved?.status !== 'paused';
  }
  function dirty() { $('future-note').textContent = '保存后根据服务端结果显示。修改中的规则尚未保存。'; $('future-times').hidden = true; mode(); }
  function lock(value) {
    uncertain = value;
    document.querySelectorAll('#task-form input, #task-form textarea, #task-form select, #task-form button').forEach(el => { el.disabled = value || el.id === 'agent'; });
  }
  function timeList(record, container) {
    container.replaceChildren();
    if (!record.schedule) { container.textContent = '仅手动运行，没有自动计划。'; return; }
    const h = document.createElement('h3'); h.textContent = '未来五次计划时间'; container.append(h);
    const hint = document.createElement('p'); hint.className = 'hint';
    hint.textContent = record.status === 'paused' ? '任务已暂停。以下为规则时间，不会自动触发。' : '计划时间按任务时区显示，实际开始时间以运行记录为准。'; container.append(hint);
    if (!record.schedule.upcomingRunsAt.length) { const p=document.createElement('p'); p.className='hint';p.textContent='本地原型未提供该规则的服务端时间样例。'; container.append(p);return; }
    const list = document.createElement('ol'); list.className = 'future';
    for (const value of record.schedule.upcomingRunsAt) {
      const li=document.createElement('li'), t=document.createElement('time'); t.dateTime=value;
      t.textContent = new Intl.DateTimeFormat('zh-CN',{timeZone:record.schedule.timezone,dateStyle:'full',timeStyle:'short'}).format(new Date(value)) + ' · ' + record.schedule.timezone;
      li.append(t);list.append(li);
    }
    container.append(list);
  }
  function details() {
    $('task-form').hidden=true; $('saved-panel').hidden=false; $('title').textContent=saved.name; $('crumb').textContent='任务详情';
    $('lifecycle').textContent=saved.status === 'paused' ? '已暂停' : '可用';
    $('run').disabled=runPending; $('run-result').hidden=!runPending;
    $('saved-trigger').textContent=saved.schedule ? '定时 · Schedule' : '手动 · Manual';
    $('saved-instructions').textContent=saved.instructions; timeList(saved,$('saved-future'));
    $('pause').hidden=!saved.schedule; $('pause').textContent=saved.status === 'paused' ? '恢复自动运行' : '暂停自动运行';
  }
  $('task-form').addEventListener('submit',e => {
    e.preventDefault(); if (uncertain) return;
    if (!$('task-form').reportValidity()) return;
    if (!$('task-name').value.trim()) { tell('任务名称不可为空白。',true); $('task-name').focus(); return; }
    const credentialIds=$('credentials').value.split('\n').map(s=>s.trim()).filter(Boolean);
    if (credentialIds.length>16 || new Set(credentialIds).size !== credentialIds.length) { tell('凭据引用最多 16 个，不可重复。',true);return; }
    try {
      const metadata=JSON.parse($('metadata').value || '{}');
      if (!metadata || Array.isArray(metadata) || typeof metadata!=='object' || Object.entries(metadata).length>16 || Object.entries(metadata).some(([k,v])=>!k||k.length>64||typeof v!=='string'||v.length>512)) throw Error();
    } catch (_) { $('metadata').closest('details').open=true;tell('元数据须为最多 16 对字符串键值。',true);$('feedback').focus();return; }
    let rule=null;
    if (trigger()==='schedule') {
      const zone=$('timezone').value.trim(), cron=expression();
      if (cron.split(/\s+/).length !== 6) {tell('Cron 需要六字段：秒、分、时、日、月、周。',true);return;}
      try { new Intl.DateTimeFormat('zh-CN',{timeZone:zone}); if(!zone)throw Error(); } catch(_) {tell('请输入有效 IANA 时区。',true);return;}
      rule={type:'cron',expression:cron,timezone:zone,upcomingRunsAt:cron==='0 0 8 * * MON-FRI'&&zone==='Asia/Shanghai'?[...fixtureTimes]:[]};
    }
    writeCount++;
    saved={name:$('task-name').value.trim(),instructions:$('instructions').value, schedule:rule,status:saved?.status || 'active',credentialIds};
    if ($('unknown-save').checked) {lock(true);tell('保存结果待确认。草稿已保留，请先核对任务记录；不会自动重新提交。',true);$('feedback').focus();return;}
    tell('已保存示例配置，尚未立即运行。');details();
  });
  document.querySelectorAll('input[name=trigger]').forEach(el=>el.addEventListener('change',dirty));
  [...textFields,'frequency','weekday'].forEach(id=>$(id).addEventListener('input',dirty));
  $('edit-cron').onclick=()=>{$('expression').value=expression();$('frequency').value='custom';dirty();$('expression').focus();};
  $('use-preset').onclick=()=>{$('frequency').value='weekdays';dirty();};
  $('edit').onclick=()=>{editing=true;$('saved-panel').hidden=true;$('task-form').hidden=false;$('title').textContent='编辑任务';$('crumb').textContent='编辑任务';$('save').textContent='保存修改';mode();};
  $('cancel').onclick=()=>{if(saved)details();else tell('草稿已保留。请从导航返回场景目录。');};
  $('pause').onclick=()=>{saved.status=saved.status==='paused'?'active':'paused';tell(saved.status==='paused'?'已暂停后续自动运行；仍可手动运行。':'已恢复后续计划，不补跑错过的时间。');details();};
  $('run').onclick=()=>{if(uncertain||$('run').disabled)return;writeCount++;runPending=true;$('run').disabled=true;$('run-result').hidden=false;$('run-result').textContent='手动运行已受理 · 已建立新的独立会话（示例），业务结果待查看。';};
  $('check').onclick=()=>{if(!uncertain){tell('当前没有待核对的保存。');return;}lock(false);tell('已从示例记录核对保存结果，没有再次写入。');details();};
  if (['schedule','paused','custom'].includes(q.get('state'))) document.querySelector('input[value=schedule]').checked=true;
  if (['schedule','paused','custom'].includes(q.get('state'))) { $('task-name').value='园区设备告警汇总';$('instructions').value='汇总最近 24 小时的设备告警，按设施和严重程度整理，并列出需要跟进的工单。'; }
  if(q.get('state')==='custom')$('frequency').value='custom';
  if(editing){saved={name:$('task-name').value,instructions:$('instructions').value,status:'paused',schedule:{type:'cron',expression:expression(),timezone:'Asia/Shanghai',upcomingRunsAt:fixtureTimes}};$('save').textContent='保存修改';$('title').textContent='编辑任务';}
  window.designPreview={setFidelity:value=>document.documentElement.dataset.fidelity=value==='low'?'low':'high'};
  window.scheduleDemo={get snapshot(){return {trigger:trigger(),uncertain,writeCount,saved};}};
  window.designPreview.setFidelity(q.get('fidelity'));mode();
})();
