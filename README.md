# Navig — Pilot console

Streamlit pilot console for **Intelligent Monitoring Flow** (NESPIC 2026 · Stream 1 · Problem D-22).
A map-first GS Road (Ganeshguri → GMCH) operations demo with coverage-aware CItCI scoring, incident and flood triage, ranked advisories, a 108 route plan, an outcomes check-back loop, and an evidence register.

> All telemetry is synthetic. No live camera, GPS, GIS, or dispatch feed is connected. Audit state is session-local and resets when the session ends.

## Deploy on Streamlit Community Cloud (free, no secrets)

1. Push the contents of this `Navig/` folder to a GitHub repository.
2. Open https://share.streamlit.io → **Create app**.
3. Select your repository and branch.
4. Set **Main file path**:
   - `Navig/streamlit_app.py` if `Navig/` sits inside a larger repository, or
   - `streamlit_app.py` if this folder is the repository root.
5. Choose Python 3.12 (Advanced settings) and click **Deploy**.
6. No secrets, database, or API keys are required.

## Run locally

```bash
cd Navig
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501.

## Console views

- **Corridor operations** — schematic map, coverage mask, CItCI breakdown, ranked advisory approval.
- **Incident triage** — confirm / reject / escalate simulated blurred-clip candidates.
- **Monsoon passability** — L0–L3 stretch updates that propagate to routing.
- **108 emergency corridor** — congestion- and flood-aware route plus junction plan; advisory only.
- **Outcomes & audit** — 90-minute observational check-backs, append-only session log, CSV export.
- **Evidence & governance** — capability labels, claim boundaries, G0–G5 gates, transparent scoring calculator.

## Project layout

```
Navig/
├── streamlit_app.py        # entrypoint + sidebar navigation
├── core.py                 # synthetic corridor engine, scoring, audit state
├── ui.py                   # map/clip HTML components and chart specs
├── assets/                 # logo + scoped console CSS
├── app_pages/              # six console views
├── .streamlit/config.toml  # dark control-room theme
├── requirements.txt
└── .gitignore
```

## Honest boundaries

- CItCI weights (`0.30 / 0.30 / 0.25 / 0.15`) are implemented and inspectable, but not field-calibrated.
- Missing coverage is shown as an abstention, never filled with an estimate.
- Signal actions, dispatch, and enforcement remain human-approved; the console is advisory only.
- Check-backs are observational comparisons against a synthetic baseline, not causal savings claims.

Built with Streamlit 1.67. Fully responsive down to tablet widths; best viewed in a 1366×768+ control-room layout.
