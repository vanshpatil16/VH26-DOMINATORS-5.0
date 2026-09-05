"""
Test Case 10: Nested Try-Except with Re-raised Exceptions
Description: Resource cleanup inside inner try block that may be bypassed by raised errors.
"""
import sqlite3

def complex_transaction_runner():
    with sqlite3.connect("bank.db") as conn:
        pass
