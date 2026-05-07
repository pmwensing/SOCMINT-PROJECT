import datetime
import json
import os

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from .config import load_settings

Base = declarative_base()


def utc_now():
    return datetime.datetime.now(datetime.UTC)


class Target(Base):
    __tablename__ = "targets"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    value = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    results = relationship(
        "Result", back_populates="target", cascade="all, delete-orphan"
    )
    profiles = relationship(
        "Profile", back_populates="target", cascade="all, delete-orphan"
    )
    media = relationship("Media", back_populates="target", cascade="all, delete-orphan")


class Tool(Base):
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    results = relationship(
        "Result", back_populates="tool", cascade="all, delete-orphan"
    )


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    tool_id = Column(Integer, ForeignKey("tools.id"), nullable=False)
    data = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    target = relationship("Target", back_populates="results")
    tool = relationship("Tool", back_populates="results")


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    source = Column(String, nullable=False)
    raw = Column(Text, nullable=False)
    normalized = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    target = relationship("Target", back_populates="profiles")


class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    source_url = Column(String, nullable=False)
    path = Column(String, nullable=False)
    checksum = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    target = relationship("Target", back_populates="media")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(String, default="viewer", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class RateLimitAttempt(Base):
    __tablename__ = "rate_limit_attempts"
    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)
    target_value = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ConnectorRun(Base):
    __tablename__ = "connector_runs"
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)
    target_value = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    connector = Column(String, nullable=False)
    status = Column(String, nullable=False)
    command = Column(Text, nullable=True)
    raw_result = Column(Text, nullable=False)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True)
    connector_run_id = Column(Integer, ForeignKey("connector_runs.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)
    source = Column(String, nullable=False)
    type = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(String, nullable=False, default="0.5")
    context = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class ScanJob(Base):
    __tablename__ = "scan_jobs"
    id = Column(Integer, primary_key=True)
    target_value = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    tools = Column(Text, nullable=False)
    enrich = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="queued", nullable=False)
    requested_by = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


Index(
    "ix_rate_limit_action_key_created_at",
    RateLimitAttempt.action,
    RateLimitAttempt.key,
    RateLimitAttempt.created_at,
)
Index("ix_audit_logs_created_at", AuditLog.created_at)
Index("ix_audit_logs_actor_action", AuditLog.actor, AuditLog.action)
Index("ix_targets_created_at", Target.created_at)
Index("ix_scan_jobs_status_created_at", ScanJob.status, ScanJob.created_at)
Index(
    "ix_connector_runs_connector_created_at",
    ConnectorRun.connector,
    ConnectorRun.created_at,
)
Index(
    "ix_findings_type_created_at",
    Finding.type,
    Finding.created_at,
)


def get_engine(database_url=None):
    settings = load_settings(require_secret=False, database_url=database_url)
    if settings.database_url.startswith("sqlite:///"):
        sqlite_path = settings.database_url.replace("sqlite:///", "", 1)
        if sqlite_path and sqlite_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
    return create_engine(settings.database_url, pool_pre_ping=True)


engine = None
Session = None


def configure_database(database_url=None, create_schema=True):
    global engine, Session
    engine = get_engine(database_url)
    Session = sessionmaker(bind=engine)
    if create_schema:
        Base.metadata.create_all(engine)
    return engine


def ensure_configured():
    if Session is None:
        configure_database()


def check_ready():
    ensure_configured()
    session = Session()
    try:
        session.execute(text("SELECT 1"))
        return True
    finally:
        session.close()


def get_user_by_username(username):
    ensure_configured()
    session = Session()
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        session.close()


def create_user(username, password, is_admin=False, role=None):
    ensure_configured()
    if get_user_by_username(username):
        return None
    session = Session()
    try:
        password_hash = generate_password_hash(password)
        user = User(
            username=username,
            password_hash=password_hash,
            is_admin=is_admin,
            role=role or ("admin" if is_admin else "viewer"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def list_users():
    ensure_configured()
    session = Session()
    try:
        return session.query(User).order_by(User.created_at.desc()).all()
    finally:
        session.close()


def update_user(user_id, is_admin=None, is_active=None, password=None, role=None):
    ensure_configured()
    session = Session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return None
        if is_admin is not None:
            user.is_admin = bool(is_admin)
            if user.is_admin:
                user.role = "admin"
        if is_active is not None:
            user.is_active = bool(is_active)
        if role:
            user.role = role
        if password:
            user.password_hash = generate_password_hash(password)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user and user.is_active and check_password_hash(user.password_hash, password):
        return user
    return None


def change_user_password(username, current_password, new_password):
    ensure_configured()
    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()
        if (
            not user
            or not user.is_active
            or not check_password_hash(user.password_hash, current_password)
        ):
            return False
        user.password_hash = generate_password_hash(new_password)
        session.commit()
        return True
    finally:
        session.close()


def count_recent_rate_limit_attempts(action, key, window_seconds):
    ensure_configured()
    cutoff = utc_now() - datetime.timedelta(seconds=window_seconds)
    session = Session()
    try:
        session.query(RateLimitAttempt).filter(
            RateLimitAttempt.created_at < cutoff
        ).delete()
        session.commit()
        return (
            session.query(RateLimitAttempt)
            .filter_by(action=action, key=key)
            .filter(RateLimitAttempt.created_at >= cutoff)
            .count()
        )
    finally:
        session.close()


def record_rate_limit_attempt(action, key):
    ensure_configured()
    session = Session()
    try:
        session.add(RateLimitAttempt(action=action, key=key))
        session.commit()
    finally:
        session.close()


def clear_rate_limit_attempts(action, key):
    ensure_configured()
    session = Session()
    try:
        session.query(RateLimitAttempt).filter_by(action=action, key=key).delete()
        session.commit()
    finally:
        session.close()


def record_audit_event(action, actor=None, target=None, ip_address=None, details=None):
    ensure_configured()
    session = Session()
    try:
        target_id = getattr(target, "id", None)
        target_value = getattr(target, "value", None)
        event = AuditLog(
            actor=actor,
            action=action,
            target_id=target_id,
            target_value=target_value,
            ip_address=ip_address,
            details=json.dumps(details or {}),
        )
        session.add(event)
        session.commit()
        return event
    finally:
        session.close()


def get_audit_events(limit=100, offset=0, actor=None, action=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(AuditLog)
        if actor:
            query = query.filter(AuditLog.actor == actor)
        if action:
            query = query.filter(AuditLog.action == action)
        return (
            query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    finally:
        session.close()


def count_audit_events(actor=None, action=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(AuditLog)
        if actor:
            query = query.filter(AuditLog.actor == actor)
        if action:
            query = query.filter(AuditLog.action == action)
        return query.count()
    finally:
        session.close()


def create_scan_job(
    target_value, target_type, tools=None, enrich=False, requested_by=None
):
    ensure_configured()
    session = Session()
    try:
        job = ScanJob(
            target_value=target_value,
            target_type=target_type,
            tools=json.dumps(sorted(tools or [])),
            enrich=bool(enrich),
            requested_by=requested_by,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    finally:
        session.close()


def list_scan_jobs(limit=100):
    ensure_configured()
    session = Session()
    try:
        return (
            session.query(ScanJob)
            .order_by(ScanJob.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        session.close()


def get_scan_job(job_id):
    ensure_configured()
    session = Session()
    try:
        return session.query(ScanJob).filter_by(id=job_id).first()
    finally:
        session.close()


def claim_next_scan_job():
    ensure_configured()
    session = Session()
    try:
        job = (
            session.query(ScanJob)
            .filter_by(status="queued")
            .order_by(ScanJob.created_at.asc())
            .first()
        )
        if not job:
            return None
        job.status = "running"
        job.started_at = utc_now()
        session.commit()
        session.refresh(job)
        snapshot = {
            "id": job.id,
            "target_value": job.target_value,
            "target_type": job.target_type,
            "tools": json.loads(job.tools or "[]"),
            "enrich": job.enrich,
        }
        return snapshot
    finally:
        session.close()


def finish_scan_job(job_id, status, error=None, target_id=None):
    ensure_configured()
    session = Session()
    try:
        job = session.query(ScanJob).filter_by(id=job_id).first()
        if not job:
            return None
        job.status = status
        job.error = error
        job.target_id = target_id
        job.finished_at = utc_now()
        session.commit()
        session.refresh(job)
        return job
    finally:
        session.close()


def delete_dossier(target_id):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(id=target_id).first()
        if not target:
            return None
        snapshot = {"id": target.id, "value": target.value, "type": target.type}
        session.delete(target)
        session.commit()
        return snapshot
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_dossier(dossier):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(value=dossier["target"]).first()
        if not target:
            target = Target(type=dossier.get("type"), value=dossier["target"])
            session.add(target)
            session.commit()

        for tool_name, data in dossier.get("data", {}).items():
            tool = session.query(Tool).filter_by(name=tool_name).first()
            if not tool:
                tool = Tool(name=tool_name)
                session.add(tool)
                session.commit()

            result = Result(target_id=target.id, tool_id=tool.id, data=json.dumps(data))
            session.add(result)

        session.commit()

        profile_map = {}
        for profile in dossier.get("profiles", []):
            profile_record = Profile(
                target_id=target.id,
                source=profile.get("url", profile.get("source", "unknown")),
                raw=json.dumps(profile.get("raw", {})),
                normalized=json.dumps(
                    {
                        "title": profile.get("title"),
                        "description": profile.get("description"),
                        "site_name": profile.get("site_name"),
                        "url": profile.get("url"),
                        "image": profile.get("image"),
                    }
                ),
            )
            session.add(profile_record)
            session.commit()
            profile_map[profile.get("url")] = profile_record

        for media_item in dossier.get("media", []):
            existing = (
                session.query(Media)
                .filter_by(target_id=target.id, source_url=media_item.get("url"))
                .first()
            )
            if existing:
                continue
            profile_id = None
            if media_item.get("url") in profile_map:
                profile_id = profile_map[media_item.get("url")].id
            session.add(
                Media(
                    target_id=target.id,
                    profile_id=profile_id,
                    source_url=media_item.get("url"),
                    path=media_item.get("path"),
                    checksum=media_item.get("checksum"),
                    content_type=media_item.get("content_type"),
                )
            )

        session.commit()

        for tool_name, data in dossier.get("data", {}).items():
            if isinstance(data, dict) and data.get("connector"):
                record_connector_run(
                    target_value=dossier["target"],
                    target_type=dossier.get("type"),
                    connector=tool_name,
                    raw_result=data,
                    target_id=target.id,
                )

        return target.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_dossier(target_value):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(value=target_value).first()
        if not target:
            return None

        dossier = {
            "target": target.value,
            "type": target.type,
            "data": {},
            "profiles": [],
            "media": [],
        }

        for result in target.results:
            dossier["data"][result.tool.name] = json.loads(result.data)

        for profile in target.profiles:
            dossier["profiles"].append(
                {
                    "source": profile.source,
                    "raw": json.loads(profile.raw or "{}"),
                    "normalized": json.loads(profile.normalized or "{}"),
                }
            )

        for media in target.media:
            dossier["media"].append(
                {
                    "source_url": media.source_url,
                    "path": media.path,
                    "checksum": media.checksum,
                    "content_type": media.content_type,
                }
            )

        return dossier
    finally:
        session.close()


def record_connector_run(
    target_value,
    target_type,
    connector,
    raw_result,
    target_id=None,
):
    ensure_configured()
    session = Session()
    try:
        if isinstance(raw_result, dict):
            status = raw_result.get("status", "unknown")
        else:
            status = "unknown"
        if isinstance(raw_result, dict):
            command = raw_result.get("command")
        else:
            command = None
        if isinstance(raw_result, dict):
            error = raw_result.get("stderr")
        else:
            error = None
        run = ConnectorRun(
            target_id=target_id,
            target_value=target_value,
            target_type=target_type,
            connector=connector,
            status=status,
            command=json.dumps(command or []),
            raw_result=json.dumps(raw_result),
            error=error,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        findings = []
        if isinstance(raw_result, dict):
            findings = raw_result.get("findings", []) or []
        for item in findings:
            session.add(
                Finding(
                    connector_run_id=run.id,
                    target_id=target_id,
                    source=item.get("source", connector),
                    type=item.get("type", "unknown"),
                    value=str(item.get("value", "")),
                    confidence=str(item.get("confidence", 0.5)),
                    context=json.dumps(item.get("context", {})),
                )
            )
        session.commit()
        return run.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_connector_runs(limit=100, connector=None, target_value=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(ConnectorRun)
        if connector:
            query = query.filter(ConnectorRun.connector == connector)
        if target_value:
            query = query.filter(ConnectorRun.target_value == target_value)
        return query.order_by(ConnectorRun.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def list_findings(limit=200, target_id=None, finding_type=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(Finding)
        if target_id:
            query = query.filter(Finding.target_id == target_id)
        if finding_type:
            query = query.filter(Finding.type == finding_type)
        return query.order_by(Finding.created_at.desc()).limit(limit).all()
    finally:
        session.close()

class SpineSubject(Base):
    __tablename__ = "spine_subjects"
    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineSeed(Base):
    __tablename__ = "spine_seeds"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    seed_type = Column(String, nullable=False)
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=False)
    pii_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineConnectorRun(Base):
    __tablename__ = "spine_connector_runs"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    connector_key = Column(String, nullable=False)
    seed_id = Column(Integer, ForeignKey("spine_seeds.id"), nullable=True)
    status = Column(String, nullable=False)
    raw_result_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineRawArtifact(Base):
    __tablename__ = "spine_raw_artifacts"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
    kind = Column(String, nullable=False)
    path = Column(Text, nullable=False)
    sha256 = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    meta_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineObservation(Base):
    __tablename__ = "spine_observations"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("spine_connector_runs.id"), nullable=False)
    observation_type = Column(String, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="0.5")
    source_ref = Column(Text, nullable=True)
    evidence_ref = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineDossierAssertion(Base):
    __tablename__ = "spine_dossier_assertions"
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey("spine_subjects.id"), nullable=False)
    assertion_type = Column(String, nullable=False)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(String, nullable=False, default="0.5")
    validation_state = Column(String, nullable=False, default="unreviewed")
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class SpineValidationEvent(Base):
    __tablename__ = "spine_validation_events"
    id = Column(Integer, primary_key=True)
    assertion_id = Column(
        Integer,
        ForeignKey("spine_dossier_assertions.id"),
        nullable=False,
    )
    actor = Column(String, nullable=True)
    action = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


def _detach_all(session, items):
    for item in items:
        session.expunge(item)
    return items


def create_spine_subject(label=None):
    ensure_configured()
    session = Session()
    try:
        subject = SpineSubject(label=label)
        session.add(subject)
        session.commit()
        session.refresh(subject)
        return subject.id
    finally:
        session.close()


def get_spine_subject(subject_id):
    ensure_configured()
    session = Session()
    try:
        subject = session.query(SpineSubject).filter_by(id=subject_id).first()
        if subject:
            session.expunge(subject)
        return subject
    finally:
        session.close()


def list_spine_subjects(limit=100):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineSubject).order_by(
            SpineSubject.created_at.desc()
        ).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def add_spine_seed(subject_id, seed_type, raw_value, normalized_value, pii_hash):
    ensure_configured()
    session = Session()
    try:
        existing = session.query(SpineSeed).filter_by(
            subject_id=subject_id,
            seed_type=seed_type,
            pii_hash=pii_hash,
        ).first()
        if existing:
            return existing.id
        seed = SpineSeed(
            subject_id=subject_id,
            seed_type=seed_type,
            raw_value=raw_value,
            normalized_value=normalized_value,
            pii_hash=pii_hash,
        )
        session.add(seed)
        session.commit()
        session.refresh(seed)
        return seed.id
    finally:
        session.close()


def list_spine_seeds(subject_id):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineSeed).filter_by(
            subject_id=subject_id
        ).order_by(SpineSeed.id.asc()).all()
        return _detach_all(session, items)
    finally:
        session.close()


def create_spine_connector_run(
    subject_id,
    connector_key,
    seed_id,
    status,
    raw_result,
):
    ensure_configured()
    session = Session()
    try:
        run = SpineConnectorRun(
            subject_id=subject_id,
            connector_key=connector_key,
            seed_id=seed_id,
            status=status,
            raw_result_json=json.dumps(raw_result),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id
    finally:
        session.close()


def list_spine_connector_runs(subject_id=None, limit=100):
    ensure_configured()
    session = Session()
    try:
        query = session.query(SpineConnectorRun)
        if subject_id is not None:
            query = query.filter_by(subject_id=subject_id)
        items = query.order_by(
            SpineConnectorRun.created_at.desc()
        ).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def create_spine_raw_artifact(
    run_id,
    kind,
    path,
    sha256,
    mime_type=None,
    size_bytes=None,
    meta=None,
):
    ensure_configured()
    session = Session()
    try:
        artifact = SpineRawArtifact(
            run_id=run_id,
            kind=kind,
            path=path,
            sha256=sha256,
            mime_type=mime_type,
            size_bytes=size_bytes,
            meta_json=json.dumps(meta or {}),
        )
        session.add(artifact)
        session.commit()
        session.refresh(artifact)
        return artifact.id
    finally:
        session.close()


def create_spine_observation(
    subject_id,
    run_id,
    observation_type,
    normalized_value,
    confidence,
    source_ref,
    evidence_ref,
    payload,
):
    ensure_configured()
    session = Session()
    try:
        item = SpineObservation(
            subject_id=subject_id,
            run_id=run_id,
            observation_type=observation_type,
            normalized_value=normalized_value,
            confidence=confidence,
            source_ref=source_ref,
            evidence_ref=evidence_ref,
            payload_json=json.dumps(payload),
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item.id
    finally:
        session.close()


def list_spine_observations(subject_id, limit=1000):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineObservation).filter_by(
            subject_id=subject_id
        ).order_by(SpineObservation.created_at.desc()).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def upsert_spine_assertion(
    subject_id,
    assertion_type,
    normalized_value,
    confidence,
    validation_state,
    payload,
):
    ensure_configured()
    session = Session()
    try:
        item = session.query(SpineDossierAssertion).filter_by(
            subject_id=subject_id,
            assertion_type=assertion_type,
            normalized_value=normalized_value,
        ).first()
        if not item:
            item = SpineDossierAssertion(
                subject_id=subject_id,
                assertion_type=assertion_type,
                normalized_value=normalized_value,
                confidence=confidence,
                validation_state=validation_state,
                payload_json=json.dumps(payload),
            )
            session.add(item)
        else:
            item.confidence = confidence
            item.payload_json = json.dumps(payload)
            item.updated_at = utc_now()
        session.commit()
        session.refresh(item)
        return item.id
    finally:
        session.close()


def list_spine_assertions(subject_id, limit=1000):
    ensure_configured()
    session = Session()
    try:
        items = session.query(SpineDossierAssertion).filter_by(
            subject_id=subject_id
        ).order_by(SpineDossierAssertion.confidence.desc()).limit(limit).all()
        return _detach_all(session, items)
    finally:
        session.close()


def validate_spine_assertion(assertion_id, actor, action, note=None):
    ensure_configured()
    session = Session()
    try:
        item = session.query(SpineDossierAssertion).filter_by(
            id=assertion_id
        ).first()
        if not item:
            return None
        if action not in {"confirmed", "rejected", "suppressed", "unreviewed"}:
            raise ValueError("Invalid validation action.")
        item.validation_state = action
        item.updated_at = utc_now()
        session.add(
            SpineValidationEvent(
                assertion_id=assertion_id,
                actor=actor,
                action=action,
                note=note,
            )
        )
        session.commit()
        return item.id
    finally:
        session.close()
