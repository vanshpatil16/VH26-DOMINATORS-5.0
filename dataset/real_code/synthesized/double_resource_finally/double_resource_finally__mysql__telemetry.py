"""Two independent handles, each released in its own finally."""

import pymysql


def telemetry_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    source = pymysql.connect(host=host, user=user)
    try:
        target = pymysql.connect(host=host, user=user)
        try:
            payload = source.cursor()
            payload = target.cursor()
        finally:
            target.close()
    finally:
        source.close()
    return payload
