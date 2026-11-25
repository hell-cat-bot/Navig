from __future__ import annotations

import streamlit as st

import core
import ui

core.bootstrap()

ui.page_header(
    "Project evidence",
    "Evidence & governance",
    "What this console implements, what it simulates, and what it refuses to claim",
    badges=(
        ":green-badge[EVIDENCE LABELS] "
        ":orange-badge[NO FIELD ACCURACY CLAIM] "
        ":blue-badge[PRIVACY BY DESIGN]"
    ),
)
st.caption(
    "Every capability carries the proposal's evidence label: Implemented, Partial, Simulated, "
    "Proposed, or Not yet. The Streamlit console is a workflow demonstration, not the field pilot."
)

MODULE_ROWS = [
    {
        "module": "Urban traffic intelligence",
        "delivered": "Synthetic camera health, a visible coverage mask, and bus-probe fallback.",
        "status": "Simulated",
    },
    {
        "module": "Congestion & bottlenecks",
        "delivered": "CItCI formula, weighted breakdown, and explicit abstention when data is missing.",
        "status": "Implemented",
    },
    {
        "module": "Short-term forecasting",
        "delivered": "A Monday baseline profile for context only; no live forecast is produced.",
        "status": "Proposed",
    },
    {
        "module": "Incident & flood triage",
        "delivered": "Confirm / reject / escalate loop with blurred ten-second clip stand-ins.",
        "status": "Simulated",
    },
    {
        "module": "Traffic decision support",
        "delivered": "Ranked options, one-click approval, rationale, and a session audit trail.",
        "status": "Implemented",
    },
    {
        "module": "Emergency green corridor",
        "delivered": "Route preview and junction timing plan; no dispatch or signal integration.",
        "status": "Simulated",
    },
    {
        "module": "Geospatial console & APIs",
        "delivered": "Schematic corridor only; no GIS tiles, GeoJSON export, or API endpoints.",
        "status": "Partial",
    },
    {
        "module": "Vision pipeline",
        "delivered": "No camera connection, no trained Assam weights, no live inference.",
        "status": "Not connected",
    },
    {
        "module": "Assam field dataset",
        "delivered": "None. Every junction, incident, and flood level is synthetic.",
        "status": "Not yet",
    },
]

st.markdown("**Capability register**")
st.html(ui.evidence_table_html(MODULE_ROWS))
st.caption(
    "Labels follow the proposal's evidence rule. A capability is never upgraded because it looks "
    "right in a demo."
)

st.space("small")
claim_col, refuse_col = st.columns(2, gap="medium")
with claim_col:
    with st.container(border=True):
        st.markdown("**This console can claim**")
        st.markdown(
            "- The CItCI weights are visible and applied with the same formula shown in the proposal.\n"
            "- Coverage gaps appear as explicit abstentions; they are never filled with estimates.\n"
            "- Every operator action produces a time-stamped session audit record.\n"
            "- Flood levels, incident evidence, and advisories are clearly labelled by evidence status.\n"
            "- The demo deploys without secrets or paid external services."
        )
with refuse_col:
    with st.container(border=True):
        st.markdown("**This console refuses to claim**")
        st.markdown(
            "- No live camera, GPS, GIS, or dispatch feed is connected; no Assam field accuracy is claimed.\n"
            "- No automated signal control, challan, face recognition, or plate storage.\n"
            "- No causal congestion reduction; check-backs are observational.\n"
            "- No persistent multi-user records in this demo; the session resets on refresh.\n"
            "- No claim that the CItCI weights are calibrated until field counts pass the gates."
        )

st.space("small")
with st.container(border=True):
    st.markdown("**Scoring transparency**")
    st.caption(
        "Move the four inputs to see how CItCI responds. The default values are the Ganeshguri "
        "scenario inputs in this replay."
    )
    slider_col, result_col = st.columns([1.7, 1], gap="large")
    with slider_col:
        first, second = st.columns(2)
        occupancy = first.slider("Road occupancy", 0, 100, 86, key="calc-occupancy")
        speed_drop = second.slider("Speed drop", 0, 100, 80, key="calc-speed")
        spillback = first.slider("Queue spillback", 0, 100, 68, key="calc-spillback")
        hazard = second.slider("Hazard penalty", 0, 100, 20, key="calc-hazard")
    score = core.citci(occupancy, speed_drop, spillback, hazard)
    band = core.band_for(score)
    with result_col:
        st.metric("CItCI", str(round(score)), help="100 × clamp(weighted sum of the four inputs).")
        badge = {"Low": "green", "Moderate": "yellow", "High": "orange", "Severe": "red"}[band]
        st.markdown(f":{badge}-badge[{band.upper()}]")
        st.caption(
            f"Occupancy {occupancy * 0.30:.1f} + speed {speed_drop * 0.30:.1f} + "
            f"spillback {spillback * 0.25:.1f} + hazard {hazard * 0.15:.1f}."
        )
        st.caption("Weights v0.9 · not yet calibrated against Assam field counts.")

st.space("small")
with st.container(border=True):
    st.markdown("**Governance gates G0–G5**")
    st.markdown(
        "| Gate | Question answered | Evidence required | Demo position |\n"
        "|---|---|---|---|\n"
        "| G0 | Is scope and data access lawful and feasible? | DPIA draft, formal data requests, site list | Not started in demo |\n"
        "| G1 | Is the evaluation benchmark credible? | Annotation guide, kappa score, stratified counts | Not yet |\n"
        "| G2 | Does the pipeline run cleanly end to end? | Replay test report and provenance audit | This console is a workflow replay, not the measurement pipeline |\n"
        "| G3 | Are live field accuracy numbers acceptable? | Precision, recall, counting error, false-alarm rate | Not yet |\n"
        "| G4 | Is the tool safe and easy for staff to use? | Security test, usability score ≥70, operator sign-off | Not yet |\n"
        "| G5 | What can honestly be claimed and scaled? | Final evaluation report, claims register, external review | Not yet |"
    )
    st.caption(
        "No gate is passed by this demo. The console exists to show the operator loop before field "
        "data and camera access are granted."
    )

st.space("small")
privacy_col, provenance_col = st.columns(2, gap="medium")
with privacy_col:
    with st.container(border=True):
        st.markdown("**Privacy & safety boundary**")
        st.markdown(
            "- Faces and plates are blurred on the edge device before clips leave a junction.\n"
            "- Evidence clips are capped at ten seconds; the demo uses placeholders, not real footage.\n"
            "- No face recognition, automated challans, or identity matching.\n"
            "- No automated signal takeover; every action is advisory and operator-approved.\n"
            "- Role-based access and append-only records are required in the pilot build."
        )
with provenance_col:
    with st.container(border=True):
        st.markdown("**Data provenance & build**")
        st.markdown(
            "- Corridor readings: synthetic Monday 08:10 replay for GS Road.\n"
            "- Incidents, flood levels, bus probes, and rainfall context: synthetic scenario data.\n"
            "- CItCI weights v0.9 copied from the proposal; not field-calibrated.\n"
            "- Console: Streamlit app, entrypoint `streamlit_app.py`, no secrets required.\n"
            "- Audit state lives in session memory and resets when the session ends."
        )

ui.page_footer()
