#!/bin/bash
# Example usage of Oracle ASM Disk Diagnostics Tool

echo "=================================================="
echo "Oracle ASM Disk Diagnostics Tool - Usage Examples"
echo "=================================================="
echo ""

echo "1. Running simulation mode (no database required):"
echo "   python3 oracle_disk_diagnostics.py --simulate both"
echo ""

echo "2. Running diagnostics with database connection:"
echo "   python3 oracle_disk_diagnostics.py \\"
echo "     --connection 'sys/password@localhost:1521/+ASM' \\"
echo "     --sysdba"
echo ""

echo "3. Running unit tests:"
echo "   python3 test.py"
echo ""

echo "=================================================="
echo "Quick Start - Try simulation mode now:"
echo "=================================================="
echo ""

python3 oracle_disk_diagnostics.py --simulate both

echo ""
echo "=================================================="
echo "For more information, see:"
echo "  - README.md (full documentation)"
echo "  - QUICK_REFERENCE.md (troubleshooting guide)"
echo "=================================================="
