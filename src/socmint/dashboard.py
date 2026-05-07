import functools
import json
import os
import re
import secrets

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


@dashboard_bp.route("/about")
@login_required
def about():
    return render_template("about.html")


@dashboard_bp.route("/healthz")
def healthz():
    if request.remote_addr not in {"127.0.0.1", "::1", "localhost"}:
        abort(404)
    return {"status": "ok"}


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
