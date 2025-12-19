## Natural-language DBA Command Executor (Oracle + OpenAI)

This tool turns a natural-language DBA request into **Oracle SQL**, applies a **local safety policy**, and can **optionally execute** the SQL against an Oracle database.

### Project layout

- **`nl_dba_executor.py`**: backward-compatible CLI wrapper
- **`nldba_executor/`**: implementation package
- **`requirements.txt`**: Python dependencies
- **`.nl_dba_executor_logs/`**: local JSONL logs (gitignored)

## Configuration

### 1) Create and use a virtual environment (recommended)

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2) Install dependencies

From the repo root:

```bash
python -m pip install -r requirements.txt
```

### 3) Set environment variables

You can export env vars directly, or store them in a local `.env` file and load it.

#### Option A: export directly

```bash
export OPENAI_API_KEY="..."
# Optional
export OPENAI_MODEL="gpt-4o-mini"
```

For execution against Oracle (only needed with `--execute`):

```bash
export ORACLE_USER="..."
export ORACLE_PASSWORD="..."
export ORACLE_DSN="host:1521/service"  # or a TNS name
```

#### Option B: use a `.env` file

Create `/workspace/.env` (repo root). Example:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_DSN=host:1521/service

# Safety toggles (optional)
# NLDBA_READONLY=1
# NLDBA_ALLOW_DESTRUCTIVE=1
```

Load it in bash:

```bash
set -a
source .env
set +a
```

### 3) Safety toggles (optional)

- **Force read-only mode** (blocks anything not starting with SELECT/WITH/EXPLAIN):

```bash
export NLDBA_READONLY=1
```

- **Allow destructive keywords** (still requires interactive confirmation):

```bash
export NLDBA_ALLOW_DESTRUCTIVE=1
```

## Execution

### Dry-run (recommended)

Dry-run prints the plan and SQL but does **not** connect to Oracle:

```bash
python nl_dba_executor.py "show blocking sessions"
```

Or via module entrypoint:

```bash
python -m nldba_executor "show blocking sessions"
```

### Execute against Oracle

Add `--execute` to run (requires Oracle env vars):

```bash
python nl_dba_executor.py "show tablespace usage" --execute
```

If the safety policy requires confirmation, you’ll be prompted.

### Non-interactive usage

If confirmation would be required, `--no-confirm` will fail instead of prompting:

```bash
python nl_dba_executor.py "drop user bob" --execute --no-confirm
```

## Test & validation

There are no unit tests in this repo yet. Use the checks below as a validation checklist.

### 1) Syntax/compile check

```bash
python -m py_compile nl_dba_executor.py
python -m py_compile nldba_executor/*.py
```

### 2) CLI help smoke test

```bash
python nl_dba_executor.py --help
python -m nldba_executor --help
```

### 3) Dry-run validation (no DB required)

```bash
OPENAI_API_KEY=... python nl_dba_executor.py "list top 10 sessions by cpu"
```

Confirm:
- SQL is what you expect
- policy decision matches the risk level
- binds (if any) look correct

### 4) Execution validation (requires Oracle)

Run a safe query first:

```bash
python nl_dba_executor.py "select sysdate from dual" --execute
```

Then try a slightly more complex read-only request:

```bash
python nl_dba_executor.py "show current user and database name" --execute
```

### 6) Deactivate the virtual environment (optional)

```bash
deactivate
```

### 5) Log validation

After a run, check logs in:

- `.nl_dba_executor_logs/events-YYYY-MM-DD.jsonl`

Each line is a JSON object describing either:
- `plan_generated`
- `execution_attempt`
