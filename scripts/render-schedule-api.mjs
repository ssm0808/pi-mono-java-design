#!/usr/bin/env node
// Render maintained Markdown without introducing another contract source.
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const topic = '01-总体架构/08-CampusClaw定时任务';
const output = path.join(root, topic, 'schedule-api-review.html');
const args = process.argv.slice(2);
const moduleIndex = args.indexOf('--marked-module');
const modulePath = moduleIndex < 0
  ? createRequire(import.meta.url).resolve('marked')
  : args[moduleIndex + 1];
if (!modulePath) throw new Error('--marked-module requires a local marked module path');
const { Marked, Renderer } = await import(pathToFileURL(path.resolve(modulePath)).href);
const escape = value => String(value).replace(/[&<>"']/g,
  char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const slug = value => value.toLowerCase().replace(/[^\p{L}\p{N}_\s-]/gu, '').replace(/\s/g, '-');
const sources = [
  { prefix: 'claw', name: 'Claw 配置与生命周期', file: `${topic}/configuration.md` },
  { prefix: 'mate', name: 'Mate 内部执行接口草案',
    file: '02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md' },
];
for (const source of sources) {
  source.text = await readFile(path.join(root, source.file), 'utf8');
  source.sha = createHash('sha256').update(source.text).digest('hex');
  source.headings = [];
  source.ids = new Set();
  const counts = new Map();
  const renderer = new Renderer();
  renderer.heading = function (token) {
    const base = slug(token.text);
    const count = counts.get(base) || 0;
    counts.set(base, count + 1);
    const id = `${source.prefix}-${base}${count ? `-${count}` : ''}`;
    source.headings.push({ text: token.text, id, depth: token.depth });
    source.ids.add(id);
    return `<h${token.depth} id="${escape(id)}">${this.parser.parseInline(token.tokens)}</h${token.depth}>\n`;
  };
  const parser = new Marked({ renderer, gfm: true });
  source.html = parser.parse(source.text).replace(/<a id="([^"]+)"/g, (_, id) => {
    const prefixed = `${source.prefix}-${id}`;
    source.ids.add(prefixed);
    return `<a id="${escape(prefixed)}"`;
  });
}

function rewriteHref(source, href) {
  if (/^[a-z][a-z\d+.-]*:/i.test(href) || href.startsWith('//')) return href;
  const [relative, fragment] = href.split('#');
  const absolute = relative
    ? path.resolve(root, path.dirname(source.file), decodeURI(relative))
    : path.join(root, source.file);
  const embedded = sources.find(item => path.join(root, item.file) === absolute);
  if (embedded && fragment) {
    const id = `${embedded.prefix}-${decodeURI(fragment)}`;
    if (!embedded.ids.has(id)) throw new Error(`Missing embedded anchor: ${href}`);
    return `#${id}`;
  }
  if (embedded && !fragment) return `#${embedded.prefix}`;
  return path.relative(path.dirname(output), absolute).split(path.sep).join('/')
    + (fragment ? `#${fragment}` : '');
}

function tablesWithLabels(html) {
  return html.replace(/<table>[\s\S]*?<\/table>/g, table => {
    const header = table.match(/<thead>([\s\S]*?)<\/thead>/)?.[1] || '';
    const labels = [...header.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)]
      .map(match => match[1].replace(/<[^>]*>/g, ''));
    return table.replace(/<tbody>([\s\S]*?)<\/tbody>/g, (_, body) =>
      `<tbody>${body.replace(/<tr>([\s\S]*?)<\/tr>/g, (row, cells) => {
        let index = 0;
        return `<tr>${cells.replace(/<td([^>]*)>/g, (cell, attrs) =>
          `<td${attrs} data-label="${labels[index++] || ''}">`)}</tr>`;
      })}</tbody>`);
  });
}

for (const source of sources) {
  source.html = source.html.replace(/\b(href|src)="([^"]+)"/g, (_, attribute, href) =>
    `${attribute}="${escape(rewriteHref(source, href.replace(/&amp;/g, '&')))}"`);
  source.html = tablesWithLabels(source.html);
  const history = source.headings.find(item => item.text.includes('版本历史'));
  if (history) {
    const start = source.html.indexOf(`<h2 id="${history.id}">`);
    source.html = source.html.slice(0, start)
      + `<details class="history"><summary>版本历史</summary>${source.html.slice(start)}</details>`;
  }
}

function headingId(source, number) {
  const heading = source.headings.find(item => item.text.startsWith(`${number} `));
  if (!heading) throw new Error(`Missing heading: ${source.file} ${number}`);
  return heading.id;
}
const claw = sources[0];
const mate = sources[1];
const operations = [
  ['POST', '/schedules', '创建配置', '4.'],
  ['GET', '/schedules', '任务列表', '4.4.'],
  ['GET', '/schedules/{scheduleId}', '任务详情', '4.3.'],
  ['POST', '/schedules/{scheduleId}', '部分更新', '4.5.'],
  ['POST', '/schedules/preview', '时间预览 · 接口清单', '2.'],
  ['DELETE', '/schedules/{scheduleId}', '删除配置', '4.6.'],
  ['POST', '/schedules/{scheduleId}/run', '立即运行', '4.7.'],
  ['POST', '/schedules/{scheduleId}/pause', '暂停', '4.8.'],
  ['POST', '/schedules/{scheduleId}/unpause', '取消暂停', '4.9.'],
  ['GET', '/schedule-runs', '运行列表', '4.11.'],
  ['GET', '/schedule-runs/{runId}', '运行详情', '4.11.'],
].map(([method, route, label, number]) =>
  ({ method, route, label, target: headingId(claw, number), group: 'claw' }));
operations.push(
  { method: 'POST', route: '/runtime/schedule-contexts/query', label: '查询执行上下文',
    target: headingId(mate, '3.'), group: 'mate' },
  { method: 'POST', route: '/runtime/credentials/resolve', label: '解析执行凭据',
    target: headingId(mate, '4.'), group: 'mate' },
);
// Ensure the display inventory still agrees with the maintained operation paths.
for (const operation of operations) {
  const source = operation.group === 'claw' ? claw : mate;
  const base = operation.group === 'claw' ? '/campusclaw-service/v1' : '/mate-service/v1';
  if (!source.text.includes(`${operation.method} ${base}${operation.route}`)
      && !source.text.includes(`${operation.method} \`${base}${operation.route}\``)) {
    throw new Error(`Operation absent from source: ${operation.method} ${operation.route}`);
  }
}
function operationLinks(group) {
  return operations.filter(item => item.group === group).map(item =>
    `<a class="operation-link" href="#${escape(item.target)}"><span class="method ${item.method.toLowerCase()}">${item.method}</span><span><strong>${escape(item.label)}</strong><code>${escape(item.route)}</code></span></a>`).join('\n');
}
const sectionLinks = sources.map(source =>
  `<div class="nav-group"><h3>${escape(source.name)} · 通用规则</h3>${source.headings
    .filter(item => item.depth === 2 && !item.text.includes('版本历史'))
    .map(item => `<a class="section-link" href="#${escape(item.id)}">${escape(item.text)}</a>`).join('\n')}</div>`).join('\n');
const manifest = sources.map(source => `  ${source.file} sha256:${source.sha}`).join('\n');
const html = `<!doctype html>
<!-- Generated by scripts/render-schedule-api.mjs; edit the Markdown sources.
${manifest}
-->
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>CampusClaw 定时任务接口</title>
<style>
:root{color-scheme:light dark;--bg:light-dark(#f7f8fa,#11151b);--panel:light-dark(#fff,#1a2028);--text:light-dark(#17202a,#edf2f7);--muted:light-dark(#5f6b78,#aab4c0);--line:light-dark(#d8dee6,#37414d);--blue:light-dark(#0969da,#58a6ff);--code:light-dark(#eef2f6,#0d1117)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.75 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--blue);text-underline-offset:3px}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--blue);outline-offset:3px}code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}code{font-size:.9em;overflow-wrap:anywhere}p{margin:12px 0}h1,h2,h3,h4{line-height:1.4}h1{font-size:28px;margin:8px 0}h2{font-size:22px;margin:36px 0 16px}h3{font-size:18px;margin:28px 0 12px}h4{font-size:16px}h1,h2,h3,h4,[id]{scroll-margin-top:24px}.skip{position:absolute;top:-100px;left:16px}.skip:focus{top:10px;background:var(--panel);padding:10px;z-index:5}.page-head{max-width:1440px;margin:auto;padding:32px 24px 22px}.eyebrow{color:var(--muted);font-size:12px;letter-spacing:.12em}.intro{max-width:900px}.meta{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.tag{padding:3px 10px;border:1px solid var(--line);border-radius:99px;background:var(--panel);font-size:12px}.pending{color:light-dark(#7d4e00,#f2cc60);border-color:light-dark(#bf8700,#d29922)}.top-links{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}.layout{display:grid;grid-template-columns:310px minmax(0,1fr);gap:24px;max-width:1440px;padding:0 24px 48px;margin:auto}.sidebar{align-self:start;position:sticky;top:16px;max-height:calc(100vh - 32px);overflow-y:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:18px}.sidebar h2{font-size:15px;margin:0 0 12px}.sidebar h3{font-size:12px;color:var(--muted);margin:18px 0 8px}.base{font-size:11px;color:var(--muted);margin:0 0 8px}.search{display:none}.enhanced .search{display:block}.search label{font-size:12px;color:var(--muted)}input{width:100%;padding:10px;border:1px solid var(--line);border-radius:7px;color:var(--text);background:var(--bg);font:inherit;margin:6px 0 0}.count{font-size:12px;color:var(--muted);margin:6px 0}.operation-link{display:flex;gap:8px;align-items:flex-start;padding:10px 6px;text-decoration:none;border-radius:7px}.operation-link:hover,.section-link:hover{background:var(--code)}.operation-link strong{display:block;font-size:13px;font-weight:600;color:var(--text)}.operation-link code{display:block;font-size:10px;line-height:1.5;color:var(--muted)}.method{flex:0 0 49px;text-align:center;font:600 10px/1.7 ui-monospace,monospace;border-radius:4px;padding:3px 2px;margin-top:2px;background:light-dark(#eaf8ee,#15331f);color:light-dark(#1f883d,#3fb950)}.method.get{background:light-dark(#eaf3ff,#132b46);color:var(--blue)}.method.delete{background:light-dark(#fff1f0,#3a1d1d);color:light-dark(#cf222e,#f85149)}.section-link{display:block;text-decoration:none;font-size:12px;padding:6px;border-radius:5px}.content{min-width:0}.notice{padding:18px 22px;border:1px solid var(--line);border-radius:12px;background:var(--panel);margin-bottom:20px}.notice p{margin:0}.notice p+p{margin-top:8px}.document{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:26px 30px;margin-bottom:24px;overflow-wrap:anywhere}.document>h1{font-size:24px}.document img{display:block;max-width:100%;height:auto;margin:20px auto}.document pre{position:relative;margin:14px 0;padding:18px;overflow:auto;border-radius:8px;background:var(--code);font-size:12px;line-height:1.65}.document pre code{font-size:inherit;white-space:pre;overflow-wrap:normal}.code-tools{display:flex;justify-content:flex-end;margin:16px 0 -10px}.copy{background:var(--panel);color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:5px 10px;cursor:pointer;font:12px inherit}.document table{width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;table-layout:fixed}.document th,.document td{padding:10px 12px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line);overflow-wrap:anywhere}.document th{background:var(--bg);color:var(--muted);font-weight:600}.document tr:last-child td{border-bottom:0}.document blockquote{border-left:3px solid var(--line);margin-left:0;padding-left:16px;color:var(--muted)}.history{margin-top:32px;border-top:1px solid var(--line);padding-top:16px}.history summary{cursor:pointer;color:var(--muted)}.document-status{font-size:12px;color:var(--muted);margin:0 0 14px}footer{font-size:12px;color:var(--muted);padding:0 4px}[hidden]{display:none!important}
@media(max-width:900px){.layout{grid-template-columns:250px minmax(0,1fr);gap:16px}.document{padding:22px}.sidebar{padding:14px}}
@media(max-width:700px){.page-head{padding:24px 16px 18px}.layout{display:block;padding:0 16px 32px}.sidebar{position:static;max-height:none;margin-bottom:20px}.document{padding:18px 14px}.notice{padding:16px}.document>h1{font-size:21px}.document h2{font-size:19px}.document h3{font-size:17px}.document table,.document tbody,.document tr,.document td{display:block;width:100%}.document thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.document tr{border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:6px 10px}.document td{padding:8px 0;border-bottom:1px solid var(--line)}.document td:before{content:attr(data-label);display:block;font-size:11px;font-weight:600;color:var(--muted);margin-bottom:4px}.document pre{padding:12px;font-size:11px}.operation-link code{font-size:11px}}
@media print{.sidebar,.copy,.code-tools,.skip{display:none}.layout{display:block;max-width:none;padding:0}.document{border:0}.page-head{padding:0}.document pre{white-space:pre-wrap}.document pre code{white-space:pre-wrap}.history{display:block}}
</style>
</head>
<body>
<a class="skip" href="#content">跳到接口正文</a>
<header class="page-head">
<div class="eyebrow">CAMPUSCLAW / M10</div>
<h1>定时任务接口</h1>
<p class="intro">配置园区告警汇总与设施巡检任务，核对保存、运行、暂停和查询的接口规则与报文。</p>
<div class="meta"><span class="tag">11 个 Claw 操作</span><span class="tag">2 个 Mate 内部接口草案</span><span class="tag pending">目标契约 · 待实现</span></div>
<nav class="top-links" aria-label="设计入口"><a href="README.md">模块主设计</a><a href="configuration.md">Claw 契约原文</a><a href="../../02-服务与接口/02-CampusMate共享客户端配置/scheduled-execution.md">Mate 草案原文</a><a href="execution.md">执行与工程落地</a><a href="source-evidence.md">源码证据</a></nav>
</header>
<div class="layout">
<aside class="sidebar" aria-label="接口目录">
<h2>接口目录</h2>
<div class="search"><label for="filter">筛选目录 · 方法、路径或名称</label><input id="filter" type="search" placeholder="例如：GET、暂停、credentials" autocomplete="off"><p id="count" class="count" aria-live="polite">13 个操作</p></div>
<nav aria-label="按操作定位">
<div class="nav-group"><h3>Claw · 目标契约</h3><p class="base">/campusclaw-service/v1</p>${operationLinks('claw')}</div>
<div class="nav-group"><h3>Mate · 内部草案</h3><p class="base">/mate-service/v1</p>${operationLinks('mate')}</div>
</nav>
<details><summary>通用规则与设计说明</summary>${sectionLinks}</details>
</aside>
<main id="content" class="content">
<div class="notice"><p><strong>本页展示当前维护文档中的目标契约。</strong>Claw 接口待实现；Mate 新增路径与字段为待实现草案。报文和证据日期沿用原文，不表示已发布或本次重新核验上游。</p><p>正常流程：保存配置 → 自动触发或显式运行 → 新建独立 Session → 查询运行记录与会话结果。HTTP 200 的 Run 回执表示受理结果，业务完成结果由 Session 管理。具体失败规则见各操作及错误契约。</p><p>时间预览目前仅有接口清单和共用规则，原文尚未展开独立的完整请求／响应章节；目录直接定位到已维护的清单。</p></div>
${sources.map(source => `<article id="${source.prefix}" class="document" aria-label="${escape(source.name)}"><p class="document-status">来源：<a href="${escape(path.relative(path.dirname(output), path.join(root, source.file)))}">${escape(source.file)}</a> · 原文完整投影</p>${source.html}</article>`).join('\n')}
<footer>Markdown 是本页的维护源；修改原文后重新生成 HTML。页面可离线打开，目录与正文不依赖 JavaScript。</footer>
</main>
</div>
<script>
document.documentElement.classList.add('enhanced');
const links = [...document.querySelectorAll('.operation-link')];
document.getElementById('filter').addEventListener('input', function () {
  const query = this.value.trim().toLowerCase();
  let visible = 0;
  for (const link of links) {
    link.hidden = !link.textContent.toLowerCase().includes(query);
    if (!link.hidden) visible++;
  }
  for (const group of document.querySelectorAll('nav[aria-label="按操作定位"] .nav-group')) {
    group.hidden = !group.querySelector('.operation-link:not([hidden])');
  }
  document.getElementById('count').textContent = visible ? visible + ' 个匹配操作' : '没有匹配操作，请调整关键词';
});
for (const block of document.querySelectorAll('pre')) {
  const tools = document.createElement('div');
  tools.className = 'code-tools';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'copy';
  button.textContent = '复制示例';
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(block.textContent);
      button.textContent = '已复制';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(block);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = '已选中，请手动复制';
    }
    setTimeout(() => { button.textContent = '复制示例'; }, 2500);
  });
  tools.append(button);
  block.before(tools);
}
</script>
</body>
</html>
`;
if (args.includes('--check')) {
  if (await readFile(output, 'utf8') !== html) throw new Error('HTML differs from the current Markdown projection');
  console.log('Schedule HTML is synchronized: 11 Claw operations, 2 Mate drafts.');
} else {
  await writeFile(output, html);
  console.log(`Rendered ${path.relative(root, output)}`);
}
