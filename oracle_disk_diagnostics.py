#!/usr/bin/env python3
"""
Oracle ASM Disk Write Error Diagnostics and Monitoring Tool
Handles ORA-15032 and ORA-15096 errors

This tool helps diagnose and monitor Oracle ASM disk write errors by:
1. Checking disk group status
2. Identifying problematic disks
3. Monitoring for lost writes
4. Providing remediation recommendations
"""

import sys
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

try:
    import cx_Oracle
    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False
    print("Warning: cx_Oracle not installed. Install with: pip install cx_Oracle")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('oracle_disk_diagnostics.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class OracleASMDiagnostics:
    """Diagnostic tool for Oracle ASM disk write errors"""
    
    def __init__(self, connection_string: str, as_sysdba: bool = False):
        """
        Initialize the diagnostics tool
        
        Args:
            connection_string: Oracle connection string (user/pass@host:port/service)
            as_sysdba: Whether to connect as SYSDBA
        """
        self.connection_string = connection_string
        self.as_sysdba = as_sysdba
        self.connection = None
        
    def connect(self) -> bool:
        """Establish connection to Oracle database"""
        if not ORACLE_AVAILABLE:
            logger.error("cx_Oracle module not available")
            return False
            
        try:
            mode = cx_Oracle.SYSDBA if self.as_sysdba else cx_Oracle.DEFAULT_AUTH
            self.connection = cx_Oracle.connect(self.connection_string, mode=mode)
            logger.info("Successfully connected to Oracle database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Oracle: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Oracle database")
    
    def check_diskgroup_status(self) -> List[Dict]:
        """
        Check the status of all ASM disk groups
        
        Returns:
            List of disk group information dictionaries
        """
        query = """
            SELECT 
                name,
                state,
                type,
                total_mb,
                free_mb,
                offline_disks,
                voting_files
            FROM v$asm_diskgroup
            ORDER BY name
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            diskgroups = []
            for row in cursor:
                diskgroup = {
                    'name': row[0],
                    'state': row[1],
                    'type': row[2],
                    'total_mb': row[3],
                    'free_mb': row[4],
                    'offline_disks': row[5],
                    'voting_files': row[6]
                }
                diskgroups.append(diskgroup)
                
                # Log warnings for problematic disk groups
                if row[1] != 'MOUNTED':
                    logger.warning(f"Disk group {row[0]} is in {row[1]} state")
                if row[5] > 0:
                    logger.warning(f"Disk group {row[0]} has {row[5]} offline disks")
            
            cursor.close()
            return diskgroups
            
        except Exception as e:
            logger.error(f"Error checking disk group status: {e}")
            return []
    
    def check_disk_status(self) -> List[Dict]:
        """
        Check the status of individual ASM disks
        
        Returns:
            List of disk information dictionaries
        """
        query = """
            SELECT 
                d.group_number,
                dg.name as diskgroup_name,
                d.disk_number,
                d.name as disk_name,
                d.path,
                d.mount_status,
                d.header_status,
                d.mode_status,
                d.state,
                d.total_mb,
                d.free_mb,
                d.reads,
                d.writes,
                d.read_errs,
                d.write_errs,
                d.read_time,
                d.write_time
            FROM v$asm_disk d
            LEFT JOIN v$asm_diskgroup dg ON d.group_number = dg.group_number
            ORDER BY dg.name, d.disk_number
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            disks = []
            for row in cursor:
                disk = {
                    'group_number': row[0],
                    'diskgroup_name': row[1],
                    'disk_number': row[2],
                    'disk_name': row[3],
                    'path': row[4],
                    'mount_status': row[5],
                    'header_status': row[6],
                    'mode_status': row[7],
                    'state': row[8],
                    'total_mb': row[9],
                    'free_mb': row[10],
                    'reads': row[11],
                    'writes': row[12],
                    'read_errors': row[13],
                    'write_errors': row[14],
                    'read_time': row[15],
                    'write_time': row[16]
                }
                disks.append(disk)
                
                # Log warnings for problematic disks
                if row[5] != 'CACHED':
                    logger.warning(f"Disk {row[3]} has mount status: {row[5]}")
                if row[6] != 'MEMBER':
                    logger.warning(f"Disk {row[3]} has header status: {row[6]}")
                if row[8] != 'NORMAL':
                    logger.warning(f"Disk {row[3]} is in {row[8]} state")
                if row[13] > 0 or row[14] > 0:
                    logger.error(f"Disk {row[3]} has errors - Read: {row[13]}, Write: {row[14]}")
            
            cursor.close()
            return disks
            
        except Exception as e:
            logger.error(f"Error checking disk status: {e}")
            return []
    
    def check_alert_log_errors(self, hours: int = 24) -> List[Dict]:
        """
        Check for recent ORA-15032 and ORA-15096 errors in alert log
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of error records
        """
        query = f"""
            SELECT 
                originating_timestamp,
                message_text,
                message_level
            FROM v$diag_alert_ext
            WHERE 
                (message_text LIKE '%ORA-15032%' OR message_text LIKE '%ORA-15096%')
                AND originating_timestamp >= SYSTIMESTAMP - INTERVAL '{hours}' HOUR
            ORDER BY originating_timestamp DESC
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            errors = []
            for row in cursor:
                error = {
                    'timestamp': row[0],
                    'message': row[1],
                    'level': row[2]
                }
                errors.append(error)
                logger.error(f"Alert Log Error [{row[0]}]: {row[1]}")
            
            cursor.close()
            return errors
            
        except Exception as e:
            logger.error(f"Error checking alert log: {e}")
            return []
    
    def check_asm_operations(self) -> List[Dict]:
        """
        Check ongoing ASM operations
        
        Returns:
            List of ongoing operations
        """
        query = """
            SELECT 
                group_number,
                operation,
                state,
                power,
                actual,
                sofar,
                est_work,
                est_rate,
                est_minutes
            FROM v$asm_operation
        """
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            operations = []
            for row in cursor:
                operation = {
                    'group_number': row[0],
                    'operation': row[1],
                    'state': row[2],
                    'power': row[3],
                    'actual': row[4],
                    'sofar': row[5],
                    'est_work': row[6],
                    'est_rate': row[7],
                    'est_minutes': row[8]
                }
                operations.append(operation)
                logger.info(f"Ongoing operation: {row[1]} in state {row[2]}")
            
            cursor.close()
            return operations
            
        except Exception as e:
            logger.error(f"Error checking ASM operations: {e}")
            return []
    
    def get_remediation_recommendations(self, 
                                       diskgroups: List[Dict], 
                                       disks: List[Dict]) -> List[str]:
        """
        Generate remediation recommendations based on diagnostics
        
        Args:
            diskgroups: Disk group information
            disks: Disk information
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check for offline disks
        offline_count = sum(dg['offline_disks'] for dg in diskgroups if dg['offline_disks'])
        if offline_count > 0:
            recommendations.append(
                f"CRITICAL: {offline_count} offline disk(s) detected. "
                "Investigate and repair/replace failed disks immediately."
            )
        
        # Check for disks with errors
        error_disks = [d for d in disks if d['read_errors'] > 0 or d['write_errors'] > 0]
        if error_disks:
            recommendations.append(
                f"ERROR: {len(error_disks)} disk(s) with I/O errors detected. "
                "Check disk paths, hardware, and storage array status."
            )
            for disk in error_disks:
                recommendations.append(
                    f"  - Disk: {disk['disk_name']} (Path: {disk['path']}) - "
                    f"Read Errors: {disk['read_errors']}, Write Errors: {disk['write_errors']}"
                )
        
        # Check for unmounted disk groups
        unmounted = [dg for dg in diskgroups if dg['state'] != 'MOUNTED']
        if unmounted:
            recommendations.append(
                f"WARNING: {len(unmounted)} disk group(s) not in MOUNTED state. "
                "Attempt to mount them or investigate why they failed to mount."
            )
        
        # Check for disks not in NORMAL state
        abnormal_disks = [d for d in disks if d['state'] != 'NORMAL']
        if abnormal_disks:
            recommendations.append(
                f"WARNING: {len(abnormal_disks)} disk(s) not in NORMAL state. "
                "These disks may be undergoing rebalancing or have issues."
            )
        
        # General recommendations for ORA-15096
        recommendations.append(
            "\nGeneral recommendations for ORA-15096 (lost disk write):"
        )
        recommendations.append(
            "1. Check storage array logs for hardware failures or configuration issues"
        )
        recommendations.append(
            "2. Verify disk path connectivity and multipathing configuration"
        )
        recommendations.append(
            "3. Check for firmware updates on storage controllers and HBAs"
        )
        recommendations.append(
            "4. Review system logs (/var/log/messages) for I/O errors"
        )
        recommendations.append(
            "5. Verify ASM disk discovery string is correctly configured"
        )
        recommendations.append(
            "6. Consider running disk surface scans on problematic disks"
        )
        
        # Recommendations for ORA-15032
        recommendations.append(
            "\nGeneral recommendations for ORA-15032 (alterations not performed):"
        )
        recommendations.append(
            "1. Check if there are sufficient disks available for the operation"
        )
        recommendations.append(
            "2. Verify disk group redundancy requirements can be met"
        )
        recommendations.append(
            "3. Check for space availability in the disk group"
        )
        recommendations.append(
            "4. Review alert log for related error messages"
        )
        recommendations.append(
            "5. Ensure no disks are in FORCING state"
        )
        
        return recommendations
    
    def generate_report(self) -> str:
        """
        Generate comprehensive diagnostics report
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("ORACLE ASM DISK WRITE ERROR DIAGNOSTICS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # Disk Group Status
        report.append("DISK GROUP STATUS")
        report.append("-" * 80)
        diskgroups = self.check_diskgroup_status()
        if diskgroups:
            for dg in diskgroups:
                report.append(f"Disk Group: {dg['name']}")
                report.append(f"  State: {dg['state']}")
                report.append(f"  Type: {dg['type']}")
                report.append(f"  Total Space: {dg['total_mb']} MB")
                report.append(f"  Free Space: {dg['free_mb']} MB")
                report.append(f"  Offline Disks: {dg['offline_disks']}")
                report.append(f"  Voting Files: {dg['voting_files']}")
                report.append("")
        else:
            report.append("No disk groups found or error retrieving information")
        report.append("")
        
        # Individual Disk Status
        report.append("INDIVIDUAL DISK STATUS")
        report.append("-" * 80)
        disks = self.check_disk_status()
        if disks:
            for disk in disks:
                report.append(f"Disk: {disk['disk_name']} (Group: {disk['diskgroup_name']})")
                report.append(f"  Path: {disk['path']}")
                report.append(f"  State: {disk['state']}")
                report.append(f"  Mount Status: {disk['mount_status']}")
                report.append(f"  Header Status: {disk['header_status']}")
                report.append(f"  Total Size: {disk['total_mb']} MB")
                report.append(f"  I/O Stats - Reads: {disk['reads']}, Writes: {disk['writes']}")
                report.append(f"  Errors - Read: {disk['read_errors']}, Write: {disk['write_errors']}")
                if disk['read_errors'] > 0 or disk['write_errors'] > 0:
                    report.append("  *** ERROR: I/O ERRORS DETECTED ***")
                report.append("")
        else:
            report.append("No disks found or error retrieving information")
        report.append("")
        
        # Recent Alert Log Errors
        report.append("RECENT ALERT LOG ERRORS (Last 24 hours)")
        report.append("-" * 80)
        errors = self.check_alert_log_errors(24)
        if errors:
            for error in errors:
                report.append(f"[{error['timestamp']}] {error['message']}")
        else:
            report.append("No recent ORA-15032 or ORA-15096 errors found")
        report.append("")
        
        # Ongoing Operations
        report.append("ONGOING ASM OPERATIONS")
        report.append("-" * 80)
        operations = self.check_asm_operations()
        if operations:
            for op in operations:
                report.append(f"Operation: {op['operation']}")
                report.append(f"  State: {op['state']}")
                report.append(f"  Progress: {op['sofar']}/{op['est_work']}")
                report.append(f"  Estimated Time: {op['est_minutes']} minutes")
                report.append("")
        else:
            report.append("No ongoing ASM operations")
        report.append("")
        
        # Remediation Recommendations
        report.append("REMEDIATION RECOMMENDATIONS")
        report.append("-" * 80)
        recommendations = self.get_remediation_recommendations(diskgroups, disks)
        for rec in recommendations:
            report.append(rec)
        report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_diagnostics(self):
        """Run complete diagnostics and generate report"""
        if not self.connect():
            logger.error("Cannot run diagnostics without database connection")
            return
        
        try:
            report = self.generate_report()
            print(report)
            
            # Save report to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"asm_diagnostics_{timestamp}.txt"
            with open(filename, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {filename}")
            
        finally:
            self.disconnect()


class OracleErrorSimulator:
    """Simulate and test error handling without requiring actual Oracle connection"""
    
    @staticmethod
    def simulate_ora_15096_scenario():
        """Simulate ORA-15096 lost disk write error scenario"""
        print("\n" + "=" * 80)
        print("SIMULATING ORA-15096: Lost Disk Write Error")
        print("=" * 80)
        print("\nScenario Description:")
        print("A write operation to ASM disk was not confirmed by the storage layer.")
        print("This typically indicates hardware or storage array issues.\n")
        
        print("Typical Causes:")
        print("1. Storage array controller failure")
        print("2. Disk firmware issues")
        print("3. Cable or HBA problems")
        print("4. Multipathing configuration errors")
        print("5. Write cache issues on storage")
        
        print("\nImmediate Actions:")
        print("1. Check storage array status and logs")
        print("2. Verify all disk paths are accessible")
        print("3. Review /var/log/messages for I/O errors")
        print("4. Check ASM alert log for additional details")
        print("5. Verify disk group redundancy is sufficient")
        
        print("\nSQL Queries to Run:")
        print("""
-- Check disk status
SELECT name, path, state, mode_status, mount_status 
FROM v$asm_disk 
WHERE state != 'NORMAL' OR mount_status != 'CACHED';

-- Check for I/O errors
SELECT name, path, reads, writes, read_errs, write_errs 
FROM v$asm_disk 
WHERE read_errs > 0 OR write_errs > 0;

-- Check disk group status
SELECT name, state, type, offline_disks 
FROM v$asm_diskgroup;
        """)
    
    @staticmethod
    def simulate_ora_15032_scenario():
        """Simulate ORA-15032 alterations not performed error scenario"""
        print("\n" + "=" * 80)
        print("SIMULATING ORA-15032: Not All Alterations Performed")
        print("=" * 80)
        print("\nScenario Description:")
        print("An ALTER DISKGROUP command could not complete all requested operations.")
        print("This often occurs with disk add/drop operations when underlying issues exist.\n")
        
        print("Typical Causes:")
        print("1. Insufficient disks to maintain redundancy")
        print("2. Disks in FORCING state")
        print("3. Disk path accessibility issues")
        print("4. Disk header corruption")
        print("5. Insufficient space for rebalancing")
        
        print("\nImmediate Actions:")
        print("1. Check alert log for detailed error messages")
        print("2. Verify disk group redundancy requirements")
        print("3. Check for disks in FORCING state")
        print("4. Ensure sufficient free space exists")
        print("5. Verify disk discovery string is correct")
        
        print("\nSQL Queries to Run:")
        print("""
-- Check for problematic disk states
SELECT group_number, name, path, header_status, mode_status, state 
FROM v$asm_disk 
WHERE header_status != 'MEMBER' OR state = 'FORCING';

-- Check rebalance operations
SELECT group_number, operation, state, power, sofar, est_work 
FROM v$asm_operation;

-- Check disk group redundancy
SELECT name, type, total_mb, free_mb, required_mirror_free_mb 
FROM v$asm_diskgroup;

-- Check for failed disk operations
SELECT group_number, operation, state, error_code 
FROM v$asm_operation 
WHERE state = 'ERROR';
        """)


def main():
    """Main entry point for the diagnostics tool"""
    parser = argparse.ArgumentParser(
        description='Oracle ASM Disk Write Error Diagnostics Tool'
    )
    parser.add_argument(
        '--connection',
        help='Oracle connection string (format: user/pass@host:port/service)',
        type=str
    )
    parser.add_argument(
        '--sysdba',
        action='store_true',
        help='Connect as SYSDBA'
    )
    parser.add_argument(
        '--simulate',
        choices=['15096', '15032', 'both'],
        help='Simulate error scenarios without database connection'
    )
    
    args = parser.parse_args()
    
    if args.simulate:
        simulator = OracleErrorSimulator()
        if args.simulate in ['15096', 'both']:
            simulator.simulate_ora_15096_scenario()
        if args.simulate in ['15032', 'both']:
            simulator.simulate_ora_15032_scenario()
        return
    
    if not args.connection:
        print("Error: --connection required (unless using --simulate)")
        print("Example: --connection 'sys/password@localhost:1521/orcl' --sysdba")
        print("\nOr use --simulate to see error scenarios without database connection")
        print("Example: --simulate both")
        sys.exit(1)
    
    if not ORACLE_AVAILABLE:
        print("Error: cx_Oracle module not installed")
        print("Install it with: pip install cx_Oracle")
        sys.exit(1)
    
    diagnostics = OracleASMDiagnostics(args.connection, args.sysdba)
    diagnostics.run_diagnostics()


if __name__ == '__main__':
    main()
