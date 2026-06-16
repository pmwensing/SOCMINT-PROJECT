# v24.5 Operational Metrics and Throughput

Adds a read-only portfolio metrics layer for case volume, stage throughput, completion counts, average and median stage duration, reviewer throughput, blocked rate, overdue rate, closure-to-archive conversion, reopen rate, and trend windows.

Metrics include:

- total, active, completed, blocked, and overdue case volume
- delivered, closed, archived, and reopened completion counts
- current case counts by normalized stage
- stage-entry throughput counts
- completed-stage duration count, average, median, minimum, and maximum hours
- reviewer completed reviews, active workload, total assignments, completion rate, and average assignment age
- blocked and overdue percentages across the portfolio
- archive conversion as a percentage of closed cases
- reopen rate as a percentage of archived cases
- configurable trend windows with event count, active-case count, stage throughput, closure completions, archive completions, and reopen completions

Trend windows default to 7, 30, and 90 days. They may be configured with `SOCMINT_PORTFOLIO_TREND_WINDOWS`, using a comma-separated list of positive day counts.

Routes:

- `GET /portfolio-operations`
- `GET /api/v1/portfolio-operations`
- `GET /api/v1/portfolio-operations/metrics`

v24.5 is read-only. It derives metrics from existing portfolio, stage, assignment, blocked/overdue, and case audit data. It creates no metrics record, mutates no source event, and introduces no migration.
