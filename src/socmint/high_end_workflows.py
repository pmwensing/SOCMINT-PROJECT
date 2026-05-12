from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import database as db
from .evidence import assertion_review_queue, connector_quality_metrics
from .evidence_custody import record_custody_event
from .evidence_intake import evidence_root
from .jobs import scan_job_health
from .report_export_center import bundle_root
from .report_export_center import export_center_payload
from .spine import build_dossier
from .ultimate_dossier import ultimate_dossier_payload
from .connectors import CONNECTORS


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return default


def _safe_slug(value: str) -> str:
    parsed = urlparse(value)
    raw = parsed.netloc or parsed.path or value or "capture"
    safe = "".join(char if char.isalnum() else "-" for char in raw.lower())
    return safe.strip("-")[:80] or "capture"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_root() -> Path:
    root = evidence_root() / "captures"
    root.mkdir(parents=True, exist_ok=True)
    return root


def export_bundle_root() -> Path:
    root = bundle_root() / "high_end"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _minimal_png_bytes() -> bytes:
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "53de0000000c49444154789c63606060000000040001f61738550000000049"
        "454e44ae426082"
    )


def _minimal_pdf_bytes(title: str, url: str) -> bytes:
    body = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Contents 4 0 R >> endobj\n"
        "4 0 obj << /Length 96 >> stream\n"
        "BT /F1 12 Tf 72 720 Td "
        f"({title[:48]}) Tj 0 -18 Td ({url[:72]}) Tj ET\n"
        "endstream endobj\n"
        "xref\n0 5\n0000000000 65535 f \n"
        "trailer << /Root 1 0 R /Size 5 >>\n%%EOF\n"
    )
    return body.encode()


def _mhtml_bytes(
    url: str,
    html: str,
    headers: dict[str, Any] | None = None,
) -> bytes:
    boundary = "socmint-capture-boundary"
    header_lines = "\n".join(
        f"X-Source-{key}: {value}" for key, value in sorted((headers or {}).items())
    )
    payload = "\n".join(
        [
            "MIME-Version: 1.0",
            f"Content-Type: multipart/related; boundary=\"{boundary}\"",
            f"X-SOCMINT-Source-URL: {url}",
            header_lines,
            "",
            f"--{boundary}",
            "Content-Type: text/html; charset=utf-8",
            f"Content-Location: {url}",
            "",
            html or "",
            f"--{boundary}--",
            "",
        ]
    )
    return payload.encode()


def default_scope() -> dict[str, Any]:
    return {
        "schema": "socmint.responsible_use_scope.v8_0",
        "authorization_banner": (
            "Use only on targets you are authorized to investigate."
        ),
        "allowed_targets": [],
        "blocked_targets": [],
        "rate_limits": {
            "captures_per_hour": 60,
            "connector_runs_per_hour": 120,
            "exports_per_hour": 30,
        },
        "sensitive_redaction_default": True,
        "export_warning": "Review sensitive data and authorization before export.",
    }


def load_scope() -> dict[str, Any]:
    row = db.get_responsible_use_scope()
    if not row:
        row = db.save_responsible_use_scope(default_scope())
    payload = _json_loads(row.payload_json, {})
    return {**default_scope(), **payload, "updated_at": row.updated_at.isoformat()}


def save_scope(payload: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    merged = {**default_scope(), **(payload or {})}
    row = db.save_responsible_use_scope(merged, actor=actor)
    return {**merged, "updated_at": row.updated_at.isoformat()}


def scope_review(target: str) -> dict[str, Any]:
    scope = load_scope()
    text = str(target or "").lower()
    blocked = [str(item).lower() for item in scope.get("blocked_targets") or []]
    allowed = [str(item).lower() for item in scope.get("allowed_targets") or []]
    if any(item and item in text for item in blocked):
        state = "blocked"
        reason = "Target matches blocked scope."
    elif allowed and not any(item and item in text for item in allowed):
        state = "needs_authorization_review"
        reason = "Target does not match configured allowed scope."
    else:
        state = "authorized"
        reason = "Target is authorized or no allowlist is configured."
    return {
        "schema": "socmint.scope_review.v8_0",
        "target": target,
        "state": state,
        "reason": reason,
        "authorization_banner": scope.get("authorization_banner"),
        "redaction_default": bool(scope.get("sensitive_redaction_default", True)),
    }


def gate_action(action: str, target: str, actor: str | None = None) -> dict[str, Any]:
    review = scope_review(target)
    allowed = review["state"] != "blocked"
    event_id = db.record_policy_gate_event(
        action,
        allowed,
        [review["reason"]],
        {"target": target, "scope_state": review["state"]},
        actor=actor,
    )
    return {
        "schema": "socmint.responsible_use_gate.v8_0",
        "event_id": event_id,
        "allowed": allowed,
        "scope_review": review,
        "rate_limits": load_scope().get("rate_limits"),
    }


def create_case(
    title: str,
    case_key: str | None = None,
    tags: list[str] | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    key = case_key or _safe_slug(title)
    row = db.upsert_case_record(key, title, tags=tags or [], actor=actor)
    db.add_case_event(key, "case_create", actor=actor)
    return case_payload(row.case_key)


def update_case(
    case_key: str,
    actor: str | None = None,
    **changes: Any,
) -> dict[str, Any]:
    row = db.get_case_record(case_key)
    if not row:
        raise ValueError("Case not found.")
    payload = _json_loads(row.payload_json, {})
    payload.update(changes.get("payload") or {})
    db.upsert_case_record(
        case_key,
        changes.get("title") or row.title,
        tags=changes.get("tags") or _json_loads(row.tags_json, []),
        status=changes.get("status") or row.status,
        priority=changes.get("priority") or row.priority,
        review_state=changes.get("review_state") or row.review_state,
        due_at=changes.get("due_at", row.due_at),
        payload=payload,
        actor=actor,
    )
    db.add_case_event(case_key, "case_update", payload=changes, actor=actor)
    return case_payload(case_key)


def add_case_event(
    case_key: str,
    event_type: str,
    actor: str | None = None,
    **payload: Any,
) -> dict[str, Any]:
    db.add_case_event(
        case_key,
        event_type,
        subject_id=payload.get("subject_id"),
        note=payload.get("note") or payload.get("comment"),
        assignee=payload.get("assignee"),
        payload=payload,
        actor=actor,
    )
    return case_payload(case_key)


def case_payload(case_key: str) -> dict[str, Any]:
    row = db.get_case_record(case_key)
    if not row:
        raise ValueError("Case not found.")
    events = db.list_case_events(case_key, limit=500)
    captures = db.list_evidence_captures(case_key=case_key, limit=500)
    return {
        "schema": "socmint.case.v8_0",
        "case_key": row.case_key,
        "title": row.title,
        "status": row.status,
        "priority": row.priority,
        "review_state": row.review_state,
        "due_at": row.due_at,
        "tags": _json_loads(row.tags_json, []),
        "payload": _json_loads(row.payload_json, {}),
        "subjects": sorted(
            {
                event.subject_id
                for event in events
                if event.subject_id is not None
            }
        ),
        "events": [_case_event_dict(event) for event in events],
        "captures": [_capture_dict(item) for item in captures],
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def list_cases(limit: int = 100) -> list[dict[str, Any]]:
    return [case_payload(row.case_key) for row in db.list_case_records(limit=limit)]


def _case_event_dict(event) -> dict[str, Any]:
    return {
        "id": event.id,
        "case_id": event.case_id,
        "event_type": event.event_type,
        "subject_id": event.subject_id,
        "note": event.note,
        "assignee": event.assignee,
        "payload": _json_loads(event.payload_json, {}),
        "actor": event.actor,
        "created_at": event.created_at.isoformat(),
    }


def capture_snapshot(
    url: str,
    html: str,
    case_key: str | None = None,
    subject_id: int | None = None,
    actor: str | None = None,
    headers: dict[str, Any] | None = None,
    cookies: list[dict[str, Any]] | None = None,
    screenshot_bytes: bytes | None = None,
    pdf_bytes: bytes | None = None,
    archive_bytes: bytes | None = None,
    automation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = gate_action("capture", url, actor=actor)
    if not gate["allowed"]:
        raise PermissionError(gate["scope_review"]["reason"])

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    slug = _safe_slug(url)
    headers = headers or {}
    cookies = cookies or []
    automation = automation or capture_automation_plan(url)
    artifacts = [
        ("html", f"{stamp}_{slug}.html", (html or "").encode(), "text/html"),
    ]
    if screenshot_bytes:
        artifacts.append(
            ("screenshot", f"{stamp}_{slug}.png", screenshot_bytes, "image/png")
        )
    if pdf_bytes:
        artifacts.append(("pdf", f"{stamp}_{slug}.pdf", pdf_bytes, "application/pdf"))
    artifacts.append(
        (
            "mhtml",
            f"{stamp}_{slug}.mhtml",
            archive_bytes or _mhtml_bytes(url, html or "", headers),
            "multipart/related",
        )
    )

    stored = []
    for artifact_type, name, data, mime_type in artifacts:
        path = capture_root() / name
        path.write_bytes(data)
        digest = _sha256_bytes(data)
        capture_id = f"{stamp}-{digest[:16]}-{artifact_type}"
        item = db.create_evidence_capture(
            capture_id,
            url,
            artifact_type,
            str(path),
            digest,
            mime_type,
            len(data),
            case_key=case_key,
            subject_id=subject_id,
            headers=headers,
            cookies=cookies,
            payload={"automation": automation},
            actor=actor,
        )
        record_custody_event(
            evidence_id=capture_id,
            action="capture",
            actor=actor,
            sha256=digest,
            status="stored",
            details={"url": url, "case_key": case_key, "subject_id": subject_id},
        )
        if case_key:
            db.add_case_event(
                case_key,
                "capture_attach",
                subject_id=subject_id,
                payload={"capture_id": capture_id, "sha256": digest},
                actor=actor,
            )
        stored.append(_capture_dict(item))

    manifest_payload = {
        "schema": "socmint.capture_manifest.v8_0_1",
        "capture_group_id": stamp,
        "generated_at": utc_now(),
        "url": url,
        "case_key": case_key,
        "subject_id": subject_id,
        "actor": actor,
        "headers": headers,
        "cookies_metadata": cookies,
        "automation": automation,
        "artifacts": stored,
    }
    manifest_bytes = json.dumps(
        manifest_payload,
        indent=2,
        sort_keys=True,
    ).encode()
    manifest_digest = _sha256_bytes(manifest_bytes)
    manifest_path = capture_root() / f"{stamp}_{slug}-MANIFEST.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_id = f"{stamp}-{manifest_digest[:16]}-manifest"
    manifest_row = db.create_evidence_capture(
        manifest_id,
        url,
        "manifest",
        str(manifest_path),
        manifest_digest,
        "application/json",
        len(manifest_bytes),
        case_key=case_key,
        subject_id=subject_id,
        headers=headers,
        cookies=cookies,
        payload={"capture_group_id": stamp},
        actor=actor,
    )
    record_custody_event(
        evidence_id=manifest_id,
        action="capture",
        actor=actor,
        sha256=manifest_digest,
        status="stored",
        details={"url": url, "case_key": case_key, "subject_id": subject_id},
    )
    stored.append(_capture_dict(manifest_row))

    return {
        "schema": "socmint.evidence_capture.v8_0",
        "url": url,
        "case_key": case_key,
        "subject_id": subject_id,
        "captures": stored,
        "manifest_capture_id": manifest_id,
        "manifest_path": str(manifest_path),
        "gate": gate,
    }


def capture_browser_snapshot(
    url: str,
    html: str | None = None,
    case_key: str | None = None,
    subject_id: int | None = None,
    actor: str | None = None,
    use_playwright: bool = True,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    cookies: list[dict[str, Any]] = []
    screenshot = _minimal_png_bytes()
    pdf = _minimal_pdf_bytes("SOCMINT Browser Capture", url)
    source_html = html or (
        "<!doctype html><html><head><title>SOCMINT capture</title></head>"
        f"<body><h1>Captured URL</h1><p>{url}</p></body></html>"
    )
    automation = capture_automation_plan(url)
    automation["mode"] = "fallback"

    if use_playwright and not html:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page()
                response = page.goto(url, wait_until="networkidle", timeout=30000)
                source_html = page.content()
                screenshot = page.screenshot(full_page=True)
                pdf = page.pdf(format="Letter")
                cookies = page.context.cookies()
                if response:
                    headers = dict(response.headers)
                browser.close()
                automation["mode"] = "playwright"
        except Exception as exc:
            automation["mode"] = "fallback"
            automation["fallback_reason"] = str(exc)

    archive = _mhtml_bytes(url, source_html, headers)
    return capture_snapshot(
        url,
        source_html,
        case_key=case_key,
        subject_id=subject_id,
        actor=actor,
        headers=headers,
        cookies=cookies,
        screenshot_bytes=screenshot,
        pdf_bytes=pdf,
        archive_bytes=archive,
        automation=automation,
    )


def _capture_dict(item) -> dict[str, Any]:
    return {
        "capture_id": item.capture_id,
        "url": item.url,
        "case_key": item.case_key,
        "subject_id": item.subject_id,
        "artifact_type": item.artifact_type,
        "path": item.path,
        "sha256": item.sha256,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "headers": _json_loads(item.headers_json, {}),
        "cookies": _json_loads(item.cookies_json, []),
        "payload": _json_loads(item.payload_json, {}),
        "actor": item.actor,
        "created_at": item.created_at.isoformat(),
    }


def list_capture_artifacts(
    case_key: str | None = None,
    subject_id: int | None = None,
) -> list[dict[str, Any]]:
    return [
        _capture_dict(item)
        for item in db.list_evidence_captures(
            case_key=case_key,
            subject_id=subject_id,
            limit=500,
        )
    ]


def verify_capture(capture_id: str) -> dict[str, Any]:
    item = db.get_evidence_capture(capture_id)
    if not item:
        return {"capture_id": capture_id, "valid": False, "reason": "not_found"}
    path = Path(item.path)
    if not path.exists():
        return {"capture_id": capture_id, "valid": False, "reason": "missing_file"}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema": "socmint.capture_verification.v8_0",
        "capture_id": capture_id,
        "valid": digest == item.sha256,
        "expected_sha256": item.sha256,
        "actual_sha256": digest,
    }


def capture_automation_plan(url: str) -> dict[str, Any]:
    return {
        "schema": "socmint.capture_automation_plan.v8_0",
        "url": url,
        "engine": "playwright",
        "steps": [
            "open_page",
            "wait_network_idle",
            "capture_headers",
            "capture_cookies_metadata",
            "full_page_screenshot",
            "export_pdf",
            "export_mhtml_or_warc",
            "hash_artifacts",
            "record_chain_of_custody",
        ],
        "retry_policy": {"attempts": 3, "backoff": "linear"},
    }


def analyst_workbench_payload(limit: int = 100) -> dict[str, Any]:
    queue = assertion_review_queue(limit=limit)
    connectors = connector_quality_metrics()
    cases = list_cases(limit=limit)
    captures = list_capture_artifacts()[:limit]
    blockers = [
        item
        for item in queue
        if "unreviewed" in item.get("reasons", [])
        or "single_source" in item.get("reasons", [])
    ]
    return {
        "schema": "socmint.analyst_workbench.v8_0",
        "queues": {
            "high_risk": [
                item
                for item in queue
                if item.get("confidence", 0) >= 0.8
                or item.get("confidence", 0) < 0.45
            ],
            "single_source": [
                item for item in queue if "single_source" in item.get("reasons", [])
            ],
            "export_blockers": blockers,
            "sensitive": [
                item
                for item in queue
                if item.get("type") in {"email", "phone", "address", "location"}
            ],
        },
        "cases": cases,
        "captures": captures,
        "connector_trust": connectors,
        "jobs": scan_job_health(),
        "policy": policy_events_payload(),
        "scope": load_scope(),
    }


def policy_events_payload(limit: int = 100) -> dict[str, Any]:
    return {
        "schema": "socmint.policy_events.v8_0",
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "allowed": bool(event.allowed),
                "reasons": _json_loads(event.reasons_json, []),
                "payload": _json_loads(event.payload_json, {}),
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
            }
            for event in db.list_policy_gate_events(limit=limit)
        ],
    }


def connector_marketplace_payload() -> dict[str, Any]:
    trust = {row.get("connector"): row for row in connector_quality_metrics()}
    return {
        "schema": "socmint.connector_marketplace.v8_0",
        "connectors": [
            {
                "name": name,
                "target_types": spec.target_types,
                "install_status": "registered",
                "trust_badge": (
                    "trusted"
                    if trust.get(name, {}).get("reliability_score", 0) >= 0.75
                    else "needs_review"
                    if name in trust
                    else "unrated"
                ),
                "capability_tags": list(spec.target_types),
                "fixture_runner": "/api/v1/connectors/sdk/validate",
                "trust": trust.get(name, {}),
            }
            for name, spec in sorted(CONNECTORS.items())
        ],
    }


def entity_resolution_lab_payload(subject_id: int) -> dict[str, Any]:
    dossier = ultimate_dossier_payload(subject_id)
    resolution = dossier.get("resolution") or {}
    delta = resolution.get("confidence_delta_inputs") or {}
    return {
        "schema": "socmint.entity_resolution_lab.v8_0",
        "subject_id": subject_id,
        "classification": resolution.get("classification") or resolution.get("label"),
        "confidence": resolution.get("confidence"),
        "explanation": resolution.get("explanation"),
        "confidence_deltas": delta,
        "source_contribution_chart": [
            {"name": key, "value": value} for key, value in sorted(delta.items())
        ],
        "contradictions": dossier.get("contradictions") or [],
        "manual_override": {"enabled": True, "audit_required": True},
    }


def graph_canvas_payload(subject_id: int) -> dict[str, Any]:
    dossier = build_dossier(subject_id)
    return {
        "schema": "socmint.graph_canvas.v8_0",
        "subject_id": subject_id,
        "nodes": dossier.get("seeds", []) + dossier.get("assertions", []),
        "edges": dossier.get("evidence_links", []),
        "controls": {
            "confidence_slider": True,
            "time_slider": True,
            "node_grouping": ["type", "source", "confidence"],
            "evidence_side_panel": True,
            "contradiction_overlays": True,
        },
    }


def build_export_manifest(
    subject_id: int | None = None,
    case_key: str | None = None,
    redacted: bool = True,
    actor: str | None = None,
    redaction_preset: str = "client",
) -> dict[str, Any]:
    gate = gate_action("export", case_key or str(subject_id or "all"), actor=actor)
    payload = {
        "subject_id": subject_id,
        "case": case_payload(case_key) if case_key else None,
        "dossier": ultimate_dossier_payload(subject_id) if subject_id else None,
        "export_center": export_center_payload(),
        "redacted": redacted,
        "redaction_preset": redaction_preset,
    }
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(stable).hexdigest()
    return {
        "schema": "socmint.export_builder_manifest.v8_0",
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "case_key": case_key,
        "redacted": redacted,
        "redaction_preset": redaction_preset,
        "formats": ["html", "pdf", "json", "csv"],
        "payload_sha256": digest,
        "signed_manifest": hashlib.sha256(f"{digest}:socmint".encode()).hexdigest(),
        "redaction_presets": ["client", "court", "internal"],
        "export_blockers": analyst_workbench_payload().get("queues", {}).get(
            "export_blockers",
            [],
        ),
        "gate": gate,
    }


def build_export_bundle(
    subject_id: int | None = None,
    case_key: str | None = None,
    redacted: bool = True,
    redaction_preset: str = "client",
    actor: str | None = None,
) -> dict[str, Any]:
    manifest = build_export_manifest(
        subject_id=subject_id,
        case_key=case_key,
        redacted=redacted,
        redaction_preset=redaction_preset,
        actor=actor,
    )
    if not manifest["gate"]["allowed"]:
        raise PermissionError(manifest["gate"]["scope_review"]["reason"])

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    if case_key:
        target = case_key
    elif subject_id:
        target = f"subject-{subject_id}"
    else:
        target = "all"
    export_id = f"high-end-{_safe_slug(str(target))}-{stamp}"
    root = export_bundle_root()
    manifest_path = root / f"{export_id}-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    artifact_paths = [manifest_path]
    case_payload_path = None
    if case_key:
        case_payload_path = root / f"{export_id}-CASE.json"
        case_payload_path.write_text(
            json.dumps(case_payload(case_key), indent=2, sort_keys=True)
        )
        artifact_paths.append(case_payload_path)

    dossier_path = None
    if subject_id:
        dossier_path = root / f"{export_id}-DOSSIER.json"
        dossier_path.write_text(
            json.dumps(ultimate_dossier_payload(subject_id), indent=2, sort_keys=True)
        )
        artifact_paths.append(dossier_path)

    readme_path = root / f"{export_id}-README.txt"
    readme_path.write_text(
        "\n".join(
            [
                "SOCMINT High-End Export Bundle",
                f"Export ID: {export_id}",
                f"Subject ID: {subject_id}",
                f"Case key: {case_key}",
                f"Redaction preset: {redaction_preset}",
                f"Generated: {manifest['generated_at']}",
                "",
                "Verify this bundle by comparing the ZIP SHA-256 and artifact "
                "hashes recorded in the bundle manifest.",
            ]
        )
    )
    artifact_paths.append(readme_path)

    files = [
        {
            "name": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in artifact_paths
    ]
    bundle_manifest = {
        "schema": "socmint.high_end_export_bundle_manifest.v8_0_1",
        "export_id": export_id,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "case_key": case_key,
        "redacted": redacted,
        "redaction_preset": redaction_preset,
        "formats": manifest["formats"],
        "signed_manifest": manifest["signed_manifest"],
        "export_blockers": manifest.get("export_blockers", []),
        "files": files,
    }
    bundle_manifest_path = root / f"{export_id}-BUNDLE-MANIFEST.json"
    bundle_manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True)
    )

    zip_path = root / f"{export_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in [*artifact_paths, bundle_manifest_path]:
            bundle.write(path, arcname=path.name)

    bundle_sha256 = _sha256_file(zip_path)
    bundle_manifest["bundle"] = {
        "name": zip_path.name,
        "path": str(zip_path),
        "size_bytes": zip_path.stat().st_size,
        "sha256": bundle_sha256,
    }
    bundle_manifest["bundle_manifest_path"] = str(bundle_manifest_path)
    bundle_manifest["verification"] = verify_export_bundle(zip_path.name)
    bundle_manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True)
    )
    return bundle_manifest


def verify_export_bundle(name: str) -> dict[str, Any]:
    root = export_bundle_root().resolve()
    zip_path = (root / Path(name).name).resolve()
    if root not in zip_path.parents and zip_path != root:
        raise ValueError("Bundle path escapes export root")
    if not zip_path.exists():
        return {"valid": False, "reason": "bundle_not_found", "name": name}

    with zipfile.ZipFile(zip_path) as bundle:
        members = bundle.namelist()
        manifest_names = [
            item for item in members if item.endswith("-BUNDLE-MANIFEST.json")
        ]
        if not manifest_names:
            return {"valid": False, "reason": "manifest_not_found", "name": name}
        payload = json.loads(bundle.read(manifest_names[0]).decode())

    files = payload.get("files") or []
    missing = [item["name"] for item in files if item["name"] not in members]
    return {
        "schema": "socmint.high_end_export_bundle_verification.v8_0_1",
        "name": Path(name).name,
        "valid": not missing,
        "missing": missing,
        "member_count": len(members),
        "expected_file_count": len(files),
        "bundle_sha256": _sha256_file(zip_path),
        "signed_manifest": payload.get("signed_manifest"),
    }
