import datetime
import json
import os

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from .config import load_settings

Base = declarative_base()


def utc_now():
    return datetime.datetime.now(datetime.UTC)


class Target(Base):
    __tablename__ = 'targets'
    id = Column(Integer, primary_key=True)
    type = Column(String)
    value = Column(String, unique=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    results = relationship('Result', back_populates='target', cascade='all, delete-orphan')
    profiles = relationship('Profile', back_populates='target', cascade='all, delete-orphan')
    media = relationship('Media', back_populates='target', cascade='all, delete-orphan')


class Tool(Base):
    __tablename__ = 'tools'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    results = relationship('Result', back_populates='tool', cascade='all, delete-orphan')


class Result(Base):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'))
    tool_id = Column(Integer, ForeignKey('tools.id'))
    data = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=utc_now)
    target = relationship('Target', back_populates='results')
    tool = relationship('Tool', back_populates='results')


class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'))
    source = Column(String)
    raw = Column(Text)
    normalized = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    target = relationship('Target', back_populates='profiles')


class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, ForeignKey('targets.id'))
    profile_id = Column(Integer, ForeignKey('profiles.id'), nullable=True)
    source_url = Column(String)
    path = Column(String)
    checksum = Column(String)
    content_type = Column(String)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    target = relationship('Target', back_populates='media')


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class RateLimitAttempt(Base):
    __tablename__ = 'rate_limit_attempts'
    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target_id = Column(Integer, ForeignKey('targets.id'), nullable=True)
    target_value = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


Index('ix_rate_limit_action_key_created_at', RateLimitAttempt.action, RateLimitAttempt.key, RateLimitAttempt.created_at)
Index('ix_audit_logs_created_at', AuditLog.created_at)
Index('ix_audit_logs_actor_action', AuditLog.actor, AuditLog.action)


def get_engine(database_url=None):
    settings = load_settings(require_secret=False, database_url=database_url)
    if settings.database_url.startswith('sqlite:///'):
        sqlite_path = settings.database_url.replace('sqlite:///', '', 1)
        if sqlite_path and sqlite_path != ':memory:':
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


def get_user_by_username(username):
    ensure_configured()
    session = Session()
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        session.close()


def create_user(username, password, is_admin=False):
    ensure_configured()
    if get_user_by_username(username):
        return None
    session = Session()
    try:
        password_hash = generate_password_hash(password)
        user = User(username=username, password_hash=password_hash, is_admin=is_admin)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    finally:
        session.close()


def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


def count_recent_rate_limit_attempts(action, key, window_seconds):
    ensure_configured()
    cutoff = utc_now() - datetime.timedelta(seconds=window_seconds)
    session = Session()
    try:
        session.query(RateLimitAttempt).filter(RateLimitAttempt.created_at < cutoff).delete()
        session.commit()
        return session.query(RateLimitAttempt).filter_by(action=action, key=key).filter(
            RateLimitAttempt.created_at >= cutoff
        ).count()
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
        target_id = getattr(target, 'id', None)
        target_value = getattr(target, 'value', None)
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


def get_audit_events(limit=100):
    ensure_configured()
    session = Session()
    try:
        return session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def delete_dossier(target_id):
    ensure_configured()
    session = Session()
    try:
        target = session.query(Target).filter_by(id=target_id).first()
        if not target:
            return None
        snapshot = {'id': target.id, 'value': target.value, 'type': target.type}
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
        target = session.query(Target).filter_by(value=dossier['target']).first()
        if not target:
            target = Target(type=dossier.get('type'), value=dossier['target'])
            session.add(target)
            session.commit()

        for tool_name, data in dossier.get('data', {}).items():
            tool = session.query(Tool).filter_by(name=tool_name).first()
            if not tool:
                tool = Tool(name=tool_name)
                session.add(tool)
                session.commit()

            result = Result(target_id=target.id, tool_id=tool.id, data=json.dumps(data))
            session.add(result)

        session.commit()

        profile_map = {}
        for profile in dossier.get('profiles', []):
            profile_record = Profile(
                target_id=target.id,
                source=profile.get('url', profile.get('source', 'unknown')),
                raw=json.dumps(profile.get('raw', {})),
                normalized=json.dumps({
                    'title': profile.get('title'),
                    'description': profile.get('description'),
                    'site_name': profile.get('site_name'),
                    'url': profile.get('url'),
                    'image': profile.get('image')
                })
            )
            session.add(profile_record)
            session.commit()
            profile_map[profile.get('url')] = profile_record

        for media_item in dossier.get('media', []):
            existing = session.query(Media).filter_by(target_id=target.id, source_url=media_item.get('url')).first()
            if existing:
                continue
            profile_id = None
            if media_item.get('url') in profile_map:
                profile_id = profile_map[media_item.get('url')].id
            session.add(Media(
                target_id=target.id,
                profile_id=profile_id,
                source_url=media_item.get('url'),
                path=media_item.get('path'),
                checksum=media_item.get('checksum'),
                content_type=media_item.get('content_type')
            ))

        session.commit()
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
            'target': target.value,
            'type': target.type,
            'data': {},
            'profiles': [],
            'media': []
        }

        for result in target.results:
            dossier['data'][result.tool.name] = json.loads(result.data)

        for profile in target.profiles:
            dossier['profiles'].append({
                'source': profile.source,
                'raw': json.loads(profile.raw or '{}'),
                'normalized': json.loads(profile.normalized or '{}')
            })

        for media in target.media:
            dossier['media'].append({
                'source_url': media.source_url,
                'path': media.path,
                'checksum': media.checksum,
                'content_type': media.content_type
            })

        return dossier
    finally:
        session.close()
