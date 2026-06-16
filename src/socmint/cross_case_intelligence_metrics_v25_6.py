from __future__ import annotations

import datetime as dt
import statistics
from collections import Counter, defaultdict
from typing import Any

from .cross_case_confirmed_link_registry_v25_2 import (
    build_confirmed_link_registry_workspace,
)
from .cross_case_intelligence_workspace_v25_0 import (
    build_cross_case_intelligence_workspace,
)
from .cross_case_link_impact_analysis_v25_4 import (
    build_cross_case_link_impact_analysis,
)
from .cross_case_relationship_graph_v25_3 import (
    build_cross_case_relationship_graph,
)
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.cross_case_intelligence_metrics.v25_6"
VERSION = "v25.6.0"


def _percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 2) if values else 0.0


def _median(values: list[float]) -> float:
    return round(statistics.median(values), 2) if values else 0.0


def _band(score: float) -> str:
    if score >= 80:
        return "strong"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "developing"
    return "limited"


def build_cross_case_intelligence_metrics(
    *,
    allowed_case_ids: set[str] | None = None,
    now: dt.datetime | None = None,
    candidate_workspace: dict[str, Any] | None = None,
    registry_workspace: dict[str, Any] | None = None,
    graph_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = now or dt.datetime.now(dt.UTC)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=dt.UTC)

    candidates = candidate_workspace or build_cross_case_intelligence_workspace(
        allowed_case_ids=allowed_case_ids
    )
    registry = registry_workspace or build_confirmed_link_registry_workspace(
        allowed_case_ids=allowed_case_ids
    )
    graph = graph_payload or build_cross_case_relationship_graph(
        allowed_case_ids=allowed_case_ids
    )

    correlation_sections = candidates.get("correlations") or {}
    candidate_items = [
        item
        for section in correlation_sections.values()
        for item in section or []
    ]
    candidate_ids = {
        str(item.get("correlation_id"))
        for item in candidate_items
        if item.get("correlation_id")
    }
    candidate_occurrences = sum(
        int(item.get("occurrence_count") or len(item.get("occurrences") or []))
        for item in candidate_items
    )
    candidate_case_ids = {
        str(case_id)
        for item in candidate_items
        for case_id in item.get("case_ids") or []
    }
    candidate_by_category = {
        section: len(items or [])
        for section, items in sorted(correlation_sections.items())
    }

    review_histories = registry.get("review_histories") or {}
    reviews = [review for history in review_histories.values() for review in history or []]
    latest_reviews = [history[-1] for history in review_histories.values() if history]
    disposition_counts = Counter(
        str(review.get("decision") or "unknown") for review in reviews
    )
    latest_disposition_counts = Counter(
        str(review.get("decision") or "unknown") for review in latest_reviews
    )
    reviewed_candidate_ids = set(review_histories)

    analyst_counts: Counter[str] = Counter()
    analyst_dispositions: dict[str, Counter[str]] = defaultdict(Counter)
    analyst_dates: dict[str, set[str]] = defaultdict(set)
    for review in reviews:
        analyst = str(review.get("reviewer") or "unknown")
        decision = str(review.get("decision") or "unknown")
        analyst_counts[analyst] += 1
        analyst_dispositions[analyst][decision] += 1
        recorded_at = str(review.get("recorded_at") or "")
        if recorded_at:
            analyst_dates[analyst].add(recorded_at[:10])

    analyst_throughput = []
    for analyst in sorted(analyst_counts):
        active_days = max(1, len(analyst_dates[analyst]))
        analyst_throughput.append({
            "analyst": analyst,
            "review_count": analyst_counts[analyst],
            "active_review_days": len(analyst_dates[analyst]),
            "reviews_per_active_day": round(analyst_counts[analyst] / active_days, 2),
            "disposition_counts": dict(sorted(analyst_dispositions[analyst].items())),
        })

    confirmed_links = registry.get("confirmed_links") or []
    confirmed_link_ids = {
        str(item.get("confirmed_link_id"))
        for item in confirmed_links
        if item.get("confirmed_link_id")
    }
    confirmed_case_ids = {
        str(case_id)
        for link in confirmed_links
        for case_id in link.get("case_ids") or []
    }
    confirmed_occurrences = sum(
        int(link.get("source_occurrence_count") or len(link.get("source_occurrences") or []))
        for link in confirmed_links
    )
    accepted_reviews = int(disposition_counts.get("accept", 0))
    latest_accepted = int(latest_disposition_counts.get("accept", 0))

    nodes = graph.get("graph", {}).get("nodes") or []
    edges = graph.get("graph", {}).get("edges") or []
    node_count = len(nodes)
    edge_count = len(edges)
    possible_undirected_edges = (node_count * (node_count - 1)) / 2 if node_count > 1 else 0
    density_percent = min(100.0, _percent(edge_count, possible_undirected_edges))
    degree_counts: Counter[str] = Counter()
    for edge in edges:
        degree_counts[str(edge.get("source"))] += 1
        degree_counts[str(edge.get("target"))] += 1
    degree_values = [float(value) for value in degree_counts.values()]

    cases_per_confirmed_link = [
        float(len(set(str(case_id) for case_id in link.get("case_ids") or [])))
        for link in confirmed_links
    ]
    visible_cases = int(candidates.get("counts", {}).get("visible_cases") or 0)

    impact_rows = []
    impact_breadth_values: list[float] = []
    for link in confirmed_links:
        link_id = str(link.get("confirmed_link_id") or "")
        if not link_id:
            continue
        impact = build_cross_case_link_impact_analysis(
            link_id,
            allowed_case_ids=allowed_case_ids,
        )
        if impact.get("status") != "ready":
            continue
        counts = impact.get("counts") or {}
        breadth = sum(
            int(counts.get(key) or 0)
            for key in (
                "affected_cases",
                "affected_entities",
                "evidence_packages",
                "review_queue_entries",
                "closure_states",
                "archive_records",
            )
        )
        impact_breadth_values.append(float(breadth))
        impact_rows.append({
            "confirmed_link_id": link_id,
            "impact_sha256": impact.get("impact_sha256"),
            "breadth_score": breadth,
            "affected_cases": counts.get("affected_cases", 0),
            "affected_entities": counts.get("affected_entities", 0),
            "evidence_packages": counts.get("evidence_packages", 0),
            "review_queue_entries": counts.get("review_queue_entries", 0),
            "closure_states": counts.get("closure_states", 0),
            "archive_records": counts.get("archive_records", 0),
        })

    review_coverage = min(
        100.0,
        _percent(len(reviewed_candidate_ids & candidate_ids), len(candidate_ids)),
    )
    confirmation_conversion = min(
        100.0,
        _percent(len(confirmed_link_ids), len(candidate_ids)),
    )
    accepted_materialization = min(
        100.0,
        _percent(len(confirmed_link_ids), accepted_reviews),
    )
    occurrence_coverage = min(
        100.0,
        _percent(confirmed_occurrences, candidate_occurrences),
    )
    cross_case_reach = min(
        100.0,
        _percent(len(confirmed_case_ids), visible_cases),
    )
    graph_support = min(
        100.0,
        round((edge_count / max(1, node_count)) * 25.0, 2),
    )

    confidence_components = {
        "review_coverage_percent": review_coverage,
        "accepted_materialization_percent": accepted_materialization,
        "source_occurrence_coverage_percent": occurrence_coverage,
        "cross_case_reach_percent": cross_case_reach,
        "graph_support_percent": graph_support,
    }
    confidence_score = _mean(list(confidence_components.values()))

    metrics_core = {
        "candidate_volume": {
            "total": len(candidate_items),
            "by_category": candidate_by_category,
            "repeated_patterns": int(candidates.get("counts", {}).get("repeated_patterns") or 0),
            "visible_cases": visible_cases,
            "source_records": int(candidates.get("counts", {}).get("source_records") or 0),
        },
        "review_dispositions": {
            "total_reviews": len(reviews),
            "reviewed_candidates": len(reviewed_candidate_ids),
            "all_decisions": dict(sorted(disposition_counts.items())),
            "latest_decisions": dict(sorted(latest_disposition_counts.items())),
            "review_coverage_percent": review_coverage,
        },
        "confirmation_conversion": {
            "confirmed_links": len(confirmed_link_ids),
            "accepted_reviews": accepted_reviews,
            "latest_accepted_reviews": latest_accepted,
            "candidate_to_confirmed_percent": confirmation_conversion,
            "accepted_to_registered_percent": accepted_materialization,
        },
        "graph_density": {
            "nodes": node_count,
            "edges": edge_count,
            "density_percent": density_percent,
            "edges_per_node": round(edge_count / max(1, node_count), 2),
            "average_degree": _mean(degree_values),
            "median_degree": _median(degree_values),
            "graph_sha256": graph.get("graph_sha256"),
        },
        "cross_case_reach": {
            "candidate_case_count": len(candidate_case_ids),
            "confirmed_case_count": len(confirmed_case_ids),
            "visible_case_count": visible_cases,
            "confirmed_case_reach_percent": cross_case_reach,
            "average_cases_per_confirmed_link": _mean(cases_per_confirmed_link),
            "median_cases_per_confirmed_link": _median(cases_per_confirmed_link),
            "maximum_cases_per_confirmed_link": int(max(cases_per_confirmed_link)) if cases_per_confirmed_link else 0,
        },
        "source_occurrence_coverage": {
            "candidate_occurrences": candidate_occurrences,
            "confirmed_occurrences": confirmed_occurrences,
            "coverage_percent": occurrence_coverage,
        },
        "impact_breadth": {
            "analyzed_links": len(impact_rows),
            "average_breadth_score": _mean(impact_breadth_values),
            "median_breadth_score": _median(impact_breadth_values),
            "maximum_breadth_score": int(max(impact_breadth_values)) if impact_breadth_values else 0,
            "links": impact_rows,
        },
        "analyst_throughput": {
            "analyst_count": len(analyst_throughput),
            "total_reviews": len(reviews),
            "analysts": analyst_throughput,
        },
        "confidence_indicators": {
            "score": confidence_score,
            "band": _band(confidence_score),
            "components": confidence_components,
            "interpretation": "operational_indicator_not_probability_or_factual_certainty",
        },
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "generated_at": generated_at.isoformat(),
        "access_scope": {
            "mode": "restricted" if allowed_case_ids is not None else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids) if allowed_case_ids is not None else None,
        },
        "metrics": metrics_core,
        "metrics_sha256": _sha(metrics_core),
        "confidence_is_operational_indicator": True,
        "confidence_is_not_probability": True,
        "source_records_mutated": False,
        "review_history_mutated": False,
        "confirmed_link_registry_mutated": False,
        "graph_mutated": False,
        "impact_records_created": False,
        "metrics_record_created": False,
        "next_action": "review_cross_case_intelligence_metrics",
    }
