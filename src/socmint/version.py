from __future__ import annotations

VERSION = "12.10.14"
RELEASE_NAME = "Release Candidate Stabilization + Fresh Deploy Gate"
RELEASE_CHANNEL = "rc"
RELEASE_TAG = "v12.10.14-rc1"
SCHEMA = "socmint.release.version.v12_10_14"


def version_payload() -> dict[str, str]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "release_name": RELEASE_NAME,
        "release_channel": RELEASE_CHANNEL,
        "release_tag": RELEASE_TAG,
    }
