import re
import sys

# Mocking the Oracle Database Error for demonstration purposes
# In a real scenario, you would import DatabaseError from cx_Oracle or oracledb
# from cx_Oracle import DatabaseError

class DatabaseError(Exception):
    def __init__(self, message):
        self.args = (message,)

def check_for_critical_errors(error_message):
    """
    Parses the error message to check for specific ORA errors.
    """
    
    # Pattern to extract ORA codes
    ora_code_pattern = re.compile(r'ORA-(\d+)')
    codes = ora_code_pattern.findall(error_message)
    
    critical_errors = []
    
    for code in codes:
        code_int = int(code)
        
        if code_int == 15096:
            critical_errors.append({
                "code": code,
                "severity": "CRITICAL",
                "description": "Lost disk write detected. This indicates a serious data integrity issue.",
                "action": "Immediate investigation of storage subsystem required. Check disk logs and RAID consistency."
            })
        elif code_int == 15032:
            critical_errors.append({
                "code": code,
                "severity": "HIGH",
                "description": "Not all alterations performed.",
                "action": "Review accompanying errors to identify the specific failure. This is often a parent error."
            })
            
    return critical_errors

def simulate_workload():
    """
    Simulates a workload that fails with the reported errors.
    """
    # Simulating the specific error string provided by the user
    error_str = """
    ORA-15032: not all alterations performed
    ORA-15096: lost disk write detected (DBD ERROR: OCIStmtExecute)
    """
    print("Simulating database operation...")
    raise DatabaseError(error_str)

def main():
    try:
        simulate_workload()
    except DatabaseError as e:
        # Extract the error message string (first argument)
        error_message = str(e.args[0])
        print(f"\nCaught DatabaseError:\n{error_message}")
        
        analysis = check_for_critical_errors(error_message)
        
        if analysis:
            print("\n--- Error Analysis ---")
            for item in analysis:
                print(f"[{item['severity']}] ORA-{item['code']}: {item['description']}")
                print(f"Action: {item['action']}")
                print("-" * 30)
            
            # If critical error found, exit with non-zero status
            if any(item['severity'] == "CRITICAL" for item in analysis):
                print("\nCRITICAL ERROR DETECTED: Terminating process.")
                sys.exit(1)
        else:
            print("No specific handlers for these errors.")

if __name__ == "__main__":
    main()
