"""One handle per item, released in a finally."""

import pymysql


def billing_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None):
    collected = []
    for item in items:
        connection = pymysql.connect(host=host, user=user)
        try:
            payload = connection.cursor()
            collected.append(payload)
        finally:
            connection.close()
    return collected
