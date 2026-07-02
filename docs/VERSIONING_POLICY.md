# Versioning Policy

SOCMINT uses two intentionally separate version streams.

## Product program versions

Product versions such as `v34.8`, `v35.0`, and `v35.1` identify reviewed capability slices in the operational product roadmap. They are recorded in release notes, planning contracts, pull requests, tests, and runtime schema/version fields.

A product program version answers:

> Which reviewed operational capability and control set does this code implement?

Product versions may advance frequently as individual workspaces, gates, audits, and recovery controls are delivered.

## Python distribution version

The `[project].version` value in `pyproject.toml` identifies the installable Python distribution. It changes only when a formal package artifact is prepared and released.

A package version answers:

> Which installable Python distribution artifact is this?

The package version does not automatically mirror the current product program version. Advancing a product slice therefore does not require changing `[project].version` unless a new installable package is also being released.

## Required release references

Formal package releases must record both identifiers:

- Python distribution version
- highest included product program version
- source commit SHA
- migration head
- verification evidence

Product-only pull requests must identify their product program version and source commit, but must not change the Python distribution version merely to keep the numbers visually aligned.

## Current decision

SOCMINT will retain independent product and package versioning. The existing package version remains unchanged until the next formal distribution release. Product development continues through the v35 program without renumbering the Python package to `35.x`.
