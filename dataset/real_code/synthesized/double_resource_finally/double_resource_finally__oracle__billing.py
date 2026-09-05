"""Two independent handles, each released in its own finally."""

import cx_Oracle


def billing_oracle(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = cx_Oracle.connect(dsn)
    try:
        target = cx_Oracle.connect(dsn)
        try:
            payload = source.cursor()
            payload = target.cursor()
        finally:
            target.close()
    finally:
        source.close()
    return payload
