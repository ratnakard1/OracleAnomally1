#!/bin/bash
# Oracle Database Creation - Main Orchestration Script
# Run as oracle user with ORACLE_HOME and ORACLE_SID set
#
# Prerequisites:
#   1. Oracle software installed
#   2. init<SID>.ora in $ORACLE_HOME/dbs/
#   3. Directories created (run 00_create_directories.sh)
#
# Usage:
#   export ORACLE_HOME=/u01/app/oracle/product/19c/dbhome_1
#   export ORACLE_BASE=/u01/app/oracle
#   export ORACLE_SID=ORCL
#   ./create_database.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE_SID=${ORACLE_SID:?"ORACLE_SID must be set"}
ORACLE_HOME=${ORACLE_HOME:?"ORACLE_HOME must be set"}
ORACLE_BASE=${ORACLE_BASE:-/u01/app/oracle}

INIT_FILE="${ORACLE_HOME}/dbs/init${ORACLE_SID}.ora"

if [[ ! -f "${INIT_FILE}" ]]; then
    echo "Error: Init file not found: ${INIT_FILE}"
    echo "Copy init.ora.template to init${ORACLE_SID}.ora and configure it."
    exit 1
fi

echo "Starting database creation for ${ORACLE_SID}..."
echo "ORACLE_HOME: ${ORACLE_HOME}"
echo "ORACLE_BASE: ${ORACLE_BASE}"

# Start instance in NOMOUNT mode
echo "Starting instance in NOMOUNT mode..."
sqlplus -S / as sysdba <<EOF
STARTUP NOMOUNT;
EOF

# Run CREATE DATABASE
# Note: You must have prepared 01_create_database.sql with actual passwords and paths
CREATE_SCRIPT="${SCRIPT_DIR}/01_create_database.sql"
if [[ -f "${CREATE_SCRIPT}" ]]; then
    echo "Running CREATE DATABASE..."
    sqlplus -S / as sysdba @"${CREATE_SCRIPT}"
else
    echo "Error: ${CREATE_SCRIPT} not found"
    sqlplus -S / as sysdba <<EOF
SHUTDOWN ABORT;
EOF
    exit 1
fi

# Run post-creation script
echo "Running post-creation script..."
sqlplus -S / as sysdba @"${SCRIPT_DIR}/02_post_creation.sql"

echo "Database ${ORACLE_SID} created successfully."
