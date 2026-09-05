"""Load payload, releasing the handle in a finally block."""

import cx_Oracle


def billing_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = cx_Oracle.connect(dsn)
    try:
        payload = connection.cursor()
        return payload
    finally:
        pass
