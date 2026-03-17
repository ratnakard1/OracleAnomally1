# Oracle Database Creation Scripts

Scripts for manually creating an Oracle database. Use these when you need fine-grained control over database creation (e.g., custom file layouts, specific character sets, or automation).

## Prerequisites

- Oracle Database software installed (19c or 21c recommended)
- `oracle` user with SYSDBA privilege
- Sufficient disk space for datafiles
- `ORACLE_HOME` and `ORACLE_BASE` environment variables set

## Scripts Overview

| Script | Description |
|--------|-------------|
| `init.ora.template` | Initialization parameter template |
| `00_create_directories.sh` | Creates required directory structure |
| `01_create_database.sql` | Main CREATE DATABASE statement |
| `02_post_creation.sql` | Data dictionary and post-creation setup |
| `03_create_application_user.sql` | Optional application user creation |
| `create_database.sh` | Orchestration script (runs all steps) |

## Quick Start

### 1. Prepare the initialization file

```bash
cp scripts/init.ora.template $ORACLE_HOME/dbs/initORCL.ora
# Edit initORCL.ora: replace <SID>, <ORACLE_HOME>, <ORACLE_BASE>
```

### 2. Create directories

```bash
./scripts/00_create_directories.sh /u01/app/oracle ORCL
```

### 3. Prepare CREATE DATABASE script

Edit `scripts/01_create_database.sql` and replace:
- `<SID>` - Your database name (e.g., ORCL)
- `<ORACLE_BASE>` - Oracle base path
- `<SYS_PASSWORD>` - SYS user password
- `<SYSTEM_PASSWORD>` - SYSTEM user password

### 4. Run database creation

```bash
export ORACLE_SID=ORCL
export ORACLE_HOME=/u01/app/oracle/product/19c/dbhome_1
export ORACLE_BASE=/u01/app/oracle
./scripts/create_database.sh
```

### 5. (Optional) Create application user

Edit `scripts/03_create_application_user.sql` and run:

```bash
sqlplus / as sysdba @scripts/03_create_application_user.sql
```

## Manual Step-by-Step

If you prefer to run steps manually:

```bash
# 1. Start instance
sqlplus / as sysdba
SQL> STARTUP NOMOUNT;

# 2. Run CREATE DATABASE (from another terminal)
sqlplus / as sysdba @scripts/01_create_database.sql

# 3. Run post-creation
sqlplus / as sysdba @scripts/02_post_creation.sql
```

## Customization

- **Character set**: Default is AL32UTF8 (Unicode). Change in `01_create_database.sql` if needed.
- **File sizes**: Adjust SIZE values for system, sysaux, undo, and temp datafiles.
- **Tablespaces**: Uncomment and modify in `02_post_creation.sql` for custom tablespaces.
- **Memory**: Edit `init.ora.template` for `memory_target`, `sga_target`, `pga_aggregate_target`.

## Security Notes

- Never commit passwords to version control. Use placeholders and set values at runtime.
- Consider using Oracle Wallet for password storage in production.
- Restrict init file permissions: `chmod 600 initORCL.ora`
