import html
import json
import os
import re
from datetime import datetime, UTC
from pathlib import Path

from . import database as db
from .contradictions import contradiction_payload
from .identity_graph import graph_payload
from .spine import build_dossier


DEFAULT_EXPORT_ROOT = "var/socmint/exports"


def export_root() -> Path:
    root = Path(os.environ.get("SOCMINT_EXPORT_DIR", DEFAULT_EXPORT_ROOT))
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_name(value: str) -> str:
    value = value or "dossier"
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return value[:80] or "dossier"


def build_export_payload(subject_id: int) -> dict:
    dossier = build_dossier(subject_id)
    graph = graph_payload(subject_id)
    contradictions = contradiction_payload(subject_id)

    return {
        "export": {
            "schema": "socmint.dossier.export.v6_6",
            "created_at": datetime.now(UTC).isoformat(),
            "subject_id": subject_id,
        },
        "dossier": dossier,
        "identity_graph": graph,
        "contradictions": contradictions,
    }


def export_dossier(subject_id: int, formats=None) -> dict:
    formats = formats or ["json", "html", "pdf"]
    payload = build_export_payload(subject_id)
    subject = payload["dossier"]["subject"]
    base = safe_name(f"subject-{subject['id']}-{subject.get('label') or 'dossier'}")
    out_dir = export_root() / base
    out_dir.mkdir(parents=True, exist_ok=True)

    files = []
    if "json" in formats:
        files.append(write_json_export(out_dir, base, payload))
    if "html" in formats:
        files.append(write_html_export(out_dir, base, payload))
    if "pdf" in formats:
        files.append(write_pdf_export(out_dir, base, payload))

    export_id = db.create_dossier_export_record(
        subject_id,
        str(out_dir),
        files,
    )

    return {
        "export_id": export_id,
        "subject_id": subject_id,
        "directory": str(out_dir),
        "files": files,
        "created_at": payload["export"]["created_at"],
    }


def write_json_export(out_dir: Path, base: str, payload: dict) -> dict:
    path = out_dir / f"{base}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return {"format": "json", "path": str(path), "size_bytes": path.stat().st_size}


def write_html_export(out_dir: Path, base: str, payload: dict) -> dict:
    path = out_dir / f"{base}.html"
    path.write_text(render_html(payload))
    return {"format": "html", "path": str(path), "size_bytes": path.stat().st_size}


def write_pdf_export(out_dir: Path, base: str, payload: dict) -> dict:
    path = out_dir / f"{base}.pdf"
    lines = render_text_lines(payload)
    path.write_bytes(simple_pdf(lines))
    return {"format": "pdf", "path": str(path), "size_bytes": path.stat().st_size}


def render_html(payload: dict) -> str:
    dossier = payload["dossier"]
    subject = dossier["subject"]
    assertions = dossier["assertions"]
    contradictions = payload["contradictions"]["contradictions"]

    assertion_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item['id']))}</td>"
        f"<td>{html.escape(str(item['type']))}</td>"
        f"<td>{html.escape(str(item['value']))}</td>"
        f"<td>{item['confidence']:.3f}</td>"
        f"<td>{html.escape(str(item['validation_state']))}</td>"
        "</tr>"
        for item in assertions
    )

    contradiction_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item['id']))}</td>"
        f"<td>{html.escape(str(item['severity']))}</td>"
        f"<td>{html.escape(str(item['type']))}</td>"
        f"<td>{html.escape(str(item['status']))}</td>"
        f"<td>{html.escape(str(item['summary']))}</td>"
        "</tr>"
        for item in contradictions
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SOCMINT Dossier Export</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #ccc; padding: 0.35rem; text-align: left; }}
    code {{ font-family: monospace; }}
  </style>
</head>
<body>
  <h1>SOCMINT Dossier Export</h1>
  <h2>Subject</h2>
  <p><strong>ID:</strong> {html.escape(str(subject["id"]))}</p>
  <p><strong>Label:</strong> {html.escape(str(subject.get("label") or ""))}</p>
  <p><strong>Created:</strong> {html.escape(str(subject.get("created_at")))}</p>

  <h2>Summary</h2>
  <ul>
    <li>Connector runs: {dossier["summary"]["connector_runs"]}</li>
    <li>Observations: {dossier["summary"]["observations"]}</li>
    <li>Assertions: {dossier["summary"]["assertions"]}</li>
    <li>Validated assertions: {dossier["summary"]["validated_assertions"]}</li>
  </ul>

  <h2>Assertions</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Type</th><th>Value</th><th>Confidence</th>
      <th>Validation</th></tr>
    </thead>
    <tbody>{assertion_rows}</tbody>
  </table>

  <h2>Contradictions</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Severity</th><th>Type</th><th>Status</th>
      <th>Summary</th></tr>
    </thead>
    <tbody>{contradiction_rows}</tbody>
  </table>
</body>
</html>
"""


def render_text_lines(payload: dict) -> list[str]:
    dossier = payload["dossier"]
    subject = dossier["subject"]
    lines = [
        "SOCMINT Dossier Export",
        f"Subject ID: {subject['id']}",
        f"Label: {subject.get('label') or ''}",
        f"Created: {subject.get('created_at')}",
        "",
        "Summary",
        f"Connector runs: {dossier['summary']['connector_runs']}",
        f"Observations: {dossier['summary']['observations']}",
        f"Assertions: {dossier['summary']['assertions']}",
        f"Validated assertions: {dossier['summary']['validated_assertions']}",
        "",
        "Top assertions",
    ]

    for item in dossier["assertions"][:40]:
        lines.append(
            f"[{item['confidence']:.3f}] {item['type']}: {item['value']}"
        )

    contradictions = payload["contradictions"]["contradictions"]
    if contradictions:
        lines.extend(["", "Contradictions"])
        for item in contradictions[:30]:
            lines.append(
                f"{item['severity']} {item['type']}: {item['summary']}"
            )

    return lines


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_pdf(lines: list[str]) -> bytes:
    objects = []
    stream_lines = ["BT", "/F1 11 Tf", "50 750 Td", "14 TL"]

    for line in lines[:52]:
        stream_lines.append(f"({pdf_escape(str(line)[:110])}) Tj")
        stream_lines.append("T*")

    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("utf-8")

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> "
        b"/Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream
        + b"\nendstream"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + str(xref).encode("ascii")
        + b"\n%%EOF\n"
    )
    return bytes(pdf)
