from __future__ import annotations

import streamlit as st

import core
import ui

core.bootstrap()

ui.page_header(
    "Monsoon operations",
    "Passability by corridor stretch",
    "L0 dry → L3 blocked · flood-aware routing for operators, ASTC, and 108",
    badges=(
        ":blue-badge[MONSOON REPLAY] "
        ":orange-badge[SYNTHETIC RAIN + DRAINAGE CONTEXT] "
        ":green-badge[HUMAN-CONFIRMED LEVELS]"
    ),
)
st.caption(
    "Levels combine roadside evidence, bus-probe slowdown, and drainage context. "
    "Operators confirm every change before routing advice updates."
)

zones = core.flood_zones()
passability = core.corridor_passability()
open_water = [
    incident
    for incident in core.incidents_open()
    if incident["kind"] == "waterlogging"
]

with st.container(horizontal=True):
    st.metric(
        "Corridor passability",
        f"L{passability['level']}",
        border=True,
        help=passability["info"]["condition"],
    )
    st.metric(
        "Stretches at L2 or above",
        str(passability["elevated"]),
        border=True,
        help="L2 and L3 trigger rerouting for cars and 108 ambulances.",
    )
    st.metric(
        "Rainfall · last 60 min",
        "12 mm",
        border=True,
        help="Synthetic IMD-style scenario value; no rainfall feed is connected.",
    )
    st.metric(
        "Drainage watch",
        f"{sum(1 for zone in zones if zone['level'] >= 1)} zones",
        border=True,
        help="Stretches with any standing water in the current scenario.",
    )

st.html(ui.flood_strip_html(zones))

if open_water:
    st.info(
        f"{open_water[0]['id']} is an open L2 candidate at {open_water[0]['location']}. "
        "Confirm or reject it in Incident triage; confirming updates this board.",
        icon=":material/water:",
    )

st.space("small")
form_col, impact_col = st.columns([1.15, 1], gap="medium")

with form_col:
    with st.container(border=True):
        st.markdown("**Log a passability update**")
        zone_id = st.selectbox(
            "Stretch",
            [zone["id"] for zone in zones],
            format_func=lambda key: next(zone["label"] for zone in zones if zone["id"] == key),
            key="flood-zone",
        )
        current_level = int(st.session_state.flood_levels[zone_id]["level"])
        level = st.segmented_control(
            "New level",
            [0, 1, 2, 3],
            default=current_level,
            format_func=lambda value: f"L{value}",
            key=f"flood-level-{zone_id}-{current_level}",
            required=True,
        )
        level = int(level) if level is not None else current_level
        note_key = f"flood-note-{zone_id}-{current_level}"
        st.text_input(
            "Evidence note (logged)",
            key=note_key,
            placeholder="What did the operator or field staff observe?",
        )
        st.button(
            "Log passability update",
            type="primary",
            width="stretch",
            icon=":material/water_drop:",
            key=f"flood-submit-{zone_id}-{current_level}",
            on_click=core.set_flood,
            args=(zone_id, level, note_key),
        )
        st.caption(
            "This demo runs on synthetic rain and drainage data. ASSAC terrain and drainage layers "
            "are not connected."
        )

with impact_col:
    info = core.FLOOD_LEVELS[level]
    with st.container(border=True):
        st.markdown(f"**Impact preview · L{level}**")
        st.markdown(f"**{info['condition']}**")
        st.caption(info["use"])
        if level == 0:
            st.caption("108 routing and ASTC plans stay on the normal corridor.")
        elif level == 1:
            st.caption(
                "108 ETA adds about 1.5 min per affected segment. ASTC sees a caution notice; "
                "two-wheelers are offered an alternate."
            )
        elif level == 2:
            st.warning(
                "Cars and 108 ambulances reroute via GNB Road. Field traffic staff are alerted. "
                "Each affected 108 segment adds about 4 minutes.",
                title="L2 reroute active",
                icon=":material/alt_route:",
            )
        else:
            st.error(
                "The road link closes in routing. A 108 advisory cannot be issued across this "
                "stretch; escalate to municipal drainage and SDRF.",
                title="L3 · corridor blocked",
                icon=":material/block:",
            )
        st.caption(
            f"Selected stretch · {next(zone['label'] for zone in zones if zone['id'] == zone_id)} · "
            f"current level L{current_level}"
        )

st.space("small")
st.markdown("**Corridor passability board**")
st.html(ui.flood_table_html(zones))

st.caption(
    "Level changes in this console are session-local pilot records. In the field build, each change "
    "carries provenance, operator identity, and a timed audit entry."
)

ui.page_footer()
