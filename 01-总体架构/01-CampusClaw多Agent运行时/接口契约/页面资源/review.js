(() => {
  const modelNode = document.getElementById('api-review-models');
  if (!modelNode) return;
  const models = JSON.parse(modelNode.textContent);
  const roots = document.querySelectorAll('[data-operation-review]');
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const append = (parent, ...children) => {
    children.filter(Boolean).forEach((child) => parent.appendChild(child));
    return parent;
  };
  const code = (text, className) => make('code', className || '', text);
  const pretty = (value) => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const renderReview = (model) => {
    const review = model.review || {};
    if (!review.questions || review.questions.length === 0) return null;
    const section = make('section', 'section review-section');
    const heading = make('div', 'review-heading');
    const copy = make('div', '');
    append(copy, make('h3', '', '本轮需要你确认'), make('p', 'muted', review.notice || '选择后可直接发送本轮评审答复。'));
    append(heading, copy, make('span', 'review-status', review.status || '评审中'));
    section.appendChild(heading);
    const form = make('form', 'review-form');
    form.dataset.operationKey = model.operation.operationKey;
    review.questions.forEach((question) => {
      const fieldset = make('fieldset', '');
      fieldset.dataset.questionId = question.id;
      fieldset.appendChild(make('legend', '', question.legend));
      question.options.forEach((option) => {
        const label = make('label', 'review-option');
        const input = make('input', '');
        input.type = 'radio';
        input.name = `${model.operation.operationKey}-${question.id}`;
        input.value = option.value;
        input.checked = Boolean(option.selected);
        const optionCopy = make('span', '');
        append(optionCopy, make('strong', '', option.label), make('small', '', option.description || ''));
        append(label, input, optionCopy);
        fieldset.appendChild(label);
      });
      form.appendChild(fieldset);
    });
    const notes = make('label', 'review-notes', '补充说明（可选）');
    const textarea = make('textarea', '');
    textarea.name = 'notes';
    textarea.rows = 3;
    textarea.placeholder = '例如：只调整第 2 项，其余采用推荐项。';
    notes.appendChild(textarea);
    form.appendChild(notes);
    const actions = make('div', 'review-actions');
    const submit = make('button', 'review-submit', '发送评审答复');
    submit.type = 'submit';
    const feedback = make('span', 'review-feedback');
    feedback.setAttribute('aria-live', 'polite');
    append(actions, submit, feedback);
    form.appendChild(actions);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const answers = review.questions.map((question) => {
        const selected = form.querySelector(`input[name="${model.operation.operationKey}-${question.id}"]:checked`);
        return `${question.id}=${selected ? selected.value : '未选择'}`;
      });
      const extra = textarea.value.trim();
      const prompt = [
        `Claw Session Events v2 接口评审：${model.operation.method} ${model.operation.path}`,
        ...answers,
        extra ? `补充说明：${extra}` : ''
      ].filter(Boolean).join('\n');
      if (window.openai && typeof window.openai.sendFollowUpMessage === 'function') {
        await window.openai.sendFollowUpMessage({ prompt });
        feedback.textContent = '已发送。';
        return;
      }
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(prompt);
        feedback.textContent = '当前环境不能直接发送，答复已复制。';
        return;
      }
      feedback.textContent = `请回复：${answers.join('，')}${extra ? `；${extra}` : ''}`;
    });
    section.appendChild(form);
    return section;
  };
  const table = (columns, rows) => {
    const wrap = make('div', 'table-wrap');
    const element = make('table', '');
    const head = make('thead', '');
    const headRow = make('tr', '');
    columns.forEach((column) => headRow.appendChild(make('th', '', column)));
    head.appendChild(headRow);
    const body = make('tbody', '');
    rows.forEach((values) => {
      const row = make('tr', '');
      values.forEach((value, index) => {
        const cell = make('td', '', value);
        cell.dataset.label = columns[index];
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
    append(element, head, body);
    wrap.appendChild(element);
    return wrap;
  };
  const renderOperation = (root, model) => {
    const api = model.api;
    const operation = model.operation;
    const shell = root.querySelector('[data-api-shell]');
    if (!shell) return;
    const fullPath = `${api.basePath.replace(/\/$/, '')}/${operation.path.replace(/^\//, '')}`;
    const topbar = make('header', 'topbar');
    const titleRow = make('div', 'row');
    append(titleRow, make('h2', '', api.title), make('span', 'tag', api.version));
    if (api.visibility) titleRow.appendChild(make('span', 'tag', api.visibility));
    titleRow.appendChild(make('span', 'tag', `字段：${api.fieldNaming}`));
    titleRow.appendChild(make('span', 'tag', `Header：${api.headerNaming}`));
    append(topbar, titleRow, code(api.basePath, 'base'));

    const methodClass = operation.method.toLowerCase();
    const article = make('article', `operation operation-${methodClass}`);
    const operationHead = make('header', 'operation-head');
    append(
      operationHead,
      make('span', `method method-${methodClass}`, operation.method),
      code(operation.path, 'path'),
      make('span', 'muted', operation.summary),
      make('span', 'operation-name', operation.shortName),
      code(operation.operationKey, 'operation-key')
    );
    article.appendChild(operationHead);
    const reviewSection = renderReview(model);
    if (reviewSection && model.review.batchReview) article.appendChild(reviewSection);
    const purpose = make('section', 'section');
    append(purpose, make('h3', '', '作用'), make('p', 'description', operation.description));
    article.appendChild(purpose);

    const authSection = make('section', 'section contract-detail auth-section');
    const authTitle = make('div', 'row section-title');
    const authTabs = make('div', 'tabs');
    const authBody = make('div', '');
    append(authTitle, make('h3', '', '调用上下文 Header'), authTabs);
    append(authSection, authTitle, authBody);
    let selectedAuth = operation.requestHeaderExamples.find((item) => item.preferred) || operation.requestHeaderExamples[0];
    const renderAuth = () => {
      authTabs.querySelectorAll('button').forEach((button) => {
        button.setAttribute('aria-pressed', String(button.dataset.authId === selectedAuth.id));
      });
      authBody.replaceChildren();
      const rows = selectedAuth.headers.map((header) => [
        header.name,
        header.required ? '是' : '否',
        header.value,
        header.description
      ]);
      const request = [
        `${operation.method} ${fullPath}`,
        ...selectedAuth.headers.map((header) => `${header.name}: ${header.value}`)
      ].join('\n');
      append(authBody, table(['Header', '必填', '示例值', '说明'], rows), append(make('pre', ''), code(request)));
    };
    operation.requestHeaderExamples.forEach((mode) => {
      const button = make('button', '', mode.label);
      button.type = 'button';
      button.dataset.authId = mode.id;
      button.addEventListener('click', () => {
        selectedAuth = mode;
        renderAuth();
      });
      authTabs.appendChild(button);
    });
    renderAuth();
    article.appendChild(authSection);

    const requestSection = make('section', 'section contract-detail request-section');
    requestSection.appendChild(make('h3', '', '参数与请求体'));
    if (operation.parameters.length) {
      const rows = operation.parameters.map((parameter) => [
        parameter.in,
        parameter.name,
        parameter.required ? '是' : '否',
        parameter.schema || '—',
        parameter.description
      ]);
      requestSection.appendChild(table(['位置', '名称', '必填', '约束', '说明'], rows));
    } else {
      requestSection.appendChild(make('p', 'muted empty', '无 path/query/header 业务参数。'));
    }
    const requestBody = operation.requestBody || {};
    requestSection.appendChild(make('p', 'muted empty', requestBody.description || '无请求体。'));
    if (requestBody.example !== undefined && requestBody.example !== null) {
      requestSection.appendChild(append(make('pre', ''), code(pretty(requestBody.example))));
    }
    (requestBody.examples || []).forEach((example, index) => {
      const details = make('details', 'static-choice');
      details.open = index === 0;
      details.appendChild(make('summary', '', example.label));
      if (example.description) details.appendChild(make('p', 'muted empty', example.description));
      details.appendChild(append(make('pre', ''), code(pretty(example.value))));
      requestSection.appendChild(details);
    });
    article.appendChild(requestSection);

    (operation.contractSections || []).forEach((item) => {
      const section = make('section', 'section contract-detail');
      append(section, make('h3', '', item.title), make('p', 'description', item.description || ''),
        table(item.columns, item.rows));
      article.appendChild(section);
    });
    const responseSection = make('section', 'section contract-detail response-section');
    const responseTitle = make('div', 'row section-title');
    const localeTabs = make('div', 'tabs');
    const statusTabs = make('div', 'tabs');
    const responseBody = make('div', '');
    append(responseTitle, make('h3', '', '响应'), localeTabs);
    append(responseSection, responseTitle, statusTabs, responseBody);
    let selectedResponse = operation.responses[0];
    let selectedLocale = Object.keys(selectedResponse.bodies)[0];
    const responseIdentity = (response) => response.id || response.status;
    const renderResponse = () => {
      statusTabs.querySelectorAll('button').forEach((button) => {
        button.setAttribute('aria-selected', String(button.dataset.responseId === responseIdentity(selectedResponse)));
      });
      const locales = Object.keys(selectedResponse.bodies);
      if (!locales.includes(selectedLocale)) selectedLocale = locales[0];
      localeTabs.replaceChildren();
      locales.forEach((locale) => {
        const button = make('button', '', locale);
        button.type = 'button';
        button.setAttribute('aria-pressed', String(locale === selectedLocale));
        button.addEventListener('click', () => {
          selectedLocale = locale;
          renderResponse();
        });
        localeTabs.appendChild(button);
      });
      responseBody.replaceChildren();
      responseBody.appendChild(
        make('p', 'description', `${selectedResponse.status} ${selectedResponse.label} — ${selectedResponse.summary}`)
      );
      const headers = { ...(selectedResponse.headers || {}) };
      if (selectedLocale !== 'default' && Object.hasOwn(headers, 'Content-Language')) {
        headers['Content-Language'] = selectedLocale;
      }
      const headerLines = Object.entries(headers).map(([name, value]) => `${name}: ${value}`);
      const payload = selectedResponse.bodies[selectedLocale];
      const output = [...headerLines, headerLines.length ? '' : null, payload === undefined ? null : pretty(payload)]
        .filter((item) => item !== null).join('\n');
      responseBody.appendChild(append(make('pre', ''), code(output)));
    };
    operation.responses.forEach((response) => {
      const button = make('button', '', response.tabLabel || response.status);
      button.type = 'button';
      button.dataset.responseId = responseIdentity(response);
      button.setAttribute('role', 'tab');
      button.addEventListener('click', () => {
        selectedResponse = response;
        renderResponse();
      });
      statusTabs.appendChild(button);
    });
    renderResponse();
    article.appendChild(responseSection);
    if (reviewSection && !model.review.batchReview) article.appendChild(reviewSection);
    shell.replaceChildren(topbar, article);
  };
  roots.forEach((root, index) => {
    if (models[index]) renderOperation(root, models[index]);
  });
})();
