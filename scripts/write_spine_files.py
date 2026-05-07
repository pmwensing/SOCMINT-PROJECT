# ruff: noqa: E501
from pathlib import Path

def write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")

write("src/socmint/seeds.py", """
import hashlib
import re
from dataclasses import dataclass

try:
    import phonenumbers
except Exception:
    phonenumbers = None


EMAIL_RE = re.compile(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{2,100}$")
URL_RE = re.compile(r"^https?://[^\\s]+$", re.I)


@dataclass(frozen=True)
class NormalizedSeed:
    seed_type: str
    raw_value: str
    normalized_value: str
    pii_hash: str


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_seed(raw_value: str, seed_type: str | None = None) -> NormalizedSeed:
    raw = (raw_value or "").strip()
    if not raw:
        raise ValueError("Seed value is required.")

    detected = seed_type or detect_seed_type(raw)

    if detected == "email":
        normalized = raw.lower()
        if not EMAIL_RE.match(normalized):
            raise ValueError("Invalid email seed.")
    elif detected == "username":
        normalized = raw.strip().lstrip("@")
        if not USERNAME_RE.match(normalized):
            raise ValueError("Invalid username seed.")
    elif detected == "phone":
        normalized = normalize_phone(raw)
    elif detected == "url":
        normalized = raw
        if not URL_RE.match(normalized):
            raise ValueError("Invalid URL seed.")
    else:
        raise ValueError(f"Unsupported seed type: {detected}")

    return NormalizedSeed(
        seed_type=detected,
        raw_value=raw,
        normalized_value=normalized,
        pii_hash=stable_hash(f"{detected}:{normalized}"),
    )


def detect_seed_type(raw_value: str) -> str:
    value = raw_value.strip()
    if EMAIL_RE.match(value.lower()):
        return "email"
    if URL_RE.match(value):
        return "url"
    if looks_like_phone(value):
        return "phone"
    return "username"


def looks_like_phone(value: str) -> bool:
    digits = re.sub(r"\\D", "", value)
    return 7 <= len(digits) <= 16


def normalize_phone(value: str) -> str:
    if phonenumbers is None:
        digits = re.sub(r"\\D", "", value)
        if not digits:
            raise ValueError("Invalid phone seed.")
        return "+" + digits if value.strip().startswith("+") else digits

    try:
        parsed = phonenumbers.parse(value, None)
    except Exception as exc:
        raise ValueError("Invalid phone seed.") from exc

    if not phonenumbers.is_possible_number(parsed):
        raise ValueError("Invalid phone seed.")

    return phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.E164,
    )
""")

write("src/socmint/artifacts.py", """
import hashlib
import json
import os
from pathlib import Path


DEFAULT_ARTIFACT_ROOT = "var/socmint/artifacts"


def artifact_root() -> Path:
    root = Path(os.environ.get("SOCMINT_ARTIFACT_DIR", DEFAULT_ARTIFACT_ROOT))
    root.mkdir(parents=True, exist_ok=True)
    return root


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_artifact(kind: str, payload: dict, prefix: str = "artifact") -> dict:
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    digest = sha256_bytes(data)
    directory = artifact_root() / kind
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{prefix}-{digest[:16]}.json"
    path.write_bytes(data)
    return {
        "kind": kind,
        "path": str(path),
        "sha256": digest,
        "mime_type": "application/json",
        "size_bytes": len(data),
    }
""")

write("src/socmint/scoring.py", """
def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_observation(
    base: float = 0.55,
    source_count: int = 1,
    archived: bool = False,
    exact_identifier_match: bool = False,
    contradiction_count: int = 0,
    analyst_validated: bool = False,
) -> float:
    score = base
    if source_count >= 2:
        score += 0.12
    if source_count >= 3:
        score += 0.08
    if archived:
        score += 0.08
    if exact_identifier_match:
        score += 0.08
    if analyst_validated:
        score += 0.12
    score -= min(0.25, contradiction_count * 0.08)
    return round(clamp(score), 3)


def confidence_band(score: float) -> str:
    if score >= 0.9:
        return "validated"
    if score >= 0.8:
        return "strong"
    if score >= 0.6:
        return "plausible"
    return "lead"
""")

write("src/socmint/spine.py", """
import json
from collections import defaultdict
from datetime import datetime, UTC

from . import database as db
from .artifacts import write_json_artifact
from .scoring import confidence_band, score_observation
from .seeds import normalize_seed


HIGH_VALUE_CONNECTORS = {
    "maigret": {"seed_types": ["username", "email"], "base": 0.56},
    "sherlock": {"seed_types": ["username", "email"], "base": 0.54},
    "socialscan": {"seed_types": ["username", "email"], "base": 0.62},
    "holehe": {"seed_types": ["email"], "base": 0.56},
    "h8mail": {"seed_types": ["email"], "base": 0.58},
    "phoneinfoga": {"seed_types": ["phone"], "base": 0.65},
    "archivebox": {"seed_types": ["url"], "base": 0.82},
}


def create_subject(label: str | None, seeds: list[dict]) -> int:
    subject_id = db.create_spine_subject(label=label)
    for seed in seeds:
        normalized = normalize_seed(seed.get("value", ""), seed.get("type") or None)
        db.add_spine_seed(
            subject_id=subject_id,
            seed_type=normalized.seed_type,
            raw_value=normalized.raw_value,
            normalized_value=normalized.normalized_value,
            pii_hash=normalized.pii_hash,
        )
    return subject_id


def run_spine_for_subject(subject_id: int, connectors: list[str] | None = None) -> dict:
    if not db.get_spine_subject(subject_id):
        raise ValueError("Subject not found.")

    selected = connectors or list(HIGH_VALUE_CONNECTORS)
    run_ids = []

    for seed in db.list_spine_seeds(subject_id):
        for key in selected:
            spec = HIGH_VALUE_CONNECTORS.get(key)
            if not spec or seed.seed_type not in spec["seed_types"]:
                continue
            run_ids.append(run_connector_for_seed(subject_id, seed, key, spec))

    correlate_subject(subject_id)
    return {"subject_id": subject_id, "run_ids": run_ids}


def run_connector_for_seed(subject_id: int, seed, connector_key: str, spec: dict) -> int:
    result = execute_connector(connector_key, seed)
    status = result.get("status", "completed")

    payload = {
        "connector": connector_key,
        "seed_type": seed.seed_type,
        "seed_hash": seed.pii_hash,
        "result": result,
        "created_at": datetime.now(UTC).isoformat(),
    }

    artifact = write_json_artifact(
        "connector-runs",
        payload,
        prefix=f"{connector_key}-{subject_id}",
    )

    run_id = db.create_spine_connector_run(
        subject_id=subject_id,
        connector_key=connector_key,
        seed_id=seed.id,
        status=status,
        raw_result=payload,
    )

    db.create_spine_raw_artifact(
        run_id=run_id,
        kind=artifact["kind"],
        path=artifact["path"],
        sha256=artifact["sha256"],
        mime_type=artifact["mime_type"],
        size_bytes=artifact["size_bytes"],
        meta=payload,
    )

    for observation in extract_observations(connector_key, seed, result, spec, artifact):
        db.create_spine_observation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type=observation["type"],
            normalized_value=observation["value"],
            confidence=str(observation["confidence"]),
            source_ref=f"run:{run_id}:{connector_key}",
            evidence_ref=f"sha256:{artifact['sha256']}",
            payload=observation,
        )

    return run_id


def execute_connector(connector_key: str, seed) -> dict:
    if connector_key == "archivebox":
        return {
            "connector": "archivebox",
            "status": "dry_run",
            "findings": [
                {
                    "type": "archive_candidate",
                    "value": seed.normalized_value,
                    "source": "archivebox",
                    "confidence": 0.82,
                }
            ],
        }

    try:
        from .connectors import run_connector

        return run_connector(
            connector_key,
            seed.normalized_value,
            seed.seed_type,
            allow_dry_run=True,
        )
    except Exception as exc:
        return {
            "connector": connector_key,
            "status": "dry_run",
            "stderr": str(exc),
            "findings": [],
        }


def extract_observations(connector_key, seed, raw_result, spec, artifact) -> list[dict]:
    observations = []
    findings = raw_result.get("findings", []) if isinstance(raw_result, dict) else []

    for finding in findings:
        value = str(finding.get("value") or finding.get("url") or "").strip()
        if not value:
            continue
        observations.append(
            {
                "type": finding.get("type", "connector_finding"),
                "value": value,
                "connector": connector_key,
                "seed_type": seed.seed_type,
                "seed_hash": seed.pii_hash,
                "confidence": float(finding.get("confidence", spec["base"])),
                "artifact_sha256": artifact["sha256"],
                "payload": finding,
            }
        )

    if not observations:
        observations.append(
            {
                "type": "seed_expansion_candidate",
                "value": seed.normalized_value,
                "connector": connector_key,
                "seed_type": seed.seed_type,
                "seed_hash": seed.pii_hash,
                "confidence": spec["base"],
                "artifact_sha256": artifact["sha256"],
                "payload": raw_result,
            }
        )

    return observations


def correlate_subject(subject_id: int) -> list[int]:
    grouped = defaultdict(list)
    for obs in db.list_spine_observations(subject_id):
        key = (obs.observation_type, (obs.normalized_value or "").lower().strip())
        grouped[key].append(obs)

    assertion_ids = []
    for (obs_type, value), group in grouped.items():
        if not value:
            continue

        source_count = len({item.source_ref for item in group})
        archived = any("archive" in item.observation_type for item in group)
        base = max(float(item.confidence or 0.5) for item in group)
        score = score_observation(
            base=base,
            source_count=source_count,
            archived=archived,
            exact_identifier_match=source_count >= 2,
        )

        payload = {
            "assertion_type": obs_type,
            "value": value,
            "confidence": score,
            "confidence_band": confidence_band(score),
            "source_count": source_count,
            "supporting_observation_ids": [item.id for item in group],
            "source_refs": [item.source_ref for item in group],
            "evidence_refs": [item.evidence_ref for item in group],
        }

        assertion_ids.append(
            db.upsert_spine_assertion(
                subject_id=subject_id,
                assertion_type=obs_type,
                normalized_value=value,
                confidence=str(score),
                validation_state="unreviewed",
                payload=payload,
            )
        )

    return assertion_ids


def build_dossier(subject_id: int) -> dict:
    subject = db.get_spine_subject(subject_id)
    if not subject:
        raise ValueError("Subject not found.")

    seeds = db.list_spine_seeds(subject_id)
    runs = db.list_spine_connector_runs(subject_id=subject_id)
    observations = db.list_spine_observations(subject_id)
    assertions = db.list_spine_assertions(subject_id)

    return {
        "subject": {
            "id": subject.id,
            "label": subject.label,
            "created_at": subject.created_at.isoformat()
            if subject.created_at
            else None,
        },
        "seeds": [
            {
                "id": seed.id,
                "type": seed.seed_type,
                "value": seed.normalized_value,
                "hash": seed.pii_hash,
            }
            for seed in seeds
        ],
        "summary": {
            "connector_runs": len(runs),
            "observations": len(observations),
            "assertions": len(assertions),
            "validated_assertions": len(
                [a for a in assertions if a.validation_state == "confirmed"]
            ),
        },
        "assertions": [
            {
                "id": item.id,
                "type": item.assertion_type,
                "value": item.normalized_value,
                "confidence": float(item.confidence or 0),
                "band": confidence_band(float(item.confidence or 0)),
                "validation_state": item.validation_state,
                "payload": json.loads(item.payload_json or "{}"),
            }
            for item in assertions
        ],
        "runs": [
            {
                "id": run.id,
                "connector": run.connector_key,
                "status": run.status,
                "created_at": run.created_at.isoformat()
                if run.created_at
                else None,
            }
            for run in runs
        ],
    }
""")

# Patch database.py by appending compact spine model/functions.
db_path = Path("src/socmint/database.py")
db_text = db_path.read_text()
if "class SpineSubject(Base):" not in db_text:
    db_text += """
class SpineSubject(Base):
    __tablename__ = "spine_subjects"
    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineSeed(Base):
    __tablename__ = "spine_seeds"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    seed_type = Column(String, nullable=False)
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=False)
    pii_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineConnectorRun(Base):
    __tablename__ = "spine_connector_runs"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    connector_key = Column(String, nullable=False)
    seed_id = Column(Integer, ForeignKey("spine_seeds.id"), nullable=True)
    status = Column(String, nullable=False)
    raw_result_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineRawArtifact(Base):
    __tablename__ = "spine_raw_artifacts"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
    kind = Column(String, nullable=False)
    path = Column(Text, nullable=False)
    sha256 = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    meta_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineObservation(Base):
    __tablename__ = "spine_observations"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
    observation_type = Column(String, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="0.5")
    source_ref = Column(Text, nullable=True)
    evidence_ref = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineDossierAssertion(Base):
    __tablename__ = "spine_dossier_assertions"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    assertion_type = Column(String, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="0.5")
    validation_state = Column(String, nullable=False, default="unreviewed")
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineValidationEvent(Base):
    __tablename__ = "spine_validation_events"
    id = Column(Integer, primary_key=True)
    assertion_id = Column(
        Integer,
        ForeignKey("spine_dossier_assertions.id"),
        nullable=False,
    )
    actor = Column(String, nullable=True)
    action = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


def _detach_all(session, items):
    for item in items:
        session.expunge(item)
    return items


def create_spine_subject(label=None):
    ensure_configured()
    session = Session()
    try:
        subject = SpineSubject(label=label)
        session.add(subject)
        session.commit()
        session.refresh(subject)
        return subject.id
    finally:
        session.close()


def get_spine_subject(subject_id):
    ensure_configured()
    session = Session()
    try:
        subject = session.query(SpineSubject).filter_by(id=subject_id).first()
        if subject:
            session.expunge(subject)
        return subject
    finally:
        session.close()


def list_spine_subjects(limit=100):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineSubject).order_by(
            SpineSubject.created_at.desc()
        ).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def add_spine_seed(subject_id, seed_type, raw_value, normalized_value, pii_hash):
    ensure_configured()
    session = Session()
    try:
        existing = session.query(SpineSeed).filter_by(
            subject_id=subject_id,
            seed_type=seed_type,
            pii_hash=pii_hash,
        ).first()
        if existing:
            return existing.id
        seed = SpineSeed(
            subject_id=subject_id,
            seed_type=seed_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            pii_hash=pii_hash,
        )
        session.add(seed)
        session.commit()
        session.refresh(seed)
        return seed.id
    finally:
        session.close()


def list_spine_seeds(subject_id):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineSeed).filter_by(
            subject_id=subject_id
        ).order_by(SpineSeed.id.asc()).all()
        return _detach_all(session, items)
    finally:
        session.close()


def create_spine_connector_run(
    subject_id,
    connector_key,
    seed_id,
    status,
    raw_result,
):
    ensure_configured()
    session = Session()
    try:
        run = SpineConnectorRun(
            subject_id=subject_id,
            connector_key=connector_key,
            seed_id=seed_id,
            status=status,
            raw_result_json=json.dumps(raw_result),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id
    finally:
        session.close()


def list_spine_connector_runs(subject_id=None, limit=100):
    ensure_configured()
    session = Session()
    try:
        query = session.query(SpineConnectorRun)
        if subject_id is not None:
            query = query.filter_by(subject_id=subject_id)
        items = query.order_by(
            SpineConnectorRun.created_at.desc()
        ).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def create_spine_raw_artifact(
    run_id,
    kind,
    path,
    sha256,
    mime_type=None,
    size_bytes=None,
    meta=None,
):
    ensure_configured()
    session = Session()
    try:
        artifact = SpineRawArtifact(
            run_id=run_id,
            kind=kind,
            path=path,
            sha256=sha256,
            mime_type=mime_type,
            size_bytes=size_bytes,
            meta_json=json.dumps(meta or {}),
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return artifact.id
    finally:
        session.close()


def create_spine_observation(
    subject_id,
    run_id,
    observation_type,
    normalized_value,
    confidence,
    source_ref,
    evidence_ref,
    payload,
):
    ensure_configured()
    session = Session()
    try:
        item = SpineObservation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type=observation_type,
            normalized_value=normalized_value,
            confidence=confidence,
            source_ref=source_ref,
            evidence_ref=evidence_ref,
            payload_json=json.dumps(payload),
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item.id
    finally:
        session.close()


def list_spine_observations(subject_id, limit=1000):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineObservation).filter_by(
            subject_id=subject_id
        ).order_by(SpineObservation.created_at.desc()).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def upsert_spine_assertion(
    subject_id,
    assertion_type,
    normalized_value,
    confidence,
    validation_state,
    payload,
):
    ensure_configured()
    session = Session()
    try:
        item = session.query(SpineDossierAssertion).filter_by(
            subject_id=subject_id,
            assertion_type=assertion_type,
            normalized_value=normalized_value,
        ).first()
        if not item:
            item = SpineDossierAssertion(
                subject_id=subject_id,
                assertion_type=assertion_type,
                normalized_value=normalized_value,
                confidence=confidence,
                validation_state=validation_state,
                payload_json=json.dumps(payload),
            )
            session.add(item)
        else:
            item.confidence = confidence
            item.payload_json = json.dumps(payload)
            item.updated_at = utc_now()
        session.commit()
        session.refresh(item)
        return item.id
    finally:
        session.close()


def list_spine_assertions(subject_id, limit=1000):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineDossierAssertion).filter_by(
            subject_id=subject_id
        ).order_by(SpineDossierAssertion.confidence.desc()).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def validate_spine_assertion(assertion_id, actor, action, note=None):
    ensure_configured()
    session = Session()
    try:
        item = session.query(SpineDossierAssertion).filter_by(
            id=assertion_id
        ).first()
        if not item:
            return None
        if action not in {"confirmed", "rejected", "suppressed", "unreviewed"}:
            raise ValueError("Invalid validation action.")
        item.validation_state = action
        item.updated_at = utc_now()
        session.add(
            SpineValidationEvent(
                assertion_id=assertion_id,
                actor=actor,
                action=action,
                note=note,
            )
        )
        session.commit()
        return item.id
    finally:
        session.close()
"""
db_path.write_text(db_text)

# Patch dashboard imports/routes.
dash_path = Path("src/socmint/dashboard.py")
dash = dash_path.read_text()

if "from .spine import build_dossier" not in dash:
    dash = dash.replace(
        "from .config import configure_logging, load_settings\n",
        "from .config import configure_logging, load_settings\n"
        "from .spine import build_dossier\n"
        "from .spine import create_subject as spine_create_subject\n"
        "from .spine import run_spine_for_subject\n",
    )

routes = """
@dashboard_bp.route("/spine", methods=["GET", "POST"])
@run_required
def spine_subjects():
    if request.method == "POST":
        label = request.form.get("label", "").strip() or None
        seeds = []
        for idx in range(1, 5):
            value = request.form.get(f"seed_{idx}", "").strip()
            seed_type = request.form.get(f"seed_type_{idx}", "").strip()
            if value:
                seeds.append({"type": seed_type or None, "value": value})
        if not seeds:
            flash("At least one seed is required.", "error")
            return redirect(url_for("dashboard.spine_subjects"))
        try:
            subject_id = spine_create_subject(label, seeds)
            audit("spine_subject_create", details={"subject_id": subject_id})
            flash(f"Created dossier subject {subject_id}.", "success")
            return redirect(url_for("dashboard.spine_dossier", subject_id=subject_id))
        except Exception as exc:
            flash(str(exc), "error")

    subjects = db.list_spine_subjects(limit=100)
    return render_template("spine.html", subjects=subjects)


@dashboard_bp.route("/spine/<int:subject_id>")
@login_required
def spine_dossier(subject_id):
    dossier = build_dossier(subject_id)
    return render_template("spine_dossier.html", dossier=dossier)


@dashboard_bp.route("/spine/<int:subject_id>/run", methods=["POST"])
@run_required
def spine_run(subject_id):
    connectors = request.form.getlist("connectors")
    try:
        result = run_spine_for_subject(subject_id, connectors or None)
        audit("spine_run", details=result)
        flash(f"Ran {len(result['run_ids'])} spine connector runs.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.spine_dossier", subject_id=subject_id))


@dashboard_bp.route(
    "/spine/assertions/<int:assertion_id>/validate",
    methods=["POST"],
)
@run_required
def spine_validate_assertion(assertion_id):
    action = request.form.get("action", "unreviewed").strip()
    note = request.form.get("note", "").strip() or None
    try:
        db.validate_spine_assertion(assertion_id, session.get("user"), action, note)
        flash(f"Assertion marked {action}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("dashboard.spine_subjects"))


@dashboard_bp.route("/api/v1/spine/subjects", methods=["POST"])
@run_required
def api_spine_create_subject():
    payload = request.get_json(silent=True) or {}
    subject_id = spine_create_subject(payload.get("label"), payload.get("seeds", []))
    return jsonify({"subject_id": subject_id}), 201


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/run", methods=["POST"])
@run_required
def api_spine_run(subject_id):
    payload = request.get_json(silent=True) or {}
    result = run_spine_for_subject(subject_id, payload.get("connectors") or None)
    return jsonify(result), 202


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/dossier")
@login_required
def api_spine_dossier(subject_id):
    return jsonify(build_dossier(subject_id))


"""

if "def spine_subjects()" not in dash:
    dash = dash.replace(
        '@dashboard_bp.route("/about")\n@login_required\ndef about():',
        routes + '@dashboard_bp.route("/about")\n@login_required\ndef about():',
    )

dash_path.write_text(dash)

write("src/socmint/templates/spine.html", """
{% extends "base.html" %}
{% block content %}
<h1>Validated Dossier Spine</h1>

<section class="card">
  <h2>Create subject from sparse seeds</h2>
  <form method="post" action="{{ url_for('dashboard.spine_subjects') }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label>Subject label</label>
    <input name="label" placeholder="Optional label">

    {% for idx in range(1, 5) %}
    <div class="seed-row">
      <select name="seed_type_{{ idx }}">
        <option value="">Auto-detect</option>
        <option value="username">Username</option>
        <option value="email">Email</option>
        <option value="phone">Phone</option>
        <option value="url">URL</option>
      </select>
      <input name="seed_{{ idx }}" placeholder="username / email / phone / URL">
    </div>
    {% endfor %}

    <button type="submit">Create dossier subject</button>
  </form>
</section>

<section class="card">
  <h2>Recent subjects</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Label</th><th>Created</th><th>Dossier</th></tr>
    </thead>
    <tbody>
      {% for subject in subjects %}
      <tr>
        <td>{{ subject.id }}</td>
        <td>{{ subject.label or "Untitled subject" }}</td>
        <td>{{ subject.created_at }}</td>
        <td>
          <a href="{{ url_for('dashboard.spine_dossier',
          subject_id=subject.id) }}">Open</a>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="4">No dossier subjects yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
""")

write("src/socmint/templates/spine_dossier.html", """
{% extends "base.html" %}
{% block content %}
<h1>Enrichment-Validated Profile Dossier</h1>

<section class="card">
  <h2>Subject</h2>
  <p><strong>ID:</strong> {{ dossier.subject.id }}</p>
  <p><strong>Label:</strong> {{ dossier.subject.label or "Untitled subject" }}</p>
  <p><strong>Created:</strong> {{ dossier.subject.created_at }}</p>
</section>

<section class="card">
  <h2>Run high-value spine</h2>
  <form
    method="post"
    action="{{ url_for('dashboard.spine_run', subject_id=dossier.subject.id) }}"
  >
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label><input type="checkbox" name="connectors" value="maigret" checked> Maigret</label>
    <label><input type="checkbox" name="connectors" value="sherlock" checked> Sherlock</label>
    <label><input type="checkbox" name="connectors" value="socialscan" checked> SocialScan</label>
    <label><input type="checkbox" name="connectors" value="holehe"> Holehe</label>
    <label><input type="checkbox" name="connectors" value="h8mail"> h8mail</label>
    <label><input type="checkbox" name="connectors" value="phoneinfoga" checked> PhoneInfoga</label>
    <label><input type="checkbox" name="connectors" value="archivebox" checked> ArchiveBox</label>
    <button type="submit">Run spine</button>
  </form>
</section>

<section class="card">
  <h2>Seeds</h2>
  <table>
    <thead><tr><th>Type</th><th>Normalized value</th><th>Hash</th></tr></thead>
    <tbody>
      {% for seed in dossier.seeds %}
      <tr>
        <td>{{ seed.type }}</td>
        <td class="mono">{{ seed.value }}</td>
        <td class="mono">{{ seed.hash[:16] }}...</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>

<section class="card">
  <h2>Dossier metrics</h2>
  <ul>
    <li>Connector runs: {{ dossier.summary.connector_runs }}</li>
    <li>Observations: {{ dossier.summary.observations }}</li>
    <li>Assertions: {{ dossier.summary.assertions }}</li>
    <li>Validated assertions: {{ dossier.summary.validated_assertions }}</li>
  </ul>
</section>

<section class="card">
  <h2>Evidence-backed assertions</h2>
  <table>
    <thead>
      <tr>
        <th>Confidence</th><th>Band</th><th>Type</th>
        <th>Value</th><th>Validation</th><th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for assertion in dossier.assertions %}
      <tr>
        <td>{{ "%.3f"|format(assertion.confidence) }}</td>
        <td>{{ assertion.band }}</td>
        <td>{{ assertion.type }}</td>
        <td class="mono">{{ assertion.value }}</td>
        <td>{{ assertion.validation_state }}</td>
        <td>
          <form
            method="post"
            action="{{ url_for('dashboard.spine_validate_assertion',
            assertion_id=assertion.id) }}"
          >
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <select name="action">
              <option value="confirmed">Confirm</option>
              <option value="rejected">Reject</option>
              <option value="suppressed">Suppress</option>
              <option value="unreviewed">Unreview</option>
            </select>
            <button type="submit">Apply</button>
          </form>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="6">No assertions yet. Run the high-value spine.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
""")

write("docs/SOCMINT_DOSSIER_SPINE_SPEC.md", """
# SOCMINT-PROJECT Dossier Spine

## Core rule

Connectors do not write truth.

Connectors write raw evidence and observations. The spine correlates
observations into dossier assertions with confidence scores, provenance,
evidence hashes, and validation state.

## Pipeline

Seed -> ConnectorRun -> RawArtifact -> Observation -> Correlation
-> DossierAssertion -> Analyst Validation -> Dossier

## High-value connector standard

A connector belongs in the production spine only if it improves at least one:

1. seed expansion
2. cross-source corroboration
3. evidence preservation
4. entity resolution
5. media/profile enrichment
6. contradiction detection
7. validated dossier quality
""")

write("scripts/socmint_spine_smoke.py", """
import json
import os
import tempfile

os.environ.setdefault("SOCMINT_SECRET_KEY", "dev-secret-key-for-socmint-spine-32chars-plus")
os.environ.setdefault("SOCMINT_ADMIN_USER", "admin")
os.environ.setdefault("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
os.environ.setdefault("SOCMINT_AUTO_CREATE_DB", "1")

from socmint.dashboard import create_app


def main():
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(database_url=f"sqlite:///{tmp}/socmint.db")
        app.config.update(TESTING=True)
        client = app.test_client()

        client.post(
            "/login",
            data={\n                "username": "admin",\n                "password": "StrongPass123!",\n                "csrf_token": csrf,\n            },
        )

        created = client.post(
            "/api/v1/spine/subjects",
            json={
                "label": "Smoke Subject",
                "seeds": [{"type": "username", "value": "exampleuser"}],
            },
        )
        assert created.status_code == 201, created.data
        subject_id = created.get_json()["subject_id"]

        run = client.post(
            f"/api/v1/spine/subjects/{subject_id}/run",
            json={"connectors": ["sherlock", "maigret"]},\n            headers={"X-CSRF-Token": csrf},
        )
        assert run.status_code == 202, run.data

        dossier = client.get(f"/api/v1/spine/subjects/{subject_id}/dossier")
        assert dossier.status_code == 200, dossier.data
        body = dossier.get_json()
        assert body["summary"]["connector_runs"] >= 1

        print(json.dumps(body["summary"], indent=2))


if __name__ == "__main__":
    main()
""")

write("tests/test_spine_v6.py", """
import pytest

from src.socmint import database as db
from src.socmint.seeds import normalize_seed
from src.socmint.spine import build_dossier, create_subject, run_spine_for_subject


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def test_normalize_seed_email():
    seed = normalize_seed(" Alice.Example+tag@Example.com ")
    assert seed.seed_type == "email"
    assert seed.normalized_value == "alice.example+tag@example.com"
    assert len(seed.pii_hash) == 64


def test_spine_creates_dossier_from_username(configured_db, monkeypatch):
    def fake_execute_connector(connector_key, seed):
        return {
            "connector": connector_key,
            "status": "dry_run",
            "findings": [
                {
                    "type": "account_presence",
                    "value": f"https://example.com/{seed.normalized_value}",
                    "source": connector_key,
                    "confidence": 0.61,
                }
            ],
        }

    monkeypatch.setattr("src.socmint.spine.execute_connector", fake_execute_connector)

    subject_id = create_subject(
        "Test Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    result = run_spine_for_subject(subject_id, ["sherlock", "maigret"])
    dossier = build_dossier(subject_id)

    assert result["run_ids"]
    assert dossier["summary"]["connector_runs"] == 2
    assert dossier["summary"]["assertions"] >= 1


def test_spine_dashboard_api(tmp_path, monkeypatch):
    from src.socmint.dashboard import create_app

    monkeypatch.setenv("SOCMINT_SECRET_KEY", "test-secret-key-for-socmint-spine-32chars-plus")
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    app = create_app(database_url=f"sqlite:///{tmp_path / 'web.db'}")
    app.config.update(TESTING=True)
    client = app.test_client()

    client.post(
        "/login",
        data={\n                "username": "admin",\n                "password": "StrongPass123!",\n                "csrf_token": csrf,\n            },
    )

    response = client.post(
        "/api/v1/spine/subjects",
        json={
            "label": "Web Subject",
            "seeds": [{"type": "username", "value": "exampleuser"}],
        },
    )
    assert response.status_code == 201
    subject_id = response.get_json()["subject_id"]

    run = client.post(
        f"/api/v1/spine/subjects/{subject_id}/run",
        json={"connectors": ["sherlock"]},\n        headers={"X-CSRF-Token": csrf},
    )
    assert run.status_code == 202

    dossier = client.get(f"/api/v1/spine/subjects/{subject_id}/dossier")
    assert dossier.status_code == 200
    assert dossier.get_json()["subject"]["id"] == subject_id
""")

# Add nav link safely.
base = Path("src/socmint/templates/base.html")
if base.exists():
    text = base.read_text()
    if "dashboard.spine_subjects" not in text:
        link = """<a href="{{ url_for('dashboard.spine_subjects') }}">Dossier Spine</a>\n"""
        if "</nav>" in text:
            text = text.replace("</nav>", link + "</nav>")
        else:
            text = text.replace("<body>", "<body>\\n<nav>" + link + "</nav>")
        base.write_text(text)

# Add CSS only if a known stylesheet exists.
for css_path in [
    Path("src/socmint/static/style.css"),
    Path("src/socmint/static/styles.css"),
    Path("src/socmint/static/app.css"),
]:
    if css_path.exists():
        css = css_path.read_text()
        if ".seed-row" not in css:
            css += """

.seed-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.seed-row input {
  flex: 1;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}
"""
            css_path.write_text(css)
        break
