from __future__ import annotations

from flask import jsonify, redirect, render_template, url_for, flash, session

from .command_center import command_center_payload
from .jobs import process_scan_jobs


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
        "/api/v1/command-center",
        endpoint="api_command_center",
        view_func=api_command_center,
        methods=["GET"],
    )
    app.add_url_rule(
        "/command-center/process-jobs",
        endpoint="command_center_process_jobs",
        view_func=command_center_process_jobs,
        methods=["POST"],
    )
