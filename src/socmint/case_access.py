from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import text

from . import database as db

CASE_ACCESS_SCHEMA = "socmint.case_access.v9_2_0"


def _now() -> dt.datetime:
    return db.utc_now()


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True)


def ensure_case_access_schema() -> None:
    db.ensure_configured()
    session = db.Session()
    try:
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS team_memberships (
                id INTEGER PRIMARY KEY,
                team_key VARCHAR(128) NOT NULL,
                username VARCHAR(255) NOT NULL,
                role VARCHAR(64) NOT NULL,
                status VARCHAR(64) NOT NULL,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(team_key, username)
            )
        """)
        )
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS case_assignments (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                username VARCHAR(255) NOT NULL,
                access_level VARCHAR(64) NOT NULL,
                status VARCHAR(64) NOT NULL,
                metadata_json TEXT NOT NULL,
                actor VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(case_id, username)
            )
        """)
        )
        session.commit()
    finally:
        session.close()


def add_team_member(
    team_key: str,
    username: str,
    role: str = "member",
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_case_access_schema()
    now = _now()
    session = db.Session()
    try:
        session.execute(
            text("""
            INSERT INTO team_memberships
            (team_key, username, role, status, metadata_json, actor, created_at, updated_at)
            VALUES (:team_key, :username, :role, 'active', :metadata_json, :actor, :now, :now)
            ON CONFLICT(team_key, username) DO UPDATE SET
                role = excluded.role,
                status = excluded.status,
                metadata_json = excluded.metadata_json,
                actor = excluded.actor,
                updated_at = excluded.updated_at
        """),
            {
                "team_key": team_key,
                "username": username,
                "role": role,
                "metadata_json": _json(metadata or {}),
                "actor": actor,
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="team_member_upsert",
        actor=actor,
        details={"team_key": team_key, "username": username, "role": role},
    )
    return team_access_summary(team_key)


def assign_case(
    case_id: int,
    username: str,
    access_level: str = "viewer",
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_case_access_schema()
    now = _now()
    session = db.Session()
    try:
        session.execute(
            text("""
            INSERT INTO case_assignments
            (case_id, username, access_level, status, metadata_json, actor, created_at, updated_at)
            VALUES (:case_id, :username, :access_level, 'active', :metadata_json, :actor, :now, :now)
            ON CONFLICT(case_id, username) DO UPDATE SET
                access_level = excluded.access_level,
                status = excluded.status,
                metadata_json = excluded.metadata_json,
                actor = excluded.actor,
                updated_at = excluded.updated_at
        """),
            {
                "case_id": int(case_id),
                "username": username,
                "access_level": access_level,
                "metadata_json": _json(metadata or {}),
                "actor": actor,
                "now": now,
            },
        )
        session.commit()
    finally:
        session.close()
    db.record_audit_event(
        action="case_assignment_upsert",
        actor=actor,
        details={
            "case_id": case_id,
            "username": username,
            "access_level": access_level,
        },
    )
    return case_access_summary(case_id)


def _user_role(username: str) -> str | None:
    user = db.get_user_by_username(username)
    return None if not user else getattr(user, "role", None)


def case_access_decision(
    username: str, case_id: int, required: str = "view"
) -> dict[str, Any]:
    ensure_case_access_schema()
    role = _user_role(username)
    if role == "admin":
        return {
            "schema": CASE_ACCESS_SCHEMA,
            "allowed": True,
            "reason": "admin",
            "username": username,
            "case_id": case_id,
            "required": required,
            "access_level": "admin",
        }
    session = db.Session()
    try:
        row = (
            session.execute(
                text("""
            SELECT access_level, status FROM case_assignments
            WHERE case_id = :case_id AND username = :username
        """),
                {"case_id": int(case_id), "username": username},
            )
            .mappings()
            .first()
        )
    finally:
        session.close()
    order = {"none": 0, "viewer": 1, "analyst": 2, "manager": 3, "owner": 4, "admin": 5}
    required_level = (
        "viewer"
        if required == "view"
        else "analyst"
        if required in {"edit", "run", "capture"}
        else "manager"
        if required in {"export", "assign"}
        else required
    )
    access_level = row["access_level"] if row and row["status"] == "active" else "none"
    allowed = order.get(access_level, 0) >= order.get(required_level, 1)
    return {
        "schema": CASE_ACCESS_SCHEMA,
        "allowed": allowed,
        "reason": "assigned" if allowed else "insufficient_case_access",
        "username": username,
        "case_id": int(case_id),
        "required": required,
        "required_level": required_level,
        "access_level": access_level,
    }


def team_access_summary(team_key: str) -> dict[str, Any]:
    ensure_case_access_schema()
    session = db.Session()
    try:
        rows = (
            session.execute(
                text(
                    "SELECT * FROM team_memberships WHERE team_key = :team_key ORDER BY username"
                ),
                {"team_key": team_key},
            )
            .mappings()
            .all()
        )
    finally:
        session.close()
    return {
        "schema": CASE_ACCESS_SCHEMA,
        "team_key": team_key,
        "members": [dict(row) for row in rows],
        "member_count": len(rows),
    }


def case_access_summary(case_id: int) -> dict[str, Any]:
    ensure_case_access_schema()
    session = db.Session()
    try:
        rows = (
            session.execute(
                text(
                    "SELECT * FROM case_assignments WHERE case_id = :case_id ORDER BY username"
                ),
                {"case_id": int(case_id)},
            )
            .mappings()
            .all()
        )
    finally:
        session.close()
    return {
        "schema": CASE_ACCESS_SCHEMA,
        "case_id": int(case_id),
        "assignments": [dict(row) for row in rows],
        "assignment_count": len(rows),
    }


def user_case_access(username: str) -> dict[str, Any]:
    ensure_case_access_schema()
    session = db.Session()
    try:
        rows = (
            session.execute(
                text(
                    "SELECT * FROM case_assignments WHERE username = :username AND status = 'active' ORDER BY case_id"
                ),
                {"username": username},
            )
            .mappings()
            .all()
        )
    finally:
        session.close()
    return {
        "schema": CASE_ACCESS_SCHEMA,
        "username": username,
        "cases": [dict(row) for row in rows],
        "case_count": len(rows),
    }
