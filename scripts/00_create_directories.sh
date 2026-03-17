#!/bin/bash
# Create Oracle database directory structure
# Run as oracle user before database creation
# Usage: ./00_create_directories.sh <ORACLE_BASE> <SID>

set -e

ORACLE_BASE=${1:?"Usage: $0 <ORACLE_BASE> <SID>"}
SID=${2:?"Usage: $0 <ORACLE_BASE> <SID>"}

BASE_DIR="${ORACLE_BASE}/oradata/${SID}"
ARCH_DIR="${ORACLE_BASE}/oradata/${SID}/archivelog"

echo "Creating directory structure for ${SID}..."

mkdir -p "${BASE_DIR}"
mkdir -p "${ARCH_DIR}"

echo "Directories created:"
echo "  - ${BASE_DIR}"
echo "  - ${ARCH_DIR}"
