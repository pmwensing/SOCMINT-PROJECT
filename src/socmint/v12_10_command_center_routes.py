from __future__ import annotations

from flask import Blueprint, jsonify, request

from .v12_10_command_center import (
    SOCMINTCommandCenterV121028,
    DossierBuilderV3,
    EvidenceIntegrityEngine,
    AutonomousRuntimeMesh,
    AnalystPropagationEngine,
    StrategicRiskEngine,
    ContinuousMonitoringEngine,
)

bp = Blueprint("v12_10_command_center", __name__)


@bp.post("/api/v12.10/command-center/cases/<case_id>/run-all")
def run_all(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify(SOCMINTCommandCenterV121028().run_all(case_id, payload))


@bp.post("/api/v12.10/dossier/run/<case_id>")
def dossier_run(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify(DossierBuilderV3().build(case_id, payload)), 202


@bp.post("/api/v12.10/evidence/integrity/<case_id>")
def evidence_integrity(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "case_id": case_id,
        **EvidenceIntegrityEngine().inspect(payload.get("artifacts", [])),
    })


@bp.post("/api/v12.10/runtime/mesh/<case_id>")
def runtime_mesh(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify({"case_id": case_id, **AutonomousRuntimeMesh().plan(payload)})


@bp.post("/api/v12.10/analyst/propagate/<case_id>")
def analyst_propagate(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "case_id": case_id,
        **AnalystPropagationEngine().apply(payload.get("graph", {}), payload.get("decisions", [])),
    })


@bp.post("/api/v12.10/risk/score/<case_id>")
def risk_score(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify({"case_id": case_id, **StrategicRiskEngine().score(payload)})


@bp.post("/api/v12.10/monitoring/evolve/<case_id>")
def monitoring_evolve(case_id: str):
    payload = request.get_json(silent=True) or {}
    return jsonify({"case_id": case_id, **ContinuousMonitoringEngine().evolve(payload)})
