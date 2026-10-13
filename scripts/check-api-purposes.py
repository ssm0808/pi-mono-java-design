#!/usr/bin/env python3
"""Check purpose prose across all maintained HTTP models and OpenAPI projections."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PROSE = re.compile(r'已确认|已评审|已定稿|待实现|待评审|本轮|本次评审|已按 [A-Z]\d+|PR #\d+')


def check_purpose(operation, source):
    description = operation.get('description')
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f'{source}: missing operation purpose')
    if STATUS_PROSE.search(description):
        raise ValueError(f'{source}: purpose contains review or delivery history')


def validate(root=ROOT):
    models = sorted(root.glob('**/接口契约/操作/*.json'))
    models += sorted(root.glob('**/事件契约/操作/*.json'))
    models += sorted(root.glob('**/统计契约/操作/*.json'))
    models += sorted(root.glob('**/查询契约/操作/*.json'))
    models += [root / '02-服务与接口/03-Model/chat-api.json']
    count = 0
    for path in models:
        if {'历史', '学习'} & set(path.relative_to(root).parts):
            continue
        operation = json.loads(path.read_text())['operation']
        check_purpose(operation, path.relative_to(root))
        if operation['path'].endswith('/commands') and operation.get('contractSections'):
            raise ValueError(f'{path}: command discovery must retain standard request/response sections only')
        count += 1
    yaml_program = 'puts JSON.generate(YAML.safe_load(File.read(ARGV[0]), permitted_classes: [], aliases: false))'
    for path in sorted(root.glob('02-服务与接口/**/*.openapi.yaml')):
        result = subprocess.run(['ruby', '-ryaml', '-rjson', '-e', yaml_program, str(path)],
                                capture_output=True, text=True, check=True)
        spec = json.loads(result.stdout)
        for route, methods in spec['paths'].items():
            for method, operation in methods.items():
                if method.lower() in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}:
                    check_purpose(operation, f'{path.relative_to(root)} {method.upper()} {route}')
                    count += 1
    return count


if __name__ == '__main__':
    print(f'API purpose checks passed: {validate()} operation presentations (JSON and OpenAPI).')
