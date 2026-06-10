# v10.32-v10.37 Open PR Triage

## Purpose

Record the non-destructive triage state for the remaining open v10 productization/UX pull requests after the v13 documentation closure work.

## Current Open PRs

| PR | Branch | Merge state | Current delta vs master | Triage |
| --- | --- | --- | --- | --- |
| #139 | `feat/v10.32-productization-ux` | Conflicting / dirty | master ahead 590, branch ahead 5 | Do not merge as-is; rebase and resolve conflicts or close as superseded. |
| #140 | `feat/v10.33-productization-ux` | Mergeable / unstable | master ahead 590, branch ahead 4 | Do not merge without rebase and full CI; likely superseded by later productization work. |
| #141 | `feat/v10.34-productization-ux` | Mergeable / unstable | master ahead 590, branch ahead 4 | Do not merge without rebase and full CI; likely superseded by later productization work. |
| #142 | `feat/v10.35-productization-ux` | Mergeable / unstable | master ahead 590, branch ahead 2 | Do not merge without rebase and full CI; likely superseded by later productization work. |
| #143 | `feat/v10.36-productization-ux` | Mergeable / unstable | master ahead 590, branch ahead 4 | Do not merge without rebase and full CI; likely superseded by later productization work. |
| #144 | `feat/v10.37-productization-ux` | Mergeable / unstable | master ahead 590, branch ahead 3 | Do not merge without rebase and full CI; likely superseded by later productization work. |

## Shared Findings

- The branches are old v10 productization/UX increments based on the v10.32 scaffold.
- Each branch is hundreds of commits behind current master.
- #139 includes extra Termux/rootless hidden-service scripts and is currently conflicting.
- #140-#144 are technically mergeable, but GitHub reports an unstable merge state and the branches have not been rebased onto the current v13/v12.10 baseline.
- Prior PR comments were posted recommending rebase/update plus CI, or closure if the work is intentionally superseded.

## Recommended Handling

- Treat these PRs as stale until their owners rebase onto current master and rerun the full gate.
- Prefer closing them as superseded if the v10.32-v10.37 productization/UX scaffold is no longer part of the current product direction.
- Do not cherry-pick files from this stack without reviewing overlap with later v10, v12, and v13 productization work.

## Verification

- `gh pr view` for #139-#144
- `git rev-list --left-right --count origin/master...origin/<branch>` for each branch
