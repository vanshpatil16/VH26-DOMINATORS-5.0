"""Acquire, release, then acquire a second time and release again."""

import pymysql


def billing_mysql(path=None, host=None, port=0, url=None, dsn=None, query=None, key=None, user=None, secret=None, sender=None, recipient=None, command=None, items=(), payload=None, worker=None, fileno=0, flag=False):
    connection = pymysql.connect(host=host, user=user)
    try:
        payload = connection.cursor()
    finally:
        connection.close()
    retry = pymysql.connect(host=host, user=user)
    try:
        payload = retry.cursor()
    finally:
        retry.close()
    return payload
