from __future__ import annotations

import csv
import html
import io
import json
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha
from .report_builder_events_v27_5 import (
    EXPORT_FORMATS,
    GENERATE_ACTION,
    SCHEMA,
    VERSION,
    _record,
    blocked,
    find_report,
    history,
)
from .saved_search_views_workspace_v27_3 import run_saved_view
from .watchlist_monitoring_workspace_v27_4 import run_watchlist_monitoring


def _source_payload(section: dict[str, Any], *, user: str, allowed_case_ids: set[str] | None, limit: int) -> dict[str, Any]:
    section_type = section["section_type"]
    if section_type == "text":
        return {"status": "text", "text": section.get("text") or "", "results": []}
    if section_type == "saved_view":
        result = run_saved_view(section["source_id"], user_identity=user, allowed_case_ids=allowed_case_ids, limit=limit)
        if result.get("status") != "saved_view_executed":
            return blocked("report_saved_view_execution_failed")
        payload = result.get("execution") or {}
        return {"status": "ready", "source": result.get("saved_view"), "results": payload.get("results") or [], "summary": {"result_count": payload.get("result_count", len(payload.get("results") or [])), "access_scope": payload.get("access_scope"), "result_set_sha256": payload.get("result_set_sha256")}}
    result = run_watchlist_monitoring(section["source_id"], user_identity=user, allowed_case_ids=allowed_case_ids, limit=limit)
    if result.get("status") != "watchlist_monitoring_completed":
        return blocked("report_watchlist_execution_failed")
    payload = result.get("execution") or {}
    return {"status": "ready", "source": {"watchlist_id": section["source_id"], "monitoring_run_id": result.get("monitoring_run_id"), "monitoring_run_sha256": result.get("watchlist_event_sha256")}, "results": payload.get("results") or [], "summary": {"result_count": payload.get("result_count", len(payload.get("results") or [])), "access_scope": payload.get("access_scope"), "result_set_sha256": result.get("result_set_sha256"), "change_detected": result.get("change_detected")}}


def _rows(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for section in sections:
        for item in section.get("results") or []:
            rows.append({
                "section": section["title"],
                "section_type": section["section_type"],
                "result_id": item.get("result_id"),
                "record_type": item.get("record_type") or item.get("result_type"),
                "case_id": item.get("case_id"),
                "score": item.get("score"),
                "title": item.get("title") or "",
                "summary": item.get("summary") or "",
                "actor": item.get("actor") or "",
                "occurred_at": item.get("occurred_at") or "",
            })
    return rows


def _render_json(package: dict[str, Any]) -> str:
    return json.dumps(package, sort_keys=True, indent=2, default=str) + "\n"


def _render_csv(package: dict[str, Any]) -> str:
    output = io.StringIO()
    fields = ["section", "section_type", "result_id", "record_type", "case_id", "score", "title", "summary", "actor", "occurred_at"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(_rows(package["sections"]))
    return output.getvalue()


def _render_html(package: dict[str, Any]) -> str:
    parts = ["<!doctype html><html><head><meta charset=\"utf-8\"><title>", html.escape(package["name"]), "</title></head><body>", f"<h1>{html.escape(package['name'])}</h1>"]
    for section in package["sections"]:
        parts.append(f"<section><h2>{html.escape(section['title'])}</h2>")
        if section.get("text"):
            parts.append(f"<p>{html.escape(section['text'])}</p>")
        if section.get("include_summary"):
            parts.append(f"<pre>{html.escape(json.dumps(section.get('summary') or {}, indent=2, sort_keys=True, default=str))}</pre>")
        if section.get("include_results"):
            parts.append("<table><thead><tr><th>Type</th><th>Case</th><th>Title</th><th>Summary</th></tr></thead><tbody>")
            for item in section.get("results") or []:
                parts.append("<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(html.escape(str(item.get("record_type") or item.get("result_type") or "")), html.escape(str(item.get("case_id") or "")), html.escape(str(item.get("title") or "")), html.escape(str(item.get("summary") or ""))))
            parts.append("</tbody></table>")
        parts.append("</section>")
    parts.append("</body></html>")
    return "".join(parts)


def latest_packages(report_id: str | None = None) -> list[dict[str, Any]]:
    packages = [item for item in history() if item.get("event_type") == "package_generated"]
    if report_id:
        packages = [item for item in packages if item.get("report_id") == report_id]
    return packages


def generate_report_package(
    report_id: str,
    *,
    user_identity: str,
    allowed_case_ids: set[str] | None = None,
    formats: list[str] | None = None,
    limit: int = 100,
    confirmed: bool,
    ip_address: str | None = None,
    resolved_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    report = find_report(report_id, user_identity)
    if report is None or report.get("report_status") != "active": return blocked("active_visible_report_required")
    if confirmed is not True: return blocked("explicit_report_generation_confirmation_required")
    requested_formats = sorted({str(item) for item in (formats or report.get("definition", {}).get("export_formats") or []) if str(item) in EXPORT_FORMATS})
    if not requested_formats: return blocked("report_export_format_required")
    rendered_sections = []
    for index, definition in enumerate(report.get("definition", {}).get("sections") or []):
        source = resolved_sections[index] if resolved_sections is not None else _source_payload(definition, user=user_identity, allowed_case_ids=allowed_case_ids, limit=limit)
        if source.get("status") == "blocked": return source
        rendered_sections.append({**definition, "source_binding": source.get("source"), "source_binding_sha256": _sha(source.get("source") or {"section_type": definition["section_type"]}), "summary": source.get("summary") or {}, "text": source.get("text") or definition.get("text"), "results": source.get("results") or []})
    package_core = {
        "name": report.get("name"), "description": report.get("definition", {}).get("description"),
        "report_id": report_id, "report_revision": report.get("revision"),
        "report_definition_sha256": report.get("definition_sha256"),
        "generated_by": user_identity, "executed_access_scope": {"mode": "restricted" if allowed_case_ids is not None else "all_visible_cases", "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None},
        "sections": rendered_sections,
    }
    files = []
    renderers = {"json": _render_json, "csv": _render_csv, "html": _render_html}
    for format_name in requested_formats:
        content = renderers[format_name](package_core)
        files.append({"format": format_name, "filename": f"{report_id}.{format_name}", "media_type": {"json":"application/json","csv":"text/csv","html":"text/html"}[format_name], "size_bytes": len(content.encode("utf-8")), "sha256": _sha(content), "content": content})
    manifest = [{key: value for key, value in item.items() if key != "content"} for item in files]
    content = {"event_type": "package_generated", "report_id": report_id, "owner": report.get("owner"), "generated_by": user_identity, "report_binding": {"report_id": report_id, "report_event_id": report.get("report_event_id"), "report_event_sha256": report.get("report_event_sha256"), "definition_sha256": report.get("definition_sha256"), "revision": report.get("revision")}, "executed_access_scope": package_core["executed_access_scope"], "section_count": len(rendered_sections), "result_count": sum(len(item.get("results") or []) for item in rendered_sections), "formats": requested_formats, "file_manifest": manifest, "file_manifest_sha256": _sha(manifest)}
    digest = _sha(content)
    event = {"schema": SCHEMA, "version": VERSION, **content, "package_id": f"report-package-{digest[:24]}", "package_event_id": f"report-package-event-{digest[:24]}", "package_sha256": digest, "source_records_mutated": False, "report_definition_mutated": False, "case_access_scope_changed": False, "report_grants_access": False}
    recorded = _record(GENERATE_ACTION, event, user_identity, ip_address)
    return {**recorded, "status": "report_package_generated", "files": files, "next_action": "download_or_review_report_package"}
