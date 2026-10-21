#!/usr/bin/env python3
"""Project Claw schedule Markdown through the repository's existing API renderer."""
import argparse
import copy
import hashlib
import html
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPIC = ROOT / '01-总体架构/08-CampusClaw定时任务'
RUNTIME = ROOT / '01-总体架构/01-CampusClaw多Agent运行时'
OUTPUT = TOPIC / 'schedule-api-review.html'
spec = importlib.util.spec_from_file_location('schedule_shared_renderer', RUNTIME / 'render_chat_http_v1.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


def plain(text):
    text = re.sub(r'!?\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text.replace('`', '').replace('**', '').replace('\\|', '|').strip()


def contract_chapter(text):
    start = text.index('<a id="interface"></a>')
    end = text.index('\n## 5. ', start)
    return text[start:end]


def sections(text):
    # Keys drop the chapter prefix: README §4.4.7 is section '4.7.'.
    pattern = r'^#{3,4} 4\.(\d+(?:\.\d+)*) ([^\n]+)\n([\s\S]*?)(?=^#{1,4} |\Z)'
    return {match[1] + '.': {'title': match[2], 'text': match[3]}
            for match in re.finditer(pattern, text, re.M)}


def examples(section):
    return [json.loads(match[1]) for match in re.finditer(
        r'```json\n([\s\S]*?)\n```', section['text'])]


def tables(section):
    result = []
    for block in re.findall(r'^\|[^\n]+\n\|[-:| ]+\n(?:\|[^\n]+\n?)+', section['text'], re.M):
        lines = block.strip().splitlines()
        split = lambda line: [plain(cell) for cell in re.split(r'(?<!\\)\|', line.strip('|'))]
        columns = split(lines[0])
        rows = [split(line) for line in lines[2:]]
        shared.require(all(len(row) == len(columns) for row in rows), 'Malformed Markdown table')
        result.append({'columns': columns, 'rows': rows})
    return result


def rules(section):
    text = re.sub(r'```[\s\S]*?```', '', section['text'])
    text = re.sub(r'^\|[^\n]*(?:\n|$)', '', text, flags=re.M)
    text = re.sub(r'<a [^>]+></a>', '', text)
    result = []
    for paragraph in re.split(r'\n\s*\n', text):
        paragraph = paragraph.strip()
        if not paragraph or paragraph.startswith(('![', '[原尺寸', '**与 Claude', '与 Claude', '官方证据')):
            continue
        result.append([str(len(result) + 1), plain(paragraph)])
    return result


def contract_sections(source, numbers):
    result = []
    for number in numbers:
        section = source[number]
        title = plain(section['title'])
        for index, table in enumerate(tables(section)):
            result.append({'title': f'{title} · 表 {index + 1}', 'description': '', **table})
        rows = rules(section)
        if rows:
            result.append({'title': f'{title} · 调用边界', 'description': '',
                           'columns': ['序号', '规则'], 'rows': rows})
    return result


def parameter(where, name, required, schema, description):
    return {'in': where, 'name': name, 'required': required,
            'schema': schema, 'description': description}


def response(status, summary, body=None, key=None, label='OK', base_headers=None):
    headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'Content-Language': 'zh-CN'}
    if base_headers:
        headers.update(base_headers)
    if body is None:
        headers.pop('Content-Language', None)
    return {'id': key or str(status), 'status': str(status), 'label': label,
            'tabLabel': str(status) + (f' · {key}' if key else ''),
            'summary': summary, 'headers': headers,
            'bodies': {} if body is None else {'zh-CN': body}}


def bilingual_errors(section, allowed=None):
    result = []
    labels = {'400': 'Bad Request', '401': 'Unauthorized', '403': 'Forbidden',
              '404': 'Not Found', '409': 'Conflict', '500': 'Internal Server Error',
              '503': 'Service Unavailable'}
    for table in tables(section):
        if table['columns'][0] != 'HTTP / resCode' or len(table['columns']) != 3:
            continue
        for identity, condition, messages in table['rows']:
            match = re.match(r'(\d+) / ([A-Z_]+)$', identity)
            if not match or (allowed and match[2] not in allowed):
                continue
            zh, en = messages.split(' / ', 1)
            status, code = match.groups()
            item = response(status, condition, key=code, label=labels[status])
            item['bodies'] = {locale: {'resCode': code, 'resMsg': message}
                              for locale, message in [('zh-CN', zh), ('en-US', en)]}
            result.append(item)
    return result


def model(key, method, route, name, purpose, params, body, responses, details, user_token=False):
    language = 'zh-CN'
    headers = [{'name': 'Accept-Language', 'value': language, 'required': False,
                'description': f'支持 zh-CN/en-US；缺省或不支持时回退 {language}；返回实际 Content-Language。'}]
    if user_token:
        headers.insert(0, {'name': 'access-token', 'value': '<当前用户的 access-token>', 'required': True,
                           'description': 'Mate 原样转发的用户 token；Claw 只用它查询用户 ID，不落库、不写日志。'})
    if body.get('required'):
        headers.insert(0, {'name': 'Content-Type', 'value': 'application/json',
                          'required': True, 'description': 'JSON 请求体。'})
    item = {
        'api': {'title': 'CampusClaw 定时任务 API',
                'version': '0.28.0',
                'basePath': '/campusclaw-service/v1',
                'visibility': 'Internal · 目标契约 · 待实现',
                'fieldNaming': 'lowerCamelCase', 'headerNaming': '保留原名'},
        'operation': {'operationKey': key, 'shortName': name, 'method': method, 'path': route,
                      'summary': name, 'description': purpose,
                      'requestHeaderExamples': [{'id': 'context', 'label': '调用上下文 Header 示例',
                                                 'preferred': True, 'headers': headers}],
                      'parameters': params, 'requestBody': body, 'responses': responses,
                      'contractSections': details},
        'review': {'questions': []},
    }
    shared.validate_model(item)
    shared.require(not re.search(r'已确认|已评审|已定稿|待实现|本轮|本次评审', purpose), 'Purpose contains status')
    return item


def build_models(claw):
    source = sections(claw)
    create, schedule = examples(source['4.'])
    update, updated, clear, invalid_rule = examples(source['4.5.'])
    deleted, delete_error = examples(source['4.6.'])
    run, busy = examples(source['4.7.'])
    paused = examples(source['4.8.'])[0]
    active = examples(source['4.9.'])[0]
    listing = examples(source['4.4.'])[0]
    not_found = examples(source['4.3.'])[0]
    common_rules = [{'title': '共用调用规则', 'description': '',
                     'columns': ['序号', '规则'], 'rows': rules(source['2.'])}]
    shared_errors = contract_sections(source, ['6.'])
    path_id = parameter('path', 'scheduleId', True, '服务端原 ID；大小写敏感、不复用',
                        '使用创建返回的原 ID，不按名称定位；精确格式沿企业 ID 契约校准。')
    no_body = {'required': False, 'description': '无请求体；不接收业务查询参数。'}
    manage_error_codes = {row['bodies']['zh-CN']['resCode']: row for row in bilingual_errors(source['4.10.'])}
    not_found_response = response(404, '目标不存在、已删除或不在当前可见范围。', not_found,
                                  'SCHEDULE_NOT_FOUND', 'Not Found')
    not_found_response['bodies']['en-US'] = {'resCode': not_found['resCode'],
                                          'resMsg': 'Schedule not found or not accessible.'}
    models = []
    busy_en = copy.deepcopy(busy)
    for table in tables(source['4.7.']):
        if table['columns'][0] == 'Run.error.type':
            for error_type, _, messages in table['rows']:
                if error_type == busy['result']['error']['type']:
                    busy_en['result']['error']['message'] = messages.split(' / ', 1)[1]

    def add(key, method, route, name, purpose, params, body, success, numbers, errors=None):
        details = common_rules + contract_sections(source, numbers) + shared_errors
        models.append(model(key, method, route, name, purpose, params, body,
                            success + (errors or []), details,
                            user_token=key in ('CreateSchedule', 'ListSchedules', 'ListScheduleRuns')))

    add('CreateSchedule', 'POST', '/schedules', '创建任务配置',
        '保存园区告警汇总任务的 Agent、prompt 和时间规则，返回完整配置及计划摘要。保存不立即运行；有效 Cron 登记自动计划。',
        [], {'required': True, 'contentType': 'application/json', 'description': '创建任务配置。字段与默认值见下方规则。', 'example': create},
        [response(201, '返回完整 Schedule；不创建 Session。', schedule, base_headers={
            'Location': '/campusclaw-service/v1/schedules/' + schedule['result']['id']})],
        ['3.', '3.1.', '3.3.', '3.4.', '3.6.', '3.7.', '4.1.', '4.1.1.', '4.2.', '5.'])
    queries = [parameter('query', row[0], False, row[1], row[1]) for row in tables(source['4.4.'])[0]['rows']]
    add('ListSchedules', 'GET', '/schedules', '查询任务列表',
        '按名称、Agent 和状态查找当前可见的任务，分页返回与详情同形的完整配置。',
        queries, {'required': False, 'description': '无请求体。响应示例对应 page=1、limit=1、status=active。'},
        [response(200, '当前查询还有后续记录，nextPage=2。', listing)], ['4.4.'])
    add('GetSchedule', 'GET', '/schedules/{scheduleId}', '查询任务详情',
        '读取任务当前完整配置与计划摘要；具体运行的受理结果和业务结果分别从 Run、Session 读取。',
        [path_id], no_body, [response(200, '复用创建成功的完整资源形状；此处展示同一示例配置。', schedule)],
        ['4.3.'], [not_found_response])
    add('UpdateSchedule', 'POST', '/schedules/{scheduleId}', '部分更新任务配置',
        '提交需要改变的字段，服务端合并最新配置并原子保存，返回完整资源；修改不触发运行。',
        [path_id], {'required': True, 'contentType': 'application/json', 'description': '至少提供一个可写字段；省略保持、null 按字段规则处理。',
                    'example': update, 'examples': [{'label': '清除自动计划', 'description': '只清除规则，不暂停任务、不运行、不取消在途。', 'value': clear}]},
        [response(200, '原子更新后返回完整配置。', updated)], ['4.5.'],
        [response(400, '字段校验失败；不部分保存。', invalid_rule, 'SCHEDULE_RULE_INVALID', 'Bad Request')])
    add('DeleteSchedule', 'DELETE', '/schedules/{scheduleId}', '删除任务配置',
        '删除任务及其全部 Run，停止未来受理，返回最后配置的一次回执；已生成 Session 保留并独立管理。',
        [path_id], {'required': False, 'description': '无业务查询、无请求体；非空正文（含 {}）返回400。'},
        [response(200, '完整 Schedule 删除回执；之后配置和对应 Run 详情404，列表排除。', deleted)],
        ['4.6.'], bilingual_errors(source['4.6.']))
    action_codes = {
        'run': ['SCHEDULE_REQUEST_INVALID', 'SCHEDULE_AUTH_REQUIRED', 'SCHEDULE_RUN_FORBIDDEN', 'SCHEDULE_NOT_FOUND', 'SCHEDULE_RUN_FAILED', 'SCHEDULE_SERVICE_UNAVAILABLE'],
        'pause': ['SCHEDULE_REQUEST_INVALID', 'SCHEDULE_AUTH_REQUIRED', 'SCHEDULE_MANAGE_FORBIDDEN', 'SCHEDULE_NOT_FOUND', 'SCHEDULE_PAUSE_FAILED', 'SCHEDULE_SERVICE_UNAVAILABLE'],
        'unpause': ['SCHEDULE_REQUEST_INVALID', 'SCHEDULE_AUTH_REQUIRED', 'SCHEDULE_MANAGE_FORBIDDEN', 'SCHEDULE_NOT_FOUND', 'SCHEDULE_ACTIVATION_REJECTED', 'SCHEDULE_UNPAUSE_FAILED', 'SCHEDULE_SERVICE_UNAVAILABLE'],
    }
    for action, key, name, purpose, number, successes in [
        ('run', 'RunSchedule', '立即运行任务', '使用已保存配置发起一次真实运行，返回已记录的 Session 受理结果；不等待业务完成。', '4.7.',
         [response(200, '已受理：返回新 Session ID。', run, '受理成功'),
          response(200, '本次忙拒绝已可靠记录；error 非空，不能视为业务成功。', busy, '已记录的受理失败')]),
        ('pause', 'PauseSchedule', '暂停自动触发', '停止后续自动受理并保留配置和历史；已受理执行继续，有权限者仍可显式运行。', '4.8.',
         [response(200, '返回 paused/manual 的完整 Schedule。', paused)]),
        ('unpause', 'UnpauseSchedule', '取消暂停', '恢复后续自动计划，从未来 Cron 时刻继续；不立即执行、不补漏跑。', '4.9.',
         [response(200, '返回 active/null 的完整 Schedule。', active)]),
    ]:
        if action == 'run':
            successes[0]['bodies']['en-US'] = copy.deepcopy(run)
            successes[1]['bodies']['en-US'] = busy_en
        add(key, 'POST', f'/schedules/{{scheduleId}}/{action}', name, purpose,
            [path_id], {'required': False, 'description': '无业务查询、无请求体；非空正文（含 {}）返回400，不接收配置覆盖。'},
            successes, [number, '4.10.'], [manage_error_codes[code] for code in action_codes[action]])
    run_queries = [parameter('query', row[0], False, row[1], row[1])
                   for table in tables(source['4.11.']) if table['columns'][0] == '列表query' for row in table['rows']]
    run_list = {'resCode': '0', 'resMsg': 'success', 'result': {'runs': [run['result']], 'nextPage': None}}
    run_missing = response(404, 'Run或所属任务不存在、已删除或不可见。',
                           {'resCode': 'SCHEDULE_RUN_NOT_FOUND', 'resMsg': '定时运行不存在或不可访问。'},
                           'SCHEDULE_RUN_NOT_FOUND', 'Not Found')
    run_missing['bodies']['en-US'] = {'resCode': 'SCHEDULE_RUN_NOT_FOUND', 'resMsg': 'Schedule run not found or not accessible.'}
    for key, route, name, params, value, note, errors in [
        ('ListScheduleRuns', '/schedule-runs', '查询运行列表', run_queries, run_list,
         '按原文 runs/nextPage 结构投影完整 Run 示例；示例仅有一条记录，无后续页。', []),
        ('GetScheduleRun', '/schedule-runs/{runId}', '查询运行详情',
         [parameter('path', 'runId', True, '服务端原 ID；大小写敏感、不复用', '独立的 Run 标识。')], run,
         '复用立即运行的完整八字段 Run 示例；业务结果仍从 Session 读取。', [run_missing]),
    ]:
        add(key, 'GET', route, name, '读取已确定的运行受理结果；Run与Session各自执行当前授权，查询不启动或取消执行。',
            params, {'required': False, 'description': '无请求体；列表支持所列筛选，详情不接收业务query。'},
            [response(200, note, value)], ['4.11.'], errors)
    return models


def render_item(index, model):
    operation = model['operation']
    key = html.escape(operation['operationKey'])
    source = 'README.md#interface'
    status = '目标契约 · 待实现'
    note = '展示原维护契约，尚未发布。身份适配与持久化接线待实现；源码证据日期沿用原文。'
    return (
        f'<details class="catalog-item" id="{key}" data-catalog-key="{key}">'
        f'<summary><span class="catalog-line"><span>{index + 1:02d}</span>'
        f'<strong>{operation["method"]}</strong><span>{operation["shortName"]}</span>'
        f'<span class="catalog-status">{status}</span></span>'
        f'<code class="catalog-path">{html.escape(operation["path"])}</code></summary>'
        f'<p class="catalog-caveat">{note}</p>'
        f'<p class="catalog-links"><a href="{source}">契约原文</a> · '
        f'<a href="source-evidence.md">设计依据与实施边界</a> · '
        f'<a href="#{key}">此接口链接</a></p>'
        f'<section class="company-api-review" data-operation-review="{key}" data-operation-index="{index}">'
        f'<div class="api-shell" data-api-shell>{shared.render_static(model, expand_details=True)}</div></section></details>'
    )


def build_html():
    source_path = TOPIC / 'README.md'
    document = source_path.read_text()
    text = contract_chapter(document)
    models = build_models(text)
    title = 'CampusClaw 定时任务接口'
    base = '/campusclaw-service/v1'
    status = 'Claw 目标契约待实现；各项证据日期与范围以源码证据文档为准。'
    links = ('<a href="README.md">模块设计</a> · <a href="README.md#interface">Claw契约原文</a> · '
             '<a href="README.md#normal-acceptance">定时任务受理流程</a>')
    identities = set()
    version_pattern = r'\| 文档版本 \| ([\d.]+)'
    version = re.search(version_pattern, document)[1]
    for item in models:
        operation = item['operation']
        shared.require(item['api']['basePath'] == base, 'Operation belongs to another service')
        full_path = base + operation['path']
        identity = (operation['method'], full_path)
        shared.require(identity not in identities, 'Duplicate operation')
        identities.add(identity)
        shared.require(f'{operation["method"]} {full_path}' in text
                       or f'{operation["method"]} `{full_path}`' in text,
                       f'Operation not found in maintained source: {identity}')
        item['api']['version'] = version
    css = shared.CSS_PATH.read_text() + (RUNTIME / '接口契约/页面资源/catalog.css').read_text()
    script = shared.JS_PATH.read_text()
    eager = '  roots.forEach((root, index) => {\n    if (models[index]) renderOperation(root, models[index]);\n  });'
    shared.require(script.count(eager) == 1, 'Shared initialization changed; inspect lazy adapter')
    script = script.replace(eager, (RUNTIME / '接口契约/页面资源/catalog.js').read_text().rstrip())
    manifest = f'{source_path.relative_to(ROOT)} sha256:{hashlib.sha256(text.encode()).hexdigest()}'
    cards = '\n'.join(render_item(index, item) for index, item in enumerate(models))
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>{title}</title>
<style>{css}</style></head><body>
<!-- Generated by scripts/render-schedule-api.py. Do not edit directly.
{manifest}
-->
<main id="schedule-api-catalog">
<header class="catalog-header"><h1>{title} · {len(models)} 项</h1>
<p>{len(models)} 个 Claw 操作：<code>{base}</code>。</p>
<p>沿用仓库现有接口页的展示与交互。展开一个接口即可查看调用上下文、参数、请求示例、规则和响应；响应状态与语言使用标签切换。</p>
<p>{status} Markdown继续作为维护源。</p>
<p>{links}</p>
</header>
{cards}
</main>
<script type="application/json" id="api-review-models" data-review-models>{shared.encode_models(models)}</script>
<script>{script}</script>
</body></html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = OUTPUT
    content = build_html()
    if args.check:
        shared.require(output.read_text() == content, 'API HTML is stale; regenerate it')
    else:
        shared.write_output(output, content)
    print(f'{output}: synchronized through the existing API renderer')


if __name__ == '__main__':
    main()
