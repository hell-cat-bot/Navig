from __future__ import annotations

import pandas as pd
import streamlit as st

import core
import ui

core.bootstrap()

ui.page_header(
    "Emergency mobility",
    "108 advisory corridor",
    "Congestion- and flood-aware route preview with a junction-by-junction timing plan",
    badges=(
        ":blue-badge[SIMULATED DISPATCH] "
        ":green-badge[ADVISORY ONLY] "
        ":gray-badge[NO AUTOMATED SIGNAL CONTROL]"
    ),
)
st.caption(
    "The console proposes a route and a manual timing plan. Dispatchers and traffic police approve "
    "and execute every step; nothing is sent to a live dispatch system in this demo."
)

readings = core.current_readings(live=core.live_mode())
passability = core.corridor_passability()

with st.container(horizontal=True):
    st.metric(
        "Active advisories",
        str(len(core.open_advisories())),
        border=True,
        help="Advisories issued in this session or seeded in the replay example.",
    )
    st.metric(
        "Corridor passability",
        f"L{passability['level']}",
        border=True,
        help=passability["info"]["condition"],
    )
    st.metric(
        "Junctions with coverage",
        f"{sum(1 for reading in readings.values() if reading['score'] is not None)} of 8",
        border=True,
        help="Last Gate has no live reading and is excluded from scoring.",
    )
    st.metric(
        "Units configured",
        str(len(core.UNITS)),
        border=True,
        help="Demo units only. No GPS feed or dispatch integration is connected.",
    )

st.space("small")
control_col, preview_col = st.columns([1.15, 1], gap="medium")

with control_col:
    with st.container(border=True):
        st.markdown("**Request parameters**")
        unit_col, origin_col = st.columns(2)
        unit_key = unit_col.selectbox(
            "108 unit",
            list(core.UNITS.keys()),
            format_func=lambda key: core.UNITS[key],
            key="ems-unit",
        )
        origin_ids = [junction.id for junction in core.JUNCTIONS if junction.id != "gmch"]
        origin_id = origin_col.selectbox(
            "Declared origin",
            origin_ids,
            format_func=lambda key: readings[key]["name"],
            key="ems-origin",
        )
        st.text_input(
            "Destination",
            value="GMCH Gate · emergency bay",
            disabled=True,
            help="The pilot advisory destination is fixed at GMCH in this demo.",
        )
        route = core.route_advice(origin_id, "gmch", readings, core.flood_level_map())
        st.caption(
            "Priority: emergency · route uses current synthetic CItCI and confirmed flood levels."
        )

with preview_col:
    with st.container(border=True):
        st.markdown("**Advisory preview**")
        if route.get("blocked"):
            st.error(
                f"The corridor is blocked at L{route['level']} on {route['zone']}. "
                "A 108 advisory cannot be issued across this stretch in the demo.",
                title="Route blocked",
                icon=":material/block:",
            )
            st.caption(
                "Escalate to municipal drainage / SDRF. Alternate-route planning is out of scope "
                "for this console."
            )
        else:
            st.metric(
                "Estimated corridor time",
                f"{route['eta_low']:.0f}–{route['eta_high']:.0f} min",
                help="Range adds a 2.4-minute uncertainty margin to the congestion-adjusted estimate.",
            )
            st.caption(
                f"{route['distance']:.1f} km · free-flow {route['freeflow']:.0f} min · "
                f"coverage {route['coverage']} of {route['endpoints']} segments with a live reading"
            )
            st.markdown(
                ":green-badge[HUMAN-IN-THE-LOOP] :gray-badge[PRE-EMPTION REQUEST, NOT CONTROL]"
            )
            st.button(
                "Issue advisory",
                type="primary",
                width="stretch",
                icon=":material/local_hospital:",
                key="issue-advisory",
                on_click=core.issue_emergency_advisory,
                args=(unit_key, origin_id),
            )
            st.caption(
                "Advisory sharing stays manual in this demo: phone/radio to dispatch, then to the "
                "traffic control room."
            )

st.space("small")
with st.container(border=True):
    st.markdown("**Junction-by-junction plan**")
    if route.get("blocked"):
        st.caption("No plan is generated while the route is blocked.")
    else:
        plan_rows = [
            {
                "Junction": row["junction"],
                "ETA (min)": row["eta_min"],
                "CItCI": row["citci"] if row["citci"] is not None else "No data",
                "Water": row["flood"],
                "Advisory action": row["action"],
            }
            for row in route["plan"]
        ]
        plan_df = pd.DataFrame(plan_rows)
        st.dataframe(
            plan_df,
            hide_index=True,
            column_config={
                "ETA (min)": st.column_config.NumberColumn(format="%.1f"),
            },
            alt="Junction-by-junction 108 advisory plan with ETA, CItCI, water level, and manual action",
        )
        st.caption(
            "All signal actions are manual and within approved limits. The console never takes over "
            "a signal or issues a green wave on its own."
        )

st.space("small")
with st.container(border=True):
    st.markdown("**Active advisories**")
    advisories = core.open_advisories()
    if advisories:
        advisory_df = pd.DataFrame(
            [
                {
                    "Time": entry["ts"],
                    "ID": entry["id"],
                    "Route": entry["junction"],
                    "Expected": entry["expected"],
                    "Status": core.STATUS_LABELS.get(entry["status"], entry["status"]),
                }
                for entry in advisories
            ]
        )
        st.dataframe(
            advisory_df,
            hide_index=True,
            alt="Active 108 advisories with time, route, expected arrival and status",
        )
    else:
        st.caption("No open advisories. Issue one above after checking the junction plan.")

ui.page_footer()
