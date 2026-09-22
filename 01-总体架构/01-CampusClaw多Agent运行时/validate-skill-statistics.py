#!/usr/bin/env python3
"""Validate the Skill statistics contract and cross-operation examples."""

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
    require('listSkillUsageStatistics' not in by_key and 'getSkillUsageDailyStatistics' not in by_key,
            'Deferred ranking/trend operations must not remain active')
    operation = by_key['QuerySkillLoadStatistics']['operation']
    require((operation['method'], operation['path']) ==
            ('POST', '/internal/skills/load-statistics/query'), 'Batch query route changed')
    require(operation['requestBody']['required'], 'Batch query requires a JSON body')
    example = operation['requestBody']['example']
    require(set(example) == {'skillIds'} and 1 <= len(example['skillIds']) <= 100, 'Invalid cumulative request')
    require(all(re.fullmatch(r'skill-[0-9a-fA-F]{32}', value) for value in example['skillIds']), 'Invalid ID')
    require({p['name'] for p in operation['parameters']} == {'Accept-Language'}, 'Unexpected query parameters')
    for response in operation['responses']:
        for payload in response['bodies'].values():
            if response['status'] == '200':
                require(set(payload) == {'resCode', 'resMsg', 'result'} and payload['resCode'] == '0', 'Invalid success')
                result = payload['result']
                require(set(result) == {'queriedAt', 'from', 'to', 'items'}, 'Response fields drifted')
                require([row['skillId'] for row in result['items']] == example['skillIds'], 'ID order changed')
                require(response['headers']['Cache-Control'] == 'no-store', 'Success response is cacheable')
                for row in result['items']:
                    require(set(row) == {'skillId', 'activationCount', 'lastLoadedAt'}, 'Item fields drifted')
                    require(type(row['activationCount']) is int and row['activationCount'] >= 0, 'Invalid count')
                    require((row['activationCount'] == 0) == (row['lastLoadedAt'] is None), 'Invalid zero item')
            else:
                require(set(payload) == {'resCode', 'resMsg'}, 'Error contains a result')
    require({r['status'] for r in operation['responses']} == {'200', '400', '500', '503'}, 'Status set changed')
    errors = {next(iter(r['bodies'].values()))['resCode'] for r in operation['responses'] if r['status'] != '200'}
    require(errors == {'INVALID_SKILL_LOAD_STATISTICS_QUERY', 'SKILL_LOAD_STATISTICS_QUERY_FAILED',
                       'SKILL_LOAD_STATISTICS_HISTORY_UNAVAILABLE'}, 'Error codes differ from implementation')
    require(sum(entry['key'] == 'QuerySkillLoadStatistics' for entry in manifest['operations']) == 1,
            'Register one batch query')
    print('Skill statistics: batch POST, selected IDs, activationCount, zero items and errors valid; ranking/trend deferred.')


if __name__ == '__main__':
    main()
