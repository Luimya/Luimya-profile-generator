"""Render horizontal bars from the original public summary-card proportions.

The upstream SVG remains the data source, preserving both existing metrics.
Only validated charts replace the last successful generated assets.
"""

import argparse
import html
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SVG_NS = {'s': 'http://www.w3.org/2000/svg'}
NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'


def outer_angle(path):
    """Sum circular outer arcs, stopping before the inner donut ring."""
    total = 0.0
    point = None
    for command, raw in re.findall(r'([MLAZ])([^MLAZ]*)', path):
        values = [float(v) for v in re.findall(NUMBER, raw)]
        if command == 'M':
            if point is not None:
                break
            point = values[-2:]
        elif command == 'A':
            if point is None or len(values) != 7:
                raise ValueError('Unsupported SVG arc')
            rx, ry, rotation, large, sweep, x, y = values
            if rx <= 0 or not math.isclose(rx, ry) or rotation != 0:
                raise ValueError('Expected an unrotated circular arc')
            start = math.atan2(point[1], point[0])
            end = math.atan2(y, x)
            angle = ((end - start) if sweep else (start - end)) % math.tau
            if large and angle < math.pi - 1e-8:
                raise ValueError('SVG large-arc flag does not match geometry')
            total += angle
            point = [x, y]
        else:
            break
    return total


def read_proportions(svg):
    root = ET.fromstring(svg)
    arcs = root.findall('.//s:g[@class="arc"]', SVG_NS)
    legend = next((g for g in root.findall('.//s:g', SVG_NS)
                   if any(r.attrib.get('width') == '14' for r in g.findall('s:rect', SVG_NS))
                   and g.findall('s:text', SVG_NS)), None)
    labels = [] if legend is None else [''.join(t.itertext()).strip()
                                        for t in legend.findall('s:text', SVG_NS)]
    if not arcs and not labels:
        text = ' '.join(root.itertext()).lower()
        if any(message in text for message in ('no data', 'no languages', 'no public')):
            return []
        raise ValueError('Upstream language card has no recognized chart data')
    if len(arcs) != len(labels):
        raise ValueError('Language labels and chart slices do not match')
    rows = []
    for label, arc in zip(labels, arcs):
        path = arc.find('s:path', SVG_NS)
        if path is None:
            raise ValueError('Language slice has no SVG path')
        color = re.search(r'fill:\s*(#[0-9a-fA-F]{6})', path.attrib.get('style', ''))
        if color is None:
            raise ValueError('Language slice has no recognized color')
        percentage = outer_angle(path.attrib['d']) / math.tau * 100
        rows.append((label, percentage, color.group(1)))
    if not math.isclose(sum(r[1] for r in rows), 100, abs_tol=0.001):
        raise ValueError('Language percentages do not sum to 100')
    return sorted(rows, key=lambda row: -row[1])


def render(title, rows):
    height = max(200, 86 + len(rows) * 52)
    summary = '; '.join(f'{name}: {value:.1f}%' for name, value, _ in rows)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{height}" viewBox="0 0 400 {height}" role="img" aria-labelledby="title description">',
             f'<title id="title">{html.escape(title)}</title>',
             f'<desc id="description">{html.escape(summary or "No public language data available.")}</desc>',
             '<style>text{font-family:Segoe UI,Ubuntu,Helvetica Neue,sans-serif}</style>',
             f'<rect x="1" y="1" width="398" height="{height-2}" rx="6" fill="#1a1b27"/>',
             f'<text x="24" y="34" fill="#70a5fd" font-size="20">{html.escape(title)}</text>',
             '<text x="24" y="55" fill="#8b91b3" font-size="11">Public GitHub activity</text>']
    for index, (name, value, color) in enumerate(rows):
        y = 85 + index * 52
        parts.extend([f'<text x="24" y="{y}" fill="#38bdae" font-size="14">{html.escape(name)}</text>',
                      f'<text x="376" y="{y}" fill="#38bdae" font-size="13" text-anchor="end">{value:.1f}%</text>',
                      f'<rect x="24" y="{y+10}" width="352" height="12" rx="6" fill="#292d42"/>',
                      f'<rect x="24" y="{y+10}" width="{352*value/100:.3f}" height="12" rx="6" fill="{color}"/>'])
    if not rows:
        parts.append('<text x="24" y="100" fill="#38bdae" font-size="14">No public language data available.</text>')
    return ''.join(parts) + '</svg>\n'


def fetch(username, endpoint):
    url = ('https://github-profile-summary-cards.vercel.app/api/cards/' + endpoint
           + '?' + urlencode({'username': username, 'theme': 'tokyonight'}))
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'GitHub-Profile-Language-Bars/1.0'})
            with urlopen(request, timeout=30) as response:
                return read_proportions(response.read().decode('utf-8'))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', required=True)
    parser.add_argument('--output', type=Path, default=Path('assets'))
    args = parser.parse_args()
    specs = [('repos-per-language', 'Top Languages by Repo', 'languages-by-repo.svg'),
             ('most-commit-language', 'Top Languages by Commit', 'languages-by-commit.svg')]
    generated = [(name, render(title, fetch(args.username, endpoint)))
                 for endpoint, title, name in specs]
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in generated:
        destination = args.output / name
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(content, encoding='utf-8')
        temporary.replace(destination)
        print(f'Updated {destination}')


if __name__ == '__main__':
    main()
