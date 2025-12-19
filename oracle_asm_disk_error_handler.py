#!/usr/bin/env python3
"""
Oracle ASM Disk Write Error Handler

This script detects, diagnoses, and provides remediation steps for:
- ORA-15032: not all alterations performed
- ORA-15096: lost disk write detected

These errors typically indicate issues with Oracle ASM (Automatic Storage Management)
disk groups, which can be caused by:
- Disk I/O failures
- Network issues (for network-attached storage)
- Disk corruption
- Hardware failures
- ASM instance configuration issues
"""

import sys
import re
import argparse
from typing import List, Dict, Optional
from datetime import datetime


class OracleASMErrorHandler:
    """Handles Oracle ASM disk write errors"""
    
    ERROR_CODES = {
        'ORA-15032': {
            'description': 'not all alterations performed',
            'severity': 'HIGH',
            'category': 'ASM_ALTERATION_FAILURE'
        },
        'ORA-15096': {
            'description': 'lost disk write detected',
            'severity': 'CRITICAL',
            'category': 'ASM_DISK_WRITE_FAILURE'
        }
    }
    
    def __init__(self):
        self.errors_detected = []
        self.diagnostic_queries = self._generate_diagnostic_queries()
    
    def parse_error(self, error_message: str) -> Optional[Dict]:
        """Parse Oracle error message and extract error code and details"""
        # First check if DBD error is present to extract it separately
        dbd_match = re.search(r'\(DBD ERROR:\s*([^)]+)\)', error_message, re.IGNORECASE)
        dbd_error = dbd_match.group(1) if dbd_match else None
        
        # Remove DBD error from message for main parsing
        clean_message = re.sub(r'\s*\(DBD ERROR:[^)]+\)', '', error_message)
        
        # Parse the main error
        error_pattern = r'ORA-(\d+):\s*(.+)'
        match = re.search(error_pattern, clean_message, re.IGNORECASE)
        
        if match:
            error_code = f"ORA-{match.group(1)}"
            error_desc = match.group(2).strip()
            
            return {
                'error_code': error_code,
                'description': error_desc,
                'dbd_error': dbd_error,
                'full_message': error_message,
                'timestamp': datetime.now().isoformat(),
                'error_info': self.ERROR_CODES.get(error_code, {})
            }
        return None
    
    def detect_errors(self, log_content: str) -> List[Dict]:
        """Detect Oracle ASM errors in log content"""
        errors = []
        lines = log_content.split('\n')
        
        for line in lines:
            parsed = self.parse_error(line)
            if parsed:
                errors.append(parsed)
        
        self.errors_detected = errors
        return errors
    
    def _generate_diagnostic_queries(self) -> Dict[str, str]:
        """Generate SQL queries for diagnosing ASM issues"""
        return {
            'check_diskgroup_status': """
                SELECT 
                    name,
                    state,
                    type,
                    total_mb,
                    free_mb,
                    usable_file_mb,
                    offline_disks,
                    compatibility,
                    database_compatibility
                FROM v$asm_diskgroup
                ORDER BY name;
            """,
            
            'check_disk_status': """
                SELECT 
                    dg.name AS diskgroup_name,
                    d.path,
                    d.name AS disk_name,
                    d.state,
                    d.mode_status,
                    d.header_status,
                    d.mount_status,
                    d.total_mb,
                    d.free_mb,
                    d.failgroup,
                    d.create_date,
                    d.repair_timer
                FROM v$asm_disk d
                JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
                ORDER BY dg.name, d.name;
            """,
            
            'check_offline_disks': """
                SELECT 
                    dg.name AS diskgroup_name,
                    d.path,
                    d.name AS disk_name,
                    d.state,
                    d.header_status,
                    d.mode_status,
                    d.repair_timer,
                    d.failgroup
                FROM v$asm_disk d
                JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
                WHERE d.state != 'NORMAL'
                ORDER BY dg.name, d.name;
            """,
            
            'check_asm_operations': """
                SELECT 
                    operation,
                    state,
                    power,
                    actual,
                    sofar,
                    est_work,
                    est_rate,
                    est_minutes
                FROM v$asm_operation
                ORDER BY operation;
            """,
            
            'check_asm_alert_log': """
                SELECT 
                    message_text,
                    message_level,
                    message_type,
                    message_timestamp
                FROM v$asm_alert_history
                WHERE message_timestamp >= SYSDATE - 1
                AND (message_text LIKE '%ORA-15032%' 
                     OR message_text LIKE '%ORA-15096%'
                     OR message_text LIKE '%disk write%'
                     OR message_text LIKE '%lost write%')
                ORDER BY message_timestamp DESC;
            """,
            
            'check_disk_io_stats': """
                SELECT 
                    dg.name AS diskgroup_name,
                    d.name AS disk_name,
                    d.reads,
                    d.writes,
                    d.read_errs,
                    d.write_errs,
                    d.read_time,
                    d.write_time
                FROM v$asm_disk_stat d
                JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
                WHERE d.read_errs > 0 OR d.write_errs > 0
                ORDER BY dg.name, (d.read_errs + d.write_errs) DESC;
            """
        }
    
    def generate_remediation_steps(self, error_code: str) -> List[str]:
        """Generate remediation steps based on error code"""
        steps = []
        
        if error_code == 'ORA-15032':
            steps = [
                "1. Check ASM alert log for detailed error messages:",
                "   SELECT * FROM v$asm_alert_history WHERE message_timestamp >= SYSDATE - 1;",
                "",
                "2. Verify disk group status:",
                "   SELECT name, state, type, offline_disks FROM v$asm_diskgroup;",
                "",
                "3. Check for offline or failed disks:",
                "   SELECT dg.name, d.path, d.name, d.state, d.header_status",
                "   FROM v$asm_disk d, v$asm_diskgroup dg",
                "   WHERE d.group_number = dg.group_number AND d.state != 'NORMAL';",
                "",
                "4. If disks are offline, attempt to bring them online:",
                "   ALTER DISKGROUP <diskgroup_name> ONLINE DISK '<disk_path>';",
                "",
                "5. Check for ongoing ASM operations:",
                "   SELECT * FROM v$asm_operation;",
                "",
                "6. If operation is stuck, you may need to:",
                "   - Wait for operation to complete",
                "   - Cancel the operation if safe to do so",
                "   - Restart ASM instance if necessary"
            ]
        
        elif error_code == 'ORA-15096':
            steps = [
                "1. CRITICAL: Lost disk write detected - immediate action required!",
                "",
                "2. Identify the affected disk:",
                "   SELECT dg.name, d.path, d.name, d.state, d.header_status, d.mode_status",
                "   FROM v$asm_disk d, v$asm_diskgroup dg",
                "   WHERE d.group_number = dg.group_number",
                "   AND d.state != 'NORMAL';",
                "",
                "3. Check disk I/O statistics for errors:",
                "   SELECT dg.name, d.name, d.read_errs, d.write_errs",
                "   FROM v$asm_disk_stat d, v$asm_diskgroup dg",
                "   WHERE d.group_number = dg.group_number",
                "   AND (d.read_errs > 0 OR d.write_errs > 0);",
                "",
                "4. Verify hardware status:",
                "   - Check disk health using OS tools (smartctl, etc.)",
                "   - Verify network connectivity (for network storage)",
                "   - Check storage array logs",
                "",
                "5. If disk is recoverable:",
                "   ALTER DISKGROUP <diskgroup_name> ONLINE DISK '<disk_path>';",
                "",
                "6. If disk is permanently failed:",
                "   ALTER DISKGROUP <diskgroup_name> DROP DISK '<disk_name>';",
                "   (Ensure redundancy allows for disk removal)",
                "",
                "7. If redundancy is compromised, add replacement disk:",
                "   ALTER DISKGROUP <diskgroup_name> ADD DISK '<new_disk_path>';",
                "",
                "8. Monitor rebalance operation:",
                "   SELECT * FROM v$asm_operation;",
                "",
                "9. Check alert log for any additional errors:",
                "   SELECT * FROM v$asm_alert_history WHERE message_timestamp >= SYSDATE - 1;"
            ]
        
        return steps
    
    def print_diagnostic_report(self):
        """Print a comprehensive diagnostic report"""
        print("=" * 80)
        print("ORACLE ASM DISK WRITE ERROR DIAGNOSTIC REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.errors_detected:
            print("No Oracle ASM errors detected.")
            return
        
        for i, error in enumerate(self.errors_detected, 1):
            print(f"\n{'=' * 80}")
            print(f"ERROR #{i}")
            print(f"{'=' * 80}")
            print(f"Error Code: {error['error_code']}")
            print(f"Description: {error['description']}")
            if error.get('dbd_error'):
                print(f"DBD Error: {error['dbd_error']}")
            
            error_info = error.get('error_info', {})
            if error_info:
                print(f"Severity: {error_info.get('severity', 'UNKNOWN')}")
                print(f"Category: {error_info.get('category', 'UNKNOWN')}")
            
            print(f"\nTimestamp: {error['timestamp']}")
            print(f"\nFull Message:\n{error['full_message']}")
            
            # Generate remediation steps
            remediation = self.generate_remediation_steps(error['error_code'])
            if remediation:
                print(f"\n{'=' * 80}")
                print("RECOMMENDED REMEDIATION STEPS:")
                print(f"{'=' * 80}")
                for step in remediation:
                    print(step)
        
        # Print diagnostic queries
        print(f"\n{'=' * 80}")
        print("DIAGNOSTIC SQL QUERIES")
        print(f"{'=' * 80}")
        for query_name, query in self.diagnostic_queries.items():
            print(f"\n-- {query_name.replace('_', ' ').title()}")
            print(query)
    
    def export_diagnostic_queries(self, output_file: str):
        """Export diagnostic queries to a SQL file"""
        with open(output_file, 'w') as f:
            f.write("-- Oracle ASM Disk Write Error Diagnostic Queries\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for query_name, query in self.diagnostic_queries.items():
                f.write(f"-- {query_name.replace('_', ' ').title()}\n")
                f.write(query)
                f.write("\n\n")


def main():
    parser = argparse.ArgumentParser(
        description='Oracle ASM Disk Write Error Handler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse error from command line
  python oracle_asm_disk_error_handler.py -e "ORA-15096: lost disk write detected"
  
  # Parse errors from log file
  python oracle_asm_disk_error_handler.py -f alert.log
  
  # Export diagnostic queries
  python oracle_asm_disk_error_handler.py --export-queries diagnostic.sql
        """
    )
    
    parser.add_argument(
        '-e', '--error',
        help='Oracle error message to parse'
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Log file containing Oracle errors'
    )
    
    parser.add_argument(
        '--export-queries',
        help='Export diagnostic queries to SQL file'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress output (useful with --export-queries)'
    )
    
    args = parser.parse_args()
    
    handler = OracleASMErrorHandler()
    
    # Process error input
    if args.error:
        handler.detect_errors(args.error)
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                content = f.read()
            handler.detect_errors(content)
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        content = sys.stdin.read()
        if content.strip():
            handler.detect_errors(content)
    
    # Export queries if requested
    if args.export_queries:
        handler.export_diagnostic_queries(args.export_queries)
        if not args.quiet:
            print(f"Diagnostic queries exported to: {args.export_queries}")
    
    # Print report unless quiet mode
    if not args.quiet:
        handler.print_diagnostic_report()
    
    # Exit with error code if errors were detected
    if handler.errors_detected:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
