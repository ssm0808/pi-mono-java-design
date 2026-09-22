#!/usr/bin/env python3
"""Generate the design repository's visual index from named PlantUML blocks."""
from html import escape
from pathlib import Path
import re
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '设计图索引.html'


def collect_diagrams():
    captions = {}
    documents = sorted(
        (path for path in ROOT.rglob('*.md') if '学习' not in path.relative_to(ROOT).parts),
        key=lambda path: (path.name != 'README.md', str(path)),
    )
    for document in documents:
        prose = re.sub(r'```.*?```', '', document.read_text(), flags=re.S)
        for caption, target in re.findall(r'!\[([^]\n]+)\]\(([^)\n]+\.svg)\)', prose):
            if '://' not in target:
                path = (document.parent / unquote(target)).resolve()
                captions.setdefault(path, caption.replace('`', ''))
    diagrams = []
    for source in sorted(ROOT.rglob('diagram.puml')):
        relative = source.relative_to(ROOT)
        if '学习' in relative.parts:
            continue
        for match in re.finditer(r'^@startuml\s+(\S+)', source.read_text(), re.M):
            name = match.group(1)
            svg = source.with_name(name + '.svg')
            if not svg.is_file():
                raise ValueError(f'Missing generated diagram: {svg}')
            metadata = ET.parse(svg).getroot()
            line = source.read_text()[:match.start()].count('\n') + 1
            diagrams.append({
                'name': name,
                'caption': captions.get(svg.resolve(), name),
                'topic': str(relative.parent),
                'svg': quote(str(svg.relative_to(ROOT)), safe='/'),
                'source': quote(str(relative), safe='/') + f'#L{line}',
                'size': metadata.get('width', '') + ' × ' + metadata.get('height', ''),
            })
    return diagrams


def render(diagrams):
    cards = []
    for item in diagrams:
        text = escape(item['topic'] + ' ' + item['name'] + ' ' + item['caption'], quote=True)
        cards.append(f'''<article data-search="{text}">
<p class="topic">{escape(item['topic'])}</p>
<h2>{escape(item['caption'])}</h2>
<button class="preview" data-src="{item['svg']}" data-name="{escape(item['caption'])}" aria-label="查看 {escape(item['caption'])}"><img loading="lazy" src="{item['svg']}" alt="{escape(item['caption'])}"></button>
<footer><span>{escape(item['size'])}</span><a href="{item['svg']}" target="_blank">原尺寸 SVG</a><a href="{item['source']}">PlantUML 源码</a></footer>
</article>''')
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CampusClaw 设计图索引</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#20252b;background:#f5f6f8}*{box-sizing:border-box}body{margin:0}header{position:sticky;top:0;z-index:1;background:#fff;border-bottom:1px solid #ddd;padding:18px 28px}h1{font-size:22px;margin:0 0 8px}header p{margin:8px 0;font-size:14px;color:#52606d}a{color:#205b9e}input{width:min(650px,100%);font:inherit;padding:10px 12px;border:1px solid #adb5bd;border-radius:5px}#count{font-size:14px;margin-left:12px}main{padding:24px;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(390px,100%),1fr));gap:20px}article{background:white;border:1px solid #d8dde3;border-radius:8px;padding:16px;min-width:0}.topic{font-size:12px;line-height:1.5;color:#607080;margin:0 0 6px;overflow-wrap:anywhere}h2{font-size:15px;margin:4px 0 14px;overflow-wrap:anywhere}.preview{display:block;width:100%;height:245px;padding:8px;border:0;background:#fff;cursor:zoom-in}.preview img{width:100%;height:100%;object-fit:contain}footer{font-size:12px;display:flex;gap:14px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid #eee}dialog{width:96vw;max-width:none;height:94vh;max-height:none;border:1px solid #aaa;border-radius:8px;padding:0}dialog::backdrop{background:#0008}.toolbar{display:flex;gap:12px;align-items:center;padding:12px;border-bottom:1px solid #ddd;background:#fff}.toolbar strong{margin-right:auto;overflow-wrap:anywhere}.toolbar button{font:inherit;padding:6px 10px;background:white;border:1px solid #aaa;border-radius:4px}.canvas{height:calc(100% - 62px);overflow:auto;padding:20px;background:white}.canvas img{display:block;max-width:none}.canvas.fit img{max-width:100%;height:auto}.canvas.document img{width:840px;height:auto}[hidden]{display:none!important}@media(max-width:600px){header{padding:14px}main{padding:12px}.toolbar{flex-wrap:wrap;font-size:13px}.toolbar strong{width:100%}}
</style></head><body><header><h1>CampusClaw 设计图索引</h1><p><a href="README.md">仓库导航</a> · 按目录或图名检索，点击预览切换原尺寸与文档宽度。</p><input id="search" type="search" placeholder="搜索 Provider、Session、计划模式……" aria-label="搜索设计图"><span id="count"></span></header><main>
''' + '\n'.join(cards) + '''</main>
<dialog id="viewer"><div class="toolbar"><strong id="title"></strong><button data-mode="fit">适应宽度</button><button data-mode="document">文档宽度</button><button data-mode="full">原尺寸</button><button id="close">关闭</button></div><div class="canvas fit"><img id="large" alt=""></div></dialog>
<script>
const cards=[...document.querySelectorAll('article')], search=document.querySelector('#search'), count=document.querySelector('#count');
function filter(){const query=search.value.toLowerCase().trim();let visible=0;for(const card of cards){card.hidden=!card.dataset.search.toLowerCase().includes(query);if(!card.hidden)visible++}count.textContent=visible+' / '+cards.length+' 张图'}
search.addEventListener('input',filter);filter();
const viewer=document.querySelector('#viewer'), canvas=viewer.querySelector('.canvas'), large=document.querySelector('#large');
for(const button of document.querySelectorAll('.preview'))button.addEventListener('click',()=>{large.src=button.dataset.src;large.alt=button.dataset.name;document.querySelector('#title').textContent=button.dataset.name;canvas.className='canvas fit';viewer.showModal();canvas.scrollTo(0,0)});
for(const button of viewer.querySelectorAll('[data-mode]'))button.addEventListener('click',()=>{canvas.className='canvas '+button.dataset.mode;canvas.scrollTo(0,0)});
document.querySelector('#close').addEventListener('click',()=>viewer.close());
</script></body></html>
'''


if __name__ == '__main__':
    diagrams = collect_diagrams()
    OUTPUT.write_text(render(diagrams))
    print(f'{OUTPUT.relative_to(ROOT)}: {len(diagrams)} diagrams')
