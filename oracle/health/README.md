# Oracle Database Health (Last 24 Hours)

This folder contains a **SQL\*Plus report** to capture Oracle Database health for the **last 24 hours** (or last *N* hours), including:

- DB Time / DB CPU (AAS)
- Host CPU utilization (AWR OS stats)
- Memory usage (PGA / SGA)
- Executions, transactions, parses
- Cache efficiency (buffer cache hit %, library cache, row cache)
- Top wait events (non-idle), plus Network and RAC/Cluster waits
- I/O performance (read/write IOPS, MB/s, avg KB per IO)
- Commit/redo performance (redo rate, log file sync latency, etc.)
- Redo log / log buffer configuration and log switch frequency
- Top SQL by elapsed time, top SQL by CPU, and SQL summary (elapsed/CPU/wait breakdown)

## Files

- `db_health_last24h.sql`: main report script (spools a report file)
- `run_db_health_last24h.sh`: helper wrapper to run the report and write output to a directory

## Prerequisites

- **SQL\*Plus** available on the host running the script (`sqlplus` in `PATH`)
- Privileges for `V$` views (`V$DATABASE`, `V$INSTANCE`, etc.)
- For **last-24h** reporting, the report uses **AWR** (`DBA_HIST_*` views). That requires:
  - Access to `DBA_HIST_*` views (commonly via `SELECT_CATALOG_ROLE` or direct grants)
  - **Diagnostics Pack licensing considerations** (AWR is part of Diagnostics Pack)

If AWR is not accessible, the script still produces a report file, but AWR-based sections may show **zeros / empty output**.

## Run (recommended)

From this directory:

```bash
chmod +x run_db_health_last24h.sh
./run_db_health_last24h.sh "/ as sysdba" 24 20 ./reports
```

This creates a file like:

- `db_health_last24h_<db_unique_name>_<timestamp>.lst`

## Run (SQL*Plus directly)

```sql
-- hours_back top_n
@db_health_last24h.sql 24 20
```

## Tips

- Increase `top_n` if you want more SQL / wait events in the report.
- In RAC, the report aggregates across instances for AWR-based deltas.

