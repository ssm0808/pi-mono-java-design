#!/usr/bin/env python3
"""Check design diagrams, references and optional reproducible SVG generation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BLOCK = re.compile(r'^@startuml\s+(\S+).*?^@enduml\s*$', re.M | re.S)
DECLARATION = re.compile(r'^\s*(?:actor|participant|boundary|control|entity|database|collections|queue)\s+(.+)$', re.M)
MESSAGE = re.compile(r'^\s*[\w.]+\s+[-<ox\\/]+(?:\[[^\]]+\])?[-<>ox\\/]+\s+[\w.]+\b.*:', re.M)
BRANCH = re.compile(r'^\s*(?:alt|opt|break)\b', re.M)
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^)\n]+)\)')


def files(pattern):
    return sorted(p for p in ROOT.rglob(pattern)
                  if not {'学习', '.git', 'node_modules'}.intersection(p.relative_to(ROOT).parts))


def is_sequence(block):
    return bool(DECLARATION.search(block)) and not re.search(
        r'^\s*(?:class\s|package\s|rectangle\s|component\s|usecase\s|\[[^\]]+\]\s+as\s|'
        r'(?:entity|database)\s+[^\n]*\{|(?:top to bottom|left to right) direction)', block, re.M)


def reference_target(document, value):
    value = value.strip('<>')
    parsed = urlsplit(value)
    if parsed.scheme or value.startswith('#'):
        return None
    return (document.parent / unquote(parsed.path)).resolve(), parsed.fragment


def render_source(source):
    with tempfile.TemporaryDirectory(prefix='campusclaw-diagram-') as folder:
        copy = Path(folder) / source.name
        copy.write_bytes(source.read_bytes())
        # Resolve any topic-local includes without changing the tracked source.
        for path in source.parent.iterdir():
            if path.is_file() and path.suffix in ('.puml', '.iuml') and path != source:
                (copy.parent / path.name).write_bytes(path.read_bytes())
        result = subprocess.run(['plantuml', '-tsvg', 'diagram.puml'], cwd=folder,
                                capture_output=True, text=True)
        if result.returncode:
            return [f'{source.relative_to(ROOT)}: PlantUML failed: {result.stdout}{result.stderr}']
        errors = []
        for match in BLOCK.finditer(source.read_text(encoding='utf-8')):
            name = match.group(1)
            generated, tracked = copy.with_name(name + '.svg'), source.with_name(name + '.svg')
            if not generated.is_file() or not tracked.is_file():
                errors.append(f'{name}: generated or tracked SVG missing')
            elif generated.read_bytes() != tracked.read_bytes():
                errors.append(f'{tracked.relative_to(ROOT)}: SVG differs from fresh generation')
        return errors


def check(render=False):
    errors, warnings, sequences = [], [], []
    sources = files('diagram.puml')
    block_count = 0
    for source in files('*.puml'):
        try:
            source.read_bytes().decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{source.relative_to(ROOT)}: PlantUML is not UTF-8')
    for source in sources:
        text = source.read_text(encoding='utf-8')
        names = set()
        preamble = text.split("@startuml", 1)[0]
        for match in BLOCK.finditer(text):
            block_count += 1
            name, block = match.group(1), match.group(0)
            if name in names:
                errors.append(f'{source.relative_to(ROOT)}: duplicate block {name}')
            names.add(name)
            svg = source.with_name(name + '.svg')
            if not svg.is_file():
                errors.append(f'{svg.relative_to(ROOT)}: missing SVG')
            if not is_sequence(block):
                continue
            participants = len(DECLARATION.findall(block))
            messages = len(MESSAGE.findall(block))
            branches = len(BRANCH.findall(block))
            sequences.append((name, participants, messages, branches))
            if participants > 6 or messages > 25 or branches > 2:
                warnings.append(f'{name}: {participants} participants, {messages} messages, '
                                f'{branches} conditional groups; inspect scope and justify boundaries')
            if not re.search(r"^'.*(?:Source|Baseline|source|baseline|Evidence|源码|基线|证据)", preamble + block, re.M):
                errors.append(f'{name}: missing source-evidence comment')
            if not re.search(r"^'.*(?:Observed behavior|Design reason|Architecture change|Presentation|已观察行为|设计原因|架构变更|表达方式)", block, re.M):
                errors.append(f'{name}: missing design-reason comment')
    for svg in files('*.svg'):
        try:
            ET.parse(svg)
        except ET.ParseError as error:
            errors.append(f'{svg.relative_to(ROOT)}: invalid XML: {error}')
    for document in files('*.md'):
        text = document.read_text(encoding='utf-8')
        if re.search(r'^\s*```\s*mermaid\b', text, re.M | re.I):
            errors.append(f'{document.relative_to(ROOT)}: Mermaid fence')
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        for link in LINK.finditer(prose):
            target = reference_target(document, link.group(1))
            if target is None:
                continue
            path, fragment = target
            if path.suffix not in ('.svg', '.puml'):
                continue
            if not path.is_file():
                errors.append(f'{document.relative_to(ROOT)}: missing {link.group(1)}')
                continue
            if path.suffix == '.puml' and fragment:
                number = re.fullmatch(r'L(\d+)', fragment)
                lines = path.read_text(encoding='utf-8').splitlines()
                if not number or not (1 <= int(number[1]) <= len(lines)):
                    errors.append(f'{document.relative_to(ROOT)}: invalid anchor {link.group(1)}')
                elif not lines[int(number[1]) - 1].startswith('@startuml '):
                    errors.append(f'{document.relative_to(ROOT)}: anchor does not identify a block: {link.group(1)}')
    if render:
        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(render_source, sources):
                errors.extend(result)
    for name, participants, messages, branches in sorted(sequences):
        print(f'SEQUENCE {name}: {participants} participants / {messages} messages / {branches} conditions')
    for warning in warnings:
        print('CHECK SCOPE:', warning)
    for error in errors:
        print('ERROR:', error)
    print(f'{len(sources)} topics; {block_count} blocks; {len(sequences)} sequences; '
          f'{len(warnings)} scope hints; {len(errors)} errors')
    print('Mechanical checks do not verify business semantics or replace visual inspection.')
    return 1 if errors else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='regenerate all topics in temporary directories and compare SVG bytes')
    args = parser.parse_args()
    raise SystemExit(check(args.render))
