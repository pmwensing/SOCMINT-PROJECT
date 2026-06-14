from __future__ import annotations

from typing import Any

from .dossier_assembly_workspace_v21_0 import (
    build_dossier_assembly_workspace,
    save_dossier_arrangement,
)
from .dossier_package_import_v21_1 import inspect_dossier_package_import


def build_dossier_assembly_workspace_v21_1(
    case_id: str,
    *,
    subject_id: int | None = None,
) -> dict[str, Any]:
    workspace = build_dossier_assembly_workspace(case_id, subject_id=subject_id)
    package_import = inspect_dossier_package_import(case_id)
    workspace["version"] = "v21.1.0"
    workspace["package_import"] = package_import
    workspace["source_identity"] = package_import["source_identity"]
    workspace["manifest_verified"] = package_import["manifest_verified"]
    workspace["package_stale"] = package_import["package_stale"]
    workspace["duplicate_import"] = package_import["duplicate_import"]
    workspace["can_arrange"] = package_import["can_arrange"]
    workspace["status"] = (
        "ready_for_arrangement"
        if package_import["can_arrange"]
        else package_import["status"]
    )
    workspace["next_action"] = package_import["next_action"]
    if subject_id is not None:
        workspace.setdefault("integration_links", {})[
            "source_evidence_citation_mapping"
        ] = f"/dossier-assembly/{case_id}/citations?subject_id={subject_id}"
    return workspace


def save_verified_dossier_arrangement(
    case_id: str,
    payload: dict[str, Any],
    *,
    actor: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    package_import = inspect_dossier_package_import(case_id)
    result = save_dossier_arrangement(
        case_id,
        payload,
        actor=actor,
        ip_address=ip_address,
    )
    result["package_import"] = package_import
    result["import_warning"] = (
        None
        if package_import["can_arrange"]
        else "legacy_api_save_without_current_package_import"
    )
    return result
