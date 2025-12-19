import unittest
from oracle_monitor import check_for_critical_errors

class TestOracleMonitor(unittest.TestCase):
    def test_parsing_critical_error(self):
        error_msg = """
        ORA-15032: not all alterations performed
        ORA-15096: lost disk write detected (DBD ERROR: OCIStmtExecute)
        """
        results = check_for_critical_errors(error_msg)
        
        codes = [item['code'] for item in results]
        self.assertIn('15096', codes)
        self.assertIn('15032', codes)
        
        critical_errors = [item for item in results if item['severity'] == 'CRITICAL']
        self.assertEqual(len(critical_errors), 1)
        self.assertEqual(critical_errors[0]['code'], '15096')

    def test_no_errors(self):
        error_msg = "ORA-00000: normal successful completion"
        results = check_for_critical_errors(error_msg)
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()
