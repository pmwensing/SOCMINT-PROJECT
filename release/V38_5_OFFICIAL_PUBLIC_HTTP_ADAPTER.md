# v38.5 — Official/Public HTTP Crawler Adapter

## Delivered

This slice adds an operator-triggered, single-page, zero-depth HTTP capture adapter for domains explicitly approved by the existing v38.2 public-discovery gate.

The adapter:

- requires an existing v38.1 discovery request and an allowing, live-network-eligible v38.2 gate decision;
- requires explicit operator confirmation and an administrative reason;
- accepts only HTTP or HTTPS URLs without embedded credentials;
- requires the requested host and every redirect target to be explicitly approved;
- resolves each host before transport and blocks loopback, private, link-local, reserved, multicast, and unspecified targets;
- uses one request at a time, zero crawl depth, one page, bounded redirects, an explicit timeout, an optional inter-request delay, an allowlisted content type, and a maximum response size;
- sends no cookies, credentials, authorization header, or authenticated browser profile;
- performs no automatic retry and no arbitrary off-domain following;
- records requested/final URL, redirect chain, response status, sanitized response headers, request timing, MIME type, byte size, adapter identity, content SHA-256, and deterministic capture SHA-256;
- does not automatically register an evidence artifact, register a source, create a v37 import, promote an observation, assign truth, merge an entity, approve a claim, mutate a dossier, export, or publish.

## Safety boundary

The transport is injected. Tests use deterministic fictional responses and perform no live third-party request. Production wiring may provide a Scrapy-compatible downloader only after deployment policy explicitly enables v38.5 live-network execution.

The adapter intentionally remains single-page and zero-depth. Broader crawl scheduling, link extraction, automatic scope expansion, private/authenticated collection, CAPTCHA handling, paywall bypass, and silent retry are prohibited.

## Focused validation

```bash
pytest -q tests/test_v38_5_public_http_crawler.py
```

## Next slice

`v38.6 — Browsertrix preservation adapter`, reusing the v38.5 domain, network-target, redirect, content, resource, authentication, and no-automatic-action controls.
