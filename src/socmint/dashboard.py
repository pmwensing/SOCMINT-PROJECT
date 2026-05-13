import functools
import json
import logging
import os
import re
import secrets
import time
import uuid

from flask import (
    Blueprint,
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import safe_join

from . import database as db
from .config import configure_logging, load_settings
from .report_review import report_runs_payload
from .report_review import review_items_payload
from .report_review import review_summary
from .report_export_center import export_center_payload
from .entity_dossier_v2 import build_full_entity_dossier_v2
from .entity_dossier_v2 import export_full_entity_dossier_v2
from .entity_dossier_v2 import safe_dossier_path
from .evidence_intake import attachment_manifest_for_export
from .evidence_intake import build_attachment_zip
from .evidence_intake import evidence_intake_payload
from .evidence_custody import chain_of_custody_report
from .evidence_custody import custody_payload
from .evidence_custody import record_custody_event
from .evidence_custody import verify_all_evidence
from .evidence_integrity import build_custody_export_pack
from .evidence_integrity import integrity_dashboard_payload
from .evidence_integrity import safe_integrity_pack_path
from .evidence_links import evidence_links_payload
from .evidence_links import link_evidence_to_review_item
from .evidence_links import review_item_attachment_map
from .evidence_links import unlink_evidence_from_review_item
from .evidence_intake import intake_evidence_file
from .evidence_intake import safe_evidence_path
from .report_export_center import load_manifest_view
from .report_export_center import safe_export_artifact_path
from .report_export_center import export_zip_bundle_payload
from .report_export_center import safe_export_bundle_path
from .report_export_center import review_gated_export_payload
from .report_review import bulk_set_review_status
from .report_review import review_audit_payload
from .report_review import set_review_status
from .workbench import create_workbench_job
from .workbench import evaluate_policy
from .workbench import list_workbench_jobs_payload
from .workbench import policy_events_payload
from .workbench import run_next_workbench_job
from .workbench import run_retention
from .workbench import run_workbench_job
from .workbench import workbench_status
from .dossier_export import export_dossier as run_dossier_export
from .contradictions import contradiction_payload
from .contradictions import detect_subject_contradictions
from .contradictions import resolve_contradiction
from .evidence import assertion_review_queue
from .evidence import connector_quality_metrics
from .evidence import get_assertion_evidence
from .account_discovery import account_discovery_queue
from .account_discovery import ingest_account_discoveries
from .account_discovery import review_account_discovery
from .identity_graph import apply_merge_candidate
from .identity_graph import build_identity_graph
from .identity_graph import graph_payload
from .enrichment import enrich_subject_media_profiles
from .enrichment import enrichment_review_queue
from .enrichment import media_profile_payload
from .enrichment import review_enrichment_finding
from .spine import build_dossier
from .spine import create_subject as spine_create_subject
from .spine import run_spine_for_subject
from .jobs import cancel_scan_job
from .jobs import requeue_scan_job
from .jobs import scan_job_health
from .high_end_workflows import add_case_event as high_end_add_case_event
from .high_end_workflows import analyst_workbench_payload as high_end_workbench
from .high_end_workflows import build_export_bundle as high_end_export_bundle
from .high_end_workflows import build_export_manifest as high_end_export_manifest
from .high_end_workflows import capture_automation_plan
from .high_end_workflows import capture_browser_snapshot
from .high_end_workflows import capture_snapshot
from .high_end_workflows import case_payload as high_end_case_payload
from .high_end_workflows import connector_marketplace_payload
from .high_end_workflows import create_case as high_end_create_case
from .high_end_workflows import entity_resolution_lab_payload
from .high_end_workflows import gate_action
from .high_end_workflows import graph_canvas_payload
from .high_end_workflows import list_capture_artifacts
from .high_end_workflows import list_cases as high_end_list_cases
from .high_end_workflows import load_scope as high_end_load_scope
from .high_end_workflows import policy_events_payload as high_end_policy_events
from .high_end_workflows import save_scope as high_end_save_scope
from .high_end_workflows import scope_review
from .high_end_workflows import update_case as high_end_update_case
from .high_end_workflows import verify_capture
from .high_end_workflows import verify_export_bundle

COMMON_PASSWORDS = {
    "password",
    "password123",
    "qwerty123",
    "letmein",
    "admin123",
    "socmint123",
    "changeme",
}
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS = 5
SIGNUP_WINDOW_SECONDS = 60 * 60
SIGNUP_MAX_ATTEMPTS = 3
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
logger = logging.getLogger(__name__)

dashboard_bp = Blueprint(
    "dashboard", __name__, template_folder="templates", static_folder="static"
)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not session.get("is_admin"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def run_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("dashboard.login"))
        if not (session.get("is_admin") or session.get("role") == "analyst"):
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def init_default_user(settings):
    if (
        settings.admin_user
        and settings.admin_password
        and not db.get_user_by_username(settings.admin_user)
    ):
        db.create_user(settings.admin_user, settings.admin_password, is_admin=True)


def validate_password_strength(password):
    if len(password) < 12:
        return "Password must be at least 12 characters long."
    if password.lower() in COMMON_PASSWORDS:
        return "Password is too common."
    checks = [
        (r"[a-z]", "lowercase letter"),
        (r"[A-Z]", "uppercase letter"),
        (r"\d", "number"),
        (r"[^A-Za-z0-9]", "symbol"),
    ]
    missing = [label for pattern, label in checks if not re.search(pattern, password)]
    if missing:
        return "Password must include at least one " + ", one ".join(missing) + "."
    return None


def validate_username(username):
    if not USERNAME_RE.fullmatch(username):
        return (
            "Username must be 3-64 characters using letters, numbers, dot, dash, "
            "or underscore."
        )
    return None


def csrf_token():
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def csrf_protect():
    if request.method != "POST":
        return None
    expected = session.get("_csrf_token")
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400)
    return None


def csp_nonce():
    nonce = getattr(g, "csp_nonce", None)
    if not nonce:
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce
    return nonce


def init_request_security():
    supplied_request_id = request.headers.get("X-Request-ID", "").strip()
    g.request_id = supplied_request_id[:128] or uuid.uuid4().hex
    g.request_started_at = time.perf_counter()
    csp_nonce()
    return None


def rate_limit_key(username=None):
    identity = username.lower() if username else "anonymous"
    return f"{request.remote_addr or 'unknown'}:{identity}"


def is_rate_limited(action, key, max_attempts, window_seconds):
    return (
        db.count_recent_rate_limit_attempts(action, key, window_seconds) >= max_attempts
    )


def record_rate_limited_action(action, key):
    db.record_rate_limit_attempt(action, key)


def clear_rate_limited_action(action, key):
    db.clear_rate_limit_attempts(action, key)


def audit(action, target=None, details=None, actor=None):
    db.record_audit_event(
        action=action,
        actor=actor if actor is not None else session.get("user"),
        target=target,
        ip_address=request.remote_addr,
        details=details,
    )


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        key = rate_limit_key(username)
        if not username or not password:
            flash("Username and password are required.", "error")
        elif validate_username(username):
            flash("Invalid username or password.", "error")
        elif is_rate_limited("login", key, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS):
            flash("Too many failed login attempts. Try again later.", "error")
        else:
            user = db.authenticate_user(username, password)
            if user:
                clear_rate_limited_action("login", key)
                session["user"] = username
                session["is_admin"] = bool(user.is_admin)
                session["role"] = user.role
                audit("login_success", actor=username)
                flash("Login successful.", "success")
                return redirect(url_for("dashboard.index"))
            record_rate_limited_action("login", key)
            audit("login_failure", actor=username)
            flash("Invalid username or password.", "error")
    return render_template("login.html")


@dashboard_bp.route("/signup", methods=["GET", "POST"])
def signup():
    settings = load_settings()
    if not settings.allow_signup:
        abort(404)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()
        key = rate_limit_key()

        if is_rate_limited("signup", key, SIGNUP_MAX_ATTEMPTS, SIGNUP_WINDOW_SECONDS):
            flash("Too many signup attempts. Try again later.", "error")
        else:
            record_rate_limited_action("signup", key)
            if not username or not password:
                flash("Username and password are required.", "error")
            elif username_error := validate_username(username):
                flash(username_error, "error")
            elif password != confirm:
                flash("Password and confirmation do not match.", "error")
            elif settings.signup_invite_code and not secrets.compare_digest(
                settings.signup_invite_code,
                request.form.get("invite_code", "").strip(),
            ):
                flash("Valid invite code is required.", "error")
            else:
                password_error = validate_password_strength(password)
                if password_error:
                    flash(password_error, "error")
                elif db.get_user_by_username(username):
                    flash("Username is already taken.", "error")
                else:
                    db.create_user(username, password, is_admin=False, role="viewer")
                    session["user"] = username
                    session["is_admin"] = False
                    session["role"] = "viewer"
                    audit(
                        "signup_success",
                        actor=username,
                        details={"invite_required": bool(settings.signup_invite_code)},
                    )
                    flash("Account created successfully.", "success")
                    return redirect(url_for("dashboard.index"))
    return render_template(
        "signup.html", invite_required=bool(settings.signup_invite_code)
    )


@dashboard_bp.route("/logout")
def logout():
    audit("logout")
    session.pop("user", None)
    session.pop("is_admin", None)
    session.pop("role", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("dashboard.login"))


@dashboard_bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm", "")
        if new_password != confirm:
            flash("Password and confirmation do not match.", "error")
        elif password_error := validate_password_strength(new_password):
            flash(password_error, "error")
        elif db.change_user_password(session["user"], current_password, new_password):
            audit("password_change")
            flash("Password changed.", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash("Current password is incorrect.", "error")
    return render_template("change_password.html")


@dashboard_bp.route("/")
@login_required
def index():
    session_db = db.Session()
    targets = session_db.query(db.Target).order_by(db.Target.created_at.desc()).all()
    session_db.close()
    product_readiness = None
    try:
        from .product_control_center import release_readiness

        product_readiness = release_readiness()
    except Exception as exc:
        product_readiness = {
            "status": "warn",
            "recommended_next_action": "Product readiness check unavailable.",
            "warnings": [str(exc)],
            "blockers": [],
        }
    return render_template(
        "dashboard.html",
        targets=targets,
        product_readiness=product_readiness,
    )


@dashboard_bp.route("/target/run", methods=["POST"])
@run_required
def run_target():
    from .main import detect_type, validate_target

    target = request.form.get("target", "").strip()
    tools = request.form.get("tools", "").strip()
    enrich = request.form.get("enrich") == "1"
    try:
        target = validate_target(target)
        target_type = detect_type(target)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("dashboard.index"))

    enabled_tools = {tool.strip() for tool in tools.split(",") if tool.strip()}
    job = db.create_scan_job(
        target,
        target_type,
        tools=enabled_tools,
        enrich=enrich,
        requested_by=session.get("user"),
    )
    audit(
        "dossier_queued",
        details={"target": target, "tools": sorted(enabled_tools), "enrich": enrich},
    )
    flash(f"Queued dossier job {job.id} for {target}.", "success")
    return redirect(url_for("dashboard.jobs"))


@dashboard_bp.route("/jobs")
@login_required
def jobs():
    jobs = db.list_scan_jobs(limit=100)
    return render_template("jobs.html", jobs=jobs, health=scan_job_health())


@dashboard_bp.route("/analyst/console")
@login_required
def analyst_console():
    payload = high_end_workbench(limit=100)
    return render_template("analyst_console.html", payload=payload)


@dashboard_bp.route("/evidence/capture", methods=["GET", "POST"])
@run_required
def high_end_capture_view():
    if request.method == "POST":
        try:
            if request.form.get("mode") == "browser":
                result = capture_browser_snapshot(
                    request.form.get("url", ""),
                    html=request.form.get("html") or None,
                    case_key=request.form.get("case_key") or None,
                    subject_id=request.form.get("subject_id", type=int),
                    actor=session.get("user"),
                    use_playwright=request.form.get("use_playwright") == "1",
                )
            else:
                result = capture_snapshot(
                    request.form.get("url", ""),
                    request.form.get("html", ""),
                    case_key=request.form.get("case_key") or None,
                    subject_id=request.form.get("subject_id", type=int),
                    actor=session.get("user"),
                )
            audit("evidence_capture", details=result)
            flash("Evidence capture stored.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("dashboard.high_end_capture_view"))
    return render_template(
        "evidence_capture.html",
        captures=list_capture_artifacts(),
        plan=capture_automation_plan(request.args.get("url", "")),
        scope=high_end_load_scope(),
    )


@dashboard_bp.route("/cases", methods=["GET", "POST"])
@login_required
def cases_view():
    if request.method == "POST":
        tags = [
            item.strip()
            for item in request.form.get("tags", "").split(",")
            if item.strip()
        ]
        result = high_end_create_case(
            request.form.get("title", "Untitled case"),
            case_key=request.form.get("case_key") or None,
            tags=tags,
            actor=session.get("user"),
        )
        audit("case_create", details={"case_key": result["case_key"]})
        return redirect(url_for("dashboard.case_detail_view", case_key=result["case_key"]))
    return render_template("cases.html", cases=high_end_list_cases())


@dashboard_bp.route("/cases/<case_key>", methods=["GET", "POST"])
@login_required
def case_detail_view(case_key):
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "update":
            high_end_update_case(
                case_key,
                actor=session.get("user"),
                priority=request.form.get("priority"),
                review_state=request.form.get("review_state"),
                due_at=request.form.get("due_at") or None,
            )
        else:
            high_end_add_case_event(
                case_key,
                action or "note",
                actor=session.get("user"),
                subject_id=request.form.get("subject_id", type=int),
                note=request.form.get("note"),
                comment=request.form.get("comment"),
                assignee=request.form.get("assignee"),
            )
        audit("case_update", details={"case_key": case_key, "action": action})
        return redirect(url_for("dashboard.case_detail_view", case_key=case_key))
    return render_template("case_detail.html", case=high_end_case_payload(case_key))


@dashboard_bp.route("/connectors/marketplace")
@login_required
def connector_marketplace_view():
    return render_template(
        "connector_marketplace.html",
        payload=connector_marketplace_payload(),
    )


@dashboard_bp.route("/responsible-use", methods=["GET", "POST"])
@login_required
def responsible_use_view():
    if request.method == "POST":
        payload = {
            "authorization_banner": request.form.get("authorization_banner"),
            "allowed_targets": [
                item.strip()
                for item in request.form.get("allowed_targets", "").splitlines()
                if item.strip()
            ],
            "blocked_targets": [
                item.strip()
                for item in request.form.get("blocked_targets", "").splitlines()
                if item.strip()
            ],
            "sensitive_redaction_default": request.form.get("redaction") == "1",
            "export_warning": request.form.get("export_warning"),
        }
        high_end_save_scope(payload, actor=session.get("user"))
        audit("responsible_use_scope_update", details=payload)
        return redirect(url_for("dashboard.responsible_use_view"))
    return render_template(
        "responsible_use.html",
        scope=high_end_load_scope(),
        policy=high_end_policy_events(),
    )


@dashboard_bp.route("/exports/builder", methods=["GET", "POST"])
@login_required
def export_builder_view():
    bundle = None
    if request.method == "POST":
        try:
            bundle = high_end_export_bundle(
                subject_id=request.form.get("subject_id", type=int),
                case_key=request.form.get("case_key") or None,
                redacted=request.form.get("redacted") == "1",
                redaction_preset=request.form.get("redaction_preset") or "client",
                actor=session.get("user"),
            )
            audit("high_end_export_bundle", details=bundle)
            flash("Export bundle built.", "success")
        except Exception as exc:
            flash(str(exc), "error")
    return render_template(
        "export_builder.html",
        manifest=high_end_export_manifest(
            subject_id=request.args.get("subject_id", type=int),
            case_key=request.args.get("case_key") or None,
            actor=session.get("user"),
        ),
        bundle=bundle,
    )


@dashboard_bp.route("/spine/<int:subject_id>/graph/canvas")
@login_required
def graph_canvas_view(subject_id):
    return render_template(
        "graph_canvas.html",
        payload=graph_canvas_payload(subject_id),
    )


@dashboard_bp.route("/spine/<int:subject_id>/resolution-lab")
@login_required
def resolution_lab_view(subject_id):
    return render_template(
        "entity_resolution_lab.html",
        payload=entity_resolution_lab_payload(subject_id),
    )


@dashboard_bp.route("/api/v1/analyst/workbench")
@login_required
def api_high_end_workbench():
    return jsonify(high_end_workbench(limit=request.args.get("limit", 100, type=int)))


@dashboard_bp.route("/api/v1/evidence/capture", methods=["POST"])
@run_required
def api_high_end_capture():
    payload = request.get_json(silent=True) or {}
    capture_fn = capture_browser_snapshot if payload.get("mode") == "browser" else capture_snapshot
    kwargs = {
        "case_key": payload.get("case_key"),
        "subject_id": payload.get("subject_id"),
        "actor": session.get("user"),
    }
    if capture_fn is capture_browser_snapshot:
        kwargs["use_playwright"] = bool(payload.get("use_playwright"))
        kwargs["html"] = payload.get("html")
        result = capture_fn(payload.get("url", ""), **kwargs)
    else:
        result = capture_fn(
            payload.get("url", ""),
            payload.get("html", ""),
            **kwargs,
        )
    return jsonify(result), 201


@dashboard_bp.route("/api/v1/evidence/captures")
@login_required
def api_high_end_captures():
    return jsonify({"captures": list_capture_artifacts()})


@dashboard_bp.route("/api/v1/evidence/captures/<capture_id>/verify")
@login_required
def api_high_end_capture_verify(capture_id):
    return jsonify(verify_capture(capture_id))


@dashboard_bp.route("/api/v1/cases")
@login_required
def api_high_end_cases():
    return jsonify({"cases": high_end_list_cases()})


@dashboard_bp.route("/api/v1/cases/<case_key>")
@login_required
def api_high_end_case(case_key):
    return jsonify(high_end_case_payload(case_key))


@dashboard_bp.route("/api/v1/connectors/marketplace")
@login_required
def api_connector_marketplace():
    return jsonify(connector_marketplace_payload())


@dashboard_bp.route("/api/v1/responsible-use/scope", methods=["GET", "PUT"])
@login_required
def api_responsible_use_scope():
    if request.method == "PUT":
        return jsonify(high_end_save_scope(request.get_json(silent=True) or {}))
    return jsonify(high_end_load_scope())


@dashboard_bp.route("/api/v1/responsible-use/review")
@login_required
def api_scope_review():
    return jsonify(scope_review(request.args.get("target", "")))


@dashboard_bp.route("/api/v1/responsible-use/gate", methods=["POST"])
@login_required
def api_gate_action():
    payload = request.get_json(silent=True) or {}
    return jsonify(
        gate_action(
            payload.get("action", "review"),
            payload.get("target", ""),
            actor=session.get("user"),
        )
    )


@dashboard_bp.route("/api/v1/exports/builder")
@login_required
def api_export_builder():
    return jsonify(
        high_end_export_manifest(
            subject_id=request.args.get("subject_id", type=int),
            case_key=request.args.get("case_key") or None,
            actor=session.get("user"),
        )
    )


@dashboard_bp.route("/api/v1/exports/builder/bundle", methods=["POST"])
@login_required
def api_export_builder_bundle():
    payload = request.get_json(silent=True) or {}
    return jsonify(
        high_end_export_bundle(
            subject_id=payload.get("subject_id"),
            case_key=payload.get("case_key"),
            redacted=bool(payload.get("redacted", True)),
            redaction_preset=payload.get("redaction_preset") or "client",
            actor=session.get("user"),
        )
    ), 201


@dashboard_bp.route("/api/v1/exports/builder/bundles/<path:name>/verify")
@login_required
def api_export_builder_bundle_verify(name):
    return jsonify(verify_export_bundle(name))


@dashboard_bp.route("/api/v1/spine/<int:subject_id>/graph/canvas")
@login_required
def api_graph_canvas(subject_id):
    return jsonify(graph_canvas_payload(subject_id))


@dashboard_bp.route("/api/v1/spine/<int:subject_id>/resolution-lab")
@login_required
def api_resolution_lab(subject_id):
    return jsonify(entity_resolution_lab_payload(subject_id))


@dashboard_bp.route("/api/v1/jobs/health")
@login_required
def api_jobs_health():
    return jsonify(scan_job_health())


@dashboard_bp.route("/api/v1/jobs/<int:job_id>/requeue", methods=["POST"])
@admin_required
def api_jobs_requeue(job_id):
    result = requeue_scan_job(job_id)
    audit("scan_job_requeue", details=result)
    return jsonify(result), 202


@dashboard_bp.route("/api/v1/jobs/<int:job_id>/cancel", methods=["POST"])
@admin_required
def api_jobs_cancel(job_id):
    payload = request.get_json(silent=True) or {}
    result = cancel_scan_job(job_id, reason=payload.get("reason") or "Canceled by operator.")
    audit("scan_job_cancel", details=result)
    return jsonify(result), 202


@dashboard_bp.route("/admin/audit")
@admin_required
def audit_log():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 25
    actor = request.args.get("actor", "").strip() or None
    action = request.args.get("action", "").strip() or None
    total = db.count_audit_events(actor=actor, action=action)
    events = db.get_audit_events(
        limit=per_page,
        offset=(page - 1) * per_page,
        actor=actor,
        action=action,
    )
    pages = max((total + per_page - 1) // per_page, 1)
    return render_template(
        "audit.html",
        events=events,
        actor=actor or "",
        action=action or "",
        page=page,
        pages=pages,
        total=total,
    )


@dashboard_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        is_admin = request.form.get("is_admin") == "1"
        role = request.form.get("role", "viewer")
        if username_error := validate_username(username):
            flash(username_error, "error")
        elif password_error := validate_password_strength(password):
            flash(password_error, "error")
        elif role not in {"viewer", "analyst", "admin"}:
            flash("Invalid role.", "error")
        elif db.get_user_by_username(username):
            flash("Username is already taken.", "error")
        else:
            db.create_user(
                username,
                password,
                is_admin=is_admin or role == "admin",
                role="admin" if is_admin else role,
            )
            audit(
                "user_create",
                details={
                    "username": username,
                    "is_admin": is_admin,
                    "role": "admin" if is_admin else role,
                },
            )
            flash(f"Created user {username}.", "success")
            return redirect(url_for("dashboard.admin_users"))

    users = db.list_users()
    return render_template("admin_users.html", users=users)


@dashboard_bp.route("/admin/users/<int:user_id>", methods=["POST"])
@admin_required
def update_admin_user(user_id):
    current_username = session.get("user")
    target_user = None
    for user in db.list_users():
        if user.id == user_id:
            target_user = user
            break
    if not target_user:
        abort(404)

    is_self = target_user.username == current_username
    password = request.form.get("password", "").strip()
    is_admin = request.form.get("is_admin") == "1"
    is_active = request.form.get("is_active") == "1"
    role = request.form.get("role", "viewer")
    if is_self and (not is_admin or not is_active):
        flash("You cannot remove your own admin or active status.", "error")
        return redirect(url_for("dashboard.admin_users"))
    if role not in {"viewer", "analyst", "admin"}:
        flash("Invalid role.", "error")
        return redirect(url_for("dashboard.admin_users"))
    if password and (password_error := validate_password_strength(password)):
        flash(password_error, "error")
        return redirect(url_for("dashboard.admin_users"))

    db.update_user(
        user_id,
        is_admin=is_admin,
        is_active=is_active,
        password=password or None,
        role="admin" if is_admin else role,
    )
    audit(
        "user_update",
        details={
            "username": target_user.username,
            "is_admin": is_admin,
            "role": "admin" if is_admin else role,
            "is_active": is_active,
            "password_rotated": bool(password),
        },
    )
    flash(f"Updated user {target_user.username}.", "success")
    return redirect(url_for("dashboard.admin_users"))


@dashboard_bp.route("/target/<int:target_id>")
@login_required
def target_detail(target_id):
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(id=target_id).first()
    if not target:
        session_db.close()
        return redirect(url_for("dashboard.index"))

    profile_records = session_db.query(db.Profile).filter_by(target_id=target.id).all()
    media_records = session_db.query(db.Media).filter_by(target_id=target.id).all()
    session_db.close()

    profiles = []
    for profile in profile_records:
        profiles.append(
            {
                "source": profile.source,
                "raw": json.loads(profile.raw or "{}"),
                "normalized": json.loads(profile.normalized or "{}"),
            }
        )

    media_items = []
    for media in media_records:
        filename = os.path.basename(media.path or "")
        media_items.append(
            {
                "source_url": media.source_url,
                "path": media.path,
                "filename": filename,
                "checksum": media.checksum,
                "content_type": media.content_type,
                "download_url": url_for(
                    "dashboard.media_file", media_id=media.id, filename=filename
                ),
            }
        )

    return render_template(
        "detail.html", target=target, profiles=profiles, media=media_items
    )


@dashboard_bp.route("/target/<int:target_id>/export")
@admin_required
def export_dossier(target_id):
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(id=target_id).first()
    if not target:
        session_db.close()
        abort(404)
    target_value = target.value
    session_db.expunge(target)
    session_db.close()

    dossier = db.get_dossier(target_value)
    if not dossier:
        abort(404)
    audit("dossier_export", target=target)
    response = jsonify(dossier)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{target_value}_dossier.json"'
    )
    return response


@dashboard_bp.route("/target/<int:target_id>/delete", methods=["POST"])
@admin_required
def delete_dossier(target_id):
    session_db = db.Session()
    target = session_db.query(db.Target).filter_by(id=target_id).first()
    if not target:
        session_db.close()
        abort(404)
    snapshot = {"id": target.id, "value": target.value, "type": target.type}
    if request.form.get("confirm_target", "").strip() != target.value:
        session_db.close()
        flash("Type the target name to confirm deletion.", "error")
        return redirect(url_for("dashboard.target_detail", target_id=target_id))
    audit("dossier_delete", target=target)
    session_db.close()
    db.delete_dossier(target_id)
    flash(f"Deleted dossier for {snapshot['value']}.", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/media/<int:media_id>/<path:filename>")
@login_required
def media_file(media_id, filename):
    settings = load_settings()
    session_db = db.Session()
    media = session_db.query(db.Media).filter_by(id=media_id).first()
    session_db.close()
    if not media or not media.path:
        abort(404)

    stored_directory = os.path.dirname(os.path.abspath(media.path))
    media_root = os.path.abspath(settings.media_dir)
    if not stored_directory.startswith(media_root + os.sep):
        abort(404)

    safe_path = safe_join(stored_directory, filename)
    if not safe_path or os.path.abspath(safe_path) != os.path.abspath(media.path):
        abort(404)
    return send_from_directory(stored_directory, filename)



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



@dashboard_bp.route("/spine/assertions/<int:assertion_id>")
@login_required
def spine_assertion_detail(assertion_id):
    evidence = get_assertion_evidence(assertion_id)
    if not evidence:
        abort(404)
    return render_template("spine_assertion.html", evidence=evidence)


@dashboard_bp.route("/api/v1/spine/assertions/<int:assertion_id>")
@login_required
def api_spine_assertion_detail(assertion_id):
    evidence = get_assertion_evidence(assertion_id)
    if not evidence:
        abort(404)
    return jsonify(evidence)


@dashboard_bp.route("/spine/connectors/quality")
@login_required
def spine_connector_quality():
    metrics = connector_quality_metrics()
    return render_template("spine_connector_quality.html", metrics=metrics)


@dashboard_bp.route("/api/v1/spine/connectors/quality")
@login_required
def api_spine_connector_quality():
    return jsonify({"connectors": connector_quality_metrics()})


@dashboard_bp.route("/api/v1/spine/assertions/review-queue")
@login_required
def api_spine_assertion_review_queue():
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    return jsonify({"assertions": assertion_review_queue(limit=limit)})


@dashboard_bp.route("/spine/subjects/<int:subject_id>/account-discovery")
@login_required
def spine_account_discovery_view(subject_id):
    return render_template(
        "spine_account_discovery.html",
        payload=account_discovery_queue(
            subject_id=subject_id,
            review_state=request.args.get("state", "unreviewed") or None,
        ),
        subject_id=subject_id,
    )


@dashboard_bp.route(
    "/spine/subjects/<int:subject_id>/account-discovery/ingest",
    methods=["POST"],
)
@run_required
def spine_account_discovery_ingest(subject_id):
    result = ingest_account_discoveries(
        subject_id,
        actor=session.get("user"),
        capture_profiles=request.form.get("capture_profiles") == "1",
    )
    audit("account_discovery_ingest", details=result)
    flash(f"Ingested {result['discovery_count']} account discoveries.", "success")
    return redirect(
        url_for("dashboard.spine_account_discovery_view", subject_id=subject_id)
    )


@dashboard_bp.route(
    "/spine/account-discovery/<int:discovery_id>/review",
    methods=["POST"],
)
@run_required
def spine_account_discovery_review(discovery_id):
    result = review_account_discovery(
        discovery_id,
        request.form.get("action", "unreviewed"),
        actor=session.get("user"),
        note=request.form.get("note"),
        promote=request.form.get("promote") == "1",
    )
    audit("account_discovery_review", details=result)
    flash("Account discovery reviewed.", "success")
    return redirect(request.referrer or url_for("dashboard.spine_subjects"))


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/account-discovery")
@login_required
def api_spine_account_discovery(subject_id):
    return jsonify(
        account_discovery_queue(
            subject_id=subject_id,
            review_state=request.args.get("state", "unreviewed") or None,
            limit=request.args.get("limit", 500, type=int),
        )
    )


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/account-discovery/ingest",
    methods=["POST"],
)
@run_required
def api_spine_account_discovery_ingest(subject_id):
    payload = request.get_json(silent=True) or {}
    return jsonify(
        ingest_account_discoveries(
            subject_id,
            actor=session.get("user"),
            capture_profiles=bool(payload.get("capture_profiles", True)),
        )
    ), 201


@dashboard_bp.route(
    "/api/v1/spine/account-discovery/<int:discovery_id>/review",
    methods=["POST"],
)
@run_required
def api_spine_account_discovery_review(discovery_id):
    payload = request.get_json(silent=True) or {}
    return jsonify(
        review_account_discovery(
            discovery_id,
            payload.get("action", "unreviewed"),
            actor=session.get("user"),
            note=payload.get("note"),
            promote=bool(payload.get("promote")),
        )
    )



@dashboard_bp.route("/spine/<int:subject_id>/graph")
@login_required
def spine_graph_view(subject_id):
    payload = graph_payload(subject_id)
    return render_template("spine_graph.html", graph=payload)


@dashboard_bp.route("/spine/<int:subject_id>/graph/build", methods=["POST"])
@run_required
def spine_graph_build(subject_id):
    try:
        graph_id = build_identity_graph(subject_id)
        audit("spine_graph_build", details={"graph_id": graph_id})
        flash(f"Built identity graph {graph_id}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.spine_graph_view", subject_id=subject_id))


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/graph")
@login_required
def api_spine_graph(subject_id):
    return jsonify(graph_payload(subject_id))


@dashboard_bp.route(
    "/spine/merge-candidates/<int:candidate_id>/review",
    methods=["POST"],
)
@run_required
def spine_merge_candidate_review(candidate_id):
    action = request.form.get("action", "unreviewed").strip()
    note = request.form.get("note", "").strip() or None
    try:
        apply_merge_candidate(
            candidate_id,
            action,
            actor=session.get("user"),
            note=note,
        )
        audit(
            "spine_merge_candidate_review",
            details={"candidate_id": candidate_id, "action": action},
        )
        flash(f"Merge candidate marked {action}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("dashboard.spine_subjects"))



@dashboard_bp.route("/spine/<int:subject_id>/media-profiles")
@login_required
def spine_media_profile_view(subject_id):
    payload = media_profile_payload(subject_id)
    return render_template("spine_media_profiles.html", payload=payload)


@dashboard_bp.route("/spine/enrichment-review")
@run_required
def spine_enrichment_review():
    subject_id = request.args.get("subject_id", type=int)
    payload = enrichment_review_queue(subject_id=subject_id)
    return render_template("spine_enrichment_review.html", payload=payload)


@dashboard_bp.route(
    "/spine/enrichments/<int:enrichment_id>/findings/<int:finding_index>/review",
    methods=["POST"],
)
@run_required
def spine_enrichment_finding_review(enrichment_id, finding_index):
    action = request.form.get("action", "").strip()
    note = request.form.get("note", "").strip() or None
    try:
        result = review_enrichment_finding(
            enrichment_id,
            finding_index,
            action,
            actor=session.get("user"),
            note=note,
        )
        audit("spine_enrichment_finding_review", details=result)
        flash(f"Enrichment finding marked {action}.", "success")
        if result.get("contradiction_ids"):
            flash("Contradictions were refreshed after promotion.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("dashboard.spine_enrichment_review"))


@dashboard_bp.route("/spine/<int:subject_id>/media-profiles/run", methods=["POST"])
@run_required
def spine_media_profile_run(subject_id):
    try:
        result = enrich_subject_media_profiles(subject_id)
        audit("spine_media_profile_enrichment", details=result)
        flash(
            f"Created {len(result['enrichment_ids'])} enrichment records.",
            "success",
        )
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(
        url_for(
            "dashboard.spine_media_profile_view",
            subject_id=subject_id,
        )
    )


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/media-profiles"
)
@login_required
def api_spine_media_profiles(subject_id):
    payload = media_profile_payload(subject_id)
    return jsonify(payload)


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/media-profiles/run",
    methods=["POST"],
)
@run_required
def api_spine_media_profiles_run(subject_id):
    payload = enrich_subject_media_profiles(subject_id)
    return jsonify(payload), 202


@dashboard_bp.route("/api/v1/spine/enrichment-review")
@run_required
def api_spine_enrichment_review():
    return jsonify(enrichment_review_queue(request.args.get("subject_id", type=int)))


@dashboard_bp.route(
    "/api/v1/spine/enrichments/<int:enrichment_id>/findings/"
    "<int:finding_index>/review",
    methods=["POST"],
)
@run_required
def api_spine_enrichment_finding_review(enrichment_id, finding_index):
    payload = request.get_json(silent=True) or {}
    result = review_enrichment_finding(
        enrichment_id,
        finding_index,
        payload.get("action", ""),
        actor=session.get("user"),
        note=payload.get("note"),
    )
    audit("spine_enrichment_finding_review", details=result)
    return jsonify(result), 202



@dashboard_bp.route("/spine/<int:subject_id>/contradictions")
@login_required
def spine_contradictions_view(subject_id):
    payload = contradiction_payload(subject_id)
    return render_template("spine_contradictions.html", payload=payload)


@dashboard_bp.route("/spine/<int:subject_id>/contradictions/run", methods=["POST"])
@run_required
def spine_contradictions_run(subject_id):
    try:
        result = detect_subject_contradictions(subject_id)
        audit("spine_contradictions_run", details=result)
        flash(
            f"Detected {len(result['contradiction_ids'])} contradictions.",
            "success",
        )
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(
        url_for(
            "dashboard.spine_contradictions_view",
            subject_id=subject_id,
        )
    )


@dashboard_bp.route(
    "/spine/contradictions/<int:contradiction_id>/resolve",
    methods=["POST"],
)
@run_required
def spine_contradiction_resolve(contradiction_id):
    status = request.form.get("status", "open").strip()
    note = request.form.get("note", "").strip() or None
    try:
        resolve_contradiction(
            contradiction_id,
            status,
            actor=session.get("user"),
            note=note,
        )
        audit(
            "spine_contradiction_resolve",
            details={"contradiction_id": contradiction_id, "status": status},
        )
        flash(f"Contradiction marked {status}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(request.referrer or url_for("dashboard.spine_subjects"))


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/contradictions")
@login_required
def api_spine_contradictions(subject_id):
    return jsonify(contradiction_payload(subject_id))


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/contradictions/run",
    methods=["POST"],
)
@run_required
def api_spine_contradictions_run(subject_id):
    return jsonify(detect_subject_contradictions(subject_id)), 202



@dashboard_bp.route("/spine/<int:subject_id>/exports")
@login_required
def spine_exports_view(subject_id):
    exports = db.list_dossier_exports(subject_id)
    return render_template(
        "spine_exports.html",
        subject_id=subject_id,
        exports=exports,
    )


@dashboard_bp.route("/spine/<int:subject_id>/exports/run", methods=["POST"])
@run_required
def spine_exports_run(subject_id):
    formats = request.form.getlist("formats") or ["json", "html", "pdf"]
    try:
        result = run_dossier_export(subject_id, formats=formats)
        audit("spine_dossier_export", details=result)
        flash(
            f"Exported dossier package {result['export_id']}.",
            "success",
        )
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.spine_exports_view", subject_id=subject_id))


@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/exports")
@login_required
def api_spine_exports(subject_id):
    exports = db.list_dossier_exports(subject_id)
    return jsonify(
        {
            "subject_id": subject_id,
            "exports": [
                {
                    "id": item.id,
                    "export_dir": item.export_dir,
                    "files": json.loads(item.files_json or "[]"),
                    "created_at": item.created_at.isoformat()
                    if item.created_at
                    else None,
                }
                for item in exports
            ],
        }
    )


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/exports/run",
    methods=["POST"],
)
@run_required
def api_spine_exports_run(subject_id):
    payload = request.get_json(silent=True) or {}
    formats = payload.get("formats") or ["json", "html", "pdf"]
    result = run_dossier_export(subject_id, formats=formats)
    return jsonify(result), 202



@dashboard_bp.route("/workbench/jobs", methods=["GET", "POST"])
@run_required
def workbench_jobs_view():
    if request.method == "POST":
        try:
            subject_id = int(request.form.get("subject_id", "0"))
            job_type = request.form.get("job_type", "").strip()
            priority = int(request.form.get("priority", "100"))
            job_id = create_workbench_job(
                job_type=job_type,
                subject_id=subject_id,
                payload={},
                actor=session.get("user"),
                priority=priority,
            )
            audit("workbench_job_create", details={"job_id": job_id})
            flash(f"Created workbench job {job_id}.", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("dashboard.workbench_jobs_view"))

    return render_template(
        "workbench_jobs.html",
        status=workbench_status(),
        jobs=list_workbench_jobs_payload(limit=100)["jobs"],
    )


@dashboard_bp.route("/workbench/jobs/<int:job_id>/run", methods=["POST"])
@run_required
def workbench_job_run(job_id):
    try:
        result = run_workbench_job(job_id, actor=session.get("user"))
        audit("workbench_job_run", details={"job_id": job_id, "result": result})
        flash(f"Ran workbench job {job_id}.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.workbench_jobs_view"))


@dashboard_bp.route("/workbench/jobs/run-next", methods=["POST"])
@run_required
def workbench_run_next():
    try:
        result = run_next_workbench_job(actor=session.get("user"))
        audit("workbench_run_next", details={"result": result})
        flash("Processed next queued job.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.workbench_jobs_view"))


@dashboard_bp.route("/workbench/policy")
@login_required
def workbench_policy_view():
    return render_template(
        "workbench_policy.html",
        events=policy_events_payload(limit=100)["events"],
    )


@dashboard_bp.route("/workbench/retention/run", methods=["POST"])
@run_required
def workbench_retention_run():
    mode = request.form.get("mode", "dry_run").strip()
    try:
        result = run_retention(mode=mode, actor=session.get("user"))
        audit("workbench_retention_run", details=result)
        flash(f"Retention run {result['retention_run_id']} completed.", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("dashboard.workbench_policy_view"))


@dashboard_bp.route("/api/v1/workbench/status")
@login_required
def api_workbench_status():
    return jsonify(workbench_status())


@dashboard_bp.route("/api/v1/workbench/jobs")
@login_required
def api_workbench_jobs():
    return jsonify(list_workbench_jobs_payload(limit=250))


@dashboard_bp.route("/api/v1/workbench/jobs", methods=["POST"])
@run_required
def api_workbench_job_create():
    payload = request.get_json(silent=True) or {}
    job_id = create_workbench_job(
        job_type=payload.get("job_type"),
        subject_id=int(payload.get("subject_id")),
        payload=payload.get("payload") or {},
        actor=session.get("user"),
        priority=int(payload.get("priority", 100)),
    )
    return jsonify({"job_id": job_id}), 201


@dashboard_bp.route("/api/v1/workbench/jobs/<int:job_id>/run", methods=["POST"])
@run_required
def api_workbench_job_run(job_id):
    return jsonify(run_workbench_job(job_id, actor=session.get("user"))), 202


@dashboard_bp.route("/api/v1/workbench/jobs/run-next", methods=["POST"])
@run_required
def api_workbench_run_next():
    return jsonify({"result": run_next_workbench_job(actor=session.get("user"))})


@dashboard_bp.route("/api/v1/workbench/policy/evaluate", methods=["POST"])
@run_required
def api_workbench_policy_evaluate():
    payload = request.get_json(silent=True) or {}
    result = evaluate_policy(
        payload.get("action", ""),
        payload.get("payload") or {},
        actor=session.get("user"),
    )
    return jsonify(result)


@dashboard_bp.route("/api/v1/workbench/policy/events")
@login_required
def api_workbench_policy_events():
    return jsonify(policy_events_payload(limit=250))


@dashboard_bp.route("/api/v1/workbench/retention/run", methods=["POST"])
@run_required
def api_workbench_retention_run():
    payload = request.get_json(silent=True) or {}
    result = run_retention(
        mode=payload.get("mode", "dry_run"),
        actor=session.get("user"),
    )
    return jsonify(result), 202






















@dashboard_bp.route("/api/v1/spine/subjects/<int:subject_id>/dossier-v2")
@login_required
def api_subject_dossier_v2(subject_id):
    return jsonify(build_full_entity_dossier_v2(subject_id))


@dashboard_bp.route(
    "/api/v1/spine/subjects/<int:subject_id>/dossier-v2/export",
    methods=["POST"],
)
@run_required
def api_subject_dossier_v2_export(subject_id):
    result = export_full_entity_dossier_v2(subject_id)
    audit(
        "full_entity_dossier_v2_export",
        details={"subject_id": subject_id, "zip_path": result.get("zip_path")},
    )
    return jsonify(result), 202


@dashboard_bp.route("/spine/subjects/<int:subject_id>/dossier")
@login_required
def subject_dossier_v2_view(subject_id):
    return render_template(
        "entity_dossier_v2.html",
        payload=build_full_entity_dossier_v2(subject_id),
    )


@dashboard_bp.route(
    "/spine/subjects/<int:subject_id>/dossier-v2/export/run",
    methods=["POST"],
)
@run_required
def subject_dossier_v2_export_run(subject_id):
    result = export_full_entity_dossier_v2(subject_id)
    flash("Dossier v2 export complete: " + str(result.get("zip_path")), "success")
    return redirect(
        url_for("dashboard.subject_dossier_v2_view", subject_id=subject_id)
    )


@dashboard_bp.route(
    "/spine/subjects/<int:subject_id>/dossier-v2/export/<path:name>/download"
)
@login_required
def subject_dossier_v2_download(subject_id, name):
    path = safe_dossier_path(name)
    return send_from_directory(
        path.parent,
        path.name,
        as_attachment=True,
        download_name=path.name,
    )

@dashboard_bp.route("/evidence/integrity")
@login_required
def evidence_integrity_view():
    case_id = request.args.get("case_id")
    subject_id_raw = request.args.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    return render_template(
        "evidence_integrity.html",
        payload=integrity_dashboard_payload(
            case_id=case_id,
            subject_id=subject_id,
        ),
    )


@dashboard_bp.route("/api/v1/evidence/integrity")
@login_required
def api_evidence_integrity():
    case_id = request.args.get("case_id")
    subject_id_raw = request.args.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    return jsonify(
        integrity_dashboard_payload(
            case_id=case_id,
            subject_id=subject_id,
        )
    )


@dashboard_bp.route("/api/v1/evidence/integrity/pack", methods=["POST"])
@run_required
def api_evidence_integrity_pack():
    payload = request.get_json(silent=True) or {}
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None
    result = build_custody_export_pack(
        case_id=payload.get("case_id"),
        subject_id=subject_id,
        actor=session.get("username"),
    )
    audit("custody_export_pack", details=result)
    return jsonify(result), 202


@dashboard_bp.route("/evidence/integrity/pack/run", methods=["POST"])
@run_required
def evidence_integrity_pack_run():
    case_id = request.form.get("case_id") or None
    subject_id_raw = request.form.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    result = build_custody_export_pack(
        case_id=case_id,
        subject_id=subject_id,
        actor=session.get("username"),
    )
    flash("Custody export pack created: " + str(result.get("zip_path")), "success")
    return redirect(url_for("dashboard.evidence_integrity_view"))


@dashboard_bp.route("/evidence/integrity/packs/<path:name>/download")
@login_required
def evidence_integrity_pack_download(name):
    path = safe_integrity_pack_path(name)
    return send_from_directory(
        path.parent,
        path.name,
        as_attachment=True,
        download_name=path.name,
    )

@dashboard_bp.route("/evidence/custody")
@login_required
def evidence_custody_view():
    evidence_id = request.args.get("evidence_id")
    action = request.args.get("action")
    return render_template(
        "evidence_custody.html",
        payload=custody_payload(evidence_id=evidence_id, action=action),
    )


@dashboard_bp.route("/api/v1/evidence/custody")
@login_required
def api_evidence_custody():
    evidence_id = request.args.get("evidence_id")
    action = request.args.get("action")
    return jsonify(custody_payload(evidence_id=evidence_id, action=action))


@dashboard_bp.route("/api/v1/evidence/custody", methods=["POST"])
@run_required
def api_evidence_custody_add():
    payload = request.get_json(silent=True) or {}
    result = record_custody_event(
        evidence_id=payload.get("evidence_id"),
        action=payload.get("action") or "manual_review",
        actor=session.get("username"),
        sha256=payload.get("sha256"),
        status=payload.get("status"),
        note=payload.get("note"),
        details=payload.get("details") or {},
    )
    audit("evidence_custody_event", details=result)
    return jsonify(result), 201


@dashboard_bp.route("/api/v1/evidence/verify")
@login_required
def api_evidence_verify_report():
    case_id = request.args.get("case_id")
    subject_id_raw = request.args.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    result = verify_all_evidence(
        case_id=case_id,
        subject_id=subject_id,
        actor=session.get("username"),
    )
    return jsonify(result)


@dashboard_bp.route("/evidence/verify/run", methods=["POST"])
@run_required
def evidence_verify_run():
    case_id = request.form.get("case_id") or None
    subject_id_raw = request.form.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    result = verify_all_evidence(
        case_id=case_id,
        subject_id=subject_id,
        actor=session.get("username"),
    )
    flash(
        "Hash verification complete: "
        + str(result.get("markdown_path") or result.get("report_path")),
        "success",
    )
    return redirect(url_for("dashboard.evidence_custody_view"))


@dashboard_bp.route("/api/v1/evidence/custody/report")
@login_required
def api_evidence_custody_report():
    evidence_id = request.args.get("evidence_id")
    return jsonify(chain_of_custody_report(evidence_id=evidence_id))

@dashboard_bp.route("/evidence/links")
@login_required
def evidence_links_view():
    return render_template(
        "evidence_links.html",
        payload=evidence_links_payload(),
    )


@dashboard_bp.route("/api/v1/evidence/links")
@login_required
def api_evidence_links_list():
    review_item_id = request.args.get("review_item_id")
    evidence_id = request.args.get("evidence_id")
    return jsonify(
        evidence_links_payload(
            review_item_id=review_item_id,
            evidence_id=evidence_id,
        )
    )


@dashboard_bp.route("/api/v1/evidence/links", methods=["POST"])
@run_required
def api_evidence_links_add():
    payload = request.get_json(silent=True) or {}
    result = link_evidence_to_review_item(
        evidence_id=payload.get("evidence_id"),
        review_item_id=payload.get("review_item_id"),
        relation=payload.get("relation") or "supports",
        confidence=payload.get("confidence"),
        note=payload.get("note"),
        created_by=session.get("username"),
    )
    audit("evidence_link_created", details=result)
    return jsonify(result), 201


@dashboard_bp.route("/api/v1/evidence/links/delete", methods=["POST"])
@run_required
def api_evidence_links_delete():
    payload = request.get_json(silent=True) or {}
    result = unlink_evidence_from_review_item(
        evidence_id=payload.get("evidence_id"),
        review_item_id=payload.get("review_item_id"),
        relation=payload.get("relation"),
    )
    audit("evidence_link_deleted", details=result)
    return jsonify(result)


@dashboard_bp.route("/evidence/links/add", methods=["POST"])
@run_required
def evidence_links_add_form():
    result = link_evidence_to_review_item(
        evidence_id=request.form.get("evidence_id"),
        review_item_id=request.form.get("review_item_id"),
        relation=request.form.get("relation") or "supports",
        confidence=(
            float(request.form.get("confidence"))
            if request.form.get("confidence")
            else None
        ),
        note=request.form.get("note") or None,
        created_by=session.get("username"),
    )
    flash("Evidence linked: " + str(result.get("link_id")), "success")
    return redirect(url_for("dashboard.evidence_links_view"))


@dashboard_bp.route("/api/v1/evidence/attachment-map")
@login_required
def api_review_item_attachment_map():
    export_manifest_name = request.args.get("export_manifest_name")
    return jsonify(review_item_attachment_map(export_manifest_name))

@dashboard_bp.route("/evidence/intake")
@login_required
def evidence_intake_view():
    return render_template(
        "evidence_intake.html",
        payload=evidence_intake_payload(),
    )


@dashboard_bp.route("/api/v1/evidence/intake")
@login_required
def api_evidence_intake_list():
    case_id = request.args.get("case_id")
    subject_id_raw = request.args.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    return jsonify(evidence_intake_payload(case_id=case_id, subject_id=subject_id))


@dashboard_bp.route("/api/v1/evidence/intake", methods=["POST"])
@run_required
def api_evidence_intake_add():
    payload = request.get_json(silent=True) or {}
    source_path = payload.get("source_path")
    case_id = payload.get("case_id")
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None
    source_note = payload.get("source_note")

    if not source_path:
        return jsonify({"error": "source_path required"}), 400

    result = intake_evidence_file(
        source_path=source_path,
        case_id=case_id,
        subject_id=subject_id,
        source_note=source_note,
    )
    audit(
        "evidence_intake",
        details={
            "case_id": case_id,
            "subject_id": subject_id,
            "sha256": result.get("sha256"),
            "stored_name": result.get("stored_name"),
        },
    )
    return jsonify(result), 201


@dashboard_bp.route("/evidence/intake/add", methods=["POST"])
@run_required
def evidence_intake_add_form():
    source_path = request.form.get("source_path")
    case_id = request.form.get("case_id") or None
    subject_id_raw = request.form.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    source_note = request.form.get("source_note") or None

    result = intake_evidence_file(
        source_path=source_path,
        case_id=case_id,
        subject_id=subject_id,
        source_note=source_note,
    )
    flash("Evidence stored: " + str(result.get("stored_name")), "success")
    return redirect(url_for("dashboard.evidence_intake_view"))


@dashboard_bp.route("/evidence/intake/files/<path:name>/download")
@login_required
def evidence_file_download(name):
    path = safe_evidence_path(name)
    return send_from_directory(
        path.parent,
        path.name,
        as_attachment=True,
        download_name=path.name,
    )


@dashboard_bp.route("/api/v1/reports/export-center/attachments", methods=["POST"])
@run_required
def api_export_attachment_manifest():
    payload = request.get_json(silent=True) or {}
    export_manifest_name = payload.get("export_manifest_name")
    case_id = payload.get("case_id")
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None

    if not export_manifest_name:
        return jsonify({"error": "export_manifest_name required"}), 400

    result = attachment_manifest_for_export(
        export_manifest_name=export_manifest_name,
        case_id=case_id,
        subject_id=subject_id,
    )
    audit("export_attachment_manifest", details=result)
    return jsonify(result), 202


@dashboard_bp.route("/api/v1/reports/export-center/attachments/zip", methods=["POST"])
@run_required
def api_export_attachment_zip():
    payload = request.get_json(silent=True) or {}
    export_manifest_name = payload.get("export_manifest_name")
    case_id = payload.get("case_id")
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None

    if not export_manifest_name:
        return jsonify({"error": "export_manifest_name required"}), 400

    result = build_attachment_zip(
        export_manifest_name=export_manifest_name,
        case_id=case_id,
        subject_id=subject_id,
    )
    audit("export_attachment_zip", details=result)
    return jsonify(result), 202

@dashboard_bp.route("/reports/export-center")
@login_required
def report_export_center_view():
    return render_template(
        "report_export_center.html",
        payload=export_center_payload(),
    )


@dashboard_bp.route("/api/v1/reports/export-center")
@login_required
def api_report_export_center():
    return jsonify(export_center_payload())


@dashboard_bp.route("/api/v1/reports/export-center/review-gated", methods=["POST"])
@run_required
def api_review_gated_export():
    payload = request.get_json(silent=True) or {}
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None
    gate_mode = payload.get("gate_mode") or "approved_and_uncertain"
    title = payload.get("title")

    result = review_gated_export_payload(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )
    manifest = result.get("manifest", {})
    audit(
        "review_gated_export",
        details={
            "subject_id": subject_id,
            "gate_mode": gate_mode,
            "manifest_path": manifest.get("manifest_path"),
            "included_count": manifest.get("included_count"),
            "excluded_count": manifest.get("excluded_count"),
        },
    )
    return jsonify(result), 202


@dashboard_bp.route("/reports/export-center/review-gated/run", methods=["POST"])
@run_required
def report_review_gated_export_run():
    subject_id_raw = request.form.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    gate_mode = request.form.get("gate_mode") or "approved_and_uncertain"
    title = request.form.get("title") or None

    result = review_gated_export_payload(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )
    manifest = result.get("manifest", {})
    flash(
        "Review-gated export complete: "
        + str(manifest.get("manifest_path", "")),
        "success",
    )
    return redirect(url_for("dashboard.report_export_center_view"))




@dashboard_bp.route("/reports/export-center/manifests/<path:name>")
@login_required
def report_export_manifest_view(name):
    payload = load_manifest_view(name)
    return render_template(
        "report_manifest_viewer.html",
        payload=payload,
    )


@dashboard_bp.route("/api/v1/reports/export-center/artifacts/<path:name>")
@login_required
def api_report_export_artifact_view(name):
    return jsonify(load_manifest_view(name))


@dashboard_bp.route("/reports/export-center/artifacts/<path:name>/download")
@login_required
def report_export_artifact_download(name):
    path = safe_export_artifact_path(name)
    return send_from_directory(
        path.parent,
        path.name,
        as_attachment=True,
        download_name=path.name,
    )




@dashboard_bp.route("/api/v1/reports/export-center/zip", methods=["POST"])
@run_required
def api_report_export_zip_bundle():
    payload = request.get_json(silent=True) or {}
    subject_id_raw = payload.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw not in (None, "") else None
    gate_mode = payload.get("gate_mode") or "approved_and_uncertain"
    title = payload.get("title")

    result = export_zip_bundle_payload(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )
    bundle = result.get("result", {}).get("bundle", {})
    audit(
        "review_gated_zip_bundle",
        details={
            "subject_id": subject_id,
            "gate_mode": gate_mode,
            "bundle_path": bundle.get("path"),
        },
    )
    return jsonify(result), 202


@dashboard_bp.route("/reports/export-center/zip/run", methods=["POST"])
@run_required
def report_export_zip_bundle_run():
    subject_id_raw = request.form.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    gate_mode = request.form.get("gate_mode") or "approved_and_uncertain"
    title = request.form.get("title") or None

    result = export_zip_bundle_payload(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )
    bundle = result.get("result", {}).get("bundle", {})
    flash("ZIP bundle complete: " + str(bundle.get("path", "")), "success")
    return redirect(url_for("dashboard.report_export_center_view"))


@dashboard_bp.route("/reports/export-center/bundles/<path:name>/download")
@login_required
def report_export_bundle_download(name):
    path = safe_export_bundle_path(name)
    return send_from_directory(
        path.parent,
        path.name,
        as_attachment=True,
        download_name=path.name,
    )

@dashboard_bp.route("/reports/review")
@login_required
def report_review_console():
    payload = {
        "summary": review_summary(),
        "items": review_items_payload().get("items", []),
        "reports": report_runs_payload().get("reports", []),
    }
    return render_template("report_review_console.html", payload=payload)


@dashboard_bp.route("/api/v1/reports/review/summary")
@login_required
def api_report_review_summary():
    return jsonify(review_summary())


@dashboard_bp.route("/api/v1/reports/review/items")
@login_required
def api_report_review_items():
    subject_id_raw = request.args.get("subject_id")
    status = request.args.get("status")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    return jsonify(review_items_payload(subject_id=subject_id, status=status))


@dashboard_bp.route("/api/v1/reports/runs")
@login_required
def api_report_runs():
    subject_id_raw = request.args.get("subject_id")
    subject_id = int(subject_id_raw) if subject_id_raw else None
    return jsonify(report_runs_payload(subject_id=subject_id))


@dashboard_bp.route("/api/v1/reports/review/items/<path:item_id>", methods=["POST"])
@run_required
def api_set_report_review_status(item_id):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "needs_review")
    note = payload.get("note")
    result = set_review_status(item_id, status, note)
    audit(
        "report_review_decision",
        details={
            "item_id": item_id,
            "status": status,
            "note": note,
        },
    )
    return jsonify(result)


@dashboard_bp.route("/reports/review/items/<path:item_id>/<status>", methods=["POST"])
@run_required
def report_review_decision(item_id, status):
    note = request.form.get("note")
    result = set_review_status(item_id, status, note)
    if result.get("updated"):
        flash(f"Review item marked {status}: {item_id}", "success")
    else:
        flash(result.get("reason", "Review update failed"), "error")
    return redirect(url_for("dashboard.report_review_console"))


@dashboard_bp.route("/about")
@login_required
def about():
    return render_template("about.html")


@dashboard_bp.route("/healthz")
def healthz():
    if request.remote_addr not in {"127.0.0.1", "::1", "localhost"}:
        abort(404)
    return {"status": "ok"}


@dashboard_bp.route("/readyz")
def readyz():
    if request.remote_addr not in {"127.0.0.1", "::1", "localhost"}:
        abort(404)
    db.check_ready()
    return {"database": "ok", "status": "ready"}


def add_security_headers(response):
    nonce = getattr(g, "csp_nonce", "")
    csp_value = (
        f"default-src 'self'; img-src 'self' data:; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    response.headers.setdefault("Content-Security-Policy", csp_value)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
    started_at = getattr(g, "request_started_at", None)
    if started_at is not None:
        logger.info(
            "request completed",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "remote_addr": request.remote_addr,
            },
        )
    return response


def create_app(database_url=None):
    settings = load_settings(database_url=database_url)
    configure_logging(settings)
    db.configure_database(settings.database_url, create_schema=settings.auto_create_db)
    init_default_user(settings)

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = settings.secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = settings.https
    app.config["SOCMINT_ALLOW_SIGNUP"] = settings.allow_signup
    app.context_processor(lambda: {"csrf_token": csrf_token, "csp_nonce": csp_nonce})
    app.before_request(init_request_security)
    app.before_request(csrf_protect)
    app.after_request(add_security_headers)
    app.register_blueprint(dashboard_bp)
    return app


@dashboard_bp.route("/api/v1/reports/review/bulk", methods=["POST"])
@run_required
def api_bulk_report_review_status():
    payload = request.get_json(silent=True) or {}
    item_ids = payload.get("item_ids") or []
    status = payload.get("status", "needs_review")
    note = payload.get("note")
    reviewer = None
    try:
        reviewer = getattr(g, "user", None) or session.get("username")
    except Exception:
        reviewer = None

    result = bulk_set_review_status(
        item_ids=item_ids,
        status=status,
        note=note,
        reviewer=reviewer,
    )
    audit(
        "bulk_report_review_decision",
        details={
            "batch_id": result.get("batch_id"),
            "status": status,
            "count": len(item_ids),
        },
    )
    return jsonify(result)


@dashboard_bp.route("/api/v1/reports/review/audit")
@login_required
def api_report_review_audit():
    item_id = request.args.get("item_id")
    batch_id = request.args.get("batch_id")
    return jsonify(review_audit_payload(item_id=item_id, batch_id=batch_id))



# ---- v9.8.1 Product Release Hardening + Route/UI Wiring ----
@dashboard_bp.route("/api/v1/product/build-status")
@login_required
def api_v981_product_build_status():
    from .product_control_center import build_status
    return jsonify(build_status())


@dashboard_bp.route("/api/v1/product/release-readiness")
@login_required
def api_v981_product_release_readiness():
    from .product_control_center import release_readiness
    return jsonify(release_readiness())


@dashboard_bp.route("/api/v1/product/smoke-summary")
@login_required
def api_v981_product_smoke_summary():
    from .product_control_center import smoke_summary
    return jsonify(smoke_summary())


@dashboard_bp.route("/api/v1/product/system-health")
@login_required
def api_v981_product_system_health():
    from .product_control_center import system_health
    return jsonify(system_health())


@dashboard_bp.route("/api/v1/product/write-reports", methods=["POST"])
@admin_required
def api_v981_product_write_reports():
    from .product_control_center import write_product_reports
    return jsonify(write_product_reports())


@dashboard_bp.route("/api/v1/dossier/<subject_id>/quality-gate")
@login_required
def api_v981_dossier_quality_gate(subject_id):
    from .dossier_quality_gate import dossier_quality_gate
    return jsonify(dossier_quality_gate(subject_id))


@dashboard_bp.route("/api/v1/dossier/<subject_id>/traceability")
@login_required
def api_v981_dossier_traceability(subject_id):
    from .dossier_traceability import evidence_to_dossier_traceability
    return jsonify(evidence_to_dossier_traceability(subject_id))


@dashboard_bp.route("/product/build-control")
@login_required
def product_build_control_center():
    from .product_control_center import build_status, release_readiness, smoke_summary, system_health

    return render_template(
        "product_build_control.html",
        build=build_status(),
        readiness=release_readiness(),
        smoke=smoke_summary(),
        health=system_health(),
    )
# ---- end v9.8.1 product routes ----



# ---- v9.8.2 Product Control Operator UX Routes ----
@dashboard_bp.route("/product/operator-runbook")
@login_required
def product_operator_runbook():
    from .product_control_center import build_status, release_readiness, smoke_summary, system_health

    return render_template(
        "product_operator_runbook.html",
        build=build_status(),
        readiness=release_readiness(),
        smoke=smoke_summary(),
        health=system_health(),
    )


@dashboard_bp.route("/api/v1/product/operator-runbook")
@login_required
def api_v982_product_operator_runbook():
    from .product_control_center import build_status, release_readiness, smoke_summary, system_health

    return jsonify(
        {
            "status": "ok",
            "version": "9.8.2",
            "operator_flow": [
                "Open /product/build-control",
                "Run make product-smoke",
                "Run make release-hardening-smoke",
                "Review dossier quality gate",
                "Review dossier traceability",
                "Merge only when release readiness is pass",
            ],
            "links": {
                "build_control": "/product/build-control",
                "product_smoke": "make product-smoke",
                "release_hardening": "make release-hardening-smoke",
                "quality_gate": "/api/v1/dossier/{subject_id}/quality-gate",
                "traceability": "/api/v1/dossier/{subject_id}/traceability",
            },
            "build": build_status(),
            "readiness": release_readiness(),
            "smoke": smoke_summary(),
            "health": system_health(),
        }
    )
# ---- end v9.8.2 product UX routes ----



# ---- v9.8.3 Product Control Runtime Actions ----
def _v983_product_runtime_snapshot(actor=None):
    from datetime import datetime, timezone
    from pathlib import Path

    from .product_control_center import build_status, release_readiness, smoke_summary, system_health

    snapshot = {
        "status": "ok",
        "version": "9.8.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "build": build_status(),
        "readiness": release_readiness(),
        "smoke": smoke_summary(),
        "health": system_health(),
        "actions": {
            "write_reports": "/api/v1/product/actions/write-reports",
            "export_snapshot": "/api/v1/product/actions/export-control-snapshot",
            "runtime_actions": "/api/v1/product/runtime-actions",
            "build_control": "/product/build-control",
        },
    }

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    json_path = release_dir / "V9_8_3_PRODUCT_CONTROL_RUNTIME_SNAPSHOT.json"
    md_path = release_dir / "V9_8_3_PRODUCT_CONTROL_RUNTIME_SNAPSHOT.md"

    json_path.write_text(json.dumps(snapshot, indent=2))
    md_path.write_text(
        "# v9.8.3 Product Control Runtime Snapshot\n\n"
        f"Generated: {snapshot['generated_at']}\n\n"
        f"Actor: {actor or 'unknown'}\n\n"
        f"Readiness: **{snapshot['readiness'].get('status')}**\n\n"
        f"Smoke: **{snapshot['smoke'].get('status')}**\n"
    )

    snapshot["artifacts"] = {
        "json": str(json_path),
        "markdown": str(md_path),
    }
    return snapshot


@dashboard_bp.route("/api/v1/product/runtime-actions")
@login_required
def api_v983_product_runtime_actions():
    return jsonify(
        {
            "status": "ok",
            "version": "9.8.3",
            "actions": [
                {
                    "key": "write_reports",
                    "label": "Write product reports",
                    "method": "POST",
                    "url": "/api/v1/product/actions/write-reports",
                    "role": "admin",
                },
                {
                    "key": "export_control_snapshot",
                    "label": "Export product control snapshot",
                    "method": "POST",
                    "url": "/api/v1/product/actions/export-control-snapshot",
                    "role": "admin",
                },
                {
                    "key": "open_build_control",
                    "label": "Open Product Build Control Center",
                    "method": "GET",
                    "url": "/product/build-control",
                    "role": "user",
                },
            ],
        }
    )


@dashboard_bp.route("/api/v1/product/actions/write-reports", methods=["POST"])
@admin_required
def api_v983_write_product_reports_action():
    from .product_control_center import write_product_reports

    result = write_product_reports()
    audit("product_reports_write", details=result)
    return jsonify({"status": "ok", "version": "9.8.3", "result": result})


@dashboard_bp.route("/api/v1/product/actions/export-control-snapshot", methods=["POST"])
@admin_required
def api_v983_export_product_snapshot_action():
    result = _v983_product_runtime_snapshot(actor=session.get("user"))
    audit("product_control_snapshot_export", details=result.get("artifacts"))
    return jsonify(result)


@dashboard_bp.route("/product/actions/write-reports", methods=["POST"])
@admin_required
def product_action_write_reports():
    from .product_control_center import write_product_reports

    result = write_product_reports()
    audit("product_reports_write", details=result)
    flash("Product reports written.", "success")
    return redirect(url_for("dashboard.product_build_control_center"))


@dashboard_bp.route("/product/actions/export-control-snapshot", methods=["POST"])
@admin_required
def product_action_export_control_snapshot():
    result = _v983_product_runtime_snapshot(actor=session.get("user"))
    audit("product_control_snapshot_export", details=result.get("artifacts"))
    flash("Product control snapshot exported.", "success")
    return redirect(url_for("dashboard.product_build_control_center"))


@dashboard_bp.route("/product/actions/refresh-readiness", methods=["POST"])
@login_required
def product_action_refresh_readiness():
    flash("Product readiness refreshed.", "success")
    return redirect(url_for("dashboard.product_build_control_center"))
# ---- end v9.8.3 product runtime actions ----



# ---- v9.8.4 Product Control Runtime History + Artifact Browser ----
def _v984_product_artifact_roots():
    from pathlib import Path

    return [
        ("release", Path("release")),
        ("product_qa", Path("storage/product_qa")),
    ]


def _v984_product_artifact_kind(path):
    name = path.name.lower()
    rel = str(path).lower()

    if "runtime_snapshot" in name or "runtime_snapshot" in rel:
        return "runtime_snapshot"
    if "hardening_report" in name or "hardening_report" in rel:
        return "hardening_report"
    if "smoke_report" in name or "smoke_report" in rel:
        return "smoke_report"
    if "readiness" in name:
        return "release_readiness"
    if "build_status" in name:
        return "build_status"
    if "manifest" in name:
        return "release_manifest"
    if path.suffix.lower() == ".md":
        return "markdown"
    if path.suffix.lower() == ".json":
        return "json"
    return "artifact"


def _v984_product_artifacts_payload():
    from datetime import datetime, timezone

    artifacts = []
    allowed_suffixes = {".md", ".json", ".txt", ".csv", ".html"}

    for root_key, root in _v984_product_artifact_roots():
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in allowed_suffixes:
                continue

            relpath = path.as_posix()
            stat = path.stat()
            artifacts.append(
                {
                    "root": root_key,
                    "path": relpath,
                    "name": path.name,
                    "kind": _v984_product_artifact_kind(path),
                    "suffix": path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime,
                        timezone.utc,
                    ).isoformat(),
                    "view_url": f"/product/artifacts/view/{relpath}",
                    "download_url": f"/product/artifacts/download/{relpath}",
                }
            )

    artifacts.sort(key=lambda item: item["modified_at"], reverse=True)

    return {
        "status": "ok",
        "version": "9.8.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(artifacts),
        "artifacts": artifacts,
        "filters": {
            "roots": sorted({item["root"] for item in artifacts}),
            "kinds": sorted({item["kind"] for item in artifacts}),
            "suffixes": sorted({item["suffix"] for item in artifacts}),
        },
    }


def _v984_safe_artifact_path(relpath):
    from pathlib import Path

    requested = Path(relpath)
    if requested.is_absolute() or ".." in requested.parts:
        abort(404)

    full = Path(relpath)
    allowed_roots = [root for _, root in _v984_product_artifact_roots()]

    if not full.exists() or not full.is_file():
        abort(404)

    resolved = full.resolve()
    if not any(str(resolved).startswith(str(root.resolve())) for root in allowed_roots if root.exists()):
        abort(404)

    return full


@dashboard_bp.route("/api/v1/product/artifacts")
@login_required
def api_v984_product_artifacts():
    payload = _v984_product_artifacts_payload()
    kind = request.args.get("kind", "").strip()
    suffix = request.args.get("suffix", "").strip()
    root = request.args.get("root", "").strip()

    artifacts = _v985_apply_artifact_review_state(payload["artifacts"])
    if kind:
        artifacts = [item for item in artifacts if item["kind"] == kind]
    if suffix:
        artifacts = [item for item in artifacts if item["suffix"] == suffix]
    if root:
        artifacts = [item for item in artifacts if item["root"] == root]
    artifacts = _v985_filter_artifacts(artifacts)

    payload = {**payload, "count": len(artifacts), "artifacts": artifacts}
    return jsonify(payload)


@dashboard_bp.route("/product/artifacts")
@login_required
def product_artifacts_view():
    payload = _v984_product_artifacts_payload()
    payload["artifacts"] = _v985_filter_artifacts(
        _v985_apply_artifact_review_state(payload["artifacts"])
    )
    payload["count"] = len(payload["artifacts"])
    return render_template("product_artifacts.html", payload=payload)


@dashboard_bp.route("/product/artifacts/view/<path:relpath>")
@login_required
def product_artifact_view(relpath):
    artifact = _v984_safe_artifact_path(relpath)
    if artifact.suffix.lower() not in {".md", ".json", ".txt", ".csv", ".html"}:
        abort(404)

    text = artifact.read_text(errors="replace")
    if len(text) > 250000:
        text = text[:250000] + "\n\n[truncated for browser view]\n"

    return render_template(
        "product_artifact_view.html",
        artifact={
            "path": artifact.as_posix(),
            "name": artifact.name,
            "kind": _v984_product_artifact_kind(artifact),
            "suffix": artifact.suffix.lower(),
        },
        content=text,
    )


@dashboard_bp.route("/product/artifacts/download/<path:relpath>")
@login_required
def product_artifact_download(relpath):
    from flask import send_file

    artifact = _v984_safe_artifact_path(relpath)
    return send_file(
        artifact.resolve(),
        as_attachment=True,
        download_name=artifact.name,
    )
# ---- end v9.8.4 product artifacts ----



# ---- v9.8.5 Product Artifact Review + Pin/Archive Controls ----
def _v985_artifact_metadata_path():
    from pathlib import Path

    path = Path("storage/product_qa/product_artifact_metadata.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v985_load_artifact_metadata():
    path = _v985_artifact_metadata_path()
    if not path.exists():
        return {"version": "9.8.5", "artifacts": {}}

    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"version": "9.8.5", "artifacts": {}}

    if not isinstance(data, dict):
        return {"version": "9.8.5", "artifacts": {}}
    data.setdefault("version", "9.8.5")
    data.setdefault("artifacts", {})
    return data


def _v985_save_artifact_metadata(data):
    path = _v985_artifact_metadata_path()
    data["version"] = "9.8.5"
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v985_bool_value(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}


def _v985_apply_artifact_review_state(artifacts):
    data = _v985_load_artifact_metadata()
    meta = data.get("artifacts", {})
    for artifact in artifacts:
        state = meta.get(
            artifact.get("path", ""),
            {
                "reviewed": False,
                "important": False,
                "archived": False,
                "reviewed_by": None,
                "reviewed_at": None,
                "note": "",
            },
        )
        artifact["review"] = state
        artifact["reviewed"] = bool(state.get("reviewed"))
        artifact["important"] = bool(state.get("important"))
        artifact["archived"] = bool(state.get("archived"))
    return artifacts


def _v985_update_artifact_review(path, reviewed=None, important=None, archived=None, note=None, actor=None):
    from datetime import datetime, timezone

    _v984_safe_artifact_path(path)

    data = _v985_load_artifact_metadata()
    artifacts = data.setdefault("artifacts", {})
    state = artifacts.setdefault(
        path,
        {
            "reviewed": False,
            "important": False,
            "archived": False,
            "reviewed_by": None,
            "reviewed_at": None,
            "note": "",
        },
    )

    if reviewed is not None:
        state["reviewed"] = _v985_bool_value(reviewed)
    if important is not None:
        state["important"] = _v985_bool_value(important)
    if archived is not None:
        state["archived"] = _v985_bool_value(archived)
    if note is not None:
        state["note"] = str(note)

    state["reviewed_by"] = actor
    state["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    artifacts[path] = state
    _v985_save_artifact_metadata(data)

    return {
        "status": "ok",
        "version": "9.8.5",
        "path": path,
        "review": state,
        "metadata_path": str(_v985_artifact_metadata_path()),
    }


def _v985_filter_artifacts(artifacts):
    reviewed = request.args.get("reviewed")
    important = request.args.get("important")
    archived = request.args.get("archived")

    if reviewed is not None:
        expected = _v985_bool_value(reviewed)
        artifacts = [item for item in artifacts if bool(item.get("reviewed")) == expected]
    if important is not None:
        expected = _v985_bool_value(important)
        artifacts = [item for item in artifacts if bool(item.get("important")) == expected]
    if archived is not None:
        expected = _v985_bool_value(archived)
        artifacts = [item for item in artifacts if bool(item.get("archived")) == expected]

    return artifacts


@dashboard_bp.route("/api/v1/product/artifact-review-state")
@login_required
def api_v985_artifact_review_state():
    return jsonify(_v985_load_artifact_metadata())


@dashboard_bp.route("/api/v1/product/artifacts/review", methods=["POST"])
@login_required
def api_v985_update_artifact_review():
    payload = request.get_json(silent=True) or request.form
    path = (payload.get("path") or "").strip()
    if not path:
        abort(400)

    result = _v985_update_artifact_review(
        path,
        reviewed=payload.get("reviewed"),
        important=payload.get("important"),
        archived=payload.get("archived"),
        note=payload.get("note"),
        actor=session.get("user"),
    )
    audit("product_artifact_review_update", details=result)
    return jsonify(result)


@dashboard_bp.route("/product/artifacts/review", methods=["POST"])
@login_required
def product_artifact_review_action():
    path = request.form.get("path", "").strip()
    if not path:
        abort(400)

    result = _v985_update_artifact_review(
        path,
        reviewed=request.form.get("reviewed"),
        important=request.form.get("important"),
        archived=request.form.get("archived"),
        note=request.form.get("note"),
        actor=session.get("user"),
    )
    audit("product_artifact_review_update", details=result)
    flash("Artifact review state updated.", "success")
    return redirect(url_for("dashboard.product_artifacts_view"))
# ---- end v9.8.5 artifact review controls ----
