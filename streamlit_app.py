from __future__ import annotations

from pathlib import Path

import streamlit as st

import core

ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="Navig · Pilot console",
    page_icon=str(ASSETS / "icon.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
)

core.bootstrap()

st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "icon.svg"))

console_pages = [
    st.Page(
        "app_pages/operations.py",
        title="Corridor operations",
        icon=":material/map:",
        default=True,
    ),
    st.Page(
        "app_pages/incidents.py",
        title="Incident triage",
        icon=":material/notifications_active:",
    ),
    st.Page(
        "app_pages/flood.py",
        title="Monsoon passability",
        icon=":material/water:",
    ),
    st.Page(
        "app_pages/emergency.py",
        title="108 emergency corridor",
        icon=":material/emergency:",
    ),
    st.Page(
        "app_pages/outcomes.py",
        title="Outcomes & audit",
        icon=":material/history:",
    ),
]
project_pages = [
    st.Page(
        "app_pages/evidence.py",
        title="Evidence & governance",
        icon=":material/verified:",
    )
]

navigation = st.navigation(
    {"Pilot console": console_pages, "Project": project_pages},
    position="sidebar",
)

with st.sidebar:
    st.markdown(f"**{core.APP['operator']}**")
    st.caption("Ulubari command centre · shift 07:00–15:00")
    st.markdown(":green-badge[CONSOLE ONLINE] :orange-badge[SYNTHETIC FEED]")
    st.divider()
    st.caption("PILOT CORRIDOR")
    st.markdown("**GS Road** · Ganeshguri → GMCH")
    st.caption("4.2 km · 8 junctions · Monday peak replay")
    st.divider()
    if st.button("Reset demo session", icon=":material/restart_alt:", width="stretch"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.caption(f"{core.APP['pilot_ref']} · console v{core.APP['version']}")

navigation.run()
