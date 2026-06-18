from __future__ import annotations

from collections import Counter
from typing import Any

from . import database
from .team_organization_events_v28_3 import SCHEMA, VERSION, current_teams, history


def _users() -> list[dict[str, Any]]:
    database.ensure_configured()
    session = database.Session()
    try:
        rows = session.query(database.User).order_by(database.User.username.asc()).all()
        return [{"username":row.username,"role":row.role,"is_admin":bool(row.is_admin),"is_active":bool(row.is_active)} for row in rows]
    finally:
        session.close()


def build_team_organization_workspace() -> dict[str, Any]:
    teams = current_teams()
    active = [item for item in teams if item.get("team_status") == "active"]
    users = {item["username"]:item for item in _users()}
    findings = []
    member_counts = Counter()
    for team in active:
        team_id = str(team.get("team_id"))
        members = list(team.get("member_usernames") or [])
        supervisor = str(team.get("supervisor_username") or "")
        if not supervisor:
            findings.append({"severity":"medium","key":"team_without_supervisor","team_id":team_id})
        elif supervisor not in users:
            findings.append({"severity":"high","key":"unknown_team_supervisor","team_id":team_id,"username":supervisor})
        elif not users[supervisor]["is_active"]:
            findings.append({"severity":"high","key":"inactive_team_supervisor","team_id":team_id,"username":supervisor})
        for username in members:
            member_counts[username] += 1
            if username not in users:
                findings.append({"severity":"high","key":"unknown_team_member","team_id":team_id,"username":username})
            elif not users[username]["is_active"]:
                findings.append({"severity":"medium","key":"inactive_team_member","team_id":team_id,"username":username})
        if not team.get("organizational_scope"):
            findings.append({"severity":"low","key":"team_without_organizational_scope","team_id":team_id})
        if not team.get("workload_group"):
            findings.append({"severity":"low","key":"team_without_workload_group","team_id":team_id})
    for username, count in member_counts.items():
        if count > 3:
            findings.append({"severity":"low","key":"user_in_many_teams","username":username,"team_count":count})
    events = history()
    workload_counts = Counter(str(item.get("workload_group") or "unassigned") for item in active)
    scope_counts = Counter(str(item.get("organizational_scope") or "unassigned") for item in active)
    return {"schema":SCHEMA,"version":VERSION,"status":"ready","teams":teams,"active_teams":active,"team_count":len(teams),"active_team_count":len(active),"member_assignment_count":sum(len(item.get("member_usernames") or []) for item in active),"supervised_team_count":sum(bool(item.get("supervisor_username")) for item in active),"organizational_scope_counts":dict(sorted(scope_counts.items())),"workload_group_counts":dict(sorted(workload_counts.items())),"organization_findings":findings,"organization_finding_count":len(findings),"team_history":events[-200:],"team_event_count":len(events),"team_membership_grants_case_access":False,"ownership_boundaries_are_descriptive":True,"case_access_scope_changed_by_view":False,"next_action":"review_team_and_organizational_structure"}
