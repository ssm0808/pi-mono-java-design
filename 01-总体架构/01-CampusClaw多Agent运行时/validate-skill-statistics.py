#!/usr/bin/env python3
"""Validate the Skill statistics contract and cross-operation examples."""

from datetime import date, timedelta
from pathlib import Path
import re

from render_chat_api import load_catalog


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_storage_design():
    topic = Path(__file__).resolve().parents[2] / '04-命令与技能/03-Skill加载统计'
    schema = (topic / 'schema.sql').read_text(encoding='utf-8')
    tables = re.findall(r'CREATE TABLE (\w+)', schema)
    require(tables == ['t_skill_usage', 't_skill_usage_stats',
                       't_skill_usage_daily_stats'], 'Statistics storage responsibilities drifted')
    require('PRIMARY KEY (session_id, root_event_id, skill_id)' in schema,
            'Usage identity must use the canonical root event')
    require('full_load_count' not in schema and 'execution_id' not in schema,
            'Retired metric or synthetic statistics execution identity returned')
    statement = (topic / 'record-usage.sql').read_text(encoding='utf-8')
    require('REQUIRES_NEW' in statement, 'Statistics transaction boundary missing')
    require('pk_skill_usage' in schema and 'pk_skill_usage' in statement,
            'Named root/Skill uniqueness conflict cannot be classified')
    statements = [line for line in statement.splitlines() if not line.lstrip().startswith('--')]
    sql = '\n'.join(statements)
    require(sql.count('ON DUPLICATE KEY UPDATE') == 2, 'Only summaries use UPSERT')
    positions = [sql.index('INSERT INTO ' + name + ' (') for name in tables]
    require(positions == sorted(positions), 'Fact must precede total and daily writes')
    require('result_event_id' not in schema, 'Read observation is not a persisted result claim')
    for table, body in re.findall(r'CREATE TABLE (\w+) \((.*?)\n\);', schema, re.S):
        columns = re.findall(r'^    (\w+)\s+(?:VARCHAR|BIGINT|DATE|TIMESTAMPTZ)', body, re.M)
        for column in columns:
            comment = rf"COMMENT ON COLUMN {table}\.{column} IS '[^']*[\u4e00-\u9fff][^']*';"
            require(re.search(comment, schema), f'Missing Chinese comment: {table}.{column}')


def main():
    validate_storage_design()
    manifest, models = load_catalog()
    by_key = {model['operation']['operationKey']: model for model in models}
    listing = by_key['listSkillUsageStatistics']['operation']
    daily = by_key['getSkillUsageDailyStatistics']['operation']
    require((listing['method'], listing['path']) == ('GET', '/skills/usage-statistics'), 'List resource route changed')
    require((daily['method'], daily['path']) == ('GET', '/skills/{skillId}/usage-statistics/daily'), 'Daily resource route changed')
    list_params = {p['name']: p for p in listing['parameters']}
    require(set(list_params) == {'period', 'sort', 'page', 'limit', 'Accept-Language'}, 'List requires an unexpected parameter or ID')
    require(not any(p['required'] for p in list_params.values()), 'List must work without preselected IDs')
    daily_params = {p['name']: p for p in daily['parameters']}
    require(set(daily_params) == {'skillId', 'period', 'Accept-Language'}, 'Daily parameter set changed')
    require(daily_params['skillId']['required'], 'Single statistic needs resource identity')
    require(list_params['period']['schema'] == 'all | 7d | 30d; default all', 'List period/default drift')
    require(daily_params['period']['schema'] == '7d | 30d; default 7d', 'Daily period/default drift')
    for operation in (listing, daily):
        require(not operation['requestBody']['required'] and operation['requestBody']['example'] is None, 'GET body must be absent')
        require(operation['responses'], 'Missing responses')
        for response in operation['responses']:
            require(response['headers']['Cache-Control'] == 'no-store', 'Statistics response is cacheable')
            for payload in response['bodies'].values():
                if response['status'] == '200':
                    require(set(payload) == {'resCode', 'resMsg', 'result'} and payload['resCode'] == '0', 'Success envelope differs')
                    require(payload['result']['scope'] == 'runtime', 'Unverified execution scope entered statistics')
                else:
                    require(set(payload) == {'resCode', 'resMsg'}, 'Error contains a result or an invalid envelope')
    results = {r['id']: next(iter(r['bodies'].values()))['result']
               for r in daily['responses'] if r['status'] == '200'}
    require({item['period'] for item in results.values()} == {'7d', '30d'}, 'Missing calendar-window example')
    for result in results.values():
        start, end = date.fromisoformat(result['fromDate']), date.fromisoformat(result['toDate'])
        days = int(result['period'][:-1])
        require((end - start).days == days, 'Date window has wrong length')
        require([row['date'] for row in result['items']] == [str(start + timedelta(days=n)) for n in range(days)], 'Daily sequence has a gap or duplicate')
        require(sum(row['usageCount'] for row in result['items']) == result['usageCount'], 'Daily values and window total disagree')
        require((result['lastUsedAt'] is None) == (result['usageCount'] == 0), 'Zero window timestamp differs')
        require(result['timeZone'] == 'Asia/Shanghai', 'Business timezone changed')
    ranked = next(iter(next(r for r in listing['responses'] if r['id'] == '200-ranking')['bodies'].values()))['result']
    detail = results['200-daily']
    row = next(item for item in ranked['items'] if item['skillId'] == detail['skillId'])
    require(row['usageCount'] == detail['usageCount'] and row['lastUsedAt'] == detail['lastUsedAt'], 'List and detail disagree for the same snapshot')
    require(all(r['usageCount'] > 0 for r in ranked['items']), 'List fabricated a zero-count resource')
    missing = [r for r in daily['responses'] if r['status'] == '404']
    require(len(missing) == 1 and all(b['resCode'] == 'SKILL_USAGE_STATISTICS_NOT_FOUND' for b in missing[0]['bodies'].values()), 'Missing statistics must not imply missing Skill')
    entries = [entry for entry in manifest['operations'] if entry['key'] in {'listSkillUsageStatistics', 'getSkillUsageDailyStatistics'}]
    require(all(entry['status'] == '使用统计目标已确认 · target-only' for entry in entries), 'Usage design status drifted')
    print('Skill statistics: two GET routes; ID-free ranking; calendar windows; matching list/daily counts; empty/missing distinction; Runtime scope; envelopes; confirmed target state, root/Skill key, isolated write order and three-table design passed. No database execution.')


if __name__ == '__main__':
    main()
