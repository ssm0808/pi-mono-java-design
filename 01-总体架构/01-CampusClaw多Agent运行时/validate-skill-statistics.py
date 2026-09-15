#!/usr/bin/env python3
"""Validate the Skill statistics contract and cross-operation examples."""

from datetime import date, timedelta

from render_chat_api import load_catalog


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    manifest, models = load_catalog()
    by_key = {model['operation']['operationKey']: model for model in models}
    listing = by_key['listSkillLoadStatistics']['operation']
    daily = by_key['getSkillLoadDailyStatistics']['operation']
    require((listing['method'], listing['path']) == ('GET', '/skills/load-statistics'), 'List resource route changed')
    require((daily['method'], daily['path']) == ('GET', '/skills/{skillId}/load-statistics/daily'), 'Daily resource route changed')
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
                else:
                    require(set(payload) == {'resCode', 'resMsg'}, 'Error contains a result or an invalid envelope')
    results = {r['id']: next(iter(r['bodies'].values()))['result']
               for r in daily['responses'] if r['status'] == '200'}
    for result in results.values():
        start, end = date.fromisoformat(result['fromDate']), date.fromisoformat(result['toDate'])
        days = int(result['period'][:-1])
        require((end - start).days == days, 'Date window has wrong length')
        require([row['date'] for row in result['items']] == [str(start + timedelta(days=n)) for n in range(days)], 'Daily sequence has a gap or duplicate')
        require(sum(row['fullLoadCount'] for row in result['items']) == result['fullLoadCount'], 'Daily values and window total disagree')
        require((result['lastLoadedAt'] is None) == (result['fullLoadCount'] == 0), 'Zero window timestamp differs')
        require(result['timeZone'] == 'Asia/Shanghai', 'Business timezone changed')
    ranked = next(iter(next(r for r in listing['responses'] if r['id'] == '200-ranking')['bodies'].values()))['result']
    detail = results['200-daily']
    row = next(item for item in ranked['items'] if item['skillId'] == detail['skillId'])
    require(row['fullLoadCount'] == detail['fullLoadCount'] and row['lastLoadedAt'] == detail['lastLoadedAt'], 'List and detail disagree for the same snapshot')
    require(all(r['fullLoadCount'] > 0 for r in ranked['items']), 'List fabricated a zero-count resource')
    missing = [r for r in daily['responses'] if r['status'] == '404']
    require(len(missing) == 1 and all(b['resCode'] == 'SKILL_LOAD_STATISTICS_NOT_FOUND' for b in missing[0]['bodies'].values()), 'Missing statistics must not imply missing Skill')
    entries = [entry for entry in manifest['operations'] if entry['key'] in {'listSkillLoadStatistics', 'getSkillLoadDailyStatistics'}]
    require(all(entry['status'] == '全文加载候选 · target-only · 口径待评审' for entry in entries), 'Proposal silently promoted to confirmed')
    print('Skill statistics: two GET routes; ID-free ranking; calendar windows; matching list/daily counts; empty/missing distinction; envelopes and proposal state passed.')


if __name__ == '__main__':
    main()
