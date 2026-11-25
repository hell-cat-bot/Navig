"""Shared visual components for the Navig pilot console.

Custom HTML/SVG is used only where Streamlit has no native equivalent:
the schematic corridor map, edge-clip frames, and compact evidence tables.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import core

_STYLE_PATH = Path(__file__).resolve().parent / "assets" / "console.css"


def inject_styles() -> None:
    st.html(_STYLE_PATH)


def _data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"

BAND_COLORS: dict[str, str] = {
    "Low": "#2DD4BF",
    "Moderate": "#F5C451",
    "High": "#FB923C",
    "Severe": "#F87171",
}

FLOOD_COLORS: dict[int, str] = {
    0: "#2DD4BF",
    1: "#38BDF8",
    2: "#FB923C",
    3: "#F87171",
}

EVIDENCE_COLORS: dict[str, str] = {
    "Implemented": "#2DD4BF",
    "Partial": "#F5C451",
    "Simulated": "#60A5FA",
    "Proposed": "#A78BFA",
    "Not connected": "#F87171",
    "Not yet": "#94A3B8",
}

INGREDIENT_COLORS: dict[str, str] = {
    "occupancy": "#2DD4BF",
    "speed_drop": "#60A5FA",
    "spillback": "#F5C451",
    "hazard": "#F87171",
}

INGREDIENT_LABELS: dict[str, str] = {
    "occupancy": "Road occupancy",
    "speed_drop": "Speed drop",
    "spillback": "Queue spillback",
    "hazard": "Hazard penalty",
}


def esc(value: Any) -> str:
    return html.escape(str(value))


def page_header(eyebrow: str, title: str, subtitle: str, badges: str = "") -> None:
    inject_styles()
    st.caption(eyebrow)
    st.title(title)
    st.caption(subtitle)
    if badges:
        st.markdown(badges)


def page_footer() -> None:
    st.divider()
    st.caption(
        f"{core.APP['name']} v{core.APP['version']} · built for the {core.APP['pilot_ref']} proposal · "
        "synthetic telemetry only · no live camera, GPS, or dispatch feed connected."
    )


def _band_from_score(score: float) -> str:
    if score <= 35:
        return "Low"
    if score <= 55:
        return "Moderate"
    if score <= 75:
        return "High"
    return "Severe"


def _points() -> list[tuple[float, float]]:
    points = []
    for index in range(len(core.JUNCTIONS)):
        t = 0.04 + index * (0.92 / (len(core.JUNCTIONS) - 1))
        x = (1 - t) ** 2 * 45 + 2 * (1 - t) * t * 400 + t**2 * 755
        y = (1 - t) ** 2 * 190 + 2 * (1 - t) * t * 65 + t**2 * 150
        points.append((round(x, 1), round(y, 1)))
    return points





def _incident_markers(open_incidents: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for incident in open_incidents:
        counts[incident["junction"]] = counts.get(incident["junction"], 0) + 1
    return counts


def corridor_map(
    readings: dict[str, dict[str, Any]],
    selected_id: str,
    overlays: list[str],
    live: bool,
    open_incidents: list[dict[str, Any]],
    summary: dict[str, Any],
    clock: str,
    decisions_logged: int,
) -> str:
    nodes = list(readings.values())
    points = _points()
    selected = readings[selected_id]
    zones = core.flood_zones()
    zone_levels = {zone["id"]: zone["level"] for zone in zones}
    incident_counts = _incident_markers(open_incidents)

    svg: list[str] = []
    svg.append('<rect x="0" y="0" width="800" height="300" fill="url(#navi-grid)" />')
    svg.append(
        '<path d="M 45 190 Q 400 65 755 150" fill="none" stroke="#1B2740" stroke-width="22" stroke-linecap="round" />'
    )

    zone_spans = {"z1": (0, 1), "z2": (2, 3), "z3": (3, 4), "z4": (4, 5), "z5": (5, 6)}
    for index in range(len(nodes) - 1):
        first_node = nodes[index]
        second_node = nodes[index + 1]
        x1, y1 = points[index]
        x2, y2 = points[index + 1]
        gap = first_node["status"] == "abstain" or second_node["status"] == "abstain"
        if gap:
            color = "#3A475C"
            dash = ' stroke-dasharray="7 9"'
        else:
            pair_scores = [
                float(node["score"])
                for node in (first_node, second_node)
                if node["score"] is not None
            ]
            average = sum(pair_scores) / len(pair_scores)
            color = BAND_COLORS[_band_from_score(average)]
            dash = ""
        svg.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="7" stroke-linecap="round"{dash} />'
        )

    svg.append(
        '<path d="M 45 190 Q 400 65 755 150" fill="none" stroke="#DDE7F4" stroke-width="1.1" '
        'stroke-dasharray="2 9" stroke-linecap="round" opacity="0.3" />'
    )

    if "Bus probes" in overlays:
        for index in range(len(nodes) - 1):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]
            for fraction in (0.32, 0.7):
                x = x1 + (x2 - x1) * fraction
                y = y1 + (y2 - y1) * fraction - 3
                svg.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#93C5FD" opacity="0.8" />'
                )

    if "Flood" in overlays:
        for zone_id, (start, end) in zone_spans.items():
            level = int(zone_levels.get(zone_id, 0))
            if level < 1:
                continue
            x = (points[start][0] + points[end][0]) / 2
            y = (points[start][1] + points[end][1]) / 2
            color = FLOOD_COLORS[level]
            svg.append(
                f'<rect x="{x - 14:.1f}" y="{y - 8}" width="28" height="16" rx="4" '
                f'fill="#0B1220" stroke="{color}" stroke-width="1.2" />'
            )
            svg.append(
                f'<text x="{x:.1f}" y="{y + 3.5}" text-anchor="middle" font-size="10" '
                f'font-weight="700" fill="{color}">L{level}</text>'
            )

    for index, node in enumerate(nodes):
        x, y = points[index]
        status = node["status"]
        if status == "abstain":
            color = "#8496AD"
            svg.append(
                f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" rx="1.5" fill="#0B1220" '
                f'stroke="{color}" stroke-width="2" stroke-dasharray="3 3" transform="rotate(45 {x} {y})" />'
            )
            score_line = "No data"
        else:
            color = BAND_COLORS[node["band"]]
            if index == core._JUNCTION_INDEX.get(selected_id, -1):
                svg.append(
                    f'<circle cx="{x}" cy="{y}" r="22" fill="{color}" opacity="0.12" />'
                )
            if status == "low":
                svg.append(
                    f'<circle cx="{x}" cy="{y}" r="9" fill="#0B1220" stroke="#F5C451" '
                    'stroke-width="2.4" stroke-dasharray="3 2" />'
                )
            else:
                svg.append(
                    f'<circle cx="{x}" cy="{y}" r="9" fill="#0B1220" stroke="{color}" stroke-width="3" />'
                )
            svg.append(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{color}" />')
            score_line = f"{node['score']} · {node['band']}"

        above = index % 2 == 0
        name_y = y - 31 if above else y + 33
        score_y = y - 12 if above else y + 52
        label_width = max(118, len(node["name"]) * 10.7, len(score_line) * 7.8) + 22
        rect_y = y - 50 if above else y + 15
        if index == core._JUNCTION_INDEX.get(selected_id, -1):
            svg.append(
                f'<rect x="{x - label_width / 2:.1f}" y="{rect_y}" width="{label_width:.1f}" height="45" '
                f'rx="8" fill="#111D30" stroke="{color}" stroke-width="1" opacity="0.96" />'
            )
        name_color = "#FFFFFF" if index == core._JUNCTION_INDEX.get(selected_id, -1) else "#DDE7F4"
        if status == "abstain":
            name_color = "#93A4BA"
        svg.append(
            f'<text x="{x}" y="{name_y}" text-anchor="middle" font-size="19.5" font-weight="600" '
            f'fill="{name_color}">{esc(node["name"])}</text>'
        )
        svg.append(
            f'<text x="{x}" y="{score_y}" text-anchor="middle" font-size="14.5" font-weight="600" '
            f'fill="{color}">{esc(score_line)}</text>'
        )

    if "Incidents" in overlays:
        for index, node in enumerate(nodes):
            count = incident_counts.get(node["name"], 0)
            if not count:
                continue
            x, y = points[index]
            cx, cy = x + 19, y - 20
            svg.append(
                f'<circle cx="{cx}" cy="{cy}" r="10" fill="#F87171" stroke="#0B1220" stroke-width="2" />'
            )
            svg.append(
                f'<text x="{cx}" y="{cy + 3.7}" text-anchor="middle" font-size="11" font-weight="800" '
                f'fill="#0B1220">{"!" if count == 1 else count}</text>'
            )

    selected_name = selected["name"]
    status_bits = []
    for node in nodes:
        if node["score"] is None:
            status_bits.append(f"{node['name']} no data")
        else:
            status_bits.append(f"{node['name']} {node['score']} {node['band']}")
    aria_label = (
        "Schematic corridor map of GS Road from Ganeshguri to GMCH. "
        + "; ".join(status_bits)
        + f". Selected junction: {selected_name}."
    )

    live_class = "" if live else " paused"
    live_text = "LIVE SIM" if live else "PAUSED"
    coverage_line = (
        f"<span><span class='navi-foot-dot'></span><b>{summary['coverage']}%</b> camera coverage</span>"
        f"<span><b>{summary['valid']} of 8</b> junctions fully valid</span>"
        f"<span><b>{summary['low']}</b> low confidence</span>"
        f"<span><b>{summary['abstain']}</b> abstained</span>"
        f"<span><b>{len(open_incidents)}</b> unverified alerts</span>"
        f"<span><b>{decisions_logged}</b> actions logged</span>"
    )
    legend = "".join(
        f"<span class='navi-legend-item'><i class='navi-l-dot' style='background:{color}'></i>{label}</span>"
        for label, color in BAND_COLORS.items()
    )
    legend += (
        "<span class='navi-legend-item'><i class='navi-l-dash'></i>No data / gap</span>"
        "<span class='navi-legend-item'><i class='navi-l-ring'></i>Low confidence</span>"
        "<span class='navi-legend-item'><i class='navi-l-incident'>!</i>Open incident</span>"
        "<span class='navi-legend-item'><i class='navi-l-flood'>L1</i>Water level</span>"
    )

    svg_markup = (
        '<svg viewBox="0 0 800 300" role="img" aria-label="'
        + esc(aria_label).replace('"', "&quot;")
        + '" xmlns="http://www.w3.org/2000/svg">'
        "<title>"
        + esc(aria_label)
        + "</title>"
        '<defs><pattern id="navi-grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1B2740" stroke-width="1" opacity="0.35" />'
        "</pattern></defs>"
        + "".join(svg)
        + "</svg>"
    )

    map_image = (
        f'<img src="{_data_uri(svg_markup)}" alt="'
        f'{esc(aria_label).replace(chr(34), "&quot;")}" />'
    )

    return (
        '<div class="navi-map">'
        '<div class="navi-map-head">'
        "<div>"
        '<div class="navi-kicker">Corridor view · Pilot map</div>'
        '<div class="navi-title">GS Road · Ganeshguri → GMCH</div>'
        '<div class="navi-sub">Schematic · not to scale · 4.2 km pilot corridor</div>'
        "</div>"
        '<div class="navi-head-right">'
        f'<span class="navi-live{live_class}"><span class="navi-live-dot"></span>{live_text}</span>'
        f'<span class="navi-chip">{summary["coverage"]}% coverage</span>'
        f'<span class="navi-chip">{esc(clock)} IST</span>'
        "</div>"
        "</div>"
        f'<div class="navi-svg-wrap">{map_image}</div>'
        f'<div class="navi-coverline">{coverage_line}</div>'
        f'<div class="navi-legend">{legend}</div>'
        '<div class="navi-map-note">Select a junction below to open its decision card.</div>'
        "</div>"
    )


def junction_pill_label(reading: dict[str, Any]) -> str:
    if reading["score"] is None:
        return f"{reading['name']} · no data"
    return f"{reading['name']} · {reading['score']}"


def breakdown_html(reading: dict[str, Any]) -> str:
    rows = []
    for key in ("occupancy", "speed_drop", "spillback", "hazard"):
        rows.append(
            f'<span class="navi-bd-label">{INGREDIENT_LABELS[key]}</span>'
            f'<span class="navi-bd-track"><span class="navi-bd-fill" '
            f'style="width:{reading[key]}%;background:{INGREDIENT_COLORS[key]}"></span></span>'
            f'<span class="navi-bd-value">{reading[key]}%</span>'
            f'<span class="navi-bd-pts">+{reading["points"][key]:.1f}</span>'
        )
    aria = (
        f"CItCI breakdown for {reading['name']}: occupancy {reading['occupancy']} percent, "
        f"speed drop {reading['speed_drop']} percent, spillback {reading['spillback']} percent, "
        f"hazard {reading['hazard']} percent; score {reading['score']}."
    )
    return (
        f'<div class="navi-bd" role="img" aria-label="{esc(aria).replace(chr(34), "&quot;")}">'
        + "".join(rows)
        + '<div class="navi-bd-total"><span>Weighted CItCI · model v0.9</span>'
        f'<b>{reading["score"]} / 100</b></div>'
        "</div>"
    )


def _clip_scene(incident: dict[str, Any]) -> str:
    kind = incident["kind"]
    if kind == "stopped_vehicle":
        overlay = (
            '<rect x="228" y="132" width="128" height="84" rx="5" fill="none" stroke="#F59E0B" '
            'stroke-width="2" stroke-dasharray="6 5" />'
            '<rect x="248" y="156" width="88" height="40" rx="7" fill="#6B7E95" />'
            '<path d="M 260 156 L 274 138 L 310 138 L 326 156 Z" fill="#94A3B8" />'
            '<rect x="266" y="144" width="18" height="9" rx="2" fill="#CBD5E1" opacity="0.75" />'
            '<rect x="291" y="144" width="18" height="9" rx="2" fill="#CBD5E1" opacity="0.75" />'
            '<circle cx="264" cy="197" r="7" fill="#1F2937" stroke="#94A3B8" stroke-width="2" />'
            '<circle cx="320" cy="197" r="7" fill="#1F2937" stroke="#94A3B8" stroke-width="2" />'
            '<rect x="270" y="183" width="30" height="8" rx="2" fill="#CBD5E1" opacity="0.35" />'
            '<rect x="270" y="183" width="7" height="8" fill="#64748B" opacity="0.65" />'
            '<rect x="284" y="183" width="7" height="8" fill="#94A3B8" opacity="0.5" />'
            '<text x="292" y="124" text-anchor="middle" font-size="11" font-weight="700" fill="#FBBF24">STOPPED · 42 s</text>'
        )
    elif kind == "wrong_way":
        overlay = (
            '<path d="M 350 176 L 210 196" stroke="#F87171" stroke-width="3" stroke-dasharray="7 4" fill="none" />'
            '<path d="M 222 186 L 205 197 L 228 200" stroke="#F87171" stroke-width="3" fill="none" stroke-linecap="round" />'
            '<rect x="274" y="168" width="34" height="14" rx="5" fill="#94A3B8" />'
            '<circle cx="281" cy="185" r="5" fill="#1F2937" stroke="#94A3B8" stroke-width="1.5" />'
            '<circle cx="301" cy="185" r="5" fill="#1F2937" stroke="#94A3B8" stroke-width="1.5" />'
            '<circle cx="297" cy="153" r="6" fill="#94A3B8" />'
            '<rect x="287" y="158" width="20" height="14" rx="4" fill="#64748B" />'
            '<rect x="288" y="146" width="18" height="10" rx="3" fill="#334155" opacity="0.65" />'
            '<text x="282" y="205" text-anchor="middle" font-size="11" font-weight="700" fill="#F87171">WRONG WAY</text>'
        )
    else:
        overlay = (
            '<ellipse cx="280" cy="192" rx="102" ry="24" fill="#1D4ED8" opacity="0.30" />'
            '<ellipse cx="280" cy="192" rx="72" ry="14" fill="#38BDF8" opacity="0.17" />'
            '<path d="M 214 187 Q 246 181 278 188 T 352 186" stroke="#7DD3FC" stroke-width="1.4" fill="none" opacity="0.8" />'
            '<path d="M 210 198 Q 246 192 280 199 T 356 195" stroke="#7DD3FC" stroke-width="1.2" fill="none" opacity="0.55" />'
            '<rect x="312" y="196" width="12" height="26" rx="1" fill="#94A3B8" opacity="0.8" />'
            '<rect x="308" y="220" width="20" height="4" rx="1" fill="#64748B" />'
            '<text x="322" y="192" text-anchor="middle" font-size="10" font-weight="700" fill="#7DD3FC">18 cm</text>'
            '<text x="250" y="146" text-anchor="middle" font-size="11" font-weight="700" fill="#7DD3FC">STANDING WATER</text>'
        )

    return (
        '<svg viewBox="0 0 420 250" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="0" y="0" width="420" height="250" fill="#0A1321" />'
        '<rect x="0" y="0" width="420" height="118" fill="#0E1A2C" />'
        '<rect x="18" y="58" width="34" height="60" fill="#142135" />'
        '<rect x="60" y="42" width="22" height="76" fill="#111D30" />'
        '<rect x="340" y="52" width="28" height="66" fill="#142135" />'
        '<rect x="374" y="70" width="26" height="48" fill="#111D30" />'
        '<rect x="0" y="118" width="420" height="6" fill="#182842" />'
        '<path d="M 0 250 L 132 250 L 178 118 L 242 118 L 288 250 L 420 250 L 420 250 L 0 250 Z" fill="#182433" />'
        '<path d="M 204 118 L 160 250" stroke="#3B4B61" stroke-width="2" opacity="0.8" />'
        '<path d="M 216 118 L 260 250" stroke="#3B4B61" stroke-width="2" opacity="0.8" />'
        '<path d="M 210 160 L 202 190 M 210 208 L 198 250" stroke="#64748B" stroke-width="2" stroke-dasharray="8 8" opacity="0.6" />'
        '<circle cx="74" cy="205" r="5" fill="#64748B" />'
        '<rect x="69" y="210" width="10" height="22" rx="4" fill="#475569" />'
        '<circle cx="102" cy="200" r="4.5" fill="#64748B" />'
        '<rect x="98" y="205" width="9" height="20" rx="4" fill="#475569" />'
        '<rect x="88" y="199" width="7" height="7" fill="#334155" opacity="0.75" />'
        '<rect x="92" y="199" width="4" height="4" fill="#0F172A" opacity="0.8" />'
        '<rect x="65" y="199" width="4" height="4" fill="#0F172A" opacity="0.8" />'
        '<rect x="66" y="198" width="9" height="8" fill="#334155" opacity="0.7" />'
        + overlay
        + '<text x="14" y="22" font-size="10" fill="#94A3B8" font-family="monospace">CAM · 08:07:41 IST</text>'
        '<text x="406" y="22" text-anchor="end" font-size="10" fill="#94A3B8" font-family="monospace">10 s</text>'
        '<rect x="14" y="30" width="104" height="16" rx="3" fill="#0B1220" opacity="0.75" />'
        '<text x="20" y="41" font-size="8.5" fill="#F5C451" font-family="monospace">SIMULATED FRAME</text>'
        "</svg>"
    )


def clip_frame_html(incident: dict[str, Any]) -> str:
    kind_label = {
        "stopped_vehicle": "Stopped vehicle",
        "wrong_way": "Wrong-way movement",
        "waterlogging": "Standing water",
    }.get(incident["kind"], incident["kind"].title())
    aria = (
        f"Simulated edge clip placeholder for {incident['id']}: {kind_label} at {incident['location']}. "
        "The clip is ten seconds long. Faces and number plates are blurred at the edge device."
    )
    return (
        f'<div class="navi-clip" role="img" aria-label="{esc(aria).replace(chr(34), "&quot;")}">'
        '<div class="navi-clip-top"><span>EDGE CLIP · SIMULATED</span><span>10 s · 480p</span></div>'
        f'<div class="navi-clip-frame"><img src="{_data_uri(_clip_scene(incident))}" alt="" /></div>'
        f'<div class="navi-clip-foot"><span>{esc(incident["source"])}</span>'
        "<span>FACES + PLATES BLURRED AT EDGE</span></div>"
        "</div>"
    )


def flood_strip_html(zones: list[dict[str, Any]]) -> str:
    cells = []
    labels = []
    for zone in zones:
        level = int(zone["level"])
        color = FLOOD_COLORS.get(level, "#94A3B8")
        active = " active" if level >= 1 else ""
        cells.append(
            f'<div class="navi-fs-cell{active}"><div class="navi-fs-bar">'
            f'<span style="width:100%;background:{color}"></span></div>'
            f'<div class="navi-fs-label"><span>{esc(zone["label"])}</span><b>L{level}</b></div></div>'
        )
        labels.append(f'{zone["label"]} L{level}')
    aria = "Passability by stretch: " + "; ".join(labels)
    return (
        f'<div class="navi-flood-strip" role="img" aria-label="{esc(aria).replace(chr(34), "&quot;")}">'
        '<div class="navi-fs-head"><span>Monsoon passability · pilot corridor</span><b>L0 dry → L3 blocked</b></div>'
        f'<div class="navi-fs-cells">{"".join(cells)}</div>'
        "</div>"
    )


def flood_table_html(zones: list[dict[str, Any]]) -> str:
    rows = []
    for zone in zones:
        level = int(zone["level"])
        color = FLOOD_COLORS.get(level, "#94A3B8")
        info = core.FLOOD_LEVELS[level]
        rows.append(
            "<tr>"
            f"<td><b>{esc(zone['label'])}</b></td>"
            f'<td><span class="navi-chip-status" style="color:{color};border-color:{color}55;background:{color}14">L{level}</span></td>'
            f"<td>{esc(info['condition'])}</td>"
            f'<td class="navi-muted">{esc(info["use"])}</td>'
            f"<td>{esc(zone['updated'])}</td>"
            f'<td class="navi-muted">{esc(zone["evidence"])}</td>'
            "</tr>"
        )
    return (
        '<div class="navi-table-wrap"><table class="navi-table">'
        "<thead><tr><th>Stretch</th><th>Level</th><th>Condition</th><th>Operator &amp; 108 use</th><th>Updated</th><th>Evidence</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def evidence_table_html(rows: list[dict[str, str]]) -> str:
    body = []
    for row in rows:
        color = EVIDENCE_COLORS.get(row["status"], "#94A3B8")
        body.append(
            "<tr>"
            f"<td><b>{esc(row['module'])}</b></td>"
            f"<td class='navi-muted'>{esc(row['delivered'])}</td>"
            f'<td><span class="navi-chip-status" style="color:{color};border-color:{color}55;background:{color}14">'
            f"{esc(row['status'])}</span></td>"
            "</tr>"
        )
    return (
        '<div class="navi-table-wrap"><table class="navi-table">'
        "<thead><tr><th>Module</th><th>What this console does</th><th>Label</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def citci_bar_spec(readings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scored = [reading for reading in readings.values() if reading["score"] is not None]
    scored = list(reversed(scored))
    data = [
        {
            "value": reading["score"],
            "itemStyle": {
                "color": BAND_COLORS[reading["band"]],
                "borderRadius": [0, 4, 4, 0],
            },
        }
        for reading in scored
    ]
    return {
        "grid": {"left": 4, "right": 46, "top": 26, "bottom": 6, "containLabel": True},
        "xAxis": {
            "type": "value",
            "min": 0,
            "max": 100,
            "splitLine": {"lineStyle": {"color": "#1E2A3D"}},
            "axisLabel": {"color": "#8FA1B8", "fontSize": 10},
        },
        "yAxis": {
            "type": "category",
            "data": [reading["name"] for reading in scored],
            "axisTick": {"show": False},
            "axisLine": {"show": False},
            "axisLabel": {"color": "#C9D6E6", "fontSize": 11},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "series": [
            {
                "type": "bar",
                "data": data,
                "barWidth": 13,
                "label": {
                    "show": True,
                    "position": "right",
                    "color": "#DDE7F4",
                    "fontSize": 11,
                    "formatter": "{c}",
                },
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"color": "#FB923C", "type": "dashed", "width": 1},
                    "label": {"formatter": "High 56", "color": "#FB923C", "fontSize": 9},
                    "data": [{"xAxis": 56}],
                },
            }
        ],
    }


def outcome_bar_spec(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "grid": {"left": 6, "right": 12, "top": 42, "bottom": 8, "containLabel": True},
        "legend": {"top": 4, "textStyle": {"color": "#C9D6E6", "fontSize": 11}},
        "tooltip": {"trigger": "axis"},
        "dataset": {"source": frame},
        "xAxis": {
            "type": "category",
            "axisLabel": {"color": "#8FA1B8", "fontSize": 9, "interval": 0},
            "axisLine": {"lineStyle": {"color": "#26354C"}},
        },
        "yAxis": {
            "type": "value",
            "name": "min",
            "nameTextStyle": {"color": "#7F92AA"},
            "axisLabel": {"color": "#8FA1B8", "fontSize": 9},
            "splitLine": {"lineStyle": {"color": "#1E2A3D"}},
        },
        "series": [
            {
                "type": "bar",
                "name": "Expected",
                "encode": {"x": "Decision", "y": "Expected"},
                "barMaxWidth": 26,
                "itemStyle": {"color": "#2DD4BF", "borderRadius": [4, 4, 0, 0]},
            },
            {
                "type": "bar",
                "name": "Observed",
                "encode": {"x": "Decision", "y": "Observed"},
                "barMaxWidth": 26,
                "itemStyle": {"color": "#F5C451", "borderRadius": [4, 4, 0, 0]},
            },
        ],
    }


def baseline_line_spec(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "grid": {"left": 6, "right": 14, "top": 24, "bottom": 8, "containLabel": True},
        "tooltip": {"trigger": "axis"},
        "dataset": {"source": frame},
        "xAxis": {
            "type": "category",
            "axisLabel": {"color": "#8FA1B8", "fontSize": 9, "interval": 3},
            "axisLine": {"lineStyle": {"color": "#26354C"}},
        },
        "yAxis": {
            "type": "value",
            "min": 0,
            "max": 100,
            "axisLabel": {"color": "#8FA1B8", "fontSize": 9},
            "splitLine": {"lineStyle": {"color": "#1E2A3D"}},
        },
        "series": [
            {
                "type": "line",
                "name": "CItCI",
                "encode": {"x": "Hour", "y": "CItCI"},
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"color": "#2DD4BF", "width": 2.5},
                "areaStyle": {"color": "rgba(45, 212, 191, 0.13)"},
                "markLine": {
                    "silent": True,
                    "symbol": "none",
                    "lineStyle": {"color": "#F5C451", "type": "dashed", "width": 1},
                    "label": {"formatter": "08:10 snapshot", "color": "#F5C451", "fontSize": 9},
                    "data": [{"xAxis": "08:00"}],
                },
            }
        ],
    }
