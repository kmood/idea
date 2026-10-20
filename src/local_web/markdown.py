"""Small, safe Markdown renderer for repository-owned research notes."""
import html
import re
from urllib.parse import urlsplit


LINK=re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def inline(text):
    parts=[];position=0
    for match in LINK.finditer(text):
        parts.append(html.escape(text[position:match.start()]))
        label=html.escape(match.group(1));url=match.group(2).strip()
        parsed=urlsplit(url)
        if parsed.scheme in ('http','https') or (not parsed.scheme and not url.startswith('//')):
            parts.append(f'<a href="{html.escape(url,quote=True)}" rel="noreferrer">{label}</a>')
        else:
            parts.append(label)
        position=match.end()
    parts.append(html.escape(text[position:]))
    return ''.join(parts)


def render_markdown(markdown):
    lines=markdown.splitlines();result=[];paragraph=[];items=[];table=[];in_code=False;code=[]
    def flush_paragraph():
        if paragraph:result.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    def flush_items():
        if items:result.append('<ul>'+''.join('<li>'+inline(item)+'</li>' for item in items)+'</ul>');items.clear()
    def flush_table():
        if not table:return
        header=table[0];body=table[2:] if len(table)>1 and all(set(cell)<=set('-: ') for cell in table[1]) else table[1:]
        result.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(cell)+'</th>' for cell in header)+'</tr></thead>')
        result.append('<tbody>'+''.join('<tr>'+''.join('<td>'+inline(cell)+'</td>' for cell in row)+'</tr>' for row in body)+'</tbody></table></div>')
        table.clear()
    for raw in lines:
        line=raw.rstrip()
        if line.startswith('```'):
            flush_paragraph();flush_items();flush_table()
            if in_code:
                result.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code.clear();in_code=False
            else:in_code=True
            continue
        if in_code:code.append(line);continue
        if line.startswith('|') and line.endswith('|'):
            flush_paragraph();flush_items();table.append([cell.strip() for cell in line[1:-1].split('|')]);continue
        flush_table()
        heading=re.match(r'^(#{1,3})\s+(.+)$',line)
        if heading:
            flush_paragraph();flush_items();level=len(heading.group(1));result.append(f'<h{level}>{inline(heading.group(2))}</h{level}>');continue
        bullet=re.match(r'^[-*]\s+(.+)$',line)
        if bullet:
            flush_paragraph();items.append(bullet.group(1));continue
        if not line.strip():flush_paragraph();flush_items();continue
        flush_items();paragraph.append(line.strip())
    flush_paragraph();flush_items();flush_table()
    if in_code:result.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(result)
