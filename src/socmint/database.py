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
    results = relationship("Result", back_populates="target", cascade="all, delete-orphan")
    profiles = relationship("Profile", back_populates="target", cascade="all, delete-orphan")
    media = relationship("Media", back_populates="target", cascade="all, delete-orphan")


class Tool(Base):
    __tablename__ = "tools"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    results = relationship("Result", back_populates="tool", cascade="all, delete-orphan")


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


Index("ix_rate_limit_action_key_created_at", RateLimitAttempt.action, RateLimitAttempt.key, RateLimitAttempt.created_at)
Index("ix_audit_logs_created_at", AuditLog.created_at)
Index("ix_audit_logs_actor_action", AuditLog.actor, AuditLog.action)
Index("ix_targets_created_at", Target.created_at)
Index("ix_scan_jobs_status_created_at", ScanJob.status, ScanJob.created_at)
Index("ix_connector_runs_connector_created_at", ConnectorRun.connector, ConnectorRun.created_at)
Index("ix_findings_type_created_at", Finding.type, Finding.created_at)


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
        user = User(username=username, password_hash=password_hash, is_admin=is_admin, role=role or ("admin" if is_admin else "viewer"))
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
            user.is_admin = is_admin
        if is_active is not None:
            user.is_active = is_active
        if password:
            user.password_hash = generate_password_hash(password)
        if role:
            user.role = role
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def delete_user(user_id):
    ensure_configured()
    session = Session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return False
        session.delete(user)
        session.commit()
        return True
    finally:
        session.close()


def save_dossier(dossier):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(value=dossier["target"]).first() or Target(type=dossier["type"], value=dossier["target"])
        session.add(target)
        session.flush()
        for tool_name, data in dossier.get("data", {}).items():
            tool = session.query(Tool).filter_by(name=tool_name).first() or Tool(name=tool_name)
            session.add(tool)
            session.flush()
            result = Result(target_id=target.id, tool_id=tool.id, data=json.dumps(data))
            session.add(result)
            if isinstance(data, dict):
                connector_run = ConnectorRun(target_id=target.id, target_value=dossier["target"], target_type=dossier["type"], connector=tool_name, status=data.get("status", "completed"), command=json.dumps(data.get("command")), raw_result=json.dumps(data), error=data.get("stderr") if data.get("status") != "completed" else None)
                session.add(connector_run)
                session.flush()
                for finding in data.get("findings", []):
                    session.add(Finding(connector_run_id=connector_run.id, target_id=target.id, source=finding.get("source", tool_name), type=finding.get("type", "unknown"), value=finding.get("value", ""), confidence=str(finding.get("confidence", 0.5)), context=json.dumps(finding)))
        session.commit()
        session.refresh(target)
        return target.id
    finally:
        session.close()


def get_dossier(target_value):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(value=target_value).first()
        if not target:
            return None
        data = {}
        for result in target.results:
            data[result.tool.name] = json.loads(result.data)
        return {"target": target.value, "type": target.type, "data": data}
    finally:
        session.close()


def list_targets(limit=100):
    ensure_configured()
    session = Session()
    try:
        return session.query(Target).order_by(Target.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def get_target(target_id):
    ensure_configured()
    session = Session()
    try:
        return session.query(Target).filter_by(id=target_id).first()
    finally:
        session.close()


def list_connector_runs(limit=100, connector=None, status=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(ConnectorRun)
        if connector:
            query = query.filter_by(connector=connector)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(ConnectorRun.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def get_connector_run(run_id):
    ensure_configured()
    session = Session()
    try:
        return session.query(ConnectorRun).filter_by(id=run_id).first()
    finally:
        session.close()


def list_findings(limit=100, finding_type=None):
    ensure_configured()
    session = Session()
    try:
        query = session.query(Finding)
        if finding_type:
            query = query.filter_by(type=finding_type)
        return query.order_by(Finding.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def create_audit_event(actor=None, action="event", target_id=None, target_value=None, ip_address=None, details=None):
    ensure_configured()
    session = Session()
    try:
        event = AuditLog(actor=actor, action=action, target_id=target_id, target_value=target_value, ip_address=ip_address, details=json.dumps(details or {}))
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
        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
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


def create_scan_job(target_value, target_type, tools=None, enrich=False, requested_by=None):
    ensure_configured()
    session = Session()
    try:
        job = ScanJob(target_value=target_value, target_type=target_type, tools=json.dumps(sorted(tools or [])), enrich=bool(enrich), requested_by=requested_by)
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
        return session.query(ScanJob).order_by(ScanJob.created_at.desc()).limit(limit).all()
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
        job = session.query(ScanJob).filter_by(status="queued").order_by(ScanJob.created_at.asc()).first()
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
            "requested_by": job.requested_by,
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


def update_scan_job_status(job_id, status, error=None):
    ensure_configured()
    session = Session()
    try:
        job = session.query(ScanJob).filter_by(id=job_id).first()
        if not job:
            return None
        job.status = status
        job.error = error
        if status in {"queued", "running"}:
            job.finished_at = None
        else:
            job.finished_at = utc_now()
        if status == "queued":
            job.started_at = None
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
        value = target.value
        session.delete(target)
        session.commit()
        return value
    finally:
        session.close()
