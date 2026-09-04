"""
Test Case 10: Nested Try-Except with Re-raised Exceptions
Description: Resource cleanup inside inner try block that may be bypassed by raised errors.
"""
import sqlite3

def complex_transaction_runner():
    conn = sqlite3.connect("bank.db")
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
        
        try:
            cursor.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 9999")
            if cursor.rowcount == 0:
                raise ValueError("Target account does not exist")
        except ValueError as ve:
            print(f"Transaction failed: {ve}")
            raise  # Re-raising exception, control bubbles up and escapes!
            
        conn.close()  # Unreachable when ValueError is re-raised!
    except Exception:
        # LEAK: Catching outer exception, but conn.close() was never called in a finally block!
        pass
