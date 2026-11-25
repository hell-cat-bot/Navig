"""Synthetic corridor engine for the Navig pilot console.

Every reading is generated locally. No camera, GPS, GIS, or dispatch feed
is connected in this deployment.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

import pandas as pd
import streamlit as st

APP: dict[str, str] = {
    "name": "Navig",
    "project": "Intelligent Monitoring Flow",
    "corridor": "GS Road · Ganeshguri → GMCH",
    "city": "Guwahati, Assam",
    "length_km": "4.2",
    "operator": "Operator A",
    "command": "Ulubari command centre",
    "pilot_ref": "NESPIC 2026 · Stream 1 · D-22",
    "scenario": "Monday peak replay",
    "version": "0.9",
}

WEIGHTS: dict[str, float] = {
    "occupancy": 0.30,
    "speed_drop": 0.30,
    "spillback": 0.25,
    "hazard": 0.15,
}

FLOOD_LEVELS: dict[int, dict[str, str]] = {
    0: {
        "name": "L0 · Dry",
        "condition": "Dry carriageway",
        "use": "Normal traffic routing and standard signal timing.",
    },
    1: {
        "name": "L1 · Shallow",
        "condition": "Shallow water, passable",
        "use": "Caution alert; suggest safer alternates for two-wheelers.",
    },
    2: {
        "name": "L2 · Impassable for small cars",
        "condition": "Impassable for small cars",
        "use": "Reroute cars and 108 ambulances; alert field traffic staff.",
    },
    3: {
        "name": "L3 · All vehicles blocked",
        "condition": "All vehicles blocked",
        "use": "Close the road link in routing; escalate to drainage / SDRF.",
    },
}


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def citci(occupancy: float, speed_drop: float, spillback: float, hazard: float) -> float:
    score = (
        WEIGHTS["occupancy"] * occupancy
        + WEIGHTS["speed_drop"] * speed_drop
        + WEIGHTS["spillback"] * spillback
        + WEIGHTS["hazard"] * hazard
    )
    return clamp(score)


def band_for(score: float) -> str:
    if score <= 35:
        return "Low"
    if score <= 55:
        return "Moderate"
    if score <= 75:
        return "High"
    return "Severe"


@dataclass(frozen=True)
class Junction:
    id: str
    name: str
    approach: str
    zone: str
    km: float
    cameras_total: int
    cameras_online: int
    occupancy: float
    speed_drop: float
    spillback: float
    hazard: float
    confidence: float
    cause: str
    cause_label: str
    cause_note: str
    sources: tuple[str, ...]
    status: str = "valid"
    stale_reason: str = ""


JUNCTIONS: tuple[Junction, ...] = (
    Junction(
        id="ganeshguri",
        name="Ganeshguri",
        approach="Approach from Ganesh Mandir",
        zone="z1",
        km=0.0,
        cameras_total=3,
        cameras_online=3,
        occupancy=86,
        speed_drop=80,
        spillback=68,
        hazard=20,
        confidence=0.78,
        cause="peak",
        cause_label="Peak demand + roadside parking",
        cause_note="Recurring Monday queue; nearside parking narrows the approach.",
        sources=("CAM-01", "CAM-02", "BUS-GPS"),
    ),
    Junction(
        id="ganesh_mandir",
        name="Ganesh Mandir",
        approach="Approach from Ganeshguri",
        zone="z1",
        km=0.55,
        cameras_total=2,
        cameras_online=2,
        occupancy=78,
        speed_drop=70,
        spillback=56,
        hazard=12,
        confidence=0.81,
        cause="peak",
        cause_label="Peak demand · school approach",
        cause_note="School drop-off traffic conflicts with the eastbound lane.",
        sources=("CAM-04", "BUS-GPS"),
    ),
    Junction(
        id="abc",
        name="ABC Point",
        approach="Approach from Ganesh Mandir",
        zone="z1",
        km=1.15,
        cameras_total=2,
        cameras_online=2,
        occupancy=71,
        speed_drop=62,
        spillback=49,
        hazard=10,
        confidence=0.74,
        cause="signal",
        cause_label="Signal imbalance",
        cause_note="Eastbound green under-serves the current arrival rate.",
        sources=("CAM-07", "BUS-GPS"),
    ),
    Junction(
        id="dispur",
        name="Dispur",
        approach="Approach from ABC Point",
        zone="z2",
        km=1.75,
        cameras_total=2,
        cameras_online=1,
        occupancy=58,
        speed_drop=46,
        spillback=38,
        hazard=8,
        confidence=0.51,
        cause="signal",
        cause_label="Signal imbalance · partial coverage",
        cause_note="One camera offline; score is low confidence and bus-probe weighted.",
        sources=("CAM-09", "BUS-GPS"),
        status="low",
        stale_reason="1 of 2 cameras online. Speed comes from bus probes only.",
    ),
    Junction(
        id="last_gate",
        name="Last Gate",
        approach="Approach from Dispur",
        zone="z3",
        km=2.35,
        cameras_total=2,
        cameras_online=0,
        occupancy=0,
        speed_drop=0,
        spillback=0,
        hazard=0,
        confidence=0.0,
        cause="unknown",
        cause_label="No live reading",
        cause_note="Edge node offline. No CItCI is issued for this junction.",
        sources=(),
        status="abstain",
        stale_reason="Both cameras offline. Last heartbeat 41 minutes ago.",
    ),
    Junction(
        id="bhangagarh",
        name="Bhangagarh",
        approach="Approach from Last Gate",
        zone="z4",
        km=2.95,
        cameras_total=2,
        cameras_online=2,
        occupancy=64,
        speed_drop=60,
        spillback=60,
        hazard=45,
        confidence=0.69,
        cause="stalled",
        cause_label="Stalled vehicle / lane block",
        cause_note="A stopped vehicle blocks one of three lanes; queue reaches upstream.",
        sources=("CAM-14", "CAM-18"),
    ),
    Junction(
        id="gmc_junction",
        name="GMC Junction",
        approach="Approach from Bhangagarh",
        zone="z5",
        km=3.55,
        cameras_total=3,
        cameras_online=2,
        occupancy=48,
        speed_drop=38,
        spillback=30,
        hazard=6,
        confidence=0.72,
        cause="works",
        cause_label="Roadworks / event",
        cause_note="Utility works narrow the left lane on the hospital approach.",
        sources=("CAM-21", "BUS-GPS"),
    ),
    Junction(
        id="gmch",
        name="GMCH Gate",
        approach="Approach from GMC Junction",
        zone="z5",
        km=4.15,
        cameras_total=2,
        cameras_online=2,
        occupancy=44,
        speed_drop=30,
        spillback=26,
        hazard=4,
        confidence=0.66,
        cause="peak",
        cause_label="Hospital gate activity",
        cause_note="Arrival and drop-off activity slows the final 300 m.",
        sources=("CAM-24", "BUS-GPS"),
    ),
)

PREV_SCORES: dict[str, float | None] = {
    "ganeshguri": 64,
    "ganesh_mandir": 57,
    "abc": 49,
    "dispur": 39,
    "last_gate": None,
    "bhangagarh": 52,
    "gmc_junction": 33,
    "gmch": 29,
}

_JUNCTION_INDEX = {junction.id: index for index, junction in enumerate(JUNCTIONS)}

SEGMENT_ZONE: dict[tuple[str, str], str] = {
    ("ganeshguri", "ganesh_mandir"): "z1",
    ("ganesh_mandir", "abc"): "z1",
    ("abc", "dispur"): "z2",
    ("dispur", "last_gate"): "z3",
    ("last_gate", "bhangagarh"): "z4",
    ("bhangagarh", "gmc_junction"): "z5",
    ("gmc_junction", "gmch"): "z5",
}

OPTION_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "peak": [
        {
            "id": "parking_plan",
            "title": "Enforce parking & hold signal plan",
            "saved": "6–11 min",
            "expected_min": 8.5,
            "risk": "Low",
            "detail": "Clear the nearside encroachment, then hold the Ganeshguri release for one cycle.",
            "fairness": "Keeps the school approach on Ganesh Mandir open.",
        },
        {
            "id": "retime_phase",
            "title": "Retime signal phase within approved limits",
            "saved": "3–6 min",
            "expected_min": 4.5,
            "risk": "Medium",
            "detail": "Add 15 s to the eastbound green at the next approved change window.",
            "fairness": "Cross traffic waits up to one extra cycle.",
        },
        {
            "id": "public_alert",
            "title": "Issue public advisory for alternate route",
            "saved": "2–4 min",
            "expected_min": 3.0,
            "risk": "Low",
            "detail": "Ask commuters to use GNB Road until the queue clears.",
            "fairness": "Diverts demand only to a published alternate.",
        },
    ],
    "signal": [
        {
            "id": "rebalance",
            "title": "Rebalance signal split at ABC",
            "saved": "4–8 min",
            "expected_min": 6.0,
            "risk": "Medium",
            "detail": "Shift 10 s from the side road to the eastbound phase within limits.",
            "fairness": "Side-road queues stay under the 2-cycle target.",
        },
        {
            "id": "point_duty",
            "title": "Manual point-duty at the junction",
            "saved": "3–5 min",
            "expected_min": 4.0,
            "risk": "Low",
            "detail": "Place one officer at the mouth of the junction during the peak.",
            "fairness": "Officer judgement is logged with the decision.",
        },
        {
            "id": "hold_upstream",
            "title": "Hold upstream release for 90 s",
            "saved": "2–4 min",
            "expected_min": 3.0,
            "risk": "Low",
            "detail": "Create a short gap so the junction can drain before the next release.",
            "fairness": "Adds a short wait upstream; no lane closure.",
        },
    ],
    "stalled": [
        {
            "id": "patrol",
            "title": "Dispatch patrol to clear the lane",
            "saved": "5–9 min",
            "expected_min": 7.0,
            "risk": "Low",
            "detail": "Nearest field unit is 4 minutes away; clear the stopped vehicle.",
            "fairness": "No diversion pushed into the school zone.",
        },
        {
            "id": "lane_merge",
            "title": "Merge advisory + upstream hold",
            "saved": "3–6 min",
            "expected_min": 4.5,
            "risk": "Medium",
            "detail": "Hold the upstream release while the blocked lane merges.",
            "fairness": "Upstream wait increases briefly.",
        },
        {
            "id": "avoid_beltola",
            "title": "Advisory: avoid eastbound GS Road",
            "saved": "1–3 min",
            "expected_min": 2.0,
            "risk": "Low",
            "detail": "Send a short public advisory while the lane is cleared.",
            "fairness": "Alternate route passes one residential stretch.",
        },
    ],
    "water": [
        {
            "id": "reroute",
            "title": "Reroute cars and 108 via GNB Road",
            "saved": "6–10 min",
            "expected_min": 8.0,
            "risk": "Medium",
            "detail": "Avoid the flooded nearside lane and hold routing on the alternate.",
            "fairness": "Adds load to GNB Road; monitored for spillback.",
        },
        {
            "id": "drainage",
            "title": "Alert municipal drainage crew",
            "saved": "3–8 min",
            "expected_min": 5.5,
            "risk": "Low",
            "detail": "Clear the blocked outfall before the water crosses the median.",
            "fairness": "No neighbourhood-level diversion.",
        },
        {
            "id": "close_lane",
            "title": "Close nearside lane at Bhangagarh",
            "saved": "4–7 min",
            "expected_min": 5.5,
            "risk": "Medium",
            "detail": "Coning and marshal approval required before any lane closure.",
            "fairness": "Two-wheelers keep the remaining lane.",
        },
    ],
    "works": [
        {
            "id": "marshal",
            "title": "Add marshal at the works taper",
            "saved": "3–6 min",
            "expected_min": 4.5,
            "risk": "Low",
            "detail": "Manual merge control at the lane taper until the peak subsides.",
            "fairness": "Works contractor retains closure permit.",
        },
        {
            "id": "narrow_window",
            "title": "Shift works to the off-peak window",
            "saved": "2–5 min",
            "expected_min": 3.5,
            "risk": "Medium",
            "detail": "Coordinate with the utility contractor to pause during peak.",
            "fairness": "Contractor schedule changes need sign-off.",
        },
        {
            "id": "advisory_works",
            "title": "Publish works advisory",
            "saved": "1–3 min",
            "expected_min": 2.0,
            "risk": "Low",
            "detail": "Tell hospital-bound traffic to use the east gate approach.",
            "fairness": "No route forced; advisory only.",
        },
    ],
    "unknown": [
        {
            "id": "verify",
            "title": "Request field verification",
            "saved": "Restores certainty",
            "expected_min": 0.0,
            "risk": "Low",
            "detail": "Ask the nearest patrol to confirm the cause before acting.",
            "fairness": "No unverified action is taken.",
        },
        {
            "id": "monitor",
            "title": "Monitor only; keep baseline plan",
            "saved": "No delay saved",
            "expected_min": 0.0,
            "risk": "Low",
            "detail": "Watch the next 10-minute trend without changing the signal plan.",
            "fairness": "No intervention, no diversion.",
        },
        {
            "id": "bus_probe",
            "title": "Use bus probes as a low-confidence fallback",
            "saved": "Coverage only",
            "expected_min": 0.0,
            "risk": "Medium",
            "detail": "Publish a low-confidence speed estimate from ASTC probes.",
            "fairness": "Cause cannot be confirmed from speed alone.",
        },
    ],
    "abstain": [
        {
            "id": "field_check",
            "title": "Request field / lens check",
            "saved": "Restores coverage",
            "expected_min": 0.0,
            "risk": "Low",
            "detail": "Dispatch a camera health check; no traffic action can be scored.",
            "fairness": "No estimate is filled in while coverage is missing.",
        },
        {
            "id": "bus_gps_only",
            "title": "Rely on bus probes only",
            "saved": "Low-confidence speed",
            "expected_min": 0.0,
            "risk": "Medium",
            "detail": "Publish moving-probe speed without a CItCI or cause tag.",
            "fairness": "Abstention stays visible on the console.",
        },
        {
            "id": "notify_control",
            "title": "Notify control room of camera outage",
            "saved": "Coverage only",
            "expected_min": 0.0,
            "risk": "Low",
            "detail": "Log the outage against the edge-node maintenance ticket.",
            "fairness": "No traffic decision is made from missing data.",
        },
    ],
}

SEED_FLOOD_ZONES: tuple[dict[str, Any], ...] = (
    {"id": "z1", "label": "Ganeshguri → ABC", "level": 0, "updated": "08:02", "evidence": "Dry · bus probes only"},
    {"id": "z2", "label": "ABC → Dispur", "level": 1, "updated": "08:00", "evidence": "Shallow water at drain crossing"},
    {"id": "z3", "label": "Dispur → Last Gate", "level": 1, "updated": "07:58", "evidence": "Shallow water · bus probe slowdown"},
    {"id": "z4", "label": "Last Gate → Bhangagarh", "level": 1, "updated": "08:07", "evidence": "Rising water · ASSAC drainage layer + CAM-18"},
    {"id": "z5", "label": "Bhangagarh → GMCH", "level": 0, "updated": "08:02", "evidence": "Dry · no standing water"},
)

SEED_INCIDENTS: tuple[dict[str, Any], ...] = (
    {
        "id": "INC-0841",
        "kind": "stopped_vehicle",
        "title": "Stopped vehicle in live lane",
        "location": "GS Road eastbound · chainage 2.4",
        "junction": "Bhangagarh",
        "confidence": 0.83,
        "detail": "42 s dwell · 1 of 3 lanes · queue forming upstream",
        "source": "CAM-14 · edge detector",
        "clip": "10 s clip · plates blurred at edge",
        "detected": "08:06",
        "status": "open",
        "flood_zone": None,
        "flood_level": None,
        "resolved_at": None,
    },
    {
        "id": "INC-0844",
        "kind": "wrong_way",
        "title": "Wrong-way movement",
        "location": "Ganesh Mandir · eastbound slip lane",
        "junction": "Ganesh Mandir",
        "confidence": 0.61,
        "detail": "2 frames · scooter entering the one-way slip",
        "source": "CAM-04 · edge detector",
        "clip": "10 s clip · faces blurred at edge",
        "detected": "08:04",
        "status": "open",
        "flood_zone": None,
        "flood_level": None,
        "resolved_at": None,
    },
    {
        "id": "WL-021",
        "kind": "waterlogging",
        "title": "Standing water · L2 candidate",
        "location": "Last Gate → Bhangagarh · nearside lane",
        "junction": "Bhangagarh",
        "confidence": 0.71,
        "detail": "18 cm depth estimate · drain outfall blocked",
        "source": "CAM-18 + ASSAC drainage layer",
        "clip": "10 s clip · plates blurred at edge",
        "detected": "08:07",
        "status": "open",
        "flood_zone": "z4",
        "flood_level": 2,
        "resolved_at": None,
    },
)

SEED_AUDIT: tuple[dict[str, Any], ...] = (
    {
        "id": "DEC-009",
        "ts": "07:58",
        "kind": "emergency",
        "junction": "Ganeshguri → GMCH",
        "title": "108 advisory · U-108-02 → GMCH",
        "expected": "ETA 12–14 min",
        "status": "advisory_open",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": None,
        "observed_min": None,
        "observed": None,
        "checked_at": None,
        "detail": "Routed around L1 water at ABC → Dispur; manual signal holds listed.",
    },
    {
        "id": "DEC-008",
        "ts": "07:52",
        "kind": "option",
        "junction": "Ganeshguri",
        "title": "Enforce parking & hold signal plan",
        "expected": "6–11 min",
        "status": "pending_check",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": 8.5,
        "observed_min": None,
        "observed": None,
        "checked_at": None,
        "detail": "Cleared nearside encroachment; hold approved for one cycle.",
    },
    {
        "id": "DEC-007",
        "ts": "07:44",
        "kind": "incident",
        "junction": "Bhangagarh",
        "title": "Confirmed stopped vehicle · INC-0838",
        "expected": "—",
        "status": "logged",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": None,
        "observed_min": None,
        "observed": None,
        "checked_at": None,
        "detail": "Blurred 10 s clip reviewed; patrol dispatched.",
    },
    {
        "id": "DEC-006",
        "ts": "07:31",
        "kind": "flood",
        "junction": "Bhangagarh → GMCH",
        "title": "L1 set · Bhangagarh → GMCH",
        "expected": "—",
        "status": "logged",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": None,
        "observed_min": None,
        "observed": None,
        "checked_at": None,
        "detail": "Shallow water at drain crossing; two-wheeler caution issued.",
    },
    {
        "id": "DEC-005",
        "ts": "07:14",
        "kind": "option",
        "junction": "Ganeshguri",
        "title": "Retime signal phase within approved limits",
        "expected": "3–6 min",
        "status": "checked",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": 4.5,
        "observed_min": 4.1,
        "observed": "4.1 min (obs.)",
        "checked_at": "08:04",
        "detail": "15 s added to eastbound green at the approved window.",
    },
    {
        "id": "DEC-004",
        "ts": "06:58",
        "kind": "option",
        "junction": "ABC Point",
        "title": "Hold upstream release for 90 s",
        "expected": "2–4 min",
        "status": "checked",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": 3.0,
        "observed_min": 2.4,
        "observed": "2.4 min (obs.)",
        "checked_at": "07:48",
        "detail": "Short upstream hold; junction drained before next release.",
    },
    {
        "id": "DEC-003",
        "ts": "06:41",
        "kind": "option",
        "junction": "Ganesh Mandir",
        "title": "Manual point-duty at the junction",
        "expected": "3–5 min",
        "status": "checked",
        "operator": "Operator A",
        "mode": "Advisory only",
        "expected_min": 4.0,
        "observed_min": 5.2,
        "observed": "5.2 min · unclear",
        "checked_at": "07:31",
        "detail": "School peak and a bus breakdown overlapped the intervention.",
    },
)

UNITS: dict[str, str] = {
    "U-108-04": "108-04 · ALS · Ganeshguri",
    "U-108-02": "108-02 · BLS · Dispur",
    "U-108-07": "108-07 · ALS · Bhangagarh",
}

BASELINE_HOURS = ["05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00"]
BASELINE_SCORES = [22, 31, 48, 62, 58, 47, 42, 40, 44, 43, 46, 52, 60, 66, 58, 47, 36, 28]

STATUS_LABELS: dict[str, str] = {
    "pending_check": "Awaiting check-back",
    "checked": "Checked",
    "logged": "Logged",
    "advisory_open": "Advisory open",
    "recorded": "Recorded",
    "confirmed": "Confirmed",
    "rejected": "Rejected",
    "escalated": "Escalated",
    "open": "Open",
}

KIND_LABELS: dict[str, str] = {
    "option": "Advisory",
    "incident": "Incident",
    "flood": "Passability",
    "emergency": "108",
    "outcome": "Outcome",
}


def bootstrap() -> None:
    ss = st.session_state
    if ss.get("bootstrapped"):
        return
    ss.bootstrapped = True
    ss.live_feed = True
    ss.selected_junction = "ganeshguri"
    ss.incidents = [dict(incident) for incident in SEED_INCIDENTS]
    ss.flood_levels = {
        zone["id"]: {"level": zone["level"], "updated": zone["updated"], "evidence": zone["evidence"]}
        for zone in SEED_FLOOD_ZONES
    }
    ss.audit = [dict(record) for record in SEED_AUDIT]
    ss.decision_seq = 10
    ss.actions = 0
    ss.last_advisory_id = "DEC-009"


def scenario_now() -> str:
    base = datetime(2026, 6, 15, 8, 10)
    return (base + timedelta(minutes=2 * st.session_state.get("actions", 0))).strftime("%H:%M")


def live_mode() -> bool:
    return bool(st.session_state.get("live_feed", True))


def current_readings(live: bool = True) -> dict[str, dict[str, Any]]:
    bucket = int(time.time() // 30) if live else 0
    readings: dict[str, dict[str, Any]] = {}
    for spec in JUNCTIONS:
        base: dict[str, Any] = {
            "id": spec.id,
            "name": spec.name,
            "approach": spec.approach,
            "km": spec.km,
            "cameras_total": spec.cameras_total,
            "cameras_online": spec.cameras_online,
            "sources": spec.sources,
            "cause": spec.cause,
            "cause_label": spec.cause_label,
            "cause_note": spec.cause_note,
            "status": spec.status,
            "stale_reason": spec.stale_reason,
            "updated_s": 24 if live else 18,
        }
        if spec.status == "abstain":
            base.update(
                occupancy=None,
                speed_drop=None,
                spillback=None,
                hazard=None,
                confidence=None,
                score=None,
                band=None,
                points={},
                updated_s=2460,
                delta_15=None,
            )
            readings[spec.id] = base
            continue

        occupancy = spec.occupancy
        speed_drop = spec.speed_drop
        spillback = spec.spillback
        hazard = spec.hazard
        confidence = spec.confidence
        if live:
            rng = random.Random(f"{spec.id}:{bucket}")
            occupancy = clamp(occupancy + rng.uniform(-2.5, 2.5))
            speed_drop = clamp(speed_drop + rng.uniform(-2.5, 2.5))
            spillback = clamp(spillback + rng.uniform(-2.0, 2.0))
            hazard = clamp(hazard + rng.uniform(-1.5, 1.5))
            confidence = clamp(confidence + rng.uniform(-0.02, 0.02), 0.05, 0.99)
            base["updated_s"] = int(time.time() % 30) + 2

        score = citci(occupancy, speed_drop, spillback, hazard)
        points = {
            "occupancy": round(WEIGHTS["occupancy"] * occupancy, 1),
            "speed_drop": round(WEIGHTS["speed_drop"] * speed_drop, 1),
            "spillback": round(WEIGHTS["spillback"] * spillback, 1),
            "hazard": round(WEIGHTS["hazard"] * hazard, 1),
        }
        prev = PREV_SCORES.get(spec.id)
        base.update(
            occupancy=round(occupancy),
            speed_drop=round(speed_drop),
            spillback=round(spillback),
            hazard=round(hazard),
            confidence=round(confidence, 2),
            score=round(score),
            band=band_for(score),
            points=points,
            delta_15=None if prev is None else round(score - prev),
        )
        readings[spec.id] = base
    return readings


def corridor_summary(readings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    scored = [reading for reading in readings.values() if reading["score"] is not None]
    scores = [float(reading["score"]) for reading in scored]
    previous = [PREV_SCORES[reading["id"]] for reading in scored if PREV_SCORES.get(reading["id"]) is not None]
    mean_score = round(sum(scores) / len(scores)) if scores else 0
    previous_mean = sum(float(value) for value in previous if value is not None) / len(previous) if previous else 0
    cameras_total = sum(junction.cameras_total for junction in JUNCTIONS)
    cameras_online = sum(junction.cameras_online for junction in JUNCTIONS)
    valid = sum(1 for reading in readings.values() if reading["status"] == "valid")
    low = sum(1 for reading in readings.values() if reading["status"] == "low")
    abstain = sum(1 for reading in readings.values() if reading["status"] == "abstain")
    return {
        "score": mean_score,
        "band": band_for(mean_score),
        "delta": round(mean_score - previous_mean),
        "reporting": len(scored),
        "valid": valid,
        "low": low,
        "abstain": abstain,
        "coverage": round(100 * cameras_online / cameras_total),
        "cameras_online": cameras_online,
        "cameras_total": cameras_total,
    }


def options_for_junction(reading: dict[str, Any]) -> list[dict[str, Any]]:
    key = "abstain" if reading["status"] == "abstain" else reading["cause"]
    return [dict(option) for option in OPTION_LIBRARY.get(key, OPTION_LIBRARY["unknown"])]


def incidents_open() -> list[dict[str, Any]]:
    return [incident for incident in st.session_state.incidents if incident["status"] == "open"]


def open_alert_count() -> int:
    elevated = sum(1 for state in st.session_state.flood_levels.values() if state["level"] >= 2)
    return len(incidents_open()) + elevated


def flood_zones() -> list[dict[str, Any]]:
    zones = []
    for base in SEED_FLOOD_ZONES:
        state = st.session_state.flood_levels.get(base["id"], {})
        zones.append({**base, **state})
    return zones


def flood_level_map() -> dict[str, int]:
    return {zone_id: int(state["level"]) for zone_id, state in st.session_state.flood_levels.items()}


def corridor_passability() -> dict[str, Any]:
    zones = flood_zones()
    level = max(zone["level"] for zone in zones)
    return {"level": level, "info": FLOOD_LEVELS[level], "elevated": sum(1 for z in zones if z["level"] >= 2)}


def zone_for_pair(first: str, second: str) -> str:
    indexes = sorted((_JUNCTION_INDEX[first], _JUNCTION_INDEX[second]))
    return SEGMENT_ZONE[(JUNCTIONS[indexes[0]].id, JUNCTIONS[indexes[1]].id)]


def _plan_action(score: float | None, flood_level: int) -> str:
    if score is None:
        action = "No camera reading · monitor bus probes"
    elif score >= 56:
        action = "Manual hold ≤20 s next cycle · marshal merge"
    elif score >= 36:
        action = "Pre-alert 500 m out · keep phase plan"
    else:
        action = "No intervention · pass through"
    if flood_level >= 2:
        action += " · avoid nearside lane"
    return action


def route_advice(
    origin_id: str,
    destination_id: str,
    readings: dict[str, dict[str, Any]],
    floods: dict[str, int],
) -> dict[str, Any]:
    start = _JUNCTION_INDEX[origin_id]
    end = _JUNCTION_INDEX[destination_id]
    if start == end:
        return {"blocked": False, "same_point": True, "plan": [], "eta_low": 0.0, "eta_high": 0.0}

    forward = end > start
    step = 1 if forward else -1
    total_distance = 0.0
    total_minutes = 0.0
    plan: list[dict[str, Any]] = [
        {
            "junction": JUNCTIONS[start].name,
            "eta_min": 0.0,
            "citci": readings[JUNCTIONS[start].id]["score"],
            "flood": "—",
            "action": "Start",
        }
    ]
    covered = 0
    endpoint_count = 0

    for index in range(start, end, step):
        first = JUNCTIONS[index]
        second = JUNCTIONS[index + step]
        zone_id = zone_for_pair(first.id, second.id)
        level = int(floods.get(zone_id, 0))
        if level >= 3:
            zone_label = next(zone["label"] for zone in SEED_FLOOD_ZONES if zone["id"] == zone_id)
            return {
                "blocked": True,
                "zone": zone_label,
                "level": level,
                "plan": plan,
                "eta_low": 0.0,
                "eta_high": 0.0,
            }
        distance = abs(second.km - first.km)
        first_score = readings[first.id]["score"]
        second_score = readings[second.id]["score"]
        available = [float(value) for value in (first_score, second_score) if value is not None]
        endpoint_count += 1
        if available:
            covered += 1
        effective = sum(available) / len(available) if available else 45.0
        speed = max(8.0, 30.0 * (1 - 0.55 * effective / 100))
        segment_minutes = distance / speed * 60
        penalty = {0: 0.0, 1: 1.5, 2: 4.0, 3: 0.0}[level]
        total_minutes += segment_minutes + penalty
        total_distance += distance
        plan.append(
            {
                "junction": second.name,
                "eta_min": round(total_minutes, 1),
                "citci": second_score,
                "flood": f"L{level}",
                "action": _plan_action(second_score, level),
            }
        )

    freeflow = total_distance / 30.0 * 60
    return {
        "blocked": False,
        "same_point": False,
        "plan": plan,
        "eta_low": round(total_minutes, 1),
        "eta_high": round(total_minutes + 2.4, 1),
        "distance": round(total_distance, 1),
        "freeflow": round(freeflow, 1),
        "coverage": covered,
        "endpoints": endpoint_count,
    }


def _next_id() -> str:
    sequence = int(st.session_state.get("decision_seq", 1))
    st.session_state.decision_seq = sequence + 1
    return f"DEC-{sequence:03d}"


def add_audit(record: dict[str, Any]) -> dict[str, Any]:
    ss = st.session_state
    ss.actions = int(ss.get("actions", 0)) + 1
    entry = {
        "id": record.get("id") or _next_id(),
        "ts": scenario_now(),
        "kind": record.get("kind", "option"),
        "junction": record.get("junction", "GS Road"),
        "title": record.get("title", "Decision logged"),
        "expected": record.get("expected", "—"),
        "status": record.get("status", "logged"),
        "operator": APP["operator"],
        "mode": record.get("mode", "Advisory only"),
        "expected_min": record.get("expected_min"),
        "observed_min": None,
        "observed": None,
        "checked_at": None,
        "detail": record.get("detail", ""),
    }
    ss.audit.insert(0, entry)
    return entry


def approve_option(junction_id: str) -> None:
    readings = current_readings(live=live_mode())
    reading = readings[junction_id]
    options = options_for_junction(reading)
    selected_id = st.session_state.get(f"opt-{junction_id}")
    option = next((item for item in options if item["id"] == selected_id), options[0])
    rationale = str(st.session_state.get(f"why-{junction_id}", "")).strip()
    entry = add_audit(
        {
            "kind": "option",
            "junction": reading["name"],
            "title": option["title"],
            "expected": option["saved"],
            "expected_min": option["expected_min"],
            "status": "pending_check" if option["expected_min"] else "logged",
            "detail": rationale or option["detail"],
        }
    )
    st.session_state[f"approved-{junction_id}"] = entry["id"]
    st.session_state[f"why-{junction_id}"] = ""
    st.toast(f"Advisory logged · {entry['id']}", icon=":material/check_circle:")


def resolve_incident(incident_id: str, action: str) -> None:
    ss = st.session_state
    incident = next((item for item in ss.incidents if item["id"] == incident_id), None)
    if incident is None or incident["status"] != "open":
        return
    incident["status"] = action
    verb = {"confirmed": "Confirmed", "rejected": "Rejected", "escalated": "Escalated"}.get(action, action.title())
    title = f"{verb} {incident['title'].lower()} · {incident['id']}"
    detail = f"{incident['clip']} · operator {verb.lower()} after review."
    if incident["kind"] == "waterlogging" and action == "confirmed" and incident.get("flood_zone"):
        zone = incident["flood_zone"]
        level = int(incident["flood_level"] or 2)
        zone_label = next(base["label"] for base in SEED_FLOOD_ZONES if base["id"] == zone)
        title += f" · L{level} set for {zone_label}"
        detail += f" Passability raised to L{level}."
    entry = add_audit(
        {
            "kind": "incident",
            "junction": incident["junction"],
            "title": title,
            "expected": "—",
            "status": "logged",
            "detail": detail,
        }
    )
    incident["resolved_at"] = entry["ts"]
    if incident["kind"] == "waterlogging" and action == "confirmed" and incident.get("flood_zone"):
        ss.flood_levels[incident["flood_zone"]] = {
            "level": int(incident["flood_level"] or 2),
            "updated": entry["ts"],
            "evidence": f"Operator-confirmed L{int(incident['flood_level'] or 2)} · {incident['id']}",
        }
    st.toast(f"{verb} · {incident['id']}", icon=":material/notifications_active:")


def set_flood(stretch_id: str, level: int, note_key: str) -> None:
    ss = st.session_state
    zone = next((base for base in SEED_FLOOD_ZONES if base["id"] == stretch_id), None)
    if zone is None:
        return
    note = str(ss.get(note_key, "")).strip() or FLOOD_LEVELS[int(level)]["condition"]
    entry = add_audit(
        {
            "kind": "flood",
            "junction": zone["label"],
            "title": f"L{int(level)} set · {zone['label']}",
            "expected": "—",
            "status": "logged",
            "detail": note,
        }
    )
    ss.flood_levels[stretch_id] = {"level": int(level), "updated": entry["ts"], "evidence": note}
    st.toast(f"Passability set to L{int(level)}", icon=":material/water_drop:")


def issue_emergency_advisory(unit_key: str, origin_id: str) -> None:
    readings = current_readings(live=live_mode())
    route = route_advice(origin_id, "gmch", readings, flood_level_map())
    if route.get("blocked"):
        return
    origin = readings[origin_id]["name"]
    entry = add_audit(
        {
            "kind": "emergency",
            "junction": f"{origin} → GMCH",
            "title": f"108 advisory · {unit_key} → GMCH",
            "expected": f"ETA {route['eta_low']:.0f}–{route['eta_high']:.0f} min",
            "status": "advisory_open",
            "detail": "Congestion- and flood-aware route shared for manual dispatch.",
        }
    )
    st.session_state.last_advisory_id = entry["id"]
    st.toast(f"108 advisory issued · {entry['id']}", icon=":material/local_hospital:")


def record_outcome(decision_id: str) -> None:
    ss = st.session_state
    record = next((item for item in ss.audit if item["id"] == decision_id), None)
    if record is None or record["status"] != "pending_check":
        return
    expected = float(record.get("expected_min") or 4.0)
    rng = random.Random(f"outcome:{decision_id}")
    observed = round(expected * rng.uniform(0.55, 1.15), 1)
    record["status"] = "checked"
    record["observed_min"] = observed
    record["observed"] = f"{observed:.1f} min (obs.)"
    entry = add_audit(
        {
            "kind": "outcome",
            "junction": record["junction"],
            "title": f"Check-back logged · {decision_id}",
            "expected": "—",
            "status": "recorded",
            "detail": record["observed"],
            "observed": record["observed"],
        }
    )
    record["checked_at"] = entry["ts"]
    st.toast(f"Check-back recorded · {decision_id}", icon=":material/query_stats:")


def audit_frame() -> pd.DataFrame:
    rows = [
        {
            "Time": entry["ts"],
            "ID": entry["id"],
            "Type": KIND_LABELS.get(entry["kind"], entry["kind"].title()),
            "Location": entry["junction"],
            "Decision": entry["title"],
            "Expected": entry["expected"],
            "Observed": entry.get("observed") or "—",
            "Status": STATUS_LABELS.get(entry["status"], entry["status"]),
        }
        for entry in st.session_state.audit
    ]
    return pd.DataFrame(rows)


def recent_audit_frame(limit: int = 3) -> pd.DataFrame:
    return audit_frame().head(limit)


def pending_decisions() -> list[dict[str, Any]]:
    return [
        entry
        for entry in st.session_state.audit
        if entry["kind"] == "option" and entry["status"] == "pending_check"
    ]


def open_advisories() -> list[dict[str, Any]]:
    return [
        entry
        for entry in st.session_state.audit
        if entry["kind"] == "emergency" and entry["status"] == "advisory_open"
    ]


def last_entry_for(junction_name: str) -> dict[str, Any] | None:
    for entry in st.session_state.audit:
        if entry["junction"] == junction_name and entry["kind"] in {"option", "incident", "flood"}:
            return entry
    return None


def outcome_frame() -> pd.DataFrame:
    rows = [
        {
            "Decision": f"{entry['id']} · {entry['junction']}",
            "Expected": round(float(entry["expected_min"]), 1),
            "Observed": round(float(entry["observed_min"]), 1),
        }
        for entry in reversed(st.session_state.audit)
        if entry["kind"] == "option"
        and entry.get("expected_min")
        and entry.get("observed_min") is not None
    ]
    return pd.DataFrame(rows)


def baseline_frame() -> pd.DataFrame:
    return pd.DataFrame({"Hour": BASELINE_HOURS, "CItCI": BASELINE_SCORES})


def checked_count() -> int:
    return sum(1 for entry in st.session_state.audit if entry["kind"] == "option" and entry["status"] == "checked")


def median_observed() -> float | None:
    values = [
        float(entry["observed_min"])
        for entry in st.session_state.audit
        if entry["kind"] == "option" and entry.get("observed_min") is not None
    ]
    return round(median(values), 1) if values else None
