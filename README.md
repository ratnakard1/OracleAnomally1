# Oracle ASM Disk Write Error Handler

This repository contains tools and documentation for handling Oracle ASM (Automatic Storage Management) disk write errors, specifically:

- **ORA-15032**: not all alterations performed
- **ORA-15096**: lost disk write detected

## Overview

These errors indicate serious issues with Oracle ASM disk groups that require immediate attention. ORA-15096 is particularly critical as it indicates that a disk write operation failed, potentially leading to data corruption or loss.

## Files

- `oracle_asm_disk_error_handler.py` - Python script to detect, parse, and provide remediation steps for ASM errors
- `asm_diagnostic_queries.sql` - SQL queries for diagnosing ASM disk issues
- `README.md` - This documentation file

## Quick Start

### Using the Error Handler Script

```bash
# Parse an error message directly
python oracle_asm_disk_error_handler.py -e "ORA-15096: lost disk write detected"

# Parse errors from a log file
python oracle_asm_disk_error_handler.py -f alert.log

# Export diagnostic queries
python oracle_asm_disk_error_handler.py --export-queries diagnostic.sql

# Read from stdin
echo "ORA-15032: not all alterations performed" | python oracle_asm_disk_error_handler.py
```

### Running Diagnostic Queries

Connect to your ASM instance as SYSDBA and run the queries in `asm_diagnostic_queries.sql`:

```bash
sqlplus / as sysasm @asm_diagnostic_queries.sql
```

## Error Details

### ORA-15032: not all alterations performed

**Severity**: HIGH  
**Description**: This error occurs when an ALTER DISKGROUP command cannot complete all requested operations. This typically happens when:

- Disks are offline or unavailable
- Insufficient space in the disk group
- Ongoing rebalance operations conflict
- Disk failures prevent the operation

**Common Causes**:
- Disk hardware failures
- Network issues (for network-attached storage)
- Disk group space constraints
- Concurrent operations blocking the alteration

### ORA-15096: lost disk write detected

**Severity**: CRITICAL  
**Description**: This error indicates that Oracle ASM detected a lost disk write operation. This is a serious condition that can lead to:

- Data corruption
- Data loss
- Inconsistent disk group state

**Common Causes**:
- Disk hardware failures
- Storage array issues
- Network problems (for network storage)
- I/O subsystem failures
- Disk controller problems

## Remediation Steps

### For ORA-15032

1. **Check disk group status**:
   ```sql
   SELECT name, state, type, offline_disks FROM v$asm_diskgroup;
   ```

2. **Identify offline disks**:
   ```sql
   SELECT dg.name, d.path, d.name, d.state, d.header_status
   FROM v$asm_disk d, v$asm_diskgroup dg
   WHERE d.group_number = dg.group_number AND d.state != 'NORMAL';
   ```

3. **Check for ongoing operations**:
   ```sql
   SELECT * FROM v$asm_operation;
   ```

4. **Attempt to bring disks online** (if safe):
   ```sql
   ALTER DISKGROUP <diskgroup_name> ONLINE DISK '<disk_path>';
   ```

5. **Review alert log**:
   ```sql
   SELECT * FROM v$asm_alert_history 
   WHERE message_timestamp >= SYSDATE - 1;
   ```

### For ORA-15096

1. **CRITICAL**: Immediately identify the affected disk

2. **Check disk I/O statistics**:
   ```sql
   SELECT dg.name, d.name, d.read_errs, d.write_errs
   FROM v$asm_disk_stat d, v$asm_diskgroup dg
   WHERE d.group_number = dg.group_number
   AND (d.read_errs > 0 OR d.write_errs > 0);
   ```

3. **Verify hardware status**:
   - Check disk health using OS tools (`smartctl`, `dmesg`, etc.)
   - Verify network connectivity (for network storage)
   - Check storage array logs

4. **If disk is recoverable**:
   ```sql
   ALTER DISKGROUP <diskgroup_name> ONLINE DISK '<disk_path>';
   ```

5. **If disk is permanently failed**:
   ```sql
   ALTER DISKGROUP <diskgroup_name> DROP DISK '<disk_name>';
   ```
   ⚠️ **Warning**: Ensure redundancy allows for disk removal

6. **Add replacement disk** (if needed):
   ```sql
   ALTER DISKGROUP <diskgroup_name> ADD DISK '<new_disk_path>';
   ```

7. **Monitor rebalance operation**:
   ```sql
   SELECT * FROM v$asm_operation;
   ```

## Prevention

To prevent these errors:

1. **Regular Monitoring**:
   - Monitor disk I/O statistics regularly
   - Set up alerts for disk errors
   - Review ASM alert logs daily

2. **Hardware Maintenance**:
   - Perform regular hardware health checks
   - Replace aging disks proactively
   - Monitor storage array health

3. **Configuration**:
   - Ensure adequate redundancy (NORMAL or HIGH)
   - Maintain proper failgroup distribution
   - Keep sufficient free space in disk groups

4. **Best Practices**:
   - Use multiple failgroups for redundancy
   - Distribute disks across different physical paths
   - Monitor disk repair timers
   - Keep ASM and database compatibility current

## Monitoring Script

You can integrate the error handler into your monitoring system:

```bash
#!/bin/bash
# Monitor Oracle alert log for ASM errors

ALERT_LOG="/u01/app/oracle/diag/asm/+asm/+ASM/trace/alert_+ASM.log"
ERROR_HANDLER="/path/to/oracle_asm_disk_error_handler.py"

# Check for errors
if grep -E "ORA-15032|ORA-15096" "$ALERT_LOG" | tail -1 | "$ERROR_HANDLER" -f -; then
    # Errors detected, send alert
    echo "ASM errors detected!" | mail -s "Oracle ASM Alert" dba@company.com
fi
```

## Requirements

- Python 3.6+
- Oracle Database with ASM (for running diagnostic queries)
- SYSDBA or ASM instance access (for diagnostic queries)

## License

This tool is provided as-is for diagnostic and remediation purposes.

## Support

For Oracle-specific issues, consult:
- Oracle Support (My Oracle Support)
- Oracle ASM documentation
- Your database administrator

## References

- Oracle Database Storage Administrator's Guide
- Oracle ASM Best Practices
- Oracle Error Messages documentation
