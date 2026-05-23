from __future__ import annotations

VERSION = "12.10.15"
RELEASE_NAME = "CI Wiring + Auto Release Gate Artifact Upload"
RELEASE_CHANNEL = "rc"
RELEASE_TAG = "v12.10.15-rc1"
SCHEMA = "socmint.release.version.v12_10_15"


def version_payload() -> dict[str, str]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "release_name": RELEASE_NAME,
        "release_channel": RELEASE_CHANNEL,
        "release_tag": RELEASE_TAG,
    }
