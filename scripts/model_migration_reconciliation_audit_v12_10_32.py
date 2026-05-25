#!/usr/bin/env python3
from __future__ import annotations

import ast
import configparser
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


ROOT = Path.cwd()
VERSION = "12.10.32"

OUT_DIR = ROOT / "release" / "model_migration_reconciliation"
OUT_JSON = OUT_DIR / "MODEL_MIGRATION_RECONCILIATION_V12_10_32.json"
OUT_MD = OUT_DIR / "MODEL_MIGRATION_RECONCILIATION_V12_10_32.md"
OUT_CSV = OUT_DIR / "MODEL_MIGRATION_RECONCILIATION_V12_10_32.csv"
OUT_PLAN = OUT_DIR / "ALEMBIC_CANDIDATE_PLAN_V12_10_32.md"

SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "storage",
    "release",
    "dist",
    "build",
}

LEGACY_HINTS = {
    "legacy",
    "old",
    "archive",
    "archived",
    "deprecated",
    "backup",
    "scratch",
    "tmp",
    "experimental",
}

TEST_HINTS = {
    "test",
    "tests",
    "fixture",
    "fixtures",
    "mock",
    "demo",
    "sample",
}

ACTIVE_HINTS = {
    "src/socmint",
    "app",
    "models",
    "dashboard",
    "workbench",
    "spine",
    "evidence",
    "dossier",
    "identity",
    "case",
    "watch",
    "policy",
    "retention",
    "graph",
    "timeline",
    "connector",
    "scan",
    "job",
    "audit",
    "user",
    "auth",
}


DOMAIN_KEYWORDS = {
    "identity": ["identity", "spine", "subject", "entity", "cluster", "resolution", "profile"],
    "evidence": ["evidence", "artifact", "vault", "custody", "hash", "lineage", "intake"],
    "dossier": ["dossier", "report", "export", "full_report", "narrative"],
    "case": ["case", "tenant", "matter"],
    "graph": ["graph", "node", "edge", "relationship", "link"],
    "watchlist": ["watch", "monitor", "alert", "continuous"],
    "connectors": ["connector", "scan", "enrich", "osint", "run", "job", "intel"],
    "policy": ["policy", "gate", "retention", "compliance", "audit"],
    "auth": ["user", "role", "auth", "session", "token"],
    "timeline": ["timeline", "event", "activity"],
    "risk": ["risk", "score", "threat", "exposure", "contradiction"],
    "system": ["setting", "config", "health", "status", "log"],
}


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def run(cmd: List[str]) -> Tuple[int, str]:
    try:
        return 0, subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
    except Exception as exc:
        return 1, getattr(exc, "output", repr(exc))


def py_files() -> List[Path]:
    files: List[Path] = []
    for p in ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if p.is_file():
            files.append(p)
    return sorted(files)


def migration_versions_dir() -> Path:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "alembic.ini")
    loc = cfg.get("alembic", "script_location", fallback="alembic")
    return ROOT / loc / "versions"


def extract_model_tables() -> Dict[str, Dict[str, Any]]:
    tables: Dict[str, Dict[str, Any]] = {}

    for path in py_files():
        text = read(path)
        rel_path = rel(path)

        for match in re.finditer(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]", text):
            table = match.group(1)
            tables.setdefault(table, {
                "table": table,
                "sources": [],
                "decl_types": set(),
            })
            tables[table]["sources"].append({
                "file": rel_path,
                "line": text[:match.start()].count("\n") + 1,
                "kind": "__tablename__",
            })
            tables[table]["decl_types"].add("__tablename__")

        for match in re.finditer(r"\bTable\(\s*['\"]([^'\"]+)['\"]", text):
            table = match.group(1)
            tables.setdefault(table, {
                "table": table,
                "sources": [],
                "decl_types": set(),
            })
            tables[table]["sources"].append({
                "file": rel_path,
                "line": text[:match.start()].count("\n") + 1,
                "kind": "Table()",
            })
            tables[table]["decl_types"].add("Table()")

    for info in tables.values():
        info["decl_types"] = sorted(info["decl_types"])

    return tables


def extract_migration_tables() -> Dict[str, Dict[str, Any]]:
    versions = migration_versions_dir()
    tables: Dict[str, Dict[str, Any]] = {}

    if not versions.exists():
        return tables

    patterns = [
        ("op.create_table", r"op\.create_table\(\s*['\"]([^'\"]+)['\"]"),
        ("_create_if_missing", r"_create_if_missing\(\s*['\"]([^'\"]+)['\"]"),
        ("op.drop_table", r"op\.drop_table\(\s*['\"]([^'\"]+)['\"]"),
        ("_drop_if_exists", r"_drop_if_exists\(\s*['\"]([^'\"]+)['\"]"),
        ("op.rename_table", r"op\.rename_table\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]"),
    ]

    for path in sorted(versions.glob("*.py")):
        text = read(path)
        rel_path = rel(path)

        for kind, pattern in patterns:
            for match in re.finditer(pattern, text):
                if kind == "op.rename_table":
                    names = [match.group(1), match.group(2)]
                else:
                    names = [match.group(1)]

                for table in names:
                    tables.setdefault(table, {
                        "table": table,
                        "sources": [],
                        "migration_ops": set(),
                    })
                    tables[table]["sources"].append({
                        "file": rel_path,
                        "line": text[:match.start()].count("\n") + 1,
                        "kind": kind,
                    })
                    tables[table]["migration_ops"].add(kind)

    for info in tables.values():
        info["migration_ops"] = sorted(info["migration_ops"])

    return tables


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def singularize(name: str) -> str:
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses"):
        return name[:-2]
    if name.endswith("s"):
        return name[:-1]
    return name


def domain_for(table: str, sources: List[Dict[str, Any]]) -> str:
    haystack = " ".join([table] + [s["file"] for s in sources]).lower()

    scores = {}
    for domain, keys in DOMAIN_KEYWORDS.items():
        score = sum(1 for key in keys if key in haystack)
        if score:
            scores[domain] = score

    if not scores:
        return "uncategorized"

    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[0][0]


def classify_active_status(table: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    paths = [s["file"].lower() for s in sources]
    combined = " ".join(paths + [table.lower()])

    if any(part in combined for part in TEST_HINTS):
        return {
            "status": "test_or_fixture",
            "confidence": 0.9,
            "reason": "path/name contains test, fixture, mock, demo, or sample hint",
        }

    if any(part in combined for part in LEGACY_HINTS):
        return {
            "status": "legacy_or_archived",
            "confidence": 0.8,
            "reason": "path/name contains legacy/archive/deprecated/experimental hint",
        }

    if any(path.startswith("src/socmint/") for path in paths):
        return {
            "status": "active_candidate",
            "confidence": 0.75,
            "reason": "declared under src/socmint",
        }

    if any(hint in combined for hint in ACTIVE_HINTS):
        return {
            "status": "active_candidate",
            "confidence": 0.55,
            "reason": "path/name contains active domain hint",
        }

    return {
        "status": "unknown_review",
        "confidence": 0.35,
        "reason": "no clear active/legacy/test signal",
    }


def indirect_coverage_hints(table: str, migration_tables: Set[str]) -> List[Dict[str, Any]]:
    hints = []

    norm = normalize_name(table)
    singular = normalize_name(singularize(table))

    for mt in migration_tables:
        mnorm = normalize_name(mt)
        msing = normalize_name(singularize(mt))

        if norm == mnorm or singular == msing:
            continue

        if norm in mnorm or mnorm in norm or singular in msing or msing in singular:
            hints.append({
                "migration_table": mt,
                "reason": "normalized substring/pluralization similarity",
                "strength": "medium",
            })

        # prefix/suffix family relation
        parts = [x for x in re.split(r"[_\W]+", table.lower()) if x]
        mparts = [x for x in re.split(r"[_\W]+", mt.lower()) if x]
        common = sorted(set(parts) & set(mparts))
        if len(common) >= 2:
            hints.append({
                "migration_table": mt,
                "reason": f"shared table tokens: {', '.join(common[:5])}",
                "strength": "low",
            })

    # Deduplicate
    seen = set()
    out = []
    for hint in hints:
        key = (hint["migration_table"], hint["reason"])
        if key not in seen:
            seen.add(key)
            out.append(hint)

    return out[:10]


def migration_priority(domain: str, status: str, table: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    score = 0
    reasons = []

    if status == "active_candidate":
        score += 50
        reasons.append("active candidate")
    elif status == "unknown_review":
        score += 25
        reasons.append("unknown requires review")
    elif status == "legacy_or_archived":
        score += 5
        reasons.append("legacy/archive likely lower priority")
    elif status == "test_or_fixture":
        score -= 10
        reasons.append("test/fixture likely excluded")

    if domain in {"identity", "evidence", "dossier", "case", "graph", "connectors", "policy"}:
        score += 20
        reasons.append(f"core domain: {domain}")

    if domain in {"watchlist", "risk", "timeline"}:
        score += 15
        reasons.append(f"operational domain: {domain}")

    if table.startswith(("spine_", "identity_", "dossier_", "evidence_", "artifact_", "workbench_", "policy_", "retention_")):
        score += 15
        reasons.append("known v6/v7/v12 family prefix")

    if len(sources) > 1:
        score += min(10, len(sources) * 2)
        reasons.append("declared/referenced in multiple files")

    if score >= 80:
        bucket = "P0"
    elif score >= 60:
        bucket = "P1"
    elif score >= 35:
        bucket = "P2"
    elif score >= 10:
        bucket = "P3"
    else:
        bucket = "EXCLUDE_OR_REVIEW"

    return {
        "score": score,
        "bucket": bucket,
        "reasons": reasons,
    }


def import_reference_count(table: str) -> Dict[str, Any]:
    # Lightweight static reference scan. Not a semantic call graph.
    count = 0
    files = []
    needle = table

    for p in py_files():
        text = read(p)
        if needle in text:
            count += text.count(needle)
            files.append(rel(p))

    return {
        "count": count,
        "files": sorted(set(files))[:20],
    }


def build_reconciliation() -> Dict[str, Any]:
    model_info = extract_model_tables()
    migration_info = extract_migration_tables()

    model_tables_set = set(model_info.keys())
    migration_tables_set = set(migration_info.keys())

    missing = sorted(model_tables_set - migration_tables_set)
    migration_only = sorted(migration_tables_set - model_tables_set)

    records = []

    for table in missing:
        info = model_info[table]
        sources = info["sources"]
        domain = domain_for(table, sources)
        active = classify_active_status(table, sources)
        refs = import_reference_count(table)
        hints = indirect_coverage_hints(table, migration_tables_set)
        priority = migration_priority(domain, active["status"], table, sources)

        # Lower priority when likely indirectly covered.
        if hints and priority["score"] >= 10:
            priority["score"] -= 5
            priority["reasons"].append("possible indirect/rename coverage")
            if priority["bucket"] == "P0" and priority["score"] < 80:
                priority["bucket"] = "P1"

        records.append({
            "table": table,
            "domain": domain,
            "status": active["status"],
            "status_confidence": active["confidence"],
            "status_reason": active["reason"],
            "priority_bucket": priority["bucket"],
            "priority_score": priority["score"],
            "priority_reasons": priority["reasons"],
            "decl_types": info["decl_types"],
            "sources": sources,
            "reference_count": refs["count"],
            "reference_files": refs["files"],
            "indirect_coverage_hints": hints,
            "migration_action": proposed_action(active["status"], hints, priority["bucket"]),
        })

    records.sort(key=lambda r: (
        {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "EXCLUDE_OR_REVIEW": 4}.get(r["priority_bucket"], 9),
        -r["priority_score"],
        r["domain"],
        r["table"],
    ))

    by_domain = defaultdict(list)
    by_status = defaultdict(list)
    by_priority = defaultdict(list)

    for r in records:
        by_domain[r["domain"]].append(r["table"])
        by_status[r["status"]].append(r["table"])
        by_priority[r["priority_bucket"]].append(r["table"])

    code_heads, heads_out = run(["alembic", "heads"])
    heads = [line.split()[0] for line in heads_out.splitlines() if line.strip()]

    return {
        "version": VERSION,
        "generated_from": str(ROOT),
        "alembic": {
            "heads_command_ok": code_heads == 0,
            "heads": heads,
            "raw_heads": heads_out,
            "versions_dir": rel(migration_versions_dir()) if migration_versions_dir().exists() else str(migration_versions_dir()),
        },
        "summary": {
            "model_table_count": len(model_tables_set),
            "migration_table_count": len(migration_tables_set),
            "missing_model_tables_from_migrations": len(missing),
            "migration_only_tables": len(migration_only),
            "priority_counts": {k: len(v) for k, v in sorted(by_priority.items())},
            "status_counts": {k: len(v) for k, v in sorted(by_status.items())},
            "domain_counts": {k: len(v) for k, v in sorted(by_domain.items())},
            "schema_mutation": "none",
            "migration_created": False,
        },
        "missing_records": records,
        "migration_only_tables": migration_only,
        "grouped": {
            "by_domain": {k: v for k, v in sorted(by_domain.items())},
            "by_status": {k: v for k, v in sorted(by_status.items())},
            "by_priority": {k: v for k, v in sorted(by_priority.items())},
        },
    }


def proposed_action(status: str, hints: List[Dict[str, Any]], bucket: str) -> str:
    if status == "test_or_fixture":
        return "exclude_from_schema; confirm test-only"
    if status == "legacy_or_archived":
        return "defer_or_archive; confirm not used by runtime"
    if hints:
        return "human_review_for_rename_or_indirect_coverage"
    if bucket in {"P0", "P1"}:
        return "candidate_for_explicit_alembic_migration_after_column_review"
    if bucket in {"P2", "P3"}:
        return "review_before_migration"
    return "exclude_or_review"


def write_json(data: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True))


def write_csv(data: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fields = [
        "priority_bucket",
        "priority_score",
        "table",
        "domain",
        "status",
        "status_confidence",
        "status_reason",
        "migration_action",
        "reference_count",
        "source_files",
        "indirect_coverage_hints",
        "priority_reasons",
    ]

    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for r in data["missing_records"]:
            writer.writerow({
                "priority_bucket": r["priority_bucket"],
                "priority_score": r["priority_score"],
                "table": r["table"],
                "domain": r["domain"],
                "status": r["status"],
                "status_confidence": r["status_confidence"],
                "status_reason": r["status_reason"],
                "migration_action": r["migration_action"],
                "reference_count": r["reference_count"],
                "source_files": ";".join(sorted({s["file"] for s in r["sources"]})),
                "indirect_coverage_hints": json.dumps(r["indirect_coverage_hints"], sort_keys=True),
                "priority_reasons": ";".join(r["priority_reasons"]),
            })


def write_markdown(data: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = data["summary"]
    lines = [
        "# v12.10.32 Model/Migration Reconciliation Audit",
        "",
        "## Result",
        "",
        "- **schema_mutation**: `none`",
        "- **migration_created**: `False`",
        f"- **model tables**: `{summary['model_table_count']}`",
        f"- **migration tables**: `{summary['migration_table_count']}`",
        f"- **missing model tables from migrations**: `{summary['missing_model_tables_from_migrations']}`",
        f"- **migration-only tables**: `{summary['migration_only_tables']}`",
        "",
        "## Priority counts",
        "",
    ]

    for bucket, count in summary["priority_counts"].items():
        lines.append(f"- **{bucket}**: `{count}`")

    lines.extend(["", "## Status counts", ""])

    for status, count in summary["status_counts"].items():
        lines.append(f"- **{status}**: `{count}`")

    lines.extend(["", "## Domain counts", ""])

    for domain, count in summary["domain_counts"].items():
        lines.append(f"- **{domain}**: `{count}`")

    lines.extend([
        "",
        "## Ranked missing tables",
        "",
        "| Priority | Score | Table | Domain | Status | Action | Sources | Hints |",
        "|---|---:|---|---|---|---|---|---:|",
    ])

    for r in data["missing_records"]:
        source_files = sorted({s["file"] for s in r["sources"]})
        lines.append(
            "| {bucket} | {score} | `{table}` | {domain} | {status} | {action} | {sources} | {hints} |".format(
                bucket=r["priority_bucket"],
                score=r["priority_score"],
                table=r["table"],
                domain=r["domain"],
                status=r["status"],
                action=r["migration_action"],
                sources="<br>".join(source_files[:5]),
                hints=len(r["indirect_coverage_hints"]),
            )
        )

    lines.extend([
        "",
        "## Migration-only tables",
        "",
    ])

    for table in data["migration_only_tables"]:
        lines.append(f"- `{table}`")

    OUT_MD.write_text("\n".join(lines))


def write_candidate_plan(data: Dict[str, Any]) -> None:
    p0p1 = [
        r for r in data["missing_records"]
        if r["priority_bucket"] in {"P0", "P1"}
        and r["migration_action"] == "candidate_for_explicit_alembic_migration_after_column_review"
    ]

    review = [
        r for r in data["missing_records"]
        if r["migration_action"] != "candidate_for_explicit_alembic_migration_after_column_review"
    ]

    lines = [
        "# v12.10.32 Safe Alembic Candidate Plan",
        "",
        "This is a **plan only**. It does not create or apply a migration.",
        "",
        "## Preconditions before generating a real migration",
        "",
        "1. Review each P0/P1 table and confirm it is used by the current runtime.",
        "2. Extract actual column definitions from SQLAlchemy models.",
        "3. Confirm table naming and possible renames.",
        "4. Exclude tests, fixtures, samples, demos, archived, and legacy modules.",
        "5. Run a dry-run migration on an empty database.",
        "6. Run downgrade safety check.",
        "",
        "## Candidate P0/P1 tables for explicit migration",
        "",
    ]

    if not p0p1:
        lines.append("_No P0/P1 explicit migration candidates detected._")
    else:
        for r in p0p1:
            lines.append(f"### `{r['table']}`")
            lines.append(f"- priority: `{r['priority_bucket']}` / score `{r['priority_score']}`")
            lines.append(f"- domain: `{r['domain']}`")
            lines.append(f"- status: `{r['status']}`")
            lines.append(f"- reason: `{r['status_reason']}`")
            lines.append(f"- sources:")
            for src in r["sources"]:
                lines.append(f"  - `{src['file']}:{src['line']}` ({src['kind']})")
            lines.append("")

    lines.extend([
        "",
        "## Tables requiring human review before migration",
        "",
    ])

    for r in review[:300]:
        lines.append(
            f"- `{r['table']}` — {r['priority_bucket']} / {r['domain']} / {r['status']} / {r['migration_action']}"
        )

    lines.extend([
        "",
        "## Skeleton for later manual migration",
        "",
        "```python",
        '"""v12.10.33 reviewed model/migration reconciliation',
        "",
        "Revision ID: 0018_reviewed_model_migration_reconciliation",
        "Revises: 0017_v12_10_schema_reconciliation",
        '"""',
        "",
        "# This skeleton is intentionally incomplete.",
        "# Fill columns manually after reviewing SQLAlchemy models.",
        "",
        "from alembic import op",
        "import sqlalchemy as sa",
        "",
        'revision = "0018_reviewed_model_migration_reconciliation"',
        'down_revision = "0017_v12_10_schema_reconciliation"',
        "branch_labels = None",
        "depends_on = None",
        "",
        "def upgrade():",
        "    # create reviewed tables only",
        "    pass",
        "",
        "def downgrade():",
        "    # drop reviewed tables only, reverse dependency order",
        "    pass",
        "```",
    ])

    OUT_PLAN.write_text("\n".join(lines))


def main() -> int:
    data = build_reconciliation()
    write_json(data)
    write_csv(data)
    write_markdown(data)
    write_candidate_plan(data)

    print(json.dumps({
        "version": VERSION,
        "schema_mutation": "none",
        "migration_created": False,
        "model_table_count": data["summary"]["model_table_count"],
        "migration_table_count": data["summary"]["migration_table_count"],
        "missing_model_tables_from_migrations": data["summary"]["missing_model_tables_from_migrations"],
        "migration_only_tables": data["summary"]["migration_only_tables"],
        "priority_counts": data["summary"]["priority_counts"],
        "status_counts": data["summary"]["status_counts"],
        "domain_counts": data["summary"]["domain_counts"],
        "report_json": str(OUT_JSON),
        "report_md": str(OUT_MD),
        "report_csv": str(OUT_CSV),
        "candidate_plan": str(OUT_PLAN),
    }, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
