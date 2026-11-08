"""Offline HTML with native SVG band and finite-spectrum plots."""
from html import escape
import json


def render_html(data, report):
    bands = report['bulk']['bands']
    scale = max(max(abs(item['upper_eV']) for item in bands), 1e-9)
    def y(value):
        return 170 - 130 * value / scale
    upper = ' '.join(f'{60 + 350 * item["k_over_pi"]:.3f},{y(item["upper_eV"]):.3f}' for item in bands)
    lower = ' '.join(f'{60 + 350 * item["k_over_pi"]:.3f},{y(item["lower_eV"]):.3f}' for item in bands)
    band_plot = ('<svg viewBox="0 0 820 360" role="img" aria-label="Infinite periodic bulk bands">'
                 '<line x1="60" y1="170" x2="760" y2="170" stroke="#94a3b8"/>'
                 '<line x1="60" y1="25" x2="60" y2="315" stroke="#64748b"/>'
                 f'<polyline points="{upper}" fill="none" stroke="#2563eb" stroke-width="2"/>'
                 f'<polyline points="{lower}" fill="none" stroke="#b45309" stroke-width="2"/>'
                 '<text x="380" y="345">k / pi  (0 to 2)</text><text x="8" y="20">E (eV)</text>'
                 f'<text x="8" y="48">{scale:.3g}</text><text x="8" y="304">{-scale:.3g}</text></svg>')
    modes = report['finite_chain']['modes']
    circles = []
    for mode in modes:
        x = 60 + 700 * mode['index'] / max(1, len(modes) - 1)
        color = '#7c3aed' if mode['classification'] == 'BOUNDARY_CANDIDATE' else '#475569'
        circles.append(f'<circle cx="{x:.3f}" cy="{y(mode["energy_eV"]):.3f}" r="4" fill="{color}"/>')
    spectrum = ('<svg viewBox="0 0 820 360" role="img" aria-label="Finite chain spectrum">'
                '<line x1="60" y1="170" x2="760" y2="170" stroke="#94a3b8"/>'
                + ''.join(circles) + '<text x="350" y="345">Sorted eigenvalue index</text>'
                '<text x="8" y="20">E (eV)</text>'
                f'<text x="8" y="48">{scale:.3g}</text><text x="8" y="304">{-scale:.3g}</text></svg>')
    rows = ''.join('<tr><td>' + str(mode['index']) + '</td><td>' + str(mode['energy_eV'])
                   + '</td><td>' + str(mode['boundary_weight']) + '</td><td>' + mode['classification']
                   + '</td></tr>' for mode in modes)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<title>SSH topology research review</title><style>'
            'body{font:16px system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#172033}'
            '.plot{overflow:auto}svg{width:100%;min-width:600px;height:auto;background:#f8fafc}'
            'table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:1px solid #cbd5e1;padding:8px;overflow-wrap:anywhere;text-align:left}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f9;padding:16px}'
            '</style></head><body><h1>Topology in physics and materials science</h1><p>'
            + escape(data['label']) + '</p><p>Idealized SSH model. No experimental material validation or device authorization.</p>'
            '<h2>' + report['status'] + '</h2><h2>Infinite periodic bulk bands</h2><div class="plot">'
            + band_plot + '</div><h2>Finite chain spectrum</h2><div class="plot">' + spectrum
            + '</div><p>Purple marks threshold-defined boundary candidates in open chains only. '
            'They are not a proof of protected edge states. The bulk and finite spectral gaps are different quantities.</p>'
            '<h2>Finite eigenmode diagnostics</h2><table><thead><tr><th>Index</th><th>Energy eV</th><th>Boundary weight</th>'
            '<th>Classification</th></tr></thead><tbody>' + rows + '</tbody></table>'
            '<h2>Complete report assumptions and numerical environment</h2><pre>'
            + escape(json.dumps(report, sort_keys=True, indent=2)) + '</pre></body></html>\n')
