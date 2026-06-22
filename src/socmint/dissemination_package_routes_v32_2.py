from __future__ import annotations

from flask import jsonify, request, session

from .dissemination_package_v32_2 import (
    assemble_dissemination_package,
    dissemination_package_history,
    dissemination_packages_for_case,
    find_dissemination_package,
)
from .user_account_workspace_v28_1 import actor_is_administrator


def _payload() -> dict:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _authorized():
    actor = str(session.get("user") or "")
    if not actor:
        return None, (jsonify({"error": "login required"}), 401)
    if not actor_is_administrator(actor):
        return None, (jsonify({"error": "administrator required"}), 403)
    return actor, None


def register_dissemination_package_routes_v32_2(app):
    @app.get("/api/v1/dissemination-governance/packages")
    def list_dissemination_packages_v32_2():
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.dissemination_packages.v32_2",
                "version": "v32.2.0",
                "dissemination_packages": dissemination_package_history(),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/cases/<case_id>/packages"
    )
    def list_case_dissemination_packages_v32_2(case_id: str):
        actor, error = _authorized()
        if error:
            return error
        return jsonify(
            {
                "schema": "socmint.case_dissemination_packages.v32_2",
                "version": "v32.2.0",
                "case_id": case_id,
                "dissemination_packages": dissemination_packages_for_case(case_id),
            }
        )

    @app.get(
        "/api/v1/dissemination-governance/packages/<dissemination_package_id>"
    )
    def get_dissemination_package_v32_2(dissemination_package_id: str):
        actor, error = _authorized()
        if error:
            return error
        package = find_dissemination_package(dissemination_package_id)
        if package is None:
            return jsonify({"error": "dissemination package not found"}), 404
        return jsonify(package)

    @app.post(
        "/api/v1/dissemination-governance/published-revisions/"
        "<published_revision_id>/audience-contracts/"
        "<audience_contract_id>/packages"
    )
    def create_dissemination_package_v32_2(
        published_revision_id: str,
        audience_contract_id: str,
    ):
        actor, error = _authorized()
        if error:
            return error
        data = _payload()
        result = assemble_dissemination_package(
            actor=actor,
            published_revision_id=published_revision_id,
            audience_contract_id=audience_contract_id,
            package_label=str(data.get("package_label") or ""),
            reason=str(data.get("reason") or ""),
            confirmed=data.get("confirmed") is True,
            note=str(data.get("note") or ""),
            ip_address=request.remote_addr,
        )
        status = (
            201
            if result.get("status") == "dissemination_package_assembled"
            else 422
        )
        return jsonify(result), status

    return app
