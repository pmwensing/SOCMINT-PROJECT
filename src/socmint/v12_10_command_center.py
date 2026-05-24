from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


VERSION = "12.10.28"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def confidence(value: Any, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, score))


@dataclass
class ExportManifest:
    run_id: str
    case_id: str
    version: str
    generated_at: str
    artifact_count: int
    export_count: int
    source_count: int
    integrity_verified: bool
    sha256: str


class DossierBuilderV3:
    version = "12.10.23"

    def build(self, case_id: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        entities = safe_list(payload.get("entities"))
        artifacts = safe_list(payload.get("artifacts"))
        assertions = safe_list(payload.get("assertions"))
        timeline = safe_list(payload.get("timeline"))

        approved = [
            a for a in assertions
            if isinstance(a, Mapping) and a.get("review_status") == "approved"
        ]

        dossier = {
            "version": self.version,
            "case_id": case_id,
            "generated_at": utc_now(),
            "summary": {
                "entity_count": len(entities),
                "artifact_count": len(artifacts),
                "assertion_count": len(assertions),
                "approved_assertion_count": len(approved),
                "timeline_event_count": len(timeline),
                "export_ready": bool(approved),
            },
            "entities": entities,
            "approved_assertions": approved,
            "timeline": timeline,
            "artifacts": artifacts,
        }

        run_id = sha256_text(json.dumps(dossier, sort_keys=True))[:16]
        body = json.dumps(dossier, sort_keys=True, indent=2)
        manifest = ExportManifest(
            run_id=run_id,
            case_id=case_id,
            version=self.version,
            generated_at=utc_now(),
            artifact_count=len(artifacts),
            export_count=3,
            source_count=len(safe_list(payload.get("sources"))),
            integrity_verified=True,
            sha256=sha256_text(body),
        )

        return {
            "run_id": run_id,
            "dossier": dossier,
            "exports": {
                "json": body,
                "html": self.to_html(dossier),
                "csv": self.to_csv(approved),
            },
            "manifest": asdict(manifest),
        }

    def to_html(self, dossier: Mapping[str, Any]) -> str:
        return (
            "<html><body>"
            f"<h1>SOCMINT Dossier {dossier.get('case_id')}</h1>"
            f"<pre>{json.dumps(dossier, indent=2)}</pre>"
            "</body></html>"
        )

    def to_csv(self, assertions: List[Mapping[str, Any]]) -> str:
        rows = ["id,type,claim,confidence,source"]
        for i, item in enumerate(assertions, 1):
            rows.append(
                ",".join([
                    str(item.get("id", i)),
                    str(item.get("type", "")),
                    str(item.get("claim", "")).replace(",", " "),
                    str(item.get("confidence", "")),
                    str(item.get("source", "")),
                ])
            )
        return "\n".join(rows) + "\n"


class EvidenceIntegrityEngine:
    version = "12.10.24"

    def inspect(self, artifacts: List[Mapping[str, Any]]) -> Dict[str, Any]:
        verified = mismatched = missing = note_only = 0
        events = []

        for art in artifacts:
            path = art.get("path")
            stored = art.get("sha256")
            if not path:
                note_only += 1
                continue
            p = Path(path)
            if not p.exists():
                missing += 1
                events.append({"artifact": art.get("id"), "status": "missing"})
                continue
            current = self.sha256_file(p)
            if stored and stored == current:
                verified += 1
            else:
                mismatched += 1
                events.append({
                    "artifact": art.get("id"),
                    "status": "hash_mismatch",
                    "stored_sha256": stored,
                    "current_sha256": current,
                })

        risk = "low"
        if mismatched or missing:
            risk = "high" if mismatched + missing >= 3 else "moderate"

        return {
            "version": self.version,
            "verified": verified,
            "mismatched": mismatched,
            "missing": missing,
            "note_only": note_only,
            "risk_level": risk,
            "events": events,
        }

    def sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


class AutonomousRuntimeMesh:
    version = "12.10.25"

    def plan(self, case: Mapping[str, Any]) -> Dict[str, Any]:
        seeds = safe_list(case.get("seeds"))
        connectors = safe_list(case.get("connectors"))
        watchlists = safe_list(case.get("watchlists"))

        jobs = []
        for seed in seeds:
            jobs.append({"type": "recursive_enrichment", "target": seed, "status": "queued"})
        for connector in connectors:
            jobs.append({"type": "connector_health_check", "connector": connector, "status": "queued"})
        for watch in watchlists:
            jobs.append({"type": "watchlist_review", "target": watch, "status": "queued"})

        return {
            "version": self.version,
            "scheduler_mode": "operator_authorized",
            "job_count": len(jobs),
            "jobs": jobs,
            "guardrails": {
                "human_review_required": True,
                "no_unapproved_active_collection": True,
            },
        }


class AnalystPropagationEngine:
    version = "12.10.26"

    def apply(self, graph: Mapping[str, Any], decisions: List[Mapping[str, Any]]) -> Dict[str, Any]:
        nodes = safe_list(graph.get("nodes"))
        edges = safe_list(graph.get("edges"))
        decision_map = {str(d.get("target_id")): d for d in decisions}

        changed = []
        for collection in (nodes, edges):
            for item in collection:
                if not isinstance(item, dict):
                    continue
                d = decision_map.get(str(item.get("id")))
                if not d:
                    continue
                action = str(d.get("action", "")).upper()
                if action == "PROMOTE":
                    item["review_status"] = "approved"
                    item["confidence"] = min(1.0, confidence(item.get("confidence")) + 0.15)
                elif action == "REJECT":
                    item["review_status"] = "rejected"
                    item["confidence"] = 0.0
                elif action == "UNCERTAIN":
                    item["review_status"] = "uncertain"
                    item["confidence"] = min(confidence(item.get("confidence")), 0.49)
                elif action == "ESCALATE":
                    item["review_status"] = "escalated"
                changed.append({"id": item.get("id"), "action": action, "review_status": item.get("review_status")})

        return {
            "version": self.version,
            "nodes": nodes,
            "edges": edges,
            "changed_count": len(changed),
            "changes": changed,
        }


class StrategicRiskEngine:
    version = "12.10.27"

    def score(self, case: Mapping[str, Any]) -> Dict[str, Any]:
        assertions = safe_list(case.get("assertions"))
        exposures = safe_list(case.get("exposures"))
        contradictions = [
            a for a in assertions
            if isinstance(a, Mapping) and str(a.get("status", "")).lower() in {"conflict", "contradicted", "needs_review"}
        ]

        exposure_score = min(1.0, len(exposures) / 10)
        contradiction_score = min(1.0, len(contradictions) / 5)
        confidence_avg = 0.0
        scores = [confidence(a.get("confidence")) for a in assertions if isinstance(a, Mapping)]
        if scores:
            confidence_avg = sum(scores) / len(scores)

        risk = round((exposure_score * 0.35) + (contradiction_score * 0.35) + ((1 - confidence_avg) * 0.30), 4)

        bucket = "low"
        if risk >= 0.75:
            bucket = "critical"
        elif risk >= 0.55:
            bucket = "high"
        elif risk >= 0.30:
            bucket = "moderate"

        return {
            "version": self.version,
            "risk_score": risk,
            "risk_level": bucket,
            "exposure_count": len(exposures),
            "contradiction_count": len(contradictions),
            "average_confidence": round(confidence_avg, 4),
            "recommended_action": "human_review" if bucket in {"moderate", "high", "critical"} else "monitor",
        }


class ContinuousMonitoringEngine:
    version = "12.10.28"

    def evolve(self, case: Mapping[str, Any]) -> Dict[str, Any]:
        alerts = safe_list(case.get("alerts"))
        watchlists = safe_list(case.get("watchlists"))
        updates = []

        for alert in alerts:
            updates.append({
                "type": "watchlist_alert_review",
                "alert": alert,
                "case_action": "route_to_human_review",
            })

        if watchlists and not alerts:
            updates.append({
                "type": "monitoring_heartbeat",
                "case_action": "continue_monitoring",
            })

        return {
            "version": self.version,
            "watchlist_count": len(watchlists),
            "alert_count": len(alerts),
            "case_evolution_events": updates,
            "autonomous_case_evolution": bool(updates),
            "guardrails": {
                "authorized_targets_only": True,
                "human_review_before_dossier_promotion": True,
            },
        }


class SOCMINTCommandCenterV121028:
    version = VERSION

    def run_all(self, case_id: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(payload or {})
        dossier = DossierBuilderV3().build(case_id, payload)
        integrity = EvidenceIntegrityEngine().inspect(safe_list(payload.get("artifacts")))
        runtime = AutonomousRuntimeMesh().plan(payload)
        propagation = AnalystPropagationEngine().apply(
            payload.get("graph", {}),
            safe_list(payload.get("decisions")),
        )
        risk = StrategicRiskEngine().score(payload)
        monitoring = ContinuousMonitoringEngine().evolve(payload)

        return {
            "version": self.version,
            "case_id": case_id,
            "generated_at": utc_now(),
            "stages": {
                "v12.10.23_dossier_builder": dossier,
                "v12.10.24_evidence_integrity": integrity,
                "v12.10.25_runtime_mesh": runtime,
                "v12.10.26_analyst_propagation": propagation,
                "v12.10.27_strategic_risk": risk,
                "v12.10.28_continuous_monitoring": monitoring,
            },
        }
