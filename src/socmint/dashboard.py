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
from .evidence import connector_quality_metrics
from .evidence import get_assertion_evidence
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
    return render_template("dashboard.html", targets=targets)


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
    return render_template("jobs.html", jobs=jobs)


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
