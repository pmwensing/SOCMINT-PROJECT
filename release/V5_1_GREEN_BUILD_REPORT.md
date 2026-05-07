# SOCMINT Workbench v5.1 Green Build Report

## Status

Green / operational.

## Verified

- Nginx frontend route works.
- `/api/health` works through Nginx.
- Signup works.
- Login works.
- JWT bearer auth works.
- Case creation works.
- Case listing works.
- Seed creation works.
- Recursive expansion works.
- Findings are generated and case-scoped.
- Connector run history is generated and case-scoped.
- Evidence vault note endpoint works.
- Frontend loads and calls API successfully.
- Docker Compose is health-gated.
- Postgres, Redis, Neo4j, API, worker, frontend, and Nginx are online.

## Canonical route contract

Browser:

```text
/api/*
```

Nginx strips `/api`:

```text
/api/* -> http://api:8000/*
/      -> http://frontend:80/
```

Backend exposes:

```text
/health
/auth/*
/cases/*
/seeds/*
/vault/*
```

## Operational commands

```bash
make test
make audit
docker compose ps
docker compose logs -f --tail=120
```

## URL

```text
http://127.0.0.1:8080
```

## Next build

v5.2 — real connector execution layer + raw result persistence.
