#!/usr/bin/env python3
"""
Test scenarios for Oracle ASM Disk Write Error Diagnostics Tool
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock cx_Oracle before importing the main module
sys.modules['cx_Oracle'] = MagicMock()

from oracle_disk_diagnostics import OracleASMDiagnostics, OracleErrorSimulator


class TestOracleASMDiagnostics(unittest.TestCase):
    """Test cases for Oracle ASM Diagnostics functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.connection_string = "sys/password@localhost:1521/+ASM"
        self.diagnostics = OracleASMDiagnostics(self.connection_string, as_sysdba=True)
    
    def test_initialization(self):
        """Test diagnostics object initialization"""
        self.assertEqual(self.diagnostics.connection_string, self.connection_string)
        self.assertTrue(self.diagnostics.as_sysdba)
        self.assertIsNone(self.diagnostics.connection)
    
    def test_get_remediation_recommendations_with_offline_disks(self):
        """Test recommendations when offline disks are detected"""
        diskgroups = [
            {'name': 'DATA', 'state': 'MOUNTED', 'offline_disks': 2, 'type': 'NORMAL'},
            {'name': 'FRA', 'state': 'MOUNTED', 'offline_disks': 0, 'type': 'EXTERN'}
        ]
        disks = []
        
        recommendations = self.diagnostics.get_remediation_recommendations(diskgroups, disks)
        
        self.assertTrue(any('CRITICAL' in rec and '2 offline' in rec for rec in recommendations))
    
    def test_get_remediation_recommendations_with_disk_errors(self):
        """Test recommendations when disk I/O errors are detected"""
        diskgroups = [{'name': 'DATA', 'state': 'MOUNTED', 'offline_disks': 0, 'type': 'NORMAL'}]
        disks = [
            {
                'disk_name': 'DATA_0001',
                'path': '/dev/oracleasm/disk1',
                'state': 'NORMAL',
                'read_errors': 5,
                'write_errors': 3
            }
        ]
        
        recommendations = self.diagnostics.get_remediation_recommendations(diskgroups, disks)
        
        self.assertTrue(any('ERROR' in rec and 'I/O errors' in rec for rec in recommendations))
        self.assertTrue(any('DATA_0001' in rec for rec in recommendations))
    
    def test_get_remediation_recommendations_with_unmounted_diskgroups(self):
        """Test recommendations when disk groups are not mounted"""
        diskgroups = [
            {'name': 'DATA', 'state': 'DISMOUNTED', 'offline_disks': 0, 'type': 'NORMAL'}
        ]
        disks = []
        
        recommendations = self.diagnostics.get_remediation_recommendations(diskgroups, disks)
        
        self.assertTrue(any('WARNING' in rec and 'not in MOUNTED state' in rec for rec in recommendations))
    
    def test_get_remediation_recommendations_includes_general_advice(self):
        """Test that general recommendations are always included"""
        diskgroups = []
        disks = []
        
        recommendations = self.diagnostics.get_remediation_recommendations(diskgroups, disks)
        
        # Should include recommendations for both ORA-15096 and ORA-15032
        rec_text = '\n'.join(recommendations)
        self.assertIn('ORA-15096', rec_text)
        self.assertIn('ORA-15032', rec_text)
        self.assertIn('storage array', rec_text.lower())
        self.assertIn('disk group redundancy', rec_text.lower())


class TestOracleErrorSimulator(unittest.TestCase):
    """Test cases for error simulation functionality"""
    
    def test_simulate_ora_15096_scenario(self):
        """Test ORA-15096 simulation output"""
        simulator = OracleErrorSimulator()
        
        # Capture stdout
        from io import StringIO
        import sys
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        simulator.simulate_ora_15096_scenario()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        self.assertIn('ORA-15096', output)
        self.assertIn('Lost Disk Write', output)
        self.assertIn('storage array', output.lower())
        self.assertIn('v$asm_disk', output)
    
    def test_simulate_ora_15032_scenario(self):
        """Test ORA-15032 simulation output"""
        simulator = OracleErrorSimulator()
        
        from io import StringIO
        import sys
        
        captured_output = StringIO()
        sys.stdout = captured_output
        
        simulator.simulate_ora_15032_scenario()
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        self.assertIn('ORA-15032', output)
        self.assertIn('Alterations', output)
        self.assertIn('redundancy', output.lower())
        self.assertIn('v$asm_diskgroup', output)


class TestReportGeneration(unittest.TestCase):
    """Test cases for report generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.diagnostics = OracleASMDiagnostics("test/test@test", as_sysdba=False)
        
        # Mock the connection and cursor
        self.diagnostics.connection = MagicMock()
    
    @patch.object(OracleASMDiagnostics, 'check_diskgroup_status')
    @patch.object(OracleASMDiagnostics, 'check_disk_status')
    @patch.object(OracleASMDiagnostics, 'check_alert_log_errors')
    @patch.object(OracleASMDiagnostics, 'check_asm_operations')
    def test_generate_report_structure(self, mock_ops, mock_errors, mock_disks, mock_diskgroups):
        """Test that generated report has correct structure"""
        # Set up mocks
        mock_diskgroups.return_value = [
            {
                'name': 'DATA',
                'state': 'MOUNTED',
                'type': 'EXTERN',
                'total_mb': 204800,
                'free_mb': 102400,
                'offline_disks': 0,
                'voting_files': 'N'
            }
        ]
        
        mock_disks.return_value = [
            {
                'diskgroup_name': 'DATA',
                'disk_name': 'DATA_0000',
                'path': '/dev/oracleasm/disk1',
                'state': 'NORMAL',
                'mount_status': 'CACHED',
                'header_status': 'MEMBER',
                'total_mb': 102400,
                'reads': 1000,
                'writes': 500,
                'read_errors': 0,
                'write_errors': 0
            }
        ]
        
        mock_errors.return_value = []
        mock_ops.return_value = []
        
        report = self.diagnostics.generate_report()
        
        # Verify report contains expected sections
        self.assertIn('ORACLE ASM DISK WRITE ERROR DIAGNOSTICS REPORT', report)
        self.assertIn('DISK GROUP STATUS', report)
        self.assertIn('INDIVIDUAL DISK STATUS', report)
        self.assertIn('RECENT ALERT LOG ERRORS', report)
        self.assertIn('ONGOING ASM OPERATIONS', report)
        self.assertIn('REMEDIATION RECOMMENDATIONS', report)
        self.assertIn('DATA', report)


class TestErrorDetection(unittest.TestCase):
    """Test cases for error detection logic"""
    
    def test_detect_disk_with_io_errors(self):
        """Test detection of disks with I/O errors"""
        disks = [
            {'disk_name': 'DISK1', 'read_errors': 0, 'write_errors': 0},
            {'disk_name': 'DISK2', 'read_errors': 5, 'write_errors': 0},
            {'disk_name': 'DISK3', 'read_errors': 0, 'write_errors': 3},
        ]
        
        error_disks = [d for d in disks if d['read_errors'] > 0 or d['write_errors'] > 0]
        
        self.assertEqual(len(error_disks), 2)
        self.assertEqual(error_disks[0]['disk_name'], 'DISK2')
        self.assertEqual(error_disks[1]['disk_name'], 'DISK3')
    
    def test_detect_offline_diskgroups(self):
        """Test detection of disk groups with offline disks"""
        diskgroups = [
            {'name': 'DG1', 'offline_disks': 0},
            {'name': 'DG2', 'offline_disks': 2},
            {'name': 'DG3', 'offline_disks': 1},
        ]
        
        offline_count = sum(dg['offline_disks'] for dg in diskgroups if dg['offline_disks'])
        
        self.assertEqual(offline_count, 3)
    
    def test_detect_abnormal_disk_states(self):
        """Test detection of disks not in NORMAL state"""
        disks = [
            {'disk_name': 'DISK1', 'state': 'NORMAL'},
            {'disk_name': 'DISK2', 'state': 'FORCING'},
            {'disk_name': 'DISK3', 'state': 'NORMAL'},
            {'disk_name': 'DISK4', 'state': 'UNKNOWN'},
        ]
        
        abnormal_disks = [d for d in disks if d['state'] != 'NORMAL']
        
        self.assertEqual(len(abnormal_disks), 2)
        disk_names = [d['disk_name'] for d in abnormal_disks]
        self.assertIn('DISK2', disk_names)
        self.assertIn('DISK4', disk_names)


def run_tests():
    """Run all test cases"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOracleASMDiagnostics))
    suite.addTests(loader.loadTestsFromTestCase(TestOracleErrorSimulator))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorDetection))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
