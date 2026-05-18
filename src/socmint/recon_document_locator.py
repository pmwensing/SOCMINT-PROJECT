from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlencode, urlparse
from urllib.request import Request, urlopen

SCHEMA = "socmint.recon.document_locator.v12_3_1"
QUEUE_SCHEMA = "socmint.recon.acquisition_queue.v12_3_1"
USER_AGENT = "SOCMINT-PROJECT-v12.3.1-document-locator/1.0"

PUBLIC_FILE_EXTENSIONS = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
    "txt": "text/plain",
    "json": "application/json",
    "xml": "application/xml",
    "eml": "message/rfc822",
    "mbox": "application/mbox",
}

DORK_TEMPLATES = [
    {"id": "filetype_pdf", "label": "PDF documents", "template": '"{target}" filetype:pdf'},
    {"id": "filetype_docs", "label": "Office documents", "template": '"{target}" (filetype:doc OR filetype:docx OR filetype:xls OR filetype:xlsx)'},
    {"id": "public_index", "label": "Open directory indexes", "template": 'intitle:"index of" "{target}"'},
    {"id": "public_cloud", "label": "Public cloud links", "template": '"{target}" (site:drive.google.com OR site:docs.google.com OR site:dropbox.com OR site:onedrive.live.com)'},
    {"id": "email_mentions", "label": "Email mentions", "template": '"{target}" email OR contact OR "@"'},
    {"id": "paste_mentions", "label": "Paste/code mentions", "template": '"{target}" (site:pastebin.com OR site:gist.github.com OR site:github.com)'},
    {"id": "court_records", "label": "Court/public records", "template": '"{target}" (court OR docket OR filing OR tribunal OR affidavit)'},
    {"id": "foi_disclosures", "label": "FOI/disclosure documents", "template": '"{target}" (FOI OR disclosure OR "freedom of information" OR "access to information")'},
]

LEGAL_LABELS = {
    "public_index": "public-index-result",
    "api_search": "api-search-result",
    "archive": "public-archive-index",
    "github_code": "public-code-search",
    "manual_review": "manual-review-required",
    "not_evidence": "located-url-not-evidence",
}


@dataclass
class DocumentLocatorResult:
    source: str
    connector: str
    query: str
    title: str
    url: str
    snippet: str = ""
    mime_type: str | None = None
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    provenance: dict[str, Any] = field(default_factory=dict)
    source_trust: str = "review"
    legal_safety: list[str] = field(default_factory=lambda: [LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]])
    acquisition_state: str = "located"
    risk: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _guess_mime(url: str) -> str | None:
    path = urlparse(url).path.lower()
    ext = path.rsplit(".", 1)[-1] if "." in path else ""
    return PUBLIC_FILE_EXTENSIONS.get(ext)


def _is_public_file(url: str) -> bool:
    return _guess_mime(url) is not None


def _safe_request_json(url: str, headers: dict[str, str] | None = None, timeout: int = 12) -> Any:
    req = Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urlopen(req, timeout=timeout) as response:  # nosec: public search/archive endpoints only
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def render_dork_templates(target: str) -> list[dict[str, str]]:
    safe_target = str(target or "").strip()
    return [{**item, "query": item["template"].format(target=safe_target)} for item in DORK_TEMPLATES]


def _mock_result(connector: str, query: str, source: str, title: str, url: str, snippet: str = "") -> DocumentLocatorResult:
    return DocumentLocatorResult(
        source=source,
        connector=connector,
        query=query,
        title=title,
        url=url,
        snippet=snippet,
        mime_type=_guess_mime(url),
        provenance={"mode": "diagnostic_stub", "public_only": True},
        source_trust="review",
        legal_safety=[LEGAL_LABELS["api_search"], LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
        risk={"requires_manual_review": True, "public_only": True, "note": "Stubbed result unless live recon is explicitly enabled."},
    )


def brave_search(query: str, count: int = 10) -> list[DocumentLocatorResult]:
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    live = os.environ.get("SOCMINT_RECON_LIVE", "").lower() in {"1", "true", "yes", "on"}
    if not api_key or not live:
        return [_mock_result("brave", query, "brave_search_api_stub", "Brave Search API configured as preferred backend", f"https://search.brave.com/search?q={quote_plus(query)}", "Set BRAVE_SEARCH_API_KEY and SOCMINT_RECON_LIVE=1 for live API calls.")]
    endpoint = "https://api.search.brave.com/res/v1/web/search?" + urlencode({"q": query, "count": count})
    payload = _safe_request_json(endpoint, headers={"Accept": "application/json", "X-Subscription-Token": api_key})
    results = []
    for rank, item in enumerate(payload.get("web", {}).get("results", []), start=1):
        url = item.get("url") or ""
        results.append(DocumentLocatorResult(
            source="brave_search_api",
            connector="brave",
            query=query,
            title=item.get("title") or url,
            url=url,
            snippet=item.get("description") or "",
            mime_type=_guess_mime(url),
            provenance={"rank": rank, "profile": item.get("profile"), "public_only": True},
            source_trust="review" if not _is_public_file(url) else "document-candidate",
            legal_safety=[LEGAL_LABELS["api_search"], LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
            risk={"requires_manual_review": True, "public_only": True},
        ))
    return results


def wayback_cdx(query: str, count: int = 10) -> list[DocumentLocatorResult]:
    target = query.strip().split()[0] if query.strip() else "example.com"
    live = os.environ.get("SOCMINT_RECON_LIVE", "").lower() in {"1", "true", "yes", "on"}
    if not live:
        return [_mock_result("wayback_cdx", query, "wayback_cdx_stub", "Wayback CDX public archive lookup", f"https://web.archive.org/cdx?url={quote_plus(target)}&output=json", "Enable SOCMINT_RECON_LIVE=1 for live CDX queries.")]
    endpoint = "https://web.archive.org/cdx?" + urlencode({"url": target, "output": "json", "limit": count, "fl": "timestamp,original,mimetype,statuscode,digest"})
    rows = _safe_request_json(endpoint)
    results = []
    for rank, row in enumerate(rows[1:] if isinstance(rows, list) and rows else [], start=1):
        timestamp, original, mimetype, statuscode, digest = (row + [None] * 5)[:5]
        results.append(DocumentLocatorResult(
            source="wayback_cdx",
            connector="wayback_cdx",
            query=query,
            title=f"Wayback capture {timestamp}",
            url=original,
            snippet=f"status={statuscode}; mimetype={mimetype}",
            mime_type=mimetype or _guess_mime(original),
            provenance={"rank": rank, "timestamp": timestamp, "digest": digest, "archive": "Internet Archive Wayback CDX"},
            source_trust="archive",
            legal_safety=[LEGAL_LABELS["archive"], LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
            risk={"requires_manual_review": True, "public_archive": True},
        ))
    return results


def commoncrawl_index(query: str, count: int = 10) -> list[DocumentLocatorResult]:
    target = query.strip().split()[0] if query.strip() else "example.com"
    live = os.environ.get("SOCMINT_RECON_LIVE", "").lower() in {"1", "true", "yes", "on"}
    if not live:
        return [_mock_result("commoncrawl", query, "commoncrawl_stub", "Common Crawl public CDX lookup", f"https://index.commoncrawl.org/?url={quote_plus(target)}", "Enable SOCMINT_RECON_LIVE=1 for live Common Crawl index queries.")]
    indexes = _safe_request_json("https://index.commoncrawl.org/collinfo.json")
    latest = indexes[0]["cdx-api"] if indexes else "https://index.commoncrawl.org/CC-MAIN-2025-18-index"
    endpoint = latest + "?" + urlencode({"url": target, "output": "json", "limit": count})
    req = Request(endpoint, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=12) as response:  # nosec: public Common Crawl endpoint
        lines = response.read().decode("utf-8", errors="replace").splitlines()
    results = []
    for rank, line in enumerate(lines[:count], start=1):
        item = json.loads(line)
        url = item.get("url") or ""
        results.append(DocumentLocatorResult(
            source="commoncrawl",
            connector="commoncrawl",
            query=query,
            title=f"Common Crawl record {item.get('timestamp')}",
            url=url,
            snippet=f"mime={item.get('mime')}; status={item.get('status')}",
            mime_type=item.get("mime") or _guess_mime(url),
            provenance={"rank": rank, "digest": item.get("digest"), "filename": item.get("filename"), "offset": item.get("offset"), "length": item.get("length")},
            source_trust="archive",
            legal_safety=[LEGAL_LABELS["archive"], LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
            risk={"requires_manual_review": True, "public_archive": True},
        ))
    return results


def github_code_search(query: str, count: int = 10) -> list[DocumentLocatorResult]:
    token = os.environ.get("GITHUB_TOKEN")
    live = os.environ.get("SOCMINT_RECON_LIVE", "").lower() in {"1", "true", "yes", "on"}
    if not token or not live:
        return [_mock_result("github_code", query, "github_code_stub", "GitHub public code search", f"https://github.com/search?q={quote_plus(query)}&type=code", "Set GITHUB_TOKEN and SOCMINT_RECON_LIVE=1 for live API calls.")]
    endpoint = "https://api.github.com/search/code?" + urlencode({"q": query, "per_page": min(count, 100)})
    payload = _safe_request_json(endpoint, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"})
    results = []
    for rank, item in enumerate(payload.get("items", []), start=1):
        html_url = item.get("html_url") or ""
        results.append(DocumentLocatorResult(
            source="github_code_search",
            connector="github_code",
            query=query,
            title=item.get("name") or html_url,
            url=html_url,
            snippet=item.get("path") or "",
            mime_type=_guess_mime(item.get("name", "")),
            provenance={"rank": rank, "repository": item.get("repository", {}).get("full_name"), "sha": item.get("sha"), "score": item.get("score")},
            source_trust="review",
            legal_safety=[LEGAL_LABELS["github_code"], LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
            risk={"requires_manual_review": True, "public_code_search": True},
        ))
    return results


CONNECTORS = {
    "brave": brave_search,
    "wayback_cdx": wayback_cdx,
    "commoncrawl": commoncrawl_index,
    "github_code": github_code_search,
}


def document_locator_search(query: str, connectors: list[str] | None = None, count: int = 10) -> dict[str, Any]:
    selected = connectors or ["brave", "wayback_cdx", "commoncrawl", "github_code"]
    all_results: list[DocumentLocatorResult] = []
    errors: list[dict[str, str]] = []
    for name in selected:
        fn = CONNECTORS.get(name)
        if not fn:
            errors.append({"connector": name, "error": "unknown connector"})
            continue
        try:
            all_results.extend(fn(query, count=count))
        except Exception as exc:
            errors.append({"connector": name, "error": str(exc)})
    results = [item.as_dict() for item in all_results]
    return {
        "schema": SCHEMA,
        "query": query,
        "connectors": selected,
        "generated_at": datetime.now(UTC).isoformat(),
        "result_count": len(results),
        "results": results,
        "errors": errors,
        "dork_templates": render_dork_templates(query),
        "legal_safety_notice": "Located URLs are leads only. They become evidence only after lawful acquisition, hashing, review, and promotion into the evidence vault.",
        "recommended_default_backend": "brave",
    }


def acquisition_queue_path(root: str | None = None) -> Path:
    base = Path(root or os.environ.get("SOCMINT_DATA_DIR", "var/socmint"))
    return base / "recon" / "manual_acquisition_queue.json"


def queue_for_manual_acquisition(result: dict[str, Any], actor: str | None = None, root: str | None = None) -> dict[str, Any]:
    path = acquisition_queue_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    queue = []
    if path.exists():
        try:
            queue = json.loads(path.read_text()).get("items", [])
        except Exception:
            queue = []
    canonical = json.dumps(result, sort_keys=True)
    item_id = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    item = {
        "id": item_id,
        "schema": QUEUE_SCHEMA,
        "queued_at": datetime.now(UTC).isoformat(),
        "actor": actor,
        "state": "manual_review_required",
        "result": result,
        "legal_safety": result.get("legal_safety") or [LEGAL_LABELS["manual_review"], LEGAL_LABELS["not_evidence"]],
        "next_step": "Review source legality and relevance, then send to v12.5 forensic intake for acquisition/preservation.",
    }
    queue = [existing for existing in queue if existing.get("id") != item_id]
    queue.append(item)
    payload = {"schema": QUEUE_SCHEMA, "updated_at": datetime.now(UTC).isoformat(), "items": queue}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return {"queued": item, "queue_path": str(path), "queue_count": len(queue)}
