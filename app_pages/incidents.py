from __future__ import annotations

from statistics import median

import streamlit as st

import core
import ui

core.bootstrap()

KIND_BADGES = {"stopped_vehicle": "orange", "wrong_way": "red", "waterlogging": "blue"}
STATUS_BADGES = {"open": "blue", "confirmed": "green", "rejected": "gray", "escalated": "orange"}

ui.page_header(
    "Triage · operator loop",
    "Incident & flood triage",
    "Blurred 10-second clips · confirm, reject, or escalate in under a minute",
    badges=(
        ":blue-badge[EDGE-BLURRED CLIPS] "
        ":orange-badge[SIMULATED DETECTIONS] "
        ":green-badge[NO AUTOMATED ENFORCEMENT]"
    ),
)
st.caption(
    "Faces and number plates are blurred on the edge device before any clip leaves the junction. "
    "The frames below are placeholders — no real camera footage is used in this demo."
)

incidents = st.session_state.incidents
open_incidents = [incident for incident in incidents if incident["status"] == "open"]
resolved_this_session = [incident for incident in incidents if incident["status"] != "open"]
open_confidences = [incident["confidence"] for incident in open_incidents]

with st.container(horizontal=True):
    st.metric("Open candidates", str(len(open_incidents)), border=True)
    st.metric("Resolved this session", str(len(resolved_this_session)), border=True)
    st.metric(
        "Median detector confidence",
        f"{round(median(open_confidences) * 100)}%" if open_confidences else "—",
        border=True,
        help="Median confidence across the open queue. Confidence is not a correctness claim.",
    )
    st.metric(
        "Clip budget",
        "10 s",
        border=True,
        help="Evidence clips are capped at ten seconds and blurred at the edge.",
    )

st.space("small")

for incident in incidents:
    with st.container(border=True):
        clip_col, detail_col = st.columns([1.05, 1.55], gap="medium")
        with clip_col:
            st.html(ui.clip_frame_html(incident))
        with detail_col:
            st.markdown(f"#### {incident['title']}")
            st.caption(
                f"{incident['id']} · {incident['location']} · detected {incident['detected']} IST"
            )
            st.markdown(
                f":{KIND_BADGES.get(incident['kind'], 'gray')}-badge[{incident['id'].split('-')[0]}] "
                f":blue-badge[CONFIDENCE {round(incident['confidence'] * 100)}%] "
                f":gray-badge[{incident['clip']}]"
            )
            st.markdown(incident["detail"])
            st.caption(f"Evidence · {incident['source']}")

            if incident["kind"] == "waterlogging":
                st.caption(
                    "Confirming this candidate sets Last Gate → Bhangagarh to L2 and updates the "
                    "108 route plan."
                )

            if incident["status"] == "open":
                confirm_col, reject_col, escalate_col = st.columns(3)
                confirm_col.button(
                    "Confirm",
                    key=f"confirm-{incident['id']}",
                    type="primary",
                    width="stretch",
                    icon=":material/check:",
                    on_click=core.resolve_incident,
                    args=(incident["id"], "confirmed"),
                )
                reject_col.button(
                    "Reject",
                    key=f"reject-{incident['id']}",
                    width="stretch",
                    icon=":material/close:",
                    on_click=core.resolve_incident,
                    args=(incident["id"], "rejected"),
                )
                escalate_col.button(
                    "Escalate",
                    key=f"escalate-{incident['id']}",
                    width="stretch",
                    icon=":material/arrow_upward:",
                    on_click=core.resolve_incident,
                    args=(incident["id"], "escalated"),
                )
                st.caption(
                    "Confirm only after reviewing the blurred clip. Nothing is issued as a challan."
                )
            else:
                badge = STATUS_BADGES.get(incident["status"], "gray")
                st.markdown(
                    f":{badge}-badge[{incident['status'].upper()}] "
                    f":gray-badge[LOGGED {incident['resolved_at']} IST]"
                )
                if incident["kind"] == "waterlogging" and incident["status"] == "confirmed":
                    st.success(
                        "Passability for Last Gate → Bhangagarh is now L2. The 108 route planner and "
                        "the monsoon board reflect the change.",
                        icon=":material/water:",
                    )
                elif incident["status"] == "rejected":
                    st.info(
                        "Candidate rejected after clip review. The rejection is kept in the audit trail.",
                        icon=":material/block:",
                    )
                elif incident["status"] == "escalated":
                    st.warning(
                        "Escalated to the shift supervisor and field team. No automatic action was taken.",
                        icon=":material/arrow_upward:",
                    )

st.space("small")
with st.container(border=True):
    st.markdown("**Operator protocol**")
    st.caption(
        "1. Watch the full 10-second clip. 2. Confirm only when the hazard is visible in more than one frame. "
        "3. Cite the evidence source in the audit note. 4. Escalate when a field response is needed."
    )
    st.caption(
        "Privacy boundary · no face recognition, no automated challans, no raw video sent to the cloud, "
        "and no plate text is stored in this console."
    )

ui.page_footer()
