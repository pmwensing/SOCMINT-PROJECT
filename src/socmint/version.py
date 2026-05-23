from __future__ import annotations

VERSION = "12.10.16"
RELEASE_NAME = "Tor Hidden Service Self-Test + Operator Diagnostics"
RELEASE_CHANNEL = "rc"
RELEASE_TAG = "v12.10.16-rc1"
SCHEMA = "socmint.release.version.v12_10_16"


def version_payload() -> dict[str, str]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "release_name": RELEASE_NAME,
        "release_channel": RELEASE_CHANNEL,
        "release_tag": RELEASE_TAG,
    }
