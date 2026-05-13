from __future__ import annotations

from flask import jsonify, session

from .beta_readiness_routes import register_beta_readiness_routes
from .case_access_routes import register_case_access_routes
from .certification_routes import register_certification_routes
from .dossier_builder_v3_routes import register_dossier_builder_v3_routes
from .dossier_export_pack_routes import register_dossier_export_pack_routes
from .dossier_export_store_routes import register_dossier_export_store_routes
from .hardening_routes import register_hardening_routes
from .operator_smoke_routes import register_operator_smoke_routes
from .production_installer_routes import register_production_installer_routes
from .production_release import production_release_check
from .production_release import production_release_summary
from .release_integrity_routes import register_release_integrity_routes
from .release_pipeline_routes import register_release_pipeline_routes


def register_production_release_routes(app):
    register_hardening_routes(app)
    register_case_access_routes(app)
    register_release_pipeline_routes(app)
    register_beta_readiness_routes(app)
    register_certification_routes(app)
    register_operator_smoke_routes(app)
    register_release_integrity_routes(app)
    register_production_installer_routes(app)
    register_dossier_builder_v3_routes(app)
    register_dossier_export_pack_routes(app)
    register_dossier_export_store_routes(app)

    @app.get("/api/v1/production-release")
    def api_production_release():
        username = session.get("user")
        return jsonify(production_release_check(username=username))

    @app.get("/api/v1/production-release/summary")
    def api_production_release_summary():
        return jsonify(production_release_summary())

    return app
