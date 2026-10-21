"""Small, safe Markdown renderer for repository-owned research notes."""
import html
import re
from urllib.parse import urlsplit


TOKEN=re.compile(r'\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`')


def inline(text):
    parts=[];position=0
    for match in TOKEN.finditer(text):
        parts.append(html.escape(text[position:match.start()]))
        if match.group(3) is not None:
            parts.append('<code>'+html.escape(match.group(3))+'</code>')
        else:
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
    lines=markdown.splitlines();result=[];paragraph=[];items=[];list_kind=None;table=[];in_code=False;code=[]
    def flush_paragraph():
        if paragraph:result.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    def flush_items():
        nonlocal list_kind
        if items:
            tag='ol' if list_kind=='ol' else 'ul'
            result.append('<'+tag+'>'+''.join('<li>'+inline(item)+'</li>' for item in items)+'</'+tag+'>')
            items.clear();list_kind=None
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
        ordered=re.match(r'^\d+[.)]\s+(.+)$',line)
        if bullet or ordered:
            kind='ul' if bullet else 'ol'
            flush_paragraph()
            if list_kind and list_kind!=kind:flush_items()
            list_kind=kind;items.append((bullet or ordered).group(1));continue
        if not line.strip():flush_paragraph();flush_items();continue
        flush_items();paragraph.append(line.strip())
    flush_paragraph();flush_items();flush_table()
    if in_code:result.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(result)
