from __future__ import annotations

VERSION = "12.10.21"
RELEASE_NAME = "Runtime Readiness Split"
RELEASE_CHANNEL = "rc"
RELEASE_TAG = "v12.10.21-rc1"
SCHEMA = "socmint.version"


def version_payload() -> dict[str, str]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "release_name": RELEASE_NAME,
        "release_channel": RELEASE_CHANNEL,
        "release_tag": RELEASE_TAG,
    }
