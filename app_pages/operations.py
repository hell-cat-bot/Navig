from __future__ import annotations

from typing import Any

import streamlit as st

import core
import ui

core.bootstrap()

BAND_BADGES = {"Low": "green", "Moderate": "yellow", "High": "orange", "Severe": "red"}
RISK_BADGES = {"Low": "green", "Medium": "orange", "High": "red"}

ui.page_header(
    "Pilot console · Ulubari command",
    "Corridor operations",
    "GS Road · Ganeshguri → GMCH · 8 junctions · map-first decision loop",
    badges=(
        ":orange-badge[SYNTHETIC TELEMETRY] "
        ":blue-badge[MONDAY PEAK REPLAY] "
        ":green-badge[ADVISORY ONLY · HUMAN APPROVAL]"
    ),
)
st.caption(
    "Live simulator with seeded sensor health: one junction abstains because both cameras are offline. "
    "No live camera, GPS, or GIS feed is connected in this deployment."
)


def junction_card(reading: dict[str, Any], live: bool) -> None:
    with st.container(border=True):
        st.markdown(f"#### {reading['name']}")
        st.caption(
            f"{reading['approach']} · chainage {reading['km']:.2f} km · "
            f"{reading['cameras_online']} of {reading['cameras_total']} cameras online"
        )

        if reading["status"] == "abstain":
            st.markdown(":red-badge[NO READING] :gray-badge[ABSTAINED, NOT FILLED]")
            st.warning(
                "No CItCI is issued at this junction. Both cameras are offline, so the console keeps the gap visible instead of estimating a score.",
                title="Camera offline — no data",
                icon=":material/visibility_off:",
            )
            cols = st.columns(2)
            cols[0].metric("CItCI", "—", help="No score is issued without usable evidence.")
            cols[1].metric("Last heartbeat", "41 min", help="Edge node health check requested.")
            st.caption(
                "Sources: none live. Bus probes do not cover this stretch. "
                "The dashed corridor segment on the map is the coverage gap."
            )
        else:
            band = reading["band"]
            cols = st.columns(3)
            delta = reading["delta_15"]
            if delta is not None:
                cols[0].metric(
                    "CItCI",
                    str(reading["score"]),
                    delta=delta,
                    delta_color="inverse",
                )
            else:
                cols[0].metric("CItCI", str(reading["score"]))
            cols[1].metric("Confidence", f"{round(reading['confidence'] * 100)}%")
            cols[2].metric("Feed age", f"{reading['updated_s']} s")
            st.caption("CItCI delta compares with the 07:55 snapshot.")
            st.markdown(
                f":{BAND_BADGES[band]}-badge[{band.upper()}] "
                f":blue-badge[DAY] :gray-badge[{len(reading['sources'])} SOURCES]"
            )
            if reading["status"] == "low":
                st.info(
                    reading["stale_reason"],
                    title="Low-confidence reading",
                    icon=":material/signal_wifi_statusbar_connected_no_internet_4:",
                )
            st.html(ui.breakdown_html(reading))
            st.caption(
                "CItCI = 100 × clamp(0.30·occupancy + 0.30·speed drop + 0.25·spillback + "
                "0.15·hazard). Weights v0.9, not yet calibrated on Assam field counts."
            )
            st.markdown(f"**Likely cause** · {reading['cause_label']}")
            st.caption(reading["cause_note"])
            st.caption("Evidence · " + " · ".join(reading["sources"]))

        st.divider()
        if reading["status"] == "abstain":
            st.markdown("**Coverage response**")
        else:
            st.markdown("**Ranked responses**")
            st.caption("Ranked by expected delay saved, safety, cost, and reversibility.")

        options = core.options_for_junction(reading)
        option_ids = [option["id"] for option in options]
        selected_option_id = st.radio(
            "Ranked responses",
            option_ids,
            index=0,
            key=f"opt-{reading['id']}",
            format_func=lambda option_id: next(
                f"{option['title']} · {option['saved']}"
                for option in options
                if option["id"] == option_id
            ),
            label_visibility="collapsed",
        )
        option = next(item for item in options if item["id"] == selected_option_id)
        st.markdown(
            f":{RISK_BADGES.get(option['risk'], 'gray')}-badge[{option['risk']} risk] "
            f":gray-badge[EXPECTED {option['saved'].upper()}]"
        )
        st.caption(option["detail"])
        st.caption(f"Fairness note · {option['fairness']}")
        st.text_input(
            "Rationale (optional, logged)",
            key=f"why-{reading['id']}",
            placeholder="One line for the audit trail",
        )
        approve_label = "Log coverage response" if reading["status"] == "abstain" else "Approve advisory"
        st.button(
            approve_label,
            key=f"approve-{reading['id']}",
            type="primary",
            width="stretch",
            icon=":material/check_circle:",
            on_click=core.approve_option,
            args=(reading["id"],),
        )
        st.caption("Advisory only · no signal changes automatically · every action requires an operator and is logged.")

        last = core.last_entry_for(reading["name"])
        if last is not None:
            st.caption(
                f"Last logged {last['ts']} · {last['id']} · "
                f"{core.STATUS_LABELS.get(last['status'], last['status'])}"
            )


@st.fragment(run_every=30, key="ops-console")
def console() -> None:
    live = core.live_mode()
    readings = core.current_readings(live=live)
    summary = core.corridor_summary(readings)

    with st.container(horizontal=True, vertical_alignment="center", gap="large"):
        st.toggle(
            "Live simulation",
            value=live,
            key="live_feed",
            help="Adds small synthetic jitter every 30 seconds. No live feed is connected.",
        )
        st.pills(
            "Map layers",
            ["Incidents", "Flood", "Bus probes"],
            selection_mode="multi",
            default=["Incidents", "Flood"],
            key="map-layers",
            width="content",
        )
        st.caption(f"Scenario clock {core.scenario_now()} IST · refresh 30 s · synthetic")

    with st.container(horizontal=True):
        st.metric(
            "Corridor CItCI",
            str(summary["score"]),
            delta=summary["delta"],
            delta_description="vs 07:55",
            delta_color="inverse",
            border=True,
            help=f"Unweighted mean across {summary['reporting']} reporting junctions.",
        )
        st.metric(
            "Camera coverage",
            f"{summary['coverage']}%",
            border=True,
            help=f"{summary['cameras_online']} of {summary['cameras_total']} edge cameras reporting.",
        )
        st.metric(
            "Junctions reporting",
            f"{summary['reporting']} of 8",
            border=True,
            help=f"{summary['valid']} fully valid · {summary['low']} low confidence · {summary['abstain']} abstained.",
        )
        st.metric(
            "Open alerts",
            str(core.open_alert_count()),
            border=True,
            help="Open incident candidates plus stretches at L2 or above. Unverified until an operator confirms.",
        )

    selected_id = st.session_state.get("focus-junction") or st.session_state.selected_junction
    if selected_id not in readings:
        selected_id = "ganeshguri"

    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        st.html(
            ui.corridor_map(
                readings,
                selected_id,
                st.session_state.get("map-layers", ["Incidents", "Flood"]),
                live,
                core.incidents_open(),
                summary,
                core.scenario_now(),
                len(st.session_state.audit),
            )
        )
        choice = st.pills(
            "Focus junction",
            list(readings.keys()),
            default=selected_id,
            required=True,
            key="focus-junction",
            format_func=lambda junction_id: ui.junction_pill_label(readings[junction_id]),
            label_visibility="collapsed",
            width="stretch",
            wrap=True,
        )
        if choice:
            st.session_state.selected_junction = choice
            selected_id = choice

        with st.container(border=True):
            st.markdown("**CItCI by junction**")
            alt_text = "CItCI by junction. " + "; ".join(
                f"{reading['name']} {reading['score']} {reading['band']}"
                if reading["score"] is not None
                else f"{reading['name']} no data"
                for reading in readings.values()
            )
            st.echarts_chart(
                ui.citci_bar_spec(readings),
                height=300,
                alt=alt_text,
            )
            st.caption(
                "Last Gate is omitted from the chart: no camera reading, so no score is issued. "
                "The abstention stays visible rather than being filled."
            )

        with st.container(border=True):
            st.markdown("**Recent decisions**")
            recent = core.recent_audit_frame(3)[["Time", "Type", "Decision", "Status"]]
            st.dataframe(
                recent,
                hide_index=True,
                height=178,
                alt="Three most recent decisions with type and check-back status",
                column_config={
                    "Time": st.column_config.TextColumn(width=60),
                    "Type": st.column_config.TextColumn(width=88),
                    "Decision": st.column_config.TextColumn(width=286),
                    "Status": st.column_config.TextColumn(width=136),
                },
            )
            st.caption("The full log and CSV export live in Outcomes & audit.")

    with right:
        junction_card(readings[selected_id], live)

    st.caption(
        "Scenario replay, not field measurement. Coverage, incidents, flood levels, and decisions "
        "are synthetic pilot data for workflow demonstration."
    )


console()
ui.page_footer()
