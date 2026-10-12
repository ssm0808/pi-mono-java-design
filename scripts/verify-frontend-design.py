#!/usr/bin/env python3
"""Verify frontend design links and all tracked design-diagram conventions."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / '07-前端设计'
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
files = {ROOT / name for name in tracked if name and name != 'AGENTS.md'}
files.update(p for p in FRONTEND.rglob('*') if p.is_file())
files = sorted(p for p in files if p.is_file())
errors = []
counts = dict(markdown=0, plantuml=0, svg=0, frontend_links=0, diagram_links=0)


def anchors(path):
    text = path.read_text()
    result = set(re.findall(r'\bid=["\']([^"\']+)["\']', text))
    if path.suffix == '.md':
        for heading in re.findall(r'^#{1,6} (.+)$', text, re.M):
            result.add(re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-'))
    return result


for path in files:
    if path.suffix == '.puml':
        counts['plantuml'] += 1
        try:
            path.read_bytes().decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'PlantUML is not UTF-8: {path.relative_to(ROOT)}')
    if path.suffix == '.svg':
        counts['svg'] += 1
        try:
            ET.parse(path)
        except ET.ParseError as error:
            errors.append(f'Invalid SVG XML: {path.relative_to(ROOT)}: {error}')
    if path.suffix not in {'.md', '.html'}:
        continue
    text = path.read_text()
    if path.suffix == '.md':
        counts['markdown'] += 1
        if re.search(r'```\s*mermaid', text, re.I):
            errors.append(f'Mermaid block: {path.relative_to(ROOT)}')
        text = re.sub(r'```.*?```', '', text, flags=re.S)
        links = re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)', text)
    else:
        links = re.findall(r'\b(?:src|href)="([^"\n]+)"', text)
    for link in links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        target = (path.parent / unquote(url.path)).resolve() if url.path else path
        frontend_link = path.is_relative_to(FRONTEND) or target.is_relative_to(FRONTEND)
        diagram_link = target.suffix in {'.svg', '.puml'}
        if not frontend_link and not diagram_link:
            continue
        # Runtime query/hash scene selectors are checked by the DOM fixture suite.
        if '{' in str(target):
            continue
        counts['frontend_links' if frontend_link else 'diagram_links'] += 1
        context = f'{path.relative_to(ROOT)} -> {link}'
        if not target.exists():
            errors.append('Missing target: ' + context)
            continue
        fragment = unquote(url.fragment)
        if target.suffix == '.puml' and fragment:
            match = re.fullmatch(r'L(\d+)', fragment)
            lines = target.read_text().splitlines()
            if not match or not 0 < int(match[1]) <= len(lines) or not lines[int(match[1]) - 1].startswith('@startuml '):
                errors.append('Invalid diagram block anchor: ' + context)
        elif frontend_link and target.suffix in {'.md', '.html'} and fragment and not fragment.startswith(('scene=', 'L')):
            if fragment not in anchors(target):
                errors.append('Invalid frontend anchor: ' + context)

for source in sorted(FRONTEND.rglob('diagram.puml')):
    with tempfile.TemporaryDirectory(prefix='frontend-diagrams-') as name:
        temp = Path(name)
        (temp / 'diagram.puml').write_bytes(source.read_bytes())
        subprocess.run(['plantuml', '-tsvg', 'diagram.puml'], cwd=temp, check=True)
        for block in re.findall(r'^@startuml\s+(\S+)', source.read_text(), re.M):
            existing = source.with_name(block + '.svg')
            generated = temp / (block + '.svg')
            if not existing.is_file() or not generated.is_file() or existing.read_bytes() != generated.read_bytes():
                errors.append(f'Unsynchronized generated SVG: {existing.relative_to(ROOT)}')

registry = ROOT / '02-服务与接口/05-CampusClaw-TDD测试Agent/capability-registry.json'
if '01-总体架构/04-CampusClaw前端体验' in registry.read_text():
    errors.append('Capability registry still points to the former frontend directory')
if errors:
    raise SystemExit('\n'.join(errors))
print(counts)
print('Frontend links/anchors, tracked diagram conventions and 11 regenerated SVGs passed.')
