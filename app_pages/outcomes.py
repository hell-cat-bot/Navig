from __future__ import annotations

import streamlit as st

import core
import ui

core.bootstrap()

ui.page_header(
    "Closed loop",
    "Outcomes & audit",
    "Every operator action is logged · check-backs compare against the Monday baseline",
    badges=(
        ":blue-badge[APPEND-ONLY LOG] "
        ":orange-badge[OBSERVATIONAL CHECK-BACKS] "
        ":gray-badge[SESSION-LOCAL IN DEMO]"
    ),
)
st.caption(
    "Check-backs are observational comparisons against a synthetic Monday baseline. "
    "They are not causal savings claims. A field pilot needs pre-registered gates and independent review."
)

pending = core.pending_decisions()
checked = core.checked_count()
median_gain = core.median_observed()

with st.container(horizontal=True):
    st.metric("Logged actions", str(len(st.session_state.audit)), border=True)
    st.metric(
        "Awaiting check-back",
        str(len(pending)),
        border=True,
        help="Advisories with an expected delay saving and no 90-minute check yet.",
    )
    st.metric(
        "Check-backs complete",
        str(checked),
        border=True,
        help="Observational comparisons recorded for approved advisories.",
    )
    st.metric(
        "Median observed gain",
        f"{median_gain} min" if median_gain is not None else "—",
        border=True,
        help="Median of logged check-backs. Sample is small and not a treatment effect.",
    )

st.space("small")
outcomes = core.outcome_frame()
baseline = core.baseline_frame()
chart_left, chart_right = st.columns(2, gap="medium")

with chart_left:
    with st.container(border=True):
        st.markdown("**Expected vs observed check-back**")
        if outcomes.empty:
            st.info(
                "No checked advisories yet. Approve an option, then pull its 90-minute check-back below.",
                icon=":material/hourglass_empty:",
            )
        else:
            st.echarts_chart(
                ui.outcome_bar_spec(outcomes),
                height=260,
                alt="Grouped bars comparing expected and observed delay recovery for checked advisories",
            )
            st.caption(
                "Seeded replay rows plus any check-backs you log this session. "
                "Observed values are observational and may include confounding traffic."
            )

with chart_right:
    with st.container(border=True):
        st.markdown("**Monday corridor baseline**")
        st.echarts_chart(
            ui.baseline_line_spec(baseline),
            height=260,
            alt="Synthetic Monday CItCI profile peaking near 08:00 and 18:00",
        )
        st.caption(
            "Synthetic weekday profile for context only. It is not an Assam field baseline."
        )

st.space("small")
check_col, note_col = st.columns([1.15, 1], gap="medium")

with check_col:
    with st.container(border=True):
        st.markdown("**Pull a 90-minute check-back**")
        if pending:
            decision_ids = [entry["id"] for entry in pending]
            decision_id = st.selectbox(
                "Pending decision",
                decision_ids,
                format_func=lambda key: next(
                    f"{entry['id']} · {entry['title']} · {entry['junction']}"
                    for entry in pending
                    if entry["id"] == key
                ),
                key=f"checkback-{len(pending)}-{pending[0]['id']}",
            )
            st.button(
                "Pull check-back",
                type="primary",
                width="stretch",
                icon=":material/query_stats:",
                key="run-checkback",
                on_click=core.record_outcome,
                args=(decision_id,),
            )
            st.caption(
                "Records a simulated 90-minute observation against the Monday baseline and marks the "
                "advisory as checked."
            )
        else:
            st.caption(
                "No advisories are waiting for a check-back. Approve a ranked option in Corridor "
                "operations to create one."
            )
        latest_outcome = next(
            (
                entry
                for entry in st.session_state.audit
                if entry["kind"] == "outcome"
            ),
            None,
        )
        if latest_outcome is not None:
            st.caption(
                f"Latest check-back · {latest_outcome['ts']} · {latest_outcome['title']} · "
                f"{latest_outcome.get('observed') or 'recorded'}"
            )

with note_col:
    with st.container(border=True):
        st.markdown("**How the evidence loop works**")
        st.caption(
            "1. An operator approves a ranked option and a check-back time is scheduled. "
            "2. The shift later compares the corridor reading with the baseline. "
            "3. The observation is stored with the original rationale and model version. "
            "4. Nothing is labelled a causal saving without a comparison group."
        )
        st.caption(
            "In the pilot build this log lands in an append-only records service with role-based "
            "access. This Streamlit demo keeps it in session state and resets on refresh."
        )

st.space("small")
with st.container(border=True):
    header_col, download_col = st.columns([2.4, 1], vertical_alignment="center")
    header_col.markdown("**Decision & outcome log**")
    audit = core.audit_frame()
    download_col.download_button(
        "Export CSV",
        data=audit.to_csv(index=False),
        file_name="navig_pilot_audit.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )
    display = audit.drop(columns=["ID"])
    st.dataframe(
        display,
        hide_index=True,
        height=min(420, 38 + 35 * len(display)),
        alt="Decision and outcome log with time, type, location, expected gain, observed result and status",
        column_config={
            "Time": st.column_config.TextColumn(width=60),
            "Type": st.column_config.TextColumn(width=86),
            "Location": st.column_config.TextColumn(width=130),
            "Decision": st.column_config.TextColumn(width=250),
            "Expected": st.column_config.TextColumn(width=96),
            "Observed": st.column_config.TextColumn(width=142),
            "Status": st.column_config.TextColumn(width=140),
        },
    )
    st.caption(
        "Seeded rows recreate a Monday shift example. New actions from this session appear at the top."
    )

ui.page_footer()
