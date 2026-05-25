INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, initial schema
-- Running upgrade  -> 0001_initial_schema

CREATE TABLE targets (
    id INTEGER NOT NULL, 
    type VARCHAR, 
    value VARCHAR, 
    created_at DATETIME, 
    PRIMARY KEY (id), 
    UNIQUE (value)
);

CREATE TABLE tools (
    id INTEGER NOT NULL, 
    name VARCHAR, 
    PRIMARY KEY (id), 
    UNIQUE (name)
);

CREATE TABLE users (
    id INTEGER NOT NULL, 
    username VARCHAR, 
    password_hash VARCHAR, 
    is_admin BOOLEAN DEFAULT 0 NOT NULL, 
    created_at DATETIME, 
    PRIMARY KEY (id), 
    UNIQUE (username)
);

CREATE TABLE rate_limit_attempts (
    id INTEGER NOT NULL, 
    action VARCHAR NOT NULL, 
    "key" VARCHAR NOT NULL, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE results (
    id INTEGER NOT NULL, 
    target_id INTEGER, 
    tool_id INTEGER, 
    data TEXT, 
    timestamp DATETIME, 
    PRIMARY KEY (id), 
    FOREIGN KEY(target_id) REFERENCES targets (id), 
    FOREIGN KEY(tool_id) REFERENCES tools (id)
);

CREATE TABLE profiles (
    id INTEGER NOT NULL, 
    target_id INTEGER, 
    source VARCHAR, 
    raw TEXT, 
    normalized TEXT, 
    created_at DATETIME, 
    PRIMARY KEY (id), 
    FOREIGN KEY(target_id) REFERENCES targets (id)
);

CREATE TABLE media (
    id INTEGER NOT NULL, 
    target_id INTEGER, 
    profile_id INTEGER, 
    source_url VARCHAR, 
    path VARCHAR, 
    checksum VARCHAR, 
    content_type VARCHAR, 
    created_at DATETIME, 
    PRIMARY KEY (id), 
    FOREIGN KEY(target_id) REFERENCES targets (id), 
    FOREIGN KEY(profile_id) REFERENCES profiles (id)
);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial_schema') RETURNING version_num;

INFO  [alembic.runtime.migration] Running upgrade 0001_initial_schema -> 0002_audit_logs_and_indexes, audit logs and rate-limit indexes
-- Running upgrade 0001_initial_schema -> 0002_audit_logs_and_indexes

CREATE TABLE audit_logs (
    id INTEGER NOT NULL, 
    actor VARCHAR, 
    action VARCHAR NOT NULL, 
    target_id INTEGER, 
    target_value VARCHAR, 
    ip_address VARCHAR, 
    details TEXT, 
    created_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(target_id) REFERENCES targets (id)
);

CREATE INDEX ix_rate_limit_action_key_created_at ON rate_limit_attempts (action, "key", created_at);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_actor_action ON audit_logs (actor, action);

UPDATE alembic_version SET version_num='0002_audit_logs_and_indexes' WHERE alembic_version.version_num = '0001_initial_schema';

INFO  [alembic.runtime.migration] Running upgrade 0002_audit_logs_and_indexes -> 0003_user_status_and_constraints, user status and stricter constraints
-- Running upgrade 0002_audit_logs_and_indexes -> 0003_user_status_and_constraints

ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL;

CREATE INDEX ix_targets_created_at ON targets (created_at);

ERROR [alembic.util.messaging] This operation cannot proceed in --sql mode; batch mode with dialect sqlite requires a live database connection with which to reflect the table "targets". To generate a batch SQL migration script using table "move and copy", a complete Table object should be passed to the "copy_from" argument of the batch_alter_table() method so that table reflection can be skipped.
  FAILED: This operation cannot proceed in --sql mode; batch mode with dialect sqlite requires a
  live database connection with which to reflect the table "targets". To generate a batch SQL
  migration script using table "move and copy", a complete Table object should be passed to the
  "copy_from" argument of the batch_alter_table() method so that table reflection can be skipped.
