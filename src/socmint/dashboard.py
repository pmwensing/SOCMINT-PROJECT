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
    # v10.0.7 wave 1 blueprint-owned read-only route registration
    try:
        from .product_artifacts import product_artifacts_bp
        from .product_post_release import product_post_release_bp
        from .product_release_flow import product_release_flow_bp

        app.register_blueprint(product_release_flow_bp)
        app.register_blueprint(product_post_release_bp)
        app.register_blueprint(product_artifacts_bp)
    except Exception as exc:
        app.logger.warning("failed to register v10.0.7 wave 1 blueprints: %s", exc)

    app.register_blueprint(dashboard_bp)

    # v10.0.4 product module registry blueprint
    try:
        from .product_registry import product_registry_bp

        app.register_blueprint(product_registry_bp)
    except Exception as exc:
        app.logger.warning("failed to register product_registry blueprint: %s", exc)

    # v10.0.0 product foundation blueprint
    try:
        from .product_v10 import product_v10_bp

        app.register_blueprint(product_v10_bp)
    except Exception as exc:
        app.logger.warning("failed to register product_v10 blueprint: %s", exc)


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



# ---- v9.8.6 Product Artifact Review Audit Trail ----
def _v986_artifact_audit_path():
    from pathlib import Path

    path = Path("storage/product_qa/product_artifact_review_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v986_load_artifact_audit():
    path = _v986_artifact_audit_path()
    if not path.exists():
        return {"version": "9.8.6", "events": []}

    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"version": "9.8.6", "events": []}

    if not isinstance(data, dict):
        return {"version": "9.8.6", "events": []}

    data.setdefault("version", "9.8.6")
    data.setdefault("events", [])
    return data


def _v986_save_artifact_audit(data):
    path = _v986_artifact_audit_path()
    data["version"] = "9.8.6"
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v986_append_artifact_audit_event(path, actor, before, after, action="artifact_review_update"):
    from datetime import datetime, timezone
    from uuid import uuid4

    data = _v986_load_artifact_audit()
    events = data.setdefault("events", [])
    changed_fields = []

    before = before or {}
    after = after or {}
    for field in ["reviewed", "important", "archived", "note"]:
        if before.get(field) != after.get(field):
            changed_fields.append(field)

    event = {
        "event_id": uuid4().hex,
        "version": "9.8.6",
        "action": action,
        "path": path,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "before": before,
        "after": after,
        "changed_fields": changed_fields,
    }
    events.append(event)
    _v986_save_artifact_audit(data)
    return event


def _v986_events_for_artifact(path=None):
    data = _v986_load_artifact_audit()
    events = data.get("events", [])
    if path:
        events = [event for event in events if event.get("path") == path]
    return events


def _v985_update_artifact_review(path, reviewed=None, important=None, archived=None, note=None, actor=None):
    from copy import deepcopy
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

    before = deepcopy(state)

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

    event = _v986_append_artifact_audit_event(
        path=path,
        actor=actor,
        before=before,
        after=deepcopy(state),
    )

    return {
        "status": "ok",
        "version": "9.8.6",
        "path": path,
        "review": state,
        "audit_event": event,
        "metadata_path": str(_v985_artifact_metadata_path()),
        "audit_path": str(_v986_artifact_audit_path()),
    }


@dashboard_bp.route("/api/v1/product/artifact-review-audit")
@login_required
def api_v986_artifact_review_audit():
    path = request.args.get("path", "").strip()
    events = _v986_events_for_artifact(path or None)
    return jsonify(
        {
            "status": "ok",
            "version": "9.8.6",
            "path": path or None,
            "count": len(events),
            "events": events,
            "audit_path": str(_v986_artifact_audit_path()),
        }
    )


@dashboard_bp.route("/product/artifacts/audit/<path:relpath>")
@login_required
def product_artifact_audit_view(relpath):
    artifact = _v984_safe_artifact_path(relpath)
    events = _v986_events_for_artifact(artifact.as_posix())
    return render_template(
        "product_artifact_audit.html",
        artifact={
            "path": artifact.as_posix(),
            "name": artifact.name,
            "kind": _v984_product_artifact_kind(artifact),
            "suffix": artifact.suffix.lower(),
        },
        events=events,
    )
# ---- end v9.8.6 product artifact audit trail ----



# ---- v9.8.7 Product Artifact Evidence Chain + Export Manifest ----
def _v987_artifact_audit_summary(path):
    events = _v986_events_for_artifact(path)
    changed_fields = sorted(
        {
            field
            for event in events
            for field in event.get("changed_fields", [])
        }
    )
    latest = events[-1] if events else None
    return {
        "event_count": len(events),
        "changed_fields": changed_fields,
        "latest_event_id": latest.get("event_id") if latest else None,
        "latest_actor": latest.get("actor") if latest else None,
        "latest_timestamp": latest.get("timestamp") if latest else None,
        "latest_after": latest.get("after") if latest else None,
    }


def _v987_selected_artifacts(include_archived=False):
    payload = _v984_product_artifacts_payload()
    artifacts = _v985_apply_artifact_review_state(payload["artifacts"])

    selected = []
    for artifact in artifacts:
        review = artifact.get("review", {})
        reviewed = bool(review.get("reviewed"))
        important = bool(review.get("important"))
        archived = bool(review.get("archived"))

        if not include_archived and archived:
            continue
        if reviewed or important:
            item = {
                "path": artifact["path"],
                "name": artifact["name"],
                "kind": artifact["kind"],
                "suffix": artifact["suffix"],
                "size_bytes": artifact["size_bytes"],
                "modified_at": artifact["modified_at"],
                "selection_reason": {
                    "reviewed": reviewed,
                    "important": important,
                    "archived": archived,
                },
                "review": review,
                "audit_summary": _v987_artifact_audit_summary(artifact["path"]),
                "links": {
                    "view": artifact.get("view_url"),
                    "download": artifact.get("download_url"),
                    "audit": f"/product/artifacts/audit/{artifact['path']}",
                },
            }
            selected.append(item)

    selected.sort(
        key=lambda item: (
            not item["selection_reason"]["important"],
            not item["selection_reason"]["reviewed"],
            item["path"],
        )
    )
    return selected


def _v987_export_manifest_payload(include_archived=False, actor=None):
    from datetime import datetime, timezone

    artifacts = _v987_selected_artifacts(include_archived=include_archived)
    return {
        "status": "ok",
        "version": "9.8.7",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "selection_policy": {
            "include_reviewed": True,
            "include_important": True,
            "include_archived": bool(include_archived),
            "exclude_unreviewed_unimportant": True,
        },
        "count": len(artifacts),
        "artifacts": artifacts,
        "summary": {
            "reviewed": sum(1 for item in artifacts if item["selection_reason"]["reviewed"]),
            "important": sum(1 for item in artifacts if item["selection_reason"]["important"]),
            "archived": sum(1 for item in artifacts if item["selection_reason"]["archived"]),
            "audit_events": sum(item["audit_summary"]["event_count"] for item in artifacts),
        },
    }


def _v987_write_export_manifest(include_archived=False, actor=None):
    from pathlib import Path

    payload = _v987_export_manifest_payload(include_archived=include_archived, actor=actor)

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    json_path = release_dir / "V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.json"
    md_path = release_dir / "V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    rows = [
        "# v9.8.7 Product Artifact Export Manifest",
        "",
        f"Generated: {payload['generated_at']}",
        f"Actor: {actor or 'unknown'}",
        f"Count: {payload['count']}",
        "",
        "## Summary",
        "",
        f"- Reviewed: {payload['summary']['reviewed']}",
        f"- Important: {payload['summary']['important']}",
        f"- Archived included: {payload['summary']['archived']}",
        f"- Audit events referenced: {payload['summary']['audit_events']}",
        "",
        "## Artifacts",
        "",
    ]
    for item in payload["artifacts"]:
        reason = item["selection_reason"]
        rows.extend(
            [
                f"### {item['path']}",
                "",
                f"- Kind: {item['kind']}",
                f"- Size: {item['size_bytes']}",
                f"- Reviewed: {reason['reviewed']}",
                f"- Important: {reason['important']}",
                f"- Archived: {reason['archived']}",
                f"- Audit events: {item['audit_summary']['event_count']}",
                f"- Latest actor: {item['audit_summary'].get('latest_actor')}",
                f"- Latest timestamp: {item['audit_summary'].get('latest_timestamp')}",
                "",
            ]
        )

    md_path.write_text("\n".join(rows))

    payload["artifacts_written"] = {
        "json": str(json_path),
        "markdown": str(md_path),
    }
    return payload


@dashboard_bp.route("/api/v1/product/artifact-export-manifest")
@login_required
def api_v987_artifact_export_manifest():
    include_archived = _v985_bool_value(request.args.get("include_archived"))
    return jsonify(
        _v987_export_manifest_payload(
            include_archived=include_archived,
            actor=session.get("user"),
        )
    )


@dashboard_bp.route("/api/v1/product/artifact-export-manifest/write", methods=["POST"])
@admin_required
def api_v987_write_artifact_export_manifest():
    payload = request.get_json(silent=True) or request.form
    include_archived = _v985_bool_value(payload.get("include_archived"))
    result = _v987_write_export_manifest(
        include_archived=include_archived,
        actor=session.get("user"),
    )
    audit("product_artifact_export_manifest_write", details=result.get("artifacts_written"))
    return jsonify(result)


@dashboard_bp.route("/product/artifacts/export-manifest")
@login_required
def product_artifact_export_manifest_view():
    include_archived = _v985_bool_value(request.args.get("include_archived"))
    payload = _v987_export_manifest_payload(
        include_archived=include_archived,
        actor=session.get("user"),
    )
    return render_template(
        "product_artifact_export_manifest.html",
        payload=payload,
        include_archived=include_archived,
    )


@dashboard_bp.route("/product/artifacts/export-manifest/write", methods=["POST"])
@admin_required
def product_artifact_export_manifest_write():
    include_archived = _v985_bool_value(request.form.get("include_archived"))
    result = _v987_write_export_manifest(
        include_archived=include_archived,
        actor=session.get("user"),
    )
    audit("product_artifact_export_manifest_write", details=result.get("artifacts_written"))
    flash("Product artifact export manifest written.", "success")
    return redirect(url_for("dashboard.product_artifact_export_manifest_view"))
# ---- end v9.8.7 product artifact evidence chain ----



# ---- v9.8.8 Product Release Package Builder ----
def _v988_package_slug(value):
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(value).strip())
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "product-release-package"


def _v988_package_root(package_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    base = Path("storage/product_packages")
    base.mkdir(parents=True, exist_ok=True)
    if not package_name:
        package_name = "v9_8_8_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return base / _v988_package_slug(package_name)


def _v988_package_file_copy(src_path, package_root, artifact_prefix="artifacts"):
    import shutil
    from pathlib import Path

    src = Path(src_path)
    if not src.exists() or not src.is_file():
        return None

    rel = src.as_posix()
    dest = package_root / artifact_prefix / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return {
        "source": rel,
        "package_path": dest.as_posix(),
        "size_bytes": dest.stat().st_size,
    }


def _v988_build_release_package(package_name=None, include_archived=False, actor=None):
    from datetime import datetime, timezone
    from pathlib import Path
    import shutil

    package_root = _v988_package_root(package_name)
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)

    manifest = _v987_export_manifest_payload(
        include_archived=include_archived,
        actor=actor,
    )

    copied_artifacts = []
    for item in manifest.get("artifacts", []):
        copied = _v988_package_file_copy(item.get("path"), package_root)
        if copied:
            copied["selection_reason"] = item.get("selection_reason", {})
            copied["review"] = item.get("review", {})
            copied["audit_summary"] = item.get("audit_summary", {})
            copied_artifacts.append(copied)

    metadata_files = []
    for src in [
        "release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.json",
        "release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.md",
        "storage/product_qa/product_artifact_metadata.json",
        "storage/product_qa/product_artifact_review_audit.json",
    ]:
        copied = _v988_package_file_copy(src, package_root, artifact_prefix="metadata")
        if copied:
            metadata_files.append(copied)

    package_manifest = {
        "status": "ok",
        "version": "9.8.8",
        "package_name": package_root.name,
        "package_path": package_root.as_posix(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "include_archived": bool(include_archived),
        "selection_policy": manifest.get("selection_policy", {}),
        "selected_count": len(manifest.get("artifacts", [])),
        "copied_artifact_count": len(copied_artifacts),
        "metadata_file_count": len(metadata_files),
        "summary": manifest.get("summary", {}),
        "copied_artifacts": copied_artifacts,
        "metadata_files": metadata_files,
        "source_manifest": manifest,
    }

    (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps(package_manifest, indent=2, sort_keys=True))

    index_lines = [
        "# Product Release Package",
        "",
        f"Version: {package_manifest['version']}",
        f"Package: {package_manifest['package_name']}",
        f"Generated: {package_manifest['generated_at']}",
        f"Actor: {actor or 'unknown'}",
        f"Selected artifacts: {package_manifest['selected_count']}",
        f"Copied artifacts: {package_manifest['copied_artifact_count']}",
        "",
        "## Included Metadata",
        "",
    ]
    for item in metadata_files:
        index_lines.append(f"- `{item['package_path']}` from `{item['source']}`")

    index_lines.extend(["", "## Selected Artifacts", ""])
    for item in copied_artifacts:
        reason = item.get("selection_reason", {})
        index_lines.extend(
            [
                f"### {item['source']}",
                "",
                f"- Package path: `{item['package_path']}`",
                f"- Reviewed: {reason.get('reviewed')}",
                f"- Important: {reason.get('important')}",
                f"- Archived: {reason.get('archived')}",
                f"- Audit events: {item.get('audit_summary', {}).get('event_count')}",
                "",
            ]
        )

    (package_root / "PACKAGE_INDEX.md").write_text("\n".join(index_lines))

    package_manifest["package_index"] = (package_root / "PACKAGE_INDEX.md").as_posix()
    package_manifest["package_manifest"] = (package_root / "PACKAGE_MANIFEST.json").as_posix()

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    latest_json = release_dir / "V9_8_8_PRODUCT_RELEASE_PACKAGE_MANIFEST.json"
    latest_md = release_dir / "V9_8_8_PRODUCT_RELEASE_PACKAGE_INDEX.md"
    latest_json.write_text(json.dumps(package_manifest, indent=2, sort_keys=True))
    latest_md.write_text("\n".join(index_lines))
    package_manifest["release_artifacts"] = {
        "json": latest_json.as_posix(),
        "markdown": latest_md.as_posix(),
    }

    return package_manifest


@dashboard_bp.route("/api/v1/product/release-package")
@login_required
def api_v988_release_package_preview():
    include_archived = _v985_bool_value(request.args.get("include_archived"))
    package_name = request.args.get("package_name", "preview")
    manifest = _v987_export_manifest_payload(
        include_archived=include_archived,
        actor=session.get("user"),
    )
    return jsonify(
        {
            "status": "ok",
            "version": "9.8.8",
            "package_name": _v988_package_slug(package_name),
            "include_archived": include_archived,
            "selected_count": manifest.get("count", 0),
            "summary": manifest.get("summary", {}),
            "selected_artifacts": manifest.get("artifacts", []),
            "would_include_metadata": [
                "release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.json",
                "release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.md",
                "storage/product_qa/product_artifact_metadata.json",
                "storage/product_qa/product_artifact_review_audit.json",
            ],
        }
    )


@dashboard_bp.route("/api/v1/product/release-package/build", methods=["POST"])
@admin_required
def api_v988_release_package_build():
    payload = request.get_json(silent=True) or request.form
    package_name = payload.get("package_name") or None
    include_archived = _v985_bool_value(payload.get("include_archived"))
    result = _v988_build_release_package(
        package_name=package_name,
        include_archived=include_archived,
        actor=session.get("user"),
    )
    audit("product_release_package_build", details=result.get("release_artifacts"))
    return jsonify(result)


@dashboard_bp.route("/product/release-package")
@login_required
def product_release_package_view():
    include_archived = _v985_bool_value(request.args.get("include_archived"))
    package_name = request.args.get("package_name", "v9_8_8_preview")
    preview = _v987_export_manifest_payload(
        include_archived=include_archived,
        actor=session.get("user"),
    )
    return render_template(
        "product_release_package.html",
        preview=preview,
        include_archived=include_archived,
        package_name=package_name,
    )


@dashboard_bp.route("/product/release-package/build", methods=["POST"])
@admin_required
def product_release_package_build():
    package_name = request.form.get("package_name") or None
    include_archived = _v985_bool_value(request.form.get("include_archived"))
    result = _v988_build_release_package(
        package_name=package_name,
        include_archived=include_archived,
        actor=session.get("user"),
    )
    audit("product_release_package_build", details=result.get("release_artifacts"))
    flash("Product release package built.", "success")
    return redirect(url_for("dashboard.product_release_package_view"))
# ---- end v9.8.8 product release package builder ----



# ---- v9.8.9 Product Release Package ZIP Export + Download ----
def _v989_packages_root():
    from pathlib import Path

    root = Path("storage/product_packages")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _v989_safe_package_dir(package_name):
    root = _v989_packages_root().resolve()
    package = _v988_package_slug(package_name)
    path = (root / package).resolve()
    if not str(path).startswith(str(root)):
        abort(404)
    if not path.exists() or not path.is_dir():
        abort(404)
    return path


def _v989_package_zip_path(package_name):
    root = _v989_packages_root()
    package = _v988_package_slug(package_name)
    return root / f"{package}.zip"


def _v989_list_release_packages():
    from datetime import datetime, timezone
    import zipfile

    root = _v989_packages_root()
    packages = []

    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue

        manifest_path = path / "PACKAGE_MANIFEST.json"
        index_path = path / "PACKAGE_INDEX.md"
        zip_path = _v989_package_zip_path(path.name)

        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except Exception:
                manifest = {}

        packages.append(
            {
                "package_name": path.name,
                "package_path": path.as_posix(),
                "manifest_path": manifest_path.as_posix() if manifest_path.exists() else None,
                "index_path": index_path.as_posix() if index_path.exists() else None,
                "zip_path": zip_path.as_posix() if zip_path.exists() else None,
                "zip_exists": zip_path.exists(),
                "zip_size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
                "zip_download_url": f"/product/release-package/download/{path.name}" if zip_path.exists() else None,
                "selected_count": manifest.get("selected_count", 0),
                "copied_artifact_count": manifest.get("copied_artifact_count", 0),
                "metadata_file_count": manifest.get("metadata_file_count", 0),
                "generated_at": manifest.get("generated_at"),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "zip_entries": zipfile.ZipFile(zip_path).namelist() if zip_path.exists() else [],
            }
        )

    packages.sort(key=lambda item: item.get("modified_at") or "", reverse=True)
    return packages


def _v989_zip_release_package(package_name):
    import zipfile

    package_dir = _v989_safe_package_dir(package_name)
    zip_path = _v989_package_zip_path(package_dir.name)

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if not path.is_file():
                continue
            zf.write(path, path.relative_to(package_dir).as_posix())

    entries = []
    with zipfile.ZipFile(zip_path) as zf:
        entries = zf.namelist()

    return {
        "status": "ok",
        "version": "9.8.9",
        "package_name": package_dir.name,
        "package_path": package_dir.as_posix(),
        "zip_path": zip_path.as_posix(),
        "zip_size_bytes": zip_path.stat().st_size,
        "zip_entry_count": len(entries),
        "zip_entries": entries,
        "download_url": f"/product/release-package/download/{package_dir.name}",
    }


@dashboard_bp.route("/api/v1/product/release-packages")
@login_required
def api_v989_release_packages():
    return jsonify(
        {
            "status": "ok",
            "version": "9.8.9",
            "count": len(_v989_list_release_packages()),
            "packages": _v989_list_release_packages(),
        }
    )


@dashboard_bp.route("/api/v1/product/release-package/<package_name>/zip", methods=["POST"])
@admin_required
def api_v989_zip_release_package(package_name):
    result = _v989_zip_release_package(package_name)
    audit("product_release_package_zip", details=result)
    return jsonify(result)


@dashboard_bp.route("/product/release-package/zip/<package_name>", methods=["POST"])
@admin_required
def product_release_package_zip(package_name):
    result = _v989_zip_release_package(package_name)
    audit("product_release_package_zip", details=result)
    flash("Product release package ZIP created.", "success")
    return redirect(url_for("dashboard.product_release_package_view"))


@dashboard_bp.route("/product/release-package/download/<package_name>")
@login_required
def product_release_package_download(package_name):
    from flask import send_file

    package = _v988_package_slug(package_name)
    zip_path = _v989_package_zip_path(package)
    root = _v989_packages_root().resolve()
    resolved = zip_path.resolve()

    if not str(resolved).startswith(str(root)) or not zip_path.exists():
        abort(404)

    return send_file(
        resolved,
        as_attachment=True,
        download_name=zip_path.name,
    )
# ---- end v9.8.9 product release package ZIP export ----



# ---- v9.9.0 Product Release Candidate Console ----
def _v990_rc_stage_definitions():
    return [
        {
            "key": "product_smoke",
            "label": "Product Smoke",
            "target": "make product-smoke",
            "artifact": "release/V9_7_PRODUCT_SMOKE_REPORT.md",
            "required": True,
        },
        {
            "key": "artifact_review",
            "label": "Artifact Review",
            "target": "make product-artifact-review-smoke",
            "artifact": "release/V9_8_5_ARTIFACT_REVIEW_HARDENING_REPORT.md",
            "required": True,
        },
        {
            "key": "artifact_review_audit",
            "label": "Artifact Review Audit",
            "target": "make product-artifact-review-audit-smoke",
            "artifact": "release/V9_8_6_ARTIFACT_REVIEW_AUDIT_HARDENING_REPORT.md",
            "required": True,
        },
        {
            "key": "export_manifest",
            "label": "Evidence Chain Export Manifest",
            "target": "make product-artifact-export-manifest-smoke",
            "artifact": "release/V9_8_7_EXPORT_MANIFEST_HARDENING_REPORT.md",
            "required": True,
        },
        {
            "key": "release_package",
            "label": "Release Package Builder",
            "target": "make product-release-package-smoke",
            "artifact": "release/V9_8_8_RELEASE_PACKAGE_HARDENING_REPORT.md",
            "required": True,
        },
        {
            "key": "zip_export",
            "label": "Release Package ZIP Export",
            "target": "make product-release-package-zip-smoke",
            "artifact": "release/V9_8_9_RELEASE_PACKAGE_ZIP_HARDENING_REPORT.md",
            "required": True,
        },
    ]


def _v990_artifact_exists(path):
    from pathlib import Path

    p = Path(path)
    return p.exists() and p.is_file()


def _v990_rc_stage_status():
    stages = []
    for stage in _v990_rc_stage_definitions():
        artifact_exists = _v990_artifact_exists(stage["artifact"])
        status = "pass" if artifact_exists else "warn"
        stages.append(
            {
                **stage,
                "status": status,
                "artifact_exists": artifact_exists,
                "artifact_view_url": f"/product/artifacts/view/{stage['artifact']}" if artifact_exists else None,
                "artifact_download_url": f"/product/artifacts/download/{stage['artifact']}" if artifact_exists else None,
            }
        )
    return stages


def _v990_rc_summary():
    stages = _v990_rc_stage_status()
    required = [stage for stage in stages if stage.get("required")]
    passed = [stage for stage in required if stage.get("status") == "pass"]
    missing = [stage for stage in required if stage.get("status") != "pass"]
    status = "pass" if len(passed) == len(required) else "warn"
    return {
        "status": status,
        "required_total": len(required),
        "required_passed": len(passed),
        "required_missing": len(missing),
        "missing_stage_keys": [stage["key"] for stage in missing],
        "stages": stages,
    }


def _v990_build_rc_manifest(actor=None):
    from datetime import datetime, timezone
    from pathlib import Path

    summary = _v990_rc_summary()
    package_preview = None
    export_manifest = None
    packages = []

    try:
        export_manifest = _v987_export_manifest_payload(include_archived=False, actor=actor)
    except Exception as exc:
        export_manifest = {"status": "warn", "error": str(exc)}

    try:
        package_preview = _v987_export_manifest_payload(include_archived=False, actor=actor)
    except Exception as exc:
        package_preview = {"status": "warn", "error": str(exc)}

    try:
        packages = _v989_list_release_packages()
    except Exception:
        packages = []

    manifest = {
        "status": summary["status"],
        "version": "9.9.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_candidate": {
            "name": "SOCMINT Workbench v9.9.0 Release Candidate",
            "base_line": "v9.8.0-v9.8.9",
            "recommended_next_action": (
                "Cut v9.9.0 release candidate tag"
                if summary["status"] == "pass"
                else "Run missing v9.8 chain smoke targets before cutting RC"
            ),
        },
        "summary": summary,
        "export_manifest_summary": export_manifest.get("summary") if isinstance(export_manifest, dict) else None,
        "package_preview_count": package_preview.get("count") if isinstance(package_preview, dict) else None,
        "built_package_count": len(packages),
        "packages": packages,
    }

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    json_path = release_dir / "V9_9_0_RELEASE_CANDIDATE_MANIFEST.json"
    md_path = release_dir / "V9_9_0_RELEASE_CANDIDATE_MANIFEST.md"

    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    rows = [
        "# v9.9.0 Release Candidate Manifest",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Status: **{manifest['status']}**",
        f"Actor: {actor or 'unknown'}",
        "",
        "## Summary",
        "",
        f"- Required passed: {summary['required_passed']}/{summary['required_total']}",
        f"- Missing: {summary['required_missing']}",
        f"- Recommended next action: {manifest['release_candidate']['recommended_next_action']}",
        "",
        "## Stage Status",
        "",
    ]
    for stage in summary["stages"]:
        rows.extend(
            [
                f"### {stage['label']}",
                "",
                f"- Status: {stage['status']}",
                f"- Target: `{stage['target']}`",
                f"- Artifact: `{stage['artifact']}`",
                f"- Artifact exists: {stage['artifact_exists']}",
                "",
            ]
        )

    md_path.write_text("\n".join(rows))

    manifest["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return manifest


@dashboard_bp.route("/api/v1/product/release-candidate")
@login_required
def api_v990_release_candidate():
    return jsonify(_v990_build_rc_manifest(actor=session.get("user")))


@dashboard_bp.route("/api/v1/product/release-candidate/write", methods=["POST"])
@admin_required
def api_v990_release_candidate_write():
    manifest = _v990_build_rc_manifest(actor=session.get("user"))
    audit("product_release_candidate_manifest_write", details=manifest.get("artifacts_written"))
    return jsonify(manifest)


@dashboard_bp.route("/product/release-candidate")
@login_required
def product_release_candidate_console():
    manifest = _v990_build_rc_manifest(actor=session.get("user"))
    return render_template("product_release_candidate.html", manifest=manifest)


@dashboard_bp.route("/product/release-candidate/write", methods=["POST"])
@admin_required
def product_release_candidate_write():
    manifest = _v990_build_rc_manifest(actor=session.get("user"))
    audit("product_release_candidate_manifest_write", details=manifest.get("artifacts_written"))
    flash("Release candidate manifest written.", "success")
    return redirect(url_for("dashboard.product_release_candidate_console"))
# ---- end v9.9.0 product release candidate console ----



# ---- v9.9.1 Release Candidate Sign-Off + Final Product Gate ----
def _v991_signoff_state_path():
    from pathlib import Path

    path = Path("storage/product_qa/release_candidate_signoff_state.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v991_signoff_audit_path():
    from pathlib import Path

    path = Path("storage/product_qa/release_candidate_signoff_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v991_load_signoff_state():
    path = _v991_signoff_state_path()
    if not path.exists():
        return {
            "version": "9.9.1",
            "decision": "pending",
            "approved": False,
            "blocked": False,
            "reason": "",
            "actor": None,
            "updated_at": None,
        }

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.1")
    data.setdefault("decision", "pending")
    data.setdefault("approved", False)
    data.setdefault("blocked", False)
    data.setdefault("reason", "")
    data.setdefault("actor", None)
    data.setdefault("updated_at", None)
    return data


def _v991_save_signoff_state(state):
    state["version"] = "9.9.1"
    path = _v991_signoff_state_path()
    path.write_text(json.dumps(state, indent=2, sort_keys=True))
    return state


def _v991_load_signoff_audit():
    path = _v991_signoff_audit_path()
    if not path.exists():
        return {"version": "9.9.1", "events": []}

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.1")
    data.setdefault("events", [])
    return data


def _v991_save_signoff_audit(data):
    data["version"] = "9.9.1"
    path = _v991_signoff_audit_path()
    path.write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v991_append_signoff_audit(action, actor, before, after, rc_status, reason=""):
    from datetime import datetime, timezone
    from uuid import uuid4

    data = _v991_load_signoff_audit()
    event = {
        "event_id": uuid4().hex,
        "version": "9.9.1",
        "action": action,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "rc_status": rc_status,
        "before": before,
        "after": after,
    }
    data.setdefault("events", []).append(event)
    _v991_save_signoff_audit(data)
    return event


def _v991_final_gate_payload(actor=None):
    from datetime import datetime, timezone

    rc_manifest = _v990_build_rc_manifest(actor=actor)
    signoff = _v991_load_signoff_state()
    audit_data = _v991_load_signoff_audit()

    rc_pass = rc_manifest.get("status") == "pass"
    approved = bool(signoff.get("approved"))
    blocked = bool(signoff.get("blocked"))

    if not rc_pass:
        gate_status = "blocked"
        can_approve = False
        recommended = "Run and pass the full RC chain before approving."
    elif blocked:
        gate_status = "blocked"
        can_approve = False
        recommended = "Resolve the block reason before release."
    elif approved:
        gate_status = "approved"
        can_approve = True
        recommended = "Release candidate approved. Ready for final release/tag."
    else:
        gate_status = "pending"
        can_approve = True
        recommended = "RC chain is passing. Awaiting operator sign-off."

    return {
        "status": "ok",
        "version": "9.9.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "gate_status": gate_status,
        "can_approve": can_approve,
        "rc_status": rc_manifest.get("status"),
        "rc_summary": rc_manifest.get("summary"),
        "signoff": signoff,
        "audit_event_count": len(audit_data.get("events", [])),
        "latest_audit_event": audit_data.get("events", [])[-1] if audit_data.get("events") else None,
        "recommended_next_action": recommended,
    }


def _v991_write_final_gate_manifest(actor=None):
    from pathlib import Path

    payload = _v991_final_gate_payload(actor=actor)
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json"
    md_path = release_dir / "V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    signoff = payload.get("signoff", {})
    rows = [
        "# v9.9.1 Final Product Gate Manifest",
        "",
        f"Generated: {payload['generated_at']}",
        f"Gate status: **{payload['gate_status']}**",
        f"RC status: **{payload['rc_status']}**",
        f"Decision: **{signoff.get('decision')}**",
        f"Approved: {signoff.get('approved')}",
        f"Blocked: {signoff.get('blocked')}",
        f"Actor: {signoff.get('actor') or actor or 'unknown'}",
        f"Reason: {signoff.get('reason')}",
        "",
        "## Recommended Next Action",
        "",
        payload.get("recommended_next_action", ""),
        "",
        "## RC Summary",
        "",
        f"- Required passed: {payload.get('rc_summary', {}).get('required_passed')}/{payload.get('rc_summary', {}).get('required_total')}",
        f"- Missing: {payload.get('rc_summary', {}).get('required_missing')}",
        f"- Sign-off audit events: {payload.get('audit_event_count')}",
        "",
    ]
    md_path.write_text("\n".join(rows))

    payload["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return payload


def _v991_apply_signoff_decision(decision, actor=None, reason=""):
    from copy import deepcopy
    from datetime import datetime, timezone

    gate_before = _v991_final_gate_payload(actor=actor)
    rc_status = gate_before.get("rc_status")
    before = deepcopy(_v991_load_signoff_state())

    decision = str(decision or "").strip().lower()
    if decision not in {"approve", "block", "reset"}:
        abort(400)

    if decision == "approve" and rc_status != "pass":
        after = deepcopy(before)
        event = _v991_append_signoff_audit(
            action="approve_denied",
            actor=actor,
            before=before,
            after=after,
            rc_status=rc_status,
            reason=reason or "Approval denied because RC chain is not passing.",
        )
        return {
            "status": "blocked",
            "version": "9.9.1",
            "approved": False,
            "reason": "RC chain must be pass before approval.",
            "audit_event": event,
            "gate": _v991_final_gate_payload(actor=actor),
        }

    if decision == "approve":
        after = {
            "version": "9.9.1",
            "decision": "approved",
            "approved": True,
            "blocked": False,
            "reason": reason or "Approved for final product release.",
            "actor": actor,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    elif decision == "block":
        after = {
            "version": "9.9.1",
            "decision": "blocked",
            "approved": False,
            "blocked": True,
            "reason": reason or "Blocked by operator.",
            "actor": actor,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        after = {
            "version": "9.9.1",
            "decision": "pending",
            "approved": False,
            "blocked": False,
            "reason": reason or "Reset to pending.",
            "actor": actor,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    _v991_save_signoff_state(after)
    event = _v991_append_signoff_audit(
        action=f"signoff_{decision}",
        actor=actor,
        before=before,
        after=after,
        rc_status=rc_status,
        reason=after.get("reason", ""),
    )
    gate = _v991_write_final_gate_manifest(actor=actor)
    return {
        "status": "ok",
        "version": "9.9.1",
        "decision": decision,
        "signoff": after,
        "audit_event": event,
        "gate": gate,
    }


@dashboard_bp.route("/api/v1/product/final-gate")
@login_required
def api_v991_final_gate():
    return jsonify(_v991_final_gate_payload(actor=session.get("user")))


@dashboard_bp.route("/api/v1/product/final-gate/signoff-audit")
@login_required
def api_v991_signoff_audit():
    data = _v991_load_signoff_audit()
    return jsonify(
        {
            "status": "ok",
            "version": "9.9.1",
            "count": len(data.get("events", [])),
            "events": data.get("events", []),
            "audit_path": str(_v991_signoff_audit_path()),
        }
    )


@dashboard_bp.route("/api/v1/product/final-gate/write", methods=["POST"])
@admin_required
def api_v991_write_final_gate():
    manifest = _v991_write_final_gate_manifest(actor=session.get("user"))
    audit("product_final_gate_manifest_write", details=manifest.get("artifacts_written"))
    return jsonify(manifest)


@dashboard_bp.route("/api/v1/product/final-gate/signoff", methods=["POST"])
@admin_required
def api_v991_signoff_decision():
    payload = request.get_json(silent=True) or request.form
    decision = payload.get("decision")
    reason = payload.get("reason", "")
    result = _v991_apply_signoff_decision(
        decision=decision,
        actor=session.get("user"),
        reason=reason,
    )
    audit("product_final_gate_signoff", details={"decision": decision, "result_status": result.get("status")})
    return jsonify(result)


@dashboard_bp.route("/product/final-gate")
@login_required
def product_final_gate_view():
    gate = _v991_final_gate_payload(actor=session.get("user"))
    audit_data = _v991_load_signoff_audit()
    return render_template(
        "product_final_gate.html",
        gate=gate,
        audit_events=audit_data.get("events", []),
    )


@dashboard_bp.route("/product/final-gate/write", methods=["POST"])
@admin_required
def product_final_gate_write():
    manifest = _v991_write_final_gate_manifest(actor=session.get("user"))
    audit("product_final_gate_manifest_write", details=manifest.get("artifacts_written"))
    flash("Final product gate manifest written.", "success")
    return redirect(url_for("dashboard.product_final_gate_view"))


@dashboard_bp.route("/product/final-gate/signoff", methods=["POST"])
@admin_required
def product_final_gate_signoff():
    decision = request.form.get("decision")
    reason = request.form.get("reason", "")
    result = _v991_apply_signoff_decision(
        decision=decision,
        actor=session.get("user"),
        reason=reason,
    )
    if result.get("status") == "blocked" and decision == "approve":
        flash("Approval blocked because the RC chain is not passing.", "error")
    else:
        flash("Final gate decision recorded.", "success")
    return redirect(url_for("dashboard.product_final_gate_view"))
# ---- end v9.9.1 release candidate sign-off gate ----



# ---- v9.9.2 Final Release Publisher + Release Notes Pack ----
def _v992_final_release_root(release_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    base = Path("storage/final_releases")
    base.mkdir(parents=True, exist_ok=True)
    if not release_name:
        release_name = "v9_9_2_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return base / _v988_package_slug(release_name)


def _v992_load_json_file(path):
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _v992_final_release_preview(actor=None):
    from datetime import datetime, timezone

    gate = _v991_final_gate_payload(actor=actor)
    rc_manifest = _v992_load_json_file("release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json")
    final_gate_manifest = _v992_load_json_file("release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json")
    packages = []
    try:
        packages = _v989_list_release_packages()
    except Exception:
        packages = []

    final_gate_approved = gate.get("gate_status") == "approved" and bool(gate.get("signoff", {}).get("approved"))
    can_publish = final_gate_approved and gate.get("rc_status") == "pass"

    checklist = [
        {
            "key": "rc_manifest",
            "label": "Release candidate manifest exists",
            "pass": rc_manifest is not None,
            "artifact": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
        },
        {
            "key": "final_gate_manifest",
            "label": "Final product gate manifest exists",
            "pass": final_gate_manifest is not None,
            "artifact": "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json",
        },
        {
            "key": "final_gate_approved",
            "label": "Final product gate is approved",
            "pass": final_gate_approved,
            "artifact": "storage/product_qa/release_candidate_signoff_state.json",
        },
        {
            "key": "rc_chain_pass",
            "label": "RC chain status is pass",
            "pass": gate.get("rc_status") == "pass",
            "artifact": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
        },
        {
            "key": "release_packages",
            "label": "At least one release package exists",
            "pass": len(packages) > 0,
            "artifact": "storage/product_packages/",
        },
    ]

    return {
        "status": "ok",
        "version": "9.9.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "can_publish": can_publish,
        "publish_status": "ready" if can_publish else "blocked",
        "recommended_next_action": (
            "Publish final release notes pack."
            if can_publish
            else "Approve the final product gate before publishing."
        ),
        "gate": gate,
        "rc_manifest": rc_manifest,
        "final_gate_manifest": final_gate_manifest,
        "packages": packages,
        "checklist": checklist,
        "checklist_passed": sum(1 for item in checklist if item["pass"]),
        "checklist_total": len(checklist),
    }


def _v992_generate_release_notes(preview, release_name):
    gate = preview.get("gate", {})
    signoff = gate.get("signoff", {})
    rc_summary = gate.get("rc_summary", {}) or {}

    lines = [
        "# SOCMINT Workbench Final Release Notes",
        "",
        f"Release: {release_name}",
        "Version: v9.9.2",
        f"Publish status: {preview.get('publish_status')}",
        f"Generated: {preview.get('generated_at')}",
        "",
        "## Final Gate",
        "",
        f"- Gate status: {gate.get('gate_status')}",
        f"- RC status: {gate.get('rc_status')}",
        f"- Sign-off decision: {signoff.get('decision')}",
        f"- Approved: {signoff.get('approved')}",
        f"- Actor: {signoff.get('actor')}",
        f"- Reason: {signoff.get('reason')}",
        "",
        "## RC Chain",
        "",
        f"- Required passed: {rc_summary.get('required_passed')}/{rc_summary.get('required_total')}",
        f"- Missing: {rc_summary.get('required_missing')}",
        "",
        "## Release Package Inventory",
        "",
    ]

    for package in preview.get("packages", []):
        lines.extend(
            [
                f"### {package.get('package_name')}",
                "",
                f"- Selected count: {package.get('selected_count')}",
                f"- Copied artifact count: {package.get('copied_artifact_count')}",
                f"- Metadata file count: {package.get('metadata_file_count')}",
                f"- ZIP exists: {package.get('zip_exists')}",
                f"- ZIP path: `{package.get('zip_path')}`",
                "",
            ]
        )

    lines.extend(["## Publish Checklist", ""])
    for item in preview.get("checklist", []):
        marker = "PASS" if item.get("pass") else "BLOCK"
        lines.append(f"- [{marker}] {item.get('label')} — `{item.get('artifact')}`")

    lines.append("")
    return "\n".join(lines)


def _v992_publish_final_release(release_name=None, actor=None):
    from pathlib import Path
    import shutil

    preview = _v992_final_release_preview(actor=actor)
    if not preview.get("can_publish"):
        return {
            "status": "blocked",
            "version": "9.9.2",
            "reason": "Final release cannot publish unless the final product gate is approved and RC status is pass.",
            "preview": preview,
        }

    root = _v992_final_release_root(release_name)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    release_name = root.name
    notes = _v992_generate_release_notes(preview, release_name)

    copied_files = []
    for src in [
        "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
        "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.md",
        "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json",
        "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.md",
        "storage/product_qa/release_candidate_signoff_state.json",
        "storage/product_qa/release_candidate_signoff_audit.json",
    ]:
        p = Path(src)
        if p.exists() and p.is_file():
            dest = root / "evidence" / src
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            copied_files.append({"source": src, "package_path": dest.as_posix(), "size_bytes": dest.stat().st_size})

    package_zips = []
    for package in preview.get("packages", []):
        zip_path = package.get("zip_path")
        if zip_path:
            p = Path(zip_path)
            if p.exists() and p.is_file():
                dest = root / "packages" / p.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest)
                package_zips.append({"source": p.as_posix(), "package_path": dest.as_posix(), "size_bytes": dest.stat().st_size})

    publish_manifest = {
        "status": "published",
        "version": "9.9.2",
        "release_name": release_name,
        "release_path": root.as_posix(),
        "actor": actor,
        "published_at": preview.get("generated_at"),
        "checklist": preview.get("checklist"),
        "checklist_passed": preview.get("checklist_passed"),
        "checklist_total": preview.get("checklist_total"),
        "final_gate": preview.get("gate"),
        "copied_files": copied_files,
        "package_zips": package_zips,
        "release_notes": (root / "RELEASE_NOTES.md").as_posix(),
    }

    (root / "RELEASE_NOTES.md").write_text(notes)
    (root / "FINAL_RELEASE_CHECKLIST.json").write_text(json.dumps(preview.get("checklist"), indent=2, sort_keys=True))
    (root / "PUBLISH_MANIFEST.json").write_text(json.dumps(publish_manifest, indent=2, sort_keys=True))

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    latest_notes = release_dir / "V9_9_2_FINAL_RELEASE_NOTES.md"
    latest_checklist = release_dir / "V9_9_2_FINAL_RELEASE_CHECKLIST.json"
    latest_manifest = release_dir / "V9_9_2_FINAL_RELEASE_PUBLISH_MANIFEST.json"

    latest_notes.write_text(notes)
    latest_checklist.write_text(json.dumps(preview.get("checklist"), indent=2, sort_keys=True))
    latest_manifest.write_text(json.dumps(publish_manifest, indent=2, sort_keys=True))

    publish_manifest["artifacts_written"] = {
        "release_notes": latest_notes.as_posix(),
        "checklist": latest_checklist.as_posix(),
        "publish_manifest": latest_manifest.as_posix(),
        "package_release_notes": (root / "RELEASE_NOTES.md").as_posix(),
        "package_manifest": (root / "PUBLISH_MANIFEST.json").as_posix(),
    }
    return publish_manifest


@dashboard_bp.route("/api/v1/product/final-release")
@login_required
def api_v992_final_release_preview():
    return jsonify(_v992_final_release_preview(actor=session.get("user")))


@dashboard_bp.route("/api/v1/product/final-release/publish", methods=["POST"])
@admin_required
def api_v992_final_release_publish():
    payload = request.get_json(silent=True) or request.form
    release_name = payload.get("release_name") or None
    result = _v992_publish_final_release(release_name=release_name, actor=session.get("user"))
    audit("product_final_release_publish", details={"status": result.get("status"), "release_name": release_name})
    return jsonify(result)


@dashboard_bp.route("/product/final-release")
@login_required
def product_final_release_view():
    preview = _v992_final_release_preview(actor=session.get("user"))
    return render_template("product_final_release.html", preview=preview)


@dashboard_bp.route("/product/final-release/publish", methods=["POST"])
@admin_required
def product_final_release_publish():
    release_name = request.form.get("release_name") or None
    result = _v992_publish_final_release(release_name=release_name, actor=session.get("user"))
    if result.get("status") == "published":
        flash("Final release notes pack published.", "success")
    else:
        flash("Final release blocked until final gate approval.", "error")
    return redirect(url_for("dashboard.product_final_release_view"))
# ---- end v9.9.2 final release publisher ----



# ---- v9.9.3 Final Release Archive + Integrity Seal ----
def _v993_final_releases_root():
    from pathlib import Path
    root = Path("storage/final_releases")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _v993_archives_root():
    from pathlib import Path
    root = Path("storage/final_release_archives")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _v993_safe_final_release_dir(release_name):
    root = _v993_final_releases_root().resolve()
    name = _v988_package_slug(release_name)
    path = (root / name).resolve()
    if not str(path).startswith(str(root)) or not path.exists() or not path.is_dir():
        abort(404)
    return path


def _v993_sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _v993_list_final_releases():
    from datetime import datetime, timezone
    root = _v993_final_releases_root()
    releases = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        publish_manifest_path = path / "PUBLISH_MANIFEST.json"
        publish_manifest = {}
        if publish_manifest_path.exists():
            try:
                publish_manifest = json.loads(publish_manifest_path.read_text())
            except Exception:
                publish_manifest = {}
        release_name = path.name
        zip_path = _v993_archives_root() / f"{release_name}.zip"
        tar_path = _v993_archives_root() / f"{release_name}.tar.gz"
        integrity_path = path / "INTEGRITY_MANIFEST.json"
        releases.append(
            {
                "release_name": release_name,
                "release_path": path.as_posix(),
                "publish_manifest_path": publish_manifest_path.as_posix() if publish_manifest_path.exists() else None,
                "integrity_manifest_path": integrity_path.as_posix() if integrity_path.exists() else None,
                "integrity_manifest_exists": integrity_path.exists(),
                "archive_zip_path": zip_path.as_posix() if zip_path.exists() else None,
                "archive_tar_path": tar_path.as_posix() if tar_path.exists() else None,
                "archive_zip_exists": zip_path.exists(),
                "archive_tar_exists": tar_path.exists(),
                "archive_zip_size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
                "archive_tar_size_bytes": tar_path.stat().st_size if tar_path.exists() else 0,
                "download_zip_url": f"/product/final-release/archive/download/{release_name}.zip" if zip_path.exists() else None,
                "download_tar_url": f"/product/final-release/archive/download/{release_name}.tar.gz" if tar_path.exists() else None,
                "status": publish_manifest.get("status"),
                "actor": publish_manifest.get("actor"),
                "published_at": publish_manifest.get("published_at"),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            }
        )
    releases.sort(key=lambda item: item.get("modified_at") or "", reverse=True)
    return releases


def _v993_build_integrity_manifest(release_name):
    from datetime import datetime, timezone
    from pathlib import Path
    release_dir = _v993_safe_final_release_dir(release_name)
    files = []
    for path in sorted(release_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(release_dir).as_posix()
        if rel == "INTEGRITY_MANIFEST.json":
            continue
        files.append({"path": rel, "size_bytes": path.stat().st_size, "sha256": _v993_sha256_file(path)})
    manifest = {
        "status": "ok",
        "version": "9.9.3",
        "release_name": release_dir.name,
        "release_path": release_dir.as_posix(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": files,
        "required_presence": {
            "release_notes": any(item["path"] == "RELEASE_NOTES.md" for item in files),
            "checklist": any(item["path"] == "FINAL_RELEASE_CHECKLIST.json" for item in files),
            "publish_manifest": any(item["path"] == "PUBLISH_MANIFEST.json" for item in files),
            "rc_manifest": any(item["path"].endswith("V9_9_0_RELEASE_CANDIDATE_MANIFEST.json") for item in files),
            "final_gate_manifest": any(item["path"].endswith("V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json") for item in files),
            "signoff_audit": any(item["path"].endswith("release_candidate_signoff_audit.json") for item in files),
            "package_zip": any(item["path"].endswith(".zip") for item in files),
        },
    }
    manifest["required_all_present"] = all(manifest["required_presence"].values())
    integrity_path = release_dir / "INTEGRITY_MANIFEST.json"
    integrity_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    latest = Path("release/V9_9_3_FINAL_RELEASE_INTEGRITY_MANIFEST.json")
    latest.parent.mkdir(exist_ok=True)
    latest.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    manifest["integrity_manifest_path"] = integrity_path.as_posix()
    manifest["latest_integrity_manifest_path"] = latest.as_posix()
    return manifest


def _v993_create_final_release_archives(release_name):
    import tarfile
    import zipfile
    from datetime import datetime, timezone
    from pathlib import Path
    release_dir = _v993_safe_final_release_dir(release_name)
    integrity = _v993_build_integrity_manifest(release_dir.name)
    archives_root = _v993_archives_root()
    zip_path = archives_root / f"{release_dir.name}.zip"
    tar_path = archives_root / f"{release_dir.name}.tar.gz"
    if zip_path.exists():
        zip_path.unlink()
    if tar_path.exists():
        tar_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(release_dir).as_posix())
    with tarfile.open(tar_path, "w:gz") as tf:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                tf.add(path, arcname=path.relative_to(release_dir).as_posix())
    with zipfile.ZipFile(zip_path) as zf:
        zip_entries = zf.namelist()
    with tarfile.open(tar_path, "r:gz") as tf:
        tar_entries = tf.getnames()
    seal = {
        "status": "ok",
        "version": "9.9.3",
        "release_name": release_dir.name,
        "release_path": release_dir.as_posix(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "integrity_manifest": integrity,
        "archive_zip_path": zip_path.as_posix(),
        "archive_tar_path": tar_path.as_posix(),
        "archive_zip_sha256": _v993_sha256_file(zip_path),
        "archive_tar_sha256": _v993_sha256_file(tar_path),
        "archive_zip_size_bytes": zip_path.stat().st_size,
        "archive_tar_size_bytes": tar_path.stat().st_size,
        "zip_entry_count": len(zip_entries),
        "tar_entry_count": len(tar_entries),
        "zip_entries": zip_entries,
        "tar_entries": tar_entries,
        "download_zip_url": f"/product/final-release/archive/download/{release_dir.name}.zip",
        "download_tar_url": f"/product/final-release/archive/download/{release_dir.name}.tar.gz",
    }
    latest_json = Path("release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.json")
    latest_md = Path("release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.md")
    latest_json.write_text(json.dumps(seal, indent=2, sort_keys=True))
    latest_md.write_text(
        "\n".join([
            "# v9.9.3 Final Release Archive Integrity Seal",
            "",
            f"Release: {release_dir.name}",
            f"Generated: {seal['generated_at']}",
            f"ZIP: `{seal['archive_zip_path']}`",
            f"ZIP SHA256: `{seal['archive_zip_sha256']}`",
            f"TAR: `{seal['archive_tar_path']}`",
            f"TAR SHA256: `{seal['archive_tar_sha256']}`",
            f"Integrity manifest: `{integrity.get('integrity_manifest_path')}`",
            f"Required all present: {integrity.get('required_all_present')}",
            "",
        ])
    )
    seal["artifacts_written"] = {
        "archive_seal_json": latest_json.as_posix(),
        "archive_seal_markdown": latest_md.as_posix(),
        "integrity_manifest_json": "release/V9_9_3_FINAL_RELEASE_INTEGRITY_MANIFEST.json",
    }
    return seal


@dashboard_bp.route("/api/v1/product/final-release/archives")
@login_required
def api_v993_final_release_archives():
    releases = _v993_list_final_releases()
    return jsonify({"status": "ok", "version": "9.9.3", "count": len(releases), "releases": releases})


@dashboard_bp.route("/api/v1/product/final-release/archive/<release_name>")
@login_required
def api_v993_final_release_archive_preview(release_name):
    release_dir = _v993_safe_final_release_dir(release_name)
    integrity = _v993_build_integrity_manifest(release_dir.name)
    return jsonify({"status": "ok", "version": "9.9.3", "release_name": release_dir.name, "integrity": integrity})


@dashboard_bp.route("/api/v1/product/final-release/archive/<release_name>/create", methods=["POST"])
@admin_required
def api_v993_create_final_release_archive(release_name):
    seal = _v993_create_final_release_archives(release_name)
    audit("product_final_release_archive_create", details=seal.get("artifacts_written"))
    return jsonify(seal)


@dashboard_bp.route("/product/final-release/archive")
@login_required
def product_final_release_archive_view():
    releases = _v993_list_final_releases()
    return render_template("product_final_release_archive.html", releases=releases)


@dashboard_bp.route("/product/final-release/archive/<release_name>/create", methods=["POST"])
@admin_required
def product_final_release_archive_create(release_name):
    seal = _v993_create_final_release_archives(release_name)
    audit("product_final_release_archive_create", details=seal.get("artifacts_written"))
    flash("Final release archive and integrity seal created.", "success")
    return redirect(url_for("dashboard.product_final_release_archive_view"))


@dashboard_bp.route("/product/final-release/archive/download/<path:filename>")
@login_required
def product_final_release_archive_download(filename):
    from flask import send_file
    from pathlib import Path
    root = _v993_archives_root().resolve()
    requested = Path(filename)
    if requested.is_absolute() or ".." in requested.parts:
        abort(404)
    path = (root / requested.name).resolve()
    if not str(path).startswith(str(root)) or not path.exists() or not path.is_file():
        abort(404)
    if not (path.name.endswith(".zip") or path.name.endswith(".tar.gz")):
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)
# ---- end v9.9.3 final release archive integrity seal ----



# ---- v9.9.4 Final Release Verification Console ----
def _v994_safe_archive_file(filename):
    from pathlib import Path

    root = _v993_archives_root().resolve()
    requested = Path(filename)
    if requested.is_absolute() or ".." in requested.parts:
        abort(404)

    path = (root / requested.name).resolve()
    if not str(path).startswith(str(root)) or not path.exists() or not path.is_file():
        abort(404)

    if not (path.name.endswith(".zip") or path.name.endswith(".tar.gz")):
        abort(404)

    return path


def _v994_verify_final_release(release_name=None):
    import tarfile
    import zipfile
    from datetime import datetime, timezone
    from pathlib import Path

    releases = _v993_list_final_releases()
    if release_name:
        releases = [item for item in releases if item.get("release_name") == _v988_package_slug(release_name)]

    if not releases:
        return {
            "status": "fail",
            "version": "9.9.4",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "release_name": _v988_package_slug(release_name) if release_name else None,
            "checks": [],
            "failures": ["no_final_release_found"],
            "summary": "No final release pack found to verify.",
        }

    release = releases[0]
    release_name = release["release_name"]
    release_dir = _v993_safe_final_release_dir(release_name)

    checks = []

    def add_check(key, label, ok, detail=None):
        checks.append(
            {
                "key": key,
                "label": label,
                "ok": bool(ok),
                "detail": detail or {},
            }
        )

    required_files = {
        "release_notes": release_dir / "RELEASE_NOTES.md",
        "checklist": release_dir / "FINAL_RELEASE_CHECKLIST.json",
        "publish_manifest": release_dir / "PUBLISH_MANIFEST.json",
        "integrity_manifest": release_dir / "INTEGRITY_MANIFEST.json",
    }

    for key, path in required_files.items():
        add_check(
            key,
            f"Required file exists: {path.name}",
            path.exists() and path.is_file(),
            {"path": path.as_posix()},
        )

    publish_manifest = _v992_load_json_file(release_dir / "PUBLISH_MANIFEST.json")
    final_gate = publish_manifest.get("final_gate", {}) if isinstance(publish_manifest, dict) else {}
    add_check(
        "publish_manifest_published",
        "Publish manifest status is published",
        isinstance(publish_manifest, dict) and publish_manifest.get("status") == "published",
        {"status": publish_manifest.get("status") if isinstance(publish_manifest, dict) else None},
    )
    add_check(
        "final_gate_approved",
        "Final gate is approved",
        final_gate.get("gate_status") == "approved" and final_gate.get("signoff", {}).get("approved") is True,
        {
            "gate_status": final_gate.get("gate_status"),
            "approved": final_gate.get("signoff", {}).get("approved"),
        },
    )

    integrity = _v992_load_json_file(release_dir / "INTEGRITY_MANIFEST.json")
    add_check(
        "integrity_manifest_present",
        "Integrity manifest is present and valid JSON",
        isinstance(integrity, dict),
        {"path": (release_dir / "INTEGRITY_MANIFEST.json").as_posix()},
    )

    if isinstance(integrity, dict):
        required_presence = integrity.get("required_presence", {})
        add_check(
            "integrity_required_presence",
            "Integrity manifest confirms required evidence presence",
            integrity.get("required_all_present") is True and all(required_presence.values()),
            {"required_presence": required_presence},
        )

        checksum_failures = []
        for item in integrity.get("files", []):
            path = release_dir / item.get("path", "")
            expected = item.get("sha256")
            actual = _v993_sha256_file(path) if path.exists() and path.is_file() else None
            if actual != expected:
                checksum_failures.append(
                    {
                        "path": item.get("path"),
                        "expected": expected,
                        "actual": actual,
                    }
                )
        add_check(
            "integrity_file_checksums",
            "All integrity-manifest file SHA256 checks match",
            not checksum_failures,
            {"failure_count": len(checksum_failures), "failures": checksum_failures[:10]},
        )

    zip_path = Path(release.get("archive_zip_path") or "")
    tar_path = Path(release.get("archive_tar_path") or "")
    if not zip_path.exists():
        zip_path = _v993_archives_root() / f"{release_name}.zip"
    if not tar_path.exists():
        tar_path = _v993_archives_root() / f"{release_name}.tar.gz"

    add_check("archive_zip_exists", "Archive ZIP exists", zip_path.exists() and zip_path.is_file(), {"path": zip_path.as_posix()})
    add_check("archive_tar_exists", "Archive TAR.GZ exists", tar_path.exists() and tar_path.is_file(), {"path": tar_path.as_posix()})

    seal = _v992_load_json_file("release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.json")
    if isinstance(seal, dict) and seal.get("release_name") == release_name:
        expected_zip = seal.get("archive_zip_sha256")
        expected_tar = seal.get("archive_tar_sha256")
    else:
        expected_zip = None
        expected_tar = None

    zip_sha = _v993_sha256_file(zip_path) if zip_path.exists() and zip_path.is_file() else None
    tar_sha = _v993_sha256_file(tar_path) if tar_path.exists() and tar_path.is_file() else None

    add_check(
        "archive_zip_checksum",
        "Archive ZIP checksum matches integrity seal when seal is available",
        zip_sha is not None and (expected_zip is None or zip_sha == expected_zip),
        {"expected": expected_zip, "actual": zip_sha},
    )
    add_check(
        "archive_tar_checksum",
        "Archive TAR.GZ checksum matches integrity seal when seal is available",
        tar_sha is not None and (expected_tar is None or tar_sha == expected_tar),
        {"expected": expected_tar, "actual": tar_sha},
    )

    zip_required = {
        "RELEASE_NOTES.md",
        "FINAL_RELEASE_CHECKLIST.json",
        "PUBLISH_MANIFEST.json",
        "INTEGRITY_MANIFEST.json",
    }
    zip_entries = set()
    tar_entries = set()
    if zip_path.exists() and zip_path.is_file():
        with zipfile.ZipFile(zip_path) as zf:
            zip_entries = set(zf.namelist())
    if tar_path.exists() and tar_path.is_file():
        with tarfile.open(tar_path, "r:gz") as tf:
            tar_entries = set(tf.getnames())

    add_check(
        "zip_required_files",
        "ZIP contains required final release files",
        zip_required.issubset(zip_entries)
        and any("V9_9_0_RELEASE_CANDIDATE_MANIFEST.json" in item for item in zip_entries)
        and any("V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json" in item for item in zip_entries)
        and any("release_candidate_signoff_audit.json" in item for item in zip_entries)
        and any(item.endswith(".zip") for item in zip_entries),
        {"entry_count": len(zip_entries)},
    )
    add_check(
        "tar_required_files",
        "TAR.GZ contains required final release files",
        zip_required.issubset(tar_entries)
        and any("V9_9_0_RELEASE_CANDIDATE_MANIFEST.json" in item for item in tar_entries)
        and any("V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json" in item for item in tar_entries)
        and any("release_candidate_signoff_audit.json" in item for item in tar_entries)
        and any(item.endswith(".zip") for item in tar_entries),
        {"entry_count": len(tar_entries)},
    )

    package_zips = []
    if isinstance(publish_manifest, dict):
        package_zips = publish_manifest.get("package_zips", [])
    package_zip_failures = []
    for item in package_zips:
        path = Path(item.get("package_path") or item.get("source") or "")
        if not path.exists() or not path.is_file():
            package_zip_failures.append({"path": path.as_posix()})
    add_check(
        "package_zips_present",
        "Package ZIPs referenced by publish manifest are present",
        len(package_zips) > 0 and not package_zip_failures,
        {"package_zip_count": len(package_zips), "failures": package_zip_failures},
    )

    failures = [check["key"] for check in checks if not check["ok"]]
    status = "pass" if not failures else "fail"

    result = {
        "status": status,
        "version": "9.9.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_name": release_name,
        "release_path": release_dir.as_posix(),
        "checks_total": len(checks),
        "checks_passed": sum(1 for check in checks if check["ok"]),
        "failures": failures,
        "checks": checks,
        "archive_zip_path": zip_path.as_posix(),
        "archive_tar_path": tar_path.as_posix(),
        "download_zip_url": f"/product/final-release/archive/download/{release_name}.zip",
        "download_tar_url": f"/product/final-release/archive/download/{release_name}.tar.gz",
        "recommended_next_action": "Final release verified." if status == "pass" else "Fix failed final release verification checks.",
    }

    release_dir_latest = Path("release")
    release_dir_latest.mkdir(exist_ok=True)
    latest_json = release_dir_latest / "V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json"
    latest_md = release_dir_latest / "V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.md"
    latest_json.write_text(json.dumps(result, indent=2, sort_keys=True))

    rows = [
        "# v9.9.4 Final Release Verification Report",
        "",
        f"Generated: {result['generated_at']}",
        f"Status: **{result['status']}**",
        f"Release: {release_name}",
        "",
        f"{result['checks_passed']}/{result['checks_total']} checks passed.",
        "",
        "## Failures",
        "",
        *([f"- {failure}" for failure in failures] or ["- None"]),
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        rows.extend(
            [
                f"### {check['label']}",
                "",
                f"- Key: `{check['key']}`",
                f"- Status: {'PASS' if check['ok'] else 'FAIL'}",
                "",
            ]
        )
    latest_md.write_text("\n".join(rows))
    result["artifacts_written"] = {"json": latest_json.as_posix(), "markdown": latest_md.as_posix()}
    return result


@dashboard_bp.route("/api/v1/product/final-release/verify")
@login_required
def api_v994_final_release_verify():
    release_name = request.args.get("release_name")
    return jsonify(_v994_verify_final_release(release_name=release_name))


@dashboard_bp.route("/product/final-release/verify")
@login_required
def product_final_release_verify_view():
    release_name = request.args.get("release_name")
    verification = _v994_verify_final_release(release_name=release_name)
    releases = _v993_list_final_releases()
    return render_template(
        "product_final_release_verify.html",
        verification=verification,
        releases=releases,
    )
# ---- end v9.9.4 final release verification console ----



# ---- v9.9.5 Final Release Lock + Distribution Readiness ----
def _v995_distribution_state_path():
    from pathlib import Path

    path = Path("storage/product_qa/final_release_distribution_state.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v995_distribution_audit_path():
    from pathlib import Path

    path = Path("storage/product_qa/final_release_distribution_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v995_load_distribution_state():
    path = _v995_distribution_state_path()
    if not path.exists():
        return {
            "version": "9.9.5",
            "locked": False,
            "ready": False,
            "decision": "pending",
            "release_name": None,
            "actor": None,
            "reason": "",
            "updated_at": None,
            "lock_manifest_sha256": None,
        }

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.5")
    data.setdefault("locked", False)
    data.setdefault("ready", False)
    data.setdefault("decision", "pending")
    data.setdefault("release_name", None)
    data.setdefault("actor", None)
    data.setdefault("reason", "")
    data.setdefault("updated_at", None)
    data.setdefault("lock_manifest_sha256", None)
    return data


def _v995_save_distribution_state(state):
    state["version"] = "9.9.5"
    _v995_distribution_state_path().write_text(json.dumps(state, indent=2, sort_keys=True))
    return state


def _v995_load_distribution_audit():
    path = _v995_distribution_audit_path()
    if not path.exists():
        return {"version": "9.9.5", "events": []}

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.5")
    data.setdefault("events", [])
    return data


def _v995_save_distribution_audit(data):
    data["version"] = "9.9.5"
    _v995_distribution_audit_path().write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v995_append_distribution_audit(action, actor, before, after, verification_status, reason=""):
    from datetime import datetime, timezone
    from uuid import uuid4

    data = _v995_load_distribution_audit()
    event = {
        "event_id": uuid4().hex,
        "version": "9.9.5",
        "action": action,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "verification_status": verification_status,
        "before": before,
        "after": after,
    }
    data.setdefault("events", []).append(event)
    _v995_save_distribution_audit(data)
    return event


def _v995_distribution_payload(release_name=None, actor=None):
    from datetime import datetime, timezone

    verification = _v994_verify_final_release(release_name=release_name)
    state = _v995_load_distribution_state()
    audit_data = _v995_load_distribution_audit()

    verification_pass = verification.get("status") == "pass"
    locked = bool(state.get("locked"))
    ready = bool(state.get("ready"))

    if not verification_pass:
        distribution_status = "blocked"
        can_mark_ready = False
        recommended = "Fix final release verification failures before distribution."
    elif ready and locked:
        distribution_status = "ready"
        can_mark_ready = False
        recommended = "Final release is locked and ready to distribute."
    elif locked and not ready:
        distribution_status = "locked"
        can_mark_ready = True
        recommended = "Release is locked. Mark ready when distribution review is complete."
    else:
        distribution_status = "verified"
        can_mark_ready = True
        recommended = "Final release verification passed. Lock and mark ready when approved."

    return {
        "status": "ok",
        "version": "9.9.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_name": verification.get("release_name"),
        "distribution_status": distribution_status,
        "can_mark_ready": can_mark_ready,
        "verification_status": verification.get("status"),
        "verification": verification,
        "state": state,
        "audit_event_count": len(audit_data.get("events", [])),
        "latest_audit_event": audit_data.get("events", [])[-1] if audit_data.get("events") else None,
        "recommended_next_action": recommended,
    }


def _v995_write_distribution_readiness_report(release_name=None, actor=None):
    from pathlib import Path

    payload = _v995_distribution_payload(release_name=release_name, actor=actor)
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V9_9_5_DISTRIBUTION_READINESS_REPORT.json"
    md_path = release_dir / "V9_9_5_DISTRIBUTION_READINESS_REPORT.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    state = payload.get("state", {})
    rows = [
        "# v9.9.5 Distribution Readiness Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['distribution_status']}**",
        f"Verification status: **{payload['verification_status']}**",
        f"Release: `{payload.get('release_name')}`",
        "",
        "## State",
        "",
        f"- Locked: {state.get('locked')}",
        f"- Ready: {state.get('ready')}",
        f"- Decision: {state.get('decision')}",
        f"- Actor: {state.get('actor')}",
        f"- Reason: {state.get('reason')}",
        f"- Lock manifest SHA256: `{state.get('lock_manifest_sha256')}`",
        "",
        "## Recommended Next Action",
        "",
        payload.get("recommended_next_action", ""),
        "",
        "## Verification",
        "",
        f"- Checks passed: {payload.get('verification', {}).get('checks_passed')}/{payload.get('verification', {}).get('checks_total')}",
        f"- Failures: {', '.join(payload.get('verification', {}).get('failures', [])) or 'None'}",
        "",
    ]
    md_path.write_text("\n".join(rows))

    payload["artifacts_written"] = {
        "json": json_path.as_posix(),
        "markdown": md_path.as_posix(),
    }
    return payload


def _v995_apply_distribution_decision(decision, release_name=None, actor=None, reason=""):
    from copy import deepcopy
    from datetime import datetime, timezone
    from pathlib import Path

    payload = _v995_distribution_payload(release_name=release_name, actor=actor)
    verification_status = payload.get("verification_status")
    before = deepcopy(_v995_load_distribution_state())

    decision = str(decision or "").strip().lower()
    if decision not in {"lock", "ready", "block", "reset"}:
        abort(400)

    if decision in {"lock", "ready"} and verification_status != "pass":
        after = deepcopy(before)
        event = _v995_append_distribution_audit(
            action=f"{decision}_denied",
            actor=actor,
            before=before,
            after=after,
            verification_status=verification_status,
            reason=reason or "Distribution decision denied because final verification is not passing.",
        )
        return {
            "status": "blocked",
            "version": "9.9.5",
            "decision": decision,
            "reason": "Final release verification must be pass before lock or ready.",
            "audit_event": event,
            "distribution": _v995_distribution_payload(release_name=release_name, actor=actor),
        }

    if decision == "lock":
        lock_manifest = Path("release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json")
        lock_sha = _v993_sha256_file(lock_manifest) if lock_manifest.exists() else None
        after = {
            "version": "9.9.5",
            "locked": True,
            "ready": False,
            "decision": "locked",
            "release_name": payload.get("release_name"),
            "actor": actor,
            "reason": reason or "Final release verification frozen and locked.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lock_manifest_sha256": lock_sha,
        }
    elif decision == "ready":
        lock_manifest = Path("release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json")
        lock_sha = _v993_sha256_file(lock_manifest) if lock_manifest.exists() else None
        after = {
            "version": "9.9.5",
            "locked": True,
            "ready": True,
            "decision": "ready",
            "release_name": payload.get("release_name"),
            "actor": actor,
            "reason": reason or "Final release locked and ready to distribute.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lock_manifest_sha256": before.get("lock_manifest_sha256") or lock_sha,
        }
    elif decision == "block":
        after = {
            "version": "9.9.5",
            "locked": False,
            "ready": False,
            "decision": "blocked",
            "release_name": payload.get("release_name"),
            "actor": actor,
            "reason": reason or "Distribution blocked by operator.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lock_manifest_sha256": before.get("lock_manifest_sha256"),
        }
    else:
        after = {
            "version": "9.9.5",
            "locked": False,
            "ready": False,
            "decision": "pending",
            "release_name": payload.get("release_name"),
            "actor": actor,
            "reason": reason or "Distribution reset to pending.",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "lock_manifest_sha256": None,
        }

    _v995_save_distribution_state(after)
    event = _v995_append_distribution_audit(
        action=f"distribution_{decision}",
        actor=actor,
        before=before,
        after=after,
        verification_status=verification_status,
        reason=after.get("reason", ""),
    )
    report = _v995_write_distribution_readiness_report(release_name=release_name, actor=actor)
    return {
        "status": "ok",
        "version": "9.9.5",
        "decision": decision,
        "state": after,
        "audit_event": event,
        "distribution": report,
    }


@dashboard_bp.route("/api/v1/product/final-release/distribution")
@login_required
def api_v995_distribution():
    release_name = request.args.get("release_name")
    return jsonify(_v995_distribution_payload(release_name=release_name, actor=session.get("user")))


@dashboard_bp.route("/api/v1/product/final-release/distribution/audit")
@login_required
def api_v995_distribution_audit():
    data = _v995_load_distribution_audit()
    return jsonify(
        {
            "status": "ok",
            "version": "9.9.5",
            "count": len(data.get("events", [])),
            "events": data.get("events", []),
            "audit_path": str(_v995_distribution_audit_path()),
        }
    )


@dashboard_bp.route("/api/v1/product/final-release/distribution/write", methods=["POST"])
@admin_required
def api_v995_distribution_write():
    payload = request.get_json(silent=True) or request.form
    release_name = payload.get("release_name") or None
    report = _v995_write_distribution_readiness_report(release_name=release_name, actor=session.get("user"))
    audit("product_distribution_readiness_write", details=report.get("artifacts_written"))
    return jsonify(report)


@dashboard_bp.route("/api/v1/product/final-release/distribution/decision", methods=["POST"])
@admin_required
def api_v995_distribution_decision():
    payload = request.get_json(silent=True) or request.form
    result = _v995_apply_distribution_decision(
        decision=payload.get("decision"),
        release_name=payload.get("release_name") or None,
        actor=session.get("user"),
        reason=payload.get("reason", ""),
    )
    audit("product_distribution_decision", details={"decision": payload.get("decision"), "status": result.get("status")})
    return jsonify(result)


@dashboard_bp.route("/product/final-release/distribution")
@login_required
def product_final_release_distribution_view():
    release_name = request.args.get("release_name")
    distribution = _v995_distribution_payload(release_name=release_name, actor=session.get("user"))
    audit_data = _v995_load_distribution_audit()
    releases = _v993_list_final_releases()
    return render_template(
        "product_final_release_distribution.html",
        distribution=distribution,
        audit_events=audit_data.get("events", []),
        releases=releases,
    )


@dashboard_bp.route("/product/final-release/distribution/write", methods=["POST"])
@admin_required
def product_final_release_distribution_write():
    release_name = request.form.get("release_name") or None
    report = _v995_write_distribution_readiness_report(release_name=release_name, actor=session.get("user"))
    audit("product_distribution_readiness_write", details=report.get("artifacts_written"))
    flash("Distribution readiness report written.", "success")
    return redirect(url_for("dashboard.product_final_release_distribution_view"))


@dashboard_bp.route("/product/final-release/distribution/decision", methods=["POST"])
@admin_required
def product_final_release_distribution_decision():
    release_name = request.form.get("release_name") or None
    decision = request.form.get("decision")
    reason = request.form.get("reason", "")
    result = _v995_apply_distribution_decision(
        decision=decision,
        release_name=release_name,
        actor=session.get("user"),
        reason=reason,
    )
    if result.get("status") == "blocked":
        flash("Distribution action blocked because final verification is not passing.", "error")
    else:
        flash("Distribution decision recorded.", "success")
    return redirect(url_for("dashboard.product_final_release_distribution_view"))
# ---- end v9.9.5 final release distribution readiness ----



# ---- v9.9.6 Final Product Release Dashboard + Version Freeze ----
def _v996_version_freeze_path():
    from pathlib import Path

    path = Path("release/V9_9_6_FINAL_PRODUCT_VERSION_FREEZE.json")
    path.parent.mkdir(exist_ok=True)
    return path


def _v996_final_release_index_paths():
    from pathlib import Path

    return {
        "json": Path("release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.json"),
        "markdown": Path("release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.md"),
    }


def _v996_final_dashboard_payload(actor=None, release_name=None):
    from datetime import datetime, timezone

    rc_manifest = _v992_load_json_file("release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json") or {}
    final_gate = _v991_final_gate_payload(actor=actor)
    archives = _v993_list_final_releases()

    if release_name:
        release_name = _v988_package_slug(release_name)
    elif archives:
        release_name = archives[0].get("release_name")

    verification = _v994_verify_final_release(release_name=release_name) if release_name else {
        "status": "fail",
        "release_name": None,
        "failures": ["no_release"],
        "checks_total": 0,
        "checks_passed": 0,
    }
    distribution = _v995_distribution_payload(release_name=release_name, actor=actor) if release_name else {
        "distribution_status": "blocked",
        "verification_status": "fail",
        "state": {},
        "recommended_next_action": "Publish and verify a final release first.",
    }

    archive = None
    for item in archives:
        if item.get("release_name") == release_name:
            archive = item
            break

    chain = {
        "release_candidate": {
            "status": rc_manifest.get("status"),
            "required_passed": rc_manifest.get("summary", {}).get("required_passed"),
            "required_total": rc_manifest.get("summary", {}).get("required_total"),
            "manifest": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
        },
        "final_gate": {
            "status": final_gate.get("gate_status"),
            "rc_status": final_gate.get("rc_status"),
            "approved": final_gate.get("signoff", {}).get("approved"),
            "manifest": "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json",
        },
        "final_release": {
            "status": "published" if archive else "missing",
            "release_name": release_name,
            "archive_zip": archive.get("archive_zip_path") if archive else None,
            "archive_tar": archive.get("archive_tar_path") if archive else None,
        },
        "archive": {
            "zip_exists": archive.get("archive_zip_exists") if archive else False,
            "tar_exists": archive.get("archive_tar_exists") if archive else False,
            "integrity_manifest_exists": archive.get("integrity_manifest_exists") if archive else False,
        },
        "verification": {
            "status": verification.get("status"),
            "checks_passed": verification.get("checks_passed"),
            "checks_total": verification.get("checks_total"),
            "failures": verification.get("failures", []),
        },
        "distribution": {
            "status": distribution.get("distribution_status"),
            "locked": distribution.get("state", {}).get("locked"),
            "ready": distribution.get("state", {}).get("ready"),
            "decision": distribution.get("state", {}).get("decision"),
        },
    }

    distribution_ready = (
        distribution.get("distribution_status") == "ready"
        and distribution.get("state", {}).get("ready") is True
        and verification.get("status") == "pass"
        and final_gate.get("gate_status") == "approved"
    )

    version_freeze = {
        "product": "SOCMINT Workbench",
        "final_version": "v9.9.6",
        "release_line": "v9.9.x final product release line",
        "release_name": release_name,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_by": actor,
        "distribution_ready": distribution_ready,
        "source_versions": {
            "release_candidate": "v9.9.0",
            "final_gate": "v9.9.1",
            "final_release_publisher": "v9.9.2",
            "archive_integrity": "v9.9.3",
            "verification": "v9.9.4",
            "distribution_readiness": "v9.9.5",
            "final_dashboard": "v9.9.6",
        },
    }

    return {
        "status": "ready" if distribution_ready else "not_ready",
        "version": "9.9.6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_name": release_name,
        "distribution_ready": distribution_ready,
        "version_freeze": version_freeze,
        "chain": chain,
        "rc_manifest": rc_manifest,
        "final_gate": final_gate,
        "verification": verification,
        "distribution": distribution,
        "archives": archives,
        "recommended_next_action": (
            "Final product release is distribution-ready."
            if distribution_ready
            else "Complete verification and distribution readiness before final release."
        ),
    }


def _v996_write_final_product_release_index(actor=None, release_name=None):
    payload = _v996_final_dashboard_payload(actor=actor, release_name=release_name)
    paths = _v996_final_release_index_paths()

    paths["json"].write_text(json.dumps(payload, indent=2, sort_keys=True))
    _v996_version_freeze_path().write_text(json.dumps(payload.get("version_freeze", {}), indent=2, sort_keys=True))

    chain = payload.get("chain", {})
    rows = [
        "# v9.9.6 Final Product Release Index",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Final version: **{payload['version_freeze']['final_version']}**",
        f"Release line: {payload['version_freeze']['release_line']}",
        f"Release name: `{payload.get('release_name')}`",
        f"Distribution ready: {payload.get('distribution_ready')}",
        "",
        "## Chain Summary",
        "",
        f"- Release Candidate: {chain.get('release_candidate', {}).get('status')} ({chain.get('release_candidate', {}).get('required_passed')}/{chain.get('release_candidate', {}).get('required_total')})",
        f"- Final Gate: {chain.get('final_gate', {}).get('status')} approved={chain.get('final_gate', {}).get('approved')}",
        f"- Final Release: {chain.get('final_release', {}).get('status')}",
        f"- Archive: zip={chain.get('archive', {}).get('zip_exists')} tar={chain.get('archive', {}).get('tar_exists')} integrity={chain.get('archive', {}).get('integrity_manifest_exists')}",
        f"- Verification: {chain.get('verification', {}).get('status')} ({chain.get('verification', {}).get('checks_passed')}/{chain.get('verification', {}).get('checks_total')})",
        f"- Distribution: {chain.get('distribution', {}).get('status')} ready={chain.get('distribution', {}).get('ready')}",
        "",
        "## Recommended Next Action",
        "",
        payload.get("recommended_next_action", ""),
        "",
    ]
    paths["markdown"].write_text("\n".join(rows))

    payload["artifacts_written"] = {
        "index_json": paths["json"].as_posix(),
        "index_markdown": paths["markdown"].as_posix(),
        "version_freeze": _v996_version_freeze_path().as_posix(),
    }
    return payload


@dashboard_bp.route("/api/v1/product/final")
@login_required
def api_v996_final_product_dashboard():
    release_name = request.args.get("release_name")
    return jsonify(_v996_final_dashboard_payload(actor=session.get("user"), release_name=release_name))


@dashboard_bp.route("/api/v1/product/final/write", methods=["POST"])
@admin_required
def api_v996_final_product_write():
    payload = request.get_json(silent=True) or request.form
    release_name = payload.get("release_name") or None
    result = _v996_write_final_product_release_index(actor=session.get("user"), release_name=release_name)
    audit("product_final_release_index_write", details=result.get("artifacts_written"))
    return jsonify(result)


@dashboard_bp.route("/product/final")
@login_required
def product_final_dashboard_view():
    release_name = request.args.get("release_name")
    payload = _v996_final_dashboard_payload(actor=session.get("user"), release_name=release_name)
    return render_template("product_final.html", payload=payload)


@dashboard_bp.route("/product/final/write", methods=["POST"])
@admin_required
def product_final_dashboard_write():
    release_name = request.form.get("release_name") or None
    result = _v996_write_final_product_release_index(actor=session.get("user"), release_name=release_name)
    audit("product_final_release_index_write", details=result.get("artifacts_written"))
    flash("Final product release index and version freeze written.", "success")
    return redirect(url_for("dashboard.product_final_dashboard_view"))
# ---- end v9.9.6 final product release dashboard ----



# ---- v9.9.7 Product Release Closeout + Operator Handoff Pack ----
def _v997_handoff_root(handoff_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    base = Path("storage/final_handoff")
    base.mkdir(parents=True, exist_ok=True)
    if not handoff_name:
        handoff_name = "v9_9_7_handoff_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return base / _v988_package_slug(handoff_name)


def _v997_required_handoff_sources():
    return [
        {
            "key": "release_candidate_manifest_json",
            "label": "Release Candidate Manifest JSON",
            "path": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
            "version": "v9.9.0",
        },
        {
            "key": "release_candidate_manifest_md",
            "label": "Release Candidate Manifest MD",
            "path": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.md",
            "version": "v9.9.0",
        },
        {
            "key": "final_gate_manifest_json",
            "label": "Final Gate Manifest JSON",
            "path": "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json",
            "version": "v9.9.1",
        },
        {
            "key": "final_gate_manifest_md",
            "label": "Final Gate Manifest MD",
            "path": "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.md",
            "version": "v9.9.1",
        },
        {
            "key": "final_release_notes",
            "label": "Final Release Notes",
            "path": "release/V9_9_2_FINAL_RELEASE_NOTES.md",
            "version": "v9.9.2",
        },
        {
            "key": "final_release_publish_manifest",
            "label": "Final Release Publish Manifest",
            "path": "release/V9_9_2_FINAL_RELEASE_PUBLISH_MANIFEST.json",
            "version": "v9.9.2",
        },
        {
            "key": "archive_seal_json",
            "label": "Archive Integrity Seal JSON",
            "path": "release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.json",
            "version": "v9.9.3",
        },
        {
            "key": "archive_seal_md",
            "label": "Archive Integrity Seal MD",
            "path": "release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.md",
            "version": "v9.9.3",
        },
        {
            "key": "integrity_manifest",
            "label": "Final Release Integrity Manifest",
            "path": "release/V9_9_3_FINAL_RELEASE_INTEGRITY_MANIFEST.json",
            "version": "v9.9.3",
        },
        {
            "key": "verification_report_json",
            "label": "Final Verification Report JSON",
            "path": "release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json",
            "version": "v9.9.4",
        },
        {
            "key": "verification_report_md",
            "label": "Final Verification Report MD",
            "path": "release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.md",
            "version": "v9.9.4",
        },
        {
            "key": "distribution_report_json",
            "label": "Distribution Readiness Report JSON",
            "path": "release/V9_9_5_DISTRIBUTION_READINESS_REPORT.json",
            "version": "v9.9.5",
        },
        {
            "key": "distribution_report_md",
            "label": "Distribution Readiness Report MD",
            "path": "release/V9_9_5_DISTRIBUTION_READINESS_REPORT.md",
            "version": "v9.9.5",
        },
        {
            "key": "final_dashboard_index_json",
            "label": "Final Dashboard Index JSON",
            "path": "release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.json",
            "version": "v9.9.6",
        },
        {
            "key": "final_dashboard_index_md",
            "label": "Final Dashboard Index MD",
            "path": "release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.md",
            "version": "v9.9.6",
        },
        {
            "key": "version_freeze",
            "label": "Version Freeze",
            "path": "release/V9_9_6_FINAL_PRODUCT_VERSION_FREEZE.json",
            "version": "v9.9.6",
        },
    ]


def _v997_handoff_preview(actor=None, release_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    final_payload = _v996_final_dashboard_payload(actor=actor, release_name=release_name)
    sources = []
    missing = []

    for item in _v997_required_handoff_sources():
        p = Path(item["path"])
        entry = {
            **item,
            "exists": p.exists() and p.is_file(),
            "size_bytes": p.stat().st_size if p.exists() and p.is_file() else 0,
            "sha256": _v993_sha256_file(p) if p.exists() and p.is_file() else None,
        }
        sources.append(entry)
        if not entry["exists"]:
            missing.append(item["key"])

    return {
        "status": "ready" if final_payload.get("status") == "ready" and not missing else "blocked",
        "version": "9.9.7",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_name": final_payload.get("release_name"),
        "final_dashboard_status": final_payload.get("status"),
        "distribution_ready": final_payload.get("distribution_ready"),
        "required_total": len(sources),
        "required_present": sum(1 for item in sources if item["exists"]),
        "missing": missing,
        "sources": sources,
        "final_dashboard": final_payload,
        "recommended_next_action": (
            "Generate operator handoff pack."
            if final_payload.get("status") == "ready" and not missing
            else "Complete final dashboard/distribution readiness and regenerate missing artifacts."
        ),
    }


def _v997_build_handoff_pack(handoff_name=None, actor=None, release_name=None):
    from pathlib import Path
    import shutil

    preview = _v997_handoff_preview(actor=actor, release_name=release_name)
    if preview.get("status") != "ready":
        return {
            "status": "blocked",
            "version": "9.9.7",
            "reason": "Operator handoff pack requires final dashboard ready status and all required v9.9.0-v9.9.6 artifacts.",
            "preview": preview,
        }

    root = _v997_handoff_root(handoff_name)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    copied = []
    for item in preview.get("sources", []):
        src = Path(item["path"])
        dest = root / "artifacts" / item["version"] / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(
            {
                "key": item["key"],
                "version": item["version"],
                "label": item["label"],
                "source": src.as_posix(),
                "package_path": dest.as_posix(),
                "size_bytes": dest.stat().st_size,
                "sha256": _v993_sha256_file(dest),
            }
        )

    checklist = [
        {
            "key": item["key"],
            "label": item["label"],
            "version": item["version"],
            "included": True,
            "package_path": item["package_path"],
            "sha256": item["sha256"],
        }
        for item in copied
    ]

    manifest = {
        "status": "ready",
        "version": "9.9.7",
        "handoff_name": root.name,
        "handoff_path": root.as_posix(),
        "actor": actor,
        "release_name": preview.get("release_name"),
        "final_dashboard_status": preview.get("final_dashboard_status"),
        "distribution_ready": preview.get("distribution_ready"),
        "required_total": preview.get("required_total"),
        "required_present": preview.get("required_present"),
        "copied_count": len(copied),
        "copied": copied,
        "checklist": checklist,
    }

    notes = [
        "# Product Release Closeout Operator Handoff Pack",
        "",
        f"Handoff: {root.name}",
        "Version: v9.9.7",
        f"Release: {preview.get('release_name')}",
        f"Status: {manifest['status']}",
        f"Distribution ready: {manifest['distribution_ready']}",
        "",
        "## Printable Handoff Checklist",
        "",
    ]
    for item in checklist:
        notes.append(f"- [x] {item['version']} — {item['label']} — `{item['package_path']}`")

    notes.extend(
        [
            "",
            "## Operator Closeout",
            "",
            "- Confirm final dashboard status is READY.",
            "- Confirm distribution readiness is ready.",
            "- Confirm archive/integrity seal is retained.",
            "- Confirm verification report is retained.",
            "- Confirm RC and final gate manifests are retained.",
            "",
        ]
    )

    (root / "HANDOFF_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    (root / "PRINTABLE_HANDOFF_CHECKLIST.md").write_text("\n".join(notes))
    (root / "README.md").write_text("\n".join(notes))

    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    latest_manifest = release_dir / "V9_9_7_OPERATOR_HANDOFF_MANIFEST.json"
    latest_checklist = release_dir / "V9_9_7_PRINTABLE_HANDOFF_CHECKLIST.md"
    latest_summary = release_dir / "V9_9_7_PRODUCT_RELEASE_CLOSEOUT_OPERATOR_HANDOFF.md"

    latest_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    latest_checklist.write_text("\n".join(notes))
    latest_summary.write_text(
        "\n".join(
            [
                "# v9.9.7 - Product Release Closeout + Operator Handoff Pack",
                "",
                f"Status: **{manifest['status']}**",
                f"Handoff: `{root.as_posix()}`",
                f"Release: `{preview.get('release_name')}`",
                f"Artifacts copied: {len(copied)}",
                "",
                "## Included Versions",
                "",
                "- v9.9.0 Release Candidate Manifest",
                "- v9.9.1 Final Product Gate",
                "- v9.9.2 Final Release Publisher",
                "- v9.9.3 Archive Integrity Seal",
                "- v9.9.4 Final Verification",
                "- v9.9.5 Distribution Readiness",
                "- v9.9.6 Final Product Dashboard + Version Freeze",
                "",
            ]
        )
    )

    manifest["artifacts_written"] = {
        "handoff_manifest": latest_manifest.as_posix(),
        "printable_checklist": latest_checklist.as_posix(),
        "summary": latest_summary.as_posix(),
        "handoff_dir": root.as_posix(),
    }
    return manifest


@dashboard_bp.route("/api/v1/product/final/handoff")
@login_required
def api_v997_handoff_preview():
    release_name = request.args.get("release_name")
    return jsonify(_v997_handoff_preview(actor=session.get("user"), release_name=release_name))


@dashboard_bp.route("/api/v1/product/final/handoff/build", methods=["POST"])
@admin_required
def api_v997_handoff_build():
    payload = request.get_json(silent=True) or request.form
    result = _v997_build_handoff_pack(
        handoff_name=payload.get("handoff_name") or None,
        actor=session.get("user"),
        release_name=payload.get("release_name") or None,
    )
    audit("product_operator_handoff_build", details=result.get("artifacts_written"))
    return jsonify(result)


@dashboard_bp.route("/product/final/handoff")
@login_required
def product_final_handoff_view():
    release_name = request.args.get("release_name")
    preview = _v997_handoff_preview(actor=session.get("user"), release_name=release_name)
    return render_template("product_final_handoff.html", preview=preview)


@dashboard_bp.route("/product/final/handoff/build", methods=["POST"])
@admin_required
def product_final_handoff_build():
    result = _v997_build_handoff_pack(
        handoff_name=request.form.get("handoff_name") or None,
        actor=session.get("user"),
        release_name=request.form.get("release_name") or None,
    )
    audit("product_operator_handoff_build", details=result.get("artifacts_written"))
    if result.get("status") == "ready":
        flash("Operator handoff pack built.", "success")
    else:
        flash("Operator handoff pack blocked until all required artifacts are present and final dashboard is ready.", "error")
    return redirect(url_for("dashboard.product_final_handoff_view"))
# ---- end v9.9.7 product release closeout handoff ----



# ---- v9.9.8 Final Release Self-Test + Post-Release Maintenance Gate ----
def _v998_maintenance_state_path():
    from pathlib import Path

    path = Path("storage/product_qa/post_release_maintenance_state.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v998_maintenance_audit_path():
    from pathlib import Path

    path = Path("storage/product_qa/post_release_maintenance_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v998_load_maintenance_state():
    path = _v998_maintenance_state_path()
    if not path.exists():
        return {
            "version": "9.9.8",
            "safe_to_start_v10": False,
            "decision": "pending",
            "actor": None,
            "reason": "",
            "release_name": None,
            "updated_at": None,
        }

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.8")
    data.setdefault("safe_to_start_v10", False)
    data.setdefault("decision", "pending")
    data.setdefault("actor", None)
    data.setdefault("reason", "")
    data.setdefault("release_name", None)
    data.setdefault("updated_at", None)
    return data


def _v998_save_maintenance_state(state):
    state["version"] = "9.9.8"
    _v998_maintenance_state_path().write_text(json.dumps(state, indent=2, sort_keys=True))
    return state


def _v998_load_maintenance_audit():
    path = _v998_maintenance_audit_path()
    if not path.exists():
        return {"version": "9.9.8", "events": []}

    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}

    if not isinstance(data, dict):
        data = {}

    data.setdefault("version", "9.9.8")
    data.setdefault("events", [])
    return data


def _v998_save_maintenance_audit(data):
    data["version"] = "9.9.8"
    _v998_maintenance_audit_path().write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v998_append_maintenance_audit(action, actor, before, after, self_test_status, reason=""):
    from datetime import datetime, timezone
    from uuid import uuid4

    data = _v998_load_maintenance_audit()
    event = {
        "event_id": uuid4().hex,
        "version": "9.9.8",
        "action": action,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "self_test_status": self_test_status,
        "before": before,
        "after": after,
    }
    data.setdefault("events", []).append(event)
    _v998_save_maintenance_audit(data)
    return event


def _v998_final_self_test_payload(actor=None, release_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    checks = []

    def add_check(key, label, ok, detail=None):
        checks.append(
            {
                "key": key,
                "label": label,
                "ok": bool(ok),
                "detail": detail or {},
            }
        )

    rc_manifest = _v992_load_json_file("release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json") or {}
    add_check(
        "release_candidate",
        "Release candidate manifest status is pass",
        rc_manifest.get("status") == "pass",
        {"status": rc_manifest.get("status"), "artifact": "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json"},
    )

    final_gate = _v991_final_gate_payload(actor=actor)
    add_check(
        "final_gate",
        "Final gate is approved",
        final_gate.get("gate_status") == "approved" and final_gate.get("signoff", {}).get("approved") is True,
        {"gate_status": final_gate.get("gate_status"), "approved": final_gate.get("signoff", {}).get("approved")},
    )

    archives = _v993_list_final_releases()
    if release_name:
        release_name = _v988_package_slug(release_name)
    elif archives:
        release_name = archives[0].get("release_name")

    archive = None
    for item in archives:
        if item.get("release_name") == release_name:
            archive = item
            break

    add_check(
        "archive",
        "Final release archive exists with ZIP, TAR, and integrity manifest",
        bool(archive)
        and archive.get("archive_zip_exists") is True
        and archive.get("archive_tar_exists") is True
        and archive.get("integrity_manifest_exists") is True,
        {"release_name": release_name, "archive": archive},
    )

    verification = _v994_verify_final_release(release_name=release_name) if release_name else {"status": "fail", "failures": ["no_release"]}
    add_check(
        "verification",
        "Final release verification status is pass",
        verification.get("status") == "pass",
        {
            "status": verification.get("status"),
            "checks_passed": verification.get("checks_passed"),
            "checks_total": verification.get("checks_total"),
            "failures": verification.get("failures", []),
        },
    )

    distribution = _v995_distribution_payload(release_name=release_name, actor=actor) if release_name else {
        "distribution_status": "blocked",
        "state": {},
    }
    add_check(
        "distribution",
        "Distribution readiness status is ready",
        distribution.get("distribution_status") == "ready" and distribution.get("state", {}).get("ready") is True,
        {
            "distribution_status": distribution.get("distribution_status"),
            "ready": distribution.get("state", {}).get("ready"),
            "locked": distribution.get("state", {}).get("locked"),
        },
    )

    final_dashboard = _v996_final_dashboard_payload(actor=actor, release_name=release_name) if release_name else {"status": "not_ready"}
    add_check(
        "final_dashboard",
        "Final product dashboard status is ready",
        final_dashboard.get("status") == "ready" and final_dashboard.get("distribution_ready") is True,
        {"status": final_dashboard.get("status"), "distribution_ready": final_dashboard.get("distribution_ready")},
    )

    handoff = _v997_handoff_preview(actor=actor, release_name=release_name) if release_name else {"status": "blocked"}
    add_check(
        "operator_handoff",
        "Operator handoff pack preview is ready",
        handoff.get("status") == "ready"
        and handoff.get("required_present") == handoff.get("required_total")
        and handoff.get("distribution_ready") is True,
        {
            "status": handoff.get("status"),
            "required_present": handoff.get("required_present"),
            "required_total": handoff.get("required_total"),
            "distribution_ready": handoff.get("distribution_ready"),
        },
    )

    handoff_manifest = _v992_load_json_file("release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json") or {}
    add_check(
        "operator_handoff_manifest",
        "Operator handoff manifest artifact exists and is ready",
        Path("release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json").exists()
        and handoff_manifest.get("status") == "ready",
        {"status": handoff_manifest.get("status"), "artifact": "release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json"},
    )

    maintenance = _v998_load_maintenance_state()
    failures = [check["key"] for check in checks if not check["ok"]]
    self_test_status = "pass" if not failures else "fail"
    v10_allowed = self_test_status == "pass" and handoff.get("status") == "ready"

    return {
        "status": self_test_status,
        "version": "9.9.8",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_name": release_name,
        "checks_total": len(checks),
        "checks_passed": sum(1 for check in checks if check["ok"]),
        "failures": failures,
        "checks": checks,
        "safe_to_start_v10_allowed": v10_allowed,
        "maintenance_state": maintenance,
        "rc_manifest": rc_manifest,
        "final_gate": final_gate,
        "archive": archive,
        "verification": verification,
        "distribution": distribution,
        "final_dashboard": final_dashboard,
        "handoff": handoff,
        "recommended_next_action": (
            "Safe to start v10 maintenance branch after operator confirmation."
            if v10_allowed
            else "Finish v9.9.7 handoff and all final release self-test checks before starting v10."
        ),
    }


def _v998_write_post_release_maintenance_report(actor=None, release_name=None):
    from pathlib import Path

    payload = _v998_final_self_test_payload(actor=actor, release_name=release_name)
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    json_path = release_dir / "V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.json"
    md_path = release_dir / "V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    rows = [
        "# v9.9.8 Post-Release Maintenance Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Release: `{payload.get('release_name')}`",
        f"Safe to start v10 allowed: {payload.get('safe_to_start_v10_allowed')}",
        "",
        f"{payload['checks_passed']}/{payload['checks_total']} self-test checks passed.",
        "",
        "## Failures",
        "",
        *([f"- {failure}" for failure in payload.get("failures", [])] or ["- None"]),
        "",
        "## Checks",
        "",
    ]
    for check in payload.get("checks", []):
        rows.extend(
            [
                f"### {check['label']}",
                "",
                f"- Key: `{check['key']}`",
                f"- Status: {'PASS' if check['ok'] else 'FAIL'}",
                "",
            ]
        )

    rows.extend(
        [
            "## Recommended Next Action",
            "",
            payload.get("recommended_next_action", ""),
            "",
        ]
    )

    md_path.write_text("\n".join(rows))
    payload["artifacts_written"] = {"json": json_path.as_posix(), "markdown": md_path.as_posix()}
    return payload


def _v998_apply_maintenance_decision(decision, actor=None, release_name=None, reason=""):
    from copy import deepcopy
    from datetime import datetime, timezone

    self_test = _v998_final_self_test_payload(actor=actor, release_name=release_name)
    before = deepcopy(_v998_load_maintenance_state())
    decision = str(decision or "").strip().lower()

    if decision not in {"safe_to_start_v10", "block_v10", "reset"}:
        abort(400)

    if decision == "safe_to_start_v10" and not self_test.get("safe_to_start_v10_allowed"):
        after = deepcopy(before)
        event = _v998_append_maintenance_audit(
            action="safe_to_start_v10_denied",
            actor=actor,
            before=before,
            after=after,
            self_test_status=self_test.get("status"),
            reason=reason or "v10 readiness denied because final self-test or v9.9.7 handoff is not ready.",
        )
        return {
            "status": "blocked",
            "version": "9.9.8",
            "decision": decision,
            "reason": "v10 readiness requires final self-test pass and v9.9.7 handoff ready.",
            "audit_event": event,
            "self_test": self_test,
        }

    if decision == "safe_to_start_v10":
        after = {
            "version": "9.9.8",
            "safe_to_start_v10": True,
            "decision": "safe_to_start_v10",
            "actor": actor,
            "reason": reason or "v9.9.x final release self-test passed and handoff is ready.",
            "release_name": self_test.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    elif decision == "block_v10":
        after = {
            "version": "9.9.8",
            "safe_to_start_v10": False,
            "decision": "blocked",
            "actor": actor,
            "reason": reason or "v10 start blocked by operator.",
            "release_name": self_test.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        after = {
            "version": "9.9.8",
            "safe_to_start_v10": False,
            "decision": "pending",
            "actor": actor,
            "reason": reason or "Post-release maintenance gate reset.",
            "release_name": self_test.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    _v998_save_maintenance_state(after)
    event = _v998_append_maintenance_audit(
        action=f"maintenance_{decision}",
        actor=actor,
        before=before,
        after=after,
        self_test_status=self_test.get("status"),
        reason=after.get("reason", ""),
    )
    report = _v998_write_post_release_maintenance_report(actor=actor, release_name=release_name)
    return {
        "status": "ok",
        "version": "9.9.8",
        "decision": decision,
        "state": after,
        "audit_event": event,
        "self_test": report,
    }


@dashboard_bp.route("/api/v1/product/final/self-test")
@login_required
def api_v998_final_self_test():
    release_name = request.args.get("release_name")
    return jsonify(_v998_final_self_test_payload(actor=session.get("user"), release_name=release_name))


@dashboard_bp.route("/api/v1/product/final/self-test/write", methods=["POST"])
@admin_required
def api_v998_final_self_test_write():
    payload = request.get_json(silent=True) or request.form
    release_name = payload.get("release_name") or None
    report = _v998_write_post_release_maintenance_report(actor=session.get("user"), release_name=release_name)
    audit("product_post_release_maintenance_write", details=report.get("artifacts_written"))
    return jsonify(report)


@dashboard_bp.route("/api/v1/product/final/self-test/maintenance", methods=["POST"])
@admin_required
def api_v998_maintenance_decision():
    payload = request.get_json(silent=True) or request.form
    result = _v998_apply_maintenance_decision(
        decision=payload.get("decision"),
        actor=session.get("user"),
        release_name=payload.get("release_name") or None,
        reason=payload.get("reason", ""),
    )
    audit("product_post_release_maintenance_decision", details={"decision": payload.get("decision"), "status": result.get("status")})
    return jsonify(result)


@dashboard_bp.route("/api/v1/product/final/self-test/maintenance-audit")
@login_required
def api_v998_maintenance_audit():
    data = _v998_load_maintenance_audit()
    return jsonify(
        {
            "status": "ok",
            "version": "9.9.8",
            "count": len(data.get("events", [])),
            "events": data.get("events", []),
            "audit_path": str(_v998_maintenance_audit_path()),
        }
    )


@dashboard_bp.route("/product/final/self-test")
@login_required
def product_final_self_test_view():
    release_name = request.args.get("release_name")
    self_test = _v998_final_self_test_payload(actor=session.get("user"), release_name=release_name)
    audit_data = _v998_load_maintenance_audit()
    return render_template(
        "product_final_self_test.html",
        self_test=self_test,
        audit_events=audit_data.get("events", []),
    )


@dashboard_bp.route("/product/final/self-test/write", methods=["POST"])
@admin_required
def product_final_self_test_write():
    release_name = request.form.get("release_name") or None
    report = _v998_write_post_release_maintenance_report(actor=session.get("user"), release_name=release_name)
    audit("product_post_release_maintenance_write", details=report.get("artifacts_written"))
    flash("Post-release maintenance report written.", "success")
    return redirect(url_for("dashboard.product_final_self_test_view"))


@dashboard_bp.route("/product/final/self-test/maintenance", methods=["POST"])
@admin_required
def product_final_self_test_maintenance():
    release_name = request.form.get("release_name") or None
    result = _v998_apply_maintenance_decision(
        decision=request.form.get("decision"),
        actor=session.get("user"),
        release_name=release_name,
        reason=request.form.get("reason", ""),
    )
    if result.get("status") == "blocked":
        flash("v10 readiness blocked until v9.9.7 handoff and final self-test are ready.", "error")
    else:
        flash("Post-release maintenance gate decision recorded.", "success")
    return redirect(url_for("dashboard.product_final_self_test_view"))
# ---- end v9.9.8 final release self-test maintenance gate ----



# ---- v9.9.9 Final v9 Line Closure + v10 Bootstrap Gate ----
def _v999_bootstrap_state_path():
    from pathlib import Path

    path = Path("storage/product_qa/v10_bootstrap_state.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v999_bootstrap_audit_path():
    from pathlib import Path

    path = Path("storage/product_qa/v10_bootstrap_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _v999_load_bootstrap_state():
    path = _v999_bootstrap_state_path()
    if not path.exists():
        return {
            "version": "9.9.9",
            "v9_closed": False,
            "v10_bootstrap_ready": False,
            "decision": "pending",
            "actor": None,
            "reason": "",
            "release_name": None,
            "updated_at": None,
            "closure_manifest_sha256": None,
            "bootstrap_manifest_sha256": None,
        }
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", "9.9.9")
    data.setdefault("v9_closed", False)
    data.setdefault("v10_bootstrap_ready", False)
    data.setdefault("decision", "pending")
    data.setdefault("actor", None)
    data.setdefault("reason", "")
    data.setdefault("release_name", None)
    data.setdefault("updated_at", None)
    data.setdefault("closure_manifest_sha256", None)
    data.setdefault("bootstrap_manifest_sha256", None)
    return data


def _v999_save_bootstrap_state(state):
    state["version"] = "9.9.9"
    _v999_bootstrap_state_path().write_text(json.dumps(state, indent=2, sort_keys=True))
    return state


def _v999_load_bootstrap_audit():
    path = _v999_bootstrap_audit_path()
    if not path.exists():
        return {"version": "9.9.9", "events": []}
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", "9.9.9")
    data.setdefault("events", [])
    return data


def _v999_save_bootstrap_audit(data):
    data["version"] = "9.9.9"
    _v999_bootstrap_audit_path().write_text(json.dumps(data, indent=2, sort_keys=True))
    return data


def _v999_append_bootstrap_audit(action, actor, before, after, safe_to_start_v10, reason=""):
    from datetime import datetime, timezone
    from uuid import uuid4

    data = _v999_load_bootstrap_audit()
    event = {
        "event_id": uuid4().hex,
        "version": "9.9.9",
        "action": action,
        "actor": actor,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "safe_to_start_v10": bool(safe_to_start_v10),
        "before": before,
        "after": after,
    }
    data.setdefault("events", []).append(event)
    _v999_save_bootstrap_audit(data)
    return event


def _v999_required_closure_artifacts():
    return [
        "release/V9_9_0_RELEASE_CANDIDATE_MANIFEST.json",
        "release/V9_9_1_FINAL_PRODUCT_GATE_MANIFEST.json",
        "release/V9_9_2_FINAL_RELEASE_PUBLISH_MANIFEST.json",
        "release/V9_9_3_FINAL_RELEASE_ARCHIVE_SEAL.json",
        "release/V9_9_4_FINAL_RELEASE_VERIFICATION_REPORT.json",
        "release/V9_9_5_DISTRIBUTION_READINESS_REPORT.json",
        "release/V9_9_6_FINAL_PRODUCT_RELEASE_INDEX.json",
        "release/V9_9_6_FINAL_PRODUCT_VERSION_FREEZE.json",
        "release/V9_9_7_OPERATOR_HANDOFF_MANIFEST.json",
        "release/V9_9_8_POST_RELEASE_MAINTENANCE_REPORT.json",
    ]


def _v999_closure_payload(actor=None, release_name=None):
    from datetime import datetime, timezone
    from pathlib import Path

    self_test = _v998_final_self_test_payload(actor=actor, release_name=release_name)
    maintenance = _v998_load_maintenance_state()
    state = _v999_load_bootstrap_state()

    artifacts = []
    missing = []
    for rel in _v999_required_closure_artifacts():
        path = Path(rel)
        exists = path.exists() and path.is_file()
        item = {
            "path": rel,
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else 0,
            "sha256": _v993_sha256_file(path) if exists else None,
        }
        artifacts.append(item)
        if not exists:
            missing.append(rel)

    safe_to_start_v10 = (
        self_test.get("status") == "pass"
        and self_test.get("safe_to_start_v10_allowed") is True
        and maintenance.get("safe_to_start_v10") is True
        and not missing
    )

    status = "closed" if safe_to_start_v10 and state.get("v9_closed") else ("ready" if safe_to_start_v10 else "blocked")

    return {
        "status": status,
        "version": "9.9.9",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "release_name": self_test.get("release_name"),
        "safe_to_start_v10": safe_to_start_v10,
        "v9_closed": bool(state.get("v9_closed")),
        "v10_bootstrap_ready": bool(state.get("v10_bootstrap_ready")),
        "self_test_status": self_test.get("status"),
        "maintenance_state": maintenance,
        "bootstrap_state": state,
        "required_total": len(artifacts),
        "required_present": sum(1 for item in artifacts if item["exists"]),
        "missing": missing,
        "artifacts": artifacts,
        "self_test": self_test,
        "recommended_next_action": (
            "Close v9.9.x and approve v10 bootstrap."
            if safe_to_start_v10 and not state.get("v10_bootstrap_ready")
            else "v9.9.x is closed and v10 bootstrap is ready."
            if state.get("v10_bootstrap_ready")
            else "Complete v9.9.8 safe-to-start-v10 gate before v10 bootstrap."
        ),
    }


def _v999_write_closure_and_bootstrap_manifests(actor=None, release_name=None):
    from pathlib import Path

    payload = _v999_closure_payload(actor=actor, release_name=release_name)
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)

    closure_json = release_dir / "V9_9_9_FINAL_V9_CLOSURE_MANIFEST.json"
    closure_md = release_dir / "V9_9_9_FINAL_V9_CLOSURE_MANIFEST.md"
    bootstrap_json = release_dir / "V9_9_9_V10_BOOTSTRAP_READINESS_MANIFEST.json"
    bootstrap_md = release_dir / "V9_9_9_V10_BOOTSTRAP_READINESS_MANIFEST.md"

    closure_json.write_text(json.dumps(payload, indent=2, sort_keys=True))

    closure_rows = [
        "# v9.9.9 Final v9 Line Closure Manifest",
        "",
        f"Generated: {payload['generated_at']}",
        f"Status: **{payload['status']}**",
        f"Release: `{payload.get('release_name')}`",
        f"Safe to start v10: {payload.get('safe_to_start_v10')}",
        f"v9 closed: {payload.get('v9_closed')}",
        f"v10 bootstrap ready: {payload.get('v10_bootstrap_ready')}",
        "",
        f"Artifacts present: {payload.get('required_present')}/{payload.get('required_total')}",
        "",
        "## Missing",
        "",
        *([f"- `{x}`" for x in payload.get("missing", [])] or ["- None"]),
        "",
        "## Required Artifacts",
        "",
    ]
    for item in payload.get("artifacts", []):
        closure_rows.append(f"- {'PRESENT' if item['exists'] else 'MISSING'} `{item['path']}` sha256=`{item.get('sha256')}`")
    closure_md.write_text("\n".join(closure_rows))

    bootstrap = {
        "status": "ready" if payload.get("v10_bootstrap_ready") else ("allowed" if payload.get("safe_to_start_v10") else "blocked"),
        "version": "9.9.9",
        "generated_at": payload["generated_at"],
        "release_name": payload.get("release_name"),
        "safe_to_start_v10": payload.get("safe_to_start_v10"),
        "v9_closed": payload.get("v9_closed"),
        "v10_bootstrap_ready": payload.get("v10_bootstrap_ready"),
        "rules": {
            "requires_v998_safe_to_start_v10": True,
            "requires_all_v9_closure_artifacts": True,
            "requires_operator_bootstrap_decision": True,
        },
        "recommended_next_action": payload.get("recommended_next_action"),
    }
    bootstrap_json.write_text(json.dumps(bootstrap, indent=2, sort_keys=True))
    bootstrap_md.write_text(
        "\n".join(
            [
                "# v9.9.9 v10 Bootstrap Readiness Manifest",
                "",
                f"Generated: {bootstrap['generated_at']}",
                f"Status: **{bootstrap['status']}**",
                f"Release: `{bootstrap.get('release_name')}`",
                f"Safe to start v10: {bootstrap.get('safe_to_start_v10')}",
                f"v9 closed: {bootstrap.get('v9_closed')}",
                f"v10 bootstrap ready: {bootstrap.get('v10_bootstrap_ready')}",
                "",
                "## Recommended Next Action",
                "",
                bootstrap.get("recommended_next_action", ""),
                "",
            ]
        )
    )

    payload["artifacts_written"] = {
        "closure_json": closure_json.as_posix(),
        "closure_markdown": closure_md.as_posix(),
        "bootstrap_json": bootstrap_json.as_posix(),
        "bootstrap_markdown": bootstrap_md.as_posix(),
    }
    return payload


def _v999_apply_bootstrap_decision(decision, actor=None, release_name=None, reason=""):
    from copy import deepcopy
    from datetime import datetime, timezone
    from pathlib import Path

    payload = _v999_closure_payload(actor=actor, release_name=release_name)
    before = deepcopy(_v999_load_bootstrap_state())
    decision = str(decision or "").strip().lower()

    if decision not in {"close_v9", "approve_v10_bootstrap", "block_v10_bootstrap", "reset"}:
        abort(400)

    if decision in {"close_v9", "approve_v10_bootstrap"} and not payload.get("safe_to_start_v10"):
        after = deepcopy(before)
        event = _v999_append_bootstrap_audit(
            action=f"{decision}_denied",
            actor=actor,
            before=before,
            after=after,
            safe_to_start_v10=False,
            reason=reason or "Denied because v9.9.8 safe-to-start-v10 gate is not true.",
        )
        return {
            "status": "blocked",
            "version": "9.9.9",
            "decision": decision,
            "reason": "v10 bootstrap requires v9.9.8 safe-to-start-v10 gate to be true.",
            "audit_event": event,
            "closure": payload,
        }

    closure_manifest = Path("release/V9_9_9_FINAL_V9_CLOSURE_MANIFEST.json")
    bootstrap_manifest = Path("release/V9_9_9_V10_BOOTSTRAP_READINESS_MANIFEST.json")

    if decision == "close_v9":
        after = {
            "version": "9.9.9",
            "v9_closed": True,
            "v10_bootstrap_ready": False,
            "decision": "v9_closed",
            "actor": actor,
            "reason": reason or "v9.9.x line closed.",
            "release_name": payload.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "closure_manifest_sha256": _v993_sha256_file(closure_manifest) if closure_manifest.exists() else None,
            "bootstrap_manifest_sha256": _v993_sha256_file(bootstrap_manifest) if bootstrap_manifest.exists() else None,
        }
    elif decision == "approve_v10_bootstrap":
        after = {
            "version": "9.9.9",
            "v9_closed": True,
            "v10_bootstrap_ready": True,
            "decision": "v10_bootstrap_ready",
            "actor": actor,
            "reason": reason or "v9.9.x closed and v10 bootstrap approved.",
            "release_name": payload.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "closure_manifest_sha256": _v993_sha256_file(closure_manifest) if closure_manifest.exists() else before.get("closure_manifest_sha256"),
            "bootstrap_manifest_sha256": _v993_sha256_file(bootstrap_manifest) if bootstrap_manifest.exists() else before.get("bootstrap_manifest_sha256"),
        }
    elif decision == "block_v10_bootstrap":
        after = {
            "version": "9.9.9",
            "v9_closed": before.get("v9_closed", False),
            "v10_bootstrap_ready": False,
            "decision": "v10_bootstrap_blocked",
            "actor": actor,
            "reason": reason or "v10 bootstrap blocked by operator.",
            "release_name": payload.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "closure_manifest_sha256": before.get("closure_manifest_sha256"),
            "bootstrap_manifest_sha256": before.get("bootstrap_manifest_sha256"),
        }
    else:
        after = {
            "version": "9.9.9",
            "v9_closed": False,
            "v10_bootstrap_ready": False,
            "decision": "pending",
            "actor": actor,
            "reason": reason or "v10 bootstrap gate reset.",
            "release_name": payload.get("release_name"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "closure_manifest_sha256": None,
            "bootstrap_manifest_sha256": None,
        }

    _v999_save_bootstrap_state(after)
    event = _v999_append_bootstrap_audit(
        action=f"bootstrap_{decision}",
        actor=actor,
        before=before,
        after=after,
        safe_to_start_v10=payload.get("safe_to_start_v10"),
        reason=after.get("reason", ""),
    )
    manifests = _v999_write_closure_and_bootstrap_manifests(actor=actor, release_name=release_name)
    return {
        "status": "ok",
        "version": "9.9.9",
        "decision": decision,
        "state": after,
        "audit_event": event,
        "closure": manifests,
    }


@dashboard_bp.route("/api/v1/product/final/v10-bootstrap")
@login_required
def api_v999_v10_bootstrap():
    release_name = request.args.get("release_name")
    return jsonify(_v999_closure_payload(actor=session.get("user"), release_name=release_name))


@dashboard_bp.route("/api/v1/product/final/v10-bootstrap/write", methods=["POST"])
@admin_required
def api_v999_v10_bootstrap_write():
    payload = request.get_json(silent=True) or request.form
    result = _v999_write_closure_and_bootstrap_manifests(
        actor=session.get("user"),
        release_name=payload.get("release_name") or None,
    )
    audit("product_v9_closure_v10_bootstrap_write", details=result.get("artifacts_written"))
    return jsonify(result)


@dashboard_bp.route("/api/v1/product/final/v10-bootstrap/decision", methods=["POST"])
@admin_required
def api_v999_v10_bootstrap_decision():
    payload = request.get_json(silent=True) or request.form
    result = _v999_apply_bootstrap_decision(
        decision=payload.get("decision"),
        actor=session.get("user"),
        release_name=payload.get("release_name") or None,
        reason=payload.get("reason", ""),
    )
    audit("product_v10_bootstrap_decision", details={"decision": payload.get("decision"), "status": result.get("status")})
    return jsonify(result)


@dashboard_bp.route("/api/v1/product/final/v10-bootstrap/audit")
@login_required
def api_v999_v10_bootstrap_audit():
    data = _v999_load_bootstrap_audit()
    return jsonify(
        {
            "status": "ok",
            "version": "9.9.9",
            "count": len(data.get("events", [])),
            "events": data.get("events", []),
            "audit_path": str(_v999_bootstrap_audit_path()),
        }
    )


@dashboard_bp.route("/product/final/v10-bootstrap")
@login_required
def product_v10_bootstrap_view():
    release_name = request.args.get("release_name")
    payload = _v999_closure_payload(actor=session.get("user"), release_name=release_name)
    audit_data = _v999_load_bootstrap_audit()
    return render_template(
        "product_v10_bootstrap.html",
        payload=payload,
        audit_events=audit_data.get("events", []),
    )


@dashboard_bp.route("/product/final/v10-bootstrap/write", methods=["POST"])
@admin_required
def product_v10_bootstrap_write():
    result = _v999_write_closure_and_bootstrap_manifests(
        actor=session.get("user"),
        release_name=request.form.get("release_name") or None,
    )
    audit("product_v9_closure_v10_bootstrap_write", details=result.get("artifacts_written"))
    flash("v9 closure and v10 bootstrap manifests written.", "success")
    return redirect(url_for("dashboard.product_v10_bootstrap_view"))


@dashboard_bp.route("/product/final/v10-bootstrap/decision", methods=["POST"])
@admin_required
def product_v10_bootstrap_decision():
    result = _v999_apply_bootstrap_decision(
        decision=request.form.get("decision"),
        actor=session.get("user"),
        release_name=request.form.get("release_name") or None,
        reason=request.form.get("reason", ""),
    )
    if result.get("status") == "blocked":
        flash("v10 bootstrap blocked until v9.9.8 safe-to-start-v10 is true.", "error")
    else:
        flash("v10 bootstrap decision recorded.", "success")
    return redirect(url_for("dashboard.product_v10_bootstrap_view"))
# ---- end v9.9.9 final v9 line closure v10 bootstrap gate ----
