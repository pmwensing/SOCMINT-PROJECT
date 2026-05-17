from __future__ import annotations

from flask import flash, jsonify, redirect, render_template, session, url_for

from .command_center import command_center_payload
from .jobs import process_scan_jobs
from .runtime_import_health import runtime_import_health_report
from .test_data_controls import clean_test_data, test_data_summary
from .v11_readiness import v11_readiness_summary


def register_command_center_routes(app) -> None:
    if "api_command_center" in app.view_functions:
        return

    from .dashboard import audit, login_required, run_required

    @login_required
    def command_center_index():
        return render_template("command_center.html", payload=command_center_payload())

    @login_required
    def api_command_center():
        return jsonify(command_center_payload())

    @login_required
    def api_test_data_summary():
        return jsonify(test_data_summary())

    @login_required
    def api_runtime_import_health():
        return jsonify(runtime_import_health_report())

    @login_required
    def api_v11_readiness_summary():
        return jsonify(v11_readiness_summary())

    @run_required
    def api_test_data_clean():
        actor = session.get("user")
        result = clean_test_data(actor=actor)
        audit(
            "test_data_clean",
            actor=actor,
            details=result,
        )
        return jsonify(result)

    @run_required
    def command_center_clean_test_data():
        actor = session.get("user")
        result = clean_test_data(actor=actor)
        audit(
            "command_center_clean_test_data",
            actor=actor,
            details=result,
        )
        deleted = result.get("subjects_deleted", 0)
        flash(f"Cleaned v11 smoke/test data. Subjects deleted: {deleted}.", "success")
        return redirect(url_for("command_center_index"))

    @run_required
    def command_center_process_jobs():
        processed = process_scan_jobs(max_jobs=5)
        audit(
            "command_center_process_jobs",
            actor=session.get("user"),
            details={"processed": processed},
        )
        completed = sum(1 for item in processed if item.get("status") == "completed")
        failed = sum(1 for item in processed if item.get("status") == "failed")
        if processed:
            flash(
                f"Processed {len(processed)} queued job(s): {completed} completed, {failed} failed.",
                "success" if not failed else "error",
            )
        else:
            flash("No queued jobs were waiting.", "success")
        return redirect(url_for("dashboard.index"))

    app.view_functions["dashboard.index"] = command_center_index
    app.add_url_rule(
        "/command-center",
        endpoint="command_center_index",
        view_func=command_center_index,
        methods=["GET"],
    )

    app.add_url_rule(
        "/api/v1/command-center",
        endpoint="api_command_center",
        view_func=api_command_center,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/admin/test-data/summary",
        endpoint="api_test_data_summary",
        view_func=api_test_data_summary,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/admin/runtime/import-health",
        endpoint="api_runtime_import_health",
        view_func=api_runtime_import_health,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/admin/v11/readiness-summary",
        endpoint="api_v11_readiness_summary",
        view_func=api_v11_readiness_summary,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/v1/admin/test-data/clean",
        endpoint="api_test_data_clean",
        view_func=api_test_data_clean,
        methods=["POST"],
    )
    app.add_url_rule(
        "/command-center/test-data/clean",
        endpoint="command_center_clean_test_data",
        view_func=command_center_clean_test_data,
        methods=["POST"],
    )
    app.add_url_rule(
        "/command-center/process-jobs",
        endpoint="command_center_process_jobs",
        view_func=command_center_process_jobs,
        methods=["POST"],
    )
