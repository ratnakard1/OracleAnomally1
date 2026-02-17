# Tablespace detail scripts

This repository contains ready-to-run SQL scripts to collect tablespace details for Oracle and PostgreSQL.

## Files

- `scripts/oracle_tablespace_details.sql`
  - Permanent tablespace usage (allocated, used, free, percent used)
  - Temp tablespace usage
  - Datafile-level details (size, max size, autoextend, status)
- `scripts/postgres_tablespace_details.sql`
  - Tablespace size, owner, and filesystem location
  - Current-database object usage grouped by tablespace

## Oracle usage

Run with SQL*Plus (or SQLcl) using a user that can read DBA views:

```bash
sqlplus user/password@//host:1521/service @scripts/oracle_tablespace_details.sql
```

Required Oracle privileges are typically:

- `SELECT_CATALOG_ROLE` (or direct access to `DBA_DATA_FILES`, `DBA_FREE_SPACE`, `DBA_TEMP_FILES`, `V$TEMP_SPACE_HEADER`)

## PostgreSQL usage

Run with `psql`:

```bash
psql "host=HOST port=5432 dbname=postgres user=USER password=PASSWORD" -f scripts/postgres_tablespace_details.sql
```

For full visibility, use an account with permissions to inspect all databases and tablespaces.
